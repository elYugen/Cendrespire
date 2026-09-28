"""Monnaie : cuivre, argent et or. 100 cuivre = 1 argent, 100 argent = 1 or.

Toutes les sommes du jeu (bourse du héros, prix, butin, récompenses) sont stockées en pièces de cuivre ;
on ne les découpe en or, argent et cuivre qu'à l'affichage.
"""
SILVER = 100                  # cuivre par pièce d'argent
GOLD = SILVER * 100           # cuivre par pièce d'or
OLD_GOLD = 10                 # anciennes sauvegardes (une seule monnaie) : 1 ancienne pièce d'or = 10 cuivre

# (nom, valeur en cuivre, couleur de la pièce)
COINS = (("or", GOLD, (240, 196, 70)), ("argent", SILVER, (206, 212, 222)), ("cuivre", 1, (206, 124, 72)))


def split(amount):
    """[(nom, nombre, couleur)] des pièces non nulles, de la plus grosse à la plus petite (cuivre seul si 0)."""
    amount = max(0, int(amount))
    res = []
    for name, value, col in COINS:
        n, amount = divmod(amount, value)
        if n:
            res.append((name, n, col))
    return res or [("cuivre", 0, COINS[-1][2])]


def text(amount):
    """« 2 or 15 argent 40 cuivre »."""
    return " ".join(f"{n} {name}" for name, n, _col in split(amount))
