"""Apparence des héros : options de personnalisation et construction de la spécification du modèle 3D.

L'apparence est enregistrée dans la sauvegarde sous forme d'indices (data["look"]) ; hero_spec() la combine
avec la tenue de la classe (casque cornu, chapeau de mage, capuche...) pour produire la spec du modèle détaillé.
"""
import random

from .data import CLASSES

SKINS = [("Porcelaine", (240, 206, 176)), ("Clair", (228, 186, 150)), ("Hâlé", (212, 162, 118)),
         ("Ambré", (178, 124, 84)), ("Brun", (132, 88, 58)), ("Ébène", (92, 62, 44)), ("Cendré", (150, 156, 164))]
HAIR_STYLES = ["Rasé", "Court", "Long", "Queue de cheval", "Crête", "Tresses"]
HAIR_COLORS = [("Noir", (38, 32, 30)), ("Brun", (92, 58, 36)), ("Châtain", (140, 96, 58)), ("Roux", (176, 82, 38)),
               ("Blond", (226, 194, 120)), ("Blanc", (230, 230, 232)), ("Gris", (138, 138, 144)),
               ("Bleu nuit", (54, 64, 120)), ("Pourpre", (122, 50, 112))]
BEARDS = ["Aucune", "Courte", "Longue", "Moustache"]
EYES = [("Bleu", (70, 130, 210)), ("Vert", (70, 160, 80)), ("Brun", (104, 66, 38)), ("Gris", (140, 150, 162)),
        ("Ambre", (214, 150, 40)), ("Violet", (160, 100, 220)), ("Braise", (240, 80, 40))]
OUTFITS = [("Cuir", (128, 82, 52)), ("Terre", (86, 62, 44)), ("Azur", (64, 72, 176)), ("Indigo", (54, 60, 156)),
           ("Forêt", (72, 104, 60)), ("Mousse", (60, 88, 48)), ("Pourpre", (112, 44, 110)),
           ("Écarlate", (150, 40, 40)), ("Ardoise", (70, 76, 86)), ("Ivoire", (214, 204, 178)), ("Ocre", (190, 140, 60)),
           ("Sarcelle", (40, 120, 120)), ("Charbon", (40, 38, 42)), ("Rose", (190, 110, 130))]
BUILDS = [("Svelte", 0.88), ("Normale", 1.0), ("Robuste", 1.14)]
MARKS = ["Aucune", "Peinture de guerre", "Cicatrice", "Tatouage runique"]
HEADGEAR = ["Masqué", "Visible"]
HEADGEAR_NAMES = {cid: c.get("headgear_name", "Couvre-chef") for cid, c in CLASSES.items()}

# (clé, libellé, liste de valeurs) : ordre d'affichage de l'éditeur
OPTIONS = [
    ("skin", "Teint", SKINS), ("build", "Carrure", BUILDS), ("hair", "Coiffure", HAIR_STYLES),
    ("hair_col", "Cheveux", HAIR_COLORS), ("beard", "Barbe", BEARDS), ("eyes", "Yeux", EYES),
    ("marks", "Marques", MARKS), ("main", "Tenue", OUTFITS), ("second", "Tenue (2de)", OUTFITS),
    ("headgear", "Couvre-chef", HEADGEAR),
]

_BASE_LOOK = dict(skin=1, build=1, hair=1, hair_col=1, beard=0, eyes=0, marks=0, main=0, second=1, headgear=1)
DEFAULTS = {cid: dict(_BASE_LOOK, **c.get("look_defaults", {})) for cid, c in CLASSES.items()}


def default_look(cls_id):
    return dict(DEFAULTS[cls_id])


def random_look(cls_id, rng=random):
    look = {key: rng.randrange(len(values)) for key, _, values in OPTIONS}
    look["headgear"] = 1
    return look


def clean_look(look, cls_id):
    """Complète / borne une apparence lue dans une sauvegarde."""
    res = default_look(cls_id)
    for key, _, values in OPTIONS:
        v = (look or {}).get(key, res[key])
        res[key] = v % len(values) if isinstance(v, int) else res[key]
    return res


def value_name(key, idx):
    values = dict((k, v) for k, _, v in OPTIONS)[key]
    v = values[idx]
    return v[0] if isinstance(v, tuple) else v


def value_color(key, idx):
    values = dict((k, v) for k, _, v in OPTIONS)[key]
    v = values[idx]
    return v[1] if isinstance(v, tuple) and isinstance(v[1], tuple) else None


def _resolve(v, main, second, skin):
    """Dans classes.json, "main" / "second" = couleurs de tenue choisies, "skin" = teint ; sinon valeur telle quelle."""
    if v == "main":
        return main
    if v == "second":
        return second
    if isinstance(v, list):
        return tuple(v)
    return v


def hero_spec(cls_id, look):
    """Spécification du modèle détaillé : tenue de la classe (classes.json « model » / « headgear ») + apparence."""
    look = clean_look(look, cls_id)
    cl = CLASSES[cls_id]
    main, second = OUTFITS[look["main"]][1], OUTFITS[look["second"]][1]
    hair = HAIR_COLORS[look["hair_col"]][1]
    spec = dict(detailed=True, skin=SKINS[look["skin"]][1], build=BUILDS[look["build"]][1],
                hair_style=HAIR_STYLES[look["hair"]], hair=hair, beard_style=BEARDS[look["beard"]], beard=hair,
                eye_col=EYES[look["eyes"]][1], marks=MARKS[look["marks"]])
    for k, v in cl["model"].items():
        if k == "arms":
            spec[k] = v      # "skin" / "body" : bras nus ou couverts
        else:
            spec[k] = _resolve(v, main, second, spec["skin"])
    if look["headgear"]:
        for k, v in cl.get("headgear", {}).items():
            spec[k] = _resolve(v, main, second, spec["skin"])
    return spec


def spec_for_save(data):
    return hero_spec(data["cls"], data.get("look"))
