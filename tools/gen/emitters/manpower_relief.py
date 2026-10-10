"""Repoblación de las meganaciones con menos gente (spec/15_balance.yaml -> manpower_relief).

Pedido del usuario (2026-10-10): "En las regiones con menos manpower, agregá
o bien una buena inyección de gente o crecimiento o aumento de población
reclutable o una combinación, con algún o algunos focus (usar los que ya
existen)".

Se mide al armar el mod, con la población del reparto ya comprimida
(territory.py -> ctx.data["manpower_new"]): la meganación con menos de
`below` x la mediana de las meganaciones recibe, en dos focos suyos que ya
existen, mano de obra en el acto y un espíritu permanente de crecimiento y
población reclutable; con menos de `strong_below`, la versión fuerte. Los
focos reciben los efectos al final de su recompensa (no se toca el spec en
disco). Corre después de territory y antes de focus_trees.
"""

from __future__ import annotations

from collections import defaultdict

from ..context import BuildContext
from ..errors import SpecError

SOURCE = "spec/15_balance.yaml -> manpower_relief"
# las pruebas fuerzan los umbrales (el mapa de prueba tiene poblaciones de juguete)
FORCE: dict | None = None


def emit(ctx: BuildContext) -> None:
    spec = (ctx.spec.raw.get("balance") or {}).get("manpower_relief") or {}
    if spec and FORCE:
        spec = {**spec, **FORCE}
    assignment = ctx.data.get("territory")
    if not spec or not assignment or ctx.vanilla is None:
        return
    pop = ctx.data.get("manpower_new") or {}
    by_state = {s.id: s for s in ctx.vanilla.states()}
    majors = [c.tag for c in ctx.spec.countries if c.is_major]
    totals: dict[str, int] = defaultdict(int)
    for sid, tag in assignment.items():
        if tag in majors and sid in by_state:
            totals[tag] += pop.get(sid, by_state[sid].manpower)
    vals = sorted(v for v in totals.values() if v > 0)
    if not vals:
        return
    median = vals[len(vals) // 2]
    trees = ctx.spec.raw["focus_trees"]["trees"]
    lines = []
    for tag in majors:
        total = totals.get(tag, 0)
        if total <= 0:
            continue
        ratio = total / median
        if ratio >= float(spec.get("below", 0.8)):
            continue
        tier = "strong" if ratio < float(spec.get("strong_below", 0.5)) else "normal"
        ids = (spec.get("focuses") or {}).get(tag) or []
        steps = [spec[tier]["first"], spec[tier]["second"]]
        focus_by_id = {f["id"]: f for b in trees[tag]["branches"] for f in b["focuses"]}
        for short, step in zip(ids, steps):
            fid = f"{tag}_{short}"
            focus = focus_by_id.get(fid)
            if focus is None:
                raise SpecError(f"manpower_relief: el foco '{fid}' no existe", where=SOURCE)
            focus["reward"] = list(focus.get("reward") or []) + [
                {"effect": "add_manpower", "value": int(step["manpower"])},
                {"effect": "dynamic_modifier", "id": step["modifier"]},
            ]
        lines.append(f"{tag} {total / 1e6:.1f}M ({ratio:.0%} de la mediana, "
                     f"{'fuerte' if tier == 'strong' else 'normal'}: {', '.join(ids)})")
    ctx.data["manpower_relief"] = lines
    ctx.note("repoblacion: mediana de las meganaciones " + f"{median / 1e6:.1f}M; "
             + ("; ".join(lines) if lines else "nadie por debajo"))
