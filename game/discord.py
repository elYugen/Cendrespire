"""Discord Rich Presence : « Joue à Cendrespire », avec le lieu (menu, village, étage) et le héros.

Parle directement au client Discord de l'ordinateur (tube nommé sous Windows, socket Unix sous macOS / Linux) :
aucun paquet supplémentaire. Tout se passe dans un fil d'exécution à part ; si Discord n'est pas lancé, le jeu
réessaie de temps en temps, sans jamais gêner la partie.

Le nom affiché (« Joue à … ») et les images sont ceux de l'application Discord dont l'identifiant est
DISCORD_APP_ID (settings.py), créée sur https://discord.com/developers/applications. Images (onglet
Rich Presence > Art Assets) : « logo » (grande image) et, en option, une image par classe (« barbare », ...).
"""
import json
import os
import socket
import struct
import sys
import threading
import time
import uuid

from .settings import DISCORD_APP_ID

RETRY = 20.0          # secondes entre deux tentatives de connexion à Discord
MIN_GAP = 5.0         # Discord limite les mises à jour (5 par 20 s)

_lock = threading.Lock()
_wanted = None        # activité demandée par le jeu (dict), ou None
_wake = threading.Event()
_thread = None
_scene = None
_since = int(time.time())


def update(scene):
    """Appelé à chaque image : calcule l'activité de la scène courante et la transmet si elle a changé."""
    global _scene, _since
    if not DISCORD_APP_ID:
        return
    if scene is not _scene:
        _scene = scene
        if getattr(scene, "presence_timer", False):   # chrono remis à zéro en entrant au village ou dans un étage
            _since = int(time.time())
    fn = getattr(scene, "presence", None)
    info = fn() if fn else None
    if info is None:          # écran de chargement : on garde l'état précédent
        return
    details, state, small = (tuple(info) + (None, None))[:3]
    act = {"details": details, "timestamps": {"start": _since},
           "assets": {"large_image": "logo", "large_text": "Cendrespire"}}
    if state:
        act["state"] = state
    if small:
        act["assets"]["small_image"], act["assets"]["small_text"] = small
    _set(act)


def _set(act):
    global _wanted, _thread
    with _lock:
        if act == _wanted:
            return
        _wanted = act
    _wake.set()
    if _thread is None:
        _thread = threading.Thread(target=_run, name="discord-rpc", daemon=True)
        _thread.start()


# ------------------------------------------------------------------ connexion au client Discord
class _Pipe:
    def __init__(self):
        self.f = self.sock = None
        for i in range(10):
            try:
                if sys.platform == "win32":
                    self.f = open(rf"\\?\pipe\discord-ipc-{i}", "r+b", buffering=0)
                else:
                    base = next((os.environ[k] for k in ("XDG_RUNTIME_DIR", "TMPDIR", "TMP", "TEMP")
                                 if os.environ.get(k)), "/tmp")
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.settimeout(10)
                    s.connect(os.path.join(base, f"discord-ipc-{i}"))
                    self.sock = s
                return
            except OSError:
                continue
        raise OSError("Discord n'est pas lancé")

    def send(self, op, payload):
        data = json.dumps(payload).encode("utf-8")
        msg = struct.pack("<II", op, len(data)) + data
        if self.f:
            self.f.write(msg)
        else:
            self.sock.sendall(msg)

    def _read(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.f.read(n - len(buf)) if self.f else self.sock.recv(n - len(buf))
            if not chunk:
                raise OSError("connexion fermée")
            buf += chunk
        return buf

    def recv(self):
        op, n = struct.unpack("<II", self._read(8))
        return op, json.loads(self._read(n).decode("utf-8"))

    def close(self):
        for o in (self.f, self.sock):
            try:
                o and o.close()
            except OSError:
                pass


def _run():
    pipe, sent, last = None, None, 0.0
    while True:
        _wake.wait(RETRY if pipe is None else None)
        _wake.clear()
        try:
            if pipe is None:
                pipe = _Pipe()
                pipe.send(0, {"v": 1, "client_id": DISCORD_APP_ID})
                op, data = pipe.recv()
                if data.get("evt") != "READY":
                    raise OSError(data.get("message", "refusé par Discord"))
                sent = None
            wait = MIN_GAP - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
            with _lock:
                act = _wanted
            if act != sent:
                pipe.send(1, {"cmd": "SET_ACTIVITY", "args": {"pid": os.getpid(), "activity": act},
                              "nonce": str(uuid.uuid4())})
                pipe.recv()
                sent, last = act, time.monotonic()
        except (OSError, ValueError, struct.error):
            if pipe:
                pipe.close()
            pipe = None
