"""Suministro e infraestructura de 2100 (spec/08_territory.yaml -> logistics).

Pedido del usuario (2026-10-10): "Aumentá la cantidad de centros de
suministro donde tenga sentido para el mundo postapocalíptico renacido del
2100. Sacalos donde no tenga sentido. Corregí niveles de infraestructura
acorde a lo mismo."

Las meganaciones reconstruyeron sus redes; las anarquías viven entre ruinas:

  infraestructura   por tipo de dueño (meganación, satélite, anarquía): suma,
                    mínimo, máximo y mínimo de la capital. Va como diferencia en
                    los edificios de la región (territory.py la aplica).
  centros de        map/supply_nodes.txt del juego, reescrito: se sacan los de
  suministro        las regiones de anarquía sin ciudad (menos su capital) y se
                    agregan en las ciudades de meganaciones y satélites que no
                    tienen, en su punto de victoria principal. Un centro sin vía
                    no recibe nada: cada uno nuevo lleva su tramo hasta la red
                    (map/railways.txt), por provincias del mismo dueño.

Si los archivos del mapa no tienen el formato esperado (nivel + provincia;
nivel + cantidad + provincias) no se tocan y el reporte lo dice.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque

from ..context import BuildContext
from .military import faction_kind

SOURCE = "spec/08_territory.yaml -> logistics"
CITY = {"city", "large_city", "metropolis", "megalopolis"}


def _spec(ctx: BuildContext) -> dict:
    return (ctx.spec.raw["territory"].get("logistics") or {})


def infrastructure_plan(ctx: BuildContext, assignment: dict[int, str], capitals: dict[str, int],
                        by_state: dict) -> dict[int, int]:
    """Región -> diferencia de infraestructura (nuevo nivel - nivel del juego)."""
    spec = _spec(ctx).get("infrastructure") or {}
    if not spec:
        return {}
    kinds = {c.tag: faction_kind(c) for c in ctx.spec.countries}
    skip = set(spec.get("skip") or [])
    cap_states = set(capitals.values())
    out: dict[int, int] = {}
    count: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for sid, tag in assignment.items():
        st = by_state.get(sid)
        rule = spec.get(kinds.get(tag, ""))
        if st is None or not rule or tag in skip:
            continue
        cur = int((st.buildings or {}).get("infrastructure", 0))
        new = cur + int(rule.get("add", 0))
        if sid in cap_states:
            if rule.get("capital_min") is not None:
                new = max(new, int(rule["capital_min"]))
            if rule.get("keep_capital"):
                new = max(new, cur)
        floor = int(rule.get("min", 0))
        if int(rule.get("add", 0)) < 0:
            floor = min(floor, cur)      # a una anarquía nunca se le sube
        new = max(new, floor)
        new = min(new, int(rule.get("max", 5)))
        if new != cur:
            out[sid] = new - cur
            count[kinds[tag]][0 if new > cur else 1] += 1
    ctx.note("infraestructura de 2100: " + ", ".join(
        f"{k} {up} suben y {down} bajan" for k, (up, down) in sorted(count.items())))
    return out


def _ints(line: str) -> list[int]:
    return [int(x) for x in re.findall(r"-?\d+", line.split("#", 1)[0])]


def supply_plan(ctx: BuildContext, assignment: dict[int, str], capitals: dict[str, int], states) -> None:
    """Reescribe map/supply_nodes.txt y map/railways.txt (ver arriba)."""
    spec = _spec(ctx).get("supply_nodes") or {}
    if not spec:
        return
    root = ctx.vanilla.root / "map"
    nodes_path, rails_path = root / "supply_nodes.txt", root / "railways.txt"
    if not nodes_path.exists() or not rails_path.exists():
        ctx.note("centros de suministro: el juego no tiene map/supply_nodes.txt o map/railways.txt; no se tocan")
        return
    node_lines = nodes_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    rail_lines = rails_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()

    # formato: nodos "nivel provincia"; vías "nivel cantidad p1 ... pn"
    parsed_nodes = [(i, _ints(l)) for i, l in enumerate(node_lines)]
    parsed_nodes = [(i, n) for i, n in parsed_nodes if n]
    if not parsed_nodes or any(len(n) != 2 for _, n in parsed_nodes):
        ctx.warn("centros de suministro: map/supply_nodes.txt no tiene el formato 'nivel provincia'; no se toca")
        return
    rails = [_ints(l) for l in rail_lines]
    rails = [r for r in rails if r]
    ok_rails = sum(1 for r in rails if len(r) >= 4 and r[1] == len(r) - 2)
    rails_ok = bool(rails) and ok_rails >= 0.9 * len(rails)
    if not rails_ok:
        ctx.warn("centros de suministro: map/railways.txt no tiene el formato esperado; no se agregan centros nuevos")
    rail_provs = {p for r in rails if len(r) >= 4 and r[1] == len(r) - 2 for p in r[2:]}

    kinds = {c.tag: faction_kind(c) for c in ctx.spec.countries}
    prov_state = {p: s.id for s in states for p in s.provinces}
    by_state = {s.id: s for s in states}
    cap_states = set(capitals.values())
    skip = set(spec.get("skip") or [])
    keep_vp = int(spec.get("keep_victory_points", 5))
    add_vp = int(spec.get("add_victory_points", 5))
    remove_in = set(spec.get("remove_in") or [])
    add_in = set(spec.get("add_in") or [])

    def is_city(st, vp_min: int) -> bool:
        return (st.category or "") in CITY or st.victory_points >= vp_min

    # 1. Sacar: regiones de anarquía sin ciudad, menos su capital
    removed: list[int] = []
    keep_idx = set()
    nodes_by_state: dict[int, list[int]] = defaultdict(list)
    for i, (level, prov) in parsed_nodes:
        sid = prov_state.get(prov)
        tag = assignment.get(sid)
        st = by_state.get(sid)
        if (tag and tag not in skip and kinds.get(tag) in remove_in and st is not None
                and sid not in cap_states and not is_city(st, keep_vp)):
            removed.append(prov)
            continue
        keep_idx.add(i)
        if sid is not None:
            nodes_by_state[sid].append(prov)

    # 2. Agregar: ciudades de meganaciones y satélites sin centro, con su vía
    added: list[int] = []
    new_rails: list[list[int]] = []
    if rails_ok and add_in:
        land = ctx.vanilla.land_provinces()
        neigh: dict[int, set[int]] = defaultdict(set)
        for a, b in ctx.vanilla.province_adjacency(ctx.out_root / ".cache"):
            neigh[a].add(b)
            neigh[b].add(a)
        max_len = int(spec.get("max_rail_length", 25))
        for sid, tag in sorted(assignment.items()):
            st = by_state.get(sid)
            if st is None or tag in skip or kinds.get(tag) not in add_in or nodes_by_state.get(sid):
                continue
            if not is_city(st, add_vp):
                continue
            hub = next((p for p in list(st.vp_provinces) + list(st.provinces) if p in land), None)
            if hub is None:
                continue
            if hub not in rail_provs:
                path = _rail_path(hub, rail_provs, neigh, land,
                                  lambda p: assignment.get(prov_state.get(p)) == tag, max_len)
                if not path:
                    continue
                new_rails.append(path)
                rail_provs.update(path)
            added.append(hub)
            nodes_by_state[sid].append(hub)

    level = parsed_nodes[0][1][0]
    out_nodes = [l for i, l in enumerate(node_lines) if i in keep_idx or not _ints(l)]
    out_nodes += [f"{level} {p}" for p in added]
    ctx.write_text("map/supply_nodes.txt", "\n".join(out_nodes) + "\n")
    if new_rails:
        ctx.write_text("map/railways.txt", "\n".join(rail_lines + [f"1 {len(r)} " + " ".join(map(str, r))
                                                                  for r in new_rails]) + "\n")
    ctx.data["supply_nodes"] = {"removed": removed, "added": added, "rails": new_rails}
    ctx.note(f"centros de suministro de 2100: {len(added)} nuevos en ciudades de meganaciones y satelites "
             f"({len(new_rails)} tramos de via), {len(removed)} sacados en regiones de anarquia sin ciudad; "
             f"quedan {len(out_nodes) - sum(1 for l in out_nodes if not _ints(l))}")


def _rail_path(start: int, rails: set[int], neigh, land: set[int], allowed, max_len: int) -> list[int] | None:
    """Camino más corto (provincias) de `start` a la red de vías, por tierra
    propia. Incluye las dos puntas."""
    prev = {start: None}
    queue = deque([(start, 0)])
    while queue:
        p, d = queue.popleft()
        if p in rails and p != start:
            path = [p]
            while prev[path[-1]] is not None:
                path.append(prev[path[-1]])
            return list(reversed(path))
        if d >= max_len:
            continue
        for q in sorted(neigh.get(p, ())):
            if q in prev or q not in land:
                continue
            if q not in rails and not allowed(q):
                continue
            prev[q] = p
            queue.append((q, d + 1))
    return None
