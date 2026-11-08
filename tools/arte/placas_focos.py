"""Placas de nombre de los focos en materiales reales (2026-11-08).

Pedido (2026-11-05): "fijate qué podés hacer con el marco, la parte del cuadrito que dice el
nombre del foco". El inventario del juego (ui_para_claude.zip -> placas_de_focos) trae las
placas por estado: no disponible, se puede empezar, completado (y las "joint" de focos
compartidos, que se pintan igual). Se rehacen con las muestras de assets/ui/materiales sobre
la silueta y el relieve del original, como la ventana de eventos (materiales_piloto.py):

  - no disponible: acero ennegrecido, borde de bronce apagado;
  - se puede empezar: vidrio ahumado con un brillo turquesa, borde de latón;
  - completado: cobre pulido, borde de latón brillante.

Siempre oscuras por dentro: el nombre del foco es texto claro.

    python -m tools.arte.placas_focos <carpeta con originales/> [maqueta.png]
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from tools.arte.materiales_piloto import SALIDA, _multiplicar_luz, guardar, material

CARPETA = "gfx/interface/focusview/titlebar"

# estado -> (material de adentro, brillo, material del borde, brillo del borde, tinte o None)
ESTADOS = {
    "unavailable": ("mat_acero_ennegrecido", 0.85, "mat_bronce_cepillado", 0.55, None),
    "can_start": ("mat_vidrio_ahumado", 1.0, "mat_laton_pulido", 0.72, (40, 170, 160)),
    "completed": ("mat_bronce_cepillado", 0.62, "mat_laton_pulido", 0.85, (190, 105, 55)),
}


def estado(nombre: str) -> str | None:
    if "texture" in nombre:
        return None
    for e in ESTADOS:
        if nombre.startswith(f"focus_{e}") or (e == "can_start" and nombre.startswith("focus_start")):
            return e
    return None


def placa(orig: Image.Image, cual: str) -> Image.Image:
    orig = orig.convert("RGBA")
    w, h = orig.size
    alfa = orig.getchannel("A")
    hay = alfa.point(lambda a: 255 if a > 40 else 0)
    # adentro: la silueta achicada 4 px; el borde es lo que queda
    adentro = hay.filter(ImageFilter.MinFilter(9))
    borde = ImageChops.subtract(hay, adentro)
    lum = ImageOps.grayscale(orig.convert("RGB"))
    media = max(1, sum(lum.tobytes()) / max(1, w * h))
    relieve = lum.point(lambda v: max(0, min(255, int(v * 128 / media))))
    mat, brillo, mat_b, brillo_b, tinte = ESTADOS[cual]
    fondo = material(mat, w, h, 0.25)
    fondo = ImageEnhance.Brightness(fondo).enhance(brillo)
    if tinte:
        capa = Image.new("RGB", (w, h), tinte)
        # brillo suave en el centro (el foco que se puede tomar "llama")
        luz = Image.new("L", (w, h), 0)
        ImageDraw.Draw(luz).ellipse((w * 0.15, -h * 0.2, w * 0.85, h * 1.2), fill=70)
        luz = luz.filter(ImageFilter.GaussianBlur(10))
        fondo = Image.composite(capa, fondo, luz)
    fondo = _multiplicar_luz(fondo, relieve, 0.5)
    metal = ImageEnhance.Brightness(material(mat_b, w, h, 0.2)).enhance(brillo_b)
    # el relieve del original entero en el borde y el emblema alado (sus plumas y la gema)
    metal = ImageEnhance.Color(metal).enhance(0.75)
    metal = _multiplicar_luz(metal, relieve, 1.6)
    out = Image.composite(metal, fondo, borde)
    # un filete oscuro entre el borde y el adentro, para que se lea el canto
    filete = ImageChops.subtract(adentro, adentro.filter(ImageFilter.MinFilter(3)))
    out = Image.composite(Image.new("RGB", (w, h), (12, 10, 8)), out, filete.point(lambda v: 150 if v else 0))
    res = out.convert("RGBA")
    res.putalpha(alfa)
    return res


def main(originales: str, maqueta: str | None = None) -> list[str]:
    base = Path(originales)
    if (base / "originales").is_dir():
        base = base / "originales"
    hechas, muestras = [], {}
    for src in sorted((base / CARPETA).glob("*.dds")):
        cual = estado(src.stem)
        if cual is None:
            continue
        img = placa(Image.open(src), cual)
        guardar(img, f"{CARPETA}/{src.name}")
        hechas.append(src.name)
        if src.stem in ("focus_unavailable_bg", "focus_can_start_bg", "focus_completed_bg"):
            muestras[cual] = (Image.open(src).convert("RGBA"), img)
    if maqueta and muestras:
        from tools.arte.materiales_piloto import _fuente
        W, H = 3 * 190 + 20, 2 * 70 + 30
        hoja = material("mat_pizarra", W, H, 0.5).convert("RGBA")
        d = ImageDraw.Draw(hoja)
        for k, cual in enumerate(("unavailable", "can_start", "completed")):
            if cual not in muestras:
                continue
            for fila, img in enumerate(muestras[cual]):
                x, y = 15 + k * 190, 15 + fila * 75
                hoja.alpha_composite(img, (x, y))
                d.text((x + img.width // 2, y + 30), "La Ley de la Semilla", fill=(240, 236, 226),
                       font=_fuente(13), anchor="mm")
        hoja = hoja.resize((W * 2, H * 2), Image.LANCZOS)
        hoja.convert("RGB").save(maqueta, quality=92)
    return hechas


if __name__ == "__main__":
    r = main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"placas de focos: {len(r)} en {SALIDA.relative_to(SALIDA.parents[2])}/{CARPETA}")
