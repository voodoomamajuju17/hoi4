"""Arte de la Ficha del Líder (2026-11-03): cristal y cobre, marcos por facción.

Dibuja con Pillow, una sola vez, las piezas que usa
tools/gen/emitters/ficha_lider.py y las deja en assets/ui/ficha/ (el build
solo las copia, no necesita Pillow). Las medidas salen de DISENO del emisor,
así lo dibujado y lo ubicado en la ventana coinciden.

    python3 -m tools.arte.arte ficha

Paleta de la maqueta aprobada: cobre #c27a45 (luz #f0b585, sombra #6b3a1c),
cristal azul petróleo casi negro, turquesa #4fd6c8 para lo que suman los
ministros.
"""

from __future__ import annotations

import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SALIDA = REPO / "assets" / "ui" / "ficha"

CU, CU_HI, CU_LO = (194, 122, 69), (240, 181, 133), (107, 58, 28)
TEAL, TEAL_HI, TEAL_LO = (79, 214, 200), (143, 243, 232), (42, 143, 136)
VIDRIO_A, VIDRIO_B = (18, 31, 39), (7, 13, 17)
ORO = (201, 170, 92)


def _lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def _grad_v(w, h, top, bottom, alpha=255):
    from PIL import Image
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        c = _lerp(top, bottom, y / max(1, h - 1))
        for x in range(w):
            px[x, y] = c + (alpha,)
    return img


def _cobre(t):
    """Color del cobre pulido a lo largo de un borde (t de 0 a 1)."""
    t = t % 1.0
    pts = [(0, CU_HI), (0.3, CU), (0.55, CU_LO), (0.75, CU), (1, CU_HI)]
    for (a, ca), (b, cb) in zip(pts, pts[1:]):
        if a <= t <= b:
            return _lerp(ca, cb, (t - a) / (b - a))
    return CU


def _borde_cobre(img, inset=0, ancho=1, alpha=255):
    from PIL import ImageDraw
    w, h = img.size
    d = ImageDraw.Draw(img)
    for k in range(ancho):
        i = inset + k
        per = 2 * (w + h)
        for x in range(i, w - i):
            d.point((x, i), _cobre(x / per) + (alpha,))
            d.point((x, h - 1 - i), _cobre((x + w + h) / per) + (alpha,))
        for y in range(i, h - i):
            d.point((i, y), _cobre((y + 2 * w + h) / per) + (alpha,))
            d.point((w - 1 - i, y), _cobre((y + w) / per) + (alpha,))


def _hilo(img, x0, x1, y, color=CU, alpha=220):
    """Línea que se desvanece en las puntas (el .hair de la maqueta)."""
    px = img.load()
    for x in range(x0, x1):
        t = (x - x0) / max(1, x1 - x0)
        a = alpha * min(1, t / 0.2, (1 - t) / 0.2)
        c = _lerp(color, CU_HI, 1 - abs(t - 0.5) * 2)
        r, g, b, a0 = px[x, y]
        k = a / 255
        px[x, y] = (round(r * (1 - k) + c[0] * k), round(g * (1 - k) + c[1] * k), round(b * (1 - k) + c[2] * k),
                    max(a0, round(a)))


def _remache(img, cx, cy, r=4):
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    for k in range(r, 0, -1):
        t = k / r
        d.ellipse((cx - k, cy - k, cx + k, cy + k), fill=_lerp((255, 217, 184), CU_LO, t) + (255,))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(20, 10, 4, 200))


def _esquinas(img, largo=22, color=CU_HI, inset=0):
    from PIL import ImageDraw
    w, h = img.size
    d = ImageDraw.Draw(img)
    c = color + (235,)
    i = inset
    for (x, y, dx, dy) in ((i, i, 1, 1), (w - 1 - i, i, -1, 1), (i, h - 1 - i, 1, -1), (w - 1 - i, h - 1 - i, -1, -1)):
        for k in range(2):
            d.line((x, y + dy * k, x + dx * largo, y + dy * k), fill=c)
            d.line((x + dx * k, y, x + dx * k, y + dy * largo), fill=c)


def fondo(D):
    from PIL import Image, ImageDraw
    W, H = D["ventana"]
    img = _grad_v(W, H, VIDRIO_A, VIDRIO_B, 242)
    # brillo turquesa muy leve arriba al centro (el cristal)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gp = glow.load()
    for y in range(0, 260):
        for x in range(W):
            dx, dy = (x - W / 2) / (W * 0.55), y / 260
            v = max(0.0, 1 - math.hypot(dx, dy))
            if v > 0:
                gp[x, y] = TEAL + (round(14 * v),)
    img.alpha_composite(glow)
    # cabecera: un velo de cobre que se apaga hacia abajo
    cab = D["cabecera"]
    px = img.load()
    for y in range(cab):
        k = 0.16 * (1 - y / cab)
        for x in range(W):
            r, g, b, a = px[x, y]
            px[x, y] = (round(r + (CU[0] - r) * k), round(g + (CU[1] - g) * k), round(b + (CU[2] - b) * k), a)
    _hilo(img, 0, W, cab)
    _hilo(img, 0, W, cab + 1, CU_LO, 120)
    # secciones (después del rótulo, que lo escribe el juego)
    sx = D["stats_x"]
    sec = D["secciones"]
    _hilo(img, sx + 110, W - 36, sec["atributos"] - 9)
    _hilo(img, sx + 170, W - 36, sec["pesa"] - 9)
    _hilo(img, 36 + 330, W - 36, sec["gabinete"] - 9)
    # renglones de las stats, cajas y anillo: se dibujan en una capa aparte y se
    # mezclan (2026-11-03, captura: dibujados directo reemplazaban el vidrio por
    # algo casi transparente y se veía el mapa a través)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for y in D["stats_y"]:
        d.line((sx, y + 44, sx + 520, y + 44), fill=(255, 255, 255, 14))
    # cajas de "lo que pesa hoy"
    ew, eh = D["efecto"]
    for x in D["efectos_x"]:
        y = D["efectos_y"]
        d.rectangle((x, y, x + ew, y + eh), fill=(255, 255, 255, 9))
        d.rectangle((x, y, x + 1, y + eh), fill=CU + (255,))
    # placa del nombre debajo del retrato
    qx0, py0, qx1, py1 = D["placa"]
    poly = [(qx0 + 14, py0), (qx1 - 14, py0), (qx1, (py0 + py1) // 2), (qx1 - 14, py1), (qx0 + 14, py1), (qx0, (py0 + py1) // 2)]
    placa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(placa)
    pd.polygon(poly, fill=(30, 18, 10, 235), outline=CU + (255,))
    img.alpha_composite(placa)
    # anillo de salud: un círculo punteado alrededor
    ax, ay, ad = D["anillo"]
    cx, cy, r = ax + ad / 2, ay + ad / 2, ad / 2 + 9
    for k in range(0, 360, 6):
        a0 = math.radians(k)
        a1 = math.radians(k + 3)
        d.line((cx + r * math.cos(a0), cy + r * math.sin(a0), cx + r * math.cos(a1), cy + r * math.sin(a1)),
               fill=CU + (120,))
    img.alpha_composite(capa)
    d = ImageDraw.Draw(img)
    # pie
    _hilo(img, 36, W - 36, H - 44, CU_LO, 160)
    # borde de cobre, filete interior, esquinas y remaches
    _borde_cobre(img, 0, 1)
    filete = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(filete).rectangle((3, 3, W - 4, H - 4), outline=(0, 0, 0, 160))
    img.alpha_composite(filete)
    _esquinas(img)
    for x, y in ((9, 9), (W - 10, 9), (9, H - 10), (W - 10, H - 10)):
        _remache(img, x, y)
    return img


def retrato_marco(D):
    from PIL import Image, ImageDraw
    _, _, w, h = D["retrato_marco"]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for k in range(8):
        t = k / 7
        for x in range(k, w - k):
            c = _lerp(_cobre(x / (2 * w)), CU_LO, t * 0.6)
            d.point((x, k), c + (255,))
            d.point((x, h - 1 - k), _lerp(c, CU_LO, 0.3) + (255,))
        for y in range(k, h - k):
            c = _lerp(_cobre(y / (2 * h) + 0.25), CU_LO, t * 0.6)
            d.point((k, y), c + (255,))
            d.point((w - 1 - k, y), _lerp(c, CU_LO, 0.3) + (255,))
    d.rectangle((7, 7, w - 8, h - 8), outline=(0, 0, 0, 230))
    d.rectangle((0, 0, w - 1, h - 1), outline=(0, 0, 0, 200))
    # sombra interior abajo, para que el nombre se lea mejor
    sombra = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sp = sombra.load()
    for y in range(h - 80, h - 8):
        a = round(170 * (y - (h - 80)) / 72)
        for x in range(8, w - 8):
            sp[x, y] = (0, 0, 0, a)
    img.alpha_composite(sombra)
    for x, y in ((3, 3), (w - 4, 3), (3, h - 4), (w - 4, h - 4)):
        _remache(img, x, y, 3)
    return img


def _barra(D, color_lleno, vacios: bool):
    from PIL import Image, ImageDraw
    _, bw, bh = D["barra"]
    n = 20
    seg, gap = 12, 3
    frames = []
    for k in range(n + 1):
        f = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        d = ImageDraw.Draw(f)
        for i in range(n):
            x = i * (seg + gap) + 2
            poly = [(x + 3, 0), (x + seg + 3, 0), (x + seg, bh - 1), (x, bh - 1)]
            if i < k:
                top, mid, low = color_lleno
                for y in range(bh):
                    t = y / (bh - 1)
                    c = _lerp(top, mid, t / 0.6) if t < 0.6 else _lerp(mid, low, (t - 0.6) / 0.4)
                    off = 3 * (1 - y / (bh - 1))
                    d.line((x + off, y, x + seg + off - 1, y), fill=c + (255,))
            elif vacios:
                d.polygon(poly, fill=(255, 255, 255, 16), outline=(255, 255, 255, 22))
        frames.append(f)
    out = Image.new("RGBA", (bw * (n + 1), bh), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        out.paste(f, (i * bw, 0))
    return out


def salud(D):
    from PIL import Image, ImageDraw
    _, _, ad = D["anillo"]
    n = 21
    out = Image.new("RGBA", (ad * n, ad), (0, 0, 0, 0))
    S = 4   # se dibuja grande y se achica: bordes suaves
    for k in range(n):
        big = Image.new("RGBA", (ad * S, ad * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(big)
        r0, r1 = (ad / 2 - 3) * S, (ad / 2 - 15) * S
        c = ad * S / 2
        d.ellipse((c - r0, c - r0, c + r0, c + r0), fill=(255, 255, 255, 20))
        frac = k / (n - 1)
        if frac > 0:
            color = CU_HI if frac > 0.3 else (226, 110, 86)
            d.pieslice((c - r0, c - r0, c + r0, c + r0), -90, -90 + 360 * frac, fill=color + (255,))
        d.ellipse((c - r1, c - r1, c + r1, c + r1), fill=(0, 0, 0, 0))
        # el agujero tiene que quedar transparente de verdad
        hole = Image.new("L", big.size, 0)
        ImageDraw.Draw(hole).ellipse((c - r1, c - r1, c + r1, c + r1), fill=255)
        big.putalpha(Image.composite(Image.new("L", big.size, 0), big.getchannel("A"), hole))
        out.paste(big.resize((ad, ad), Image.LANCZOS), (k * ad, 0))
    return out


def _hexagono(w, h, inset=0):
    return [(w * 0.25 + inset * 0.5, inset), (w * 0.75 - inset * 0.5, inset), (w - 1 - inset, h / 2),
            (w * 0.75 - inset * 0.5, h - 1 - inset), (w * 0.25 + inset * 0.5, h - 1 - inset), (inset, h / 2)]


def boton(D):
    from PIL import Image, ImageDraw
    final = D["boton"]
    n = 46   # se dibuja a 46 y se achica al tamaño de la barra
    S = 4
    big = Image.new("RGBA", (n * S, n * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.polygon(_hexagono(n * S, n * S), fill=CU + (255,))
    d.polygon(_hexagono(n * S, n * S, 2 * S), fill=(20, 32, 40, 250))
    d.polygon(_hexagono(n * S, n * S, 3 * S), fill=(14, 22, 28, 255))
    c = n * S / 2
    # busto: cabeza y hombros en cobre claro, una corona chica arriba
    d.ellipse((c - 5 * S, c - 10 * S, c + 5 * S, c), fill=CU_HI + (255,))
    d.pieslice((c - 11 * S, c + 1 * S, c + 11 * S, c + 21 * S), 180, 360, fill=CU_HI + (255,))
    for dx in (-5, 0, 5):
        d.polygon([(c + (dx - 2) * S, c - 12 * S), (c + dx * S, c - 16 * S), (c + (dx + 2) * S, c - 12 * S)], fill=CU + (255,))
    return big.resize((final, final), Image.LANCZOS)


def boton_accion(D):
    from PIL import Image, ImageDraw
    w, h = D["accion"]
    img = _grad_v(w, h, (40, 58, 66), (14, 24, 30))
    _borde_cobre(img, 0, 1)
    d = ImageDraw.Draw(img)
    d.line((2, 1, w - 3, 1), fill=(255, 255, 255, 40))
    return img


def boton_chico(D):
    from PIL import Image, ImageDraw
    w, h = D["boton_chico"]
    img = _grad_v(w, h, (40, 58, 66), (14, 24, 30))
    _borde_cobre(img, 0, 1)
    return img


def carta_ancha(D):
    from PIL import Image, ImageDraw
    w, h = D["heredero"][2], D["heredero"][3]
    img = Image.new("RGBA", (w, h), (30, 18, 10, 120))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w - 1, h - 1), outline=CU_HI + (200,))
    d.rectangle((4, 6, 4 + 68, 6 + 91), outline=CU + (255,))
    return img


def carta(D):
    from PIL import Image, ImageDraw
    w, h = D["gabinete"][4], D["gabinete"][5]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 80))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w - 1, h - 1), outline=CU + (150,))
    d.rectangle((4, 6, 4 + 68, 6 + 91), outline=CU + (255,))
    return img


def apagado(D):
    from PIL import Image
    w, h = D["gabinete"][4], D["gabinete"][5]
    return Image.new("RGBA", (w, h), (4, 8, 10, 165))


def sin_retrato(D):
    from PIL import Image, ImageDraw
    w, h = 156, 210
    img = _grad_v(w, h, (26, 40, 48), (8, 14, 18))
    d = ImageDraw.Draw(img)
    d.ellipse((w / 2 - 30, 46, w / 2 + 30, 116), fill=(3, 6, 8, 255))
    d.pieslice((w / 2 - 70, 120, w / 2 + 70, 300), 180, 360, fill=(3, 6, 8, 255))
    d.arc((w / 2 - 31, 45, w / 2 + 31, 117), 200, 330, fill=CU + (180,), width=2)
    return img


# -- marcos por facción (van encima del fondo, solo en los bordes) ---------------

def _vacio():
    from PIL import Image
    return Image.new("RGBA", (8, 8), (0, 0, 0, 0))


def _enredadera(d, x0, y0, sx, sy, color):
    """Rama con hojas desde una esquina (sx, sy: hacia dónde crece)."""
    pts = []
    for i in range(41):
        t = i / 40
        # curva de Bézier de la maqueta: M8 112 C8 60 30 22 112 8 (en 120x120)
        bx = (1 - t) ** 3 * 8 + 3 * (1 - t) ** 2 * t * 8 + 3 * (1 - t) * t ** 2 * 30 + t ** 3 * 112
        by = (1 - t) ** 3 * 112 + 3 * (1 - t) ** 2 * t * 60 + 3 * (1 - t) * t ** 2 * 22 + t ** 3 * 8
        pts.append((x0 + sx * bx * 0.8, y0 + sy * (120 - by) * 0.8))
    d.line(pts, fill=color + (255,), width=3)
    for t, lado in ((0.25, 1), (0.45, -1), (0.65, 1), (0.82, -1)):
        x, y = pts[int(t * 40)]
        hx, hy = x + sx * 11 * lado, y + sy * 9
        d.polygon([(x, y), (hx - sx * 3, hy - sy * 8), (hx + sx * 7, hy)], fill=color + (150,), outline=color + (255,))
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color + (255,))


def marco_efe(D):
    from PIL import Image, ImageDraw
    W, H = D["ventana"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((5, 5, W - 6, H - 6), outline=ORO + (120,))
    # cada rama nace en la esquina y sube por el borde (96 px)
    _enredadera(d, 6, 6 + 96, 1, -1, ORO)
    _enredadera(d, W - 7, 6 + 96, -1, -1, ORO)
    _enredadera(d, 6, H - 7 - 96, 1, 1, ORO)
    _enredadera(d, W - 7, H - 7 - 96, -1, 1, ORO)
    return img


def marco_fcu(D):
    from PIL import Image, ImageDraw
    W, H = D["ventana"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cromo = lambda t: _lerp((159, 178, 200), (233, 240, 248), 1 - abs(((t * 3) % 1) - 0.5) * 2)
    for x in range(W):
        d.point((x, 1), cromo(x / W) + (255,))
        d.point((x, H - 2), cromo(x / W + 0.3) + (255,))
    for y in range(H):
        d.point((1, y), cromo(y / H) + (220,))
        d.point((W - 2, y), cromo(y / H + 0.5) + (220,))
    # esquinas cortadas: un chaflán de cromo en dos esquinas, como la ventana de la FCU
    for (x0, y0, x1, y1) in ((0, 30, 30, 0), (W - 31, H - 1, W - 1, H - 31)):
        d.line((x0, y0, x1, y1), fill=(233, 240, 248, 255), width=3)
    tri = [(0, 0), (28, 0), (0, 28)]
    d.polygon(tri, fill=(6, 12, 26, 255))
    d.polygon([(W - 1, H - 1), (W - 29, H - 1), (W - 1, H - 29)], fill=(6, 12, 26, 255))
    # marcas de medición azules
    for x in range(60, W - 60, 24):
        d.line((x, 4, x, 8 if (x // 24) % 4 else 12), fill=(94, 200, 255, 160))
    return img


def marco_asc(D):
    from PIL import Image, ImageDraw
    W, H = D["ventana"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W - 1, H - 1), outline=(232, 228, 220, 255), width=3)
    rojo = (200, 16, 46)
    # la cuña roja de la esquina de arriba a la derecha
    cuña = Image.new("RGBA", (420, 200), (0, 0, 0, 0))
    ImageDraw.Draw(cuña).rectangle((0, 70, 420, 130), fill=rojo + (235,))
    cuña = cuña.rotate(24, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(cuña, (W - 200, -cuña.height // 2 - 10))
    # franja roja y blanca abajo
    for x in range(3, W - 3):
        c = rojo if (x // 40) % 2 == 0 else (232, 228, 220)
        for y in range(H - 9, H - 3):
            img.putpixel((x, y), c + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W - 1, H - 1), outline=(232, 228, 220, 255), width=3)
    return img


def _estrella(d, cx, cy, r, color):
    d.polygon([(cx, cy - r), (cx + r * 0.25, cy - r * 0.25), (cx + r, cy), (cx + r * 0.25, cy + r * 0.25),
               (cx, cy + r), (cx - r * 0.25, cy + r * 0.25), (cx - r, cy), (cx - r * 0.25, cy - r * 0.25)],
              fill=color + (255,))


def marco_zal(D):
    from PIL import Image, ImageDraw
    W, H = D["ventana"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # un velo vino arriba al centro
    px = img.load()
    for y in range(0, 220):
        for x in range(W):
            v = max(0.0, 1 - math.hypot((x - W / 2) / (W * 0.5), y / 220))
            if v > 0:
                px[x, y] = (120, 30, 40, round(70 * v))
    d = ImageDraw.Draw(img)
    bronce = (184, 149, 90)
    d.rectangle((6, 6, W - 7, H - 7), outline=bronce + (255,))
    d.rectangle((10, 10, W - 11, H - 11), outline=bronce + (200,))
    for x, y in ((18, 18), (W - 19, 18), (18, H - 19), (W - 19, H - 19)):
        _estrella(d, x, y, 9, (214, 178, 110))
    _estrella(d, W // 2, 8, 6, (214, 178, 110))
    return img


def marco_zjp(D):
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    W, H = D["ventana"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    carmesi, neon = (208, 16, 58), (255, 45, 120)
    d.rectangle((0, 0, W - 1, 2), fill=carmesi + (255,))
    d.rectangle((0, H - 2, W - 1, H - 1), fill=carmesi + (255,))
    brillo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(brillo)
    for y in range(0, int(H * 0.75)):
        a = round(255 * (1 - y / (H * 0.75)))
        bd.line((1, y, 3, y), fill=neon + (a,))
    img.alpha_composite(brillo.filter(ImageFilter.GaussianBlur(4)))
    img.alpha_composite(brillo)
    # el sello: 将軍 en vertical, en carmesí, abajo a la derecha
    for fuente in ("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
                   "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"):
        if Path(fuente).exists():
            f = ImageFont.truetype(fuente, 30)
            for i, ch in enumerate("将軍"):
                d.text((W - 52, H - 128 + i * 36), ch, font=f, fill=carmesi + (210,))
            break
    return img


PIEZAS = {
    "fondo": fondo, "retrato_marco": retrato_marco,
    "barra_total": lambda D: _barra(D, (TEAL_HI, TEAL, TEAL_LO), True),
    "barra_base": lambda D: _barra(D, (CU_HI, CU, CU_LO), False),
    "salud": salud, "boton": boton, "boton_accion": boton_accion, "boton_chico": boton_chico, "carta_ancha": carta_ancha, "carta": carta, "apagado": apagado, "sin_retrato": sin_retrato,
    "marco_base": lambda D: _vacio(), "marco_efe": marco_efe, "marco_fcu": marco_fcu, "marco_asc": marco_asc,
    "marco_zal": marco_zal, "marco_zjp": marco_zjp,
}


def dibujar(salida: Path = SALIDA) -> list[str]:
    import sys
    sys.path.insert(0, str(REPO))
    from tools.gen import art
    from tools.gen.emitters.ficha_lider import DISENO
    salida.mkdir(parents=True, exist_ok=True)
    hechas = []
    for nombre, fn in PIEZAS.items():
        img = fn(DISENO).convert("RGBA")
        raw = img.tobytes()
        art.write_dds(salida / f"{nombre}.dds", img.width, img.height,
                      [tuple(raw[k:k + 4]) for k in range(0, len(raw), 4)])
        hechas.append(f"{nombre} {img.width}x{img.height}")
    return [f"ficha: {len(hechas)} piezas en {salida.relative_to(REPO)}"] + ["  " + h for h in hechas]


def main(argv: list[str]) -> None:
    for line in dibujar(Path(argv[0]) if argv else SALIDA):
        print(line)
