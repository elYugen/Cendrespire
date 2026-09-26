"""Effets sonores synthétisés à la volée (aucun fichier audio requis)."""
import array
import math
import random
import time

import pygame

_sounds = {}
_last = {}
_enabled = False


def init():
    global _enabled
    try:
        pygame.mixer.init(22050, -16, 1, 512)
        freq, size, ch = pygame.mixer.get_init()
        if size != -16:
            return
        pygame.mixer.set_num_channels(24)
        _build(freq, ch)
        _enabled = True
    except Exception:
        _enabled = False


def _make(freq, ch, dur, fn, vol=0.5):
    n = int(freq * dur)
    buf = array.array("h")
    for i in range(n):
        v = fn(i / freq, i / n)
        s = int(max(-1.0, min(1.0, v)) * vol * 32767)
        buf.append(s)
        if ch == 2:
            buf.append(s)
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _lowpass(k):
    state = [0.0]

    def f(x):
        state[0] += (x - state[0]) * k
        return state[0]
    return f


def _build(freq, ch):
    rnd = random.Random(7)
    noise = lambda: rnd.uniform(-1, 1)
    tau = math.tau

    lp1 = _lowpass(0.25)
    _sounds["swing"] = _make(freq, ch, 0.14, lambda t, p: lp1(noise()) * (1 - p) ** 2 * 1.6, 0.35)
    lp2 = _lowpass(0.15)
    _sounds["hit"] = _make(freq, ch, 0.13, lambda t, p: (math.sin(tau * (140 - 90 * p) * t) * (1 - p) ** 2
                                                        + lp2(noise()) * (1 - p) ** 5), 0.45)
    lp3 = _lowpass(0.5)
    _sounds["arrow"] = _make(freq, ch, 0.12, lambda t, p: lp3(noise()) * math.sin(math.pi * p) * 0.8, 0.3)
    _sounds["magic"] = _make(freq, ch, 0.2, lambda t, p: math.sin(tau * (500 + 500 * p) * t + 3 * math.sin(tau * 30 * t))
                             * (1 - p) * 0.7, 0.3)
    lp4 = _lowpass(0.08)
    _sounds["fire"] = _make(freq, ch, 0.35, lambda t, p: lp4(noise()) * 3 * math.sin(math.pi * p ** 0.5), 0.4)
    lp5 = _lowpass(0.05)
    _sounds["explosion"] = _make(freq, ch, 0.6, lambda t, p: (lp5(noise()) * 4 + math.sin(tau * 55 * t) * 0.6)
                                 * (1 - p) ** 2, 0.5)
    _sounds["ice"] = _make(freq, ch, 0.45, lambda t, p: (math.sin(tau * 1320 * t) + math.sin(tau * 1760 * t)
                                                        + math.sin(tau * 2093 * t)) / 3 * (1 - p) ** 1.5, 0.3)
    _sounds["gold"] = _make(freq, ch, 0.16, lambda t, p: math.sin(tau * (1250 if p < 0.4 else 1650) * t) * (1 - p), 0.25)
    _sounds["pickup"] = _make(freq, ch, 0.12, lambda t, p: math.sin(tau * (600 + 400 * p) * t) * (1 - p), 0.3)
    _sounds["levelup"] = _make(freq, ch, 0.8, lambda t, p: math.sin(tau * [523, 659, 784, 1046][min(3, int(p * 4))] * t)
                               * (1 - p) ** 0.5, 0.35)
    lp6 = _lowpass(0.2)
    _sounds["hurt"] = _make(freq, ch, 0.16, lambda t, p: (math.sin(tau * 95 * t) + lp6(noise()) * 1.5) * (1 - p), 0.4)
    _sounds["death"] = _make(freq, ch, 0.35, lambda t, p: (math.sin(tau * (220 - 160 * p) * t) * 0.6
                                                          + (noise() if rnd.random() < 0.08 else 0)) * (1 - p), 0.35)
    _sounds["potion"] = _make(freq, ch, 0.35, lambda t, p: math.sin(tau * (300 + 200 * math.sin(tau * 12 * t)) * t) * (1 - p), 0.3)
    lp7 = _lowpass(0.03)
    _sounds["portal"] = _make(freq, ch, 1.0, lambda t, p: (lp7(noise()) * 5 * math.sin(math.pi * p)
                                                          + math.sin(tau * (200 + 300 * p) * t) * 0.3 * math.sin(math.pi * p)), 0.4)
    lp8 = _lowpass(0.06)
    _sounds["roar"] = _make(freq, ch, 1.2, lambda t, p: ((((t * 60) % 1) * 2 - 1) * 0.5 + lp8(noise()) * 3)
                            * math.sin(math.pi * min(1, p * 3)) * (1 - p), 0.5)
    _sounds["click"] = _make(freq, ch, 0.05, lambda t, p: math.sin(tau * 900 * t) * (1 - p), 0.2)
    _sounds["chest"] = _make(freq, ch, 0.4, lambda t, p: (math.sin(tau * 180 * t) * (1 - p) + (noise() * 0.3 if p < 0.2 else 0)), 0.4)
    _sounds["seal"] = _make(freq, ch, 1.0, lambda t, p: (math.sin(tau * 110 * t) + math.sin(tau * 165 * t)) / 2
                            * math.sin(math.pi * p), 0.4)


def play(name, vol=1.0):
    if not _enabled:
        return
    s = _sounds.get(name)
    if s is None:
        return
    now = time.monotonic()
    if now - _last.get(name, 0) < 0.04:
        return
    _last[name] = now
    s.set_volume(vol)
    s.play()
