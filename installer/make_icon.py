"""Dessine l'icône de Cendrespire (la tour sur fond de braises) et l'écrit en .ico multi-tailles.

L'icône du jeu est assets/cendrespire.ico ; ce script sert à la regénérer (ou à la créer si elle manque).
Usage : python installer/make_icon.py [sortie.ico]   (par défaut : assets/cendrespire.ico)
"""
import io
import math
import os
import struct
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

SIZES = (256, 64, 48, 32, 16)


def draw(size):
    big = size * 4   # sur-échantillonné puis réduit : bords lisses
    s = pygame.Surface((big, big), pygame.SRCALPHA)
    c = big / 2
    # disque de fond : dégradé braise vers nuit
    for i in range(60, 0, -1):
        k = i / 60
        col = (int(18 + 150 * (1 - k) ** 2), int(12 + 50 * (1 - k) ** 3), int(22 + 10 * (1 - k)))
        pygame.draw.circle(s, col, (c, c), big * 0.48 * k)
    pygame.draw.circle(s, (236, 206, 140), (c, c), big * 0.48, max(2, big // 64))
    # la tour : une flèche effilée, sombre, avec des créneaux
    base_y, top_y = big * 0.84, big * 0.12
    tower = [(c - big * 0.17, base_y), (c - big * 0.11, big * 0.46), (c - big * 0.07, big * 0.46),
             (c - big * 0.045, big * 0.30), (c, top_y), (c + big * 0.045, big * 0.30), (c + big * 0.07, big * 0.46),
             (c + big * 0.11, big * 0.46), (c + big * 0.17, base_y)]
    pygame.draw.polygon(s, (14, 10, 12), tower)
    pygame.draw.polygon(s, (236, 206, 140), tower, max(2, big // 80))
    # fenêtres rougeoyantes
    for fy, fw in ((0.62, 0.028), (0.52, 0.022), (0.38, 0.016)):
        r = pygame.Rect(0, 0, big * fw, big * fw * 2.2)
        r.center = (c, big * fy)
        pygame.draw.rect(s, (255, 150, 50), r, border_radius=int(r.w / 2))
    # cendres qui s'élèvent
    for i in range(14):
        a = i * 2.39996
        rr = big * (0.16 + 0.26 * ((i * 37) % 11) / 11)
        x, y = c + math.cos(a) * rr, c + math.sin(a) * rr * 0.9
        if abs(x - c) > big * 0.13:
            pygame.draw.circle(s, (255, 190, 110), (x, y), big * (0.008 + 0.006 * (i % 3)))
    return pygame.transform.smoothscale(s, (size, size))


def write_ico(path):
    """Fichier .ico dont chaque image est un PNG (format reconnu par Windows depuis Vista)."""
    blobs = []
    for n in SIZES:
        buf = io.BytesIO()
        pygame.image.save(draw(n), buf, "png")
        blobs.append(buf.getvalue())
    header = struct.pack("<HHH", 0, 1, len(SIZES))
    offset = 6 + 16 * len(SIZES)
    entries = b""
    for n, data in zip(SIZES, blobs):
        entries += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    with open(path, "wb") as f:
        f.write(header + entries + b"".join(blobs))


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "assets", "cendrespire.ico")
    write_ico(out)
    print("Icône écrite :", out)
