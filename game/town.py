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
   └──────────────── porte sud ─────────────────┘
   La rue du marché sort par la porte est vers la zone d'entraînement (mannequin, cibles, râteliers).
"""
import math

NAME = "Cendreval"
W, H = 60, 46                              # la zone d'entraînement s'étend à l'est des remparts

# ---------------------------------------------------------------- remparts et portes
WALL_X0, WALL_X1, WALL_Y0, WALL_Y1 = 2, 44, 9, 43
GATE_X0, GATE_X1 = 21, 25                  # ouverture des portes nord et sud (colonnes incluses)
EAST_GATE_Y0, EAST_GATE_Y1 = 25, 27        # porte est, au bout de la rue du marché (rangées incluses)

# ---------------------------------------------------------------- tour et portail
TOWER = (23.0, 1.0)                        # centre de Cendrespire (au-delà de l'esplanade)
TOWER_CELLS = {(x, y) for x in range(19, 28) for y in range(0, 3)}
PORTAL = (23.0, 5.4)

# ---------------------------------------------------------------- rues (rectangles de cases, bornes incluses)
STREETS = [
    (21, 2, 25, 45),        # avenue nord-sud, de la tour à la porte sud
    (16, 3, 30, 8),         # esplanade de la tour
    (3, 16, 43, 17),        # rue haute
    (3, 25, 43, 27),        # rue du marché
    (44, 25, 47, 27),       # chemin de la porte est vers la zone d'entraînement
    (3, 35, 43, 36),        # rue basse
    (7, 18, 17, 24),        # place du marché
    (29, 18, 38, 24),       # cour de la forge
    (7, 28, 10, 33),        # cour de la couturière
    (11, 28, 16, 29),       # terrasse de la taverne
]
SQUARE = (23.0, 26.0)
SQUARE_R = 5.5

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
]
TAVERN = (13.5, 31.5)

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
LAMPS = [(20.3, 11.5), (25.7, 11.5), (20.3, 19.5), (25.7, 19.5), (20.3, 33.5), (25.7, 33.5), (20.3, 40.0),
         (25.7, 40.0), (7.0, 24.4), (14.0, 24.4), (32.0, 24.4), (39.0, 24.4), (7.0, 34.4), (14.0, 34.4),
         (32.0, 34.4), (39.0, 34.4), (17.5, 5.0), (28.5, 5.0)]
GARDEN_TREES = [(4.2, 11.0), (9.6, 11.2), (15.0, 11.0), (19.4, 12.0), (26.6, 12.0), (31.0, 11.0), (36.4, 11.2),
                (42.2, 11.0), (4.0, 41.4), (9.5, 41.6), (15.2, 41.2), (19.4, 40.6), (27.0, 41.2), (31.2, 41.6),
                (36.8, 41.4), (42.3, 41.2), (42.3, 26.6), (35.6, 33.4), (29.4, 33.6), (42.0, 33.0)]
CARTS = [(18.4, 34.0, 0.4), (30.6, 17.2, 1.6)]
BENCHES = [(19.2, 26.0, math.pi / 2), (26.8, 26.0, -math.pi / 2)]
BANNERS = [(20.2, 9.6), (25.8, 9.6), (20.2, 42.4), (25.8, 42.4)]

# ---------------------------------------------------------------- zone d'entraînement (hors les murs, à l'est)
TRAINING = (48, 19, 57, 33)                # cour d'entraînement (cases, bornes incluses)
DUMMY = (54.0, 26.0)                       # mannequin immortel
TARGETS = [(56.2, 21.0), (56.2, 31.0)]     # cibles de paille (décor)
RACKS = [(48.7, 20.3), (48.7, 31.7)]       # râteliers d'armes
TRAINING_SIGN = (48.4, 24.3)

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
    dict(id="garde_sud", pos=(20.0, 41.8), facing=math.pi / 2, name="Garde de la porte sud", model="knight",
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
    dict(id="brunhild", pos=(50.6, 23.6), facing=0.4, name="Brunhild la Maîtresse d'armes", model="knight",
         palette={"Blue": (110, 40, 36), "Gold": "hide"},
         line="Frappez ce mannequin autant qu'il vous plaira : lui ne rend jamais les coups. Regardez vos dégâts "
              "par seconde au-dessus de sa tête."),
]
SHOPKEEPERS = {"gorvan": "Gorvan le Marchand", "hilda": "Hilda la Forgeronne", "ysolde": "Ysolde la Couturière"}
NPC_IDS = set(SHOPKEEPERS) | {v["id"] for v in VILLAGERS}
FIREFLIES = [(4, 10, 16, 5), (27, 10, 16, 5), (3, 37, 18, 5), (27, 37, 17, 5)]   # jardins : x, y, largeur, hauteur


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
    return cells


def training_cells():
    x0, y0, x1, y1 = TRAINING
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def walkable_cells():
    """Intérieur des remparts, esplanade, route du sud et zone d'entraînement, moins les maisons, les remparts
    et la tour."""
    inside = {(x, y) for x in range(WALL_X0 + 1, WALL_X1) for y in range(WALL_Y0 + 1, WALL_Y1)}
    return (inside | street_cells() | training_cells()) - house_cells() - rampart_cells() - TOWER_CELLS


def obstacles():
    """Obstacles ronds (x, y, rayon en cases) : fontaine, étals, forge, arbres..."""
    obs = [(*FOUNTAIN, 2.2), (*WELL, 0.6), (*MERCHANT_STALL, 0.8), (*FURNACE, 0.65), (*ANVIL, 0.35),
           (*GRIND, 0.4), (*RACK, 0.4), (*WARDROBE, 0.45), (*MIRROR, 0.35),
           (PORTAL[0] - 1.45, PORTAL[1], 0.35), (PORTAL[0] + 1.45, PORTAL[1], 0.35)]
    obs += [(x, y, 0.65) for x, y, _ in MARKET_STALLS]
    obs += [(x, y, 0.5) for x, y in TAVERN_TABLES]
    obs += [(x, y, 0.3) for x, y in GARDEN_TREES]
    obs += [(x, y, 0.6) for x, y, _ in CARTS]
    obs += [(*DUMMY, 0.45), (*TRAINING_SIGN, 0.25)] + [(x, y, 0.55) for x, y in TARGETS]
    obs += [(x, y, 0.45) for x, y in RACKS]
    return obs
