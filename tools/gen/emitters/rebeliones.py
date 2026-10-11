"""Dónde se levantan las rebeliones del ultimátum (spec/04_diplomacy.yaml -> rebellions).

Pedido del usuario (2026-10-11): "las rebeliones tienen que tener más
sentido": en Roma un cisma entre el este y el oeste, en la HSN la cruz del mar
se queda con un nodo y la mitad de la flota. Lo que necesita el mapa sale de
acá y queda registrado para el efecto civil_war (`region`, effects.py):

  side: east|west   las regiones del país al arrancar que están al este (u
                    oeste) de la mitad de sus regiones, por la posición de sus
                    edificios en map/buildings.txt; capital, la de más puntos de
                    victoria de ese lado
  states: [...]     regiones por nombre (la primera que exista es la capital)

Sin map/buildings.txt (o sin regiones) la rebelión sale igual, sin región: el
juego reparte el país según `size`.
"""

from __future__ import annotations

from ..context import BuildContext
from . import effects as effects_mod

SOURCE = "spec/04_diplomacy.yaml -> rebellions"


def prepare(ctx: BuildContext) -> None:
    cfg = (ctx.spec.raw["diplomacy"].get("rebellions") or {}).get("regions") or {}
    regions: dict[str, tuple[int, list[int]]] = {}
    if not cfg or ctx.vanilla is None:
        effects_mod.use_regions({})
        return
    from .territory import normalize
    territory = ctx.data.get("territory") or {}
    ids = ctx.data.get("state_ids_by_name") or {}
    states = {s.id: s for s in ctx.vanilla.states()}
    pos = ctx.vanilla.state_positions()
    notes = []
    for name, r in cfg.items():
        picked: list[int] = []
        if r.get("side"):
            own = [sid for sid, t in territory.items() if t == r["tag"] and sid in pos]
            if len(own) >= 2:
                xs = sorted(pos[s] for s in own)
                mid = xs[len(xs) // 2]
                east = r["side"] == "east"
                picked = sorted((s for s in own if (pos[s] >= mid if east else pos[s] < mid)),
                                key=lambda s: -states[s].victory_points if s in states else 0)
        for names in r.get("states") or []:
            sid = next((ids[normalize(n)] for n in names if normalize(n) in ids), None)
            if sid is not None and sid not in picked:
                picked.append(sid)
        if picked:
            regions[name] = (picked[0], sorted(picked))
            notes.append(f"{name} {len(picked)} regiones (capital {picked[0]})")
        else:
            notes.append(f"{name} sin region (el juego reparte por tamaño)")
    effects_mod.use_regions(regions)
    ctx.data["rebellion_regions"] = regions
    ctx.note("rebeliones: " + "; ".join(notes))
