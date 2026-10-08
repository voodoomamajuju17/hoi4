"""Efectos en formato spec -> Paradox script. Lo usan focos y eventos.

Formato del spec: lista de { effect, value } o uno de los compuestos:
  { effect: swap_ideas, remove, add }
  { effect: annex, target: TAG }                 -> annex_country
  { effect: wargoal, target: TAG, type: X }      -> create_wargoal
  { effect: wargoal_holders, states: [[nombres]], type: take_state }
      -> objetivo de guerra contra quien tenga cada región ahora (no ROOT, sus
         satélites, su facción ni los que garantiza)
  { effect: build, building: X, level: N }       -> en la capital, con slots
  { effect: add_resource, resource: X, amount: N } -> en la capital (id resuelto en el build)
  { effect: add_variable, var: X, value: N }      -> add_to_variable
  { effect: set_variable, var: X, value: N }      -> set_variable
  { effect: clamp, var: X, min: A, max: B }       -> clamp_variable
  { effect: flag, value: X, days: N } / { effect: clear_flag, value: X }   (days: vence sola)
  { effect: in_state, state: [nombres], effects: [...] } -> ID = { ... }
  { effect: build_here, building, level }         -> construcción en la región del scope
  { effect: claim, value: TAG }                   -> add_claim_by (en regiones)
  { effect: random, options: [ { weight: N, effects: [...] }, ... ] } -> random_list
  { effect: remove_idea, value: X }               -> remove_ideas
  { effect: timed_idea, idea: X, days: N }        -> add_timed_idea
  { effect: event, id: ns.N, days: D, target: TAG } -> country_event (en TAG si se da)
  { effect: scope, target: TAG, effects: [...] }   -> TAG = { ... }  (no "on": YAML lo lee como true)
  { effect: promote, character: X }               -> promote_character (reclutado en la historia)
  { effect: if, when: {condiciones}, then: [...], else: [...] }
  { effect: run, value: X }                       -> X = yes (efecto de 14_decisions.yaml -> scripted_effects)
  { effect: leader_trait, value: X }              -> add_country_leader_trait
  { effect: tech_bonus, category: X, bonus: 0.5, uses: 1 } -> add_tech_bonus (categoría leída del juego)
  { effect: capital, effects: [...] }             -> capital_scope
  { effect: states, pick: random|every, when: {..}, effects: [..] }
                                                  -> random_owned_controlled_state / every_owned_state
  { effect: global_flag, value: X }                -> set_global_flag (condiciones global_flag / not_global_flag)
  { effect: end_puppet, value: TAG }               -> end_puppet (en el scope del señor: TAG se independiza)
  { effect: guarantee, value: TAG }                -> diplomatic_relation guarantee (condición guarantees: TAG)
  En regiones: { effect: resource_here, resource: X, amount: N } -> add_resource en esa región
  Condiciones: owns_state: [nombres] (país), owned_by: TAG (región)
  { effect: every_country, when: {..}, effects: [..] } -> every_country (eventos mundiales)
  { effect: or_cores, country: TAG, kind: anarchy|satellite, then: [..], gone: [..], spare: [TAGS] }
      -> si TAG sigue como se espera, `then`; si no, núcleos en lo propio de su tierra y reclamos en el resto
  En regiones: { effect: add_core, value: TAG } / { effect: state_flag, value: X }
               { effect: clear_state_flag, value: X }
Los efectos se validan contra documentation/ del juego (verify_keys) y los
ids de idea contra 05_ideas.yaml.
"""

from __future__ import annotations

import re
import unicodedata

from ..errors import SpecError
from ..pdx import Block, Compare, Quoted

# Regiones por nombre (lo carga cada emisor desde el reparto del territorio).
# Un nombre que no está en el juego se reemplaza por algo que nunca se cumple
# y queda anotado en UNRESOLVED para que el emisor avise.
_STATES: dict[str, int] | None = None
UNRESOLVED: set[str] = set()


def use_states(mapping: dict[str, int] | None) -> None:
    global _STATES
    _STATES = mapping


_TERRITORY: dict[int, str] = {}


def use_territory(mapping: dict | None) -> None:
    """state id -> dueño al arranque (08_territory): para objetivos de guerra
    sobre "el territorio de los Emiratos" sin escribir ids a mano."""
    global _TERRITORY
    _TERRITORY = {int(k): v for k, v in (mapping or {}).items()}


# Nombres legibles de las variables (14_decisions.yaml -> variable_names).
# HOI4 no muestra add_to_variable en los tooltips: un foco que solo suma una
# variable decía "Este enfoque no tiene efecto". Cada add_variable con nombre
# lleva un custom_effect_tooltip "Granjas del Sol: +1".
_VAR_NAMES: dict[str, dict] = {}
TOOLTIPS: dict[str, tuple[str, str]] = {}


def use_variable_names(spec_raw: dict) -> None:
    global _VAR_NAMES
    _VAR_NAMES = (spec_raw.get("decisions") or {}).get("variable_names") or {}
    _use_civil_war_memory(spec_raw)


# Guerra civil: lo que el país tenía al empezarla (2026-09-30). El ganador
# terminaba sin la mayoría de sus espíritus; al empezar se anota cada espíritu
# y cada variable de la mecánica, y al terminar el ganador recupera lo que le
# falte (civil_war_restore). Quedan afuera los espíritus temporales y los que
# un efecto de recálculo pone y saca solo.
_CW_IDEAS: dict[str, list[str]] = {}
_CW_VARS: dict[str, list[str]] = {}


def _use_civil_war_memory(spec_raw: dict) -> None:
    def walk(o):
        if isinstance(o, dict):
            yield o
            for v in o.values():
                yield from walk(v)
        elif isinstance(o, list):
            for v in o:
                yield from walk(v)

    dec = spec_raw.get("decisions") or {}
    managed = {e.get("value") for e in walk(dec.get("scripted_effects")) if e.get("effect") == "remove_idea"}
    managed |= {e.get("remove") for e in walk(dec.get("scripted_effects")) if e.get("effect") == "swap_ideas"}
    managed |= {e.get("idea") for e in walk(spec_raw) if e.get("effect") == "timed_idea"}
    _CW_IDEAS.clear()
    for tag, groups in ((spec_raw.get("ideas") or {}).get("countries") or {}).items():
        ids = [i["id"] for g in ("starting_ideas", "focus_ideas") for i in (groups or {}).get(g) or []
               if isinstance(i, dict) and i.get("id") and i["id"] not in managed]
        _CW_IDEAS[tag] = ids
    names = set(_VAR_NAMES)
    for mech in (spec_raw.get("mechanics") or {}).get("mechanics") or []:
        names |= {v["name"] for v in mech.get("variables") or [] if isinstance(v, dict) and v.get("name")}
    _CW_VARS.clear()
    for n in sorted(names):
        _CW_VARS.setdefault(n.split("_", 1)[0], []).append(n)


def _variable_tooltip(var: str, value) -> str | None:
    name = _VAR_NAMES.get(var)
    if not name or name.get("hidden") or not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    num = float(value)
    shown = f"{num:+g}".replace(".", ",")
    key = f"MN_tt_{var}_{'m' if num < 0 else 'p'}{abs(num):g}".replace(".", "_")
    TOOLTIPS[key] = (f"§Y{name['english']}§!: {f'{num:+g}'}", f"§Y{name['spanish']}§!: {shown}")
    return key


# Guerras civiles (2026-09-29): el líder del bando rebelde se renombra y toma
# el retrato del personaje. set_country_leader_portrait pide un sprite: cada
# retrato usado se declara acá (ruta -> nombre del sprite).
PORTRAIT_SPRITES: dict[str, str] = {}


def portrait_sprite(path: str) -> str:
    name = "GFX_portrait_mn_" + re.sub(r"[^A-Za-z0-9_]", "_", path.rsplit("/", 1)[-1].rsplit(".", 1)[0])
    PORTRAIT_SPRITES[path] = name
    return name


def flush_tooltips(ctx) -> None:
    """Define la localisation de los tooltips usados hasta ahora (una vez cada uno)."""
    done = ctx.data.setdefault("tooltips_defined", set())
    for key, (en, es) in sorted(TOOLTIPS.items()):
        if key in done:
            continue
        ctx.loc.define_and_reference(key, en=en, es=es, file="meganations_tooltips", origin="tooltips")
        done.add(key)
    if PORTRAIT_SPRITES:
        sprites = Block()
        for path, name in sorted(PORTRAIT_SPRITES.items()):
            sprites.add("spriteType", Block([("name", Quoted(name)), ("texturefile", Quoted(path))]))
        ctx.write_script("interface/meganations_civil_war_portraits.gfx", Block([("spriteTypes", sprites)]),
                         source="guerras civiles: retratos de los lideres rebeldes")


def template_token(name: str) -> str:
    """Nombre de plantilla de división como una sola palabra ASCII: create_unit
    no leía las comillas de adentro (error.log 2026-09-30: "Malformed token:
    Milicia"). "Leva de Emergencia I" -> "Leva_de_Emergencia_I"."""
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^A-Za-z0-9_]+", "_", text).strip("_")


def _norm(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.lower().split())


# Ids de todos los focos del mod (los carga focus_trees.emit antes de
# renderizar nada): una condición `focus:` con un id que no existe es un error.
KNOWN_FOCUSES: set[str] = set()


def resolve_state(names) -> int | None:
    names = [names] if isinstance(names, (str, int)) else list(names)
    for n in names:
        if isinstance(n, int):
            return n
        if _STATES and _norm(n) in _STATES:
            return _STATES[_norm(n)]
    UNRESOLVED.add(" / ".join(str(n) for n in names))
    return None

# Alcances del juego que valen donde se pide un país (eventos de respuesta:
# FROM es el que mandó el evento).
SCOPES = {"ROOT", "FROM", "PREV"}
RELATIONS = {"guarantee", "non_aggression_pact", "military_access", "docking_rights"}

# Efectos cuyo valor es un número o un id suelto: `efecto = valor`.
MATH_OPS = {
    "set": "set_variable",
    "add": "add_to_variable",
    "sub": "subtract_from_variable",
    "mul": "multiply_variable",
    "div": "divide_variable",
}

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
                 shared_slots: set[str] | None = None, tech_categories: set[str] | None = None,
                 dynamic_modifiers: set[str] | None = None):
        self.dynamic_modifiers = dynamic_modifiers
        self.tech_categories = tech_categories
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
                if item.get("states"):
                    ids = [resolve_state(n) for n in item["states"]]
                    ids = [i for i in ids if i is not None]
                    if ids:
                        inner.add("generator", Block([(None, i) for i in ids]))
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
            if effect == "add_variable":
                tip = _variable_tooltip(item["var"], item["value"])
                if tip:
                    block.add("custom_effect_tooltip", tip)
                    effects_used.setdefault("custom_effect_tooltip", owner)
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
                # game.log 2026-10-02: sin `value` la bandera no frenaba nada (las
                # elecciones de la Unión salían todos los meses). El juego escribe
                # siempre { flag value = 1 days }.
                block.add(key, Block([("flag", item["value"]), ("value", 1), ("days", int(item["days"]))]))
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
                if ec.tags and target not in ec.tags and target not in SCOPES:
                    raise SpecError(f"{owner}: evento para '{target}', que no es un pais del mod", where=where)
                block.add(target, Block([("country_event", inner)]))
            else:
                block.add("country_event", inner)
            effects_used.setdefault("country_event", owner)
            continue
        if effect == "end_puppet":
            # el país del scope deja de tener a `value` como satélite (la independencia)
            target = item["value"]
            if ec.tags and target not in ec.tags:
                raise SpecError(f"{owner}: end_puppet de '{target}', que no es un pais del mod", where=where)
            block.add("end_puppet", target)
            effects_used.setdefault("end_puppet", owner)
            continue
        if effect == "global_flag":
            # marca de todo el mundo (eventos mundiales: salen una sola vez aunque
            # los pulsen varias potencias). Con days vence sola (las crisis del
            # siglo, 2026-10-02: una cada tantos meses).
            if item.get("days"):
                # game.log 2026-10-02: el juego no hace vencer las banderas globales
                # (las crisis del siglo salían todos los meses). Usar flag con days
                # en cada país que tenga que esperar.
                raise SpecError(f"{owner}: global_flag con days no vence en el juego; "
                                "usar {effect: flag, days} en los países", where=where)
            block.add("set_global_flag", item["value"])
            effects_used.setdefault("set_global_flag", owner)
            continue
        if effect == "every_country":
            # a cada país que cumpla `when` (eventos mundiales, 2026-09-29)
            inner = Block()
            if item.get("when"):
                inner.add("limit", render_conditions(owner, item["when"], ec.triggers_used, where=where))
            inner.entries.extend(render_effects(owner, item.get("effects") or [], ec, effects_used, where=where).entries)
            block.add("every_country", inner)
            effects_used.setdefault("every_country", owner)
            continue
        if effect == "scope":
            target = item.get("target")
            if ec.tags and target not in ec.tags and target not in SCOPES:
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
        if effect == "tech_bonus":
            # category puede ser una lista de alternativas: gana la primera que
            # el juego tenga (2026-09-30: el nombre de la categoría de apoyo no
            # se pudo confirmar sin el juego instalado)
            cats = item["category"] if isinstance(item["category"], list) else [item["category"]]
            cat = next((c for c in cats if not ec.tech_categories or c in ec.tech_categories), None)
            if cat is None:
                if ec.warn:
                    ec.warn(f"{owner}: la categoria de investigacion '{' / '.join(cats)}' no existe en este juego; "
                            f"se omite el bono.")
                continue
            inner = Block()
            inner.add("name", owner)
            inner.add("bonus", float(item.get("bonus", 0.5)))
            inner.add("uses", int(item.get("uses", 1)))
            inner.add("category", cat)
            block.add("add_tech_bonus", inner)
            effects_used.setdefault("add_tech_bonus", owner)
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
        if effect == "transfer_to":
            # en una región: se la entrega al país (TAG = { transfer_state = PREV })
            target = item["value"]
            if ec.tags and target not in ec.tags:
                raise SpecError(f"{owner}: transfer_to '{target}' no es un pais del mod", where=where)
            block.add(target, Block([("transfer_state", "PREV")]))
            effects_used.setdefault("transfer_state", owner)
            continue
        if effect in ("puppet", "white_peace"):
            target = item["value"]
            if ec.tags and target not in ec.tags and target not in SCOPES:
                raise SpecError(f"{owner}: {effect} '{target}' no es un pais del mod", where=where)
            block.add(effect, target)
            effects_used.setdefault(effect, owner)
            continue
        if effect == "declare_war":
            target = item["target"]
            if ec.tags and target not in ec.tags:
                raise SpecError(f"{owner}: declare_war contra '{target}', que no es un pais del mod", where=where)
            kind = item.get("type", "annex_everything")
            if ec.wargoals and kind not in ec.wargoals:
                raise SpecError(f"{owner}: tipo de wargoal '{kind}' no existe en common/wargoals/", where=where)
            inner = Block([("target", target), ("type", kind)])
            region = item.get("territory_of")
            if region:
                ids = sorted(sid for sid, tag in _TERRITORY.items() if tag == region)
                if ids:
                    inner.add("generator", Block([(None, i) for i in ids]))
            block.add("declare_war_on", inner)
            effects_used.setdefault("declare_war_on", owner)
            continue
        if effect == "send_equipment":
            target = item["target"]
            if ec.tags and target not in ec.tags:
                raise SpecError(f"{owner}: send_equipment a '{target}', que no es un pais del mod", where=where)
            block.add("send_equipment", Block([("type", item["type"]), ("amount", int(item["amount"])), ("target", target)]))
            effects_used.setdefault("send_equipment", owner)
            continue
        if effect == "opinion":
            target = item["target"]
            if ec.tags and target not in ec.tags:
                raise SpecError(f"{owner}: opinion hacia '{target}', que no es un pais del mod", where=where)
            block.add("add_opinion_modifier", Block([("target", target), ("modifier", item["modifier"])]))
            effects_used.setdefault("add_opinion_modifier", owner)
            continue
        if effect in ("add_core", "state_flag", "clear_state_flag"):
            key = {"add_core": "add_core_of", "state_flag": "set_state_flag", "clear_state_flag": "clr_state_flag"}[effect]
            if effect == "add_core" and ec.tags and item["value"] not in ec.tags:
                raise SpecError(f"{owner}: add_core '{item['value']}' no es un pais del mod", where=where)
            block.add(key, item["value"])
            effects_used.setdefault(key, owner)
            continue
        if effect == "in_state":
            sid = resolve_state(item["state"])
            if sid is None:
                continue
            block.add(str(sid), render_effects(owner, item.get("effects") or [], ec, effects_used, where=where))
            continue
        if effect == "build_here":
            building = item.get("building")
            if ec.buildings and building not in ec.buildings:
                raise SpecError(f"{owner}: el edificio '{building}' no existe en common/buildings/", where=where)
            level = int(item.get("level", 1))
            construction = Block()
            construction.add("type", building)
            construction.add("level", level)
            construction.add("instant_build", True)
            # como `build`: fábricas y astilleros llevan su propio slot, si no
            # en una región llena la construcción no se haría
            if ec.shared_slots is None or building in ec.shared_slots:
                block.add("add_extra_state_shared_building_slots", level)
                effects_used.setdefault("add_extra_state_shared_building_slots", owner)
            block.add("add_building_construction", construction)
            effects_used.setdefault("add_building_construction", owner)
            continue
        if effect == "wargoal_holders":
            # 2026-10-02 (pedido del usuario): la forma final pide regiones que
            # cambian de dueño en la partida; el objetivo va contra el dueño
            # de cada una en el momento de tomar la decisión.
            kind = item.get("type", "take_state")
            if ec.wargoals and kind not in ec.wargoals:
                raise SpecError(f"{owner}: tipo de wargoal '{kind}' no existe en common/wargoals/", where=where)
            for names in item.get("states") or []:
                sid = resolve_state(names)
                if sid is None:
                    continue
                friendly = Block([("tag", "ROOT"), ("is_subject_of", "ROOT"), ("is_in_faction_with", "ROOT"),
                                  ("ROOT", Block([("has_guaranteed", "PREV")]))])
                limit = Block([("NOT", Block([("is_controlled_by", "ROOT")])),
                               ("OWNER", Block([("NOT", Block([("OR", friendly)]))]))])
                goal = Block([("type", kind), ("target", "PREV"), ("generator", Block([(None, sid)]))])
                take = Block([("limit", limit),
                              ("OWNER", Block([("ROOT", Block([("create_wargoal", goal)]))]))])
                block.add(str(sid), Block([("if", take)]))
            effects_used.setdefault("create_wargoal", owner)
            continue
        if effect == "claim":
            block.add("add_claim_by", item["value"])
            effects_used.setdefault("add_claim_by", owner)
            continue
        if effect == "capital":
            block.add("capital_scope", render_effects(owner, item.get("effects") or [], ec, effects_used, where=where))
            continue
        if effect == "run":
            name = item["value"]
            if ec.scripted is not None and name not in ec.scripted:
                raise SpecError(f"{owner}: run '{name}' no esta en 14_decisions.yaml -> scripted_effects",
                                where=where)
            block.add(name, True)
            continue
        if effect == "math":
            # Cuentas sobre variables, en orden: [op, var, valor] con op en
            # set/add/sub/mul/div; el valor puede ser un número u otra variable.
            for op, var, value in item["ops"]:
                if op == "round":
                    block.add("round_variable", var)
                    effects_used.setdefault("round_variable", owner)
                    continue
                key = MATH_OPS.get(op)
                if key is None:
                    raise SpecError(f"{owner}: math '{op}' no existe (usar {', '.join(MATH_OPS)})", where=where)
                block.add(key, Block([("var", var), ("value", value)]))
                effects_used.setdefault(key, owner)
            continue
        if effect == "dynamic_modifier":
            # Espíritu vivo: se agrega una vez; sus números salen de variables.
            mid = item["id"]
            if ec.dynamic_modifiers is not None and mid not in ec.dynamic_modifiers:
                raise SpecError(f"{owner}: dynamic_modifier '{mid}' no esta en 14_decisions.yaml -> dynamic_modifiers",
                                where=where)
            if item.get("days"):
                # con duración (2026-10-01, Leva Forzosa): se va solo. Nunca dos
                # veces el mismo (crash 2026-10-03: las crisis del siglo lo
                # apilaban 8 veces por mes).
                block.add("if", Block([
                    ("limit", Block([("NOT", Block([("has_dynamic_modifier", Block([("modifier", mid)]))]))])),
                    ("add_dynamic_modifier", Block([("modifier", mid), ("days", int(item["days"]))]))]))
                ec.triggers_used.setdefault("has_dynamic_modifier", owner)
                effects_used.setdefault("add_dynamic_modifier", owner)
                continue
            guard = Block()
            guard.add("limit", Block([("NOT", Block([("has_dynamic_modifier", Block([("modifier", mid)]))]))]))
            guard.add("add_dynamic_modifier", Block([("modifier", mid)]))
            block.add("if", guard)
            ec.triggers_used.setdefault("has_dynamic_modifier", owner)
            effects_used.setdefault("add_dynamic_modifier", owner)
            continue
        if effect == "fortify":
            # fuertes en todas las regiones propias (edificio de provincia, en las fronteras)
            building = item.get("building", "bunker")
            if ec.buildings and building not in ec.buildings:
                if ec.warn:
                    ec.warn(f"{owner}: el edificio '{building}' no existe en este juego; no se fortifica.")
                continue
            prov = Block([("all_provinces", True)])
            if item.get("border_only", True):
                prov.add("limit_to_border", True)
            construction = Block([("type", building), ("level", int(item.get("level", 1))),
                                  ("province", prov), ("instant_build", True)])
            block.add("every_owned_state", Block([("add_building_construction", construction)]))
            effects_used.setdefault("every_owned_state", owner)
            effects_used.setdefault("add_building_construction", owner)
            continue
        if effect == "division_template":
            regs = Block()
            for i, r in enumerate(item["regiments"]):
                regs.add(r, Block([("x", i // 5), ("y", i % 5)]))
            tpl = Block([("name", Quoted(template_token(item["name"]))), ("regiments", regs)])
            if item.get("support"):
                sup = Block()
                for i, r in enumerate(item["support"]):
                    sup.add(r, Block([("x", 0), ("y", i)]))
                tpl.add("support", sup)
            block.add("division_template", tpl)
            effects_used.setdefault("division_template", owner)
            continue
        if effect == "ensure_template":
            # La plantilla, solo si el país ya no la tiene (error.log 2026-10-01:
            # la IA borra o renombra "Milicia" y las levas fallaban). has_template
            # no se verifica contra la documentación: si faltara, lo dice error.log.
            regs = Block()
            for i, r in enumerate(item["regiments"]):
                regs.add(r, Block([("x", i // 5), ("y", i % 5)]))
            name = template_token(item["name"])
            block.add("if", Block([
                ("limit", Block([("NOT", Block([("has_template", Quoted(name))]))])),
                ("division_template", Block([("name", Quoted(name)), ("regiments", regs)]))]))
            effects_used.setdefault("division_template", owner)
            continue
        if effect == "create_units":
            # create_unit solo vale en scope de state (error.log 2026-09-29:
            # "create_unit -- invalid scope state" en los focos de la Anarquía):
            # las divisiones salen en la capital, o en cualquier state propio
            # controlado si la capital está ocupada. PREV es el país.
            def units() -> Block:
                out = Block()
                for i in range(int(item["count"])):
                    # error.log 2026-09-30: "Malformed token: Milicia" / "division
                    # string was not parsed correctly" con las comillas internas.
                    # Si el nombre de la plantilla es una sola palabra va sin
                    # comillas y sin nombre de división (el juego le pone uno).
                    xp = float(item.get("experience", 0.3))
                    div = f"division_template = {template_token(item['template'])} start_experience_factor = {xp}"
                    out.add("create_unit", Block([("division", Quoted(div)), ("owner", "PREV")]))
                return out
            if item.get("zones"):
                # 2026-10-02 (Tierras Sin Ley): en cada zona, en la primera de
                # sus regiones que el país todavía controle; zona perdida, nada.
                for zone in item["zones"]:
                    ids = [i for i in (resolve_state(n) for n in zone) if i is not None]
                    if not ids:
                        continue
                    def branch(rest: list[int]) -> Block:
                        i = rest[0]
                        b = Block([("limit", Block([(str(i), Block([("is_controlled_by", "ROOT"),
                                                                    ("is_owned_by", "ROOT")]))])),
                                   (str(i), units())])
                        return b
                    out = None
                    for i in reversed(ids):
                        b = branch([i])
                        if out is not None:
                            b_else = Block([("if", out[0])] + ([("else", out[1])] if out[1] is not None else []))
                            out = (b, b_else)
                        else:
                            out = (b, None)
                    block.add("if", out[0])
                    if out[1] is not None:
                        block.add("else", out[1])
                for k in ("create_unit",):
                    effects_used.setdefault(k, owner)
                ec.triggers_used.setdefault("is_controlled_by", owner)
                ec.triggers_used.setdefault("is_owned_by", owner)
                continue
            block.add("if", Block([
                ("limit", Block([("capital_scope", Block([("is_controlled_by", "PREV")]))])),
                ("capital_scope", units())]))
            block.add("else", Block([("random_owned_controlled_state", units())]))
            for k in ("create_unit", "random_owned_controlled_state"):
                effects_used.setdefault(k, owner)
            ec.triggers_used.setdefault("is_controlled_by", owner)
            continue
        if effect == "civil_war":
            # Guerra civil (2026-09-29). El país que juega es siempre el bando
            # que eligió: el otro bando es el que se separa (start_civil_war).
            # El que se separa toma nombre y bandera propios (cosmetic tag) y su
            # líder se renombra con el retrato del personaje.
            tag = item["tag"]
            # memoria de lo que el país tiene al empezar (ver civil_war_restore)
            for idea in _CW_IDEAS.get(tag, []):
                block.add("if", Block([("limit", Block([("has_idea", idea)])),
                                       ("set_global_flag", f"MN_cw_{idea}")]))
            for var in _CW_VARS.get(tag, []):
                block.add("set_variable", Block([("var", f"global.MN_cw_{var}"), ("value", var)]))
            block.add("set_country_flag", f"{tag}_cw_origen")
            for k in ("set_global_flag", "set_variable", "set_country_flag"):
                effects_used.setdefault(k, owner)
            ec.triggers_used.setdefault("has_idea", owner)
            inner = Block([("ideology", item["ideology"]), ("size", float(item.get("size", 0.35)))])
            block.add("start_civil_war", inner)
            rebels = item.get("rebels") or {}
            rb = Block([("limit", Block([("original_tag", tag), ("NOT", Block([("tag", tag)])),
                                         ("has_civil_war", True)]))])
            if rebels.get("cosmetic_tag"):
                rb.add("set_cosmetic_tag", rebels["cosmetic_tag"])
            leader = rebels.get("leader") or {}
            if leader.get("name"):
                key = f"{rebels.get('cosmetic_tag', tag)}_leader"
                TOOLTIPS[key] = (leader["name"]["english"], leader["name"]["spanish"])
                # efectos 1.12+: no se verifican contra documentation/ (si faltaran, el
                # juego solo lo anota en error.log; la guerra civil sale igual)
                rb.add("set_country_leader_name", Block([("name", key)]))
            if leader.get("portrait"):
                rb.add("set_country_leader_portrait", Block([("portrait", portrait_sprite(leader["portrait"]))]))
            if rebels.get("effects"):
                rb.entries.extend(render_effects(owner, rebels["effects"], ec, effects_used, where=where).entries)
            block.add("random_country", rb)
            if item.get("global_flag"):
                block.add("set_global_flag", item["global_flag"])
                effects_used.setdefault("set_global_flag", owner)
            for k in ("start_civil_war", "random_country", "set_cosmetic_tag"):
                effects_used.setdefault(k, owner)
            for k in ("original_tag", "tag", "has_civil_war"):
                ec.triggers_used.setdefault(k, owner)
            continue
        if effect == "civil_war_restore":
            # El ganador recupera los espíritus que el país tenía al empezar la
            # guerra y le faltan; si el ganador es el otro bando (no tiene la
            # bandera de origen), también las variables de la mecánica.
            tag = item["tag"]
            for idea in _CW_IDEAS.get(tag, []):
                block.add("if", Block([("limit", Block([("has_global_flag", f"MN_cw_{idea}"),
                                                        ("NOT", Block([("has_idea", idea)]))])),
                                       ("add_ideas", idea)]))
                block.add("clr_global_flag", f"MN_cw_{idea}")
            if _CW_VARS.get(tag):
                sets = Block([("limit", Block([("NOT", Block([("has_country_flag", f"{tag}_cw_origen")]))]))])
                for var in _CW_VARS[tag]:
                    sets.add("set_variable", Block([("var", var), ("value", f"global.MN_cw_{var}")]))
                block.add("if", sets)
            for k in ("add_ideas", "clr_global_flag", "set_variable"):
                effects_used.setdefault(k, owner)
            for k in ("has_global_flag", "has_idea", "has_country_flag"):
                ec.triggers_used.setdefault(k, owner)
            continue
        if effect == "mio_reset":
            # OIM (2026-09-30): common/on_actions/09_aat_on_actions.txt les suma
            # tamaño al arrancar según la fecha (add_mio_size = 3 y 4), y en 2100
            # todas arrancaban con 4 puntos. Una sola vez, para todos los países,
            # se las baja de a uno hasta 1. Sintaxis de documentation/ (1.19.3):
            # add_mio_size y has_mio_size en scope de la OIM; no se verifican
            # contra la lista (si faltaran, lo dice error.log sin romper el mod).
            steps = Block()
            for _ in range(int(item.get("steps", 6))):
                steps.add("if", Block([("limit", Block([("has_mio_size", Compare(">", 1))])),
                                       ("add_mio_size", -1)]))
            block.add("if", Block([
                ("limit", Block([("NOT", Block([("has_global_flag", "MN_mio_reset")]))])),
                ("set_global_flag", "MN_mio_reset"),
                ("every_country", Block([("every_military_industrial_organization", steps)])),
            ]))
            continue
        if effect == "intelligence_agency":
            # todas las meganaciones arrancan con su agencia de inteligencia
            # (La Résistance), una sola vez.
            block.add("if", Block([("limit", Block([("NOT", Block([("has_intelligence_agency", True)]))])),
                                   ("create_intelligence_agency", True)]))
            effects_used.setdefault("create_intelligence_agency", owner)
            ec.triggers_used.setdefault("has_intelligence_agency", owner)
            continue
        if effect == "cosmetic_tag":
            # nombre y bandera nuevos (02_countries.yaml -> cosmetic_tags)
            block.add("set_cosmetic_tag", item["value"])
            effects_used.setdefault("set_cosmetic_tag", owner)
            continue
        if effect == "white_peace_all":
            # Paz blanca con todos los enemigos; antes, cada uno se queda con lo
            # que controla (lo propio ocupado pasa al ocupante y al revés).
            block.add("every_owned_state", Block([
                ("limit", Block([("NOT", Block([("is_controlled_by", "ROOT")]))])),
                ("CONTROLLER", Block([("transfer_state", "PREV")]))]))
            block.add("every_state", Block([
                ("limit", Block([("is_controlled_by", "ROOT"), ("NOT", Block([("is_owned_by", "ROOT")]))])),
                ("ROOT", Block([("transfer_state", "PREV")]))]))
            block.add("every_enemy_country", Block([("white_peace", "ROOT")]))
            for k in ("every_owned_state", "every_state", "every_enemy_country", "transfer_state", "white_peace"):
                effects_used.setdefault(k, owner)
            ec.triggers_used.setdefault("is_controlled_by", owner)
            ec.triggers_used.setdefault("is_owned_by", owner)
            continue
        if effect == "or_cores":
            # Análisis 2026-10-01: un foco que pide que exista una anarquía o un
            # satélite quedaba gris para siempre si otro se lo comía antes. Ahora
            # el foco se toma igual: si el país sigue como se espera, `then`; si
            # no, núcleos en lo que ya es tuyo de su tierra y reclamos sobre el
            # resto (y si es satélite tuyo, se anexa primero).
            #   kind: anarchy   -> "sigue" = existe y no es satélite de nadie
            #   kind: satellite -> "sigue" = existe y es satélite de ROOT
            target, kind = item["country"], item.get("kind", "anarchy")
            if ec.tags and target not in ec.tags:
                raise SpecError(f"{owner}: or_cores sobre '{target}', que no es un pais del mod", where=where)
            if kind not in ("anarchy", "satellite"):
                raise SpecError(f"{owner}: or_cores.kind '{kind}' (anarchy o satellite)", where=where)
            alive = Block([("country_exists", target)])
            alive.add(target, Block([("is_subject", False)]) if kind == "anarchy"
                      else Block([("is_subject_of", "ROOT")]))
            gone = Block()
            if kind == "anarchy":
                gone.add("if", Block([
                    ("limit", Block([("country_exists", target), (target, Block([("is_subject_of", "ROOT")]))])),
                    ("annex_country", Block([("target", target), ("transfer_troops", True)]))]))
                effects_used.setdefault("annex_country", owner)
            gone.add("every_owned_state", Block([
                ("limit", Block([("is_core_of", target)])), ("add_core_of", "ROOT")]))
            # spare: países cuyas regiones no se reclaman (el Santuario que el EFE juró proteger)
            spare = list(item.get("spare") or [])
            for t in spare:
                if ec.tags and t not in ec.tags:
                    raise SpecError(f"{owner}: or_cores.spare '{t}' no es un pais del mod", where=where)
            gone.add("every_state", Block([
                ("limit", Block([("is_core_of", target),
                                 ("NOT", Block([("is_owned_by", t) for t in ["ROOT"] + spare]))])),
                ("add_claim_by", "ROOT")]))
            gone.entries.extend(render_effects(owner, item.get("gone") or [], ec, effects_used, where=where).entries)
            then = render_effects(owner, item.get("then") or [], ec, effects_used, where=where)
            if then.entries:
                block.add("if", Block([("limit", alive)] + then.entries))
                block.add("else", gone)
            else:
                # sin premio normal: solo el camino alternativo
                block.add("if", Block([("limit", Block([("NOT", Block([("AND", alive)]))]))] + gone.entries))
            for k in ("every_owned_state", "every_state", "add_core_of", "add_claim_by"):
                effects_used.setdefault(k, owner)
            for k in ("country_exists", "is_subject", "is_subject_of", "is_core_of", "is_owned_by"):
                ec.triggers_used.setdefault(k, owner)
            continue
        if effect == "add_to_war_of":
            # `who` entra en todas las guerras que tiene `ally` (contra sus enemigos)
            ally, who = item["ally"], item.get("who", "ROOT")
            block.add(ally, Block([("every_enemy_country", Block([
                (who, Block([("add_to_war", Block([("targeted_alliance", ally), ("enemy", "PREV")]))]))]))]))
            effects_used.setdefault("every_enemy_country", owner)
            effects_used.setdefault("add_to_war", owner)
            continue
        if effect == "armistice":
            # Paz con `value` y los suyos: cada país de su bando (él, sus
            # satélites, su facción) firma con cada país del bando de ROOT que
            # esté en guerra con él, y cada uno se queda con lo que ocupa del
            # otro. Firmar solo entre las dos potencias dejaba a los satélites
            # peleando y la guerra seguía (revisión 2026-09-29).
            # 2026-10-08: el traspaso iba por event_target guardados dentro de
            # los bucles y en la partida no pasaba nada (el EFE le ganaba a la
            # NAS y volvían al status quo). Ahora se recorre cada state y se le
            # entrega a quien lo controla (OWNER/CONTROLLER), sin event_target.
            other = item["value"]
            if ec.tags and other not in ec.tags and other not in SCOPES:
                raise SpecError(f"{owner}: armistice con '{other}', que no es un pais del mod", where=where)

            def side(leader: str) -> Block:
                return Block([("OR", Block([("tag", leader), ("is_subject_of", leader),
                                            ("is_in_faction_with", leader)]))])
            for holder, loser in (("ROOT", other), (other, "ROOT")):
                block.add("every_state", Block([
                    ("limit", Block([("OWNER", side(loser)), ("CONTROLLER", side(holder))])),
                    ("CONTROLLER", Block([("transfer_state", "PREV")]))]))
            block.add("every_country", Block([
                ("limit", side(other)),
                ("every_enemy_country", Block([
                    ("limit", side("ROOT")),
                    ("white_peace", "PREV"),
                    # tregua de verdad: el juego no deja volver a declarar en ese plazo
                    ("set_truce", Block([("target", "PREV"), ("days", int(item.get("truce_days", 364)))]))]))]))
            for k in ("every_state", "every_country", "every_enemy_country", "transfer_state", "white_peace",
                      "set_truce"):
                effects_used.setdefault(k, owner)
            for k in ("tag", "is_subject_of", "is_in_faction_with"):
                ec.triggers_used.setdefault(k, owner)
            continue
        if effect == "add_slot":
            # en una región: un espacio de construcción compartido más
            block.add("add_extra_state_shared_building_slots", int(item.get("value", 1)))
            effects_used.setdefault("add_extra_state_shared_building_slots", owner)
            continue
        if effect == "leave_faction":
            block.add("leave_faction", True)
            effects_used.setdefault("leave_faction", owner)
            continue
        if effect in ("guarantee", "relation"):
            # el país del scope garantiza a `value` (el Santuario de Gaia, 2026-09-29);
            # relation: otra relación (non_aggression_pact, military_access) con
            # `value` (los pactos entre potencias, 2026-10-02)
            target = item["value"]
            if ec.tags and target not in ec.tags and target not in SCOPES:
                raise SpecError(f"{owner}: {effect} con '{target}', que no es un pais del mod", where=where)
            kind = "guarantee" if effect == "guarantee" else item["type"]
            if kind not in RELATIONS:
                raise SpecError(f"{owner}: relation.type '{kind}' ({', '.join(sorted(RELATIONS))})", where=where)
            rel = Block([("country", target), ("relation", kind), ("active", True)])
            if kind == "guarantee" and target not in SCOPES:
                # error.log 2026-10-03: "The relation(guarantee) already exists"
                block.add("if", Block([("limit", Block([("NOT", Block([("has_guaranteed", target)]))])),
                                       ("diplomatic_relation", rel)]))
                ec.triggers_used.setdefault("has_guaranteed", owner)
            else:
                block.add("diplomatic_relation", rel)
            effects_used.setdefault("diplomatic_relation", owner)
            continue
        if effect == "resource_here":
            # en una región: suma un recurso a ESA región
            resource = item["resource"]
            if ec.resources and resource not in ec.resources:
                raise SpecError(f"{owner}: recurso '{resource}' desconocido", where=where)
            block.add("add_resource", Block([("type", resource), ("amount", int(item.get("amount", 1)))]))
            effects_used.setdefault("add_resource", owner)
            continue
        if effect == "end_guarantee":
            # el país del scope deja de garantizar a `value`
            block.add("diplomatic_relation", Block([("country", item["value"]), ("relation", "guarantee"), ("active", False)]))
            effects_used.setdefault("diplomatic_relation", owner)
            continue
        if effect == "create_faction":
            block.add("create_faction", Quoted(item["value"]))
            effects_used.setdefault("create_faction", owner)
            continue
        if effect == "add_to_faction":
            block.add("add_to_faction", item["value"])
            effects_used.setdefault("add_to_faction", owner)
            continue
        if effect == "equipment":
            # equipo al depósito (arquetipo o variante): add_equipment_to_stockpile
            inner = Block()
            inner.add("type", item["type"])
            inner.add("amount", int(item["amount"]))
            block.add("add_equipment_to_stockpile", inner)
            effects_used.setdefault("add_equipment_to_stockpile", owner)
            continue
        if effect == "idea_tiers":
            # Niveles excluyentes de una idea: gana el primer nivel cuya
            # condición se cumple. Solo se quita o se pone lo que cambia, así
            # el tooltip no muestra "quita X / pone X" cuando nada cambia
            # (HOI4 evalúa los `limit` al mostrar el tooltip).
            tiers = item["tiers"]
            effective = []
            for i, tier in enumerate(tiers):
                earlier = [t.get("when") or {} for t in tiers[:i]]
                parts = [tier.get("when") or {}]
                if earlier:
                    parts.append({"not": {"any": earlier}} if all(earlier) else {"always": False})
                effective.append({"all": parts})
            for tier, eff in zip(tiers, effective):
                if ec.known_ideas and tier["idea"] not in ec.known_ideas:
                    raise SpecError(f"{owner}: idea_tiers usa '{tier['idea']}', que no existe", where=where)
                remove = Block()
                remove.add("limit", render_conditions(owner, {"all": [{"idea": tier["idea"]}, {"not": eff}]},
                                                      ec.triggers_used, where=where))
                remove.add("remove_ideas", tier["idea"])
                block.add("if", remove)
            for tier, eff in zip(tiers, effective):
                add = Block()
                add.add("limit", render_conditions(owner, {"all": [{"not_idea": tier["idea"]}, eff]},
                                                   ec.triggers_used, where=where))
                add.add("add_ideas", tier["idea"])
                block.add("if", add)
            effects_used.setdefault("remove_ideas", owner)
            effects_used.setdefault("add_ideas", owner)
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
      flags: [X, Y]                       -> todas esas banderas
      at_war: true|false                  -> has_war
      idea / not_idea: X                  -> has_idea
      focus: X                            -> has_completed_focus
      country_exists: TAG
      core_of / not_core_of: TAG          -> is_core_of (en regiones)
      state_flag / not_state_flag: X      -> has_state_flag (en regiones)
      state_flag_days: { flag, days }     -> has_state_flag = { flag days > N }
      stability_below: 0.4                -> has_stability < 0.4
      divisions_at_least: 12              -> has_army_size = { size > 11 }
      factories_at_least: 60              -> num_of_factories > 59
      tech: X                             -> has_tech = X (validada contra el árbol)
      manpower_at_least: 500000           -> has_manpower > 499999
      war_support_at_least: 0.6           -> has_war_support > 0.6
      equipment_at_least: {type, amount}  -> has_equipment = { type > amount-1 }
      date_after: "2105.1.1"              -> date > 2105.1.1
      capitulated: true                   -> has_capitulated
      controls_state: [nombres]           -> controls_state (región por nombre)
      war_with: TAG                       -> has_war_with
      controls_all: [[nombres], ..]       -> controla todas esas regiones
      neighbor_state_flag: X              -> any_neighbor_state tiene esa bandera (en regiones)
      country: { tag, when: {..} }        -> TAG = { .. }
      any: [ {..}, {..} ]                 -> OR
      not: { .. }                         -> NOT (no se cumplen todas juntas)
      explained: { id, english, spanish, when: {..} } -> custom_trigger_tooltip
                                          (el requisito se lee con ese texto, no con el nombre de la bandera)
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
        elif key == "flags":
            for f in value:
                block.add("has_country_flag", f)
            triggers_used.setdefault("has_country_flag", owner)
        elif key in ("flag", "not_flag"):
            if key == "flag":
                block.add("has_country_flag", value)
            else:
                block.add("NOT", Block([("has_country_flag", value)]))
            triggers_used.setdefault("has_country_flag", owner)
        elif key in ("global_flag", "not_global_flag"):
            if key == "global_flag":
                block.add("has_global_flag", value)
            else:
                block.add("NOT", Block([("has_global_flag", value)]))
            triggers_used.setdefault("has_global_flag", owner)
        elif key == "exists":
            block.add("exists", bool(value))
            triggers_used.setdefault("exists", owner)
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
            if KNOWN_FOCUSES and value not in KNOWN_FOCUSES:
                raise SpecError(f"{owner}: la condicion pide el foco '{value}', que no existe en ningun arbol",
                                where=where)
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
        elif key == "flag_older":
            # has_country_flag = { flag = X days > N }: la bandera se puso hace más
            # de N días (freno de repetición que no depende de que la bandera venza)
            block.add("has_country_flag", Block([("flag", value["flag"]), ("days", Compare(">", int(value["days"])))]))
            triggers_used.setdefault("has_country_flag", owner)
        elif key == "state_flag_days":
            inner = Block()
            inner.add("flag", value["flag"])
            inner.add("days", Compare(">", int(value["days"])))
            block.add("has_state_flag", inner)
            triggers_used.setdefault("has_state_flag", owner)
        elif key == "controls_state":
            sid = resolve_state(value)
            if sid is None:
                block.add("always", False)
            else:
                block.add("controls_state", sid)
                triggers_used.setdefault("controls_state", owner)
        elif key == "owns_state":
            # es dueño de la región (nombres alternativos de UNA región)
            sid = resolve_state(value)
            if sid is None:
                block.add("always", False)
            else:
                block.add("owns_state", sid)
                triggers_used.setdefault("owns_state", owner)
        elif key == "owned_by":
            # en una región: su dueño es `value`
            block.add("is_owned_by", value)
            triggers_used.setdefault("is_owned_by", owner)
        elif key == "guarantees":
            block.add("has_guaranteed", value)
            triggers_used.setdefault("has_guaranteed", owner)
        elif key == "controls_any_of":
            # controla al menos una región de las que `value` tenía al arranque
            ids = sorted(sid for sid, tag in _TERRITORY.items() if tag == value)
            if not ids:
                block.add("always", False)
            else:
                block.add("OR", Block([("controls_state", i) for i in ids]))
                triggers_used.setdefault("controls_state", owner)
        elif key == "is_ai":
            block.add("is_ai", bool(value))
            triggers_used.setdefault("is_ai", owner)
        elif key == "infrastructure_below":
            # en una región: todavía hay lugar para infraestructura (el máximo es
            # 5). Es la condición del foco genérico infrastructure_effort.
            block.add("free_building_slots", Block([
                ("building", "infrastructure"), ("size", Compare(">", max(0, 5 - int(value)))),
                ("include_locked", True)]))
            triggers_used.setdefault("free_building_slots", owner)
        elif key == "surrender_at_least":
            block.add("surrender_progress", Compare(">", float(value)))
            triggers_used.setdefault("surrender_progress", owner)
        elif key == "in_faction_with":
            block.add("is_in_faction_with", value)
            triggers_used.setdefault("is_in_faction_with", owner)
        elif key == "war_with":
            block.add("has_war_with", value)
            triggers_used.setdefault("has_war_with", owner)
        elif key == "country":
            block.add(value["tag"], render_conditions(owner, value["when"], triggers_used, where=where))
        elif key == "tag":
            block.add("tag", value)
            triggers_used.setdefault("tag", owner)
        elif key == "major":
            block.add("is_major", bool(value))
            triggers_used.setdefault("is_major", owner)
        elif key == "subject_of":
            # el lado del satélite (2026-09-29): sigue siendo satélite de `value`
            block.add("is_subject_of", value)
            triggers_used.setdefault("is_subject_of", owner)
        elif key == "civil_war":
            block.add("has_civil_war", bool(value))
            triggers_used.setdefault("has_civil_war", owner)
        elif key == "subject":
            # es satélite de alguien (cualquiera)
            block.add("is_subject", bool(value))
            triggers_used.setdefault("is_subject", owner)
        elif key == "neighbor_state_flag":
            block.add("any_neighbor_state", Block([("has_state_flag", value)]))
            triggers_used.setdefault("any_neighbor_state", owner)
            triggers_used.setdefault("has_state_flag", owner)
        elif key == "controls_all":
            for names in value:
                sid = resolve_state(names)
                if sid is None:
                    block.add("always", False)
                else:
                    block.add("controls_state", sid)
                    triggers_used.setdefault("controls_state", owner)
        elif key == "coastal":
            block.add("is_coastal", bool(value))
            triggers_used.setdefault("is_coastal", owner)
        elif key == "factories_at_least":
            block.add("num_of_factories", Compare(">", int(value) - 1))
            triggers_used.setdefault("num_of_factories", owner)
        elif key == "tech":
            block.add("has_tech", value)
            triggers_used.setdefault("has_tech", owner)
        elif key == "manpower_at_least":
            block.add("has_manpower", Compare(">", int(value) - 1))
            triggers_used.setdefault("has_manpower", owner)
        elif key == "war_support_at_least":
            block.add("has_war_support", Compare(">", float(value)))
            triggers_used.setdefault("has_war_support", owner)
        elif key == "equipment_at_least":
            block.add("has_equipment", Block([(value["type"], Compare(">", int(value["amount"]) - 1))]))
            triggers_used.setdefault("has_equipment", owner)
        elif key == "date_after":
            block.add("date", Compare(">", str(value)))
            triggers_used.setdefault("date", owner)
        elif key == "capitulated":
            block.add("has_capitulated", bool(value))
            triggers_used.setdefault("has_capitulated", owner)
        elif key == "divisions_at_least":
            # has_army_size = { size > N-1 }: cuenta divisiones de tierra
            block.add("has_army_size", Block([("size", Compare(">", int(value) - 1))]))
            triggers_used.setdefault("has_army_size", owner)
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
        elif key == "all":
            # lista de condiciones que se cumplen todas (para combinar la misma clave dos veces)
            for sub in value:
                block.entries.extend(render_conditions(owner, sub, triggers_used, where=where).entries)
        elif key == "always":
            block.add("always", bool(value))
        elif key == "not":
            inner = render_conditions(owner, value, triggers_used, where=where)
            # NOT = { A B } en HOI4 es "ninguna"; "no se cumplen todas" es NOT = { AND = {A B} }.
            block.add("NOT", inner if len(inner.entries) == 1 else Block([("AND", inner)]))
        elif key == "explained":
            tip = f"MN_tt_req_{value['id']}"
            TOOLTIPS[tip] = (value["english"], value["spanish"])
            inner = render_conditions(owner, value["when"], triggers_used, where=where)
            block.add("custom_trigger_tooltip", Block([("tooltip", tip)] + inner.entries))
        elif key == "stability_at_least":
            block.add("has_stability", Compare(">", float(value)))
            triggers_used.setdefault("has_stability", owner)
        else:
            raise SpecError(f"{owner}: condicion desconocida '{key}'", where=where)
    return block


def dynamic_modifier_ids(spec_raw: dict) -> set[str]:
    return {m["id"] for m in (spec_raw.get("decisions") or {}).get("dynamic_modifiers") or []}


# efectos que escribe el generador mismo (no están en 14_decisions.yaml)
GENERATED_SCRIPTED = {"MEGANATIONS_renovar_casus_belli"}


def scripted_effect_ids(spec_raw: dict) -> set[str]:
    unique = {f"{u['id']}_desbloqueo" for u in (spec_raw.get("unique_units") or {}).get("units") or []}
    return {e["id"] for e in (spec_raw.get("decisions") or {}).get("scripted_effects") or []} | GENERATED_SCRIPTED | unique
