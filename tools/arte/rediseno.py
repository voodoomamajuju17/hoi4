"""Rediseño de la interfaz desde cero (2026-11-03).

Pedido: "necesito que cambie radicalmente TODO el GUI, no quiero cambio de color y
ya, seguir los primeros mockups [...] se tiene que ver bien y bello".

Cada pieza del juego se dibuja de nuevo en el estilo de las maquetas aprobadas
(cristal y cobre): del original se toma solo el plano (su forma, sus
compartimentos y sus bordes) y encima se dibuja:
  - vidrio liso azul petróleo casi negro, con un brillo frío arriba;
  - los compartimentos del original (huecos para texto, ranuras) como vidrio
    más hondo, sin la textura de metal rayado;
  - cada borde del plano como un filete fino de cobre (más claro arriba);
  - el contorno con filo de cobre pulido y, en las piezas grandes, escuadras de
    cobre en las esquinas y remaches;
  - el papel (eventos, paneles de información) queda papel marfil liso, con
    filete de cobre.
Mismo tamaño, cuadros y transparencia que el original: todo sigue calzando.
"""

from __future__ import annotations

CU, CU_HI, CU_LO = (194, 122, 69), (240, 181, 133), (107, 58, 28)
VID_A, VID_B = (20, 34, 43), (6, 12, 16)
HONDO = (3, 7, 10)
PAPEL = (236, 226, 206)


def _lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _vgrad(w, h, top, bot):
    from PIL import Image
    col = Image.new("RGB", (1, h))
    for y in range(h):
        col.putpixel((0, y), _lerp(top, bot, y / max(1, h - 1)))
    return col.resize((w, h))


def _cobre_v(w, h):
    from PIL import Image
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        col.putpixel((0, y), _lerp(CU_HI, CU, t / 0.5) if t < 0.5 else _lerp(CU, CU_LO, (t - 0.5) / 0.5))
    return col.resize((w, h))


def redibujar(original, *, esquinas: bool | None = None, papel_ok: bool = True, mosaico: bool = False):
    """Una pieza (un cuadro) redibujada en cristal y cobre."""
    from PIL import Image, ImageChops, ImageFilter, ImageStat
    src = original.convert("RGBA")
    w, h = src.size
    alpha = src.getchannel("A")
    rgb = src.convert("RGB")
    lum = rgb.convert("L").filter(ImageFilter.MedianFilter(5)) if min(w, h) >= 8 else rgb.convert("L")
    hsv = rgb.convert("HSV")
    _, sat, val = hsv.split()

    # papel: claro y cálido (eventos, Información, Historia del país); la máscara se
    # alisa (cerrar huecos) para que sea una hoja entera y no manchas
    papel = Image.new("L", (w, h), 0)
    if papel_ok:
        suave = rgb.convert("L").filter(ImageFilter.GaussianBlur(4))
        calido = sat.filter(ImageFilter.GaussianBlur(4))
        papel = ImageChops.multiply(suave.point(lambda v: 255 if v > 125 else 0),
                                    calido.point(lambda s: 255 if s > 30 else 0))
        r = max(3, min(w, h) // 40) | 1
        papel = papel.filter(ImageFilter.MaxFilter(r)).filter(ImageFilter.MaxFilter(r))
        papel = papel.filter(ImageFilter.MinFilter(r)).filter(ImageFilter.MinFilter(r))
        papel = papel.filter(ImageFilter.GaussianBlur(1))
        # solo hojas de verdad: si es menos del 15% de la pieza, era metal claro
        if ImageStat.Stat(papel).mean[0] < 255 * 0.15:
            papel = Image.new("L", (w, h), 0)

    # huecos: lo bastante más oscuro que su entorno
    entorno = lum.filter(ImageFilter.BoxBlur(max(2, min(w, h) // 10)))
    hondo = ImageChops.subtract(entorno, lum).point(lambda d: min(255, max(0, (d - 8) * 12)))
    hondo = hondo.filter(ImageFilter.GaussianBlur(1))

    # centro en mosaico (el juego lo repite): vidrio parejo, sin degradé que haga franjas
    base = Image.new("RGB", (w, h), _lerp(VID_A, VID_B, 0.55)) if mosaico else _vgrad(w, h, VID_A, VID_B)
    base = Image.composite(_vgrad(w, h, (8, 15, 20), HONDO), base, hondo)
    # en las piezas que se apilan (sin escuadras) el papel va parejo, si no hace franjas
    hoja = Image.new("RGB", (w, h), _lerp(PAPEL, (224, 210, 186), 0.5)) if esquinas is False \
        else _vgrad(w, h, PAPEL, (224, 210, 186))
    base = Image.composite(hoja, base, papel)

    # filetes: los bordes del plano, finos, en cobre
    bordes = lum.filter(ImageFilter.GaussianBlur(1.3)).filter(ImageFilter.FIND_EDGES)
    bordes = bordes.point(lambda e: 0 if e < 20 else min(255, (e - 20) * 6))
    bordes = bordes.filter(ImageFilter.MedianFilter(3))
    bordes = ImageChops.multiply(bordes, ImageChops.invert(papel.filter(ImageFilter.MinFilter(3))))
    cobre = _cobre_v(w, h)
    linea = bordes.point(lambda v: round(min(255, v * 0.9)))
    out = Image.composite(cobre, base, linea)

    # contorno de la forma: filo pulido + sombra interior
    duro = alpha.point(lambda a: 255 if a > 90 else 0)
    if min(w, h) >= 6:
        adentro = duro.filter(ImageFilter.MinFilter(3))
        filo = ImageChops.subtract(duro, adentro)
        out = Image.composite(cobre, out, filo)
        if min(w, h) >= 12:
            adentro2 = adentro.filter(ImageFilter.MinFilter(3))
            sombra = ImageChops.subtract(adentro, adentro2).point(lambda v: v * 160 // 255)
            out = Image.composite(Image.new("RGB", (w, h), (0, 0, 0)), out, sombra)

    out = out.convert("RGBA")
    # escuadras y remaches en las piezas grandes
    if esquinas is None:
        esquinas = w >= 120 and h >= 60
    if esquinas:
        from PIL import ImageDraw
        box = duro.getbbox()
        if box:
            d = ImageDraw.Draw(out)
            l, t, r, b = box[0] + 2, box[1] + 2, box[2] - 3, box[3] - 3
            L = max(10, min(26, (r - l) // 8, (b - t) // 4))
            for (x, y, dx, dy) in ((l, t, 1, 1), (r, t, -1, 1), (l, b, 1, -1), (r, b, -1, -1)):
                for k in range(2):
                    d.line((x, y + dy * k, x + dx * L, y + dy * k), fill=CU_HI + (255,))
                    d.line((x + dx * k, y, x + dx * k, y + dy * L), fill=CU_HI + (255,))
                cx, cy = x + dx * 7, y + dy * 7
                for rr in (3, 2, 1):
                    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr),
                              fill=_lerp((255, 217, 184), CU_LO, rr / 3) + (255,))
    out.putalpha(alpha)
    return out


def redibujar_cuadros(original, n: int = 1, **kw):
    from PIL import Image
    src = original.convert("RGBA")
    fw = src.width // max(1, n)
    out = Image.new("RGBA", src.size, (0, 0, 0, 0))
    for i in range(max(1, n)):
        f = src.crop((i * fw, 0, (i + 1) * fw, src.height))
        r = redibujar(f, **kw)
        if n > 1 and i == 1:   # mouse encima: un poco más de luz
            from PIL import ImageEnhance
            a = r.getchannel("A")
            r = ImageEnhance.Brightness(r.convert("RGB")).enhance(1.25).convert("RGBA")
            r.putalpha(a)
        out.paste(r, (i * fw, 0))
    return out
