"""Armas y tecnologías con nombre e imagen de cada facción (17_research.yaml ->
by_faction, pedido del usuario 2026-10-03).

El equipo y la tecnología son los mismos para todos; cambia lo que ve cada país:

  localisation  <TAG>_<equipo> y <TAG>_<tecnología>   "Fusil Espina II"
  interface     GFX_<TAG>_<equipo>_medium y GFX_<TAG>_<tecnología>_medium,
                desde assets/<estilo>/tech/<familia>.dds, al tamaño del ícono
                del juego (sin imagen, queda la del juego)

Los satélites usan el estilo de su señor; `inherit` asigna otros. Lo que solo
habilita una tecnología bloqueada por una unidad única no se toca (ya tiene el
nombre de la unidad). El reporte dice si el juego instalado usa esos nombres
por país (claves y sprites con prefijo de TAG), para saber que se ven.
"""

from __future__ import annotations

import re

from ..context import BuildContext
from ..pdx import Block, Quoted
from .unit_names import roman

SOURCE = "spec/17_research.yaml -> by_faction"
LOC_FILE = "meganations_faction_tech"
GFX_FILE = "interface/meganations_faction_tech.gfx"
TEX_DIR = "gfx/interface/technologies/meganations"


def emit(ctx: BuildContext) -> None:
    spec = (ctx.spec.raw.get("research_look") or {}).get("by_faction") or {}
    if not spec or ctx.vanilla is None:
        return
    families = spec["families"]
    names = spec["names"]
    inherit = spec.get("inherit") or {}
    for tag, fams in names.items():
        unknown = set(fams) - set(families)
        if unknown:
            from ..errors import SpecError
            raise SpecError(f"by_faction.names.{tag}: familias que no existen: {', '.join(sorted(unknown))}",
                            where=SOURCE)

    # Quién usa qué estilo
    style_of: dict[str, str] = {}
    for c in ctx.spec.countries:
        if c.tag in names:
            style_of[c.tag] = c.tag
        elif c.tag in inherit and inherit[c.tag] in names:
            style_of[c.tag] = inherit[c.tag]
        elif c.is_subject and c.overlord in names:
            style_of[c.tag] = c.overlord

    tree = ctx.vanilla.tech_tree()
    equipment = dict(ctx.vanilla.equipment())
    for info in tree.values():     # lo que habilita una tecnología también cuenta
        for e in info.get("enables") or ():
            equipment.setdefault(e, (e, 0))
    members = family_members(families, equipment)
    locks = ctx.data.get("tech_locks") or {}
    enabled_by: dict[str, list[str]] = {}
    for t, info in tree.items():
        for e in info.get("enables") or ():
            enabled_by.setdefault(e, []).append(t)

    def free(eq: str) -> list[str]:
        """Tecnologías (no únicas) que habilitan el equipo."""
        return [t for t in sorted(enabled_by.get(eq, [])) if t not in locks]

    repo = ctx.spec.root.parent
    textures = ctx.vanilla.gfx_textures()
    sprites = Block()
    written: dict[tuple[str, str, int, int], str] = {}
    counts = {"nombres": 0, "tecnologias": 0, "sprites": 0}
    for tag, style in sorted(style_of.items()):
        named_techs: set[str] = set()
        for fam, entry in names[style].items():
            art = repo / "assets" / style / "tech" / f"{fam}.dds"
            for eq, gen in members.get(fam, []):
                if enabled_by.get(eq) and not free(eq):
                    continue      # de una unidad única
                en, es = f"{entry['en']} {roman(gen)}", f"{entry['es']} {roman(gen)}"
                for key in (f"{tag}_{eq}", f"{tag}_{eq}_short"):
                    ctx.loc.define_and_reference(key, en=en, es=es, file=LOC_FILE, origin=f"faction_tech:{tag}")
                counts["nombres"] += 1
                targets = [eq]
                for t in free(eq):
                    if t in named_techs:
                        continue      # habilita varios equipos: el primero le da el nombre
                    named_techs.add(t)
                    ctx.loc.define_and_reference(f"{tag}_{t}", en=en, es=es, file=LOC_FILE,
                                                 origin=f"faction_tech:{tag}")
                    counts["tecnologias"] += 1
                    targets.append(t)
                if art.exists():
                    for target in targets:
                        rel = _texture(ctx, art, style, fam, textures.get(f"GFX_{target}_medium"), written)
                        sprites.add("spriteType", Block([("name", Quoted(f"GFX_{tag}_{target}_medium")),
                                                         ("texturefile", Quoted(rel))]))
                        counts["sprites"] += 1
    if sprites.entries:
        ctx.write_script(GFX_FILE, Block([("spriteTypes", sprites)]), source=SOURCE)
    ctx.note(f"armas por faccion: {counts['nombres']} nombres de equipo y {counts['tecnologias']} de tecnologia "
             f"para {len(style_of)} paises ({len(names)} estilos); {counts['sprites']} iconos propios "
             f"({len(written)} imagenes)")
    _probe(ctx, members, enabled_by)


def family_members(families: dict, equipment: dict) -> dict[str, list[tuple[str, int]]]:
    """familia -> [(equipo, generación)], generación 1, 2, 3... dentro de cada
    raíz (light_tank_chassis_0 -> 1). Solo equipos concretos, no arquetipos."""
    out: dict[str, list[tuple[str, int]]] = {}
    for fam, f in families.items():
        by_stem: dict[str, list[tuple[int, str]]] = {}
        for eq, (archetype, _) in equipment.items():
            if archetype is None:
                continue
            for pattern in f["match"]:
                m = re.match(pattern, eq)
                if m:
                    by_stem.setdefault(eq[:m.start(1)], []).append((int(m.group(1)), eq))
                    break
        found = []
        for stem in sorted(by_stem):
            for gen, (_, eq) in enumerate(sorted(by_stem[stem]), start=1):
                found.append((eq, gen))
        out[fam] = found
    return out


def _texture(ctx: BuildContext, art, style: str, fam: str, vanilla_tex: str | None,
             written: dict[tuple[str, str, int, int], str]) -> str:
    """La imagen de la familia al tamaño del ícono del juego (una por tamaño)."""
    from .menu import _dims, _resize, _texture_dims
    data = art.read_bytes()
    w, h = _dims(data)
    size = _texture_dims(ctx, vanilla_tex) if vanilla_tex else (0, 0)
    nw, nh = size if size[0] and size[1] else (w, h)
    key = (style, fam, nw, nh)
    if key in written:
        return written[key]
    if (nw, nh) != (w, h) and w and h:
        data = _resize(data, w, h, nw, nh)
    rel = f"{TEX_DIR}/{style}_{fam}_{nw}x{nh}.dds"
    dest = ctx.mod_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    ctx.track(dest)
    written[key] = rel
    return rel


def _probe(ctx: BuildContext, members: dict, enabled_by: dict) -> None:
    """¿El juego instalado usa nombres e íconos por país? Si trae alguno
    (GER_infantry_equipment_1, GFX_GER_..._medium), los nuestros se ven."""
    eqs = [eq for fam in members.values() for eq, _ in fam]
    techs = sorted({t for eq in eqs for t in enabled_by.get(eq, [])})
    tags = ("GER", "SOV", "ENG", "USA", "FRA", "ITA", "JAP")
    loc_eq = ctx.vanilla.localisation("english", {f"{t}_{e}" for t in tags for e in eqs})
    loc_tech = ctx.vanilla.localisation("english", {f"{t}_{x}" for t in tags for x in techs})
    gfx = ctx.vanilla.gfx_names()
    pat = re.compile(r"^GFX_[A-Z]{3}_(.+)_medium$")
    gfx_eq = sorted(n for n in gfx if (m := pat.match(n)) and m.group(1) in set(eqs))
    gfx_tech = sorted(n for n in gfx if (m := pat.match(n)) and m.group(1) in set(techs))
    ctx.note("armas por faccion, que usa el juego por pais: "
             f"nombres de equipo {len(loc_eq)} (ej. {', '.join(sorted(loc_eq)[:3]) or '-'}); "
             f"nombres de tecnologia {len(loc_tech)} (ej. {', '.join(sorted(loc_tech)[:3]) or '-'}); "
             f"iconos de equipo {len(gfx_eq)} (ej. {', '.join(gfx_eq[:3]) or '-'}); "
             f"iconos de tecnologia {len(gfx_tech)} (ej. {', '.join(gfx_tech[:3]) or '-'})")
