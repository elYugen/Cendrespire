"""Cendreval, la ville au pied de la tour : plan complet (rues, bâtiments, échoppes, PNJ, décor).

Tout est en cases (1 case = 40 unités logiques), x vers l'est, y vers le sud. Ce plan est la seule source :
dungeon.build_hub() en tire la grille praticable, r3d/city.py le décor 3D et hub.py les personnages.

        forêt           [ tour ]            forêt
                     esplanade + portail
   ┌──────────────── porte nord ────────────────┐   remparts
   │ maisons            avenue          maisons  │
   │══════════════ rue haute ════════════════════│
   │ marché / Gorvan     puits  │   forge / Hilda │
   │════════ rue du marché ═(fontaine)═══════════│
   │ couturière  taverne        │   maisons       │
   │══════════════ rue basse ════════════════════│
   │ maisons            avenue           maisons  │
   │═════════════ rue du Temple ═════════════════│
   │ sanctuaire │ cour   (place des    cour │ bibliothèque
   │ de l'Oubli │        Oracles)          │ (Théodric)
   │════════════ rue des Remparts ═══════════════│
   │ maisons            avenue           maisons  │
   └──────────────── porte sud ─────────────────┘
   La rue du marché sort par la porte est vers la zone d'entraînement (mannequin, cibles, râteliers).
   Au sud de la porte sud, l'avenue mène à l'arène (futur mode joueur contre joueur).
"""
import math

NAME = "Cendreval"
W, H = 60, 80                              # zone d'entraînement à l'est des remparts, arène au sud

# ---------------------------------------------------------------- remparts et portes
WALL_X0, WALL_X1, WALL_Y0, WALL_Y1 = 2, 44, 9, 59
GATE_X0, GATE_X1 = 21, 25                  # ouverture des portes nord et sud (colonnes incluses)
EAST_GATE_Y0, EAST_GATE_Y1 = 25, 27        # porte est, au bout de la rue du marché (rangées incluses)

# ---------------------------------------------------------------- tour et portail
TOWER = (23.0, 1.0)                        # centre de Cendrespire (au-delà de l'esplanade)
TOWER_CELLS = {(x, y) for x in range(19, 28) for y in range(0, 3)}
PORTAL = (23.0, 5.4)

# ---------------------------------------------------------------- rues (rectangles de cases, bornes incluses)
STREETS = [
    (21, 2, 25, 65),        # avenue nord-sud, de la tour à l'entrée de l'arène
    (16, 3, 30, 8),         # esplanade de la tour
    (3, 16, 43, 17),        # rue haute
    (3, 25, 43, 27),        # rue du marché
    (44, 25, 47, 27),       # chemin de la porte est vers la zone d'entraînement
    (3, 35, 43, 36),        # rue basse
    (7, 18, 17, 24),        # place du marché
    (29, 18, 38, 24),       # cour de la forge
    (7, 28, 10, 33),        # cour de la couturière
    (11, 28, 16, 29),       # terrasse de la taverne
    # quartier du Temple (au sud de l'ancienne enceinte)
    (3, 44, 43, 45),        # rue du Temple
    (3, 54, 43, 55),        # rue des Remparts
    (10, 46, 16, 53),       # cour du sanctuaire de l'Oubli
    (30, 46, 35, 53),       # cour de la bibliothèque
]
SQUARE = (23.0, 26.0)
SQUARE_R = 5.5
ORACLES = (23.0, 49.5)                     # place des Oracles et sa statue
ORACLES_R = 4.3

# ---------------------------------------------------------------- bâtiments
# (x, y, modules de 2 cases, étages, orientation, toit) — orientation = direction de la façade :
# 0 sud, pi nord, pi/2 est, -pi/2 ouest
RED, TEAL, SLATE, OCHRE, GREEN = (0.62, 0.24, 0.2), (0.30, 0.50, 0.46), (0.34, 0.36, 0.44), (0.66, 0.46, 0.2), \
    (0.34, 0.46, 0.26)
S, N_, E, O = 0.0, math.pi, math.pi / 2, -math.pi / 2
HOUSES = [
    # quartier nord-ouest et nord-est (façade sur la rue haute)
    (6.5, 14.0, 2, 2, S, RED), (12.5, 14.0, 2, 1, S, TEAL), (17.5, 14.0, 1, 2, S, SLATE),
    (28.5, 14.0, 1, 2, S, OCHRE), (33.5, 14.0, 2, 1, S, RED), (39.5, 14.0, 2, 2, S, TEAL),
    # boutiques
    (4.9, 21.0, 2, 2, E, OCHRE),        # maison du marchand
    (41.1, 21.0, 2, 1, O, SLATE),       # forge
    (4.9, 30.5, 2, 1, E, GREEN),        # atelier de la couturière
    (13.5, 31.5, 2, 2, N_, RED),        # taverne « Le Tison »
    # quartier sud-est (façade sur la rue du marché)
    (32.5, 30.0, 2, 1, N_, SLATE), (38.5, 30.0, 2, 2, N_, TEAL),
    # quartier sud (façade sur la rue basse)
    (6.5, 38.5, 2, 1, N_, TEAL), (12.5, 38.5, 2, 2, N_, SLATE), (17.5, 38.5, 1, 1, N_, OCHRE),
    (28.5, 38.5, 1, 1, N_, RED), (33.5, 38.5, 2, 2, N_, GREEN), (39.5, 38.5, 2, 1, N_, OCHRE),
    # quartier du Temple
    (8.0, 50.0, 2, 2, E, GREEN),        # sanctuaire de l'Oubli (Oriane)
    (38.0, 50.0, 2, 2, O, SLATE),       # bibliothèque (Théodric)
    (6.5, 57.4, 2, 1, N_, RED), (12.5, 57.4, 2, 2, N_, TEAL), (17.5, 57.4, 1, 1, N_, OCHRE),
    (28.5, 57.4, 1, 2, N_, SLATE), (33.5, 57.4, 2, 1, N_, GREEN), (39.5, 57.4, 2, 2, N_, RED),
]
TAVERN = (13.5, 31.5)
SANCTUARY = (8.0, 50.0)
LIBRARY = (38.0, 50.0)

# ---------------------------------------------------------------- lieux et mobilier
FOUNTAIN = SQUARE
WELL = (18.6, 21.4)
MERCHANT_STALL = (9.8, 21.2)
MARKET_STALLS = [(11.8, 19.2, 0.2), (11.8, 23.4, -0.2), (15.2, 19.2, 3.0), (15.2, 23.4, -3.0)]
FURNACE = (37.4, 19.3)
ANVIL = (34.6, 21.4)
GRIND = (36.2, 23.4)
RACK = (38.4, 22.8)
WARDROBE = (7.7, 29.1)
MIRROR = (9.5, 29.0)
TAVERN_TABLES = [(12.2, 28.7), (15.4, 28.7)]
STASH = (16.5, 28.8)                       # coffre de stockage, au bout de la terrasse de la taverne
LAMPS = [(20.3, 11.5), (25.7, 11.5), (20.3, 19.5), (25.7, 19.5), (20.3, 33.5), (25.7, 33.5), (20.3, 40.0),
         (25.7, 40.0), (7.0, 24.4), (14.0, 24.4), (32.0, 24.4), (39.0, 24.4), (7.0, 34.4), (14.0, 34.4),
         (32.0, 34.4), (39.0, 34.4), (17.5, 5.0), (28.5, 5.0),
         (20.3, 46.2), (25.7, 46.2), (20.3, 53.0), (25.7, 53.0), (14.0, 46.2), (32.0, 46.2), (14.0, 53.6),
         (32.0, 53.6), (7.0, 53.6), (39.0, 53.6), (7.0, 46.0), (39.0, 46.0)]
GARDEN_TREES = [(4.2, 11.0), (9.6, 11.2), (15.0, 11.0), (19.4, 12.0), (26.6, 12.0), (31.0, 11.0), (36.4, 11.2),
                (42.2, 11.0), (4.0, 41.4), (9.5, 41.6), (15.2, 41.2), (19.4, 40.6), (27.0, 41.2), (31.2, 41.6),
                (36.8, 41.4), (42.3, 41.2), (42.3, 26.6), (35.6, 33.4), (29.4, 33.6), (42.0, 33.0),
                (18.0, 47.0), (28.0, 47.0), (18.0, 52.4), (28.0, 52.4), (3.8, 46.4), (42.3, 46.4), (3.8, 53.0),
                (42.3, 53.0)]
CARTS = [(18.4, 34.0, 0.4), (30.6, 17.2, 1.6), (15.6, 55.0, 1.4)]
BENCHES = [(19.2, 26.0, math.pi / 2), (26.8, 26.0, -math.pi / 2), (19.9, 49.5, math.pi / 2),
           (26.1, 49.5, -math.pi / 2)]
BANNERS = [(20.2, 9.6), (25.8, 9.6), (20.2, 58.4), (25.8, 58.4), (10.4, 47.6), (10.4, 52.4), (35.6, 47.6),
           (35.6, 52.4)]
LECTERNS = [(33.0, 48.0), (33.0, 52.0)]    # pupitres de la bibliothèque
CANDLES = [(12.2, 48.0), (12.2, 52.0)]     # chandeliers du sanctuaire

# ---------------------------------------------------------------- zone d'entraînement (hors les murs, à l'est)
TRAINING = (48, 19, 57, 33)                # cour d'entraînement (cases, bornes incluses)
DUMMY = (54.0, 26.0)                       # mannequin immortel
TARGETS = [(56.2, 21.0), (56.2, 31.0)]     # cibles de paille (décor)
RACKS = [(48.7, 20.3), (48.7, 31.7)]       # râteliers d'armes
TRAINING_SIGN = (48.4, 24.3)

# ---------------------------------------------------------------- arène (au sud de la porte sud)
ARENA = (23.0, 71.0)                       # centre de la piste de sable
ARENA_R = 6.3                              # rayon de la piste (cases)
ARENA_GATE = 0.85                          # demi-ouverture de l'entrée nord (radians), dans l'axe de l'avenue
ARENA_BRAZIERS = [(ARENA[0] + 5.6 * math.cos(a), ARENA[1] + 5.6 * math.sin(a)) for a in (0.35, 1.2, 1.95, 2.8)]

# ---------------------------------------------------------------- personnages
SPAWN = (23.0, 32.3)
MERCHANT = (11.0, 21.2, 0.0)               # devant son étal, face à la place (et non plus caché derrière)
SMITH = (33.7, 21.4, 0.0)
TAILOR = (9.2, 31.0, -math.pi / 2)
# habitants : id (quêtes), position et orientation de départ, nom, modèle animé, palette, réplique et, pour ceux
# qui se promènent, tournée (cases parcourues en boucle, sans traverser les obstacles de obstacles())
VILLAGERS = [
    dict(id="elise", pos=(13.8, 28.6), facing=1.2, name="Élise l'Aubergiste", model="farmer",
         palette={"LightBlue": (150, 110, 80), "Red": (190, 170, 130)},
         line="Bienvenue au Tison ! La soupe est chaude, la bière est fraîche.",
         route=[(13.8, 28.6), (13.8, 26.3), (17.6, 26.4), (10.2, 26.2)]),
    dict(id="anselme", pos=(26.9, 29.3), facing=2.4, name="Frère Anselme", model="hooded",
         palette={"Black": (90, 70, 50), "LightBrown": (180, 160, 120)},
         line="Que la lumière vous garde dans les étages obscurs de la tour.",
         route=[(26.9, 29.3), (23.0, 30.4), (19.9, 29.1), (19.6, 22.4), (23.0, 21.2), (26.4, 22.4)]),
    dict(id="garde_sud", pos=(20.0, 57.8), facing=math.pi / 2, name="Garde de la porte sud", model="knight",
         palette={"Blue": (50, 70, 130), "Gold": "hide"},
         line="Personne n'est jamais revenu du sommet. Pas encore."),
    dict(id="garde_nord", pos=(20.0, 10.6), facing=-math.pi / 2, name="Garde de la porte nord", model="knight",
         palette={"Blue": (120, 36, 40), "Gold": "hide"},
         line="Au-delà de cette porte : Cendrespire. Bonne chance, aventurier."),
    dict(id="mira", pos=(18.2, 25.2), facing=0.3, name="Mira la Fileuse", model="witch",
         palette={"Purple": (60, 110, 90), "Gold": (220, 200, 140)},
         line="Ysolde, près de la rue du marché, coud des merveilles.",
         route=[(18.2, 25.2), (16.8, 22.8), (13.5, 21.3), (13.5, 16.6), (18.0, 16.6), (17.0, 20.5)]),
    dict(id="aldebert", pos=(30.2, 25.6), facing=3.0, name="Maître Aldebert", model="knight",
         palette={"Blue": (90, 70, 40), "Gold": "hide"},
         line="On dit qu'au sommet de Cendrespire brûle une flamme éternelle.",
         route=[(30.2, 25.6), (35.5, 26.2), (40.2, 26.0), (35.5, 25.8)]),
    dict(id="garde_ronde", pos=(8.0, 16.1), facing=0.0, name="Sergent Bréval", model="knight",
         palette={"Blue": (70, 80, 60), "Gold": "hide"},
         line="Je fais ma ronde, jour et nuit. Rien ne sort de la tour sans que je le voie.",
         route=[(8.0, 16.1), (38.0, 16.1)]),
    dict(id="varek", pos=(20.4, 65.6), facing=0.9, name="Varek le Maître de l'arène", model="knight",
         palette={"Blue": (60, 60, 64), "Gold": (200, 160, 70)},
         line="Bientôt, les aventuriers de Cendreval s'affronteront ici même. Entraînez-vous : l'arène n'aime "
              "pas les faibles."),
    dict(id="brunhild", pos=(50.6, 23.6), facing=0.4, name="Brunhild la Maîtresse d'armes", model="knight",
         palette={"Blue": (110, 40, 36), "Gold": "hide"},
         line="Frappez ce mannequin autant qu'il vous plaira : lui ne rend jamais les coups. Regardez vos dégâts "
              "par seconde au-dessus de sa tête."),
    # quartier du Temple
    dict(id="maelle", pos=(26.6, 51.8), facing=2.4, name="Sœur Maëlle", model="hooded",
         palette={"Black": (200, 196, 180), "LightBrown": (150, 120, 60)},
         line="La statue des Oracles veille sur Cendreval depuis mille ans. Elle a vu partir bien des grimpeurs.",
         route=[(26.6, 51.8), (26.6, 47.2), (19.4, 47.2), (19.4, 51.8)]),
    dict(id="roderic", pos=(26.4, 56.6), facing=-math.pi / 2, name="Capitaine Roderic", model="knight",
         palette={"Blue": (40, 60, 100), "Gold": (200, 170, 80)},
         line="La garde manque de bras. Si vous cherchez du travail honnête, parlez-moi."),
    dict(id="pip", pos=(8.0, 44.5), facing=0.0, name="Pip le Gamin", model="farmer",
         palette={"LightBlue": (90, 130, 60), "Red": (170, 120, 70)},
         line="Hé ! Vous avez vu la bibliothèque ? Théodric dit que les livres parlent, la nuit !",
         route=[(8.0, 44.5), (38.0, 44.5)]),
]
SHOPKEEPERS = {"gorvan": "Gorvan le Marchand", "hilda": "Hilda la Forgeronne", "ysolde": "Ysolde la Couturière",
               "oriane": "Oriane, Gardienne de l'Oubli", "theodric": "Théodric l'Érudit"}
GREETINGS = {                              # saluts des commerçants quand le héros approche
    "gorvan": "Approchez ! Lames, armures, babioles : tout se vend, tout s'achète.",
    "hilda": "Une arme émoussée ? Posez-la sur l'enclume.",
    "ysolde": "Oh, cette tenue... Laissez-moi arranger ça.",
    "oriane": "Tout peut s'oublier, voyageur. Même ce que l'on croyait être.",
    "theodric": "Chut... Les livres n'aiment pas le bruit.",
}
ORIANE = (11.4, 50.0, 0.0)                 # devant le sanctuaire, face à sa cour
THEODRIC = (34.6, 50.0, math.pi)           # devant la bibliothèque
NPC_IDS = set(SHOPKEEPERS) | {v["id"] for v in VILLAGERS}
FIREFLIES = [(4, 10, 16, 5), (27, 10, 16, 5), (3, 37, 18, 5), (27, 37, 17, 5), (3, 46, 4, 8), (40, 46, 4, 8)]   # jardins : x, y, largeur, hauteur


# ---------------------------------------------------------------- géométrie dérivée
def house_cells():
    """Cases occupées par les maisons (murs : on ne les traverse pas)."""
    cells = set()
    for x, y, n, _fl, rot, _roof in HOUSES:
        hl, hw = n + 0.1, 1.1
        if abs(math.sin(rot)) > 0.5:
            hl, hw = hw, hl
        for tx in range(int(x - hl), int(x + hl - 1e-6) + 1):
            for ty in range(int(y - hw), int(y + hw - 1e-6) + 1):
                cells.add((tx, ty))
    return cells


def rampart_cells():
    cells = set()
    for x in range(WALL_X0, WALL_X1 + 1):
        for y in (WALL_Y0, WALL_Y1):
            if not GATE_X0 <= x <= GATE_X1:
                cells.add((x, y))
    for y in range(WALL_Y0, WALL_Y1 + 1):
        cells.add((WALL_X0, y))
        if not EAST_GATE_Y0 <= y <= EAST_GATE_Y1:
            cells.add((WALL_X1, y))
    return cells


def street_cells():
    cells = set()
    for x0, y0, x1, y1 in STREETS:
        cells |= {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    cx, cy = SQUARE
    cells |= {(x, y) for x in range(W) for y in range(H) if math.hypot(x + 0.5 - cx, y + 0.5 - cy) < SQUARE_R}
    ox, oy = ORACLES
    cells |= {(x, y) for x in range(W) for y in range(H) if math.hypot(x + 0.5 - ox, y + 0.5 - oy) < ORACLES_R}
    return cells


def arena_cells():
    cx, cy = ARENA
    return {(x, y) for x in range(W) for y in range(H) if math.hypot(x + 0.5 - cx, y + 0.5 - cy) < ARENA_R}


def arena_ring_cells():
    """Couronne des gradins autour de la piste : sol dégagé (ni talus ni arbres) où sont posés les gradins."""
    cx, cy = ARENA
    return {(x, y) for x in range(W) for y in range(H)
            if ARENA_R <= math.hypot(x + 0.5 - cx, y + 0.5 - cy) < ARENA_R + 3.6}


def training_cells():
    x0, y0, x1, y1 = TRAINING
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def walkable_cells():
    """Intérieur des remparts, esplanade, route du sud et zone d'entraînement, moins les maisons, les remparts
    et la tour."""
    inside = {(x, y) for x in range(WALL_X0 + 1, WALL_X1) for y in range(WALL_Y0 + 1, WALL_Y1)}
    return ((inside | street_cells() | training_cells() | arena_cells()) - house_cells() - rampart_cells()
            - TOWER_CELLS)


def obstacles():
    """Obstacles ronds (x, y, rayon en cases) : fontaine, étals, forge, arbres..."""
    obs = [(*FOUNTAIN, 2.2), (*WELL, 0.6), (*MERCHANT_STALL, 0.8), (*FURNACE, 0.65), (*ANVIL, 0.35),
           (*GRIND, 0.4), (*RACK, 0.4), (*WARDROBE, 0.45), (*MIRROR, 0.35),
           (PORTAL[0] - 1.45, PORTAL[1], 0.35), (PORTAL[0] + 1.45, PORTAL[1], 0.35)]
    obs += [(x, y, 0.65) for x, y, _ in MARKET_STALLS]
    obs += [(x, y, 0.5) for x, y in TAVERN_TABLES] + [(*STASH, 0.45)]
    obs += [(*ORACLES, 1.1)] + [(x, y, 0.35) for x, y in LECTERNS + CANDLES]
    obs += [(x, y, 0.3) for x, y in GARDEN_TREES]
    obs += [(x, y, 0.6) for x, y, _ in CARTS]
    obs += [(*DUMMY, 0.45), (*TRAINING_SIGN, 0.25)] + [(x, y, 0.55) for x, y in TARGETS]
    obs += [(x, y, 0.45) for x, y in RACKS]
    obs += [(x, y, 0.4) for x, y in ARENA_BRAZIERS if math.hypot(x - ARENA[0], y - ARENA[1]) < ARENA_R]
    return obs
