"""Zone d'entraînement de Cendreval : mannequin immortel qui ne bouge pas, n'attaque pas et mesure les dégâts."""
import math
import random
from collections import deque

from . import sfx
from .entities import Monster

WINDOW = 5.0        # secondes prises en compte pour les dégâts par seconde


class TrainingDummy(Monster):
    """Ennemi d'entraînement : encaisse tout (World.damage_monster appelle on_hit), ne meurt jamais."""
    immortal = True

    def __init__(self, x, y, facing=math.pi):
        d = dict(id="mannequin", name="Mannequin d'entraînement", hp=1000, dmg=(0, 0), speed=0, radius=16,
                 ai="melee", range=0, cd=99, windup=1, xp=0, floor=1)
        super().__init__(d, x, y, 1)
        self.facing = facing
        self.hits = deque()           # (instant, dégâts)
        self.total = 0.0
        self.wobble = 0.0
        self.now = 0.0

    def update(self, dt, world):
        self.now = world.time
        self.flash = max(0.0, self.flash - dt)
        self.wobble = max(0.0, self.wobble - dt * 2.5)
        self.stun = self.slow = self.burn = self.curse = 0.0
        self.kx = self.ky = 0.0
        while self.hits and self.now - self.hits[0][0] > WINDOW:
            self.hits.popleft()
        if not self.hits:
            self.total = 0.0

    def on_hit(self, world, dmg, crit):
        self.hits.append((world.time, dmg))
        self.total += dmg
        self.hp = self.max_hp
        self.flash = 0.1
        self.wobble = 1.0
        top = self.height() + 8
        world.add_text(self.x, self.y, top, f"{int(dmg)}", (255, 214, 70) if crit else (245, 245, 240),
                       24 if crit else 17)
        world.particles.emit(self.x, self.y, (220, 190, 110), n=6, speed=80, life=0.5, size=3, glow=False,
                             gravity=400, up=140, z=34)
        sfx.play("hit", 0.35)

    def dps(self):
        if not self.hits:
            return 0.0
        span = max(1.0, min(WINDOW, self.now - self.hits[0][0]))
        return sum(d for _t, d in self.hits) / span

    def height(self):
        return 62

    def render(self, fr, t):
        x, y = self.x, self.y
        wood, straw, cloth = (112, 80, 50), (214, 184, 110), (170, 60, 50)
        if self.flash > 0:
            straw = cloth = (255, 255, 255)
        k = self.wobble * math.sin(t * 28) * 3.5         # tremble sous les coups
        fr.box(x, y, 0, 13, 13, 3, (86, 78, 70), mesh="cylinder")
        fr.part("cylinder", (x, y, 22), (3, 0, 0), (0, 0, 22), (0, 3, 0), wood)
        c, s = math.cos(self.facing), math.sin(self.facing)
        fr.part("cylinder", (x + k * c, y + k * s, 38), (10, 0, 0), (k * c * 0.3, k * s * 0.3, 13), (0, 10, 0), straw)
        fr.part("cylinder", (x + k * c, y + k * s, 38), (10.6, 0, 0), (0, 0, 3), (0, 10.6, 0), cloth)
        # bras : une traverse perpendiculaire à la direction du regard
        fr.part("cylinder", (x + k * c, y + k * s, 44), (-s * 17, c * 17, 0), (0, 0, 2.2), (c * 2.2, s * 2.2, 0),
                wood)
        fr.part("sphere", (x + k * c * 1.4, y + k * s * 1.4, 58), (7, 0, 0), (0, 0, 7), (0, 7, 0), straw)
        # cible peinte sur le ventre, côté regard
        for r, col in ((7.5, (230, 225, 210)), (5, cloth), (2.4, (230, 225, 210))):
            fr.part("cylinder", (x + c * 10.2 + k * c, y + s * 10.2 + k * s, 38), (c * 0.4, s * 0.4, 0),
                    (0, 0, r), (-s * r, c * r, 0), col)
        if self.hits:
            fr.decal(x, y, 22, 22, (255, 200, 90), 0.35, kind=1, inner=0.8, rot=t)
