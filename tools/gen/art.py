"""Arte placeholder, generado programáticamente y sin dependencias.

Se escriben TGA y DDS a mano con struct. No hace falta Pillow: los formatos
sin comprimir son triviales y así el generador corre en cualquier Python 3.11+
con solo PyYAML.

NADA de acá es arte final. Son rectángulos con bandas de color, pensados para
que el mod cargue y para distinguir países de un vistazo.

NOTA DE FORMATO — las banderas de HOI4 son .TGA, no .dds.
El pedido original decía "banderas placeholder en .dds", que es lo que usa
Stellaris. En HOI4 van en gfx/flags/<TAG>.tga, con copias reducidas en
gfx/flags/medium/ y gfx/flags/small/. Se generan .tga por eso. El escritor de
DDS queda disponible para iconos y otros GFX que sí lo usan.
"""

from __future__ import annotations

import struct
from pathlib import Path

RGB = tuple[int, int, int]

# Dimensiones de bandera de HOI4. Confirmar contra la instalación en Fase 4:
# si no coinciden el juego escala igual, pero se ve borroso.
FLAG_SIZES = {
    "": (82, 52),
    "medium": (41, 26),
    "small": (10, 7),
}


# ---------------------------------------------------------------------------
# TGA
# ---------------------------------------------------------------------------


def write_tga(path: Path, width: int, height: int, pixels: list[RGB]) -> None:
    """TGA sin comprimir, 24 bits, orden BGR, origen abajo-izquierda."""
    if len(pixels) != width * height:
        raise ValueError(f"esperaba {width * height} pixeles, recibi {len(pixels)}")
    header = struct.pack(
        "<BBBHHBHHHHBB",
        0,          # longitud del campo id
        0,          # sin paleta
        2,          # RGB sin comprimir
        0, 0, 0,    # spec de paleta (vacia)
        0, 0,       # origen x, y
        width,
        height,
        24,         # bits por pixel
        0,          # descriptor: origen abajo-izquierda
    )
    body = bytearray()
    # TGA guarda de abajo hacia arriba.
    for y in range(height - 1, -1, -1):
        for x in range(width):
            r, g, b = pixels[y * width + x]
            body += bytes((b, g, r))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + bytes(body))


# ---------------------------------------------------------------------------
# DDS
# ---------------------------------------------------------------------------

_DDSD_CAPS = 0x1
_DDSD_HEIGHT = 0x2
_DDSD_WIDTH = 0x4
_DDSD_PIXELFORMAT = 0x1000
_DDSD_PITCH = 0x8
_DDPF_ALPHAPIXELS = 0x1
_DDPF_RGB = 0x40
_DDSCAPS_TEXTURE = 0x1000


def write_dds(path: Path, width: int, height: int, pixels: list[RGB], alpha: int = 255) -> None:
    """DDS sin comprimir, 32 bits A8R8G8B8. Para iconos, no para banderas."""
    if len(pixels) != width * height:
        raise ValueError(f"esperaba {width * height} pixeles, recibi {len(pixels)}")
    flags = _DDSD_CAPS | _DDSD_HEIGHT | _DDSD_WIDTH | _DDSD_PIXELFORMAT | _DDSD_PITCH
    header = b"DDS " + struct.pack(
        "<IIIIII",
        124,            # tamano del header
        flags,
        height,
        width,
        width * 4,      # pitch
        0,              # profundidad
    )
    header += struct.pack("<I", 0)          # mipmaps
    header += b"\x00" * 44                  # reservado
    header += struct.pack(
        "<IIIIIIII",
        32,                                 # tamano del pixelformat
        _DDPF_RGB | _DDPF_ALPHAPIXELS,
        0,                                  # fourcc
        32,                                 # bits por pixel
        0x00FF0000,                         # mascara R
        0x0000FF00,                         # mascara G
        0x000000FF,                         # mascara B
        0xFF000000,                         # mascara A
    )
    header += struct.pack("<IIIII", _DDSCAPS_TEXTURE, 0, 0, 0, 0)

    body = bytearray()
    for r, g, b in pixels:
        body += bytes((b, g, r, alpha))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + bytes(body))


# ---------------------------------------------------------------------------
# Composición de placeholders
# ---------------------------------------------------------------------------


def _shade(color: RGB, factor: float) -> RGB:
    return tuple(max(0, min(255, int(c * factor))) for c in color)  # type: ignore[return-value]


def flag_pixels(width: int, height: int, base: RGB) -> list[RGB]:
    """Bandera placeholder: tres bandas horizontales derivadas del color del país.

    Elegido a propósito para que se lea como placeholder y no como diseño.
    Además distingue países de un vistazo en el mapa y en el selector.
    """
    light = _shade(base, 1.35)
    dark = _shade(base, 0.6)
    pixels: list[RGB] = []
    for y in range(height):
        third = (y * 3) // height
        row_color = (light, base, dark)[third]
        for x in range(width):
            # Franja vertical más clara al asta, para que se note la orientación.
            pixels.append(_shade(row_color, 1.25) if x < max(1, width // 8) else row_color)
    return pixels


def write_country_flags(gfx_root: Path, tag: str, color: RGB) -> list[Path]:
    """Escribe las tres variantes de bandera que HOI4 espera por país."""
    written = []
    for variant, (w, h) in FLAG_SIZES.items():
        target = gfx_root / "flags" / variant / f"{tag}.tga" if variant else gfx_root / "flags" / f"{tag}.tga"
        write_tga(target, w, h, flag_pixels(w, h, color))
        written.append(target)
    return written
