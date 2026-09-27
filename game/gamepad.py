"""Manette (Xbox, PlayStation, Switch Pro... via la base de SDL : boutons nommés comme sur une manette Xbox).

En jeu :
  stick gauche : se déplacer          stick droit : viser (sinon : l'ennemi le plus proche devant soi)
  A : interagir (près d'un habitant, coffre, portail...) sinon attaquer   RT : attaquer (maintenu)
  X · Y · B · RB : sorts 1 à 4        LB : roulade          LT : potion
  croix gauche · haut · droite : artefacts R · T · G      croix bas : carte
  Start : menu (Échap)                Select : carte
Dans les menus (et les écrans titre, création, marchand, forge...) :
  stick gauche ou croix : curseur     A : clic              X : clic droit
  B : retour (Échap)                  LB / RB : page précédente / suivante
Les menus restent pilotés par la souris : la manette déplace le vrai curseur et simule ses clics.
"""
import math

import pygame

try:
    from pygame._sdl2 import controller as sdl_ctrl
except ImportError:             # très vieux pygame : pas de manette
    sdl_ctrl = None

from .settings import VIEW

DEAD = 0.22                     # zone morte des sticks
CURSOR_SPEED = 900              # vitesse du curseur virtuel (unités de conception par seconde)
AIM_RANGE = 220                 # distance du point visé au stick droit (unités du monde)
ASSIST_RANGE = 320              # portée de la visée automatique

B = pygame                      # alias court pour les constantes de boutons
BTN = {"a": B.CONTROLLER_BUTTON_A, "b": B.CONTROLLER_BUTTON_B, "x": B.CONTROLLER_BUTTON_X,
       "y": B.CONTROLLER_BUTTON_Y, "lb": B.CONTROLLER_BUTTON_LEFTSHOULDER, "rb": B.CONTROLLER_BUTTON_RIGHTSHOULDER,
       "start": B.CONTROLLER_BUTTON_START, "back": B.CONTROLLER_BUTTON_BACK,
       "up": B.CONTROLLER_BUTTON_DPAD_UP, "down": B.CONTROLLER_BUTTON_DPAD_DOWN,
       "left": B.CONTROLLER_BUTTON_DPAD_LEFT, "right": B.CONTROLLER_BUTTON_DPAD_RIGHT}
NAME = {v: k for k, v in BTN.items()}


class Pad:
    def __init__(self):
        self.pads = {}              # identifiant d'instance -> manette ouverte
        self.axes = {}              # axe -> valeur (-1..1)
        self.held = set()           # boutons maintenus (noms)
        self.active = False         # dernière entrée venue de la manette (et non du clavier / de la souris)
        self.cursor = None          # curseur virtuel (coordonnées de conception) dans les menus
        self.trig = {"lt": False, "rt": False}

    # ------------------------------------------------------------------ branchement
    def init(self):
        if sdl_ctrl is None:
            return
        try:
            sdl_ctrl.init()
            for i in range(sdl_ctrl.get_count()):
                self.open(i)
        except pygame.error:
            pass

    def open(self, index):
        try:
            if sdl_ctrl.is_controller(index):
                c = sdl_ctrl.Controller(index)
                self.pads[c.as_joystick().get_instance_id()] = c
        except pygame.error:
            pass

    @property
    def connected(self):
        return bool(self.pads)

    # ------------------------------------------------------------------ lecture
    def stick(self, side):
        """Vecteur (x, y) du stick « left » ou « right », zone morte retirée (0 à 1 en norme)."""
        ax = pygame.CONTROLLER_AXIS_LEFTX if side == "left" else pygame.CONTROLLER_AXIS_RIGHTX
        ay = pygame.CONTROLLER_AXIS_LEFTY if side == "left" else pygame.CONTROLLER_AXIS_RIGHTY
        x, y = self.axes.get(ax, 0.0), self.axes.get(ay, 0.0)
        m = math.hypot(x, y)
        if m < DEAD:
            return 0.0, 0.0
        k = min(1.0, (m - DEAD) / (1 - DEAD)) / m
        return x * k, y * k

    def trigger(self, side):
        axis = pygame.CONTROLLER_AXIS_TRIGGERLEFT if side == "lt" else pygame.CONTROLLER_AXIS_TRIGGERRIGHT
        return self.axes.get(axis, 0.0) > 0.5

    # ------------------------------------------------------------------ événements
    def handle(self, e, game):
        """Traite un événement SDL de manette. Renvoie la liste d'événements souris/clavier à transmettre à la
        scène (menus), vide en jeu (la scène lit l'état de la manette elle-même)."""
        t = e.type
        if t == pygame.CONTROLLERDEVICEADDED:
            self.open(e.device_index)
            return []
        if t == pygame.CONTROLLERDEVICEREMOVED:
            self.pads.pop(getattr(e, "instance_id", None), None)
            return []
        if t == pygame.CONTROLLERAXISMOTION:
            self.axes[e.axis] = e.value / 32767.0
            if abs(e.value) > 12000:
                self.active = True
            out = []
            for side in ("lt", "rt"):          # gâchettes : transformées en appuis
                now = self.trigger(side)
                if now != self.trig[side]:
                    self.trig[side] = now
                    if now:
                        out += self.press(side, game)
                    else:
                        self.held.discard(side)
            return out
        if t in (pygame.CONTROLLERBUTTONDOWN, pygame.CONTROLLERBUTTONUP):
            name = NAME.get(e.button)
            if not name:
                return []
            self.active = True
            if t == pygame.CONTROLLERBUTTONDOWN:
                return self.press(name, game)
            self.held.discard(name)
            if in_menu(game) and name in ("a", "x"):
                return [self.mouse_event(pygame.MOUSEBUTTONUP, 1 if name == "a" else 3)]
            return []
        return []

    def press(self, name, game):
        self.held.add(name)
        scene = game.scene
        if in_menu(game):
            if name in ("a", "x"):
                return [self.mouse_event(pygame.MOUSEBUTTONDOWN, 1 if name == "a" else 3)]
            if name in ("b", "start"):
                return [key_event(pygame.K_ESCAPE)]
            if name in ("lb", "rb"):
                return [key_event(pygame.K_TAB, pygame.KMOD_SHIFT if name == "lb" else 0)]
            if name == "back":
                return [key_event(pygame.K_ESCAPE)]
            return []
        world_press(scene, name)
        return []

    def mouse_event(self, etype, button):
        pos = self.cursor or ui_mouse()
        return pygame.event.Event(etype, pos=pos, button=button, touch=False, window=None)

    # ------------------------------------------------------------------ chaque image
    def update(self, dt, game):
        if not self.pads:
            return
        if in_menu(game):
            if self.cursor is None:
                self.cursor = ui_mouse()
            x, y = self.stick("left")
            for name, (dx, dy) in (("left", (-1, 0)), ("right", (1, 0)), ("up", (0, -1)), ("down", (0, 1))):
                if name in self.held:
                    x, y = x + dx * 0.6, y + dy * 0.6
            if x or y:
                from .settings import SCREEN_W, SCREEN_H
                cx, cy = self.cursor or ui_mouse()
                cx = max(0, min(SCREEN_W - 1, cx + x * CURSOR_SPEED * dt))
                cy = max(0, min(SCREEN_H - 1, cy + y * CURSOR_SPEED * dt))
                self.cursor = (cx, cy)
                set_mouse(game, cx, cy)
        else:
            self.cursor = None


def in_menu(game):
    """Écran piloté au curseur : hors du monde, ou dans un menu / une boutique du monde."""
    from .world import World
    s = game.scene
    if not isinstance(s, World):
        return True
    return bool(s.modal or s.left_panel or s.show_inv)


def key_event(key, mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod, scancode=0, unicode="", window=None)


def ui_mouse():
    from . import ui
    return ui.mouse_pos()


def set_mouse(game, x, y):
    if game.window is None:
        return
    px = (x * VIEW.s + VIEW.ox) / VIEW.ratio
    py = (y * VIEW.s + VIEW.oy) / VIEW.ratio
    pygame.mouse.set_pos((px, py))


# =========================================================================== en jeu
def world_press(world, name):
    from . import artifacts, spells
    from .items import ART_SLOTS
    p = world.player
    if p.dead:
        return
    if name == "a":
        obj = world.nearest_interactable()
        PAD.a_attacks = obj is None          # A maintenu attaque seulement s'il n'a pas servi à interagir
        if obj:
            obj.interact(world)
        return
    if name == "lb":
        dx, dy = move_dir(world) or (math.cos(p.facing), math.sin(p.facing))
        p.start_roll(world, dx, dy)
    elif name in ("x", "y", "b", "rb"):
        i = ("x", "y", "b", "rb").index(name)
        if i < len(p.spells):
            spells.cast(world, p.spells[i])
    elif name == "lt":
        p.drink_potion(world)
    elif name in ("left", "up", "right"):
        artifacts.use(world, ART_SLOTS[("left", "up", "right").index(name)])
    elif name in ("down", "back"):
        world.big_map = not world.big_map
    elif name == "start":
        world.open_pause()


def move_dir(world):
    """Direction de déplacement (monde) donnée par le stick gauche, ou None."""
    x, y = PAD.stick("left")
    if not (x or y):
        return None
    dx, dy = world.cam.screen_to_world_dir(x, y)
    m = math.hypot(dx, dy) or 1.0
    return dx / m, dy / m


def aim_point(world):
    """Point visé à la manette : stick droit, sinon l'ennemi le plus proche devant le héros, sinon devant lui."""
    p = world.player
    x, y = PAD.stick("right")
    if x or y:
        dx, dy = world.cam.screen_to_world_dir(x, y)
        m = math.hypot(dx, dy) or 1.0
        return p.x + dx / m * AIM_RANGE, p.y + dy / m * AIM_RANGE
    fx, fy = math.cos(p.facing), math.sin(p.facing)
    best, bs = None, None
    for mo in world.monsters:
        if mo.dead or not mo.targetable:
            continue
        vx, vy = mo.x - p.x, mo.y - p.y
        d = math.hypot(vx, vy)
        if d > ASSIST_RANGE or d < 1 or not world.los(p.x, p.y, mo.x, mo.y):
            continue
        facing_k = (vx * fx + vy * fy) / d          # 1 : droit devant, -1 : derrière
        score = d * (1.6 - facing_k)
        if bs is None or score < bs:
            best, bs = mo, score
    if best:
        return best.x, best.y
    return p.x + fx * AIM_RANGE * 0.6, p.y + fy * AIM_RANGE * 0.6


def attack_held():
    return "rt" in PAD.held or ("a" in PAD.held and PAD.a_attacks)


PAD = Pad()
PAD.a_attacks = False           # A maintenu attaque seulement quand il n'a pas servi à interagir
