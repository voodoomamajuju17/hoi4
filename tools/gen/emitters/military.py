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
from . import economy as economy_mod
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
    specialty = _specialties(ctx, spec.get("research") or {})
    tree = ctx.vanilla.tech_tree()
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
        year = int(spec["stockpile_year"][kind])
        ctx.data["techs"][c.tag] = specialty.get(c.tag, [])

        base = [t for t in (spec.get("research") or {}).get("base_techs", []) if t in tree]
        ctx.data["techs"][c.tag] = list(dict.fromkeys(base + specialty.get(c.tag, [])))

        if kind == "anarchy":
            continue

        garrison = spec["army"]["garrison"]
        count = int((garrison.get("overrides") or {}).get(c.tag, garrison[kind]))
        tpl = spec["army"]["templates"][garrison["template"]]
        tpl_name = tpl["name"]["spanish"]
        root = Block()
        root.add("division_template", _template(tpl))

        # Guarnición mínima en la capital (pedido del usuario, 2026-09-25).
        cap = (ctx.data.get("capitals") or {}).get(c.tag)
        spot = by_state.get(cap) if cap in by_state and any(p in land for p in by_state[cap].provinces) else None
        if spot is None:
            spot = next((s for s in sorted(owned, key=lambda s: (-s.manpower, s.id))
                         if any(p in land for p in s.provinces)), owned[0])
        units = Block()
        for n in range(count):
            province = next((p for p in spot.provinces if p in land), spot.provinces[0] if spot.provinces else None)
            if province is None:
                continue
            div = Block()
            div.add("name", Quoted(f"{n + 1}.ª {tpl_name} de {display_name(spot, names)}"))
            div.add("location", province)
            div.add("division_template", Quoted(tpl_name))
            div.add("start_experience_factor", 0.2)
            units.add("division", div)
        root.add("units", units)

        oob = f"{c.tag}_2100"
        ctx.write_text(f"history/units/{oob}.txt", banner_for(SOURCE) + render(root))
        ctx.data["oob"][c.tag] = oob
        ctx.data["division_count"][c.tag] = count
        ic = sum(economy_mod.buildings_of(ctx, s).get("industrial_complex", 0)
                 + economy_mod.buildings_of(ctx, s).get("arms_factory", 0) for s in owned)

        stock = []
        for archetype, amount in (spec["stockpile"]["per_kind"].get(kind) or {}).items():
            item = _best_variant(equipment, archetype, year)
            if item is None:
                if archetype not in warned:
                    ctx.warn(f"deposito: no hay variante de '{archetype}' hasta {year} en el juego; se saltea.")
                    warned.add(archetype)
                continue
            stock.append((item, int(amount)))
        conv = spec["stockpile"]["convoys"]
        convoy = _best_variant(equipment, conv["equipment"], year)
        if convoy:
            stock.append((convoy, int(conv["base"] + ic * float(conv["per_ic"]))))
        elif "convoy" not in warned:
            ctx.warn(f"deposito: no encontre el equipo de convoyes '{conv['equipment']}'.")
            warned.add("convoy")
        ctx.data["stockpile"][c.tag] = stock

    total_divs = sum(ctx.data["division_count"].values())
    ctx.note(f"arranque militar: {total_divs} divisiones en total")


def _specialties(ctx: BuildContext, research: dict) -> dict[str, list[str]]:
    """Investigación de arranque (pedido del usuario, 2026-09-25): nadie
    tiene nada investigado salvo las primeras N tecnologías de la pestaña
    de su especialidad. "Primeras" = en el orden del árbol: solo se toma una
    tecnología cuando ya se tomaron sus padres de la misma pestaña, por año
    y posición; de un par excluyente (xor) se toma la primera."""
    tree = ctx.vanilla.tech_tree()
    all_folders = sorted({t["folder"] for t in tree.values() if t["folder"]})
    n = int(research.get("techs_per_specialty", 5))
    parents: dict[str, set[str]] = {}
    for name, t in tree.items():
        for child in t["leads_to"]:
            parents.setdefault(child, set()).add(name)
    out: dict[str, list[str]] = {}
    lines = []
    for tag, cat in (research.get("specialty") or {}).items():
        options = (research.get("folders") or {}).get(cat)
        if not options:
            raise SpecError(f"research: la especialidad '{cat}' de {tag} no esta en folders", where=SOURCE)
        # Lista de alternativas: la primera que exista gana. Así se prefieren las
        # pestañas de los DLC (nsb_armour, bba_air, mtgnaval...) sobre las viejas,
        # que con esos DLC ni se muestran.
        if all(isinstance(o, str) for o in options):
            options = [options]
        folders: set[str] = set()
        prefixes: list[str] = []
        for prefixes in options:
            folders = {f for f in all_folders if "doctrine" not in f.lower()
                       and any(f.lower().startswith(p) for p in prefixes)}
            if folders:
                break
        if not folders:
            ctx.warn(f"investigacion: ninguna pestaña del juego empieza con {prefixes} ({tag}); "
                     f"pestañas: {', '.join(all_folders)}")
            continue
        pool = {k: v for k, v in tree.items() if v["folder"] in folders and v["eligible"]}
        picked: list[str] = []
        blocked: set[str] = set()
        while len(picked) < n:
            cands = [t for t in pool if t not in picked and t not in blocked
                     and all(p in picked for p in parents.get(t, ()) if p in pool)]
            if not cands:
                break
            cands.sort(key=lambda t: (pool[t]["year"], pool[t]["y"], pool[t]["x"], t))
            chosen = cands[0]
            picked.append(chosen)
            blocked.update(pool[chosen]["xor"])
        out[tag] = picked
        lines.append(f"{tag} {cat} ({', '.join(sorted(folders))}): {', '.join(picked)}")
    ctx.note("investigacion de arranque (el resto del mundo, nada):\n      " + "\n      ".join(lines))
    try:
        _dump_tree(ctx, tree)
    except Exception as exc:  # noqa: BLE001 - es solo un informe, nunca frena el mod
        ctx.warn(f"investigacion.txt no se pudo escribir ({exc}); el mod sale igual.")
    return out


def _dump_tree(ctx: BuildContext, tree: dict[str, dict]) -> None:
    """build/investigacion.txt: el árbol del juego instalado, pestaña por
    pestaña, con sus nombres en inglés y castellano. Es la base para
    renombrar las tecnologías y evaluar el rediseño de la investigación."""
    import re
    en = ctx.vanilla.localisation("english", set(tree))
    es = ctx.vanilla.localisation("spanish", set(tree))
    by_folder: dict[str, list[str]] = {}
    for name, t in tree.items():
        by_folder.setdefault(t["folder"] or "(sin pestaña)", []).append(name)
    lines = ["INVESTIGACION DEL JUEGO INSTALADO (para renombrar y rediseñar)", "=" * 100,
             "pestaña | año | x,y | tecnologia | ingles | castellano | excluye | lleva a", ""]
    for folder in sorted(by_folder):
        names = sorted(by_folder[folder], key=lambda n: (tree[n]["year"], tree[n]["y"], tree[n]["x"], n))
        lines.append(f"-- {folder} ({len(names)})")
        for n in names:
            t = tree[n]
            lines.append(f"{folder} | {t['year']} | {t['x']:g},{t['y']:g} | {n} | {en.get(n, '-')} | {es.get(n, '-')}"
                         f" | {' '.join(t['xor']) or '-'} | {' '.join(t['leads_to']) or '-'}"
                         + ("" if t["eligible"] else " | (doctrina o variante sin DLC)"))
        lines.append("")
    # Los años de la pantalla de investigación: ¿texto fijo en la interfaz?
    years = re.compile(r'text\s*=\s*"(19[3-5]\d)"')
    hits = []
    for gui in sorted((ctx.vanilla.root / "interface").glob("**/*.gui")):
        try:
            found = years.findall(gui.read_text(encoding="utf-8-sig", errors="replace"))
        except OSError:
            continue
        if found:
            hits.append(f"{gui.relative_to(ctx.vanilla.root).as_posix()}: {len(found)} ({', '.join(sorted(set(found)))})")
    lines.append("AÑOS ESCRITOS EN LA INTERFAZ (texto fijo \"19xx\")")
    lines += hits or ["ninguno: los años salen de otro lado"]
    path = ctx.out_root / "investigacion.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ctx.data["research_path"] = str(path)


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

