"""Artefacts (inspirés de Minecraft Dungeons) : objets actifs à recharge, équipés dans 3 emplacements.

Leurs effets sont décrits dans data/artifacts.json et exécutés par l'interpréteur de spells.py
("v" dans un effet = puissance de l'artefact selon sa rareté et son amélioration).
"""
from . import spells
from .data import ARTIFACTS
from .items import art_value


def use(world, slot):
    p = world.player
    it = p.equipment.get(slot)
    if not it or p.dead or p.leap:
        return
    if p.art_cds.get(slot, 0) > 0:
        return
    a = ARTIFACTS.get(it["art"])
    if not a:
        return
    ctx = spells.Ctx(world, *world.aim_point(), mult=1.0, color=a["color"], value=art_value(it))
    if spells.run(a["effects"], ctx) is False:
        return
    cd = a["cd"] * (1 - p.stats["cdr"] / 100)
    p.art_cds[slot] = cd
    p.art_total[slot] = cd
