# -*- coding: utf-8 -*-
"""Control de calidad de las imágenes generadas (2026-11-06).

Pedido: "aumentá el control de calidad y la prevención de errores de los que
siempre vemos". Los que vimos en los lotes del 2026-11-05/06:
  - archivos vacíos o cortados (no abren);
  - fondo blanco o liso cuando se pidió transparente;
  - el dibujo cortado contra el borde;
  - imágenes casi vacías o planas;
  - el mismo pedido dos veces en un zip (grande y 95x85).
Lo usan la Fábrica (tools/fabrica/fabrica_hoi4.py, en la PC del usuario) y
`arte importar` (tools/arte/arte.py). Solo necesita Pillow.
"""

from __future__ import annotations

import io
from pathlib import Path


def abrir(origen):
    """La imagen en RGBA, o None si el archivo está vacío o cortado.
    `origen`: ruta o bytes."""
    from PIL import Image
    try:
        datos = origen if isinstance(origen, (bytes, bytearray)) else Path(origen).read_bytes()
        if not datos:
            return None
        img = Image.open(io.BytesIO(datos))
        img.load()
        return img.convert("RGBA")
    except Exception:
        return None


def _borde(img):
    w, h = img.size
    px = img.load()
    return ([px[x, 0] for x in range(w)] + [px[x, h - 1] for x in range(w)]
            + [px[0, y] for y in range(h)] + [px[w - 1, y] for y in range(h)])


def quitar_fondo(img, tolerancia: int = 28):
    """Si la imagen no trae transparencia y su borde es de un color parejo (el
    fondo blanco o gris de siempre), lo vuelve transparente rellenando desde los
    bordes. Devuelve (imagen, se_quitó)."""
    from PIL import Image, ImageDraw, ImageFilter
    a = img.getchannel("A")
    if a.getextrema()[0] < 250:
        return img, False   # ya tiene transparencia
    borde = _borde(img)
    # color del fondo: el promedio del borde, si el borde es parejo
    n = len(borde)
    media = tuple(sum(p[i] for p in borde) // n for i in range(3))
    lejos = sum(1 for p in borde if max(abs(p[i] - media[i]) for i in range(3)) > tolerancia)
    if lejos > n * 0.15:
        return img, False   # el borde no es un fondo liso: es parte del dibujo
    marca = (255, 0, 255)
    trabajo = img.convert("RGB")
    w, h = trabajo.size
    # relleno desde varios puntos del borde (el fondo puede quedar partido en islas)
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if trabajo.getpixel((x, y)) != marca:
            ImageDraw.floodfill(trabajo, (x, y), marca, thresh=tolerancia)
    m = Image.new("L", (w, h), 0)
    mp, tp = m.load(), trabajo.load()
    for yy in range(h):
        for xx in range(w):
            if tp[xx, yy] == marca:
                mp[xx, yy] = 255
    # borde suave: 1 px de transición para que no quede serruchado
    m = m.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    out = img.copy()
    out.putalpha(Image.eval(m, lambda v: 255 - v))
    return out, True


def revisar(img, transparente: bool) -> list[str]:
    """Problemas encontrados (vacío si está bien). Se llama DESPUÉS de quitar_fondo."""
    from PIL import ImageStat
    if img is None:
        return ["no abre (archivo vacío o cortado)"]
    w, h = img.size
    problemas = []
    if min(w, h) < 16:
        problemas.append(f"demasiado chica ({w}x{h})")
    a = img.getchannel("A")
    opaco = sum(a.histogram()[128:]) / (w * h)
    if transparente:
        if opaco > 0.97:
            problemas.append("sin transparencia: el fondo no se pudo quitar")
        elif opaco < 0.08:
            problemas.append("casi vacía (el dibujo ocupa menos del 8 %)")
        borde = _borde(img)
        tocan = sum(1 for p in borde if p[3] > 128) / len(borde)
        if tocan > 0.20:
            problemas.append(f"el dibujo toca el borde en el {round(tocan * 100)} % del contorno (¿cortado?)")
    else:
        dev = ImageStat.Stat(img.convert("L")).stddev[0]
        if dev < 6:
            problemas.append("imagen plana (casi un solo color)")
    return problemas


def hoja_de_contacto(rutas, destino, lado: int = 120, columnas: int = 10, problemas: dict | None = None) -> None:
    """Todas las imágenes en una sola hoja, con su nombre, para revisar de un vistazo.
    Las que no pasaron el control llevan un marco rojo."""
    from PIL import Image, ImageDraw
    rutas = list(rutas)
    if not rutas:
        return
    problemas = problemas or {}
    filas = (len(rutas) + columnas - 1) // columnas
    alto = lado + 18
    hoja = Image.new("RGBA", (columnas * lado, filas * alto), (28, 38, 46, 255))
    d = ImageDraw.Draw(hoja)
    for i, r in enumerate(rutas):
        x, y = (i % columnas) * lado, (i // columnas) * alto
        img = abrir(r)
        if img is not None:
            img.thumbnail((lado - 8, lado - 8))
            hoja.alpha_composite(img, (x + (lado - img.width) // 2, y + (lado - img.height) // 2))
        if Path(r).name in problemas or img is None:
            d.rectangle((x + 1, y + 1, x + lado - 2, y + lado - 2), outline=(230, 50, 50, 255), width=3)
        d.text((x + 4, y + lado), Path(r).stem[:20], fill=(220, 220, 220, 255))
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    hoja.convert("RGB").save(destino)


def mejores_por_nombre(rutas) -> dict:
    """Si el mismo pedido viene dos veces (la grande y la de 95x85), se queda con la
    más grande que abra bien. Devuelve {nombre_sin_extensión: ruta}."""
    elegido: dict = {}
    for r in rutas:
        img = abrir(r)
        if img is None:
            continue
        stem = Path(r).stem
        area = img.width * img.height
        if stem not in elegido or area > elegido[stem][1]:
            elegido[stem] = (r, area)
    return {k: v[0] for k, v in elegido.items()}
