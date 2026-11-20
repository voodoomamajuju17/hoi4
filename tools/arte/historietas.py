"""La Historieta (spec/46_historietas.yaml, 2026-11-18): las páginas de 8 viñetas de cada nación.

  componer(tag)   arma assets/historietas/paginas/<TAG>.dds: el fondo y las calles con el estilo de la
                  nación, cada viñeta (su dibujo si ya llegó: assets/historietas/<TAG>_<n>.dds; si no,
                  una trama de puntos en los colores de la nación), su forma, su borde y el recuadro
                  vacío del texto (el juego escribe encima). Ver tools/gen/historietas_geo.py.
  items()         los pedidos de arte (una imagen por viñeta, del tamaño y la forma de su lugar).
  vista(tag, png) la página con los textos en castellano encima, para revisarla.

Uso:  python3 -m tools.arte.historietas            (arma las 13 páginas)
      python3 -m tools.arte.historietas EFE x.png  (vista previa con textos)
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.gen import historietas_geo as geo  # noqa: E402

DIR = REPO / "assets" / "historietas"
PAGINAS = DIR / "paginas"

# fondo (calles), borde (tinta, color, ancho), recuadro, banda del título, trama (dos colores)
ESTILOS = {
    "organico": dict(fondo=(44, 31, 19), borde=((26, 16, 8), (196, 164, 82), 5), caja=(241, 229, 194),
                     banda=(22, 60, 32), trama=((38, 88, 48), (128, 156, 74))),
    "placa": dict(fondo=(16, 56, 40), borde=((10, 10, 10), (206, 34, 34), 4), caja=(247, 245, 238),
                  banda=(150, 18, 18), trama=((190, 36, 36), (238, 228, 214))),
    "cristal": dict(fondo=(12, 22, 46), borde=((6, 10, 22), (194, 204, 218), 3), caja=(233, 239, 247),
                    banda=(20, 34, 66), trama=((32, 54, 96), (150, 170, 198))),
    "ola": dict(fondo=(10, 56, 66), borde=((8, 14, 16), (190, 150, 74), 4), caja=(247, 239, 214),
                banda=(8, 44, 54), trama=((22, 112, 122), (232, 220, 182))),
    "sol": dict(fondo=(148, 136, 116), borde=((40, 28, 10), (216, 172, 58), 4), caja=(238, 247, 241),
                banda=(96, 58, 20), trama=((212, 150, 56), (58, 150, 160))),
    "rollo": dict(fondo=(18, 30, 26), borde=((8, 12, 10), (96, 166, 124), 3), caja=(243, 237, 219),
                  banda=(26, 44, 38), trama=((70, 122, 100), (212, 222, 202))),
    "kente": dict(fondo=(30, 24, 14), borde=((0, 0, 0), (232, 182, 34), 5), caja=(252, 239, 206),
                  banda=(110, 30, 20), trama=((182, 60, 30), (242, 192, 62))),
    "marmol": dict(fondo=(226, 222, 214), borde=((30, 8, 10), (142, 22, 32), 4), caja=(251, 249, 242),
                   banda=(120, 16, 26), trama=((150, 40, 40), (232, 202, 142))),
    "remaches": dict(fondo=(86, 60, 42), borde=((14, 14, 10), (60, 64, 44), 5), caja=(233, 227, 207),
                     banda=(48, 50, 36), trama=((90, 96, 70), (182, 162, 130))),
    "ojiva": dict(fondo=(200, 110, 28), borde=((40, 6, 12), (152, 22, 42), 4), caja=(251, 241, 216),
                  banda=(120, 20, 36), trama=((200, 80, 40), (242, 202, 122))),
    "arena": dict(fondo=(206, 170, 112), borde=((14, 10, 6), (204, 162, 72), 3), caja=(247, 233, 201),
                  banda=(60, 40, 20), trama=((210, 160, 90), (250, 222, 162))),
    "selva": dict(fondo=(56, 42, 24), borde=((10, 24, 12), (40, 96, 44), 5), caja=(237, 233, 201),
                  banda=(18, 46, 22), trama=((40, 92, 52), (202, 122, 52))),
    "astillero": dict(fondo=(16, 24, 40), borde=((4, 6, 12), (232, 184, 30), 4), caja=(244, 242, 236),
                      banda=(120, 18, 28), trama=((30, 50, 86), (226, 180, 40))),
    "telar": dict(fondo=(120, 52, 40), borde=((20, 14, 10), (190, 176, 150), 4), caja=(240, 234, 220),
                  banda=(46, 52, 44), trama=((88, 96, 84), (176, 70, 56))),
    "chatarra": dict(fondo=(20, 19, 17), borde=((0, 0, 0), (156, 74, 30), 4), caja=(250, 232, 128),
                     banda=(30, 28, 24), trama=((122, 62, 30), (232, 202, 62))),
}


def _cfg() -> dict:
    from tools.gen import specload
    return specload.load(REPO / "spec").raw["historietas"]


def _cfg_crudo() -> dict:
    """Sin cargar todo el spec (para los pedidos y el armado)."""
    import yaml
    return yaml.safe_load((REPO / "spec" / "46_historietas.yaml").read_text(encoding="utf-8"))["historietas"]


def arte_de(tag: str, n: int) -> Path:
    return DIR / f"{tag}_{n}.dds"


# ---------------------------------------------------------------------------- formas

def _poligono(rect, forma, esquinas, primero, ultimo, s):
    x, y, w, h = rect
    if forma == "arco":
        a = geo.arco_alto(w, h, forma)
        pts = [(x, y + h), (x, y + a)]
        for i in range(0, 41):
            t = math.pi - math.pi * i / 40
            pts.append((x + w / 2 + (w / 2) * math.cos(t), y + a - a * math.sin(t)))
        return pts + [(x + w, y + h)]
    if forma == "ojiva":
        a = geo.arco_alto(w, h, forma)
        pts = [(x, y + h), (x, y + a)]
        for i in range(1, 21):          # curva izquierda hasta la punta
            t = i / 20
            pts.append((x + (w / 2) * (1 - (1 - t) ** 2), y + a - a * (t ** 1.6)))
        for i in range(19, -1, -1):     # y su espejo
            t = i / 20
            pts.append((x + w - (w / 2) * (1 - (1 - t) ** 2), y + a - a * (t ** 1.6)))
        return pts + [(x + w, y + h)]
    if esquinas == "chaflan":
        c = 16
        return [(x + c, y), (x + w - c, y), (x + w, y + c), (x + w, y + h - c), (x + w - c, y + h),
                (x + c, y + h), (x, y + h - c), (x, y + c)]
    if esquinas == "inclinado":
        return [(x + (0 if primero else s), y), (x + w, y), (x + w - (0 if ultimo else s), y + h), (x, y + h)]
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def _mascara(size, rect, forma, esquinas, primero, ultimo, s):
    from PIL import Image, ImageDraw
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    x, y, w, h = rect
    if forma == "circulo":
        r = min(w, h) / 2
        cx, cy = x + w / 2, y + h / 2
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    elif esquinas == "redondo" and forma == "rect":
        d.rounded_rectangle((x, y, x + w - 1, y + h - 1), radius=20, fill=255)
    else:
        d.polygon(_poligono(rect, forma, esquinas, primero, ultimo, s), fill=255)
    return m


# ---------------------------------------------------------------------------- texturas

def _ruido(img, rnd, fuerza=18, paso=3):
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    w, h = img.size
    for _ in range(w * h // (paso * paso * 6)):
        x, y = rnd.randrange(w), rnd.randrange(h)
        r, g, b = img.getpixel((x, y))[:3]
        k = rnd.randint(-fuerza, fuerza)
        d.rectangle((x, y, x + paso, y + paso), fill=(max(0, min(255, r + k)), max(0, min(255, g + k)),
                                                       max(0, min(255, b + k))))


def _mezcla(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _fondo(estilo: str, rnd):
    from PIL import Image, ImageDraw
    e = ESTILOS[estilo]
    img = Image.new("RGB", (geo.W, geo.H), e["fondo"])
    d = ImageDraw.Draw(img)
    W, H = geo.W, geo.H
    if estilo == "kente":
        cols = [(232, 182, 34), (20, 118, 60), (178, 40, 30), (14, 12, 10)]
        for by in range(0, H, 24):
            for bx in range(0, W, 24):
                c = cols[(bx // 24 + by // 24 * 2) % 4]
                if (bx // 24 + by // 24) % 2:
                    for k in range(0, 24, 6):
                        d.rectangle((bx, by + k, bx + 23, by + k + 2), fill=c)
                else:
                    for k in range(0, 24, 6):
                        d.rectangle((bx + k, by, bx + k + 2, by + 23), fill=c)
    elif estilo == "marmol":
        _ruido(img, rnd, 8, 4)
        for _ in range(40):
            x, y = rnd.randrange(W), rnd.randrange(H)
            pts = [(x, y)]
            for _k in range(12):
                x += rnd.randint(-30, 30)
                y += rnd.randint(-8, 30)
                pts.append((x, y))
            d.line(pts, fill=(180, 176, 168), width=1)
    elif estilo == "sol":
        _ruido(img, rnd, 10, 4)
        y = 0
        while y < H:      # piedra inca: hiladas de bloques
            hh = rnd.randint(26, 40)
            x = -rnd.randint(0, 40)
            while x < W:
                ww = rnd.randint(40, 90)
                d.rounded_rectangle((x + 1, y + 1, x + ww - 2, y + hh - 2), radius=7, outline=(96, 86, 70), width=2)
                x += ww
            y += hh
    elif estilo == "placa":
        for _ in range(170):
            x, y = rnd.randrange(W), rnd.randrange(H)
            pts = [(x, y)]
            for _k in range(4):
                if rnd.random() < 0.5:
                    x += rnd.choice((-1, 1)) * rnd.randint(20, 90)
                else:
                    y += rnd.choice((-1, 1)) * rnd.randint(20, 90)
                pts.append((x, y))
            d.line(pts, fill=(176, 110, 50), width=2)
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(210, 160, 90))
    elif estilo == "cristal":
        for x in range(0, W, 7):
            d.line((x, 0, x, H), fill=(20, 32, 60))
    elif estilo in ("ola", "rollo"):
        c = (20, 84, 94) if estilo == "ola" else (30, 52, 44)
        for y0 in range(0, H + 20, 16):
            pts = [(x, y0 + 5 * math.sin(x / 22 + y0)) for x in range(0, W + 10, 6)]
            d.line(pts, fill=c, width=2)
    elif estilo == "arena":
        for y in range(H):
            d.line((0, y, W, y), fill=_mezcla((222, 188, 128), (178, 136, 80), y / H))
        for y0 in range(0, H, 22):
            pts = [(x, y0 + 9 * math.sin(x / 60 + y0 / 7)) for x in range(0, W + 10, 8)]
            d.line(pts, fill=(194, 152, 96), width=2)
    elif estilo in ("selva", "organico"):
        _ruido(img, rnd, 14, 3)
        for _ in range(60 if estilo == "selva" else 34):
            x, y = rnd.randrange(W), rnd.randrange(H)
            pts = []
            for k in range(30):
                pts.append((x + k * 6, y + 14 * math.sin(k / 3 + x)))
            d.line(pts, fill=(36, 84, 40) if estilo == "selva" else (40, 70, 36), width=3)
            for px, py in pts[::5]:
                d.ellipse((px - 5, py - 3, px + 5, py + 3), fill=(52, 112, 52))
    elif estilo == "remaches":
        _ruido(img, rnd, 22, 3)
        for _ in range(140):
            x, y = rnd.randrange(W), rnd.randrange(H)
            d.line((x, y, x + rnd.randint(-40, 40), y + rnd.randint(-6, 6)), fill=(60, 40, 28), width=1)
    elif estilo == "ojiva":
        for y in range(10, H, 26):
            for x in range(10 + (y // 26 % 2) * 13, W, 26):
                d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(232, 160, 60))
    elif estilo == "astillero":   # vigas de grúa en celosía
        for x0 in range(-H, W, 46):
            d.line((x0, H, x0 + H, 0), fill=(40, 52, 76), width=3)
            d.line((x0, 0, x0 + H, H), fill=(28, 38, 60), width=2)
    elif estilo == "telar":       # ladrillo rojo
        for y in range(0, H, 14):
            off = 0 if (y // 14) % 2 else 22
            d.line((0, y, W, y), fill=(178, 160, 140), width=2)
            for x in range(-off, W, 44):
                d.line((x, y, x, y + 14), fill=(178, 160, 140), width=2)
        _ruido(img, rnd, 10, 4)
    elif estilo == "chatarra":
        _ruido(img, rnd, 12, 4)
        for _ in range(26):
            x, y, r = rnd.randrange(W), rnd.randrange(H), rnd.randint(20, 70)
            d.ellipse((x - r, y - r // 2, x + r, y + r // 2), fill=(52, 30, 18))
    return img


def _trama(size, estilo, rnd):
    """Lo que va en una viñeta sin dibujo todavía: degradé y trama de puntos de historieta."""
    from PIL import Image, ImageDraw
    a, b = ESTILOS[estilo]["trama"]
    w, h = size
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    ang = rnd.random() * math.pi
    ux, uy = math.cos(ang), math.sin(ang)
    largo = abs(w * ux) + abs(h * uy) or 1
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            t = ((x * ux + y * uy) - min(0, w * ux) - min(0, h * uy)) / largo
            d.rectangle((x, y, x + 3, y + 3), fill=_mezcla(a, b, max(0.0, min(1.0, t))))
    oscuro = _mezcla(a, (0, 0, 0), 0.45)
    paso = 10
    for y in range(0, h + paso, paso):
        for x in range((y // paso % 2) * paso // 2, w + paso, paso):
            t = ((x * ux + y * uy) - min(0, w * ux) - min(0, h * uy)) / largo
            r = 1 + 3.2 * (1 - max(0.0, min(1.0, t)))
            d.ellipse((x - r, y - r, x + r, y + r), fill=oscuro)
    return img


def _cubrir(img, w, h):
    from PIL import Image
    k = max(w / img.width, h / img.height)
    img = img.convert("RGB").resize((max(w, round(img.width * k)), max(h, round(img.height * k))), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


# ---------------------------------------------------------------------------- la página

def _filas_de(cfg):
    """Para cada viñeta: (primera de su fila, última de su fila)."""
    out = []
    for _alto, anchos in cfg["filas"]:
        for j in range(len(anchos)):
            out.append((j == 0, j == len(anchos) - 1))
    return out


def pagina_png(tag: str, cfg: dict):
    from PIL import Image, ImageDraw
    estilo = cfg["estilo"]
    e = ESTILOS[estilo]
    rnd = random.Random(f"historieta-{tag}")
    img = _fondo(estilo, rnd)
    d = ImageDraw.Draw(img)
    W, H = geo.W, geo.H
    tinta, color, ancho = e["borde"]
    # bandas del título y del pie
    for y0, y1 in ((0, geo.AREA[1] - 8), (H - 60, H)):
        d.rectangle((0, y0, W, y1), fill=e["banda"])
        d.line((0, y1 if y0 == 0 else y0, W, y1 if y0 == 0 else y0), fill=color, width=3)
    if estilo == "chatarra":
        for y0, y1 in ((0, 8), (H - 8, H)):
            for x in range(-20, W, 28):
                d.polygon([(x, y1), (x + 14, y0), (x + 28, y0), (x + 14, y1)], fill=(232, 196, 40))
    pag = geo.pagina(cfg)
    s = geo.INCLINE.get(estilo, 0)
    esquinas = geo.ESQUINAS[estilo]
    filas = _filas_de(cfg)
    for n, (rect, forma, caja, area, (prim, ult)) in enumerate(
            zip(pag["rects"], pag["formas"], pag["recuadros"], pag["artes"], filas), 1):
        x, y, w, h = rect
        ax, ay, aw, ah = area
        arte = arte_de(tag, n)
        if forma == "circulo":
            # el círculo entra en el área del dibujo; la franja del texto va debajo, fuera del círculo
            r = min(aw, ah) / 2
            ccx, ccy = ax + aw / 2, ay + ah / 2
            cuadro = (int(ccx - r), int(ccy - r), int(2 * r), int(2 * r))
        else:
            cuadro = area
        if arte.exists():
            contenido = _cubrir(Image.open(arte), cuadro[2], cuadro[3])
        else:
            contenido = _trama((cuadro[2], cuadro[3]), estilo, rnd)
        if forma == "circulo":
            m = _mascara((W, H), cuadro, forma, esquinas, prim, ult, s)
        else:
            m = _mascara((W, H), rect, forma, esquinas, prim, ult, s)
        capa = Image.new("RGB", (W, H), e["caja"])     # el papel de la franja del texto
        capa.paste(contenido, (cuadro[0], cuadro[1]))
        if forma != "circulo":
            ImageDraw.Draw(capa).line((x, ay + ah + 2, x + w, ay + ah + 2), fill=tinta, width=3)
        if estilo == "sol" and forma == "circulo":   # rayos del sol alrededor de la viñeta redonda
            cx, cy, r = cuadro[0] + cuadro[2] / 2, cuadro[1] + cuadro[3] / 2, cuadro[2] / 2
            for k in range(24):
                t = 2 * math.pi * k / 24
                t2 = t + math.pi / 24
                d.polygon([(cx + r * math.cos(t), cy + r * math.sin(t)),
                           (cx + (r + 26) * math.cos(t + math.pi / 48), cy + (r + 26) * math.sin(t + math.pi / 48)),
                           (cx + r * math.cos(t2), cy + r * math.sin(t2))], fill=(222, 178, 62))
        img.paste(capa, (0, 0), m)
        # borde: tinta gruesa y una línea de color adentro
        if forma == "circulo":
            r = cuadro[2] / 2
            cx, cy = cuadro[0] + r, cuadro[1] + r
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=tinta, width=ancho)
            d.ellipse((cx - r + ancho, cy - r + ancho, cx + r - ancho, cy + r - ancho), outline=color, width=2)
        elif esquinas == "redondo" and forma == "rect":
            d.rounded_rectangle((x, y, x + w - 1, y + h - 1), radius=20, outline=tinta, width=ancho)
            d.rounded_rectangle((x + ancho, y + ancho, x + w - 1 - ancho, y + h - 1 - ancho), radius=16,
                                outline=color, width=2)
        else:
            pts = _poligono(rect, forma, esquinas, prim, ult, s)
            d.line(pts + [pts[0]], fill=tinta, width=ancho, joint="curve")
            d.line(pts + [pts[0]], fill=color, width=2, joint="curve")
        if estilo == "remaches":
            for px in range(x + 14, x + w - 8, 30):
                for py in (y + 8, y + h - 9):
                    d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=(150, 140, 120), outline=(20, 20, 16))
        if estilo == "rollo" and h > w:   # rollos colgantes: varas de madera arriba y abajo
            for py in (y - 6, y + h - 3):
                d.rounded_rectangle((x - 5, py, x + w + 4, py + 9), radius=4, fill=(122, 74, 38), outline=(40, 22, 10))
                for px in (x - 9, x + w + 1):
                    d.ellipse((px, py - 1, px + 10, py + 10), fill=(212, 170, 70), outline=(60, 40, 10))
        # en la redonda, el texto va en un recuadro debajo del círculo (en las demás, la franja ya es papel)
        if forma == "circulo":
            cx, cy, cw, ch = caja
            d.rectangle((cx + 4, cy + 4, cx + cw + 3, cy + ch + 3), fill=(0, 0, 0))
            d.rectangle((cx, cy, cx + cw - 1, cy + ch - 1), fill=e["caja"], outline=tinta, width=2)
    # columnas de mármol entre las viñetas con arco
    if estilo == "marmol":
        rects = pag["rects"]
        for a, b in zip(rects, rects[1:]):
            if a[1] == b[1] and pag["formas"][rects.index(a)] == "arco":
                gx = a[0] + a[2] + 1
                d.rectangle((gx, a[1] + 30, gx + geo.GUTTER - 3, a[1] + a[3]), fill=(244, 240, 232), outline=(150, 140, 130))
                d.rectangle((gx - 3, a[1] + 24, gx + geo.GUTTER, a[1] + 32), fill=(210, 170, 70))
    d.rectangle((0, 0, W - 1, H - 1), outline=color, width=3)
    d.rectangle((3, 3, W - 4, H - 4), outline=tinta, width=2)
    return img


def componer(tag: str, cfg: dict | None = None) -> Path:
    cfg = cfg or _cfg_crudo()[tag]
    PAGINAS.mkdir(parents=True, exist_ok=True)
    dest = PAGINAS / f"{tag}.dds"
    pagina_png(tag, cfg).save(dest, "DDS", pixel_format="DXT1")
    return dest


def vista(tag: str, png: Path) -> None:
    """La página con los textos en castellano encima (aproximados), para revisarla."""
    from PIL import ImageDraw, ImageFont
    cfg = _cfg_crudo()[tag]
    img = pagina_png(tag, cfg)
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("DejaVuSans-Bold.ttf", 13)
        ft = ImageFont.truetype("DejaVuSerif-Bold.ttf", 28)
    except OSError:
        f = ft = ImageFont.load_default()
    pag = geo.pagina(cfg)
    d.text((geo.W // 2, 32), f"({tag}) en 2100", fill=(255, 255, 255), font=ft, anchor="mm")
    for v, (cx, cy, cw, ch) in zip(cfg["vinetas"], pag["recuadros"]):
        words, line, y = v["texto"]["spanish"].split(), "", cy + 6
        for wd in words:
            prueba = (line + " " + wd).strip()
            if d.textlength(prueba, font=f) > cw - 16:
                d.text((cx + 8, y), line, fill=(0, 0, 0), font=f)
                line, y = wd, y + geo.LINEA_PX
            else:
                line = prueba
        d.text((cx + 8, y), line, fill=(0, 0, 0), font=f)
    lx, ly, _lw, _lh = geo.LEMA_TEXTO
    d.text((lx, ly + 4), f"“{cfg['boton']['spanish']}”", fill=(255, 230, 160), font=f)
    bx, by = geo.BOTON
    d.rectangle((bx, by, bx + 210, by + 30), fill=(60, 50, 30), outline=(200, 170, 90))
    d.text((bx + 105, by + 15), "Continuar", fill=(255, 255, 255), font=f, anchor="mm")
    sx, sy = geo.SALTAR
    d.rectangle((sx, sy, sx + 210, sy + 30), fill=(60, 50, 30), outline=(200, 170, 90))
    d.text((sx + 105, sy + 15), "No me interesa el lore", fill=(255, 255, 255), font=f, anchor="mm")
    img.save(png)


ESTILO_PEDIDO = (
    "ONE comic-book panel (a single image, not a page): no panel borders, no frames, no speech balloons, "
    "no captions, no text, no letters, no numbers, no watermark. Strong readable composition at small size. "
    "The whole image is shown (the caption goes in a strip below it, not over it). Keep the main subject in "
    "the centre: the edges may be cropped to fit the panel")


def items() -> list[dict]:
    """Los pedidos: una imagen por viñeta, a 2x del tamaño de su lugar en la página."""
    out = []
    for tag, cfg in _cfg_crudo().items():
        pag = geo.pagina(cfg)
        for n, (v, area, forma) in enumerate(zip(cfg["vinetas"], pag["artes"], pag["formas"]), 1):
            # 2026-11-20: el tamaño del dibujo (sin la franja del texto, que va abajo)
            w, h = (min(area[2], area[3]),) * 2 if forma == "circulo" else (area[2], area[3])
            forma_txt = {"circulo": " The panel is ROUND: compose for a circle (corners will be cut off).",
                         "arco": " The panel has a ROUND ARCH on top: the top corners will be cut off.",
                         "ojiva": " The panel has a POINTED ARCH on top: the top corners will be cut off."}.get(forma, "")
            out.append({
                "type": "comic_panel", "tag": tag, "id": f"historieta_{tag}_{n}", "dest": arte_de(tag, n),
                "done": arte_de(tag, n).exists(), "size": (w * 2, h * 2),
                "style": f"{ESTILO_PEDIDO}; comic style of this nation: {' '.join(cfg['dibujo'].split())}",
                "description": (f"Panel {n} of 8 of the opening comic of this nation ('{v['texto']['english']}' "
                                f"is the caption the game writes below it; do NOT write it). DRAW: {v['arte']} "
                                f"Panel shape {w}x{h} (aspect {w / h:.2f}:1).{forma_txt}"),
            })
    return out


def importar_vineta(item: dict, img) -> None:
    """Guarda la viñeta (al tamaño de su lugar, DXT1) y vuelve a armar la página de su nación."""
    w, h = item["size"][0] // 2, item["size"][1] // 2
    item["dest"].parent.mkdir(parents=True, exist_ok=True)
    _cubrir(img, w, h).save(item["dest"], "DDS", pixel_format="DXT1")
    componer(item["tag"])


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        vista(sys.argv[1], Path(sys.argv[2]))
    else:
        for t, c in _cfg_crudo().items():
            print(componer(t, c).relative_to(REPO))
