"""Muestras de material para los modelos 3D (2026-11-09, arte/pedidos_fijos/28_texturas_modelos.txt).

    python -m tools.arte.texturas_modelos <carpeta con los png>

Copia cada textura_<NACIÓN>_<material>.png a assets/modelos/texturas/ (las opacas en .jpg) y, si al repetirla se ve el
corte (el borde de un lado no sigue al del otro), la empareja: cerca de cada borde se funde con la
imagen corrida media vuelta, que ahí sí empalma. Saca del pedido las que ya llegaron.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

REPO = Path(__file__).resolve().parents[2]
DEST = REPO / "assets" / "modelos" / "texturas"
PEDIDO = REPO / "arte" / "pedidos_fijos" / "28_texturas_modelos.txt"
BANDA = 0.18   # parte de cada lado que se funde


def _dif(a, b) -> float:
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


def corte(img: Image.Image) -> tuple[bool, bool]:
    """(se ve el corte de izquierda a derecha, se ve de arriba a abajo)."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    hz = _dif(rgb.crop((0, 0, 1, h)), rgb.crop((w - 1, 0, w, h)))
    hz_v = _dif(rgb.crop((w - 2, 0, w - 1, h)), rgb.crop((w - 1, 0, w, h)))
    vt = _dif(rgb.crop((0, 0, w, 1)), rgb.crop((0, h - 1, w, h)))
    vt_v = _dif(rgb.crop((0, h - 2, w, h - 1)), rgb.crop((0, h - 1, w, h)))
    return hz > max(15, 2.5 * hz_v), vt > max(15, 2.5 * vt_v)


def _mascara(n: int, horizontal: bool, size) -> Image.Image:
    w, h = size
    b = int(n * BANDA)
    vals = []
    for i in range(n):
        d = min(i, n - 1 - i)
        vals.append(255 if d < 2 else max(0, int(255 * (1 - d / b))) if d < b else 0)
    if horizontal:
        fila = Image.new("L", (n, 1)); fila.putdata(vals)
        return fila.resize((w, h))
    colm = Image.new("L", (1, n)); colm.putdata(vals)
    return colm.resize((w, h))


def emparejar(img: Image.Image) -> Image.Image:
    hz, vt = corte(img)
    out = img
    w, h = img.size
    if hz:
        corrida = ImageChops.offset(out, w // 2, 0)
        out = Image.composite(corrida, out, _mascara(w, True, (w, h)))
    if vt:
        corrida = ImageChops.offset(out, 0, h // 2)
        out = Image.composite(corrida, out, _mascara(h, False, (w, h)))
    return out


def sacar_del_pedido() -> int:
    if not PEDIDO.exists():
        return 0
    texto = PEDIDO.read_text(encoding="utf-8")
    cab, *bloques = texto.split("ASSET_REQUEST")
    def llego(b):
        n = re.search(r"filename:\s*(\S+)", b).group(1)
        return (DEST / n).exists() or (DEST / n).with_suffix(".jpg").exists()
    quedan = [b for b in bloques if not llego(b)]
    cab = re.sub(r"^# \d+ ", f"# {len(quedan)} ", cab, count=1)
    PEDIDO.write_text(cab + "".join("ASSET_REQUEST" + b for b in quedan), encoding="utf-8")
    return len(quedan)


def main(carpeta: str) -> list[str]:
    DEST.mkdir(parents=True, exist_ok=True)
    hechas = []
    for f in sorted(Path(carpeta).rglob("textura_*.png")):
        img = Image.open(f)
        img.load()
        transparente = "A" in img.getbands() and img.getchannel("A").getextrema()[0] < 250
        img = img.convert("RGBA" if transparente else "RGB")
        nota = ""
        if not transparente:   # los calcos no se repiten
            hz, vt = corte(img)
            if hz or vt:
                img = emparejar(img)
                nota = " (emparejada)"
        if transparente:
            img.save(DEST / f.name, optimize=True)
        else:   # opacas en jpg de alta calidad: el repo no carga 1,5 MB por muestra
            img.save(DEST / (f.stem + ".jpg"), quality=93, subsampling=0)
        hechas.append(f.name + nota)
    return hechas


if __name__ == "__main__":
    r = main(sys.argv[1])
    print("\n".join(r))
    print(f"{len(r)} texturas en assets/modelos/texturas; quedan {sacar_del_pedido()} en el pedido")
