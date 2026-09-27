"""Moteur de rendu 3D (moderngl) : ombres portées, lumières ponctuelles, instanciation,
décalques au sol, particules, ciel en dégradé et composition de l'interface pygame."""
import math
from collections import defaultdict

import moderngl
import numpy as np
import pygame

from . import shaders as S
from .camera import U, look_at, ortho
from .meshes import PRIMITIVES, quad2d

OUTLINES = False           # contour noir des personnages (désactivé : rendu plus doux)
INST_FMT = "3f 3f 3f 3f 4f/i"
INST_ATTRS = ("i_ax", "i_ay", "i_az", "i_pos", "i_col")
IDENTITY = np.array([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0], dtype="f4")


def _c(col):
    return (col[0] / 255.0, col[1] / 255.0, col[2] / 255.0)


class Frame:
    """Tout ce qu'il faut dessiner pour une image, en coordonnées logiques (x, y au sol, z en hauteur)."""

    def __init__(self):
        self.parts = defaultdict(list)
        self.adds = defaultdict(list)
        self.decals = []
        self.glows = []
        self.solids = []
        self.lights = []
        self.outline = False       # vrai pendant le dessin d'un personnage : contour cartoon et ombrage en paliers
        self.skinned = []          # personnages animés : (modèle, matrice, articulations, palette, teinte, émission)

    def skin(self, model, matrix, joints, palette, tint=(0.0, 0.0, 0.0, 0.0), emis=0.0):
        """Personnage animé (glTF) : matrice de placement en coordonnées 3D du moteur."""
        self.skinned.append((model, matrix, joints, palette, tint, emis))

    @staticmethod
    def _v(v):
        return (v[0] * U, v[2] * U, v[1] * U)

    def part(self, mesh, c, ax, ay, az, color, emis=0.0, additive=False):
        a, b, d, p = self._v(ax), self._v(ay), self._v(az), self._v(c)
        col = _c(color)
        if additive:
            target = self.adds[mesh]
        else:
            target = self.parts[mesh + "#o" if self.outline else mesh]
        target.extend(
            (a[0], a[1], a[2], b[0], b[1], b[2], d[0], d[1], d[2], p[0], p[1], p[2], col[0], col[1], col[2], emis))

    def box(self, x, y, z, hx, hy, hz, color, emis=0.0, mesh="cube", additive=False):
        """Forme alignée sur les axes, posée sur la hauteur z (base)."""
        self.part(mesh, (x, y, z + hz), (hx, 0, 0), (0, 0, hz), (0, hy, 0), color, emis, additive)

    def decal(self, x, y, rx, ry, color, alpha, kind=0, rot=0.0, inner=0.0, p1=0.0, lift=0.0):
        c = _c(color)
        self.decals.extend((x * U, 0.015 + lift, y * U, rx * U, ry * U, rot, c[0], c[1], c[2], alpha,
                            kind, inner, p1, 0.0))

    def glow(self, x, y, z, size, color, alpha=1.0):
        c = _c(color)
        self.glows.extend((x * U, z * U, y * U, size * U, c[0], c[1], c[2], alpha))

    def solid(self, x, y, z, size, color, alpha=1.0):
        c = _c(color)
        self.solids.extend((x * U, z * U, y * U, size * U, c[0], c[1], c[2], alpha))

    def light(self, x, y, z, radius, color, intensity=1.0):
        self.lights.append((x * U, z * U, y * U, radius * U, color[0] / 255, color[1] / 255, color[2] / 255,
                            intensity))


class Env:
    """Ambiance d'une scène."""

    def __init__(self, **kw):
        self.clear = (0.02, 0.02, 0.03)
        self.sky = None                     # (haut, milieu, bas, soleil_écran(x,y,intensité), couleur_soleil)
        self.sun_dir = (-0.45, -1.0, -0.3)
        self.sun_col = (0.22, 0.24, 0.32)
        self.amb_sky = (0.2, 0.2, 0.26)
        self.amb_ground = (0.09, 0.08, 0.08)
        self.shadows = True
        self.shadow_extent = 17.0
        self.cut = 1.7
        self.fog_col = (0.0, 0.0, 0.0)
        self.fog = (16.0, 30.0)
        self.player = (0.0, 0.0, 0.0)
        self.__dict__.update(kw)


class Renderer:
    def __init__(self, ctx):
        self.ctx = ctx
        ctx.enable(moderngl.DEPTH_TEST)
        self.p_lit = ctx.program(vertex_shader=S.LIT_VS, fragment_shader=S.LIT_FS)
        self.p_add = ctx.program(vertex_shader=S.LIT_VS, fragment_shader=S.ADD_FS)
        self.p_depth = ctx.program(vertex_shader=S.DEPTH_VS, fragment_shader=S.DEPTH_FS)
        self.p_decal = ctx.program(vertex_shader=S.DECAL_VS, fragment_shader=S.DECAL_FS)
        self.p_part = ctx.program(vertex_shader=S.PART_VS, fragment_shader=S.PART_FS)
        self.p_sky = ctx.program(vertex_shader=S.SKY_VS, fragment_shader=S.SKY_FS)
        self.p_ui = ctx.program(vertex_shader=S.UI_VS, fragment_shader=S.UI_FS)
        self.p_outline = ctx.program(vertex_shader=S.OUTLINE_VS, fragment_shader=S.OUTLINE_FS)
        try:
            self.p_skin = ctx.program(vertex_shader=S.SKIN_VS, fragment_shader=S.LIT_FS)
            self.p_skin_depth = ctx.program(vertex_shader=S.SKIN_DEPTH_VS, fragment_shader=S.DEPTH_FS)
            self.p_skin_outline = ctx.program(vertex_shader=S.SKIN_OUTLINE_VS, fragment_shader=S.OUTLINE_FS)
        except Exception as e:          # carte graphique trop limitée : héros procéduraux
            from . import skinned
            skinned.ENABLED = False
            print(f"[personnages] animation sur carte graphique indisponible ({e}) : modèles procéduraux")
        self.skin_gpu = {}

        self.meshes = {}
        for name, fn in PRIMITIVES.items():
            data = fn()
            vbo = ctx.buffer(data.tobytes())
            # deux jeux d'instances par primitive : décor / effets, et personnages (« #o », avec contour)
            for key in (name, name + "#o"):
                ibuf = ctx.buffer(reserve=64 * 64, dynamic=True)
                self.meshes[key] = {
                    "n": len(data) // 10, "ibuf": ibuf, "toon": key.endswith("#o"),
                    "lit": self._vao(self.p_lit, vbo, ibuf, depth=False),
                    "add": self._vao(self.p_add, vbo, ibuf, depth=False),
                    "depth": self._vao(self.p_depth, vbo, ibuf, depth=True),
                    "outline": self.ctx.vertex_array(self.p_outline, [(vbo, "3f 3f 16x", "in_pos", "in_norm"),
                                                                      (ibuf, INST_FMT, *INST_ATTRS)]),
                }
        self.ident = ctx.buffer(IDENTITY.tobytes())
        self.static = None
        q = ctx.buffer(quad2d().tobytes())
        self.decal_buf = ctx.buffer(reserve=56 * 64, dynamic=True)
        self.vao_decal = ctx.vertex_array(self.p_decal, [(q, "2f", "in_uv"),
                                                         (self.decal_buf, "3f 2f 1f 4f 4f/i", "i_c", "i_r", "i_rot",
                                                          "i_col", "i_shape")])
        self.part_buf = ctx.buffer(reserve=32 * 64, dynamic=True)
        self.vao_part = ctx.vertex_array(self.p_part, [(q, "2f", "in_uv"),
                                                       (self.part_buf, "3f 1f 4f/i", "i_p", "i_s", "i_col")])
        self.vao_sky = ctx.vertex_array(self.p_sky, [(q, "2f", "in_uv")])
        self.vao_ui = ctx.vertex_array(self.p_ui, [(q, "2f", "in_uv")])
        self.p_dim = ctx.program(vertex_shader=S.DIM_VS, fragment_shader=S.DIM_FS)
        self.vao_dim = ctx.vertex_array(self.p_dim, [(q, "2f", "in_uv")])
        self.shadow_tex = ctx.depth_texture((2048, 2048))
        self.shadow_tex.compare_func = "<="
        self.shadow_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.shadow_fbo = ctx.framebuffer(depth_attachment=self.shadow_tex)
        self.size = None
        self.msaa = None
        self.ui_tex = None
        self.samples = min(4, ctx.max_samples)

    def _vao(self, prog, vbo, ibuf, depth):
        if depth:
            return self.ctx.vertex_array(prog, [(vbo, "3f 12x 16x", "in_pos"), (ibuf, "3f 3f 3f 3f 16x/i", *INST_ATTRS[:4])])
        return self.ctx.vertex_array(prog, [(vbo, "3f 3f 4f", "in_pos", "in_norm", "in_col"), (ibuf, INST_FMT, *INST_ATTRS)])

    def _skin_gpu(self, model):
        """Envoie une fois pour toutes les sommets d'un modèle animé à la carte graphique."""
        key = id(model)
        if key not in self.skin_gpu:
            vbo = self.ctx.buffer(model.vertices.tobytes())
            fmt = ("3f 3f 1f 4f 4f", "in_pos", "in_norm", "in_mat", "in_joints", "in_weights")
            self.skin_gpu[key] = {
                "lit": self.ctx.vertex_array(self.p_skin, [(vbo, *fmt)]),
                "depth": self.ctx.vertex_array(self.p_skin_depth,
                                               [(vbo, "3f 12x 4x 4f 4f", "in_pos", "in_joints", "in_weights")]),
                "outline": self.ctx.vertex_array(self.p_skin_outline, [(vbo, *fmt)]),
                "vbo": vbo,
            }
        return self.skin_gpu[key]

    @staticmethod
    def _joints_bytes(joints):
        buf = np.zeros((64, 4, 4), dtype="f4")
        buf[:len(joints)] = joints.transpose(0, 2, 1)
        return buf.tobytes()

    def _draw_skinned(self, frame, pass_name, **uniforms):
        prog = {"lit": self.p_skin, "depth": self.p_skin_depth, "outline": self.p_skin_outline}[pass_name]
        for name, val in uniforms.items():
            if name in prog:
                if isinstance(val, bytes):
                    prog[name].write(val)
                else:
                    prog[name].value = val
        for model, matrix, joints, palette, tint, emis in frame.skinned:
            g = self._skin_gpu(model)
            prog["u_model"].write(np.ascontiguousarray(matrix.T, dtype="f4").tobytes())
            prog["u_joints"].write(self._joints_bytes(joints))
            if "u_pal" in prog:
                prog["u_pal"].write(np.ascontiguousarray(palette, dtype="f4").tobytes())
            if "u_tint" in prog:
                prog["u_tint"].value = tuple(tint)
            if "u_emis" in prog:
                prog["u_emis"].value = emis
            g[pass_name].render()

    # ------------------------------------------------------------------ ressources
    def set_static(self, arr):
        """Maillage statique du niveau (sol, murs, décor)."""
        if self.static:
            for v in self.static.values():
                v.release()
            self.static = None
        if arr is None or len(arr) == 0:
            return
        vbo = self.ctx.buffer(np.ascontiguousarray(arr, dtype="f4").tobytes())
        self.static = {
            "vbo": vbo,
            "lit": self.ctx.vertex_array(self.p_lit, [(vbo, "3f 3f 4f", "in_pos", "in_norm", "in_col"),
                                                      (self.ident, INST_FMT, *INST_ATTRS)]),
            "depth": self.ctx.vertex_array(self.p_depth, [(vbo, "3f 12x 16x", "in_pos"),
                                                          (self.ident, "3f 3f 3f 3f 16x/i", *INST_ATTRS[:4])]),
        }
        self.static_n = len(arr)

    def ensure_size(self, size):
        if size == self.size:
            return
        self.size = size
        if self.msaa:
            for o in self.msaa:
                o.release()
        color = self.ctx.renderbuffer(size, samples=self.samples)
        depth = self.ctx.depth_renderbuffer(size, samples=self.samples)
        self.msaa = (self.ctx.framebuffer(color_attachments=[color], depth_attachment=depth), color, depth)

    @staticmethod
    def _set(prog, name, value):
        if name in prog:
            prog[name].value = value

    @staticmethod
    def _write(buf, data):
        b = data.tobytes()
        if len(b) > buf.size:
            buf.orphan(max(len(b), buf.size * 2))
        buf.write(b)

    # ------------------------------------------------------------------ image
    def render(self, frame, cam, env, screen, overlay=None):
        """overlay : (couleur de voile rgba) — l'image précédente est gardée, assombrie, et la scène est dessinée
        par-dessus (portrait du héros devant le jeu, dans les menus)."""
        ctx = self.ctx
        self.ensure_size(screen.size)
        cam.set_size(*screen.size)
        cam.update()
        counts = {}
        for name, data in frame.parts.items():
            arr = np.array(data, dtype="f4")
            self._write(self.meshes[name]["ibuf"], arr)
            counts[name] = len(arr) // 16

        # ombres (lumière directionnelle orthographique autour de la cible)
        L = np.array(env.sun_dir, dtype="f4")
        L /= np.linalg.norm(L)
        tgt = cam.target
        ext = env.shadow_extent
        texel = ext * 2 / 2048
        snapped = np.floor(tgt / texel) * texel
        lv = look_at(snapped - L * 40, snapped, (0, 1, 0) if abs(L[1]) < 0.99 else (0, 0, 1))
        light_vp = (ortho(-ext, ext, -ext, ext, 1.0, 90.0) @ lv).astype("f4")
        lvp_bytes = light_vp.T.tobytes()
        if env.shadows:
            self.shadow_fbo.use()
            ctx.viewport = (0, 0, 2048, 2048)
            self.shadow_fbo.clear(depth=1.0)
            ctx.enable(moderngl.DEPTH_TEST)
            ctx.disable(moderngl.BLEND)
            self.p_depth["u_light_vp"].write(lvp_bytes)
            if self.static:
                self.static["depth"].render(instances=1)
            for name, n in counts.items():
                if n:
                    self.meshes[name]["depth"].render(instances=n)
            if frame.skinned:
                self._draw_skinned(frame, "depth", u_light_vp=lvp_bytes)

        # passe principale (anticrénelage 4x)
        fbo = self.msaa[0]
        fbo.use()
        ctx.viewport = (0, 0, *screen.size)
        if overlay:
            ctx.disable(moderngl.DEPTH_TEST)
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            self.p_dim["u_col"].value = tuple(overlay)
            self.vao_dim.render()
            fbo.color_mask = (False, False, False, False)
            fbo.use()                      # le masque de couleur ne s'applique qu'à l'activation
            fbo.clear(depth=1.0)
            fbo.color_mask = (True, True, True, True)
            fbo.use()
        else:
            fbo.clear(*env.clear, 1.0, depth=1.0)
        vp_bytes = cam.vp.T.astype("f4").tobytes()
        if env.sky and not overlay:
            top, mid, bottom, sun, sun_col = env.sky
            ctx.disable(moderngl.DEPTH_TEST)
            self._set(self.p_sky, "u_top", top)
            self._set(self.p_sky, "u_mid", mid)
            self._set(self.p_sky, "u_bottom", bottom)
            self._set(self.p_sky, "u_sun", sun)
            self._set(self.p_sky, "u_sun_col", sun_col)
            self._set(self.p_sky, "u_aspect", screen.size[0] / screen.size[1])
            self.vao_sky.render()
        ctx.enable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND)
        p = self.p_lit
        p["u_vp"].write(vp_bytes)
        if "u_light_vp" in p:
            p["u_light_vp"].write(lvp_bytes)
        self._set(p, "u_sun_dir", tuple(L))
        self._set(p, "u_sun_col", env.sun_col)
        self._set(p, "u_sky", env.amb_sky)
        self._set(p, "u_ground", env.amb_ground)
        self._set(p, "u_shadow_on", 1.0 if env.shadows else 0.0)
        self._set(p, "u_cam", tuple(cam.eye))
        pl = env.player
        self._set(p, "u_player", (pl[0] * U, (pl[2] + 22) * U, pl[1] * U))
        self._set(p, "u_cut", env.cut)
        self._set(p, "u_fog_col", env.fog_col)
        self._set(p, "u_fog_center", (float(tgt[0]), 0.0, float(tgt[2])))
        self._set(p, "u_fog", env.fog)
        lights = sorted(frame.lights, key=lambda l: (l[0] - tgt[0]) ** 2 + (l[2] - tgt[2]) ** 2)[:S.MAX_LIGHTS]
        lp = np.zeros((S.MAX_LIGHTS, 4), dtype="f4")
        lc = np.zeros((S.MAX_LIGHTS, 4), dtype="f4")
        for i, l in enumerate(lights):
            lp[i] = l[0:4]
            lc[i] = l[4:8]
        if "u_lpos" in p:
            p["u_lpos"].write(lp.tobytes())
            p["u_lcol"].write(lc.tobytes())
        self._set(p, "u_nl", len(lights))
        if "u_shadow" in p:
            self.shadow_tex.use(location=0)
            p["u_shadow"].value = 0
        self._set(p, "u_toon", 0.0)
        if self.static:
            self.static["lit"].render(instances=1)
        for toon in (False, True):
            self._set(p, "u_toon", 1.0 if toon else 0.0)
            for name, n in counts.items():
                if n and self.meshes[name]["toon"] == toon:
                    self.meshes[name]["lit"].render(instances=n)
        if frame.skinned:
            ps = self.p_skin
            for name in ("u_sun_dir", "u_sun_col", "u_sky", "u_ground", "u_shadow_on", "u_cam", "u_player", "u_cut",
                         "u_fog_col", "u_fog_center", "u_fog", "u_nl"):
                if name in p and name in ps:
                    ps[name].value = p[name].value
            if "u_lpos" in ps:
                ps["u_lpos"].write(lp.tobytes())
                ps["u_lcol"].write(lc.tobytes())
            if "u_shadow" in ps:
                ps["u_shadow"].value = 0
            self._set(ps, "u_toon", 1.0)
            self._draw_skinned(frame, "lit", u_vp=vp_bytes, u_light_vp=lvp_bytes)
        # contours des personnages (épaisseur ~2 px à 720p, proportionnelle à la définition)
        po = self.p_outline if OUTLINES else None
        if po:
            po["u_vp"].write(vp_bytes)
            self._set(po, "u_cam", tuple(float(v) for v in cam.eye))
            w_px = max(1.5, screen.size[1] / 720 * 2.0)
            self._set(po, "u_px", (2 * w_px / screen.size[0], 2 * w_px / screen.size[1]))
            for name, n in counts.items():
                if n and self.meshes[name]["toon"]:
                    self.meshes[name]["outline"].render(instances=n)
        if po and frame.skinned:
            self._draw_skinned(frame, "outline", u_vp=vp_bytes, u_px=po["u_px"].value if "u_px" in po else (0, 0),
                               u_cam=tuple(float(v) for v in cam.eye))

        # décalques au sol
        if frame.decals:
            arr = np.array(frame.decals, dtype="f4")
            self._write(self.decal_buf, arr)
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            fbo.depth_mask = False
            self.p_decal["u_vp"].write(vp_bytes)
            self.vao_decal.render(instances=len(arr) // 14)
            fbo.depth_mask = True

        # formes additives (énergie, faisceaux)
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.ONE, moderngl.ONE
        fbo.depth_mask = False
        pa = self.p_add
        pa["u_vp"].write(vp_bytes)
        self._set(pa, "u_cam", tuple(cam.eye))
        for name, data in frame.adds.items():
            arr = np.array(data, dtype="f4")
            self._write(self.meshes[name]["ibuf"], arr)
            self.meshes[name]["add"].render(instances=len(arr) // 16)

        # particules
        pp = self.p_part
        pp["u_vp"].write(vp_bytes)
        self._set(pp, "u_right", tuple(float(v) for v in cam.right))
        self._set(pp, "u_up", tuple(float(v) for v in cam.up))
        if frame.solids:
            arr = np.array(frame.solids, dtype="f4")
            self._write(self.part_buf, arr)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            fbo.depth_mask = True
            self._set(pp, "u_mode", 1)
            self.vao_part.render(instances=len(arr) // 8)
            fbo.depth_mask = False
        if frame.glows:
            arr = np.array(frame.glows, dtype="f4")
            self._write(self.part_buf, arr)
            ctx.blend_func = moderngl.ONE, moderngl.ONE
            self._set(pp, "u_mode", 0)
            self.vao_part.render(instances=len(arr) // 8)
        fbo.depth_mask = True
        ctx.disable(moderngl.BLEND)
        ctx.copy_framebuffer(screen, fbo)

    # ------------------------------------------------------------------ composition finale
    def clear(self, target, color=(0.0, 0.0, 0.0)):
        target.use()
        target.clear(*color, 1.0)

    def present(self, screen, screen_size, viewport, color_tex, ui_surf):
        """Image 3D puis interface pygame (alpha prémultiplié), dans la zone 16:9 de l'écran."""
        ctx = self.ctx
        screen.use()
        ctx.viewport = (0, 0, *screen_size)
        screen.clear(0.0, 0.0, 0.0, 1.0)
        ctx.viewport = viewport
        ctx.disable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND)
        color_tex.use(location=0)
        self.p_ui["u_tex"].value = 0
        self.p_ui["u_flip"].value = 0.0
        self.vao_ui.render()
        size = ui_surf.get_size()
        if self.ui_tex is None or self.ui_tex.size != size:
            if self.ui_tex:
                self.ui_tex.release()
            self.ui_tex = ctx.texture(size, 4)
            self.ui_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
            masks = ui_surf.get_masks()
            self.ui_tex.swizzle = "BGRA" if masks[0] == 0xFF0000 else "RGBA"
        self.ui_tex.write(ui_surf.get_view("1"))
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA
        self.ui_tex.use(location=0)
        self.p_ui["u_flip"].value = 1.0
        self.vao_ui.render()
        ctx.disable(moderngl.BLEND)
        ctx.enable(moderngl.DEPTH_TEST)
