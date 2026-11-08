"""Panel de Política con más lugar para los espíritus (2026-11-07).

Pedido: "¿puede cambiarse esto para hacer más lugar al espacio para espíritus? Me gustarían
íconos más grandes". El juego muestra los espíritus en una grilla de 6 a tamaño completo y,
cuando son más de 6, pasa a otra grilla con íconos a la mitad. Acá la grilla grande pasa a
tener dos filas (hasta 12 a tamaño completo) y todo lo que está debajo de los espíritus
(facción, ideología, la torta, los botones de ocupados y súbditos, las leyes) baja lo mismo.

Se parte del countrypoliticsview.gui del juego instalado y se le cambian solo esas cosas: si
en esta versión del juego no aparece alguna, se avisa y no se toca la pantalla.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..context import BuildContext

GUI = "interface/countrypoliticsview.gui"
FILAS = 2           # filas de espíritus a tamaño completo
ALTO_FILA = 68      # el alto de un espíritu en la grilla del juego
DY = ALTO_FILA * (FILAS - 1)
# lo que está debajo de los espíritus (y baja DY)
BAJAN = ("pol_faction_icon", "political_pie_chart", "ruling_party_info", "autonomy_progress_view",
         "show_subjects_button", "ideas", "tutorial_glow", "politics_bottom", "manage_occupied_button",
         "manage_occupied_button_text", "subjects_button_container", "show_exiles_collaborations_button",
         "manage_exiled_collaborations_governments", "icon_exiled_collaborations_governments",
         "icon_occupied_territories", "parties_grid")
FONDO = "GFX_mn_pol_view_bg_alto"
FONDO_TEX = "gfx/interface/meganations/pol_view_bg_alto.dds"
_POS = re.compile(r'position\s*=\s*\{\s*x\s*=\s*(-?\d+)\s*y\s*=\s*(-?\d+)\s*\}')


def _bajar(texto: str, nombre: str, dy: int) -> str | None:
    m = re.search(r'name\s*=\s*"%s"' % re.escape(nombre), texto)
    if not m:
        return None
    p = _POS.search(texto, m.end())
    siguiente = re.search(r'name\s*=', texto[m.end():])
    if not p or (siguiente and m.end() + siguiente.start() < p.start()):
        return None
    nuevo = f"position = {{ x = {p.group(1)} y = {int(p.group(2)) + dy} }}"
    return texto[:p.start()] + nuevo + texto[p.end():]


def _bloque(texto: str, nombre: str) -> tuple[int, int] | None:
    """(inicio, fin) del bloque { ... } que tiene name = "nombre"."""
    m = re.search(r'name\s*=\s*"%s"' % re.escape(nombre), texto)
    if not m:
        return None
    ini = texto.rfind("{", 0, m.start())
    d, i = 1, ini + 1
    while i < len(texto) and d:
        d += {"{": 1, "}": -1}.get(texto[i], 0)
        i += 1
    return ini, i


def _cambiar_en(texto: str, nombre: str, viejo: str, nuevo: str) -> str | None:
    b = _bloque(texto, nombre)
    if not b:
        return None
    cuerpo = texto[b[0]:b[1]]
    cambiado, n = re.subn(viejo, nuevo, cuerpo, count=1)
    if not n:
        return None
    return texto[:b[0]] + cambiado + texto[b[1]:]


def parchar(texto: str) -> tuple[str | None, list[str]]:
    """El .gui del juego con la grilla de dos filas y lo de abajo corrido. (None, faltan) si
    algo no está como se espera."""
    faltan = []
    pasos = [
        ("spirit_grid", r'size\s*=\s*\{\s*width\s*=\s*(\d+)\s*height\s*=\s*%d\s*\}' % ALTO_FILA,
         lambda m: f"size = {{ width = {m.group(1)} height = {ALTO_FILA * FILAS} }}"),
        ("spirit_grid", r'max_slots\s*=\s*\{\s*x\s*=\s*(\d+)\s*y\s*=\s*1\s*\}',
         lambda m: f"max_slots = {{ x = {m.group(1)} y = {FILAS} }}"),
        ("national_spirit_container", r'size\s*=\s*\{\s*width\s*=\s*(\d+)\s*height\s*=\s*(\d+)\s*\}',
         lambda m: f"size = {{ width = {m.group(1)} height = {int(m.group(2)) + DY} }}"),
        ("pol_view_bg", r'spriteType\s*=\s*"GFX_pol_view_bg"', lambda m: f'spriteType = "{FONDO}"'),
    ]
    for nombre, viejo, nuevo in pasos:
        r = _cambiar_en(texto, nombre, viejo, nuevo)
        if r is None:
            faltan.append(nombre)
        else:
            texto = r
    for nombre in BAJAN:
        r = _bajar(texto, nombre, DY)
        if r is None:
            faltan.append(nombre)
        else:
            texto = r
    return (None if faltan else texto), faltan


FONDO_ASSET = "assets/ui/politica/pol_view_bg_alto.dds"


def fondo_alto(src: Path, dest: Path) -> None:
    """El fondo del panel estirado DY píxeles repitiendo una franja de la zona de los espíritus.
    Se corre una vez con Pillow (tools/arte) y queda en assets/: el armado no necesita Pillow
    (2026-11-08, "No module named 'PIL'" en la compu del usuario)."""
    from PIL import Image
    from .. import art
    img = Image.open(src).convert("RGBA")
    w, h = img.size
    corte = min(h - 2, 150)   # 44 + 150: a la altura de los espíritus
    franja = img.crop((0, corte, w, corte + 1))
    out = Image.new("RGBA", (w, h + DY))
    out.paste(img.crop((0, 0, w, corte)), (0, 0))
    for k in range(DY):
        out.paste(franja, (0, corte + k))
    out.paste(img.crop((0, corte, w, h)), (0, corte + DY))
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = out.tobytes()
    art.write_dds(dest, out.width, out.height, [tuple(raw[k:k + 4]) for k in range(0, len(raw), 4)])


def _fondo_alto(ctx: BuildContext) -> bool:
    if not (ctx.spec.root.parent / FONDO_ASSET).exists():
        return False
    ctx.copy_asset(FONDO_ASSET, FONDO_TEX)
    return True


def emit(ctx: BuildContext) -> None:
    if ctx.vanilla is None:
        return
    src = ctx.vanilla.root / GUI
    if not src.exists():
        ctx.note(f"política: no está {GUI} en el juego; los espíritus quedan como en el juego")
        return
    texto, faltan = parchar(src.read_text(encoding="utf-8-sig", errors="replace"))
    if texto is None:
        ctx.warn(f"política: {GUI} de este juego no es el esperado ({', '.join(faltan)}); "
                 "los espíritus quedan como en el juego")
        return
    if not _fondo_alto(ctx):
        texto = texto.replace(f'spriteType = "{FONDO}"', 'spriteType = "GFX_pol_view_bg"')
    else:
        ctx.write_text("interface/meganations_politica.gfx",
                       "spriteTypes = {\n\tspriteType = {\n\t\tname = \"%s\"\n\t\ttexturefile = \"%s\"\n\t}\n}\n"
                       % (FONDO, FONDO_TEX))
    ctx.write_text(GUI, "# Generado por tools/gen/emitters/politica_gui.py desde el del juego:\n"
                        f"# espíritus en {FILAS} filas a tamaño completo, lo de abajo {DY} px más abajo.\n" + texto)
    ctx.note(f"política: espíritus en {FILAS} filas a tamaño completo (hasta {6 * FILAS}); lo de abajo baja {DY} px")
