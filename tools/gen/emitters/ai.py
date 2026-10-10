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
from ..pdx import Block, Compare
from .effects import render_conditions

SOURCE = "spec/16_ai.yaml"
# tipos cuyo `id` no es un país sino un rol o un tipo de equipo: se validan
# contra los ids que el juego usa con ese mismo tipo
ID_CHECKED = {"role_ratio", "unit_ratio", "equipment_production_factor", "equipment_variant_production_factor"}
# tipos cuyo `id` es una tecnología: se validan contra el árbol instalado
TECH_IDS = {"research_tech", "research_weight_factor"}
# tipos documentados (hoi4.paradoxwikis.com/AI_modding) que el juego base puede
# no usar en sus propios planes: se aceptan aunque no aparezcan en common/ai_strategy/.
# research_weight_factor = { id = <tecnología> value = <% de más> } (2026-09-30:
# "la HSN no investiga barcos"; research_tech no existe, éste sí).
DOCUMENTED = {"research_weight_factor"}


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
            if known is not None and kind not in known and kind not in DOCUMENTED:
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
                # research_weight_factor: una tecnología del árbol instalado
                if kind in TECH_IDS:
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
    # Nadie se alía con la Anarquía ni la garantiza (2026-09-29: una
    # partida mostró a los Caudillos del Amazonas dentro de la facción de la FCU).
    pariah = defaults.get("anarchy_pariah") or {}
    if pariah:
        anarchies = [c.tag for c in ctx.spec.countries if not c.is_major and not c.is_subject]
        for c in ctx.spec.countries:
            if c.tag in anarchies:
                continue
            add_plan(f"{c.tag}_no_se_alia_con_la_anarquia", c.tag,
                     [{"type": kind, "target": a, "value": int(v)} for a in anarchies for kind, v in pariah.items()])
    riv = defaults.get("rivals") or {}
    if riv:
        for r in ctx.spec.raw["diplomacy"].get("rivalries", []) or []:
            a, b = r["between"]
            for x, y in ((a, b), (b, a)):
                add_plan(f"{x}_rivaliza_con_{y}", x,
                         [{"type": "antagonize", "target": y, "value": riv.get("antagonize", 30)}])

    _military_plans(ctx, spec.get("military") or {}, add_plan)
    _anarchy_war_plans(ctx, spec.get("anarchy_wars") or {}, add_plan)
    _destiny_war_plans(ctx, spec.get("destiny_wars") or {}, add_plan)
    _coalition_plans(ctx, spec.get("coalition") or {}, add_plan)

    for p in spec.get("plans", []) or []:
        add_plan(p["id"], p["country"], p["strategies"], p.get("enable"), p.get("abort"))
    # unidades únicas (20_unique_units.yaml): se activan con su desbloqueo
    for p in ctx.data.get("unique_ai_plans") or []:
        add_plan(p["id"], p["country"], p["strategies"], p.get("enable"), p.get("abort"))

    if dropped_ids:
        ctx.warn(f"ia: ids que el juego no usa con ese tipo, se omiten: {', '.join(sorted(dropped_ids))}")
    if dropped:
        ctx.warn(f"ia: el juego no conoce estos tipos de ai_strategy, se omiten: {', '.join(sorted(dropped))}")
    if written:
        ctx.write_script("common/ai_strategy/meganations_ai.txt", root, source=SOURCE)
        ctx.note(f"ia: {written} planes de estrategia")
    ctx.verify_keys("triggers", triggers_used)
    _naval_cap(ctx, spec.get("naval_cap") or {})


NAVAL_CAP = "MEGANATIONS_tope_naval"
NAVAL_CAP_FILE = "common/dynamic_modifiers/meganations_tope_naval.txt"
NAVAL_CAP_ON_ACTIONS = "common/on_actions/05_meganations_tope_naval.txt"


def _naval_cap(ctx: BuildContext, cap: dict) -> None:
    """Tope de flota de la IA (2026-10-02: el EFE con 710 barcos en 2106).

    Un modificador dinámico que se da a todos los países al arrancar y solo
    pesa cuando el país es IA y tiene más barcos que su tope
    (has_navy_size): sus astilleros pierden la producción hasta que baje.

      naval_cap: {default: 25, by_country: {TAG: n}, modifiers: {...}, name: {english, spanish}}
    """
    if not cap:
        return
    mods = cap.get("modifiers") or {}
    if not mods:
        raise SpecError("naval_cap: sin modificadores", where=SOURCE)
    if ctx.vanilla is not None and ctx.vanilla.is_documented("triggers", "has_navy_size") is False:
        ctx.warn("ia: el juego no tiene has_navy_size; no se escribe el tope de flota de la IA.")
        return
    tags = {c.tag for c in ctx.spec.countries}
    per = {t: int(n) for t, n in (cap.get("by_country") or {}).items()}
    unknown = sorted(set(per) - tags)
    if unknown:
        raise SpecError(f"naval_cap.by_country: paises que no existen: {', '.join(unknown)}", where=SOURCE)
    default = int(cap.get("default", 25))

    def navy_over(n: int) -> Block:
        return Block([("size", Compare(">", n))])

    over_cap = Block()
    for t, n in sorted(per.items()):
        over_cap.add("AND", Block([("original_tag", t), ("has_navy_size", navy_over(n))]))
    rest = Block([("NOT", Block([("original_tag", t) for t in sorted(per)]))]) if per else Block()
    rest.add("has_navy_size", navy_over(default))
    over_cap.add("AND", rest)
    body = Block([("enable", Block([("is_ai", True), ("OR", over_cap)]))])
    for key, value in mods.items():
        body.add(key, float(value))
    name = cap.get("name") or {}
    ref = ctx.loc.define_and_reference(NAVAL_CAP, en=name.get("english", "Fleet at Capacity"),
                                       es=name.get("spanish", "Flota completa"), file="meganations_ai",
                                       origin="naval_cap")
    ctx.write_script(NAVAL_CAP_FILE, Block([(ref, body)]), source=SOURCE)
    effect = Block([("every_country", Block([("add_dynamic_modifier", Block([("modifier", NAVAL_CAP)]))]))])
    root = Block([("on_actions", Block([("on_startup", Block([("effect", effect)]))]))])
    ctx.write_script(NAVAL_CAP_ON_ACTIONS, root, source=SOURCE)
    ctx.verify_keys("modifiers", {k: "naval_cap" for k in mods})
    ctx.verify_keys("effects", {"add_dynamic_modifier": "naval_cap", "every_country": "naval_cap"})
    ctx.verify_keys("triggers", {"has_navy_size": "naval_cap", "is_ai": "naval_cap", "original_tag": "naval_cap"})
    caps = ", ".join(f"{t} {n}" for t, n in sorted(per.items()))
    ctx.note(f"ia: tope de flota para la IA ({caps}; el resto {default}): pasado el tope, astilleros {mods}")


def _military_plans(ctx: BuildContext, mil: dict, add_plan) -> None:
    """IA militar (2026-09-27): qué construye cada potencia, qué investiga y
    cuánta industria pone en armas, en paz y en guerra.

      military:
        peace: [ {type, value} ]          todas las meganaciones
        war:   [ {type, value} ]          todas, mientras están en guerra
        research_value: 60                (lo usa research.py: ai_will_do de las
                                          tecnologías que siguen en su especialidad)
        by_country: { TAG: [ {type, id, value} ] }
        anarchy: [ {type, value} ]        los países de la Anarquía
    """
    if not mil:
        return
    per = mil.get("by_country") or {}
    for c in ctx.spec.countries:
        if c.is_major:
            strategies = list(mil.get("peace") or []) + list(per.get(c.tag) or [])
            add_plan(f"{c.tag}_militar", c.tag, strategies)
            research = _research_weights(mil, c.tag)
            if research:
                add_plan(f"{c.tag}_investigacion", c.tag, research)
            if mil.get("war"):
                add_plan(f"{c.tag}_militar_en_guerra", c.tag, list(mil["war"]), enable={"at_war": True},
                         abort={"at_war": False})
        elif not c.is_subject and mil.get("anarchy"):
            add_plan(f"{c.tag}_defensa", c.tag, list(mil["anarchy"]))


def _research_weights(mil: dict, tag: str) -> list[dict]:
    """naval_research y armor_research (2026-09-30: "la HSN no investiga
    barcos"): además del ai_will_do de cada tecnología (research.py), una
    estrategia research_weight_factor por tecnología con el valor del país
    (value = 300 es +300%). Si una tecnología está en los dos bloques, gana
    el valor más alto."""
    best: dict[str, int] = {}
    for key in ("naval_research", "armor_research"):
        block = mil.get(key) or {}
        v = (block.get("by_country") or {}).get(tag, block.get("value"))
        if not v:
            continue
        for t in block.get("techs") or []:
            best[t] = max(best.get(t, 0), int(v))
    return [{"type": "research_weight_factor", "id": t, "value": v} for t, v in best.items()]


def destiny_targets(ctx: BuildContext) -> dict[str, list[str]]:
    """Meganación -> quiénes tienen al arrancar las regiones que pide su forma
    final (las de <TAG>_reclamar_el_destino, 14_decisions), sin ella misma,
    sus satélites ni su facción."""
    from .territory import normalize
    ids = ctx.data.get("state_ids_by_name") or {}
    territory = ctx.data.get("territory") or {}
    subjects = {c.tag: c.overlord for c in ctx.spec.countries if c.is_subject}
    faction_of = {}
    for f in (ctx.spec.raw["diplomacy"].get("factions") or []):
        for m in f.get("members") or []:
            faction_of[m] = f["id"]
    out: dict[str, list[str]] = {}
    for cat in (ctx.spec.raw.get("decisions") or {}).get("categories") or []:
        for d in cat.get("decisions") or []:
            if not str(d.get("id", "")).endswith("_reclamar_el_destino"):
                continue
            tag = d["id"].split("_")[0]
            holders: list[str] = []
            for e in d.get("effects") or []:
                if e.get("effect") != "wargoal_holders":
                    continue
                for names in e.get("states") or []:
                    sid = next((ids[normalize(n)] for n in names if normalize(n) in ids), None)
                    who = territory.get(sid)
                    if (who and who != tag and subjects.get(who) != tag
                            and not (faction_of.get(who) and faction_of.get(who) == faction_of.get(tag))
                            and who not in holders):
                        holders.append(who)
            out[tag] = holders
    return out


def _destiny_war_plans(ctx: BuildContext, wars: dict, add_plan) -> None:
    """La IA persigue su forma final (2026-10-10, pedido del usuario: "que
    persiga más agresivamente sus objetivos finales"). Con el destino abierto
    (<TAG>_destino_abierto) y hasta proclamarla: más fábricas militares, y
    contra cada dueño de arranque de sus regiones: prepararse, conquistar,
    hostigar y declarar con un ejército de verdad (sin otra guerra, o con uno
    muy grande)."""
    if not wars:
        return
    targets = destiny_targets(ctx)
    lines = []
    for tag, holders in sorted(targets.items()):
        open_ = {"flag": f"{tag}_destino_abierto", "not_flag": f"{tag}_forma_final"}
        done = {"flag": f"{tag}_forma_final"}
        if wars.get("military_ratio"):
            add_plan(f"{tag}_destino_se_arma", tag,
                     [{"type": "added_military_to_civilian_factory_ratio", "value": int(wars["military_ratio"])}],
                     enable=open_, abort=done)
        for t in holders:
            gone = {"any": [done, {"not": {"country_exists": t}}, {"country": {"tag": t, "when": {"subject_of": tag}}}]}
            add_plan(f"{tag}_destino_contra_{t}", tag, [
                {"type": "prepare_for_war", "target": t, "value": wars.get("prepare", 150)},
                {"type": "conquer", "target": t, "value": wars.get("conquer", 250)},
                {"type": "antagonize", "target": t, "value": wars.get("antagonize", 60)},
            ], enable=open_, abort=gone)
            declare = dict(open_)
            declare["not"] = {"war_with": t}
            declare["any"] = [{"at_war": False}, {"divisions_at_least": int(wars.get("divisions_two_fronts", 50))}]
            declare["divisions_at_least"] = int(wars.get("divisions", 30))
            add_plan(f"{tag}_destino_declara_a_{t}", tag,
                     [{"type": "declare_war", "target": t, "value": wars.get("declare", 200)}], enable=declare, abort=gone)
        lines.append(f"{tag} contra {', '.join(holders) or '-'}")
    ctx.note("ia: guerras del destino: " + "; ".join(lines))


def _anarchy_war_plans(ctx: BuildContext, wars: dict, add_plan) -> None:
    """Guerras contra la Anarquía vecina (2026-09-28): todos arrancan en paz
    con un casus belli permanente (04_diplomacy -> anarchy_hostility). La IA
    se prepara desde el día uno y declara a partir de su fecha
    (declare_after, escalonada para que no sea todos contra todos el primer
    año), con un ejército mínimo y sin otra guerra abierta."""
    if not wars:
        return
    after = wars.get("declare_after") or {}
    for mega, anar in ctx.data.get("anarchy_pairs") or []:
        # Si la anarquía pasa a ser satélite de otro (una conferencia de paz),
        # declararle es declararle a su señor: la partida de 2026-09-29 tuvo a
        # Roma en guerra con la Comuna porque Eurasia era satélite de la ASC.
        free = {"country": {"tag": anar, "when": {"subject": False}}}
        gone = {"any": [{"not": {"country_exists": anar}},
                        {"country": {"tag": anar, "when": {"subject": True}}}]}
        # prepararse sí desde el día uno; conquistar, recién desde su fecha
        add_plan(f"{mega}_se_prepara_contra_{anar}", mega, [
            {"type": "prepare_for_war", "target": anar, "value": wars.get("prepare", 100)},
            {"type": "antagonize", "target": anar, "value": wars.get("antagonize", 50)},
        ], enable=free, abort=gone)
        conquer_enable = dict(free)
        if after.get(mega):
            conquer_enable["date_after"] = str(after[mega])
        add_plan(f"{mega}_contra_{anar}", mega, [
            {"type": "conquer", "target": anar, "value": wars.get("conquer", 150)},
        ], enable=conquer_enable, abort=gone)
        enable = {"divisions_at_least": int(wars.get("divisions", 12)), "at_war": False,
                  "country": {"tag": anar, "when": {"not_flag": f"{anar}_intocable", "subject": False}}}
        if after.get(mega):
            enable["date_after"] = str(after[mega])
        add_plan(f"{mega}_declara_a_{anar}", mega,
                 [{"type": "declare_war", "target": anar, "value": wars.get("declare", 100)}], enable=enable, abort=gone)


def _coalition_plans(ctx: BuildContext, cfg: dict, add_plan) -> None:
    """La Coalición de Ginebra (2026-10-10): quien se unió (bandera
    MEGANATIONS_en_coalicion) se prepara contra cada potencia que proclamó su
    forma final o tiene la Hegemonía Mundial, salvo la propia, su señor o su
    facción."""
    if not cfg:
        return
    tags = (ctx.spec.raw["diplomacy"].get("race") or {}).get("tags") or []
    for a in tags:
        for b in tags:
            if a == b:
                continue
            enable = {"flag": "MEGANATIONS_en_coalicion",
                      "country": {"tag": b, "when": {"any": [{"flag": f"{b}_forma_final"},
                                                            {"flag": "MEGANATIONS_hegemon"}]}},
                      "not": {"any": [{"subject_of": b}, {"in_faction_with": b}]}}
            add_plan(f"{a}_coalicion_contra_{b}", a, [
                {"type": "antagonize", "target": b, "value": cfg.get("antagonize", 80)},
                {"type": "prepare_for_war", "target": b, "value": cfg.get("prepare", 100)},
                {"type": "conquer", "target": b, "value": cfg.get("conquer", 120)},
            ], enable=enable, abort={"any": [{"not": {"country_exists": b}}, {"subject_of": b}]})
    ctx.note(f"ia: coalicion de Ginebra lista para {len(tags)} potencias")
