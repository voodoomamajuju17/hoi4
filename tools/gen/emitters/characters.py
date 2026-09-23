"""Personajes (common/characters/, sintaxis moderna — TN003).

Produce:
  common/characters/<TAG>_characters.txt
  gfx/leaders/<TAG>/<archivo>.dds    retrato placeholder
  localisation del nombre visible

Solo se emiten los personajes con `id` en 03_leaders.yaml. Las entradas sin id
son huecos declarados (Q016): no se inventa un líder para taparlos, el juego
genera uno genérico.

Traits: el doc no da ninguno (Q015) y un trait inexistente rompe la carga
(TN004), así que el bloque sale vacío.
"""

from __future__ import annotations

from ..art import write_dds
from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted

SOURCE = "spec/03_leaders.yaml"
LOC_FILE = "meganations_characters"

# Tamaño estándar de retrato de líder en HOI4.
PORTRAIT_SIZE = (156, 210)


def defined_characters(ctx: BuildContext) -> list[dict]:
    return [ch for ch in ctx.spec.raw["leaders"].get("characters", []) or [] if ch.get("id")]


def leaders_of(ctx: BuildContext, tag: str) -> list[dict]:
    return [
        ch for ch in defined_characters(ctx)
        if ch["country"] == tag and isinstance((ch.get("roles") or {}).get("country_leader"), dict)
    ]


def emit(ctx: BuildContext) -> None:
    types, _ = ctx.spec.ideology_index()
    by_country: dict[str, list[dict]] = {}
    for ch in defined_characters(ctx):
        by_country.setdefault(ch["country"], []).append(ch)

    for tag in sorted(by_country):
        country = ctx.spec.country(tag)
        characters = Block()
        for ch in by_country[tag]:
            cid = ch["id"]
            body = Block()
            body.add("name", ctx.loc.reference(cid, f"characters:{cid}"))

            portrait_path = (ch.get("portrait") or {}).get("path")
            if portrait_path:
                _write_portrait(ctx, portrait_path, country.color)
                large = Block()
                large.add("large", Quoted(portrait_path))
                portraits = Block()
                portraits.add("civilian", large)
                body.add("portraits", portraits)

            leader = (ch.get("roles") or {}).get("country_leader")
            if isinstance(leader, dict):
                ideology = leader.get("ideology")
                if ideology not in types:
                    raise SpecError(
                        f"{cid}: ideologia de lider '{ideology}' no existe en 01_ideologies.yaml",
                        where="03_leaders.yaml",
                    )
                if ideology != country.ideology:
                    ctx.warn(
                        f"{cid} lidera con '{ideology}' pero {tag} arranca en "
                        f"'{country.ideology}'. Ver TN001."
                    )
                role = Block()
                role.add("ideology", ideology)
                role.add("traits", Block())
                body.add("country_leader", role)

            characters.add(cid, body)

            regnal = (ch.get("name") or {}).get("regnal")
            if not isinstance(regnal, dict):
                raise SpecError(f"{cid}: falta name.regnal en EN y ES", where="03_leaders.yaml")
            ctx.loc.define(cid, en=regnal["english"], es=regnal["spanish"],
                           file=LOC_FILE, origin=f"characters:{cid}")

        root = Block()
        root.add("characters", characters)
        ctx.write_script(f"common/characters/{tag}_characters.txt", root, source=SOURCE)


def _write_portrait(ctx: BuildContext, relative: str, color: tuple[int, int, int]) -> None:
    """Retrato placeholder: fondo liso del color del país, con un marco claro.

    Se lee como placeholder a propósito (regla de arte del proyecto).
    """
    w, h = PORTRAIT_SIZE
    frame = tuple(min(255, int(c * 1.5) + 40) for c in color)
    pixels = [
        frame if x < 4 or y < 4 or x >= w - 4 or y >= h - 4 else color
        for y in range(h)
        for x in range(w)
    ]
    path = ctx.mod_root / relative
    write_dds(path, w, h, pixels)
    ctx.track(path)
