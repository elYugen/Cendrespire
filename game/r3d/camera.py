"""Caméra 3D : perspective en plongée qui suit le héros, projection écran et lancer de rayon souris.

Conventions : la logique du jeu travaille en unités « monde 2D » (x, y au sol, 40 unités = 1 tuile)
et en hauteur z. En 3D : X = x/40, Y(haut) = z/40, Z = y/40.
"""
import math

import numpy as np

U = 1.0 / 40.0


def to3(x, y, z=0.0):
    return (x * U, z * U, y * U)


def perspective(fovy, aspect, near, far):
    f = 1.0 / math.tan(fovy / 2)
    m = np.zeros((4, 4), dtype="f4")
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


def ortho(l, r, b, t, n, f):
    m = np.identity(4, dtype="f4")
    m[0, 0] = 2 / (r - l)
    m[1, 1] = 2 / (t - b)
    m[2, 2] = -2 / (f - n)
    m[0, 3] = -(r + l) / (r - l)
    m[1, 3] = -(t + b) / (t - b)
    m[2, 3] = -(f + n) / (f - n)
    return m


def look_at(eye, target, up=(0, 1, 0)):
    eye, target, up = (np.array(v, dtype="f4") for v in (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.identity(4, dtype="f4")
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[0, 3], m[1, 3], m[2, 3] = -s @ eye, -u @ eye, f @ eye
    return m


class Camera3D:
    def __init__(self, yaw=45.0, pitch=52.0, dist=17.0, fov=36.0):
        self.yaw, self.pitch, self.dist, self.fov = yaw, pitch, dist, fov
        self.tx = self.ty = 0.0     # cible en coordonnées logiques
        self.tz = 0.0
        self.shake = 0.0
        self.shake_off = (0.0, 0.0)
        self.ndc_shift = (0.0, 0.0)   # décale l'image (portrait dans un menu)
        self.w, self.h = 1280, 720
        self.eye = np.zeros(3, dtype="f4")
        self.target = np.zeros(3, dtype="f4")
        self.update()

    def set_size(self, w, h):
        self.w, self.h = max(1, w), max(1, h)

    def update(self):
        yaw, pitch = math.radians(self.yaw), math.radians(self.pitch)
        t = np.array(to3(self.tx + self.shake_off[0], self.ty + self.shake_off[1], self.tz), dtype="f4")
        hd = np.array((math.sin(yaw), 0, math.cos(yaw)), dtype="f4")   # côté d'où regarde la caméra
        self.eye = t + (hd * math.cos(pitch) + np.array((0, math.sin(pitch), 0), dtype="f4")) * self.dist
        self.target = t
        self.view = look_at(self.eye, t)
        self.proj = perspective(math.radians(self.fov), self.w / self.h, 0.5, 120.0)
        if self.ndc_shift != (0.0, 0.0):
            T = np.identity(4, dtype="f4")
            T[0, 3], T[1, 3] = self.ndc_shift
            self.proj = T @ self.proj
        self.vp = (self.proj @ self.view).astype("f4")
        self.inv_vp = np.linalg.inv(self.vp)
        self.right = self.view[0, :3].copy()
        self.up = self.view[1, :3].copy()
        # direction « avant » à l'écran, projetée au sol (en coordonnées logiques x, y)
        fw = t - self.eye
        self.fwd2 = np.array((fw[0], fw[2]), dtype="f4")
        self.fwd2 /= np.linalg.norm(self.fwd2)
        self.right2 = np.array((self.right[0], self.right[2]), dtype="f4")
        self.right2 /= np.linalg.norm(self.right2)

    def screen_to_world_dir(self, mx, my):
        """Direction clavier (écran) -> direction logique au sol."""
        d = self.right2 * mx - self.fwd2 * my
        n = float(np.linalg.norm(d))
        return (float(d[0] / n), float(d[1] / n)) if n > 1e-6 else (0.0, 0.0)

    def project(self, x, y, z=0.0):
        """Coordonnées logiques -> pixels écran (None si derrière la caméra)."""
        p = self.vp @ np.array((*to3(x, y, z), 1.0), dtype="f4")
        if p[3] <= 0.01:
            return None
        return ((p[0] / p[3] + 1) * 0.5 * self.w, (1 - p[1] / p[3]) * 0.5 * self.h)

    def project_many(self, pts):
        arr = np.array([(x * U, z * U, y * U, 1.0) for x, y, z in pts], dtype="f4")
        p = arr @ self.vp.T
        w = np.maximum(p[:, 3], 0.01)
        return np.stack(((p[:, 0] / w + 1) * 0.5 * self.w, (1 - p[:, 1] / w) * 0.5 * self.h), axis=1)

    def ray_ground(self, sx, sy, height=0.0):
        """Point logique (x, y) visé par le pixel écran, sur un plan de hauteur donnée."""
        nx, ny = sx / self.w * 2 - 1, 1 - sy / self.h * 2
        a = self.inv_vp @ np.array((nx, ny, -1, 1), dtype="f4")
        b = self.inv_vp @ np.array((nx, ny, 1, 1), dtype="f4")
        a, b = a[:3] / a[3], b[:3] / b[3]
        d = b - a
        hy = height * U
        if abs(d[1]) < 1e-6:
            return self.tx, self.ty
        t = (hy - a[1]) / d[1]
        p = a + d * t
        return float(p[0] / U), float(p[2] / U)

    def pixel_scale(self, x, y, z=0.0):
        """Pixels écran par unité logique à cet endroit (pour dimensionner les textes)."""
        a = self.project(x, y, z)
        b = self.project(x, y, z + 40)
        if not a or not b:
            return 1.0
        return abs(a[1] - b[1]) / 40.0
