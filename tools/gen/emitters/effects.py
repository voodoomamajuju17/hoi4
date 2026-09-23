"""Efectos en formato spec -> Paradox script. Lo usan focos y eventos.

Formato del spec: lista de { effect, value } o uno de los compuestos:
  { effect: swap_ideas, remove, add }
  { effect: annex, target: TAG }                 -> annex_country
  { effect: wargoal, target: TAG, type: X }      -> create_wargoal
  { effect: build, building: X, level: N }       -> en la capital, con slots
  { effect: add_resource, resource: X, amount: N } -> en la capital (id resuelto en el build) Los efectos se validan contra
documentation/ del juego (verify_keys) y los ids de idea contra 05_ideas.yaml.
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
                 capital: int | None = None, resources: set[str] | None = None, warn=None):
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
            scope.add("add_extra_state_shared_building_slots", level)
            scope.add("add_building_construction", construction)
            block.add("capital_scope", scope)
            effects_used.setdefault("add_extra_state_shared_building_slots", owner)
            effects_used.setdefault("add_building_construction", owner)
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
