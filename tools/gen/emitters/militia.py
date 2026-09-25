"""Milicias iniciales: una división por territorio contiguo (08_territory.yaml).

Produce:
  history/units/<TAG>_2100.txt   plantilla + divisiones
y deja en ctx.data["oob"][TAG] el nombre, que la historia del país usa en `oob`.

"Territorio contiguo" = componente conexa de los states del país, donde dos
states son vecinos si alguna provincia de uno toca alguna del otro en
map/provinces.bmp. Las islas y los enclaves quedan como territorios propios,
cada uno con su milicia. Cada división se ubica en una provincia de tierra del
state con más manpower de su territorio.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted, banner_for, render
from .territory import display_name


def emit(ctx: BuildContext) -> None:
    assignment: dict[int, str] | None = ctx.data.get("territory")
    territories = ctx.spec.raw["territory"].get("territories") or {}
    wanted = {tag: t["militia"] for tag, t in territories.items()
              if isinstance(t, dict) and isinstance(t.get("militia"), dict)}
    if not wanted:
        return
    if ctx.vanilla is None or assignment is None:
        for tag in wanted:
            ctx.skip(f"milicias de {tag}", "hace falta el mapa del juego (--vanilla-path)", "Q035")
        return

    units = _unit_types(ctx)
    adjacency = ctx.vanilla.province_adjacency(ctx.out_root / ".cache")
    land = ctx.vanilla.land_provinces()
    by_state = {s.id: s for s in ctx.vanilla.states()}
    names = ctx.data.get("state_names") or {}
    ctx.data.setdefault("oob", {})

    for tag, spec in wanted.items():
        for regiment in spec["regiments"]:
            if units and regiment not in units:
                raise SpecError(f"milicia de {tag}: el regimiento '{regiment}' no existe en common/units/",
                                where="08_territory.yaml")
        owned = sorted(sid for sid, t in assignment.items() if t == tag)
        if not owned:
            continue
        blobs = _components(owned, by_state, adjacency)

        template_name = spec["template_name"]["spanish"]
        root = Block()
        template = Block()
        template.add("name", Quoted(template_name))
        regiments = Block()
        for i, regiment in enumerate(spec["regiments"]):
            pos = Block()
            pos.add("x", 0)
            pos.add("y", i)
            regiments.add(regiment, pos)
        template.add("regiments", regiments)
        root.add("division_template", template)

        divisions = Block()
        placed = 0
        mil = (ctx.spec.raw.get("military") or {}).get("militia", {}) or {}
        per = float(mil.get("states_per_division", 0) or 0)
        per_country = int(mil.get("per_country", 0) or 0)
        if per_country:
            # Una cantidad fija por país, en el territorio más poblado.
            blobs = [max(blobs, key=lambda b: sum(by_state[sid].manpower for sid in b))]
        for blob in blobs:
            # Una cada `per` states del territorio (mínimo una), en sus states
            # más poblados. Sin `per`: una por territorio.
            count = per_country or (max(1, round(len(blob) / per)) if per > 0 else 1)
            spots = sorted(blob, key=lambda sid: (-by_state[sid].manpower, sid))
            for i in range(count):
                sid = spots[i % len(spots)]
                province = next((p for p in by_state[sid].provinces if p in land), None)
                if province is None:
                    continue
                div = Block()
                div.add("name", Quoted(f"{template_name} de {display_name(by_state[sid], names)}"
                                       + (f" {i // len(spots) + 1}" if i >= len(spots) else "")))
                div.add("location", province)
                div.add("division_template", Quoted(template_name))
                div.add("start_experience_factor", 0.1)
                divisions.add("division", div)
                placed += 1
        root.add("units", divisions)

        oob = f"{tag}_2100"
        ctx.write_text(f"history/units/{oob}.txt", banner_for("spec/08_territory.yaml -> militia") + render(root))
        ctx.data["oob"][tag] = oob
        ctx.data.setdefault("militia_count", {})[tag] = placed
        if not adjacency:
            ctx.warn(f"milicias de {tag}: no pude leer map/provinces.bmp; una division por state.")
        ctx.note(f"milicias de {tag}: {placed} divisiones en {len(blobs)} territorios contiguos")


def _components(owned: list[int], by_state, adjacency: set[tuple[int, int]]) -> list[list[int]]:
    prov_to_state = {p: sid for sid in owned for p in by_state[sid].provinces}
    neighbours: dict[int, set[int]] = {sid: set() for sid in owned}
    for a, b in adjacency:
        sa, sb = prov_to_state.get(a), prov_to_state.get(b)
        if sa is not None and sb is not None and sa != sb:
            neighbours[sa].add(sb)
            neighbours[sb].add(sa)
    seen: set[int] = set()
    out: list[list[int]] = []
    for start in owned:
        if start in seen:
            continue
        stack, blob = [start], []
        seen.add(start)
        while stack:
            sid = stack.pop()
            blob.append(sid)
            for n in neighbours[sid]:
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        out.append(sorted(blob))
    return out


def _unit_types(ctx: BuildContext) -> set[str]:
    import re
    out: set[str] = set()
    for path in (ctx.vanilla.root / "common" / "units").glob("*.txt"):
        try:
            out.update(re.findall(r"^\t([a-z_]+)\s*=\s*\{", path.read_text(encoding="utf-8-sig", errors="replace"),
                                  re.MULTILINE))
        except OSError:
            continue
    return out
