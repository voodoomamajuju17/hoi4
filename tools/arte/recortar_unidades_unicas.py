"""Íconos de las unidades únicas, recortados de las pantallas de carga 16-19
(2026-10-09: "no veo el ícono del gliptodonte o otras unidades únicas").

Cada unidad se recorta de su pantalla y se separa del fondo con GrabCut de
OpenCV. Escribe previews PNG en <salida> y, con --write,
assets/<TAG>/armas/<uid>.dds (faction_tech.py las lleva al equipo y a las
tecnologías de la unidad). Herramienta de desarrollo: necesita opencv y numpy,
no la corre empezar.bat.

    python3 tools/arte/recortar_unidades_unicas.py . /tmp/previews --write
"""
import sys
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

REPO = Path(sys.argv[1])
OUT = Path(sys.argv[2])
WRITE = "--write" in sys.argv
sys.path.insert(0, str(REPO))
from tools.gen.art import write_dds

L = REPO / "assets/menu/loading"
# (archivo, caja en la imagen 1920x1440: x0, y0, x1, y1)
UNITS = {
    "EFE_gliptodonte": ("16_EFE_vs_NAS_gliptodonte_contra_condores.dds", (110, 250, 1240, 870)),
    "NAS_hijos_del_condor": ("16_EFE_vs_NAS_gliptodonte_contra_condores.dds", (1120, 0, 1920, 300)),
    "APF_kiboko": ("17_APF_vs_NRE_kiboko_contra_onagro.dds", (10, 330, 950, 770)),
    "NRE_onagro": ("17_APF_vs_NRE_kiboko_contra_onagro.dds", (1650, 330, 1910, 445)),
    "ASC_centinela": ("18_ASC_vs_FCU_centinelas_contra_ala_de_obsidiana.dds", (640, 700, 1140, 1090)),
    "FCU_ala_de_obsidiana": ("18_ASC_vs_FCU_centinelas_contra_ala_de_obsidiana.dds", (290, 0, 1920, 460)),
    "SHD_dragon_del_canal": ("19_SHD_vs_HSN_dragon_contra_leviatan.dds", (0, 380, 760, 610)),
    "HSN_leviatan": ("19_SHD_vs_HSN_dragon_contra_leviatan.dds", (1385, 385, 1578, 612)),
}

ONLY_BIGGEST = {"ASC_centinela", "HSN_leviatan"}


def cut(uid, src, box):
    im = np.array(Image.open(L / src).convert("RGB"))
    x0, y0, x1, y1 = box
    crop = im[y0:y1, x0:x1].copy()
    h, w = crop.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    m = max(2, int(min(w, h) * 0.03))
    rect = (m, m, w - 2 * m, h - 2 * m)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    bgr = cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)
    cv2.grabCut(bgr, mask, rect, bgd, fgd, 8, cv2.GC_INIT_WITH_RECT)
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    # la pieza más grande (sin manchas sueltas) y bordes suaves
    n, lab, stats, _ = cv2.connectedComponentsWithStats(fg)
    if n > 1:
        keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        big = stats[keep, cv2.CC_STAT_AREA]
        fg = np.zeros_like(fg)
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] >= big * 0.15:
                if i == keep or uid not in ONLY_BIGGEST:
                    fg[lab == i] = 255
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    alpha = cv2.GaussianBlur(fg, (5, 5), 0)
    rgba = np.dstack([crop, alpha])
    if w > 600:   # como las demás armas (600 de ancho): el ícono del juego mide 146x54
        im2 = Image.fromarray(rgba, "RGBA").resize((600, round(h * 600 / w)), Image.LANCZOS)
        rgba = np.array(im2)
    return rgba

for uid, (src, box) in UNITS.items():
    rgba = cut(uid, src, box)
    img = Image.fromarray(rgba, "RGBA")
    # preview sobre gris
    bg = Image.new("RGBA", img.size, (90, 90, 90, 255))
    bg.alpha_composite(img)
    bg.convert("RGB").save(OUT / f"{uid}.png")
    if WRITE:
        tag = uid.split("_")[0]
        h, w = rgba.shape[:2]
        px = [tuple(int(c) for c in p) for p in rgba.reshape(-1, 4)]
        write_dds(REPO / "assets" / tag / "armas" / f"{uid}.dds", w, h, px)
    print(uid, img.size, "fg%", round(float((rgba[..., 3] > 128).mean()) * 100))
