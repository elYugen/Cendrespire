"""Vérifie le contenu JSON (data/) avant l'empaquetage : code de retour 1 et message si un fichier est invalide."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game import content  # noqa: E402

if content.ERROR is None:
    try:
        import game.talents  # noqa: F401,E402  (valide aussi les arbres de talents)
    except content.ContentError as e:
        content.ERROR = str(e)
if content.ERROR:
    print(content.ERROR)
    sys.exit(1)
print("Contenu valide.")
