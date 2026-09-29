"""La Guerra en las Sombras: operaciones de inteligencia (spec/18_intelligence.yaml).

Produce:
  common/operations/meganations_operations.txt   (una por potencia objetivo)
  localisation: nombre y descripción de cada operación

Nada de la estructura se escribe de memoria: cada operación copia una del juego
instalado (sus fases, su riesgo y su equipo) y le cambia el nombre, el texto,
los requisitos y los efectos. Sin el juego instalado se usa una estructura de
respaldo y se avisa.

Alcance (operaciones del juego): ROOT es el país que la lanza, FROM el objetivo.
La defensa y la desescalada son decisiones (14_decisions.yaml).
"""

from __future__ import annotations

import copy

from ..context import BuildContext
from ..pdx import Block
from . import effects as effects_mod
from . import ideas as ideas_mod
from .effects import EffectContext, render_conditions, render_effects, scripted_effect_ids

SOURCE = "spec/18_intelligence.yaml"
LOC_FILE = "meganations_intelligence"

# Operaciones del juego que sirven de molde, en orden de preferencia. Las que
# eligen una región o dan fichas propias no sirven: la nuestra apunta a un país.
PREFERRED_TEMPLATES = ("operation_steal_tech", "operation_infiltrate_civilian_government",
                       "operation_infiltrate_armed_forces_army", "operation_boost_ideology")
AVOID_KEYS = ("selection_target_state", "selection_target", "awarded_tokens", "requirements")
# Lo que la operación del molde conserva (además de sus valores sueltos).
KEEP_BLOCKS = ("phases", "equipment")
# Lo que ponemos nosotros (se saca del molde).
OURS = ("is_captured_cipher", "is_staged_coup", "on_start", "name", "desc", "priority", "days", "network_strength", "operatives", "visible", "available",
        "outcome_execute", "outcome_potential", "outcome_modifiers", "ai_will_do", "target_weight",
        "will_lead_to_war_with")


_COMMON_KEYS = {"name", "desc", "icon", "map_icon", "priority", "days", "network_strength", "operatives",
                "visible", "available", "outcome_execute", "outcome_potential", "ai_will_do", "phases", "equipment"}


def _diagnose(ctx: BuildContext, ops: dict[str, Block]) -> None:
    """Para el reporte: las operaciones del juego y sus claves propias, para
    elegir el molde con datos (18_intelligence.yaml -> template)."""
    for name in sorted(ops):
        extra = [k for k in ops[name].keys() if k not in _COMMON_KEYS]
        ctx.note(f"operacion del juego: {name} ({len(ops[name])} claves): {', '.join(extra) or '-'}")


def _template(ctx: BuildContext) -> tuple[str, Block]:
    ops = ctx.vanilla.operations() if ctx.vanilla else {}
    if ops:
        _diagnose(ctx, ops)
    wanted = (ctx.spec.raw.get("intelligence") or {}).get("template")
    if wanted and wanted in ops:
        return wanted, ops[wanted]
    if wanted:
        ctx.warn(f"operaciones de inteligencia: el molde '{wanted}' no existe en este juego; elijo otro.")
    usable = {n: b for n, b in ops.items() if "phases" in b and not any(k in b for k in AVOID_KEYS)
              and str(b.get("will_lead_to_war_with") or "no") != "yes"}
    for name in PREFERRED_TEMPLATES:
        if name in usable:
            return name, usable[name]
    if usable:
        name = min(usable, key=lambda n: (len(usable[n]), n))
        return name, usable[name]
    if ops:
        name = next(n for n in sorted(ops) if "phases" in ops[n]) if any("phases" in b for b in ops.values()) else None
        if name:
            return name, ops[name]
    return "", Block()


def _fallback(ctx: BuildContext) -> Block:
    """Sin el juego instalado: una fase propia y los valores mínimos."""
    phase = Block([("name", "mn_fase_sombras"), ("desc", "mn_fase_sombras_desc"),
                   ("icon", "GFX_operation_phase_icon_infiltration"),
                   ("picture", "GFX_operation_phase_picture_infiltration")])
    ctx.write_script("common/operation_phases/meganations_phases.txt", Block([("mn_fase_sombras", phase)]),
                     source=SOURCE)
    ctx.loc.define_and_reference("mn_fase_sombras", en="Into the Shadows", es="En las Sombras",
                                 file=LOC_FILE, origin="operations")
    ctx.loc.define_and_reference("mn_fase_sombras_desc", en="Our agents move in.", es="Nuestros agentes entran.",
                                 file=LOC_FILE, origin="operations")
    return Block([("icon", "GFX_operations_steal_tech"), ("return_on_complete", True),
                  ("phases", Block([(None, Block([("mn_fase_sombras", Block([("base", 1)]))]))]))])


def _sub(value, mapping: dict[str, str]):
    if isinstance(value, str):
        for k, v in mapping.items():
            value = value.replace("{" + k + "}", v)
        return value
    if isinstance(value, list):
        return [_sub(v, mapping) for v in value]
    if isinstance(value, dict):
        return {k: _sub(v, mapping) for k, v in value.items()}
    return value


def _describe(items: list) -> tuple[str, str]:
    """"Saturación de las cubas +12, ..." con los nombres de 14_decisions -> variable_names."""
    en, es = [], []
    for it in items:
        name = effects_mod._VAR_NAMES.get(it.get("var")) if it.get("effect") == "add_variable" else None
        if not name or name.get("hidden"):
            continue
        v = it["value"]
        en.append(f"{name['english']} {v:+g}")
        es.append(f"{name['spanish']} {v:+g}")
    return ", ".join(en), ", ".join(es)


def emit(ctx: BuildContext) -> None:
    spec = ctx.spec.raw.get("intelligence")
    if not spec:
        return
    _emit(ctx, spec)
    if ctx.vanilla is not None:
        _agency_upgrades(ctx, spec.get("agency_upgrades") or [])
    effects_mod.flush_tooltips(ctx)


def _emit(ctx: BuildContext, spec: dict) -> None:
    effects_mod.use_variable_names(ctx.spec.raw)
    from . import events as events_mod
    megas = spec["megas"]
    for t in megas:
        ctx.spec.country(t)
    effect_ctx = EffectContext(
        ideas_mod.all_idea_ids(ctx), {c.tag for c in ctx.spec.countries}, warn=ctx.warn,
        events=events_mod.all_event_ids(ctx), scripted=scripted_effect_ids(ctx.spec.raw),
    )
    triggers_used = effect_ctx.triggers_used
    effects_used: dict[str, str] = {}
    rivals: dict[str, set[str]] = {t: set() for t in megas}
    for a, b in spec.get("rivals") or []:
        rivals[a].add(b)
        rivals[b].add(a)
    disc = spec["discovery"]
    ev = spec["events"]

    tpl_name, tpl = _template(ctx)
    if tpl_name:
        ctx.note(f"operaciones de inteligencia: estructura copiada de '{tpl_name}' del juego")
    else:
        ctx.warn("operaciones de inteligencia: no encontre operaciones del juego (common/operations); "
                 "se usa una estructura de respaldo sin probar.")
        tpl = _fallback(ctx)
    base = Block([(k, v) for k, v in tpl.entries
                  if k not in OURS and (not isinstance(v, Block) or k in KEEP_BLOCKS)])

    op_icons = _operation_icons(ctx, spec, tpl)
    out = Block()
    for t in megas:
        country = ctx.spec.country(t)
        var = f"MN_inf_{t}"
        for level, op in enumerate(spec["operations"], start=1):
            oid = f"mn_op_{op['id']}_{t}"
            where = f"18_intelligence.yaml:{op['id']}"
            b = Block()
            b.add("name", oid)
            b.add("desc", f"{oid}_desc")
            b.entries.extend(copy.deepcopy(base.entries))
            own_icon = op_icons.get(op["id"])
            if own_icon:
                b.entries = [(k, own_icon if k == "icon" else v) for k, v in b.entries]
            b.add("priority", 10 + level)
            b.add("days", int(op["days"]))
            b.add("network_strength", int(op["network_strength"]))
            b.add("operatives", int(op["operatives"]))

            attackers = [a for a in megas if a != t]
            visible = Block([("FROM", Block([("tag", t)])),
                             ("OR", Block([("tag", a) for a in attackers]))])
            b.add("visible", visible)
            avail = {"not_flag": f"MN_pacto_{t}"}
            if op["min"]:
                avail["variable_at_least"] = {"var": var, "value": op["min"]}
            b.add("available", render_conditions(oid, avail, triggers_used, where=where))

            gain = int(op["gain"])
            discovered = [{"effect": "add_variable", "var": var, "value": -int(disc["penalty"])},
                          {"effect": "add_political_power", "value": -25},
                          {"effect": "event", "id": ev["discovered"], "target": t}]

            def roll(pct):
                return {"effect": "random", "options": [{"weight": pct, "effects": discovered},
                                                        {"weight": 100 - pct, "effects": []}]}
            half = gain // 2 if gain > 0 else gain
            items = [{"effect": "if", "when": {"flag": f"MN_vigilado_por_{t}"},
                      "then": [{"effect": "add_variable", "var": var, "value": half}, roll(disc["shielded"])],
                      "else": [{"effect": "add_variable", "var": var, "value": gain}, roll(disc["open"])]},
                     {"effect": "clamp", "var": var, "min": 0, "max": 100}]
            for a in attackers:
                eff = _sub(op.get("attacker") or [], {"A": a, "T": t})
                if eff:
                    items.append({"effect": "if", "when": {"tag": a}, "then": eff})
            execute = render_effects(oid, items, effect_ctx, effects_used, where=where)

            hits: list = []
            for item in op.get("target") or []:
                if item == "mechanic":
                    hits = (spec.get("mechanic_hits") or {}).get(t) or []
                elif item == "rebellion":
                    hits = (spec.get("rebellion_hits") or {}).get(t) or []
            target: list = []
            for item in op.get("target") or []:
                if item == "mechanic":
                    target.extend((spec.get("mechanic_hits") or {}).get(t) or [])
                elif item == "rebellion":
                    target.extend((spec.get("rebellion_hits") or {}).get(t) or [])
                    target.append({"effect": "event", "id": ev["uprising"]})
                else:
                    target.append(_sub(item, {"T": t}))
            if target:
                execute.add("FROM", render_effects(oid, target, effect_ctx, effects_used, where=where))
            b.add("outcome_execute", execute)

            ai = Block([("factor", 1)])
            if rivals[t]:
                ai.add("modifier", Block([("factor", 3), ("OR", Block([("tag", r) for r in sorted(rivals[t])]))]))
            ai.add("modifier", Block([("factor", 3), ("has_war_with", "FROM")]))
            b.add("ai_will_do", ai)
            for k in ("tag", "has_war_with"):
                triggers_used.setdefault(k, oid)
            out.add(oid, b)

            en_t, es_t = country.name_en, country.name_es
            need_en = f"Requires infiltration {op['min']} in {en_t}. " if op["min"] else ""
            need_es = f"Pide infiltración {op['min']} en {es_t}. " if op["min"] else ""
            if gain > 0:
                g_en = f"Infiltration +{gain} (+{half} if they are guarding against us)."
                g_es = f"Infiltración +{gain} (+{half} si se blindaron contra nosotros)."
            else:
                g_en, g_es = f"Spends {-gain} infiltration.", f"Gasta {-gain} de infiltración."
            risk_en = f"Risk of being discovered: {disc['open']}% ({disc['shielded']}% if they guard against us)."
            risk_es = f"Riesgo de que nos descubran: {disc['open']}% ({disc['shielded']}% si se blindaron contra nosotros)."
            hit_en, hit_es = _describe(hits)
            if hit_en:
                risk_en = f"In {en_t}: {hit_en}.\\n{risk_en}"
                risk_es = f"En {es_t}: {hit_es}.\\n{risk_es}"
            now_en = f"Our infiltration in {en_t}: [?{var}]"
            now_es = f"Nuestra infiltración en {es_t}: [?{var}]"
            ctx.loc.define_and_reference(oid, en=op["name"]["english"], es=op["name"]["spanish"],
                                         file=LOC_FILE, origin="operations")
            ctx.loc.define_and_reference(
                f"{oid}_desc",
                en=f"{op['desc']['english']}\\n\\n{need_en}{g_en}\\n{risk_en}\\n\\n{now_en}",
                es=f"{op['desc']['spanish']}\\n\\n{need_es}{g_es}\\n{risk_es}\\n\\n{now_es}",
                file=LOC_FILE, origin="operations")

    ctx.write_script("common/operations/meganations_operations.txt", out, source=SOURCE)
    ctx.verify_keys("effects", effects_used)
    ctx.verify_keys("triggers", triggers_used)
    ctx.note(f"operaciones de inteligencia: {len(out)} (6 por meganación objetivo)")



def _operation_icons(ctx: BuildContext, spec: dict, tpl: Block) -> dict[str, str]:
    """assets/intelligence/ops/<id>.dds -> sprite propio, al tamaño del ícono del molde."""
    from .menu import _dims, _resize, _texture_dims
    from ..pdx import Quoted
    repo = ctx.spec.root.parent
    size = (0, 0)
    if ctx.vanilla is not None:
        tex = ctx.vanilla.gfx_textures().get(str(tpl.get("icon") or ""))
        if tex:
            size = _texture_dims(ctx, tex)
    sprites = Block()
    out: dict[str, str] = {}
    for op in spec["operations"]:
        src = repo / "assets" / "intelligence" / "ops" / f"{op['id']}.dds"
        if not src.exists():
            continue
        data = src.read_bytes()
        w, h = _dims(data)
        if size[0] and size[1] and (w, h) != size:
            data = _resize(data, w, h, size[0], size[1])
        rel = f"gfx/interface/operations/meganations/{op['id']}.dds"
        dest = ctx.mod_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        ctx.track(dest)
        name = f"GFX_mn_op_{op['id']}"
        sprites.add("spriteType", Block([("name", Quoted(name)), ("texturefile", Quoted(rel))]))
        out[op["id"]] = name
    if sprites.entries:
        ctx.write_script("interface/meganations_operations.gfx", Block([("spriteTypes", sprites)]), source=SOURCE)
        ctx.note(f"operaciones de inteligencia: {len(out)} iconos propios")
    return out


def _agency_upgrades(ctx: BuildContext, items: list[dict]) -> None:
    """Nombres de 2100 para las mejoras de la agencia (se buscan por el texto que
    muestra el juego en español) y, si llegó el dibujo, su ícono."""
    import re
    from .menu import _dims, _resize, _texture_dims
    repo = ctx.spec.root.parent
    files = sorted((ctx.vanilla.root / "common" / "intelligence_agency_upgrades").glob("*.txt"))
    texts = []
    for f in files:
        try:
            texts.append(f.read_text(encoding="utf-8-sig", errors="replace"))
        except OSError:
            continue
    blob = "\n".join(texts)
    textures = ctx.vanilla.gfx_textures()
    renamed, icons, missing = 0, 0, []
    for it in items:
        keys = ctx.vanilla.loc_keys_with_text_in(it["was"], "spanish")
        # solo las claves de la agencia (el mismo texto puede estar en otro lado)
        keys = [k for k in keys if re.search(r"(?i)upgrade|agency|branch|intel|crypt|operative|defen", k)] or keys[:1]
        if not keys:
            missing.append(it["was"])
            continue
        for k in keys:
            ctx.loc.define_and_reference(k, en=it["english"], es=it["spanish"],
                                         file="replace/meganations_intelligence", origin=f"agency:{it['id']}")
        renamed += 1
        # ícono: la primera referencia GFX_ cerca de la clave en common/intelligence_agency_upgrades
        sprite = None
        for k in keys:
            m = re.search(rf"\b{re.escape(k)}\b", blob)
            if m:
                g = re.search(r"GFX_[A-Za-z0-9_]+", blob[m.end():m.end() + 800])
                if g:
                    sprite = g.group(0)
                    break
        own = repo / "assets" / "agency" / f"{it['id']}.dds"
        tex = textures.get(sprite or "")
        if sprite is None or tex is None:
            ctx.note(f"agencia: '{it['was']}' -> claves {', '.join(keys[:3])}; icono sin ubicar")
            continue
        if not own.exists():
            continue
        data = own.read_bytes()
        w, h = _dims(data)
        vw, vh = _texture_dims(ctx, tex)
        if vw and vh and (w, h) != (vw, vh):
            data = _resize(data, w, h, vw, vh)
        dest = ctx.mod_root / tex
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        ctx.track(dest)
        icons += 1
    ctx.note(f"agencia: {renamed} mejoras con nombre de 2100, {icons} iconos propios"
             + (f"; no encontre: {', '.join(missing)}" if missing else ""))
