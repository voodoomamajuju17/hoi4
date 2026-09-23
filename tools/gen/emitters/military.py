"""Arranque militar: tecnologías, ejército y equipo (spec/13_military.yaml).

Produce:
  history/units/<TAG>_2100.txt     plantillas + divisiones
y deja para la historia de cada país (history.py):
  ctx.data["techs"][TAG]       tecnologías de arranque (set_technology)
  ctx.data["stockpile"][TAG]   [(equipo, cantidad)] (add_equipment_to_stockpile)
  ctx.data["oob"][TAG]         nombre del oob

Nada se escribe de memoria: tecnologías, equipos y regimientos se leen de la
instalación. Un regimiento que no existe frena el build; un arquetipo de
equipo que no existe se saltea con aviso (los depósitos son un extra).

La Anarquía no pasa por acá para el ejército (tiene sus milicias, militia.py),
pero sí recibe su nivel tecnológico.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted, banner_for, render
from .territory import display_name

SOURCE = "spec/13_military.yaml"


def faction_kind(c) -> str:
    if c.is_major:
        return "meganation"
    if c.is_subject:
        return "satellite"
    return "anarchy"


def emit(ctx: BuildContext) -> None:
    spec = ctx.spec.raw.get("military")
    assignment = ctx.data.get("territory")
    if not spec:
        return
    if ctx.vanilla is None or assignment is None:
        ctx.skip("arranque militar", "tecnologias, equipos y regimientos salen del juego instalado", "Q035")
        return

    by_state = {s.id: s for s in ctx.vanilla.states()}
    names = ctx.data.get("state_names") or {}
    land = ctx.vanilla.land_provinces()
    techs = ctx.vanilla.technologies()
    equipment = ctx.vanilla.equipment()
    sub_units = ctx.vanilla.sub_units()
    _check_templates(spec, sub_units)

    ctx.data.setdefault("oob", {})
    ctx.data.setdefault("techs", {})
    ctx.data.setdefault("stockpile", {})
    ctx.data.setdefault("division_count", dict(ctx.data.get("militia_count") or {}))
    warned: set[str] = set()

    for c in ctx.spec.countries:
        owned = [by_state[sid] for sid, tag in assignment.items() if tag == c.tag and sid in by_state]
        if not owned:
            continue
        kind = faction_kind(c)
        year = int(spec["tech_levels"][kind])
        ctx.data["techs"][c.tag] = sorted(name for name, y, ok in techs if ok and y <= year)

        if kind == "anarchy" or kind not in spec["army"]["divisions"]:
            continue

        ic = sum((s.buildings or {}).get("industrial_complex", 0) + (s.buildings or {}).get("arms_factory", 0)
                 for s in owned)
        rule = spec["army"]["divisions"][kind]
        total = min(int(rule["max"]), int(rule["base"] + ic * float(rule["per_ic"])))
        plan = _split(total, spec["army"]["mix"][kind])

        root = Block()
        for key in plan:
            root.add("division_template", _template(spec["army"]["templates"][key]))

        # Divisiones repartidas entre los states más poblados, en ronda.
        spots = [s for s in sorted(owned, key=lambda s: (-s.manpower, s.id))
                 if any(p in land for p in s.provinces)] or owned
        units = Block()
        i = 0
        for key, count in plan.items():
            tpl_name = spec["army"]["templates"][key]["name"]["spanish"]
            for n in range(count):
                s = spots[i % len(spots)]
                i += 1
                province = next((p for p in s.provinces if p in land), s.provinces[0] if s.provinces else None)
                if province is None:
                    continue
                div = Block()
                div.add("name", Quoted(f"{n + 1}.ª {tpl_name} de {display_name(s, names)}"))
                div.add("location", province)
                div.add("division_template", Quoted(tpl_name))
                div.add("start_experience_factor", 0.2)
                units.add("division", div)
        root.add("units", units)

        oob = f"{c.tag}_2100"
        ctx.write_text(f"history/units/{oob}.txt", banner_for(SOURCE) + render(root))
        ctx.data["oob"][c.tag] = oob
        ctx.data["division_count"][c.tag] = sum(plan.values())

        stock = []
        for archetype, per_div in spec["stockpile"]["per_division"].items():
            item = _best_variant(equipment, archetype, year)
            if item is None:
                if archetype not in warned:
                    ctx.warn(f"deposito: no hay variante de '{archetype}' hasta {year} en el juego; se saltea.")
                    warned.add(archetype)
                continue
            stock.append((item, int(per_div * sum(plan.values()))))
        conv = spec["stockpile"]["convoys"]
        convoy = _best_variant(equipment, conv["equipment"], year)
        if convoy:
            stock.append((convoy, int(conv["base"] + ic * float(conv["per_ic"]))))
        elif "convoy" not in warned:
            ctx.warn(f"deposito: no encontre el equipo de convoyes '{conv['equipment']}'.")
            warned.add("convoy")
        ctx.data["stockpile"][c.tag] = stock

    total_divs = sum(ctx.data["division_count"].values())
    ctx.note(f"arranque militar: {total_divs} divisiones en total; tecnologias por nivel "
             + ", ".join(f"{k} hasta {v}" for k, v in spec["tech_levels"].items() if isinstance(v, int)))


def _check_templates(spec: dict, sub_units: set[str]) -> None:
    if not sub_units:
        return
    for key, tpl in spec["army"]["templates"].items():
        for unit in list(tpl["regiments"]) + list(tpl.get("support", [])):
            if unit not in sub_units:
                raise SpecError(f"plantilla {key}: el regimiento '{unit}' no existe en common/units/",
                                where="13_military.yaml")


def _template(tpl: dict) -> Block:
    b = Block()
    b.add("name", Quoted(tpl["name"]["spanish"]))
    regiments = Block()
    # Columnas de a 3 regimientos, como las plantillas vanilla.
    for i, unit in enumerate(tpl["regiments"]):
        pos = Block()
        pos.add("x", i // 3)
        pos.add("y", i % 3)
        regiments.add(unit, pos)
    b.add("regiments", regiments)
    if tpl.get("support"):
        support = Block()
        for i, unit in enumerate(tpl["support"]):
            pos = Block()
            pos.add("x", 0)
            pos.add("y", i)
            support.add(unit, pos)
        b.add("support", support)
    return b


def _split(total: int, mix: dict[str, float]) -> dict[str, int]:
    """Reparte `total` divisiones según proporciones, sumando exacto."""
    raw = {k: total * float(v) for k, v in mix.items()}
    out = {k: int(v) for k, v in raw.items()}
    rest = total - sum(out.values())
    for k in sorted(raw, key=lambda k: -(raw[k] - out[k]))[:rest]:
        out[k] += 1
    return {k: v for k, v in out.items() if v > 0}


def _best_variant(equipment: dict, archetype: str, year: int) -> str | None:
    candidates = [(y, name) for name, (arch, y) in equipment.items() if arch == archetype and y <= year]
    return max(candidates)[1] if candidates else None

