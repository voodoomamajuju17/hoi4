"""Albión distinta en cada camino (spec/44_albion_caminos.yaml, 2026-11-17).

El primer foco de cada camino pone la bandera de transición y cambia el retrato de cada personaje de ese
camino (los comunes y los propios) por el de su medio: assets/ZAL/leaders/<id>__<camino>.dds. El efecto
set_portraits solo se escribe si el retrato ya llegó (tools/gen/emitters/effects.py).
"""

from __future__ import annotations

from typing import Any


def ruta(cid: str, camino: str) -> str:
    return f"gfx/leaders/ZAL/{cid}__{camino}.dds"


def rol(ch: dict) -> str:
    """El tipo de retrato del personaje (army, navy o civilian), como lo arma characters.py."""
    p = (ch.get("portrait") or {}).get("role")
    if p:
        return p
    roles = {k for k, v in (ch.get("roles") or {}).items() if v}
    if "navy_leader" in roles:
        return "navy"
    if roles & {"field_marshal", "corps_commander"}:
        return "army"
    adv = (ch.get("roles") or {}).get("advisor")
    if isinstance(adv, dict) and adv.get("slot") in ("army_chief", "high_command", "air_chief"):
        return "army"
    if isinstance(adv, dict) and adv.get("slot") == "navy_chief":
        return "navy"
    return "civilian"


def personajes(cfg: dict) -> list[tuple[str, str]]:
    """(personaje, camino) de cada retrato que hace falta."""
    out = []
    for camino, c in cfg["caminos"].items():
        out += [(cid, camino) for cid in list(cfg.get("comunes") or []) + list(c.get("propios") or [])]
    return out


def expandir(raw: dict[str, Any], cfg: dict) -> dict[str, Any]:
    chars = {c["id"]: c for c in raw["leaders"]["characters"]}
    focos: dict[str, dict] = {}
    for camino, c in cfg["caminos"].items():
        efectos = [{"effect": "cosmetic_tag", "value": c["bandera"]}]
        for cid in list(cfg.get("comunes") or []) + list(c.get("propios") or []):
            if cid not in chars:
                raise ValueError(f"44_albion_caminos: '{cid}' no es un personaje")
            efectos.append({"effect": "set_portraits", "character": cid, "role": rol(chars[cid]),
                            "large": ruta(cid, camino)})
        focos[c["foco"]] = {"reward_append": efectos}
    return {"extend_focuses": focos}
