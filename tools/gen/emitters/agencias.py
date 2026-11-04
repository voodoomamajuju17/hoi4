"""Agencias de inteligencia propias de las meganaciones (2026-10-29).

Captura del usuario: al crear la agencia salía el "Research and Analysis Wing"
de la India de 1936. create_intelligence_agency elige entre las agencias de
common/intelligence_agencies; el mod no tenía ninguna, así que el juego daba
una de las suyas. Pedido: "usá la imagen del espíritu" (el Servicio de
Inteligencia de cada potencia, assets/<TAG>/ideas/<TAG>_servicio_de_inteligencia.dds).

Produce:
  common/intelligence_agencies/meganations_agencias.txt
  interface/meganations_agencias.gfx
  gfx/interface/intelligence_agency_logos/meganations/<TAG>.dds
"""

from __future__ import annotations

import struct

from ..context import BuildContext
from ..pdx import Block, Quoted, banner_for, render

SOURCE = "tools/gen/emitters/agencias.py (pedido del usuario 2026-10-29)"

# 2026-11-03 (glosario del inglés): castellano, inglés. El nombre se escribe
# como clave de localisation para que cada idioma vea el suyo.
NOMBRES = {
    "EFE": ("Las Raíces del Imperio", "The Roots of the Empire"),
    "ASC": ("Dirección de Vigilancia Algorítmica", "Directorate of Algorithmic Surveillance"),
    "FCU": ("Consultora de Riesgo Consolidado", "Consolidated Risk Consultancy"),
    "HSN": ("Oficina de Seguros y Manifiestos", "Office of Insurance and Manifests"),
    "NAS": ("Los Ojos del Inti", "The Eyes of Inti"),
    "SHD": ("Oficina del Caudal Oculto", "Office of the Hidden Current"),
    "APF": ("Consejo de las Voces Lejanas", "Council of Distant Voices"),
    "NRE": ("Frumentarii", "Frumentarii"),
}


def emit(ctx: BuildContext) -> None:
    repo = ctx.spec.root.parent
    agencias = Block()
    sprites = Block()
    hechas = []
    for c in ctx.spec.countries:
        if not c.is_major:
            continue
        src = repo / "assets" / c.tag / "ideas" / f"{c.tag}_servicio_de_inteligencia.dds"
        if not src.exists():
            continue
        tex = f"gfx/interface/intelligence_agency_logos/meganations/{c.tag}.dds"
        dest = ctx.mod_root / tex
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_logo(src.read_bytes()))
        ctx.track(dest)
        gfx = f"GFX_intelligence_agency_logo_MEGANATIONS_{c.tag}"
        sprites.add("spriteType", Block([("name", Quoted(gfx)), ("texturefile", Quoted(tex))]))
        es, en = NOMBRES.get(c.tag, (f"Servicio de Inteligencia de {c.tag}", f"{c.tag} Intelligence Service"))
        nombre = ctx.loc.define_and_reference(f"MN_agencia_{c.tag}", en=en, es=es,
                                              file="meganations_intelligence", origin=f"agencias:{c.tag}")
        agencias.add("intelligence_agency", Block([
            ("picture", gfx),
            ("names", Block([(None, Quoted(nombre))])),
            ("default", Block([("original_tag", c.tag)])),
            ("available", Block([("original_tag", c.tag)])),
        ]))
        hechas.append(c.tag)
    if not hechas:
        return
    ctx.write_text("common/intelligence_agencies/meganations_agencias.txt", banner_for(SOURCE) + render(agencias))
    ctx.write_text("interface/meganations_agencias.gfx",
                   banner_for(SOURCE) + render(Block([("spriteTypes", sprites)])))
    ctx.note(f"agencias: propias con el emblema del Servicio de Inteligencia ({', '.join(hechas)})")


# 2026-11-01 (captura del usuario: el emblema salía chico y arriba a la
# izquierda del aro de la agencia). El juego dibuja el logo a su tamaño, desde
# la esquina del hueco; el espíritu mide 64x64 y el aro está centrado en
# (66, 66). El emblema se recorta a lo que tiene dibujo, se agranda a ~100 px
# y se centra en un lienzo de 132x132, así cae en el medio del hueco.
LIENZO = 132
EMBLEMA = 100


def _logo(src: bytes) -> bytes:
    """DDS A8R8G8B8 de 64x64 -> DDS de LIENZO x LIENZO con el emblema centrado."""
    if src[:4] != b"DDS " or struct.unpack_from("<I", src, 88)[0] != 32:
        return src  # formato inesperado: va tal cual
    h, w = struct.unpack_from("<II", src, 12)
    body = src[128:128 + w * h * 4]
    # bytes en memoria: B, G, R, A. Premultiplicado para que el borde no se ensucie.
    px = []
    for i in range(w * h):
        b, g, r, a = body[i * 4:i * 4 + 4]
        f = a / 255
        px.append((b * f, g * f, r * f, float(a)))
    xs = [i % w for i in range(w * h) if px[i][3] > 8]
    ys = [i // w for i in range(w * h) if px[i][3] > 8]
    if not xs:
        return src
    x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
    bw, bh = x1 - x0, y1 - y0
    k = EMBLEMA / max(bw, bh)
    nw, nh = round(bw * k), round(bh * k)
    ox, oy = (LIENZO - nw) // 2, (LIENZO - nh) // 2

    def at(x: int, y: int):
        if x0 <= x < x1 and y0 <= y < y1:
            return px[y * w + x]
        return (0.0, 0.0, 0.0, 0.0)

    out = bytearray(LIENZO * LIENZO * 4)
    for y in range(nh):
        sy = y0 + (y + 0.5) / k - 0.5
        iy = int(sy // 1)
        fy = sy - iy
        for x in range(nw):
            sx = x0 + (x + 0.5) / k - 0.5
            ix = int(sx // 1)
            fx = sx - ix
            p00, p10, p01, p11 = at(ix, iy), at(ix + 1, iy), at(ix, iy + 1), at(ix + 1, iy + 1)
            c = [p00[j] * (1 - fx) * (1 - fy) + p10[j] * fx * (1 - fy)
                 + p01[j] * (1 - fx) * fy + p11[j] * fx * fy for j in range(4)]
            a = c[3]
            o = ((oy + y) * LIENZO + ox + x) * 4
            if a > 0:
                out[o:o + 4] = bytes([min(255, round(c[0] * 255 / a)), min(255, round(c[1] * 255 / a)),
                                      min(255, round(c[2] * 255 / a)), min(255, round(a))])
    header = bytearray(src[:128])
    struct.pack_into("<III", header, 12, LIENZO, LIENZO, LIENZO * 4)
    return bytes(header) + bytes(out)
