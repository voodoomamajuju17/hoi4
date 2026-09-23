"""Diplomacia de arranque (spec/04_diplomacy.yaml): mundo vivo.

Produce:
  common/opinion_modifiers/meganations_opinion_modifiers.txt
y deja en ctx.data["diplomacy_history"][TAG] entradas que la historia del país
agrega tal cual:
  add_opinion_modifier   rivalidades (en los dos sentidos)
  declare_war_on         guerras activas al arranque
  add_named_threat       tensión mundial inicial (en el país por defecto)

Los reclamos sobre la Anarquía los calcula territory.py (necesita el mapa).
Tipos de wargoal verificados contra common/wargoals; efectos contra
documentation/. Un país sin territorio no entra en guerras ni rivalidades.
"""

from __future__ import annotations

from collections import defaultdict

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block

SOURCE = "spec/04_diplomacy.yaml"
LOC_FILE = "meganations_diplomacy"


def emit(ctx: BuildContext) -> None:
    spec = ctx.spec.raw["diplomacy"]
    territory = ctx.data.get("territory") or {}
    alive = set(territory.values())
    out: dict[str, list] = defaultdict(list)
    effects: dict[str, str] = {}

    mods = spec.get("opinion_modifiers") or []
    if mods:
        body = Block()
        for m in mods:
            mb = Block()
            mb.add("value", int(m["value"]))
            body.add(ctx.loc.reference(m["id"], f"diplomacy:{m['id']}"), mb)
            ctx.loc.define(m["id"], en=m["name"]["english"], es=m["name"]["spanish"],
                           file=LOC_FILE, origin=f"diplomacy:{m['id']}")
        root = Block()
        root.add("opinion_modifiers", body)
        ctx.write_script("common/opinion_modifiers/meganations_opinion_modifiers.txt", root, source=SOURCE)
    known_mods = {m["id"] for m in mods}

    for r in spec.get("rivalries", []) or []:
        a, b = r["between"]
        if r["modifier"] not in known_mods:
            raise SpecError(f"rivalidad {a}-{b}: modificador '{r['modifier']}' no definido", where=SOURCE)
        if a not in alive or b not in alive:
            continue
        for x, y in ((a, b), (b, a)):
            om = Block()
            om.add("target", y)
            om.add("modifier", r["modifier"])
            out[x].append(("add_opinion_modifier", om))
        effects["add_opinion_modifier"] = SOURCE

    wargoals = ctx.vanilla.wargoal_types() if ctx.vanilla else set()
    for w in spec.get("wars_at_start", []) or []:
        if not isinstance(w, dict):
            continue
        att, dfd = w["attacker"], w["defender"]
        if att not in alive or dfd not in alive:
            ctx.warn(f"guerra {att} -> {dfd}: alguno no tiene territorio; no se declara.")
            continue
        if wargoals and w["wargoal"] not in wargoals:
            raise SpecError(f"wargoal '{w['wargoal']}' no existe en common/wargoals/", where=SOURCE)
        dw = Block()
        dw.add("target", dfd)
        dw.add("type", w["wargoal"])
        out[att].append(("declare_war_on", dw))
        effects["declare_war_on"] = SOURCE
        ctx.note(f"guerra al arranque: {att} contra {dfd}")

    tension = spec.get("world_tension")
    if isinstance(tension, dict) and tension.get("threat"):
        host = ctx.spec.raw["scenario"]["bookmark"]["default_country"]
        key = ctx.loc.define_and_reference(
            "MEGANATIONS_THREAT_COLLAPSE", en=tension["name"]["english"], es=tension["name"]["spanish"],
            file=LOC_FILE, origin="diplomacy:world_tension",
        )
        nt = Block()
        nt.add("threat", int(tension["threat"]))
        nt.add("name", key)
        out[host].append(("add_named_threat", nt))
        effects["add_named_threat"] = SOURCE

    ctx.data["diplomacy_history"] = dict(out)
    ctx.verify_keys("effects", effects)
