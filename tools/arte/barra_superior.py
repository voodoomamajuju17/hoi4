"""La carcasa de la fecha, la velocidad y la tensión mundial (arriba a la derecha), en el estilo del
Receptor (2026-11-16: "este marco no tiene un pingo que ver con lo nuevo, diseñá otro").

Es la textura del juego gfx/interface/topbar/armyoverview_buttons_bg.dds (403 x 101). El juego dibuja
encima la fecha, los botones de ejército, marina y aviación, el de música, el globo de la tensión con
su porcentaje y los tres botones chicos de la derecha; acá solo va la carcasa, con cada hueco en su
lugar exacto (medido sobre el original): canto de cobre, cuerpo de acero ennegrecido, cada hueco
hundido con su bisel de latón y el globo engarzado en un dial con marcas.

Salida: assets/ui/materiales_piel/gfx/interface/topbar/armyoverview_buttons_bg.dds (ui_skin la pone
encima de la piel de cristal).

Uso:  python3 -m tools.arte.barra_superior [vista.png]
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from .selector import (BRONCE, COBRE_LUZ, TURQUESA, _bisel, _dds, _material, _sombra_interior, _tono,
                       _tornillo)

REPO = Path(__file__).resolve().parents[2]
SALIDA = REPO / "assets" / "ui" / "materiales_piel" / "gfx" / "interface" / "topbar" / "armyoverview_buttons_bg.dds"
W, H = 403, 101
K = 3
# huecos del original (x0, y0, x1, y1) y círculos (cx, cy, r)
FECHA = (81, 11, 279, 34)
BOTONES = [(142, 66, 19), (191, 66, 19), (237, 66, 19)]
MUSICA = (280, 76, 13)
GLOBO = (326, 48, 33)
PORCENTAJE = (307, 77, 349, 93)
CHICOS = [(376, 19, 13), (382, 47, 13), (376, 75, 13)]


def _silueta():
    """Banda de arriba (de punta a punta, con la esquina izquierda en bisel) y cuerpo de abajo."""
    from PIL import Image, ImageDraw
    m = Image.new("L", (W * K, H * K), 0)
    d = ImageDraw.Draw(m)
    d.polygon([(14 * K, 4 * K), (W * K, 4 * K), (W * K, 44 * K), (30 * K, 44 * K)], fill=255)
    d.rounded_rectangle((96 * K, 30 * K, W * K + 20 * K, 98 * K), 14 * K, fill=255)
    cx, cy, r = GLOBO
    d.ellipse(((cx - r - 9) * K, (cy - r - 9) * K, (cx + r + 9) * K, (cy + r + 9) * K), fill=255)
    return m


def _hueco(img, caja, r, aro=True):
    from PIL import ImageDraw
    x0, y0, x1, y1 = (v * K for v in caja)
    if aro:
        b = 3 * K
        ImageDraw.Draw(img).rounded_rectangle((x0 - b, y0 - b, x1 + b, y1 + b), r + b, fill=BRONCE + (255,))
        _bisel(img, (x0 - b, y0 - b, x1 + b, y1 + b), r + b, 2 * K, hundido=False)
    ImageDraw.Draw(img).rounded_rectangle((x0, y0, x1, y1), r, fill=(8, 12, 14, 255))
    _sombra_interior(img, (x0, y0, x1, y1), r, 3 * K)


def _zocalo(img, cx, cy, r, marcas=False):
    """Hueco redondo con aro de latón (y marcas de dial si `marcas`)."""
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    a = r + 4
    d.ellipse(((cx - a) * K, (cy - a) * K, (cx + a) * K, (cy + a) * K), fill=BRONCE + (255,))
    _bisel(img, ((cx - a) * K, (cy - a) * K, (cx + a) * K, (cy + a) * K), a * K, 2 * K, hundido=False)
    if marcas:
        for k in range(48):
            ang = math.radians(k * 7.5)
            l1 = r + 1.2
            l2 = r + (3.6 if k % 4 == 0 else 2.4)
            d.line(((cx + math.cos(ang) * l1) * K, (cy + math.sin(ang) * l1) * K,
                    (cx + math.cos(ang) * l2) * K, (cy + math.sin(ang) * l2) * K),
                   fill=(60, 40, 22, 255), width=max(1, K // 2 + (1 if k % 4 == 0 else 0)))
    d.ellipse(((cx - r) * K, (cy - r) * K, (cx + r) * K, (cy + r) * K), fill=(8, 12, 14, 255))
    _sombra_interior(img, ((cx - r) * K, (cy - r) * K, (cx + r) * K, (cy + r) * K), r * K, 3 * K)


def dibujar_pieza():
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    sil = _silueta()
    cuerpo = _tono(_material("mat_acero_ennegrecido", W * K, H * K, 0.5), 0.8)
    img = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0))
    img.paste(cuerpo, (0, 0), sil)
    # canto de cobre alrededor de toda la silueta
    borde = ImageChops.subtract(sil, sil.filter(ImageFilter.MinFilter(4 * K + 1)))
    cobre = _tono(_material("mat_cobre_patina", W * K, H * K, 0.35), 1.0, (120, 70, 40), 0.3)
    img.paste(cobre, (0, 0), borde)
    luz = Image.new("RGBA", img.size, COBRE_LUZ + (0,))
    luz.putalpha(ImageChops.subtract(sil, sil.filter(ImageFilter.MinFilter(K + 1 if K % 2 == 0 else K))).point(lambda v: v // 2))
    img.alpha_composite(luz)
    d = ImageDraw.Draw(img)
    # costura entre banda y cuerpo, y una línea de pilotos turquesa en la banda (debajo de la fecha)
    d.line((100 * K, 42 * K, 290 * K, 42 * K), fill=(20, 12, 8, 220), width=K)
    for k in range(3):
        cx, cy, r = 40 + k * 12, 26, 2.2
        d.ellipse(((cx - r) * K, (cy - r) * K, (cx + r) * K, (cy + r) * K),
                  fill=(TURQUESA if k == 0 else (30, 52, 50)) + (255,), outline=(20, 16, 12, 255), width=1)
    # rejilla de parlante en el extremo izquierdo de la banda
    for y in range(10, 20, 3):
        d.line((26 * K + (20 - y) * K // 2, y * K, 70 * K, y * K), fill=(6, 7, 8, 255), width=K)
    # huecos
    _hueco(img, FECHA, 6 * K)
    _hueco(img, PORCENTAJE, 6 * K)
    for cx, cy, r in BOTONES:
        _zocalo(img, cx, cy, r)
    _zocalo(img, *MUSICA)
    for cx, cy, r in CHICOS:
        _zocalo(img, cx, cy, r)
    _zocalo(img, *GLOBO, marcas=True)
    for cx, cy in ((106, 40), (106, 90), (288, 92)):
        _tornillo(img, cx * K, cy * K, int(2.2 * K))
    out = img.resize((W, H), Image.LANCZOS)
    # sombra suave hacia abajo (como el original)
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = out.getchannel("A").filter(ImageFilter.GaussianBlur(2))
    sombra.paste((0, 0, 0, 150), (0, 2), a)
    sombra.alpha_composite(out)
    return sombra


def dibujar() -> list[str]:
    _dds(dibujar_pieza(), SALIDA)
    return [f"barra superior: carcasa de la fecha y la tensión en {SALIDA.relative_to(REPO)}"]


def vista_previa(dest: Path) -> None:
    """La carcasa sobre un mapa liso, con fecha, botones y globo de prueba."""
    from PIL import Image, ImageDraw, ImageFont
    fondo = Image.new("RGBA", (W + 40, H + 30), (120, 128, 150, 255))
    fondo.alpha_composite(dibujar_pieza(), (20, 10))
    d = ImageDraw.Draw(fondo)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
    except OSError:
        f = ImageFont.load_default()
    d.text((20 + 180, 10 + 22), "9:00, 17 Mar, 2100", font=f, fill=(232, 226, 210), anchor="mm")
    d.text((20 + 328, 10 + 85), "29%", font=f, fill=(232, 226, 210), anchor="mm")
    for cx, cy, r in BOTONES:
        d.ellipse((20 + cx - 15, 10 + cy - 15, 20 + cx + 15, 10 + cy + 15), fill=(150, 98, 60, 255))
    cx, cy, r = GLOBO
    d.ellipse((20 + cx - 30, 10 + cy - 30, 20 + cx + 30, 10 + cy + 30), fill=(60, 110, 120, 255))
    fondo.convert("RGB").resize((fondo.width * 2, fondo.height * 2)).save(dest)


if __name__ == "__main__":
    print("\n".join(dibujar()))
    if len(sys.argv) > 1:
        vista_previa(Path(sys.argv[1]))
