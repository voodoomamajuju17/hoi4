"""Balance económico de arranque (spec/15_balance.yaml).

Lo llama territory.py después del reparto y ANTES de reescribir los states:
devuelve cambios por state que _rewrite aplica.

  resource_delta[state][recurso]   transferencias (+ receptor, - donante)
  added_buildings[state][edificio] fábricas nuevas en slots libres

Reglas duras del usuario:
  - La Anarquía no dona ni recibe, ni recibe fábricas.
  - El total mundial de cada recurso es invariable: toda unidad que recibe
    un país sale de otro. Se verifica al final y el build falla si no cierra.
"""

from __future__ import annotations

from collections import defaultdict

from ..context import BuildContext
from ..errors import GenError
from ..vanilla import StateInfo


def plan(ctx: BuildContext, assignment: dict[int, str], capitals: dict[str, int]) -> tuple[dict, dict]:
    spec = ctx.spec.raw.get("balance") or {}
    by_state = {s.id: s for s in ctx.vanilla.states()}
    kinds = {c.tag: ("mega" if c.is_major else "sat" if c.is_subject else "anarchy") for c in ctx.spec.countries}
    resource_delta: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    added: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    if spec.get("resource_floor"):
        _resource_floor(ctx, spec["resource_floor"], assignment, capitals, by_state, kinds, resource_delta)
    if spec.get("industrialization"):
        _industrialize(ctx, spec["industrialization"], assignment, by_state, added)
    return resource_delta, added


# ---------------------------------------------------------------------------


def _resource_floor(ctx, spec, assignment, capitals, by_state, kinds, delta) -> None:
    floor = float(spec["per_meganation"])
    moved_total = 0
    for res in spec["resources"]:
        # Stock actual por país y por state (solo países del mod, sin Anarquía).
        amount: dict[int, float] = {}
        for sid, tag in assignment.items():
            if kinds.get(tag) in ("mega", "sat"):
                amount[sid] = (by_state[sid].resources or {}).get(res, 0.0)

        def country_total(tag: str) -> float:
            return sum(v + delta[sid][res] for sid, v in amount.items() if assignment[sid] == tag)

        for tag in sorted(t for t, k in kinds.items() if k == "mega"):
            need = floor - country_total(tag)
            cap = capitals.get(tag)
            if need <= 0 or cap is None:
                continue
            # Donantes: otros países del mod, el que más tiene primero.
            donors = sorted(
                {assignment[sid] for sid in amount if assignment[sid] != tag},
                key=lambda d: -country_total(d),
            )
            for donor in donors:
                if need <= 0:
                    break
                keep = floor if kinds[donor] == "mega" else 0.0
                spare = country_total(donor) - keep
                if spare <= 0:
                    continue
                states = sorted((sid for sid in amount if assignment[sid] == donor),
                                key=lambda sid: -(amount[sid] + delta[sid][res]))
                for sid in states:
                    if need <= 0 or spare <= 0:
                        break
                    avail = amount[sid] + delta[sid][res]
                    take = min(avail, need, spare)
                    if take <= 0:
                        continue
                    take = int(take)
                    if take == 0:
                        continue
                    delta[sid][res] -= take
                    delta[cap][res] += take
                    need -= take
                    spare -= take
                    moved_total += take
            if need > 0:
                ctx.warn(f"recursos: {tag} queda con {floor - need:.0f} de {res} (no hay mas excedente fuera de la Anarquia).")

        # Invariante: lo que se sacó es exactamente lo que se puso.
        net = sum(d[res] for d in delta.values())
        if abs(net) > 1e-9:
            raise GenError(f"el total mundial de {res} cambio en {net}: la transferencia no cierra",
                           where="15_balance.yaml")
    if moved_total:
        ctx.note(f"recursos: {moved_total} unidades transferidas para los minimos; total mundial intacto")


def _industrialize(ctx, spec, assignment, by_state, added) -> None:
    slots_by_cat = ctx.vanilla.state_category_slots()
    shared = ctx.vanilla.shared_slot_buildings()
    building = spec["building"]
    if not slots_by_cat:
        ctx.warn("industrializacion: no pude leer common/state_category/; se saltea.")
        return
    # Franja por tipo de país (2026-09-25): quien está por debajo del mínimo
    # recibe fábricas civiles; quien pasa el máximo pierde fábricas, primero
    # en sus states más industriales.
    band = spec.get("band") or {}
    kind = {c.tag: ("meganation" if c.is_major else "satellite" if c.is_subject else "anarchy")
            for c in ctx.spec.countries}
    targets = dict(spec.get("targets") or {})
    for tag, k in kind.items():
        if k not in band:
            continue
        low, high = band[k]
        owned = [by_state[sid] for sid, t in assignment.items() if t == tag and sid in by_state]
        if not owned:
            continue
        ic = sum(_ic(s) for s in owned)
        if ic < low:
            targets[tag] = max(int(low), int(targets.get(tag, 0)))
        elif ic > high:
            _deindustrialize(ctx, tag, owned, ic - int(high), added)
    for tag, target in targets.items():
        owned = [by_state[sid] for sid, t in assignment.items() if t == tag and sid in by_state]
        ic = sum(_ic(s) for s in owned)
        need = int(target) - ic
        if need <= 0:
            continue
        placed = 0
        for s in sorted(owned, key=lambda s: (-s.manpower, s.id)):
            free = _free_slots(s, slots_by_cat, shared) - sum(added[s.id].values())
            if free <= 0:
                continue
            n = min(free, need - placed)
            added[s.id][building] += n
            placed += n
            if placed >= need:
                break
        msg = f"industrializacion: {tag} {ic} -> {ic + placed} IC (+{placed} {building})"
        if placed < need:
            msg += f"; faltan {need - placed}: no hay mas slots libres"
        ctx.note(msg)


def _deindustrialize(ctx, tag, owned, excess, added) -> None:
    """Saca `excess` fábricas (civiles y militares, la que haya más en el
    state) empezando por los states más industriales."""
    removed = {"industrial_complex": 0, "arms_factory": 0}
    left = excess
    for s in sorted(owned, key=lambda s: (-_ic(s), s.id)):
        if left <= 0:
            break
        have = {k: (s.buildings or {}).get(k, 0) + added[s.id].get(k, 0) for k in removed}
        while left > 0 and (have["industrial_complex"] > 0 or have["arms_factory"] > 0):
            k = "industrial_complex" if have["industrial_complex"] >= have["arms_factory"] else "arms_factory"
            have[k] -= 1
            added[s.id][k] -= 1
            removed[k] += 1
            left -= 1
    total = sum(removed.values())
    ctx.note(f"industrializacion: {tag} baja {total} IC ({removed['industrial_complex']} civiles, "
             f"{removed['arms_factory']} militares) para quedar en la franja")


def _ic(s: StateInfo) -> int:
    b = s.buildings or {}
    return b.get("industrial_complex", 0) + b.get("arms_factory", 0)


def _free_slots(s: StateInfo, slots_by_cat: dict[str, int], shared: set[str]) -> int:
    total = slots_by_cat.get(s.category or "", 0)
    used = sum(v for k, v in (s.buildings or {}).items() if k in shared)
    return max(0, total - used)


def buildings_of(ctx: BuildContext, s: StateInfo) -> dict[str, int]:
    """Edificios del state después del balance (vanilla + industrialización)."""
    out = dict(s.buildings or {})
    for k, n in ((ctx.data.get("added_buildings") or {}).get(s.id) or {}).items():
        out[k] = out.get(k, 0) + n
    return out


def resources_of(ctx: BuildContext, s: StateInfo) -> dict[str, float]:
    """Recursos del state después de las transferencias."""
    out = dict(s.resources or {})
    for k, d in ((ctx.data.get("resource_delta") or {}).get(s.id) or {}).items():
        out[k] = out.get(k, 0.0) + d
    return {k: v for k, v in out.items() if v > 0}
