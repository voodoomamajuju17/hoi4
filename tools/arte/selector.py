"""Arte PROVISIONAL del selector-receptor (2026-11-13, "Receptor 2100, prototipo").

Carcasa con las zonas marcadas y una tecla de canal de dos cuadros (normal, elegida), solo para
probar la distribución dentro del juego. El arte final se encarga con las medidas que salgan de
la prueba. Se dibuja una vez con Pillow y queda en assets/ui/selector/ (el armado solo lo copia).

    python3 -m tools.arte.selector
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SALIDA = REPO / "assets" / "ui" / "selector"

# Medidas del informe (coordenadas de gamesetup_interesting_countries_window, 1225 x 717)
VENTANA = (1225, 717)
ZONAS = {
    "cabecera": (24, 16, 1177, 48),
    "monitor": (24, 76, 686, 534),
    "banco": (730, 76, 471, 408),
    "filtros": (730, 490, 471, 120),
    "pie": (24, 626, 1177, 68),
}
TECLA = (230, 60)
PASO = (240, 68)

GRAFITO_A, GRAFITO_B = (46, 50, 54), (24, 26, 29)
COBRE, COBRE_LUZ = (194, 122, 69), (240, 181, 133)
TURQUESA = (79, 214, 200)
VIDRIO = (8, 22, 26)


def _dds(img, dest: Path) -> None:
    import sys
    sys.path.insert(0, str(REPO))
    from tools.gen import art
    img = img.convert("RGBA")
    raw = img.tobytes()
    dest.parent.mkdir(parents=True, exist_ok=True)
    art.write_dds(dest, img.width, img.height, [tuple(raw[k:k + 4]) for k in range(0, len(raw), 4)])


def fondo():
    from PIL import Image, ImageDraw
    W, H = VENTANA
    img = Image.new("RGBA", (W, H))
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        c = tuple(round(GRAFITO_A[i] + (GRAFITO_B[i] - GRAFITO_A[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = c + (250,)
    d = ImageDraw.Draw(img)
    # rejilla de parlante, tenue, en el banco (la carcasa del receptor)
    for y in range(0, H, 6):
        d.line((0, y, W, y), fill=(255, 255, 255, 6))
    x, y, w, h = ZONAS["monitor"]
    d.rounded_rectangle((x - 6, y - 6, x + w + 6, y + h + 6), 14, fill=(12, 13, 15, 255), outline=COBRE + (255,), width=3)
    d.rounded_rectangle((x, y, x + w, y + h), 10, fill=VIDRIO + (255,), outline=TURQUESA + (90,), width=1)
    for k in range(12):                         # reflejo tenue en la esquina de arriba
        d.line((x + 20 + k * 6, y + 4, x + 4, y + 20 + k * 6), fill=(255, 255, 255, 5))
    for nombre in ("banco", "filtros"):
        x, y, w, h = ZONAS[nombre]
        d.rounded_rectangle((x, y, x + w, y + h), 8, fill=(18, 20, 22, 235), outline=COBRE + (160,), width=1)
    for nombre in ("cabecera", "pie"):
        x, y, w, h = ZONAS[nombre]
        d.rounded_rectangle((x, y, x + w, y + h), 6, fill=(30, 32, 35, 220), outline=COBRE + (110,), width=1)
    d.rectangle((0, 0, W - 1, H - 1), outline=COBRE + (255,), width=2)
    return img


def tecla():
    """Dos cuadros uno al lado del otro: normal y elegida/encima (como la tecla del juego)."""
    from PIL import Image, ImageDraw
    w, h = TECLA
    img = Image.new("RGBA", (w * 2, h), (0, 0, 0, 0))
    for k, (borde, fondo_c) in enumerate(((COBRE, (34, 36, 40)), (TURQUESA, (20, 52, 54)))):
        d = ImageDraw.Draw(img)
        x0 = k * w
        d.rounded_rectangle((x0 + 1, 1, x0 + w - 2, h - 2), 7, fill=fondo_c + (245,), outline=borde + (255,), width=2)
        d.line((x0 + 8, 5, x0 + w - 9, 5), fill=(255, 255, 255, 30))
    return img


def dibujar() -> list[str]:
    _dds(fondo(), SALIDA / "fondo.dds")
    _dds(tecla(), SALIDA / "tecla.dds")
    return [f"selector: fondo {VENTANA[0]}x{VENTANA[1]} y tecla {TECLA[0]}x{TECLA[1]} (2 cuadros) en {SALIDA.relative_to(REPO)}"]


if __name__ == "__main__":
    for linea in dibujar():
        print(linea)
