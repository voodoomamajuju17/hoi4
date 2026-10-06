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
    sizes = _Sizes(ctx, textures, equipment, tree)
    sprites = Block()
    written: dict[tuple[str, str, int, int], str] = {}
    counts = {"nombres": 0, "tecnologias": 0, "sprites": 0}
    for tag, style in sorted(style_of.items()):
        named_techs: set[str] = set()
        for fam, entry in names[style].items():
            # v2 (arte/armas_descripciones.yaml) primero; si no, la primera tanda
            art = repo / "assets" / style / "armas" / f"{fam}.dds"
            if not art.exists():
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
                        rel = _texture(ctx, art, style, fam, sizes.of(target), written)
                        sprites.add("spriteType", Block([("name", Quoted(f"GFX_{tag}_{target}_medium")),
                                                         ("texturefile", Quoted(rel))]))
                        counts["sprites"] += 1
    # Unidades únicas (2026-10-03: "¿no hay imagen única para el Gliptodonte?"):
    # assets/<TAG>/armas/<id>.dds -> su equipo y sus tecnologías bloqueadas,
    # para el país dueño (y nadie más, son solo suyas).
    for uu in ctx.data.get("uu_art") or []:
        art = repo / "assets" / uu["tag"] / "armas" / f"{uu['id']}.dds"
        if not art.exists():
            continue
        targets = ([uu["equipment"]] if uu.get("equipment") else []) + list(uu.get("techs") or [])
        for target in targets:
            rel = _texture(ctx, art, uu["tag"], uu["id"], sizes.of(target), written)
            sprites.add("spriteType", Block([("name", Quoted(f"GFX_{uu['tag']}_{target}_medium")),
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


# 2026-10-03 (captura del usuario: "algunas imágenes son gigantes"): sin la
# medida del ícono del juego la imagen quedaba en 300x200 y tapaba la fila de
# al lado. Si el sprite exacto no se puede leer (muchos están dentro de los zip
# de las expansiones), se usa la medida más común de los íconos de equipo o de
# tecnología del juego, y si tampoco, una fija.
# 2026-10-06 (captura: "las imágenes están perfectas pero la escala es un poco
# chica"): respaldo más grande y se recorta el borde transparente de la imagen
# antes de encajarla. 17_research -> by_faction.icon_size pisa estos valores y
# `scale` agranda o achica todo.
FALLBACK_EQUIPMENT = (160, 72)
FALLBACK_TECH = (100, 50)


class _Sizes:
    def __init__(self, ctx: BuildContext, textures: dict, equipment: dict, tree: dict):
        from .menu import _texture_dims
        self.ctx, self.textures, self.tree = ctx, textures, tree
        self.archetype = {e: a for e, (a, _) in equipment.items() if a}
        self._dims = _texture_dims
        self._cache: dict[str, tuple[int, int]] = {}
        eq_keys = set(equipment) | {a for a in self.archetype.values()}
        pat = re.compile(r"^GFX_(?:[A-Z]{3}_)?(\w+?)_medium$")
        eq_sizes, tech_sizes = [], []
        for name, tex in textures.items():
            m = pat.match(name)
            if not m or m.group(1) not in eq_keys and m.group(1) not in tree:
                continue
            d = self._read(tex)
            if d[0] and d[1]:
                (eq_sizes if m.group(1) in eq_keys else tech_sizes).append(d)
        conf = ((ctx.spec.raw.get("research_look") or {}).get("by_faction") or {}).get("icon_size") or {}
        self.scale = float(conf.get("scale", 1.0))
        # la medida del juego manda (reporte 2026-10-06: 146x54); icon_size es el respaldo
        self.default_eq = _most_common(eq_sizes) or tuple(conf.get("equipment") or ()) or FALLBACK_EQUIPMENT
        self.default_tech = _most_common(tech_sizes) or tuple(conf.get("tech") or ()) or FALLBACK_TECH
        ctx.note(f"armas por faccion: tamano de los iconos {self.default_eq[0]}x{self.default_eq[1]} (equipo, "
                 f"{len(eq_sizes)} del juego) y {self.default_tech[0]}x{self.default_tech[1]} (tecnologia, "
                 f"{len(tech_sizes)} del juego)")

    def _read(self, tex: str) -> tuple[int, int]:
        if tex not in self._cache:
            self._cache[tex] = self._dims(self.ctx, tex)
        return self._cache[tex]

    def of(self, target: str) -> tuple[int, int]:
        w, h = self._of(target)
        return max(1, round(w * self.scale)), max(1, round(h * self.scale))

    def _of(self, target: str) -> tuple[int, int]:
        names = [f"GFX_{target}_medium"]
        names += sorted(n for n in self.textures if n.endswith(f"_{target}_medium") and n.startswith("GFX_"))
        if target in self.archetype:
            names.append(f"GFX_{self.archetype[target]}_medium")
        for n in names:
            if n in self.textures:
                d = self._read(self.textures[n])
                if d[0] and d[1]:
                    return d
        return self.default_tech if target in self.tree and target not in self.archetype else self.default_eq


def _most_common(sizes: list[tuple[int, int]]) -> tuple[int, int] | None:
    if not sizes:
        return None
    from collections import Counter
    return Counter(sizes).most_common(1)[0][0]


def _fit(data: bytes, w: int, h: int, nw: int, nh: int) -> bytes:
    """Encaja la imagen entera en nw x nh (sin cortar), centrada, con fondo
    transparente; promedia los píxeles al achicar. DDS A8R8G8B8 sin comprimir
    (el que escribe art.write_dds)."""
    import struct
    body = data[128:128 + w * h * 4]
    # recorte del borde transparente: el arma llena el ícono
    xs0, ys0, xs1, ys1 = w, h, -1, -1
    for y in range(0, h):
        row = body[y * w * 4:(y + 1) * w * 4]
        alphas = row[3::4]
        if max(alphas) > 16:
            ys0, ys1 = min(ys0, y), y
            first = next(i for i, a in enumerate(alphas) if a > 16)
            last = len(alphas) - 1 - next(i for i, a in enumerate(reversed(alphas)) if a > 16)
            xs0, xs1 = min(xs0, first), max(xs1, last)
    if xs1 >= xs0 and ys1 >= ys0 and (xs1 - xs0 + 1, ys1 - ys0 + 1) != (w, h):
        cw, ch = xs1 - xs0 + 1, ys1 - ys0 + 1
        body = b"".join(body[(y * w + xs0) * 4:(y * w + xs1 + 1) * 4] for y in range(ys0, ys1 + 1))
        w, h = cw, ch
    scale = min(nw / w, nh / h)
    sw, sh = max(1, round(w * scale)), max(1, round(h * scale))
    ox, oy = (nw - sw) // 2, (nh - sh) // 2
    out = bytearray(nw * nh * 4)
    for y in range(sh):
        y0, y1 = y * h // sh, max(y * h // sh + 1, (y + 1) * h // sh)
        for x in range(sw):
            x0, x1 = x * w // sw, max(x * w // sw + 1, (x + 1) * w // sw)
            acc = [0, 0, 0, 0]
            n = 0
            for yy in range(y0, y1):
                row = yy * w * 4
                for xx in range(x0, x1):
                    i = row + xx * 4
                    a = body[i + 3]
                    acc[0] += body[i] * a
                    acc[1] += body[i + 1] * a
                    acc[2] += body[i + 2] * a
                    acc[3] += a
                    n += 1
            o = ((y + oy) * nw + x + ox) * 4
            if acc[3]:
                out[o:o + 4] = bytes((acc[0] // acc[3], acc[1] // acc[3], acc[2] // acc[3], acc[3] // n))
    header = bytearray(data[:128])
    struct.pack_into("<III", header, 12, nh, nw, nw * 4)
    return bytes(header) + bytes(out)


def _texture(ctx: BuildContext, art, style: str, fam: str, size: tuple[int, int],
             written: dict[tuple[str, str, int, int], str]) -> str:
    """La imagen de la familia al tamaño del ícono del juego (una por tamaño)."""
    from .menu import _dims
    nw, nh = size
    key = (style, fam, nw, nh)
    if key in written:
        return written[key]
    data = art.read_bytes()
    w, h = _dims(data)
    if (nw, nh) != (w, h) and w and h:
        data = _fit(data, w, h, nw, nh)
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
