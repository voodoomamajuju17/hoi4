"""Geometría de la Historieta (spec/46_historietas.yaml, 2026-11-18).

La comparten el armado del mod (tools/gen/emitters/historietas.py: dónde va cada texto) y el arte
(tools/arte/historietas.py: dónde va cada viñeta y cada recuadro en la página). Sin PIL.

Una página por nación: la ventana entera (W x H) es una sola imagen con las viñetas, los bordes y los
recuadros de texto ya dibujados; el juego escribe encima el título, los textos y el botón.
"""

from __future__ import annotations

W, H = 1160, 740
AREA = (18, 64, 1124, 610)      # x, y, ancho, alto de la zona de viñetas
GUTTER = 12
TITULO = (40, 12, W - 80, 44)   # banda del título
BOTON = (W - 262, H - 54)       # el botón (GFX_mn_ficha_boton_accion)
SALTAR = (W - 484, H - 54)      # "No me interesa el lore" (2026-11-20)
LEMA_TEXTO = (36, H - 48, W - 560, 30)
CHAR_PX = 8.4                   # ancho medio de una letra de hoi_18mbs (generoso: mejor que sobre lugar)
LINEA_PX = 21
INSET = 10

# estilo de página: esquinas de todas las viñetas ("recto", "redondo", "chaflan", "inclinado")
ESQUINAS = {"organico": "redondo", "placa": "chaflan", "cristal": "redondo", "ola": "inclinado",
            "sol": "recto", "rollo": "recto", "kente": "recto", "marmol": "recto", "remaches": "recto",
            "ojiva": "recto", "arena": "recto", "selva": "redondo", "chatarra": "inclinado",
            "astillero": "chaflan", "telar": "recto"}
INCLINE = {"ola": 18, "chatarra": 24}


def vinetas(filas: list) -> list[tuple[int, int, int, int]]:
    """filas: [[alto, [ancho, ancho...]], ...] (pesos) -> rectángulos en orden de lectura."""
    x0, y0, aw, ah = AREA
    total_h = sum(float(f[0]) for f in filas)
    libre_h = ah - GUTTER * (len(filas) - 1)
    rects, y = [], y0
    for i, (alto, anchos) in enumerate(filas):
        h = round(libre_h * float(alto) / total_h) if i < len(filas) - 1 else y0 + ah - y
        libre_w = aw - GUTTER * (len(anchos) - 1)
        tot = sum(float(a) for a in anchos)
        x = x0
        for j, a in enumerate(anchos):
            w = round(libre_w * float(a) / tot) if j < len(anchos) - 1 else x0 + aw - x
            rects.append((x, y, w, h))
            x += w + GUTTER
        y += h + GUTTER
    return rects


def lineas(texto: str, ancho: int) -> int:
    por_linea = max(8, int((ancho - 16) / CHAR_PX))
    n, actual = 1, 0
    for palabra in texto.split():
        largo = len(palabra) + (1 if actual else 0)
        if actual + largo > por_linea:
            n, actual = n + 1, len(palabra)
        else:
            actual += largo
    return n


def recuadro(rect, forma: str, estilo: str, lugar: str, textos: list[str]) -> tuple[int, int, int, int]:
    """El recuadro del texto de una viñeta (x, y, ancho, alto).

    2026-11-20 ("¿El texto tapa así todas las imágenes??"): el texto ya no va encima del dibujo, va en una
    franja de papel ABAJO de la viñeta (como Príncipe Valiente); el dibujo queda entero arriba (area_arte).
    En la viñeta redonda, la franja va debajo del círculo."""
    x, y, w, h = rect
    s = INCLINE.get(estilo, 0)
    if forma == "circulo":
        cw = min(w - 2 * INSET, 340)
        n = max(lineas(t, cw) for t in textos)
        ch = n * LINEA_PX + 10
        return (int(x + w / 2 - cw / 2), y + h - ch - 4, cw, ch)
    cw = w - 12 - 2 * s
    n = max(lineas(t, cw) for t in textos)
    ch = n * LINEA_PX + 10
    return (x + 6 + s // 2, y + h - ch - 6, cw, ch)


def area_arte(rect, forma: str, caja) -> tuple[int, int, int, int]:
    """Dónde va el dibujo: toda la viñeta salvo la franja del texto (x, y, ancho, alto)."""
    x, y, w, h = rect
    return (x, y, w, caja[1] - 6 - y)


def pagina(cfg: dict) -> dict:
    """{rects, formas, recuadros} de una nación (cfg = su entrada de 46_historietas)."""
    rects = vinetas(cfg["filas"])
    vs = cfg["vinetas"]
    if len(rects) != len(vs):
        raise ValueError(f"historieta: {len(rects)} lugares en las filas y {len(vs)} viñetas")
    estilo = cfg["estilo"]
    formas = [v.get("forma", "rect") for v in vs]
    cajas = [recuadro(r, f, estilo, v.get("caja", "arriba"),
                      [v["texto"]["spanish"], v["texto"]["english"]])
             for r, f, v in zip(rects, formas, vs)]
    artes = [area_arte(r, f, c) for r, f, c in zip(rects, formas, cajas)]
    return {"rects": rects, "formas": formas, "recuadros": cajas, "artes": artes}


def arco_alto(w: int, h: int, forma: str) -> int:
    """Cuánto ocupa el arco arriba de una viñeta con arco u ojiva."""
    return int(min(w / 2, h * 0.38)) if forma == "arco" else int(min(w * 0.55, h * 0.42))
