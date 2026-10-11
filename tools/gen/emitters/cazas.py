"""Cazas gratis con ciertos focos (spec/13_military.yaml -> free_fighters).

Pedido del usuario (2026-10-11): "añadí cazas gratis con ciertos focus".
Con el diseñador de aviones (By Blood Alone) un caza es un diseño sobre un
fuselaje, no un equipo suelto: cada potencia recibe su propio diseño (con el
nombre de su caza en 17_research -> by_faction, "Caza-Planeador Kuntur") la
primera vez que un foco se lo da (MEGANATIONS_diseno_caza_<TAG>, con las
tecnologías que pide), y el foco suma N aviones de ese diseño al depósito.

Corre después de territory y antes de focus_trees: los focos reciben los
efectos al final de su recompensa (no se toca el spec en disco).
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted
from . import unique_units as uu

SOURCE = "spec/13_military.yaml -> free_fighters"
FILE = "common/scripted_effects/meganations_cazas.txt"


def _config(spec_raw: dict) -> dict:
    return (spec_raw.get("military") or {}).get("free_fighters") or {}


def effect_name(tag: str) -> str:
    return f"MEGANATIONS_diseno_caza_{tag}"


def scripted_ids(spec_raw: dict) -> set[str]:
    return {effect_name(fid.split("_")[0]) for fid in (_config(spec_raw).get("focuses") or {})}


def prepare(ctx: BuildContext) -> None:
    cfg = _config(ctx.spec.raw)
    focuses = cfg.get("focuses") or {}
    if not focuses or ctx.vanilla is None:
        return
    tree = ctx.vanilla.tech_tree()
    equip = uu._equipment_blocks(ctx.vanilla.root)
    modules = uu._module_blocks(ctx.vanilla.root)
    enabled_by: dict[str, str] = {}
    for t, info in sorted(tree.items(), key=lambda kv: (kv[1]["year"], kv[0])):
        for e in info["enables"]:
            enabled_by.setdefault(e, t)
    names = ((ctx.spec.raw.get("research_look") or {}).get("by_faction") or {}).get("names") or {}
    trees = ctx.spec.raw["focus_trees"]["trees"]
    tags = sorted({fid.split("_")[0] for fid in focuses})
    out = Block()
    built: dict[str, tuple[str, str]] = {}
    for tag in tags:
        country = ctx.spec.country(tag)
        plane = (names.get(tag) or {}).get("light_plane") or {}
        design = dict(cfg.get("design") or {})
        design["name"] = plane.get("es") or f"Caza {country.name_es.split()[0]}"
        variant, grant = uu._design(ctx, f"cazas_{tag}", design, equip, modules, tree, enabled_by)
        if variant is None:
            continue
        chassis = str(variant.get("type"))
        # el ícono propio del caza de la facción (faction_tech lo registra como
        # GFX_<TAG>_<fuselaje>_medium si hay imagen; el diseño muestra su `icon`)
        repo = ctx.spec.root.parent
        if any((repo / "assets" / tag / sub / "light_plane.dds").exists() for sub in ("armas", "tech")):
            variant.entries = [(k, v) for k, v in variant.entries if k != "icon"]
            variant.add("icon", Quoted(f"GFX_{tag}_{chassis}_medium"))
        if chassis in enabled_by:
            grant.insert(0, enabled_by[chassis])
        flag = f"MEGANATIONS_diseno_caza_hecho"
        body = Block([("limit", Block([("NOT", Block([("has_country_flag", flag)]))])),
                      ("set_country_flag", flag)])
        if grant:
            body.add("set_technology", Block([(t, 1) for t in dict.fromkeys(grant)] + [("popup", False)]))
        body.add("create_equipment_variant", variant)
        out.add(effect_name(tag), Block([("if", body)]))
        built[tag] = (chassis, design["name"])
    if not out.entries:
        ctx.warn("cazas gratis: el juego no tiene un fuselaje de caza con casillas; los focos no dan cazas.")
        return
    ctx.write_script(FILE, out, source=SOURCE)
    ctx.verify_keys("effects", {k: "free_fighters" for k in
                                ("set_country_flag", "set_technology", "create_equipment_variant",
                                 "add_equipment_to_stockpile")})
    ctx.verify_keys("triggers", {"has_country_flag": "free_fighters"})
    lines = []
    for fid, amount in focuses.items():
        tag = fid.split("_")[0]
        if tag not in built:
            continue
        focus = next((f for b in trees[tag]["branches"] for f in b["focuses"] if f["id"] == fid), None)
        if focus is None:
            raise SpecError(f"free_fighters: el foco '{fid}' no existe", where=SOURCE)
        chassis, name = built[tag]
        focus["reward"] = list(focus.get("reward") or []) + [
            {"effect": "run", "value": effect_name(tag)},
            {"effect": "equipment", "type": chassis, "amount": int(amount), "variant": name, "producer": tag},
        ]
        lines.append(f"{fid} {amount} '{name}'")
    ctx.note("cazas gratis: " + "; ".join(lines))
