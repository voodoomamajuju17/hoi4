"""Estrategias de IA (spec/16_ai.yaml -> common/ai_strategy/meganations_ai.txt).

Cada plan es un bloque de ai_strategy de HOI4: a qué país se aplica
(`allowed`), cuándo se activa (`enable`), cuándo se abandona (`abort`) y una
lista de estrategias { type, target|id, value }.

Además se generan dos planes automáticos:
  - satélites: el señor protege a sus satélites y los satélites apoyan al
    señor (defaults.satellites);
  - rivales: las rivalidades de 04_diplomacy se antagonizan
    (defaults.rivals).

Los tipos se validan contra los que usa el juego instalado en
common/ai_strategy/: un tipo que el juego no conoce se descarta con aviso,
nunca se inventa. Una estrategia contra un país sin territorio se omite.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block
from .effects import render_conditions

SOURCE = "spec/16_ai.yaml"
# tipos cuyo `id` no es un país sino un rol o un tipo de equipo: se validan
# contra los ids que el juego usa con ese mismo tipo
ID_CHECKED = {"role_ratio", "unit_ratio", "equipment_production_factor", "equipment_variant_production_factor"}


def emit(ctx: BuildContext) -> None:
    spec = ctx.spec.raw.get("ai") or {}
    territory = ctx.data.get("territory") or {}
    alive = set(territory.values()) if territory else {c.tag for c in ctx.spec.countries}
    tags = {c.tag for c in ctx.spec.countries}
    known = ctx.vanilla.ai_strategy_types() if ctx.vanilla else None
    if known is None:
        ctx.warn("ia: los tipos de ai_strategy no se validaron (falta --vanilla-path o common/ai_strategy/).")
    known_ids = ctx.vanilla.ai_strategy_ids() if ctx.vanilla else None
    techs = set(ctx.vanilla.tech_tree()) if ctx.vanilla else None
    triggers_used: dict[str, str] = {}
    root = Block()
    dropped: set[str] = set()
    dropped_ids: set[str] = set()
    written = 0

    def add_plan(pid: str, country: str, strategies: list[dict], enable=None, abort=None) -> None:
        nonlocal written
        if country not in tags:
            raise SpecError(f"ia {pid}: '{country}' no es un pais del mod", where=SOURCE)
        if country not in alive:
            return
        lines = []
        targets = []
        for st in strategies:
            kind = st["type"]
            if known is not None and kind not in known:
                dropped.add(kind)
                continue
            target = st.get("target")
            if target is not None:
                if target not in tags:
                    raise SpecError(f"ia {pid}: '{target}' no es un pais del mod", where=SOURCE)
                if target not in alive:
                    continue
                targets.append(target)
            ident = target if target is not None else st.get("id")
            if target is None and ident is not None:
                # ids de rol/equipo: solo los que el juego usa con ese tipo;
                # research_tech: una tecnología del árbol instalado
                if kind == "research_tech":
                    if techs is not None and ident not in techs:
                        dropped_ids.add(f"{kind}:{ident}")
                        continue
                elif kind in ID_CHECKED and known_ids is not None and ident not in known_ids.get(kind, set()):
                    dropped_ids.add(f"{kind}:{ident}")
                    continue
            b = Block()
            b.add("type", kind)
            if ident is not None:
                b.add("id", ident)
            b.add("value", int(st["value"]))
            lines.append(b)
        if not lines:
            return
        plan = Block()
        plan.add("allowed", Block([("original_tag", country)]))
        triggers_used.setdefault("original_tag", pid)
        plan.add("enable", render_conditions(pid, enable, triggers_used, where=SOURCE) if enable
                 else Block([("always", True)]))
        if abort:
            plan.add("abort", render_conditions(pid, abort, triggers_used, where=SOURCE))
        elif targets:
            # se abandona cuando ya no queda ninguno de sus objetivos
            uniq = list(dict.fromkeys(targets))
            cond = ({"country_exists": uniq[0]} if len(uniq) == 1
                    else {"any": [{"country_exists": t} for t in uniq]})
            plan.add("abort", render_conditions(pid, {"not": cond}, triggers_used, where=SOURCE))
        else:
            plan.add("abort", Block([("always", False)]))
        for b in lines:
            plan.add("ai_strategy", b)
        root.add(f"MEGANATIONS_{pid}", plan)
        written += 1

    defaults = spec.get("defaults") or {}
    sat = defaults.get("satellites") or {}
    if sat:
        for c in ctx.spec.countries:
            if c.is_subject and c.overlord:
                add_plan(f"{c.overlord}_protege_{c.tag}", c.overlord,
                         [{"type": "protect", "target": c.tag, "value": sat.get("protect", 100)},
                          {"type": "befriend", "target": c.tag, "value": sat.get("befriend", 100)}])
                add_plan(f"{c.tag}_apoya_{c.overlord}", c.tag,
                         [{"type": "befriend", "target": c.overlord, "value": sat.get("befriend", 100)},
                          {"type": "support", "target": c.overlord, "value": sat.get("support", 100)}])
    riv = defaults.get("rivals") or {}
    if riv:
        for r in ctx.spec.raw["diplomacy"].get("rivalries", []) or []:
            a, b = r["between"]
            for x, y in ((a, b), (b, a)):
                add_plan(f"{x}_rivaliza_con_{y}", x,
                         [{"type": "antagonize", "target": y, "value": riv.get("antagonize", 30)}])

    _military_plans(ctx, spec.get("military") or {}, add_plan)

    for p in spec.get("plans", []) or []:
        add_plan(p["id"], p["country"], p["strategies"], p.get("enable"), p.get("abort"))

    if dropped_ids:
        ctx.warn(f"ia: ids que el juego no usa con ese tipo, se omiten: {', '.join(sorted(dropped_ids))}")
    if dropped:
        ctx.warn(f"ia: el juego no conoce estos tipos de ai_strategy, se omiten: {', '.join(sorted(dropped))}")
    if written:
        ctx.write_script("common/ai_strategy/meganations_ai.txt", root, source=SOURCE)
        ctx.note(f"ia: {written} planes de estrategia")
    ctx.verify_keys("triggers", triggers_used)


def _military_plans(ctx: BuildContext, mil: dict, add_plan) -> None:
    """IA militar (2026-09-27): qué construye cada potencia, qué investiga y
    cuánta industria pone en armas, en paz y en guerra.

      military:
        peace: [ {type, value} ]          todas las meganaciones
        war:   [ {type, value} ]          todas, mientras están en guerra
        research_value: 60                research_tech para las tecnologías que
                                          siguen en su especialidad (13_military)
        by_country: { TAG: [ {type, id, value} ] }
        anarchy: [ {type, value} ]        los países de la Anarquía
    """
    if not mil:
        return
    nxt = ctx.data.get("specialty_next") or {}
    per = mil.get("by_country") or {}
    for c in ctx.spec.countries:
        if c.is_major:
            strategies = list(mil.get("peace") or []) + list(per.get(c.tag) or [])
            value = mil.get("research_value")
            if value:
                strategies += [{"type": "research_tech", "id": t, "value": value} for t in nxt.get(c.tag, [])]
            add_plan(f"{c.tag}_militar", c.tag, strategies)
            if mil.get("war"):
                add_plan(f"{c.tag}_militar_en_guerra", c.tag, list(mil["war"]), enable={"at_war": True},
                         abort={"at_war": False})
        elif not c.is_subject and mil.get("anarchy"):
            add_plan(f"{c.tag}_defensa", c.tag, list(mil["anarchy"]))
