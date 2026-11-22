"""Guías de los marcos de la pantalla de carga (2026-11-22): una imagen al doble del tamaño final con las
zonas que el juego usa (placa del título, ranura de la barra, zona de la frase) marcadas, para adjuntar al
pedido arte/pedidos_marcos_pantalla_carga.txt. Se guardan en arte/referencias/."""

from __future__ import annotations

from pathlib import Path

from tools.gen import carga_geo as G

REPO = Path(__file__).resolve().parents[2]
GUIAS = {"carga_marco_estado": "referencias/carga_marco_estado_guia.png",
         "carga_marco_frase": "referencias/carga_marco_frase_guia.png"}


def escribir() -> list[str]:
    from PIL import Image, ImageDraw
    k = 2
    zonas = {"carga_marco_estado": (G.ESTADO, [(G.ESTADO_TITULO, (255, 80, 80), "TITULO"),
                                               (G.ESTADO_RANURA, (80, 160, 255), "BARRA")]),
             "carga_marco_frase": (G.FRASE, [(G.FRASE_TEXTO, (255, 80, 80), "FRASE")])}
    for pid, ((w, h), rects) in zonas.items():
        im = Image.new("RGB", (w * k, h * k), (40, 40, 40))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, w * k - 1, h * k - 1), outline=(200, 200, 200), width=2)
        for (x, y, rw, rh), col, txt in rects:
            d.rectangle((x * k, y * k, (x + rw) * k - 1, (y + rh) * k - 1), outline=col, width=4)
            d.text((x * k + 10, y * k + 6), txt, fill=col)
        dest = REPO / "arte" / GUIAS[pid]
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, optimize=True)
    return list(GUIAS.values())


if __name__ == "__main__":
    print(escribir())
