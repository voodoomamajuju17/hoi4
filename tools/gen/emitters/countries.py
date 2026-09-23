"""Países: tags, archivos de país, colores, banderas y sus nombres.

Produce:
  common/country_tags/00_meganations.txt
  common/countries/<Nombre>.txt
  common/countries/colors.txt
  gfx/flags/{,medium/,small/}<TAG>.tga
  localisation de nombres y adjetivos

Sobre los nombres: HOI4 arma el nombre del pais como <TAG>_<ideologia>, con
<TAG>_DEF de fallback. O sea que hay una clave por combinacion pais x ideologia
que el pais pueda adoptar. Se emite la del arranque mas la de fallback; si mas
adelante un pais puede cambiar de ideologia por evento o foco, hay que agregar
la clave de esa ideologia o el jugador ve la clave cruda.
"""

from __future__ import annotations

from ..art import write_country_flags
from ..context import BuildContext
from ..pdx import Block, Tagged
from ..specload import Country

SOURCE = "spec/02_countries.yaml"
LOC_FILE = "meganations_countries"

# Q013: se reusan culturas graficas vanilla (una por region, campo `graphics`
# de cada pais: "southamerican" -> southamerican_gfx / southamerican_2d). Un
# valor inventado rompe la carga, asi que se valida contra los que usa algun
# pais vanilla; si no existe, se cae a la europea occidental con aviso.
DEFAULT_GFX = "western_european"


def emit(ctx: BuildContext) -> None:
    _emit_tags(ctx)
    _emit_country_files(ctx)
    _emit_colors(ctx)
    _emit_flags(ctx)
    _emit_localisation(ctx)


def _emit_tags(ctx: BuildContext) -> None:
    b = Block()
    for c in sorted(ctx.spec.countries, key=lambda x: x.tag):
        b.add(c.tag, f"countries/{c.filename}.txt")
    ctx.write_script("common/country_tags/00_meganations.txt", b, source=SOURCE)


def _emit_country_files(ctx: BuildContext) -> None:
    known = ctx.vanilla.graphical_cultures() if ctx.vanilla is not None else None
    used: dict[str, list[str]] = {}
    for c in ctx.spec.countries:
        base = c.raw.get("graphics") or DEFAULT_GFX
        gfx, gfx2d = f"{base}_gfx", f"{base}_2d"
        if known is not None and known[0] and (gfx not in known[0] or gfx2d not in known[1]):
            ctx.warn(f"{c.tag}: la cultura grafica '{base}' no existe en este juego; uso {DEFAULT_GFX}.")
            gfx, gfx2d = f"{DEFAULT_GFX}_gfx", f"{DEFAULT_GFX}_2d"
        b = Block()
        b.add("graphical_culture", gfx)
        b.add("graphical_culture_2d", gfx2d)
        ctx.write_script(f"common/countries/{c.filename}.txt", b, source=SOURCE)
        used.setdefault(gfx.removesuffix("_gfx"), []).append(c.tag)
    ctx.note("culturas graficas: " + "; ".join(f"{k} ({len(v)})" for k, v in sorted(used.items())))


def _emit_colors(ctx: BuildContext) -> None:
    """common/countries/colors.txt — color de mapa y de interfaz."""
    b = Block()
    for c in sorted(ctx.spec.countries, key=lambda x: x.tag):
        entry = Block()
        entry.add("color", _rgb(c.color))
        entry.add("color_ui", _rgb(c.color))
        b.add(c.tag, entry)
    ctx.write_script("common/countries/colors.txt", b, source=SOURCE)


def _rgb(color: tuple[int, int, int]) -> Tagged:
    """`rgb { r g b }` en una línea, como el colors.txt vanilla."""
    return Tagged("rgb", tuple(color))


def _emit_flags(ctx: BuildContext) -> None:
    """Bandera del usuario si el spec tiene `flag_asset`; si no, placeholder.

    `flag_asset` es una carpeta con <TAG>.tga, medium/<TAG>.tga y
    small/<TAG>.tga. <TAG>.tga es el fallback para cualquier ideología.
    """
    gfx_root = ctx.mod_root / "gfx"
    for c in ctx.spec.countries:
        asset = c.raw.get("flag_asset")
        if asset:
            for variant in ("", "medium/", "small/"):
                ctx.copy_asset(f"{asset}/{variant}{c.tag}.tga", f"gfx/flags/{variant}{c.tag}.tga")
            continue
        for path in write_country_flags(gfx_root, c.tag, c.color):
            ctx.track(path)


def _emit_localisation(ctx: BuildContext) -> None:
    for c in ctx.spec.countries:
        # Fallback: se usa cuando no hay clave para la ideologia actual.
        ctx.loc.define_and_reference(
            f"{c.tag}_DEF", en=c.name_en, es=c.name_es, file=LOC_FILE, origin=f"countries:{c.tag}"
        )
        ctx.loc.define_and_reference(
            f"{c.tag}_DEF_ADJ", en=c.adj_en, es=c.adj_es, file=LOC_FILE, origin=f"countries:{c.tag}"
        )
        # Nombre bajo la ideologia con la que arranca.
        ctx.loc.define_and_reference(
            f"{c.tag}_{c.ideology}",
            en=c.name_en,
            es=c.name_es,
            file=LOC_FILE,
            origin=f"countries:{c.tag}",
        )
        ctx.loc.define_and_reference(
            f"{c.tag}_{c.ideology}_ADJ",
            en=c.adj_en,
            es=c.adj_es,
            file=LOC_FILE,
            origin=f"countries:{c.tag}",
        )


def country_name_key(c: Country) -> str:
    return f"{c.tag}_{c.ideology}"
