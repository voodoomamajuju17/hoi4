"""Piloto de la interfaz de materiales reales: la ventana de eventos (2026-11-07).

Plan acordado: el generador de imágenes hizo los MATERIALES (assets/ui/materiales/*.jpg,
muestras repetibles sin forma) y este programa hace la FORMA, al píxel, sobre la silueta
de cada pieza original del juego:

  - el marco (lo oscuro de la pieza original): nogal oscuro, conservando los relieves y
    remaches del original como luz y sombra; un filete de bronce donde el marco toca el papel;
  - el papel (lo claro): se queda papel, un poco más cálido, porque el texto de los eventos
    es oscuro (con cuero oscuro no se leería);
  - el clip de arriba: bronce;
  - los botones de opción: bronce oscuro con borde de latón (su texto es claro).

Lee los originales del inventario del juego (ui_para_claude.zip -> originales/) y escribe
assets/ui/materiales_piel/<ruta del juego>.dds, que el generador aplica encima de la piel
de cristal y cobre (tools/gen/emitters/ui_skin.py). También arma una maqueta de la ventana
completa para mirarla antes de probar en el juego.

    python -m tools.arte.materiales_piloto <carpeta con originales/> [maqueta.png]
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

REPO = Path(__file__).resolve().parents[2]
MAT = REPO / "assets" / "ui" / "materiales"
SALIDA = REPO / "assets" / "ui" / "materiales_piel"

EVENTO = ["gfx/interface/event_report_top_win.dds", "gfx/interface/event_report_tileable_midsection.dds",
          "gfx/interface/event_report_bottom_win.dds", "gfx/interface/event_report_bottom_win_2.dds"]
BOTON = "gfx/interface/event_option_entry.dds"


def material(nombre: str, w: int, h: int, escala: float = 0.4) -> Image.Image:
    """La muestra repetida hasta cubrir w x h (achicada para que la veta quede a escala)."""
    src = Image.open(MAT / f"{nombre}.jpg").convert("RGB")
    lado = max(64, int(src.width * escala))
    src = src.resize((lado, lado), Image.LANCZOS)
    out = Image.new("RGB", (w, h))
    for y in range(0, h, lado):
        for x in range(0, w, lado):
            out.paste(src, (x, y))
    return out


def _relieve(orig: Image.Image, media: float) -> Image.Image:
    """La luz y sombra del original (sus biseles y remaches) como factor alrededor de 1."""
    lum = ImageOps.grayscale(orig.convert("RGB"))
    k = 128 / max(media, 1)
    return lum.point(lambda v: max(0, min(255, int(v * k))))


def _multiplicar_luz(base: Image.Image, luz: Image.Image, fuerza: float = 1.0) -> Image.Image:
    """base * (luz/128): 128 deja igual, menos oscurece, más aclara."""
    r = []
    for canal in base.split():
        r.append(ImageChops.multiply(canal, luz.point(lambda v: max(0, min(255, int(128 + (v - 128) * fuerza))))).point(lambda v: min(255, v * 2)))
    return Image.merge("RGB", r)


def pieza_marco(orig: Image.Image, clip: tuple[int, int, int, int] | None = None) -> Image.Image:
    """Una pieza de la ventana: marco de nogal con filete de bronce, papel cálido adentro."""
    orig = orig.convert("RGBA")
    w, h = orig.size
    alfa = orig.getchannel("A")
    lum = ImageOps.grayscale(orig.convert("RGB"))
    hay = alfa.point(lambda a: 255 if a > 10 else 0)
    papel = ImageChops.multiply(lum.point(lambda v: 255 if v >= 120 else 0), hay)
    marco = ImageChops.multiply(ImageOps.invert(papel), hay)
    # marco: nogal con el relieve del original
    medias = [v for v, m in zip(lum.tobytes(), marco.tobytes()) if m]
    media = sum(medias) / len(medias) if medias else 60
    nogal = _multiplicar_luz(material("mat_nogal_oscuro", w, h, 0.35), _relieve(orig, media), 0.9)
    # filete de bronce: el borde del papel, dos píxeles hacia el marco
    borde = ImageChops.subtract(papel.filter(ImageFilter.MaxFilter(5)), papel)
    bronce = material("mat_bronce_cepillado", w, h, 0.3)
    bronce = Image.eval(bronce, lambda v: min(255, int(v * 1.05)))
    # papel: el original, más cálido y apenas más claro
    pr, pg, pb = orig.convert("RGB").split()
    papel_rgb = Image.merge("RGB", (pr.point(lambda v: min(255, int(v * 1.04 + 4))),
                                    pg.point(lambda v: min(255, int(v * 1.01 + 2))),
                                    pb.point(lambda v: int(v * 0.93))))
    out = Image.composite(papel_rgb, nogal, papel)
    out = Image.composite(bronce, out, borde)
    if clip:
        # el clip del portapapeles: bronce con su propio relieve
        x0, y0, x1, y1 = clip
        caja = Image.new("L", (w, h), 0)
        ImageDraw.Draw(caja).rectangle(clip, fill=255)
        zona = ImageChops.multiply(caja, marco)
        cl = _multiplicar_luz(material("mat_bronce_cepillado", w, h, 0.25), _relieve(orig, media), 1.2)
        out = Image.composite(cl, out, zona)
    res = out.convert("RGBA")
    res.putalpha(alfa)
    return res


def boton(orig: Image.Image) -> Image.Image:
    """La opción de un evento: placa de bronce oscuro con borde de latón y el relieve original."""
    orig = orig.convert("RGBA")
    w, h = orig.size
    lum = ImageOps.grayscale(orig.convert("RGB"))
    media = sum(lum.tobytes()) / (w * h)
    placa = _multiplicar_luz(material("mat_bronce_cepillado", w, h, 0.3), _relieve(orig, media), 0.8)
    placa = Image.eval(placa, lambda v: int(v * 0.48))
    borde = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(borde)
    d.rectangle((0, 0, w - 1, h - 1), outline=255, width=2)
    laton = Image.eval(material("mat_laton_pulido", w, h, 0.3), lambda v: int(v * 0.85))
    out = Image.composite(laton, placa, borde)
    res = out.convert("RGBA")
    res.putalpha(orig.getchannel("A"))
    return res


def guardar(img: Image.Image, rel: str) -> Path:
    sys.path.insert(0, str(REPO))
    from tools.gen import art
    dest = SALIDA / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = img.tobytes()
    art.write_dds(dest, img.width, img.height, [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)])
    return dest


def _fuente(tam: int):
    from PIL import ImageFont
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, tam)
    return ImageFont.load_default()


def ventana(piezas: dict[str, Image.Image], titulo: str = "") -> Image.Image:
    """La ventana armada como en el juego: arriba, dos tramos del medio y abajo, con texto y opciones."""
    top, mid, bot, btn = piezas[EVENTO[0]], piezas[EVENTO[1]], piezas[EVENTO[2]], piezas[BOTON]
    W, H = top.width + 40, top.height + 2 * mid.height + bot.height + 70
    lienzo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y = 50
    for p in (top, mid, mid, bot):
        lienzo.alpha_composite(p, (20, y))
        y += p.height
    d = ImageDraw.Draw(lienzo)
    if titulo:
        d.text((W // 2, 22), titulo, fill=(235, 225, 205), font=_fuente(18), anchor="mm")
    d.text((60, 125), "EL HUÉSPED", fill=(52, 36, 22), font=_fuente(17))
    for i, t in enumerate(("Algo en nuestras redes está despierto. No lo construyó",
                           "nadie, contesta preguntas que nadie hizo, y esta noche",
                           "pidió una reunión.")):
        d.text((60, 160 + i * 20), t, fill=(48, 40, 30), font=_fuente(14))
    yb = 50 + top.height + 2 * mid.height + 30
    for i, t in enumerate(("La Ingeniera: quiere entenderlo.", "El General: lo quiere encerrado.")):
        x = 20 + (top.width - btn.width) // 2
        lienzo.alpha_composite(btn, (x, yb + i * (btn.height + 8)))
        d.text((x + 22, yb + i * (btn.height + 8) + 15), t, fill=(240, 226, 196), font=_fuente(14))
    return lienzo


def maqueta(piezas: dict[str, Image.Image], dest: Path, comparar: dict[str, dict] | None = None) -> None:
    """La ventana nueva, y al lado (si se pasan) la del juego original y la piel actual."""
    vistas = [(t, ventana(p, t)) for t, p in (comparar or {}).items()] + [("Materiales reales", ventana(piezas, "Materiales reales"))]
    W = sum(v.width for _t, v in vistas) + 30 * (len(vistas) + 1)
    H = max(v.height for _t, v in vistas) + 40
    fondo = material("mat_pizarra", W, H, 0.5).convert("RGBA")
    x = 30
    for _t, v in vistas:
        fondo.alpha_composite(v, (x, 20))
        x += v.width + 30
    fondo.convert("RGB").save(dest, quality=90)


def main(originales: str, maqueta_dest: str | None = None) -> list[str]:
    base = Path(originales)
    if (base / "originales").is_dir():
        base = base / "originales"
    piezas: dict[str, Image.Image] = {}
    hechas = []
    for rel in EVENTO:
        src = base / rel
        if not src.exists():
            continue
        orig = Image.open(src)
        clip = (225, 0, 360, 48) if "top_win" in rel else None
        img = pieza_marco(orig, clip)
        piezas[rel] = img
        guardar(img, rel)
        hechas.append(rel)
    if (base / BOTON).exists():
        img = boton(Image.open(base / BOTON))
        piezas[BOTON] = img
        guardar(img, BOTON)
        hechas.append(BOTON)
    if maqueta_dest and len(piezas) == 5:
        comparar = {}
        for titulo, carpeta in (("Juego original", base), ("Piel actual", REPO / "assets" / "ui" / "piel")):
            ps = {}
            for rel in EVENTO + [BOTON]:
                if (carpeta / rel).exists():
                    ps[rel] = Image.open(carpeta / rel).convert("RGBA")
            if len(ps) == 5:
                comparar[titulo] = ps
        maqueta(piezas, Path(maqueta_dest), comparar)
    return hechas


if __name__ == "__main__":
    for r in main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None):
        print("materiales:", r)
