"""La carrera del destino y lo que la rodea (spec/04_diplomacy.yaml -> race).

Pedido del usuario (2026-10-10): "Pensá bien qué podrías ajustar o agregar
para hacerlo más divertido" -> "Dale, hacé todas". Las partes que necesitan
el mapa (qué región es cuál, la capital de cada uno) salen de acá; los textos,
eventos, decisiones y espíritus están en 12_events (meganations_mundo.90-123)
y 14_decisions.

Produce common/scripted_effects/meganations_carrera.txt:

  MEGANATIONS_carrera_pulso   lo corre cada potencia en su pulso mensual
                              (MEGANATIONS_eventos_mundiales):
    marcador     global.MEGANATIONS_carrera_<TAG> = regiones clave que
                 controla (las de su forma final: controls_all de
                 <TAG>_proclamar_la_forma_final). El panel de la carrera las
                 muestra.
    alarma       con el destino abierto y a una región de la forma final, una
                 vez: evento oculto meganations_mundo.90 en ese país, que le
                 avisa al resto (mundo.91, FROM = el que está por llegar).
    misiones     al abrir el destino se anota la meta: las regiones de ese día
                 + 2 (MEGANATIONS_carrera_meta), para su misión de un año.
    exilio       capital de arranque perdida en guerra -> bandera
                 MEGANATIONS_capital_perdida (decisión del exilio); al
                 recuperarla, mundo.97.
    caudillos    una anarquía que ya no existe puede volver: su capital de
                 arranque en manos de esta potencia, desde la fecha, en guerra o
                 con poca estabilidad, una chance por mes (mundo.100-103).
    rivales      el rival jurado: aviso (mundo.120), guerra jurada (121),
                 venganza cumplida (122) y humillación del vencido (123).
  MEGANATIONS_frenar_<TAG>    objetivos de guerra (take_state) contra <TAG> por
                              cada región de su forma final que ya es suya.
  MEGANATIONS_frenar_FROM     lo mismo contra FROM (coalición, alarma).
  MEGANATIONS_caudillo_<A>_titere / _libre   la anarquía vuelve como satélite
                              propio o libre y en guerra.
"""

from __future__ import annotations

from ..context import BuildContext
from ..pdx import Block, Compare, Quoted

SOURCE = "spec/04_diplomacy.yaml -> race"
ALARM_EVENT = "meganations_mundo.90"
HOME_EVENT = "meganations_mundo.97"
CAUDILLO_EVENTS = {"ZWE": "meganations_mundo.100", "ZWI": "meganations_mundo.101",
                   "ZWM": "meganations_mundo.102", "ZWB": "meganations_mundo.103"}
NEMESIS_EVENTS = ("meganations_mundo.120", "meganations_mundo.121", "meganations_mundo.122", "meganations_mundo.123")
NEMESIS_TARGET = "meganations_rival_jurado"
# alarma y meta de la misión solo si se resolvieron al menos estas regiones
MIN_REGIONS = 3
AVENGER_TARGET = "meganations_vengador"


def scripted_ids(spec_raw: dict) -> set[str]:
    """Los efectos que genera este módulo (para que `run` los acepte)."""
    race = (spec_raw.get("diplomacy") or {}).get("race") or {}
    if not race:
        return set()
    tags = race.get("tags") or []
    out = {"MEGANATIONS_carrera_pulso", "MEGANATIONS_frenar_FROM"}
    out |= {f"MEGANATIONS_frenar_{t}" for t in tags}
    for a in (race.get("caudillos") or {}).get("anarchies") or []:
        out |= {f"MEGANATIONS_caudillo_{a}_titere", f"MEGANATIONS_caudillo_{a}_libre"}
    return out


def destiny_states(ctx: BuildContext) -> dict[str, list[int]]:
    """TAG -> regiones (ids) que pide su forma final (controls_all)."""
    from .territory import normalize
    ids = ctx.data.get("state_ids_by_name") or {}
    out: dict[str, list[int]] = {}
    for cat in (ctx.spec.raw.get("decisions") or {}).get("categories") or []:
        for d in cat.get("decisions") or []:
            did = str(d.get("id", ""))
            if not did.endswith("_proclamar_la_forma_final"):
                continue
            states = []
            for names in (d.get("available") or {}).get("controls_all") or []:
                sid = next((ids[normalize(n)] for n in names if normalize(n) in ids), None)
                if sid is not None and sid not in states:
                    states.append(sid)
            out[did.split("_")[0]] = states
            want = len((d.get("available") or {}).get("controls_all") or [])
            if len(states) < want and ctx.vanilla is not None and ids:
                ctx.warn(f"carrera del destino: {did} pide {want} regiones y se encontraron {len(states)}; "
                         "el marcador cuenta solo esas")
    return out


def emit(ctx: BuildContext) -> None:
    race = ctx.spec.raw["diplomacy"].get("race") or {}
    if not race:
        return
    tags = list(race.get("tags") or [])
    destiny = destiny_states(ctx)
    capitals = ctx.data.get("capitals") or {}
    totals = {t: len(destiny.get(t, [])) for t in tags}
    effects: dict[str, str] = {}
    triggers: dict[str, str] = {}

    def gvar(t: str) -> str:
        return f"global.MEGANATIONS_carrera_{t}"

    root = Block()
    pulse = Block()

    # 1. marcador
    for t in tags:
        pulse.add("set_variable", Block([("var", gvar(t)), ("value", 0)]))
        for sid in destiny.get(t, []):
            pulse.add("if", Block([
                ("limit", Block([(str(sid), Block([("is_controlled_by", t)]))])),
                ("add_to_variable", Block([("var", gvar(t)), ("value", 1)]))]))
    # 2. alarma: a una región de la forma final
    for t in tags:
        if totals[t] < MIN_REGIONS:
            continue
        pulse.add("if", Block([
            ("limit", Block([
                ("country_exists", t),
                (t, Block([("has_country_flag", f"{t}_destino_abierto"),
                           ("NOT", Block([("has_country_flag", f"{t}_forma_final")]))])),
                ("check_variable", Block([("var", gvar(t)), ("value", totals[t] - 1),
                                          ("compare", "greater_than_or_equals")])),
                ("NOT", Block([("has_global_flag", f"MEGANATIONS_alarma_{t}")]))])),
            ("set_global_flag", f"MEGANATIONS_alarma_{t}"),
            (t, Block([("country_event", Block([("id", ALARM_EVENT), ("days", 1)]))]))]))
    # 3. misiones: la meta del primer año del destino
    extra = int(race.get("mission_extra_regions", 2))
    for t in tags:
        if totals[t] < MIN_REGIONS:
            continue
        pulse.add("if", Block([
            ("limit", Block([("tag", t), ("has_country_flag", f"{t}_destino_abierto"),
                             ("NOT", Block([("has_country_flag", "MEGANATIONS_carrera_inicio")]))])),
            ("set_country_flag", "MEGANATIONS_carrera_inicio"),
            ("set_variable", Block([("var", "MEGANATIONS_carrera_meta"), ("value", gvar(t))])),
            ("add_to_variable", Block([("var", "MEGANATIONS_carrera_meta"), ("value", extra)])),
            ("clamp_variable", Block([("var", "MEGANATIONS_carrera_meta"), ("min", 0), ("max", totals[t])]))]))
    # 4. el exilio: la capital de ARRANQUE (el juego muda la actual cuando cae)
    exile = 0
    for t in tags:
        cap = capitals.get(t)
        if cap is None:
            continue
        exile += 1
        pulse.add("if", Block([
            ("limit", Block([("tag", t), ("has_country_flag", "MEGANATIONS_capital_perdida"),
                             ("controls_state", cap)])),
            ("clr_country_flag", "MEGANATIONS_capital_perdida"),
            ("if", Block([("limit", Block([("has_country_flag", "MEGANATIONS_en_exilio")])),
                          ("clr_country_flag", "MEGANATIONS_en_exilio"),
                          ("country_event", Block([("id", HOME_EVENT), ("days", 1)]))]))]))
        pulse.add("if", Block([
            ("limit", Block([("tag", t), ("has_war", True), ("NOT", Block([("controls_state", cap)])),
                             ("NOT", Block([("has_country_flag", "MEGANATIONS_capital_perdida")]))])),
            ("set_country_flag", "MEGANATIONS_capital_perdida")]))
    # 5. los caudillos vuelven
    cfg = race.get("caudillos") or {}
    caudillos = []
    for a in cfg.get("anarchies") or []:
        cap = capitals.get(a)
        if cap is None or a not in CAUDILLO_EVENTS:
            continue
        caudillos.append(a)
        chance = int(cfg.get("chance", 4))
        pulse.add("if", Block([
            ("limit", Block([
                ("date", Compare(">", str(cfg.get("after", "2102.1.1")))),
                ("NOT", Block([("country_exists", a)])),
                ("NOT", Block([("has_global_flag", f"MEGANATIONS_caudillo_{a}")])),
                (str(cap), Block([("is_owned_by", "ROOT")])),
                ("OR", Block([("has_war", True),
                              ("has_stability", Compare("<", float(cfg.get("stability_below", 0.4))))]))])),
            ("random_list", Block([
                (str(chance), Block([("set_global_flag", f"MEGANATIONS_caudillo_{a}"),
                                     ("country_event", Block([("id", CAUDILLO_EVENTS[a]), ("days", 1)]))])),
                (str(100 - chance), Block())]))]))
    # 6. el rival jurado
    nemesis = race.get("nemesis") or {}
    for t, n in sorted(nemesis.items()):
        save = (n, Block([("save_event_target_as", NEMESIS_TARGET)]))
        body = Block([("limit", Block([("tag", t), ("country_exists", n)]))])
        body.add("if", Block([
            ("limit", Block([("date", Compare(">", str(race.get("nemesis_from", "2100.2.1")))),
                             ("NOT", Block([("has_country_flag", "MEGANATIONS_rival_anunciado")]))])),
            ("set_country_flag", "MEGANATIONS_rival_anunciado"), save,
            ("country_event", Block([("id", NEMESIS_EVENTS[0]), ("days", 1)]))]))
        body.add("if", Block([
            ("limit", Block([("has_war_with", n), ("NOT", Block([("has_country_flag", "MEGANATIONS_guerra_jurada")]))])),
            ("set_country_flag", "MEGANATIONS_guerra_jurada"), save,
            ("country_event", Block([("id", NEMESIS_EVENTS[1]), ("days", 1)]))]))
        body.add("if", Block([
            ("limit", Block([("has_country_flag", "MEGANATIONS_guerra_jurada"),
                             ("NOT", Block([("has_war_with", n)]))])),
            ("clr_country_flag", "MEGANATIONS_guerra_jurada")]))
        body.add("if", Block([
            ("limit", Block([("has_war_with", n), (n, Block([("has_capitulated", True)])),
                             ("NOT", Block([("has_country_flag", f"MEGANATIONS_venganza_{n}")]))])),
            ("set_country_flag", f"MEGANATIONS_venganza_{n}"), save,
            ("save_event_target_as", AVENGER_TARGET),
            ("country_event", Block([("id", NEMESIS_EVENTS[2]), ("days", 1)])),
            (n, Block([("country_event", Block([("id", NEMESIS_EVENTS[3]), ("days", 1)]))]))]))
        pulse.add("if", body)
    root.add("MEGANATIONS_carrera_pulso", pulse)

    # frenar: objetivos de guerra por las regiones de su forma final que ya son suyas
    for t in tags:
        body = Block()
        for sid in destiny.get(t, []):
            body.add("if", Block([
                ("limit", Block([("NOT", Block([("tag", t)])), (str(sid), Block([("is_owned_by", t)]))])),
                ("create_wargoal", Block([("type", "take_state"), ("target", t),
                                          ("generator", Block([(None, sid)]))]))]))
        if not body.entries:
            body.add("log", Quoted(f"MEGANATIONS frenar {t}: sin regiones resueltas"))
        root.add(f"MEGANATIONS_frenar_{t}", body)
    from_body = Block()
    for t in tags:
        from_body.add("if", Block([("limit", Block([("FROM", Block([("tag", t)]))])),
                                   (f"MEGANATIONS_frenar_{t}", True)]))
    root.add("MEGANATIONS_frenar_FROM", from_body)

    # caudillos: vuelve como satélite propio (con su ejército) o libre y en guerra
    for a in caudillos:
        units = int(cfg.get("divisions", 6))
        def raise_army(scope_units: int) -> list:
            out = [("if", Block([
                ("limit", Block([("NOT", Block([("has_template", Quoted("Hueste"))]))])),
                ("division_template", Block([("name", Quoted("Hueste")), ("regiments", Block(
                    [("infantry", Block([("x", 0), ("y", i)])) for i in range(4)]
                    + [("infantry", Block([("x", 1), ("y", i)])) for i in range(3)]))]))]))]
            spawn = Block()
            for _ in range(scope_units):
                spawn.add("create_unit", Block([("division", Quoted("division_template = Hueste start_experience_factor = 0.4")),
                                                ("owner", "PREV")]))
            out.append(("capital_scope", spawn))
            out.append(("add_equipment_to_stockpile", Block([("type", "infantry_equipment"),
                                                             ("amount", int(cfg.get("equipment", 4000)))])))
            out.append(("add_manpower", int(cfg.get("manpower", 60000))))
            return out
        puppet = Block([("release_puppet", a)])
        puppet.add(a, Block([("set_country_flag", "MEGANATIONS_titere_buscado")] + raise_army(units // 2)))
        root.add(f"MEGANATIONS_caudillo_{a}_titere", puppet)
        free = Block([("release", a)])
        free.add(a, Block(raise_army(units) + [
            ("add_dynamic_modifier", Block([("modifier", "MEGANATIONS_caudillo_vuelve"), ("days", 730)])),
            ("declare_war_on", Block([("target", "PREV"), ("type", "annex_everything")]))]))
        root.add(f"MEGANATIONS_caudillo_{a}_libre", free)

    ctx.write_script("common/scripted_effects/meganations_carrera.txt", root, source=SOURCE)
    for k in ("set_variable", "add_to_variable", "clamp_variable", "set_global_flag", "country_event",
              "set_country_flag", "clr_country_flag", "random_list", "save_event_target_as", "create_wargoal",
              "log", "release_puppet", "release", "division_template", "create_unit", "add_equipment_to_stockpile",
              "add_manpower", "add_dynamic_modifier", "declare_war_on"):
        effects[k] = SOURCE
    for k in ("is_controlled_by", "is_owned_by", "country_exists", "has_country_flag", "check_variable",
              "has_global_flag", "tag", "controls_state", "has_war", "date", "has_stability", "has_war_with",
              "has_capitulated", "has_template"):
        triggers[k] = SOURCE
    ctx.verify_keys("effects", effects)
    ctx.verify_keys("triggers", {k: v for k, v in triggers.items() if k != "has_template"})
    ctx.data["race_totals"] = totals
    ctx.note("carrera del destino: regiones clave " + ", ".join(f"{t} {totals[t]}" for t in tags)
             + f"; exilio vigilado en {exile}; caudillos que pueden volver: {', '.join(caudillos) or '-'}; "
             + "rivales jurados: " + ", ".join(f"{t}->{n}" for t, n in sorted(nemesis.items())))
