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
    # 2026-11-05 ("definitivamente necesita un nuevo ícono"): si llegó el arte pedido
    # (arte/pedidos_fijos/24_barra_superior.txt), va ese, achicado al tamaño de la barra
    fuente = SALIDA / "fuente" / "boton_lider.png"
    if fuente.exists():
        img = Image.open(fuente).convert("RGBA")
        caja = img.getchannel("A").point(lambda a: 255 if a > 16 else 0).getbbox()
        if caja:
            img = img.crop(caja)
        img.thumbnail((final, final), Image.LANCZOS)
        out = Image.new("RGBA", (final, final), (0, 0, 0, 0))
        out.alpha_composite(img, ((final - img.width) // 2, (final - img.height) // 2))
        return out
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
    # 2026-11-05 ("no vi el color de facción en el EFE, ¿no debería ser un verde?")
    VERDE = (92, 196, 112)
    d.rectangle((5, 5, W - 6, H - 6), outline=VERDE + (120,))
    # cada rama nace en la esquina y sube por el borde (96 px)
    _enredadera(d, 6, 6 + 96, 1, -1, VERDE)
    _enredadera(d, W - 7, 6 + 96, -1, -1, VERDE)
    _enredadera(d, 6, H - 7 - 96, 1, 1, VERDE)
    _enredadera(d, W - 7, H - 7 - 96, -1, 1, VERDE)
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


def _marco_color(color):
    """Marco sobrio en el color de la facción (2026-11-03, HSN, NAS, SHD, APF y Roma):
    filete fino a 5 px del borde y escuadras con remache en las cuatro esquinas."""
    def dibujar(D):
        from PIL import Image, ImageDraw, ImageFilter
        W, H = D["ventana"]
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle((5, 5, W - 6, H - 6), outline=color + (150,))
        L = 46
        for (x, y, dx, dy) in ((5, 5, 1, 1), (W - 6, 5, -1, 1), (5, H - 6, 1, -1), (W - 6, H - 6, -1, -1)):
            for k in range(3):
                d.line((x, y + dy * k, x + dx * L, y + dy * k), fill=color + (255,))
                d.line((x + dx * k, y, x + dx * k, y + dy * L), fill=color + (255,))
            d.ellipse((x + dx * 10 - 3, y + dy * 10 - 3, x + dx * 10 + 3, y + dy * 10 + 3), fill=color + (255,))
        halo = img.filter(ImageFilter.GaussianBlur(2))
        halo.alpha_composite(img)
        return halo
    return dibujar


# -- detalles por facción (2026-11-05, "ponele un toque más de personalidad a la ventana
# del líder... expandir el uso del color único"): encima de cada marco, en el color de
# la facción (11_scenario.yaml -> faction_accents): el filete de la cabecera, un rombo y
# un tramo de color al empezar cada sección, un halo detrás del retrato, el borde de la
# placa del nombre, el canto de las cajas de "lo que pesa hoy" y la viñeta del lema.

def _hilo_color(img, x0, x1, y, color, alpha=230, puntas=0.25):
    """Línea de 1 px en el color dado que se apaga en las puntas, con un halo de 1 px."""
    from PIL import Image, ImageDraw, ImageFilter
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for x in range(x0, x1):
        t = (x - x0) / max(1, x1 - x0)
        a = alpha * max(0.0, min(1.0, t / puntas, (1 - t) / puntas))
        d.point((x, y), tuple(color) + (round(a),))
    halo = capa.filter(ImageFilter.GaussianBlur(1.4))
    img.alpha_composite(halo)
    img.alpha_composite(capa)


def _rombo(d, cx, cy, r, color, alpha=255):
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=tuple(color) + (alpha,),
              outline=(20, 10, 4, 200))


def _detalles(img, D, color):
    from PIL import Image, ImageDraw, ImageFilter
    W, H = D["ventana"]
    color = tuple(color)
    claro = _lerp(color, (255, 255, 255), 0.35)
    # halo detrás del retrato: se ve alrededor del marco del retrato
    mx, my, mw, mh = D["retrato_marco"]
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).rounded_rectangle((mx - 4, my - 4, mx + mw + 4, my + mh + 4), radius=10,
                                          outline=color + (150,), width=6)
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(7)))
    # cabecera: el filete de cobre toma el color de la facción en el centro
    _hilo_color(img, 0, W, D["cabecera"], color, 210, 0.3)
    # secciones: un rombo y un tramo de color al empezar cada filete
    sx, sec = D["stats_x"], D["secciones"]
    d = ImageDraw.Draw(img)
    for x0, y in ((sx + 110, sec["atributos"] - 9), (sx + 170, sec["pesa"] - 9), (36 + 330, sec["gabinete"] - 9)):
        _hilo_color(img, x0 + 8, x0 + 150, y, color, 230, 0.6)
        d = ImageDraw.Draw(img)
        _rombo(d, x0, y, 4, claro)
    # placa del nombre: un filete de color por dentro del borde de cobre
    qx0, py0, qx1, py1 = D["placa"]
    i = 4
    poly = [(qx0 + 14 + i, py0 + i), (qx1 - 14 - i, py0 + i), (qx1 - i, (py0 + py1) // 2), (qx1 - 14 - i, py1 - i),
            (qx0 + 14 + i, py1 - i), (qx0 + i, (py0 + py1) // 2)]
    placa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(placa).polygon(poly, outline=color + (190,))
    img.alpha_composite(placa)
    d = ImageDraw.Draw(img)
    for x in (qx0 + 2, qx1 - 2):
        _rombo(d, x, (py0 + py1) // 2, 3, claro)
    # cajas de "lo que pesa hoy": el canto izquierdo en el color de la facción
    ew, eh = D["efecto"]
    for x in D["efectos_x"]:
        y = D["efectos_y"]
        d.rectangle((x, y, x + 1, y + eh), fill=color + (255,))
        d.line((x + 2, y, x + 40, y), fill=color + (110,))
    # pie: viñeta del lema
    _rombo(d, 56, H - 25, 4, claro)
    return img


def _colores_estilo() -> dict:
    """Estilo de marco -> color de la facción (de 11_scenario.yaml, faction_accents)."""
    import yaml
    from tools.gen.emitters.ficha_lider import ESTILOS_POR_DEFECTO
    cfg = (yaml.safe_load((REPO / "spec" / "11_scenario.yaml").read_text(encoding="utf-8"))
           .get("ficha_lider") or {})
    colores = (cfg.get("faction_accents") or {}).get("colors") or {}
    estilos = {**ESTILOS_POR_DEFECTO, **(cfg.get("styles") or {})}
    return {e: colores[t] for t, e in estilos.items() if t in colores}


PIEZAS = {
    "fondo": fondo, "retrato_marco": retrato_marco,
    "barra_total": lambda D: _barra(D, (TEAL_HI, TEAL, TEAL_LO), True),
    "barra_base": lambda D: _barra(D, (CU_HI, CU, CU_LO), False),
    "salud": salud, "boton": boton, "boton_accion": boton_accion, "boton_chico": boton_chico, "carta_ancha": carta_ancha, "carta": carta, "apagado": apagado, "sin_retrato": sin_retrato,
    "marco_base": lambda D: _vacio(), "marco_efe": marco_efe, "marco_fcu": marco_fcu, "marco_asc": marco_asc,
    "marco_zal": marco_zal, "marco_zjp": marco_zjp,
    "marco_hsn": _marco_color((46, 184, 178)), "marco_nas": _marco_color((240, 192, 64)),
    "marco_shd": _marco_color((72, 186, 128)), "marco_apf": _marco_color((222, 146, 54)),
    "marco_nre": _marco_color((156, 76, 168)),
}


def dibujar(salida: Path = SALIDA) -> list[str]:
    import sys
    sys.path.insert(0, str(REPO))
    from tools.gen import art
    from tools.gen.emitters.ficha_lider import DISENO
    salida.mkdir(parents=True, exist_ok=True)
    hechas = []
    colores = _colores_estilo()
    for nombre, fn in PIEZAS.items():
        img = fn(DISENO).convert("RGBA")
        estilo = nombre[len("marco_"):] if nombre.startswith("marco_") else None
        if estilo in colores and img.size == tuple(DISENO["ventana"]):
            img = _detalles(img, DISENO, colores[estilo])
        raw = img.tobytes()
        art.write_dds(salida / f"{nombre}.dds", img.width, img.height,
                      [tuple(raw[k:k + 4]) for k in range(0, len(raw), 4)])
        hechas.append(f"{nombre} {img.width}x{img.height}")
    return [f"ficha: {len(hechas)} piezas en {salida.relative_to(REPO)}"] + ["  " + h for h in hechas]


def recursos_chicos(lado: int = 28) -> list[str]:
    """Los íconos de recursos propios (assets/ui/recursos, 512 px) achicados para la barra
    superior (2026-11-03): el juego no achica bien una imagen grande, sale serruchada."""
    import sys
    sys.path.insert(0, str(REPO))
    from PIL import Image
    from tools.gen import art
    base = REPO / "assets" / "ui" / "recursos"
    salida = base / "chicos"
    hechas = []
    for src in sorted(base.glob("*.dds")):
        img = Image.open(src).convert("RGBA")
        caja = img.getchannel("A").point(lambda a: 255 if a > 16 else 0).getbbox()
        if caja:
            img = img.crop(caja)
        k = lado / max(img.size)
        img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
        lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
        lienzo.alpha_composite(img, ((lado - img.width) // 2, (lado - img.height) // 2))
        raw = lienzo.tobytes()
        art.write_dds(salida / src.name, lado, lado, [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)])
        hechas.append(src.stem)
    return [f"recursos: {len(hechas)} íconos chicos ({lado} px) en {salida.relative_to(REPO)}"]


def recursos_ficha(colores: dict, lado_emblema: int = 44, lado_marca: int = 260) -> list[str]:
    """El recurso propio en la Ficha del Líder (2026-11-05): un emblema junto a "EL LÍDER"
    (con un halo suave en el color de la facción) y una marca de agua grande y tenue,
    teñida de ese color, detrás de los atributos. Solo los recursos principales
    (los de la barra superior), que son los que identifican a la nación."""
    import sys
    sys.path.insert(0, str(REPO))
    from PIL import Image, ImageFilter, ImageOps
    from tools.gen import art
    base = REPO / "assets" / "ui" / "recursos"

    def ajustar(img, lado, relleno=1.0):
        caja = img.getchannel("A").point(lambda a: 255 if a > 16 else 0).getbbox()
        if caja:
            img = img.crop(caja)
        k = lado * relleno / max(img.size)
        img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
        lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
        lienzo.alpha_composite(img, ((lado - img.width) // 2, (lado - img.height) // 2))
        return lienzo

    def guardar(img, ruta):
        raw = img.tobytes()
        art.write_dds(ruta, img.width, img.height, [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)])

    hechas = []
    for icono, color in colores.items():
        src = base / f"{icono}.dds"
        if not src.exists():
            continue
        color = tuple(color)
        img = Image.open(src).convert("RGBA")
        # emblema: el ícono con un halo de color detrás
        e = ajustar(img, lado_emblema, 0.86)
        halo = Image.new("RGBA", e.size, color + (0,))
        halo.putalpha(e.getchannel("A").point(lambda a: round(a * 0.7)))
        halo = halo.filter(ImageFilter.GaussianBlur(3))
        halo.alpha_composite(e)
        guardar(halo, base / "emblema" / f"{icono}.dds")
        # marca de agua: luminancia del ícono teñida del color de la facción, muy tenue
        m = ajustar(img, lado_marca, 0.92)
        gris = ImageOps.grayscale(m.convert("RGB"))
        tinte = ImageOps.colorize(gris, black=_lerp(color, (0, 0, 0), 0.6), white=_lerp(color, (255, 255, 255), 0.4))
        tinte = tinte.convert("RGBA")
        tinte.putalpha(m.getchannel("A").point(lambda a: round(a * 0.085)))
        guardar(tinte, base / "marca" / f"{icono}.dds")
        hechas.append(icono)
    return [f"recursos: {len(hechas)} emblemas ({lado_emblema} px) y marcas de agua ({lado_marca} px) "
            f"en {base.relative_to(REPO)}/emblema y /marca"]


def _colores_recurso() -> dict:
    """Ícono de cada recurso principal (barra superior) -> color de su facción."""
    import yaml
    cfg = (yaml.safe_load((REPO / "spec" / "11_scenario.yaml").read_text(encoding="utf-8"))
           .get("ficha_lider") or {})
    colores = (cfg.get("faction_accents") or {}).get("colors") or {}
    return {i["icon"]: colores[i["country"]] for i in (cfg.get("resource_bar") or {}).get("items") or []
            if i.get("country") in colores}


def acentos(colores: dict, ancho_barra: int, ancho_pol: int) -> list[str]:
    """Acentos de color por facción (2026-11-03): un hilo de luz para debajo de la barra
    superior y un par de escuadras para las esquinas de Política."""
    import sys
    sys.path.insert(0, str(REPO))
    from PIL import Image, ImageDraw, ImageFilter
    from tools.gen import art
    salida = SALIDA / "acentos"
    def guardar(img, nombre):
        raw = img.tobytes()
        art.write_dds(salida / f"{nombre}.dds", img.width, img.height, [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)])
    for tag, c in colores.items():
        c = tuple(c)
        # hilo: 1 px brillante con un halo suave, que se apaga en las puntas
        w, h = ancho_barra, 7
        hilo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(hilo)
        for x in range(w):
            t = x / max(1, w - 1)
            a = min(1.0, t / 0.08, (1 - t) / 0.25)
            d.point((x, 3), c + (round(235 * a),))
        halo = hilo.filter(ImageFilter.GaussianBlur(1.6))
        halo.alpha_composite(hilo)
        guardar(halo, f"hilo_{tag}")
        # escuadras: dos esquinas en L para arriba de Política (izquierda y derecha)
        L, g = 34, 2
        for lado in ("izq", "der"):
            e = Image.new("RGBA", (L + 4, L + 4), (0, 0, 0, 0))
            d = ImageDraw.Draw(e)
            x0 = 2 if lado == "izq" else L + 1
            dx = 1 if lado == "izq" else -1
            for k in range(g):
                d.line((x0, 2 + k, x0 + dx * L, 2 + k), fill=c + (230,))
                d.line((x0 + dx * k, 2, x0 + dx * k, 2 + L), fill=c + (230,))
            d.ellipse((x0 + dx * 6 - 2, 6, x0 + dx * 6 + 2, 10), fill=c + (255,))
            halo = e.filter(ImageFilter.GaussianBlur(1.2))
            halo.alpha_composite(e)
            guardar(halo, f"escuadra_{lado}_{tag}")
    return [f"acentos: {len(colores)} facciones en {salida.relative_to(REPO)}"]


# -- la Lámina de las aventuras (2026-11-06) -----------------------------------------
# "Necesito que la aventura se note que NO es un evento más: cuadro más grande, más
# texto, más personalidad, imagen impactante en tono obra de arte." La ventana mide lo
# mismo que la Ficha (1020x740) y usa sus marcos por facción; el fondo es un vidrio
# limpio con el lugar de la pintura enmarcado en cobre, como en una galería.

LAMINA = {"ventana": (1020, 740), "pintura": (30, 96, 960, 408), "texto": (40, 516, 940, 168)}


def lamina_fondo():
    from PIL import Image, ImageDraw
    W, H = LAMINA["ventana"]
    img = _grad_v(W, H, VIDRIO_A, VIDRIO_B, 245)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    x, y, w, h = LAMINA["pintura"]
    # el marco de galería de la pintura: sombra, moldura de cobre en dos filetes
    d.rectangle((x - 10, y - 10, x + w + 10, y + h + 10), fill=(0, 0, 0, 120))
    d.rectangle((x - 7, y - 7, x + w + 6, y + h + 6), outline=CU + (255,), width=3)
    d.rectangle((x - 3, y - 3, x + w + 2, y + h + 2), outline=CU_LO + (255,), width=1)
    img.alpha_composite(capa)
    _hilo(img, 40, W - 40, 88)
    _hilo(img, 60, W - 60, y + h + 14, CU_LO, 160)
    _borde_cobre(img, 0, 1)
    _esquinas(img)
    for cx, cy in ((9, 9), (W - 10, 9), (9, H - 10), (W - 10, H - 10)):
        _remache(img, cx, cy)
    return img


def lamina_vacia():
    """La pintura de mientras: un lienzo oscuro con una veladura cálida, sin dibujo."""
    from PIL import Image, ImageFilter
    _, _, w, h = LAMINA["pintura"]
    img = _grad_v(w, h, (46, 34, 26), (14, 12, 12), 255)
    luz = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    lp = luz.load()
    for yy in range(h):
        for xx in range(w):
            v = max(0.0, 1 - math.hypot((xx - w * 0.38) / (w * 0.55), (yy - h * 0.35) / (h * 0.9)))
            if v > 0:
                lp[xx, yy] = (210, 150, 90, round(70 * v))
    img.alpha_composite(luz.filter(ImageFilter.GaussianBlur(8)))
    return img


def laminas(salida: Path | None = None) -> list[str]:
    import sys
    sys.path.insert(0, str(REPO))
    from tools.gen import art
    salida = salida or (REPO / "assets" / "ui" / "laminas")
    salida.mkdir(parents=True, exist_ok=True)

    def guardar(img, nombre):
        raw = img.convert("RGBA").tobytes()
        art.write_dds(salida / f"{nombre}.dds", img.width, img.height,
                      [tuple(raw[k:k + 4]) for k in range(0, len(raw), 4)])

    guardar(lamina_fondo(), "fondo")
    guardar(lamina_vacia(), "vacia")
    from PIL import Image
    guardar(Image.new("RGBA", (8, 8), (0, 0, 0, 0)), "sin_marco")   # países sin marco propio
    colores = _colores_estilo()
    hechas = 2
    for nombre, fn in PIEZAS.items():
        if not nombre.startswith("marco_") or nombre == "marco_base":
            continue
        img = fn({"ventana": LAMINA["ventana"]}).convert("RGBA")
        estilo = nombre[len("marco_"):]
        if estilo in colores and img.size == LAMINA["ventana"]:
            _hilo_color(img, 0, LAMINA["ventana"][0], 88, tuple(colores[estilo]), 200, 0.3)
        guardar(img, nombre)
        hechas += 1
    return [f"láminas: {hechas} piezas en {salida.relative_to(REPO)}"]


def main(argv: list[str]) -> None:
    if argv and argv[0] == "laminas":
        for line in laminas():
            print(line)
        return
    if argv and argv[0] == "acentos":
        import yaml
        cfg = (yaml.safe_load((REPO / "spec" / "11_scenario.yaml").read_text(encoding="utf-8"))
               .get("ficha_lider") or {}).get("faction_accents") or {}
        for line in acentos(cfg.get("colors") or {}, int((cfg.get("topbar") or {}).get("width", 690)),
                            int((cfg.get("politics") or {}).get("width", 540))):
            print(line)
        return
    if argv and argv[0] == "recursos":
        for line in recursos_chicos() + recursos_ficha(_colores_recurso()):
            print(line)
        return
    for line in dibujar(Path(argv[0]) if argv else SALIDA):
        print(line)
