"""Escenario de 2100: bookmark propio y fechas del juego.

Produce:
  common/bookmarks/meganations_2100.txt
  common/defines/00_meganations_defines.lua
  localisation del nombre, la descripción y la historia de cada país destacado

El bookmark usa el vanilla como plantilla: de ahí salen `picture` y el bloque
`effect` (clima aleatorio), y se verifica que los campos que emitimos existan
en el bookmark del juego. Sin --vanilla-path se emite igual con valores
vanilla conocidos y se avisa, porque el descriptor reemplaza common/bookmarks
entero y un mod sin ningún bookmark no arranca partida.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted, parse_file
from . import focus_trees as focus_mod
from . import ideas as ideas_mod

SOURCE = "spec/11_scenario.yaml"
LOC_FILE = "meganations_scenario"
FALLBACK_PICTURE = "GFX_select_date_1936"
EMITTED_FIELDS = ("name", "desc", "date", "picture", "default_country")


def emit(ctx: BuildContext) -> None:
    scenario = ctx.spec.raw["scenario"]
    _emit_defines(ctx, scenario["game_dates"])
    _emit_bookmark(ctx, scenario["bookmark"])


def _emit_defines(ctx: BuildContext, dates: dict) -> None:
    if ctx.vanilla is not None:
        defines = ctx.vanilla.root / "common" / "defines" / "00_defines.lua"
        if defines.exists():
            text = defines.read_text(encoding="utf-8-sig", errors="replace")
            for key in ("START_DATE", "END_DATE"):
                if f"{key} =" not in text and f"{key}=" not in text:
                    raise SpecError(f"NGame.{key} no existe en 00_defines.lua de esta version",
                                    where="11_scenario.yaml")
    lines = [
        "-- ARCHIVO GENERADO - NO EDITAR A MANO",
        f"-- Fuente: {SOURCE}. Para cambiarlo, edita el spec y corre: make build",
        "",
        f'NDefines.NGame.START_DATE = "{dates["start"]}"',
        f'NDefines.NGame.END_DATE = "{dates["end"]}"',
        "",
    ]
    ctx.write_text("common/defines/00_meganations_defines.lua", "\n".join(lines))


def _vanilla_bookmarks(ctx: BuildContext) -> list[Block]:
    if ctx.vanilla is None:
        return []
    out: list[Block] = []
    for path in sorted((ctx.vanilla.root / "common" / "bookmarks").glob("*.txt")):
        try:
            root = parse_file(path)
        except ValueError:
            continue
        bookmarks = root.get("bookmarks")
        if isinstance(bookmarks, Block):
            out.extend(b for b in bookmarks.get_all("bookmark") if isinstance(b, Block))
    return out


def _vanilla_template(ctx: BuildContext) -> tuple[Block | None, set[str]]:
    """(plantilla, campos que usa algún bookmark vanilla).

    En 1.19.3 hay bookmarks sin `default` (solo el de 1936 lo tiene), así que
    los campos se validan contra la UNIÓN de todos, y la plantilla preferida
    es la que se marca como default.
    """
    all_bookmarks = _vanilla_bookmarks(ctx)
    if not all_bookmarks:
        return None, set()
    fields = {k for b in all_bookmarks for k in b.keys()}
    preferred = next((b for b in all_bookmarks if "default" in b.keys()), all_bookmarks[0])
    return preferred, fields


def _emit_bookmark(ctx: BuildContext, spec: dict) -> None:
    template, fields = _vanilla_template(ctx)
    if template is None:
        ctx.warn(f"bookmark: sin plantilla vanilla, uso picture={FALLBACK_PICTURE} sin verificar.")
    else:
        missing = [f for f in EMITTED_FIELDS if f not in fields]
        if missing:
            raise SpecError(
                f"el bookmark vanilla no tiene los campos {missing}: el formato cambio en esta version",
                where="11_scenario.yaml",
            )

    bid = spec["id"]
    b = Block()
    b.add("name", Quoted(_loc(ctx, f"{bid}_NAME", spec["name"])))
    b.add("desc", Quoted(_loc(ctx, f"{bid}_DESC", spec["desc"])))
    b.add("date", spec["date"])
    picture = template.get("picture") if template is not None else None
    b.add("picture", picture if picture is not None else Quoted(FALLBACK_PICTURE))
    default_country = spec["default_country"]
    ctx.spec.country(default_country)
    b.add("default_country", Quoted(default_country))
    # `default` solo si algún bookmark del juego lo usa: en 1.19.3 el reporte
    # mostró que no se puede dar por sentado.
    if template is None or "default" in fields:
        b.add("default", True)

    territory = ctx.data.get("territory")
    for entry in spec.get("featured", []) or []:
        tag = entry["tag"]
        country = ctx.spec.country(tag)
        if territory is not None and tag not in territory.values():
            ctx.warn(f"bookmark: {tag} no tiene territorio, no lo destaco.")
            continue
        cb = Block()
        cb.add("history", Quoted(_loc(ctx, f"{tag}_{bid}_DESC", entry["history"])))
        cb.add("ideology", country.ideology_group)
        ideas = Block()
        for iid in ideas_mod.starting_idea_ids(ctx, tag):
            ideas.add(None, iid)
        cb.add("ideas", ideas)
        focuses = Block()
        for fid in focus_mod.root_focus_ids(ctx, tag):
            focuses.add(None, fid)
        cb.add("focuses", focuses)
        b.add(tag, cb)

    others = Block()
    others.add("history", Quoted(_loc(ctx, f"OTHER_{bid}_DESC", spec["others_history"])))
    b.add('"---"', others)

    effect = template.get("effect") if template is not None else None
    if isinstance(effect, Block):
        b.add("effect", effect)

    bookmarks = Block()
    bookmarks.add("bookmark", b)
    root = Block()
    root.add("bookmarks", bookmarks)
    ctx.write_script("common/bookmarks/meganations_2100.txt", root, source=SOURCE)
    ctx.note(f"escenario: arranca el {spec['date'].rsplit('.', 1)[0]}, pais por defecto {default_country}")


def _loc(ctx: BuildContext, key: str, texts: dict) -> str:
    return ctx.loc.define_and_reference(
        key, en=texts["english"], es=texts["spanish"], file=LOC_FILE, origin=f"scenario:{key}"
    )
