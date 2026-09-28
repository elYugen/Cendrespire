"""Sceau du gardien : la condition à remplir sur un étage pour ouvrir la salle du boss.

Chaque étage (sauf le premier et les étages BOSS) tire une condition au hasard :
  kills     : éliminer un nombre de créatures (le sceau d'origine)
  shards    : retrouver les fragments du sceau dispersés dans l'étage
  elites    : abattre des champions (monstres d'élite)
  braziers  : allumer des brasiers ; chacun réveille une embuscade
  keeper    : traquer le Geôlier du sceau, puis ramasser la clé qu'il laisse tomber
TowerScene.seal_count() donne l'avancement, seal_needed le total. La condition n'est jamais annoncée au joueur :
il la découvre en explorant (seule la jauge du sceau, près de la minicarte, montre qu'il avance).
"""
import math

from . import sfx
from .entities import Interactable, Monster
from .fx import RingFX
from .settings import TILE

WEIGHTS = {"kills": 3, "shards": 3, "elites": 2, "braziers": 2, "keeper": 2}
SHARD_COL = (150, 220, 255)
FIRE_COL = (255, 150, 60)
KEY_COL = (255, 210, 90)


def pick(rng, floor):
    """Condition d'un étage : toujours le massacre au premier étage (découverte du jeu)."""
    if floor <= 1:
        return "kills"
    kinds = list(WEIGHTS)
    return rng.choices(kinds, weights=[WEIGHTS[k] for k in kinds])[0]


def far_rooms(world, n):
    """Salles éloignées de l'entrée (ni l'entrée, ni l'arène), réparties dans l'étage."""
    d = world.dungeon
    sx, sy = d.start_room.center
    rooms = [r for r in d.rooms if r is not d.start_room and r is not d.boss_room]
    rooms.sort(key=lambda r: -math.dist(r.center, (sx, sy)))
    pool = rooms[:max(n * 3, 6)]
    return world.rng.sample(pool, min(n, len(pool)))


# =========================================================================== objets de quête d'étage
class SealShard(Interactable):
    """Fragment du sceau : cristal flottant à ramasser."""
    prompt = "Ramasser le fragment du sceau"
    radius = 80
    map_color = SHARD_COL

    def __init__(self, x, y):
        super().__init__(x, y)
        self.taken = False

    def can_interact(self, world):
        return not self.taken

    def interact(self, world):
        self.taken = True
        world.interactables.remove(self)
        world.seal_have += 1
        world.particles.emit(self.x, self.y, SHARD_COL, n=30, speed=150, life=0.6, size=4, up=120, z=30)
        world.effects.append(RingFX(self.x, self.y, 10, 90, 0.4, SHARD_COL, 5))
        world.message("Le fragment vibre entre vos mains : quelque chose se fissure au loin...", SHARD_COL, 4)
        sfx.play("seal", 0.5)

    def render(self, fr, t):
        z = 34 + 5 * math.sin(t * 2 + self.x)
        a = t * 1.5
        c, s = math.cos(a) * 7, math.sin(a) * 7
        fr.part("cone", (self.x, self.y, z), (c, s, 0), (0, 0, 16), (-s, c, 0), SHARD_COL, 0.8)
        fr.part("cone", (self.x, self.y, z), (c, s, 0), (0, 0, -12), (-s, c, 0), SHARD_COL, 0.8)
        fr.glow(self.x, self.y, z, 46, SHARD_COL, 0.8)
        fr.light(self.x, self.y, 40, 190, SHARD_COL, 1.0)
        fr.decal(self.x, self.y, 30, 30, SHARD_COL, 0.35, kind=1, inner=0.8, rot=t)


class Brazier(Interactable):
    """Brasier éteint : l'allumer fait avancer le sceau et réveille une embuscade."""
    prompt = "Allumer le brasier"
    radius = 80
    map_color = FIRE_COL

    def __init__(self, x, y, room):
        super().__init__(x, y)
        self.room = room
        self.lit = False

    def can_interact(self, world):
        return not self.lit

    def interact(self, world):
        self.lit = True
        world.seal_have += 1
        world.flash_light(self.x, self.y, 300, FIRE_COL, 0.5)
        world.particles.emit(self.x, self.y, FIRE_COL, n=40, speed=160, life=0.7, size=4, up=200, z=40)
        sfx.play("fire", 0.8)
        world.message("Le brasier s'embrase : des créatures surgissent !",
                      FIRE_COL, 4)
        world.ambush(self.x, self.y, self.room)

    def render(self, fr, t):
        fr.box(self.x, self.y, 0, 12, 12, 10, (70, 64, 60), mesh="cylinder")
        fr.box(self.x, self.y, 10, 16, 16, 5, (96, 84, 70), mesh="cylinder")
        if self.lit:
            k = 1 + 0.15 * math.sin(t * 9 + self.x)
            fr.glow(self.x, self.y, 30, 34 * k, FIRE_COL, 0.95)
            fr.glow(self.x, self.y, 40, 20 * k, (255, 230, 150), 0.9)
            fr.light(self.x, self.y, 50, 260 * k, FIRE_COL, 1.4)
        else:
            fr.decal(self.x, self.y, 26, 26, FIRE_COL, 0.2 + 0.1 * math.sin(t * 3), kind=1, inner=0.8)


class SealKey(Interactable):
    """Clé du sceau, lâchée par le Geôlier."""
    prompt = "Ramasser la clé du sceau"
    radius = 80
    map_color = KEY_COL

    def interact(self, world):
        world.interactables.remove(self)
        world.seal_have = 1
        world.message("Clé du sceau récupérée !", KEY_COL, 4)
        sfx.play("pickup")

    def render(self, fr, t):
        z = 26 + 4 * math.sin(t * 3)
        a = t * 2
        c, s = math.cos(a), math.sin(a)
        fr.part("cylinder", (self.x, self.y, z), (c * 2, s * 2, 0), (0, 0, 9), (-s * 2, c * 2, 0), KEY_COL, 0.7)
        fr.part("sphere", (self.x, self.y, z + 12), (5, 0, 0), (0, 0, 5), (0, 5, 0), KEY_COL, 0.7)
        fr.glow(self.x, self.y, z, 40, KEY_COL, 0.8)
        fr.light(self.x, self.y, 30, 160, KEY_COL, 1.0)


def make_keeper(world, room, floor):
    """Le Geôlier du sceau : un champion plus coriace, qui lâche la clé en mourant."""
    from .data import ELITE_AFFIXES, MONSTERS
    pool = [mid for mid, m in MONSTERS.items() if m["floor"] <= floor and m["ai"] in ("melee", "brute")]
    mid = world.rng.choice(pool or list(MONSTERS))
    x, y = world.random_point(room, MONSTERS[mid]["radius"] + 12)
    m = Monster(mid, x, y, floor, world.rng.choice(list(ELITE_AFFIXES)))
    m.max_hp *= 1.6
    m.hp = m.max_hp
    m.name = "Geôlier du sceau"
    m.keeper = True
    return m
