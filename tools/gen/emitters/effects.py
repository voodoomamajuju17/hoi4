"""Efectos en formato spec -> Paradox script. Lo usan focos y eventos.

Formato del spec: lista de { effect, value } o uno de los compuestos:
  { effect: swap_ideas, remove, add }
  { effect: annex, target: TAG }                 -> annex_country
  { effect: wargoal, target: TAG, type: X }      -> create_wargoal
  { effect: build, building: X, level: N }       -> en la capital, con slots
  { effect: add_resource, resource: X, amount: N } -> en la capital (id resuelto en el build)
  { effect: add_variable, var: X, value: N }      -> add_to_variable
  { effect: set_variable, var: X, value: N }      -> set_variable
  { effect: clamp, var: X, min: A, max: B }       -> clamp_variable
  { effect: flag, value: X, days: N } / { effect: clear_flag, value: X }   (days: vence sola)
  { effect: random, options: [ { weight: N, effects: [...] }, ... ] } -> random_list
  { effect: remove_idea, value: X }               -> remove_ideas
  { effect: timed_idea, idea: X, days: N }        -> add_timed_idea
  { effect: event, id: ns.N, days: D, target: TAG } -> country_event (en TAG si se da)
  { effect: scope, target: TAG, effects: [...] }   -> TAG = { ... }  (no "on": YAML lo lee como true)
  { effect: promote, character: X }               -> promote_character (reclutado en la historia)
  { effect: if, when: {condiciones}, then: [...], else: [...] }
  { effect: run, value: X }                       -> X = yes (efecto de 14_decisions.yaml -> scripted_effects)
  { effect: leader_trait, value: X }              -> add_country_leader_trait
  { effect: states, pick: random|every, when: {..}, effects: [..] }
                                                  -> random_owned_controlled_state / every_owned_state
  En regiones: { effect: add_core, value: TAG } / { effect: state_flag, value: X }
               { effect: clear_state_flag, value: X }
Los efectos se validan contra documentation/ del juego (verify_keys) y los
ids de idea contra 05_ideas.yaml.
"""

from __future__ import annotations

from ..errors import SpecError
from ..pdx import Block

# Efectos cuyo valor es un número o un id suelto: `efecto = valor`.
SCALAR_EFFECTS = {
    "add_political_power",
    "add_stability",
    "add_war_support",
    "army_experience",
    "navy_experience",
    "air_experience",
    "add_manpower",
    "add_ideas",
    "add_research_slot",
}


class EffectContext:
    """Lo que hace falta para validar efectos que apuntan a cosas del juego."""

    def __init__(self, known_ideas: set[str], tags: set[str],
                 buildings: set[str] | None = None, wargoals: set[str] | None = None,
                 capital: int | None = None, resources: set[str] | None = None, warn=None,
                 characters: set[str] | None = None, events: set[str] | None = None,
                 triggers_used: dict[str, str] | None = None, scripted: set[str] | None = None,
                 shared_slots: set[str] | None = None):
        self.shared_slots = shared_slots
        self.scripted = scripted
        self.characters = characters
        self.events = events
        self.triggers_used = triggers_used if triggers_used is not None else {}
        self.capital = capital
        self.warn = warn
        self.resources = resources or set()
        self.known_ideas = known_ideas
        self.tags = tags
        self.buildings = buildings or set()
        self.wargoals = wargoals or set()


def render_effects(owner: str, items: list[dict], known,
                   effects_used: dict[str, str], *, where: str) -> Block:
    ec = known if isinstance(known, EffectContext) else EffectContext(known, set())
    known_ideas = ec.known_ideas
    block = Block()
    for item in items:
        effect = item.get("effect")
        if effect in ("annex", "wargoal"):
            target = item.get("target")
            if ec.tags and target not in ec.tags:
                raise SpecError(f"{owner}: {effect} contra '{target}', que no es un pais del mod", where=where)
            inner = Block()
            if effect == "annex":
                inner.add("target", target)
                inner.add("transfer_troops", True)
                block.add("annex_country", inner)
                effects_used.setdefault("annex_country", owner)
            else:
                kind = item.get("type", "annex_everything")
                if ec.wargoals and kind not in ec.wargoals:
                    raise SpecError(f"{owner}: tipo de wargoal '{kind}' no existe en common/wargoals/",
                                    where=where)
                inner.add("type", kind)
                inner.add("target", target)
                block.add("create_wargoal", inner)
                effects_used.setdefault("create_wargoal", owner)
            continue
        if effect == "build":
            building = item.get("building")
            if ec.buildings and building not in ec.buildings:
                raise SpecError(f"{owner}: el edificio '{building}' no existe en common/buildings/",
                                where=where)
            level = int(item.get("level", 1))
            construction = Block()
            construction.add("type", building)
            construction.add("level", level)
            construction.add("instant_build", True)
            scope = Block()
            # Solo las fábricas y astilleros ocupan slots compartidos; la
            # infraestructura o una base aérea no necesitan slot extra.
            if ec.shared_slots is None or building in ec.shared_slots:
                scope.add("add_extra_state_shared_building_slots", level)
                effects_used.setdefault("add_extra_state_shared_building_slots", owner)
            scope.add("add_building_construction", construction)
            block.add("capital_scope", scope)
            effects_used.setdefault("add_building_construction", owner)
            continue
        if effect in ("add_variable", "set_variable"):
            inner = Block()
            inner.add("var", item["var"])
            inner.add("value", item["value"])
            key = "add_to_variable" if effect == "add_variable" else "set_variable"
            block.add(key, inner)
            effects_used.setdefault(key, owner)
            continue
        if effect == "clamp":
            inner = Block()
            inner.add("var", item["var"])
            inner.add("min", item["min"])
            inner.add("max", item["max"])
            block.add("clamp_variable", inner)
            effects_used.setdefault("clamp_variable", owner)
            continue
        if effect in ("flag", "clear_flag"):
            key = "set_country_flag" if effect == "flag" else "clr_country_flag"
            if effect == "flag" and item.get("days"):
                # bandera que vence sola: sirve como espera compartida entre decisiones
                block.add(key, Block([("flag", item["value"]), ("days", int(item["days"]))]))
            else:
                block.add(key, item["value"])
            effects_used.setdefault(key, owner)
            continue
        if effect == "remove_idea":
            if item.get("value") not in known_ideas:
                raise SpecError(f"{owner}: remove_idea '{item.get('value')}' no es una idea del spec", where=where)
            block.add("remove_ideas", item["value"])
            effects_used.setdefault("remove_ideas", owner)
            continue
        if effect == "timed_idea":
            if item.get("idea") not in known_ideas:
                raise SpecError(f"{owner}: timed_idea '{item.get('idea')}' no es una idea del spec", where=where)
            inner = Block()
            inner.add("idea", item["idea"])
            inner.add("days", int(item["days"]))
            block.add("add_timed_idea", inner)
            effects_used.setdefault("add_timed_idea", owner)
            continue
        if effect == "event":
            eid = item["id"]
            if ec.events is not None and eid not in ec.events:
                raise SpecError(f"{owner}: el evento '{eid}' no existe en 12_events.yaml", where=where)
            inner = Block()
            inner.add("id", eid)
            inner.add("days", int(item.get("days", 1)))
            target = item.get("target")
            if target:
                if ec.tags and target not in ec.tags:
                    raise SpecError(f"{owner}: evento para '{target}', que no es un pais del mod", where=where)
                block.add(target, Block([("country_event", inner)]))
            else:
                block.add("country_event", inner)
            effects_used.setdefault("country_event", owner)
            continue
        if effect == "scope":
            target = item.get("target")
            if ec.tags and target not in ec.tags:
                raise SpecError(f"{owner}: 'scope' apunta a '{target}', que no es un pais del mod", where=where)
            block.add(target, render_effects(owner, item.get("effects") or [], ec, effects_used, where=where))
            continue
        if effect == "promote":
            cid = item["character"]
            if ec.characters is not None and cid not in ec.characters:
                raise SpecError(f"{owner}: promote '{cid}' no es un personaje de 03_leaders.yaml", where=where)
            # Ya está reclutado desde la historia (history.py): acá solo se asciende.
            block.add("promote_character", cid)
            effects_used.setdefault("promote_character", owner)
            continue
        if effect == "random":
            inner = Block()
            for opt in item["options"]:
                inner.add(str(int(opt.get("weight", 1))),
                          render_effects(owner, opt.get("effects") or [], ec, effects_used, where=where))
            block.add("random_list", inner)
            effects_used.setdefault("random_list", owner)
            continue
        if effect == "leader_trait":
            block.add("add_country_leader_trait", item["value"])
            effects_used.setdefault("add_country_leader_trait", owner)
            continue
        if effect == "states":
            pick = item.get("pick", "every")
            key = {"random": "random_owned_controlled_state", "every": "every_owned_state"}.get(pick)
            if key is None:
                raise SpecError(f"{owner}: states.pick '{pick}' (random o every)", where=where)
            inner = Block()
            if item.get("when"):
                inner.add("limit", render_conditions(owner, item["when"], ec.triggers_used, where=where))
            inner.entries.extend(render_effects(owner, item.get("effects") or [], ec, effects_used, where=where).entries)
            block.add(key, inner)
            effects_used.setdefault(key, owner)
            continue
        if effect in ("add_core", "state_flag", "clear_state_flag"):
            key = {"add_core": "add_core_of", "state_flag": "set_state_flag", "clear_state_flag": "clr_state_flag"}[effect]
            if effect == "add_core" and ec.tags and item["value"] not in ec.tags:
                raise SpecError(f"{owner}: add_core '{item['value']}' no es un pais del mod", where=where)
            block.add(key, item["value"])
            effects_used.setdefault(key, owner)
            continue
        if effect == "run":
            name = item["value"]
            if ec.scripted is not None and name not in ec.scripted:
                raise SpecError(f"{owner}: run '{name}' no esta en 14_decisions.yaml -> scripted_effects",
                                where=where)
            block.add(name, True)
            continue
        if effect == "if":
            inner = Block()
            inner.add("limit", render_conditions(owner, item.get("when") or {}, ec.triggers_used, where=where))
            inner.entries.extend(render_effects(owner, item.get("then") or [], ec, effects_used, where=where).entries)
            if item.get("else"):
                inner.add("else", render_effects(owner, item["else"], ec, effects_used, where=where))
            block.add("if", inner)
            continue
        if effect == "add_resource":
            resource = item.get("resource")
            if ec.resources and resource not in ec.resources:
                raise SpecError(f"{owner}: recurso '{resource}' desconocido", where=where)
            if ec.capital is None:
                if ec.warn:
                    ec.warn(f"{owner}: add_resource omitido, no hay capital resuelta (falta --vanilla-path).")
                continue
            inner = Block()
            inner.add("type", resource)
            inner.add("amount", int(item.get("amount", 1)))
            inner.add("state", ec.capital)
            block.add("add_resource", inner)
            effects_used.setdefault("add_resource", owner)
            continue
        if effect == "swap_ideas":
            for role in ("remove", "add"):
                if item.get(role) not in known_ideas:
                    raise SpecError(f"{owner}: swap_ideas.{role} '{item.get(role)}' no es una idea del spec",
                                    where=where)
            inner = Block()
            inner.add("remove_idea", item["remove"])
            inner.add("add_idea", item["add"])
            block.add("swap_ideas", inner)
        elif effect in SCALAR_EFFECTS:
            value = item.get("value")
            if effect == "add_ideas" and value not in known_ideas:
                raise SpecError(f"{owner}: add_ideas '{value}' no es una idea del spec", where=where)
            block.add(effect, value)
        else:
            raise SpecError(
                f"{owner}: efecto '{effect}' no soportado por el generador",
                hint=f"soportados: swap_ideas, {', '.join(sorted(SCALAR_EFFECTS))}",
                where=where,
            )
        effects_used.setdefault(effect, owner)
    return block


def render_conditions(owner: str, spec: dict, triggers_used: dict[str, str], *, where: str) -> Block:
    """Condiciones comunes a focos, decisiones y efectos `if`.

      variable_at_least: { var, value }   -> check_variable (forma larga, sin operador)
      variable_below: { var, value }      -> check_variable less_than
      variable_between: { var, min, max } -> dos check_variable
      variables_below: [ {var, value}, .. ] -> todas por debajo
      all_between: { vars: [..], min, max }
      stability_at_least: 0.4             -> has_stability > 0.4
      flag / not_flag: X                  -> has_country_flag
      at_war: true|false                  -> has_war
      idea / not_idea: X                  -> has_idea
      focus: X                            -> has_completed_focus
      country_exists: TAG
      core_of / not_core_of: TAG          -> is_core_of (en regiones)
      state_flag / not_state_flag: X      -> has_state_flag (en regiones)
      state_flag_days: { flag, days }     -> has_state_flag = { flag days > N }
      stability_below: 0.4                -> has_stability < 0.4
      any: [ {..}, {..} ]                 -> OR
      not: { .. }                         -> NOT (no se cumplen todas juntas)
    Varias condiciones en el mismo bloque se cumplen todas (AND).
    """
    from ..pdx import Compare

    def check(var, value, compare):
        inner = Block()
        inner.add("var", var)
        inner.add("value", value)
        inner.add("compare", compare)
        triggers_used.setdefault("check_variable", owner)
        return ("check_variable", inner)

    block = Block()
    for key, value in spec.items():
        if key == "variable_at_least":
            block.entries.append(check(value["var"], value["value"], "greater_than_or_equals"))
        elif key == "variable_below":
            block.entries.append(check(value["var"], value["value"], "less_than"))
        elif key == "variables_below":
            for v in value:
                block.entries.append(check(v["var"], v["value"], "less_than"))
        elif key == "variable_between":
            block.entries.append(check(value["var"], value["min"], "greater_than_or_equals"))
            block.entries.append(check(value["var"], value["max"], "less_than_or_equals"))
        elif key == "all_between":
            for var in value["vars"]:
                block.entries.append(check(var, value["min"], "greater_than_or_equals"))
                block.entries.append(check(var, value["max"], "less_than_or_equals"))
        elif key in ("flag", "not_flag"):
            if key == "flag":
                block.add("has_country_flag", value)
            else:
                block.add("NOT", Block([("has_country_flag", value)]))
            triggers_used.setdefault("has_country_flag", owner)
        elif key == "at_war":
            block.add("has_war", bool(value))
            triggers_used.setdefault("has_war", owner)
        elif key in ("idea", "not_idea"):
            if key == "idea":
                block.add("has_idea", value)
            else:
                block.add("NOT", Block([("has_idea", value)]))
            triggers_used.setdefault("has_idea", owner)
        elif key == "focus":
            block.add("has_completed_focus", value)
            triggers_used.setdefault("has_completed_focus", owner)
        elif key == "country_exists":
            block.add("country_exists", value)
            triggers_used.setdefault("country_exists", owner)
        elif key in ("core_of", "not_core_of"):
            if key == "core_of":
                block.add("is_core_of", value)
            else:
                block.add("NOT", Block([("is_core_of", value)]))
            triggers_used.setdefault("is_core_of", owner)
        elif key in ("state_flag", "not_state_flag"):
            if key == "state_flag":
                block.add("has_state_flag", value)
            else:
                block.add("NOT", Block([("has_state_flag", value)]))
            triggers_used.setdefault("has_state_flag", owner)
        elif key == "state_flag_days":
            inner = Block()
            inner.add("flag", value["flag"])
            inner.add("days", Compare(">", int(value["days"])))
            block.add("has_state_flag", inner)
            triggers_used.setdefault("has_state_flag", owner)
        elif key == "stability_below":
            block.add("has_stability", Compare("<", float(value)))
            triggers_used.setdefault("has_stability", owner)
        elif key == "any":
            ors = Block()
            for sub in value:
                inner = render_conditions(owner, sub, triggers_used, where=where)
                if len(inner.entries) == 1:
                    ors.entries.extend(inner.entries)
                else:
                    ors.add("AND", inner)
            block.add("OR", ors)
        elif key == "not":
            inner = render_conditions(owner, value, triggers_used, where=where)
            # NOT = { A B } en HOI4 es "ninguna"; "no se cumplen todas" es NOT = { AND = {A B} }.
            block.add("NOT", inner if len(inner.entries) == 1 else Block([("AND", inner)]))
        elif key == "stability_at_least":
            block.add("has_stability", Compare(">", float(value)))
            triggers_used.setdefault("has_stability", owner)
        else:
            raise SpecError(f"{owner}: condicion desconocida '{key}'", where=where)
    return block


def scripted_effect_ids(spec_raw: dict) -> set[str]:
    return {e["id"] for e in (spec_raw.get("decisions") or {}).get("scripted_effects") or []}
