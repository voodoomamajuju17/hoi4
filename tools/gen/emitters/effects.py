"""Efectos en formato spec -> Paradox script. Lo usan focos y eventos.

Formato del spec: lista de { effect, value } o
{ effect: swap_ideas, remove, add }. Los efectos se validan contra
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
}


def render_effects(owner: str, items: list[dict], known_ideas: set[str],
                   effects_used: dict[str, str], *, where: str) -> Block:
    block = Block()
    for item in items:
        effect = item.get("effect")
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
