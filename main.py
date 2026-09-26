"""Tour des Tourments — point d'entrée.

Lancement :  python main.py
"""
import sys

import pygame

from game import sfx
from game.settings import SCREEN_W, SCREEN_H, FPS, TITLE


class Game:
    def __init__(self):
        pygame.init()
        sfx.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED | pygame.RESIZABLE)
        pygame.display.set_caption(TITLE)
        pygame.key.start_text_input()
        self.clock = pygame.time.Clock()
        self.running = True
        self.next_scene = None
        self.fade = 1.0
        self.fading_out = False
        from game.scenes import TitleScene
        self.scene = TitleScene(self)

    def change_scene(self, scene):
        self.next_scene = scene
        self.fading_out = True

    def quit(self):
        self.running = False

    def run(self):
        veil = pygame.Surface((SCREEN_W, SCREEN_H))
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000, 0.05)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    if hasattr(self.scene, "save"):
                        self.scene.save()
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif not self.fading_out:
                    self.scene.handle_event(e)
            if self.fading_out:
                self.fade = min(1.0, self.fade + dt * 4)
                if self.fade >= 1.0:
                    self.scene = self.next_scene
                    self.next_scene = None
                    self.fading_out = False
            else:
                self.fade = max(0.0, self.fade - dt * 3)
                self.scene.update(dt)
            self.scene.draw(self.screen)
            if self.fade > 0:
                veil.set_alpha(int(255 * self.fade))
                self.screen.blit(veil, (0, 0))
            pygame.display.flip()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
    sys.exit()
