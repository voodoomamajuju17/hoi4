"""Paneles de decisiones (spec/14_decisions.yaml).

Produce:
  common/decisions/categories/meganations_categories.txt
  common/decisions/meganations_decisions.txt
  localisation: <categoria>, <categoria>_desc, <decision>, <decision>_desc

Nada se escribe de memoria:
  - los campos que usamos (cost, days_re_enable, complete_effect...) se
    verifican contra los que usan las decisiones y categorías vanilla;
  - los íconos se eligen entre los que usan las decisiones vanilla
    (icon_prefer en orden, si no el primero disponible).
Sin --vanilla-path se emite con el primer ícono preferido y se avisa.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, parse_file
from . import ideas as ideas_mod
from . import effects as effects_mod
from .effects import EffectContext, scripted_effect_ids, render_conditions, render_effects

SOURCE = "spec/14_decisions.yaml"
LOC_FILE = "meganations_decisions"
DECISION_FIELDS = ("icon", "cost", "days_re_enable", "available", "complete_effect", "ai_will_do")
# Campos opcionales: se validan solo si algún spec los usa.
OPTIONAL_FIELDS = ("visible", "fire_only_once")
CATEGORY_FIELDS = ("icon", "allowed")


def emit(ctx: BuildContext) -> None:
    effects_mod.use_states(ctx.data.get("state_ids_by_name"))
    categories = (ctx.spec.raw.get("decisions") or {}).get("categories") or []
    scripted = (ctx.spec.raw.get("decisions") or {}).get("scripted_effects") or []
    if not categories and not scripted:
        return
    vanilla = _vanilla(ctx)
    known_ideas = ideas_mod.all_idea_ids(ctx)
    effects_used: dict[str, str] = {}
    from . import events as events_mod
    from .focus_trees import character_ids
    effect_ctx = EffectContext(
        known_ideas, {c.tag for c in ctx.spec.countries},
        ctx.vanilla.building_keys() if ctx.vanilla else None,
        ctx.vanilla.wargoal_types() if ctx.vanilla else None,
        warn=ctx.warn, characters=character_ids(ctx), events=events_mod.all_event_ids(ctx),
        scripted=scripted_effect_ids(ctx.spec.raw),
        tech_categories=ctx.vanilla.tech_categories() if ctx.vanilla else None,
        shared_slots=ctx.vanilla.shared_slot_buildings() if ctx.vanilla else None,
    )
    triggers_used = effect_ctx.triggers_used
    used_optional: set[str] = set()

    cats = Block()
    decs = Block()
    for cat in categories:
        cid = cat["id"]
        tag = cat["country"]
        ctx.spec.country(tag)
        cb = Block()
        cb.add("icon", _icon(ctx, vanilla["category_icons"], cat.get("icon_prefer", [])))
        allowed = Block()
        allowed.add("original_tag", tag)
        cb.add("allowed", allowed)
        triggers_used.setdefault("original_tag", cid)
        cats.add(ctx.loc.reference(cid, f"decisions:{cid}"), cb)
        _loc(ctx, cid, cat["name"], define_only=True)
        _loc(ctx, f"{cid}_desc", cat["desc"])

        body = Block()
        # after_effects: se aplican al final de CADA decisión del panel (ej.
        # recalcular la Sinergia del Directorio después de cada contrato).
        after = cat.get("after_effects") or []
        for d in cat.get("decisions", []) or []:
            did = d["id"]
            db = Block()
            db.add("icon", _icon(ctx, vanilla["decision_icons"], d.get("icon_prefer", [])))
            db.add("cost", int(d.get("cost", 0)))
            if d.get("cooldown_days"):
                db.add("days_re_enable", int(d["cooldown_days"]))
            if d.get("visible"):
                db.add("visible", render_conditions(did, d["visible"], triggers_used, where=SOURCE))
                used_optional.add("visible")
            if d.get("fire_only_once"):
                db.add("fire_only_once", True)
                used_optional.add("fire_only_once")
            if d.get("available"):
                db.add("available", render_conditions(did, d["available"], triggers_used, where=SOURCE))
            db.add("complete_effect", render_effects(did, list(d["effects"]) + list(after), effect_ctx,
                                                     effects_used, where=SOURCE))
            ai = Block()
            ai_spec = d.get("ai") or {}
            ai.add("factor", ai_spec.get("factor", int(d.get("ai_factor", 1))))
            # peso condicional: la IA decide según el estado de la mecánica
            for m in ai_spec.get("modifiers") or []:
                mod = Block()
                mod.add("factor", m["factor"])
                mod.entries.extend(render_conditions(did, m["when"], triggers_used, where=SOURCE).entries)
                ai.add("modifier", mod)
            db.add("ai_will_do", ai)
            body.add(ctx.loc.reference(did, f"decisions:{did}"), db)
            _loc(ctx, did, d["name"], define_only=True)
            _loc(ctx, f"{did}_desc", d["desc"])
        decs.add(cid, body)

    if scripted:
        se = Block()
        for e in scripted:
            se.add(e["id"], render_effects(e["id"], e["effects"], effect_ctx, effects_used, where=SOURCE))
        ctx.write_script("common/scripted_effects/meganations_effects.txt", se, source=SOURCE)
    _check_fields(vanilla, ctx, used_optional)
    ctx.write_script("common/decisions/categories/meganations_categories.txt", cats, source=SOURCE)
    ctx.write_script("common/decisions/meganations_decisions.txt", decs, source=SOURCE)
    ctx.verify_keys("effects", effects_used)
    ctx.verify_keys("triggers", triggers_used)
    ctx.note(f"decisiones: {sum(len(c.get('decisions', [])) for c in categories)} en {len(categories)} panel(es)")


def _vanilla(ctx: BuildContext) -> dict:
    out = {"decision_icons": [], "category_icons": [], "decision_fields": set(), "category_fields": set()}
    if ctx.vanilla is None:
        return out
    root = ctx.vanilla.root / "common" / "decisions"
    for path in sorted(root.glob("categories/*.txt")):
        try:
            block = parse_file(path)
        except ValueError:
            continue
        for _, cat in block.entries:
            if isinstance(cat, Block):
                out["category_fields"].update(cat.keys())
                icon = cat.get("icon")
                if icon is not None and not isinstance(icon, Block):
                    out["category_icons"].append(str(getattr(icon, "text", icon)))
    for path in sorted(root.glob("*.txt")):
        try:
            block = parse_file(path)
        except ValueError:
            continue
        for _, cat in block.entries:
            if not isinstance(cat, Block):
                continue
            for _, dec in cat.entries:
                if isinstance(dec, Block):
                    out["decision_fields"].update(dec.keys())
                    icon = dec.get("icon")
                    if icon is not None and not isinstance(icon, Block):
                        out["decision_icons"].append(str(getattr(icon, "text", icon)))
    return out


def _icon(ctx: BuildContext, available: list[str], prefer: list[str]) -> str:
    if not available:
        if ctx.vanilla is not None:
            ctx.warn("decisiones: no encontre iconos vanilla; uso el preferido sin verificar.")
        return prefer[0] if prefer else "generic_industry"
    for icon in prefer:
        if icon in available:
            return icon
    return available[0]


def _check_fields(vanilla: dict, ctx: BuildContext, used_optional: set[str] = frozenset()) -> None:
    if ctx.vanilla is None:
        return
    decision_fields = DECISION_FIELDS + tuple(sorted(used_optional))
    for fields, known, what in ((decision_fields, vanilla["decision_fields"], "decision"),
                                (CATEGORY_FIELDS, vanilla["category_fields"], "categoria")):
        if not known:
            continue
        missing = [f for f in fields if f not in known]
        if missing:
            raise SpecError(f"ninguna {what} vanilla usa {missing}: el formato cambio en esta version",
                            where=SOURCE)


def _loc(ctx: BuildContext, key: str, texts: dict, *, define_only: bool = False) -> None:
    if define_only:
        ctx.loc.define(key, en=texts["english"], es=texts["spanish"], file=LOC_FILE, origin=f"decisions:{key}")
    else:
        ctx.loc.define_and_reference(key, en=texts["english"], es=texts["spanish"],
                                     file=LOC_FILE, origin=f"decisions:{key}")
