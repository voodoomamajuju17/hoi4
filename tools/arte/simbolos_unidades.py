"""Íconos de unidades y símbolos de división (2026-11-11, arte/pedidos_fijos/27_unidades_y_simbolos.txt).

    python -m tools.arte.simbolos_unidades <carpeta con los png>

- unidad_<textura>.png -> assets/ui/piel/gfx/interface/counters/divisions_large/<textura>.dds y su
  versión del mapa (divisions_small/onmap_<textura>.dds). El juego los usa con 2 cuadros: el dibujo y
  el símbolo OTAN (cuando está activada esa opción); los dos llevan la silueta de cobre. La piel los
  lleva al tamaño del juego al armar el mod.
- simbolo_<NACIÓN>_<n>.png -> assets/ui/simbolos_division/simbolo_<NACIÓN>_<n>.dds (128x128); el
  armado los suma como símbolos de división nuevos, después de los del juego (ui_skin.simbolos).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
PIEL = REPO / "assets" / "ui" / "piel" / "gfx" / "interface" / "counters"
SIMBOLOS = REPO / "assets" / "ui" / "simbolos_division"
CUADRO = (76, 42)        # un cuadro de unit_infantry_icon.dds del juego (152x42, 2 cuadros)


def _dds(img: Image.Image, dest: Path) -> None:
    from tools.gen import art
    img = img.convert("RGBA")
    raw = img.tobytes()
    art.write_dds(dest, img.width, img.height, [tuple(raw[k:k + 4]) for k in range(0, len(raw), 4)])


def _encajar(img: Image.Image, w: int, h: int, margen: int = 2) -> Image.Image:
    img = img.convert("RGBA")
    caja = img.getchannel("A").getbbox()
    if caja:
        img = img.crop(caja)
    img.thumbnail((w - 2 * margen, h - 2 * margen), Image.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(img, ((w - img.width) // 2, (h - img.height) // 2))
    return out


def unidad(src: Path) -> list[Path]:
    tex = src.stem[len("unidad_"):]
    cuadro = _encajar(Image.open(src), *CUADRO)
    tira = Image.new("RGBA", (CUADRO[0] * 2, CUADRO[1]), (0, 0, 0, 0))
    tira.alpha_composite(cuadro, (0, 0))
    tira.alpha_composite(cuadro, (CUADRO[0], 0))
    hechos = []
    for dest in (PIEL / "divisions_large" / f"{tex}.dds", PIEL / "divisions_small" / f"onmap_{tex}.dds"):
        _dds(tira, dest)
        hechos.append(dest)
    return hechos


def simbolo(src: Path) -> Path:
    dest = SIMBOLOS / f"{src.stem}.dds"
    _dds(_encajar(Image.open(src), 128, 128, 0), dest)
    return dest


def main(carpeta: str) -> tuple[int, int]:
    u = s = 0
    for f in sorted(Path(carpeta).rglob("*.png")):
        if f.name.startswith("unidad_"):
            unidad(f)
            u += 1
        elif f.name.startswith("simbolo_"):
            simbolo(f)
            s += 1
    return u, s


if __name__ == "__main__":
    u, s = main(sys.argv[1])
    print(f"{u} íconos de unidad, {s} símbolos de división")
