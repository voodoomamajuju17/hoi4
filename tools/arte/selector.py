"""Arte del selector-receptor (2026-11-13, "Receptor 2100"; prototipo probado en el juego).

Se arma acá, a la medida exacta de la ventana, con las texturas de material reales que ya están en
assets/ui/materiales/ (acero ennegrecido, bronce cepillado, fieltro grafito, vidrio ahumado) y cuatro
piezas ilustradas que se encargan aparte (arte/pedidos_fijos/30_selector_receptor.txt) y se guardan en
assets/ui/selector/fuente/:

    selector_vidrio.png    pantalla del monitor (vidrio oscuro con reflejo tenue)
    selector_dial.png      dial mundial de sintonía (marca de agua del monitor y adorno de la cabecera)
    selector_medidor.png   medidor de señal analógico (cabecera, a la derecha)
    selector_rejilla.png   rejilla de parlante repetible (fondo del banco de teclas)

Si falta alguna, se usa un reemplazo dibujado acá (el selector funciona igual). Las coordenadas son
las del prototipo (gamesetup_interesting_countries_window, 1225 x 717) que se probó en el juego.
Se dibuja una vez con Pillow y queda en assets/ui/selector/ (el armado del mod solo copia los .dds):

    python3 -m tools.arte.selector
"""

from __future__ import annotations

import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SALIDA = REPO / "assets" / "ui" / "selector"
FUENTE = SALIDA / "fuente"
MATERIALES = REPO / "assets" / "ui" / "materiales"

VENTANA = (1225, 717)
ZONAS = {
    "cabecera": (24, 16, 1177, 48),
    "monitor": (24, 76, 686, 534),
    "banco": (730, 76, 471, 408),
    "filtros": (730, 490, 471, 120),
    "pie": (24, 626, 1177, 68),
}
TECLA = (230, 60)
DIAL = 100            # el dial mundial en el zócalo (revisión del receptor, 2026-11-15)
MEDIDOR = (170, 65)   # el medidor de señal, a la misma altura
PASO = (240, 68)
# dentro de la tecla (selector_gui.py): bandera en (10, 9) a 0,75 (82 x 52 -> 62 x 39), nombre desde x 76
VENTANA_BANDERA = (9, 8, 64, 41)   # el hueco justo de la bandera (62 x 39 en 10, 9)
# zonas del monitor donde va texto (coordenadas de la ventana): retrato, datos, título, ideas, historia
TITULO_X = 435

GRAFITO = (24, 26, 29)
BRONCE = (176, 128, 74)
COBRE_LUZ = (240, 181, 133)
TURQUESA = (79, 214, 200)
PIEZAS = ("selector_vidrio", "selector_dial", "selector_medidor", "selector_rejilla")
K = 2   # se dibuja al doble y se achica al final (bordes suaves)


def _dds(img, dest: Path) -> None:
    import sys
    sys.path.insert(0, str(REPO))
    from tools.gen import art
    img = img.convert("RGBA")
    raw = img.tobytes()
    dest.parent.mkdir(parents=True, exist_ok=True)
    art.write_dds(dest, img.width, img.height, [tuple(raw[k:k + 4]) for k in range(0, len(raw), 4)])


def _fuente(nombre: str):
    from PIL import Image
    p = FUENTE / f"{nombre}.png"
    return Image.open(p).convert("RGBA") if p.exists() else None


def _material(nombre: str, w: int, h: int, escala: float = 1.0):
    """La textura repetida hasta cubrir w x h."""
    from PIL import Image
    src = Image.open(MATERIALES / f"{nombre}.jpg").convert("RGBA")
    if escala != 1.0:
        src = src.resize((max(1, int(src.width * escala)), max(1, int(src.height * escala))), Image.LANCZOS)
    out = Image.new("RGBA", (w, h))
    for y in range(0, h, src.height):
        for x in range(0, w, src.width):
            out.paste(src, (x, y))
    return out


def _cubrir(img, w: int, h: int):
    """Escala y recorta al centro para cubrir w x h sin deformar."""
    from PIL import Image
    f = max(w / img.width, h / img.height)
    img = img.resize((max(w, round(img.width * f)), max(h, round(img.height * f))), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def _tono(img, factor: float, tinte=None, mezcla: float = 0.0):
    from PIL import Image, ImageEnhance
    img = ImageEnhance.Brightness(img).enhance(factor)
    if tinte:
        capa = Image.new("RGBA", img.size, tinte + (255,))
        img = Image.blend(img, capa, mezcla)
    return img


def _mascara_redonda(w: int, h: int, r: int):
    from PIL import Image, ImageDraw
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return m


def _pegar(base, img, x: int, y: int, r: int = 0) -> None:
    base.alpha_composite(img, (x, y)) if not r else base.paste(img, (x, y), _mascara_redonda(img.width, img.height, r))


def _bisel(base, caja, r: int, ancho: int, hundido: bool) -> None:
    """Luz arriba a la izquierda y sombra abajo a la derecha (o al revés si está hundido)."""
    from PIL import Image, ImageDraw, ImageFilter
    x0, y0, x1, y1 = caja
    luz = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(luz)
    claro, oscuro = (255, 236, 210, 70), (0, 0, 0, 150)
    a, b = (oscuro, claro) if hundido else (claro, oscuro)
    for k in range(ancho):
        t = 1 - k / ancho
        d.rounded_rectangle((x0 + k, y0 + k, x1 - k, y1 - k), max(1, r - k),
                            outline=None)
        d.arc((x0 + k, y0 + k, x0 + k + 2 * r, y0 + k + 2 * r), 180, 270, fill=a[:3] + (int(a[3] * t),))
        d.line((x0 + k + r, y0 + k, x1 - k - r, y0 + k), fill=a[:3] + (int(a[3] * t),))
        d.line((x0 + k, y0 + k + r, x0 + k, y1 - k - r), fill=a[:3] + (int(a[3] * t),))
        d.arc((x1 - k - 2 * r, y1 - k - 2 * r, x1 - k, y1 - k), 0, 90, fill=b[:3] + (int(b[3] * t),))
        d.line((x0 + k + r, y1 - k, x1 - k - r, y1 - k), fill=b[:3] + (int(b[3] * t),))
        d.line((x1 - k, y0 + k + r, x1 - k, y1 - k - r), fill=b[:3] + (int(b[3] * t),))
    base.alpha_composite(luz.filter(ImageFilter.GaussianBlur(0.6 * K)))


def _sombra_interior(base, caja, r: int, prof: int) -> None:
    from PIL import Image, ImageDraw, ImageFilter, ImageChops
    x0, y0, x1, y1 = caja
    w, h = x1 - x0, y1 - y0
    m = Image.new("L", (w + 4 * prof, h + 4 * prof), 255)
    ImageDraw.Draw(m).rounded_rectangle((2 * prof, 2 * prof + prof // 2, 2 * prof + w, 2 * prof + h + prof // 2), r, fill=0)
    m = m.filter(ImageFilter.GaussianBlur(prof))
    m = m.crop((2 * prof, 2 * prof, 2 * prof + w, 2 * prof + h))
    m = ImageChops.multiply(m, _mascara_redonda(w, h, r))
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    capa.putalpha(m.point(lambda v: int(v * 0.85)))
    base.alpha_composite(capa, (x0, y0))


def _tornillo(base, cx: int, cy: int, r: int) -> None:
    from PIL import ImageDraw
    d = ImageDraw.Draw(base)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(92, 70, 44, 255), outline=(30, 22, 14, 255), width=max(1, K))
    d.ellipse((cx - r + K, cy - r + K, cx + r - 2 * K, cy + r - 2 * K), fill=BRONCE + (255,))
    d.line((cx - r + 2 * K, cy, cx + r - 2 * K, cy), fill=(50, 36, 22, 255), width=max(1, K))


# -- piezas de reemplazo (si todavía no llegó la ilustrada) ----------------------------------

def _dial_dibujado(lado: int):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, r = lado / 2, lado / 2 - 2
    d.ellipse((c - r, c - r, c + r, c + r), outline=BRONCE + (255,), width=max(2, lado // 40))
    d.ellipse((c - r * 0.78, c - r * 0.78, c + r * 0.78, c + r * 0.78), outline=BRONCE + (160,), width=max(1, lado // 120))
    for k in range(72):
        a = math.radians(k * 5)
        largo = 0.12 if k % 6 == 0 else 0.06
        d.line((c + math.cos(a) * r * (0.94 - largo), c + math.sin(a) * r * (0.94 - largo),
                c + math.cos(a) * r * 0.94, c + math.sin(a) * r * 0.94), fill=COBRE_LUZ + (220,), width=max(1, lado // 200))
    for k in range(1, 4):                       # meridianos y paralelos del globo
        rr = r * 0.7 * k / 3
        d.ellipse((c - rr, c - r * 0.7, c + rr, c + r * 0.7), outline=TURQUESA + (90,), width=max(1, lado // 220))
        y = r * 0.7 * (k / 3 - 0.5) * 1.4
        d.line((c - math.sqrt(max(0, (r * 0.7) ** 2 - y * y)), c + y, c + math.sqrt(max(0, (r * 0.7) ** 2 - y * y)), c + y),
               fill=TURQUESA + (90,), width=max(1, lado // 220))
    a = math.radians(-60)
    d.line((c, c, c + math.cos(a) * r * 0.9, c + math.sin(a) * r * 0.9), fill=TURQUESA + (255,), width=max(2, lado // 90))
    d.ellipse((c - r * 0.06, c - r * 0.06, c + r * 0.06, c + r * 0.06), fill=BRONCE + (255,))
    return img


def _medidor_dibujado(w: int, h: int):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), h // 6, fill=(214, 196, 158, 255), outline=BRONCE + (255,), width=max(2, h // 18))
    cx, cy, r = w / 2, h * 1.35, h * 1.05
    for k in range(21):
        a = math.radians(-128 + k * 3.8)
        largo = 0.16 if k % 5 == 0 else 0.08
        col = (150, 40, 30, 255) if k > 15 else (40, 34, 28, 255)
        d.line((cx + math.cos(a) * r * (1 - largo), cy + math.sin(a) * r * (1 - largo), cx + math.cos(a) * r, cy + math.sin(a) * r),
               fill=col, width=max(1, h // 40))
    a = math.radians(-104)
    d.line((cx, cy, cx + math.cos(a) * r * 1.02, cy + math.sin(a) * r * 1.02), fill=(20, 18, 16, 255), width=max(1, h // 30))
    return img


def _rejilla_dibujada(lado: int):
    from PIL import Image, ImageDraw
    img = _material("mat_acero_ennegrecido", lado, lado, 0.5)
    d = ImageDraw.Draw(img)
    paso = 7 * K
    for y in range(paso // 2, lado, paso):
        for x in range(paso // 2 + (paso // 2 if (y // paso) % 2 else 0), lado, paso):
            d.ellipse((x - 1.6 * K, y - 1.6 * K, x + 1.6 * K, y + 1.6 * K), fill=(6, 7, 8, 255))
    return img


# -- la carcasa ------------------------------------------------------------------------------

def fondo():
    from PIL import Image, ImageDraw, ImageFilter
    W, H = VENTANA[0] * K, VENTANA[1] * K
    s = lambda caja: tuple(v * K for v in caja)
    img = _tono(_material("mat_acero_ennegrecido", W, H, 0.75), 0.9)
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))               # se oscurece hacia abajo
    ImageDraw.Draw(sombra).rectangle((0, 0, W, H), fill=(0, 0, 0, 0))
    for y in range(H):
        a = int(70 * (y / H) ** 1.5)
        ImageDraw.Draw(sombra).line((0, y, W, y), fill=(0, 0, 0, a))
    img.alpha_composite(sombra)

    # banco de teclas: acero oscuro y tranquilo, hundido (2026-11-15, revisión del receptor: la rejilla
    # queda para el zócalo de abajo, donde van el dial y el medidor)
    x, y, w, h = s(ZONAS["banco"])
    _pegar(img, _tono(_material("mat_acero_ennegrecido", w, h, 0.5), 0.6), x, y, 8 * K)
    _sombra_interior(img, (x, y, x + w, y + h), 8 * K, 6 * K)
    _bisel(img, (x - 2 * K, y - 2 * K, x + w + 2 * K, y + h + 2 * K), 10 * K, 2 * K, hundido=True)

    # el zócalo de abajo a la derecha: la rejilla del parlante, con el dial y el medidor a la misma altura
    x, y, w, h = s(ZONAS["filtros"])
    rej = _fuente("selector_rejilla")
    rej = _material_desde(rej, w, h) if rej is not None else _rejilla_dibujada(max(w, h))
    _pegar(img, _tono(rej.crop((0, 0, w, h)), 0.75), x, y, 8 * K)
    _sombra_interior(img, (x, y, x + w, y + h), 8 * K, 6 * K)
    _bisel(img, (x - 2 * K, y - 2 * K, x + w + 2 * K, y + h + 2 * K), 10 * K, 2 * K, hundido=True)
    dial = (_fuente("selector_dial") or _dial_dibujado(512)).resize((DIAL * K,) * 2, Image.LANCZOS)
    med = _fuente("selector_medidor")
    mw, mh = MEDIDOR
    med = _cubrir(med, mw * K, mh * K) if med is not None else _medidor_dibujado(mw * K, mh * K)
    sep = 30 * K
    x0 = x + (w - dial.width - sep - med.width) // 2
    for pieza, px in ((dial, x0), (med, x0 + dial.width + sep)):
        py = y + (h - pieza.height) // 2
        # una sombra suave debajo, para que parezcan montados sobre la rejilla
        sombra_p = Image.new("RGBA", pieza.size, (0, 0, 0, 0))
        sombra_p.putalpha(pieza.getchannel("A").point(lambda v: int(v * 0.6)))
        img.alpha_composite(sombra_p.filter(ImageFilter.GaussianBlur(4 * K)), (px + 2 * K, py + 4 * K))
        img.alpha_composite(pieza, (px, py))

    # cabecera y pie: placas hundidas de fieltro grafito (texto claro encima)
    for nombre, r in (("cabecera", 6), ("pie", 6)):
        x, y, w, h = s(ZONAS[nombre])
        _pegar(img, _tono(_material("mat_fieltro_grafito", w, h, 0.5), 0.55), x, y, r * K)
        _sombra_interior(img, (x, y, x + w, y + h), r * K, 4 * K)
        _bisel(img, (x - 2 * K, y - 2 * K, x + w + 2 * K, y + h + 2 * K), (r + 2) * K, 2 * K, hundido=True)

    # el monitor: marco de bronce, vidrio, dial de marca de agua y reflejo
    x, y, w, h = s(ZONAS["monitor"])
    m = 10 * K
    marco = _tono(_material("mat_bronce_cepillado", w + 2 * m, h + 2 * m, 0.6), 0.8)
    _pegar(img, marco, x - m, y - m, 16 * K)
    _bisel(img, (x - m, y - m, x + w + m, y + h + m), 16 * K, 3 * K, hundido=False)
    vid = _fuente("selector_vidrio")
    vid = _cubrir(vid, w, h) if vid is not None else _tono(_cubrir(Image.open(MATERIALES / "mat_vidrio_ahumado.jpg").convert("RGBA"), w, h), 0.55, (8, 30, 34), 0.35)
    # el texto del juego va encima: el vidrio queda oscuro y parejo (se aplana el contraste)
    from PIL import ImageEnhance
    vid = ImageEnhance.Contrast(_tono(vid, 0.75)).enhance(0.7)
    # sin el dial de marca de agua: el vidrio queda libre para leer (revisión del receptor)
    lineas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lineas)
    for yy in range(0, h, 3 * K):
        dl.line((0, yy, w, yy), fill=(0, 0, 0, 28))
    vid.alpha_composite(lineas)
    reflejo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(reflejo).polygon([(0, 0), (int(w * 0.42), 0), (0, int(h * 0.55))], fill=(220, 255, 250, 14))
    vid.alpha_composite(reflejo.filter(ImageFilter.GaussianBlur(30 * K)))
    _pegar(img, vid, x, y, 10 * K)
    _sombra_interior(img, (x, y, x + w, y + h), 10 * K, 10 * K)
    ImageDraw.Draw(img).rounded_rectangle((x, y, x + w, y + h), 10 * K, outline=TURQUESA + (70,), width=K)
    for cx, cy in ((x - m // 2, y - m // 2), (x + w + m // 2, y - m // 2), (x - m // 2, y + h + m // 2),
                   (x + w + m // 2, y + h + m // 2)):
        _tornillo(img, cx, cy, 4 * K)

    for nombre in ("banco", "filtros"):
        x, y, w, h = s(ZONAS[nombre])
        for cx, cy in ((x - 9 * K, y - 9 * K), (x + w + 9 * K, y - 9 * K)):
            if 0 < cx < W and 0 < cy < H:
                _tornillo(img, cx, cy, 3 * K)

    # borde exterior
    ImageDraw.Draw(img).rounded_rectangle((K, K, W - K, H - K), 12 * K, outline=BRONCE + (255,), width=2 * K)
    _bisel(img, (0, 0, W - 1, H - 1), 12 * K, 3 * K, hundido=False)
    img = img.resize(VENTANA, Image.LANCZOS)
    img.putalpha(_mascara_redonda(*VENTANA, 12).point(lambda v: min(v, 250)))
    return img


def _material_desde(img, w: int, h: int):
    """Una pieza repetible (la rejilla) repetida hasta cubrir w x h."""
    from PIL import Image
    t = img.resize((256 * K, 256 * K), Image.LANCZOS)
    out = Image.new("RGBA", (w, h))
    for y in range(0, h, t.height):
        for x in range(0, w, t.width):
            out.paste(t, (x, y))
    return out


def tecla():
    """Dos cuadros uno al lado del otro: normal y elegida (como GFX_country_selection_entry del juego)."""
    from PIL import Image, ImageDraw, ImageFilter
    w, h = TECLA[0] * K, TECLA[1] * K
    out = Image.new("RGBA", (w * 2, h), (0, 0, 0, 0))
    for cuadro in (0, 1):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        # 2026-11-15 (revisión del receptor): la elegida está hundida (sombra arriba, filo de luz
        # abajo) y solo la delata su piloto turquesa; sin halo ni borde de color
        cuerpo = _tono(_material("mat_acero_ennegrecido", w, h, 0.4), 0.85 if cuadro else 1.15)
        _pegar(img, cuerpo, 0, 0, 7 * K)
        _bisel(img, (0, 0, w - 1, h - 1), 7 * K, 3 * K, hundido=bool(cuadro))
        if cuadro:
            _sombra_interior(img, (0, 0, w, h), 7 * K, 5 * K)
        # la ventanita de la bandera: un hueco transparente (2026-11-14, captura: las banderas no se
        # veían; la bandera va debajo de la tecla en la plantilla del juego), con sombra y borde de bronce
        bx, by, bw, bh = (v * K for v in VENTANA_BANDERA)
        hueco = Image.new("L", (w, h), 255)
        ImageDraw.Draw(hueco).rounded_rectangle((bx, by, bx + bw, by + bh), 2 * K, fill=0)
        from PIL import ImageChops
        img.putalpha(ImageChops.multiply(img.getchannel("A"), hueco))
        _sombra_interior(img, (bx, by, bx + bw, by + bh), 2 * K, 2 * K)
        ImageDraw.Draw(img).rounded_rectangle((bx - K, by - K, bx + bw + K, by + bh + K), 3 * K, outline=BRONCE + (230,), width=K)
        # la placa del nombre
        px0, py0, px1, py1 = 76 * K, 7 * K, w - 6 * K, h - 7 * K
        placa = _tono(_material("mat_fieltro_grafito", px1 - px0, py1 - py0, 0.35), 0.7)
        if cuadro:
            placa = _tono(placa, 1.0, (18, 70, 68), 0.2)
        _pegar(img, placa, px0, py0, 4 * K)
        _sombra_interior(img, (px0, py0, px1, py1), 4 * K, 2 * K)
        # el piloto: apagado o encendido
        cx, cy, r = w - 12 * K, 13 * K, 3 * K
        d = ImageDraw.Draw(img)
        if cuadro:
            brillo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(brillo).ellipse((cx - 3 * r, cy - 3 * r, cx + 3 * r, cy + 3 * r), fill=TURQUESA + (110,))
            img.alpha_composite(brillo.filter(ImageFilter.GaussianBlur(3 * K)))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(TURQUESA if cuadro else (30, 52, 50)) + (255,),
                  outline=(20, 16, 12, 255), width=K)
        ImageDraw.Draw(img).rounded_rectangle((K, K, w - 2 * K, h - 2 * K), 7 * K, outline=BRONCE + (255,), width=2 * K)
        out.alpha_composite(img, (cuadro * w, 0))
    return out.resize((TECLA[0] * 2, TECLA[1]), Image.LANCZOS)


def dibujar() -> list[str]:
    _dds(fondo(), SALIDA / "fondo.dds")
    _dds(tecla(), SALIDA / "tecla.dds")
    llegadas = [p for p in PIEZAS if (FUENTE / f"{p}.png").exists()]
    return [f"selector: carcasa {VENTANA[0]}x{VENTANA[1]} y tecla {TECLA[0]}x{TECLA[1]} (2 cuadros) en "
            f"{SALIDA.relative_to(REPO)}; piezas ilustradas: {', '.join(llegadas) or 'ninguna todavía (reemplazos dibujados)'}"]


def vista_previa(dest: Path) -> None:
    """La carcasa con teclas y rectángulos donde el juego pone sus datos (para mirar sin el juego)."""
    from PIL import Image, ImageDraw
    f, t = fondo(), tecla()
    normal, elegida = t.crop((0, 0, TECLA[0], TECLA[1])), t.crop((TECLA[0], 0, 2 * TECLA[0], TECLA[1]))
    for k in range(11):
        col, fila = k % 2, k // 2
        f.alpha_composite(elegida if k == 0 else normal, (730 + col * PASO[0], 76 + fila * PASO[1]))
    d = ImageDraw.Draw(f)
    # retrato, país, datos en pares, banda de espíritus (grupo, ideas y foco) e historia
    for caja in ((44, 96, 156, 210), (218, 96, 472, 30), (218, 136, 472, 135), (44, 322, 66, 68),
                 (120, 322, 430, 66), (554, 308, 105, 100), (44, 432, 646, 22), (44, 462, 646, 128)):
        x, y, w, h = caja
        d.rectangle((x, y, x + w, y + h), outline=(255, 255, 255, 60))
    f.save(dest)


if __name__ == "__main__":
    for linea in dibujar():
        print(linea)
