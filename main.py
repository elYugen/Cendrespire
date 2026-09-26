"""Cendrespire — point d'entrée.

Lancement :  python main.py
Rendu 3D (moderngl / OpenGL 3.3) + interface pygame, à la résolution native de l'écran (Retina compris).
"""
import sys

import moderngl
import pygame

from game import sfx
from game.r3d.renderer import Renderer, Frame
from game.settings import SCREEN_W, SCREEN_H, FPS, TITLE, VIEW

MOUSE_EVENTS = (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)


class Game:
    def __init__(self, headless=False, size=(SCREEN_W, SCREEN_H)):
        pygame.init()
        sfx.init()
        self.headless = headless
        if headless:
            self.window = None
            self.ctx = moderngl.create_context(standalone=True, require=330)
            self.ratio = 1.0
            self.screen = self.ctx.simple_framebuffer(size)
            self.screen_size = size
        else:
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, True)
            self.window = pygame.Window(TITLE, size, opengl=True, allow_high_dpi=True, resizable=True)
            self.window.minimum_size = (640, 360)
            self.ctx = moderngl.create_context()
            self.ratio = self.ctx.screen.size[0] / self.window.size[0]
            self.screen = self.ctx.screen
            self.screen_size = self.ctx.screen.size
            pygame.key.start_text_input()
        self.renderer = Renderer(self.ctx)
        self.target = None
        self.ui_surf = None
        self.static_owner = None
        self.refresh_view()
        self.clock = pygame.time.Clock()
        self.running = True
        self.next_scene = None
        self.fade = 1.0
        self.fading_out = False
        from game.scenes import TitleScene
        self.scene = TitleScene(self)

    # ------------------------------------------------------------------ affichage
    def refresh_view(self):
        if self.window:
            pw, ph = self.window.size
            fw, fh = int(round(pw * self.ratio)), int(round(ph * self.ratio))
            self.ctx.viewport = (0, 0, fw, fh)
            self.screen = self.ctx.detect_framebuffer()
            self.screen_size = (fw, fh)
        fw, fh = self.screen_size
        s = min(fw / SCREEN_W, fh / SCREEN_H)
        cw, ch = int(SCREEN_W * s), int(SCREEN_H * s)
        VIEW.s = s
        VIEW.w, VIEW.h = cw, ch
        VIEW.ox, VIEW.oy = (fw - cw) // 2, (fh - ch) // 2
        VIEW.ratio = self.ratio
        VIEW.version += 1
        if self.target:
            self.target.release()
            self.target_tex.release()
            self.target_depth.release()
        self.target_tex = self.ctx.texture((cw, ch), 4)
        self.target_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.target_depth = self.ctx.depth_renderbuffer((cw, ch))
        self.target = self.ctx.framebuffer(color_attachments=[self.target_tex], depth_attachment=self.target_depth)
        self.ui_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)

    def toggle_fullscreen(self):
        if not self.window:
            return
        if self.window.size != pygame.display.get_desktop_sizes()[0]:
            self.window.set_fullscreen(True)
        else:
            self.window.set_windowed()
        self.refresh_view()

    def change_scene(self, scene):
        self.next_scene = scene
        self.fading_out = True

    def quit(self):
        self.running = False

    def convert_event(self, e):
        if e.type in MOUSE_EVENTS:
            d = dict(e.dict)
            x, y = e.pos
            d["pos"] = ((x * self.ratio - VIEW.ox) / VIEW.s, (y * self.ratio - VIEW.oy) / VIEW.s)
            return pygame.event.Event(e.type, d)
        return e

    # ------------------------------------------------------------------ une image
    def render(self):
        scene = self.scene
        mesh = getattr(scene, "static_mesh", None)
        if mesh is None and hasattr(scene, "geo"):
            mesh = scene.geo.mesh
        if self.static_owner is not scene:
            self.renderer.set_static(mesh)
            self.static_owner = scene
        fr = Frame()
        res = scene.render3d(fr)
        if res:
            cam, env = res
            self.renderer.render(fr, cam, env, self.target)
        else:
            self.renderer.clear(self.target)
        self.ui_surf.fill((0, 0, 0, 0))
        scene.draw_ui(self.ui_surf)
        if self.fade > 0:
            veil = pygame.Surface(self.ui_surf.get_size(), pygame.SRCALPHA)
            veil.fill((0, 0, 0, int(255 * self.fade)))
            self.ui_surf.blit(veil, (0, 0))
        vp = (VIEW.ox, self.screen_size[1] - VIEW.oy - VIEW.h, VIEW.w, VIEW.h)
        self.renderer.present(self.screen, self.screen_size, vp, self.target_tex, self.ui_surf)

    def step(self, dt, events=()):
        for e in events:
            if e.type == pygame.QUIT:
                if hasattr(self.scene, "save"):
                    self.scene.save()
                self.running = False
            elif e.type in (pygame.WINDOWRESIZED, pygame.WINDOWSIZECHANGED, pygame.WINDOWDISPLAYCHANGED):
                self.refresh_view()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif not self.fading_out:
                self.scene.handle_event(self.convert_event(e))
        if self.fading_out:
            self.fade = min(1.0, self.fade + dt * 4)
            if self.fade >= 1.0:
                self.scene = self.next_scene
                self.next_scene = None
                self.fading_out = False
        else:
            self.fade = max(0.0, self.fade - dt * 3)
            self.scene.update(dt)
        self.render()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000, 0.05)
            self.step(dt, pygame.event.get())
            self.window.flip()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
    sys.exit()
