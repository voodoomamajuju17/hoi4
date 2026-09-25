"""Reporte de balance: qué arranca teniendo cada facción.

Produce:
  build/balance.txt    (fuera de la carpeta del mod: es para leer, no para el juego)

Los números salen de los states del juego como quedan después del reparto:
recursos, fábricas, manpower, provincias y puntos de victoria vanilla, más lo
que agrega el mod (el BioSteel inicial, las milicias). Si cambia el reparto,
cambia el reporte.

No lo usa el juego. Sirve para balancear sin tener que abrir una partida.
"""

from __future__ import annotations

from collections import Counter

from ..context import BuildContext
from . import economy as economy_mod
from .territory import display_name

RESOURCES = ["oil", "aluminium", "rubber", "tungsten", "steel", "chromium", "coal"]
RES_SHORT = {"oil": "Petr", "aluminium": "Alum", "rubber": "Cauch", "tungsten": "Tungs",
             "steel": "Acero", "chromium": "Cromo", "coal": "Carbon", "biosteel": "BioS"}


def emit(ctx: BuildContext) -> None:
    from . import effects as effects_mod
    for name in sorted(effects_mod.UNRESOLVED):
        ctx.warn(f"region '{name}' no existe en este juego: esa condicion nunca se cumple.")
    effects_mod.UNRESOLVED.clear()
    assignment: dict[int, str] | None = ctx.data.get("territory")
    if ctx.vanilla is None or assignment is None:
        return

    by_state = {s.id: s for s in ctx.vanilla.states()}
    names = ctx.data.get("state_names") or {}
    continents = ctx.vanilla.state_continents()
    land = ctx.vanilla.land_provinces()
    deposits = ctx.data.get("deposits") or {}
    militia = ctx.data.get("division_count") or ctx.data.get("militia_count") or {}
    extra_res = sorted({k for d in deposits.values() for k in d})
    res_cols = RESOURCES + extra_res

    rows = []
    for c in ctx.spec.countries:
        owned = [by_state[sid] for sid, tag in assignment.items() if tag == c.tag and sid in by_state]
        res = Counter()
        bld = Counter()
        cont = Counter()
        for s in owned:
            for k, v in economy_mod.resources_of(ctx, s).items():
                res[k] += v
            for k, v in (deposits.get(s.id) or {}).items():
                res[k] += v
            for k, v in economy_mod.buildings_of(ctx, s).items():
                bld[k] += v
            if continents.get(s.id):
                cont[continents[s.id]] += 1
        kind = ("Meganacion" if c.is_major else
                f"Satelite de {c.overlord}" if c.is_subject else "Anarquia/indep.")
        rows.append({
            "tag": c.tag, "name": c.name_es, "kind": kind, "ideology": c.ideology,
            "states": len(owned),
            "provinces": sum(1 for s in owned for p in s.provinces if p in land) if land
                         else sum(len(s.provinces) for s in owned),
            "manpower": sum(s.manpower for s in owned),
            "civ": bld["industrial_complex"], "mil": bld["arms_factory"], "dock": bld["dockyard"],
            "infra": (sum(s.buildings.get("infrastructure", 0) for s in owned if s.buildings) / len(owned))
                     if owned else 0,
            "vp": sum(s.victory_points for s in owned),
            "res": res,
            "cont": cont,
            "top": sorted(owned, key=lambda s: -s.manpower)[:3],
            "divisions": militia.get(c.tag, 0),
            "ships": (ctx.data.get("ships") or {}).get(c.tag, 0),
            "planes": (ctx.data.get("planes") or {}).get(c.tag, 0),
        })

    lines: list[str] = []
    add = lines.append
    add("2100 MEGANATIONS - BALANCE DE ARRANQUE")
    add("=" * 100)
    add("Datos del juego instalado, despues del reparto del mod. Manpower = poblacion base de los")
    add("states (el reclutable es un porcentaje segun leyes). IC = fabricas civiles + militares.")
    add("")

    header = f"{'TAG':4} {'Pais':32} {'Tipo':18} {'States':>6} {'Prov':>5} {'Manpower':>10} " \
             f"{'Civ':>4} {'Mil':>4} {'Astil':>5} {'IC':>4} {'Infra':>5} {'VP':>4} {'Div':>4} {'Barcos':>6} {'Aviones':>7}"
    add(header)
    add("-" * len(header))
    groups = [("Meganacion",), ("Satelite",), ("Anarquia",)]
    for prefix in (g[0] for g in groups):
        for r in sorted((r for r in rows if r["kind"].startswith(prefix)), key=lambda r: -(r["civ"] + r["mil"])):
            add(f"{r['tag']:4} {r['name'][:32]:32} {r['kind'][:18]:18} {r['states']:>6} {r['provinces']:>5} "
                f"{_mp(r['manpower']):>10} {r['civ']:>4} {r['mil']:>4} {r['dock']:>5} "
                f"{r['civ'] + r['mil']:>4} {r['infra']:>5.1f} {r['vp']:>4} {r['divisions']:>4} "
                f"{r['ships']:>6} {r['planes']:>7}")
    add("")

    add("RECURSOS")
    head = f"{'TAG':4} " + " ".join(f"{RES_SHORT.get(k, k[:6]):>6}" for k in res_cols)
    add(head)
    add("-" * len(head))
    for r in rows:
        add(f"{r['tag']:4} " + " ".join(f"{int(r['res'].get(k, 0)):>6}" for k in res_cols))
    add("")

    counters = []
    for m in ctx.spec.raw["mechanics"].get("mechanics", []) or []:
        if isinstance(m.get("variable"), dict):
            counters.append(m["variable"])
        counters += [dict(v, country=v.get("country", m.get("country"))) for v in m.get("variables") or []]
    if counters:
        add("CONTADORES NACIONALES (no son recursos del mapa)")
        for v in counters:
            add(f"{v['country']:4} {v['name']}: arranca en {v['start']}")
        add("")

    add("TERRITORIO APROXIMADO")
    add("-" * 100)
    for r in rows:
        total = sum(r["cont"].values()) or 1
        conts = ", ".join(f"{k} {100 * v // total}%" for k, v in r["cont"].most_common(3)) or "sin territorio"
        top = ", ".join(display_name(s, names) for s in r["top"]) or "-"
        add(f"{r['tag']:4} {conts:40} principales: {top}")
    add("")

    total_ic = sum(r["civ"] + r["mil"] for r in rows) or 1
    # Totales mundiales por recurso: tienen que ser idénticos a los vanilla.
    add("TOTAL MUNDIAL DE RECURSOS (tiene que ser igual al del juego base)")
    for k in RESOURCES:
        vanilla_total = sum((s.resources or {}).get(k, 0) for s in by_state.values())
        now = sum(economy_mod.resources_of(ctx, s).get(k, 0) for s in by_state.values())
        mark = "OK" if abs(vanilla_total - now) < 1e-6 else "DISTINTO"
        add(f"  {RES_SHORT.get(k, k):7} vanilla {vanilla_total:8.0f}   mod {now:8.0f}   {mark}")
    add("")

    add("PESO RELATIVO (IC sobre el total del mundo)")
    add("-" * 100)
    for r in sorted(rows, key=lambda r: -(r["civ"] + r["mil"])):
        share = 100 * (r["civ"] + r["mil"]) / total_ic
        add(f"{r['tag']:4} {share:5.1f}%  {'#' * int(share)}")
    add("")

    tree_rows = _tree_values(ctx)
    if tree_rows:
        add("VALOR DE LOS ARBOLES (todo lo que dan los focos si se hicieran todos, sin contar exclusiones)")
        add("-" * 100)
        add(f"{'TAG':4} {'Focos':>5} {'Dias':>5} {'Civ':>4} {'Mil':>4} {'Ast':>4} {'Casillas':>8} {'PP':>6} "
            f"{'Ideas':>5} {'Bonos inv.':>10} {'Exp.':>5}")
        for tag, v in tree_rows:
            add(f"{tag:4} {v['focos']:>5} {v['dias']:>5} {v['civ']:>4} {v['mil']:>4} {v['ast']:>4} {v['slot']:>8} "
                f"{v['pp']:>6} {v['ideas']:>5} {v['tb']:>10} {v['xp']:>5}")
        add("")

    add("ALERTAS")
    add("-" * 100)
    no_army = [r["tag"] for r in rows if r["states"] and not r["divisions"]]
    if no_army:
        add(f"! Sin ejercito inicial: {', '.join(no_army)}.")
    techs = ctx.data.get("techs") or {}
    stock = ctx.data.get("stockpile") or {}
    if techs:
        add("Tecnologias de arranque (solo la especialidad de cada meganacion): " + ", ".join(
            f"{tag} {len(v)}" for tag, v in sorted(techs.items()) if v))
    no_stock = [r["tag"] for r in rows if r["states"] and r["kind"] != "Anarquia/indep." and not stock.get(r["tag"])]
    if no_stock:
        add(f"! Sin equipo en deposito: {', '.join(no_stock)}.")
    empty = [r["tag"] for r in rows if not r["states"]]
    if empty:
        add(f"! Sin territorio (no existen en el mapa): {', '.join(empty)}")

    path = ctx.out_root / "balance.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ctx.track(path)
    ctx.data["balance_path"] = path
    ctx.note(f"balance: {path}")


def _tree_values(ctx: BuildContext) -> list[tuple[str, dict]]:
    """Suma los premios de cada árbol: fábricas, casillas, PP, ideas, bonos."""
    trees = (ctx.spec.raw.get("focus_trees") or {}).get("trees") or {}
    out = []
    for tag, tree in trees.items():
        if not isinstance(tree, dict) or not tree.get("branches"):
            continue
        v = dict(focos=0, dias=0, civ=0, mil=0, ast=0, slot=0, pp=0, ideas=0, tb=0, xp=0)

        def walk(items):
            for e in items or []:
                kind = e.get("effect")
                if kind in ("build", "build_here"):
                    key = {"industrial_complex": "civ", "arms_factory": "mil", "dockyard": "ast"}.get(e.get("building"))
                    if key:
                        v[key] += int(e.get("level", 1))
                elif kind == "add_research_slot":
                    v["slot"] += int(e.get("value", 1))
                elif kind == "add_political_power" and e.get("value", 0) > 0:
                    v["pp"] += int(e["value"])
                elif kind in ("add_ideas", "swap_ideas", "timed_idea"):
                    v["ideas"] += 1
                elif kind == "tech_bonus":
                    v["tb"] += int(e.get("uses", 1))
                elif kind in ("army_experience", "navy_experience", "air_experience"):
                    v["xp"] += int(e.get("value", 0))
                walk(e.get("effects"))
                walk(e.get("then"))

        for branch in tree["branches"]:
            for f in branch.get("focuses") or []:
                v["focos"] += 1
                v["dias"] += int(f.get("days", 0))
                walk(f.get("reward"))
        out.append((tag, v))
    return out


def _mp(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}k"
    return str(value)
