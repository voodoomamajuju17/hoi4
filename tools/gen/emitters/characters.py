"""Personajes (common/characters/, sintaxis moderna — TN003).

Produce:
  common/characters/<TAG>_characters.txt
  gfx/leaders/<TAG>/<archivo>.dds    retrato placeholder
  localisation del nombre visible

Solo se emiten los personajes con `id` en 03_leaders.yaml. Las entradas sin id
son huecos declarados (Q016): no se inventa un líder para taparlos, el juego
genera uno genérico.

Traits: propios del mod (03_leaders.yaml -> leader_traits), escritos en
  common/country_leader/meganations_traits.txt
Un trait vanilla escrito de memoria rompe la carga si no existe (TN004); uno
propio lo definimos nosotros. Un personaje que pide un trait que no está en
leader_traits frena el build.
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


TRAITS_SOURCE = "spec/03_leaders.yaml -> leader_traits"


def _emit_traits(ctx: BuildContext) -> set[str]:
    traits = ctx.spec.raw["leaders"].get("leader_traits") or []
    if not traits:
        return set()
    if ctx.vanilla is not None:
        found = any(
            "leader_traits" in p.read_text(encoding="utf-8-sig", errors="replace")
            for p in (ctx.vanilla.root / "common" / "country_leader").glob("*.txt")
        )
        if not found:
            raise SpecError("common/country_leader/ del juego no usa 'leader_traits': cambio el formato",
                            where="03_leaders.yaml")
    body = Block()
    modifiers_used: dict[str, str] = {}
    for trait in traits:
        tid = trait["id"]
        tb = Block()
        tb.add("random", False)
        for key, value in (trait.get("modifiers") or {}).items():
            tb.add(key, float(value))
            modifiers_used.setdefault(key, tid)
        body.add(ctx.loc.reference(tid, f"traits:{tid}"), tb)
        ctx.loc.define(tid, en=trait["name"]["english"], es=trait["name"]["spanish"],
                       file=LOC_FILE, origin=f"traits:{tid}")
    root = Block()
    root.add("leader_traits", body)
    ctx.write_script("common/country_leader/meganations_traits.txt", root, source=TRAITS_SOURCE)
    ctx.verify_keys("modifiers", modifiers_used)
    return {t["id"] for t in traits}


def emit(ctx: BuildContext) -> None:
    known_traits = _emit_traits(ctx)
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
                traits = Block()
                wanted = leader.get("traits")
                for trait in wanted if isinstance(wanted, list) else []:
                    if trait not in known_traits:
                        raise SpecError(f"{cid}: el trait '{trait}' no esta en leader_traits",
                                        where="03_leaders.yaml")
                    traits.add(None, trait)
                role.add("traits", traits)
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
