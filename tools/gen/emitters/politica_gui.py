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
# 2026-11-12 (captura: hueco grande debajo de los espíritus): ahora nunca hay más de 6 a la vez
# (emitters/espiritus.py), así que alcanza una fila; la segunda quedaba vacía
FILAS = 1           # filas de espíritus a tamaño completo
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
        # 2026-11-08 (captura: "los espíritus se ven exactamente del mismo tamaño"): con más de 6 el
        # juego usa igual la grilla chica; esa también pasa a casillas grandes, 6 por fila
        ("spirit_grid_over_defined", r'size\s*=\s*\{\s*width\s*=\s*\d+\s*height\s*=\s*\d+\s*\}',
         lambda m: f"size = {{ width = 354 height = {ALTO_FILA * FILAS} }}"),
        ("spirit_grid_over_defined", r'slotsize\s*=\s*\{\s*width\s*=\s*\d+\s*height\s*=\s*\d+\s*\}',
         lambda m: f"slotsize = {{ width = 59 height = {ALTO_FILA} }}"),
        ("spirit_grid_over_defined", r'max_slots_horizontal\s*=\s*\d+', lambda m: "max_slots_horizontal = 6"),
        ("spirit_grid_over_defined", r'position\s*=\s*\{\s*x\s*=\s*\d+\s*y\s*=\s*\d+\s*\}',
         lambda m: "position = { x = 1 y = 2 }"),
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
    # 2026-11-12 ("el gráfico circular no tiene ningún sentido para nosotros; ahí tendría que estar
    # el botón del Líder"): el gráfico de popularidad se va fuera de la pantalla; su lugar lo
    # ocupa el botón de la Ficha (boton_lider)
    r = _cambiar_en(texto, "political_pie_chart", r'position\s*=\s*\{\s*x\s*=\s*-?\d+\s*y\s*=\s*(-?\d+)\s*\}',
                    lambda m: f"position = {{ x = -3000 y = {m.group(1)} }}")
    if r is None:
        faltan.append("political_pie_chart")
    else:
        texto = r
    # 2026-11-12 (captura: "atrás siguen las siglas del gráfico, no las queremos"): la lista de
    # ideologías con su porcentaje (chart_explanation) también se va
    r = _cambiar_en(texto, "chart_explanation", r'position\s*=\s*\{\s*x\s*=\s*-?\d+\s*y\s*=\s*(-?\d+)\s*\}',
                    lambda m: f"position = {{ x = -3000 y = {m.group(1)} }}")
    if r is None:
        faltan.append("chart_explanation")
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
    if DY == 0 or not _fondo_alto(ctx):
        texto = texto.replace(f'spriteType = "{FONDO}"', 'spriteType = "GFX_pol_view_bg"')
    else:
        ctx.write_text("interface/meganations_politica.gfx",
                       "spriteTypes = {\n\tspriteType = {\n\t\tname = \"%s\"\n\t\ttexturefile = \"%s\"\n\t}\n}\n"
                       % (FONDO, FONDO_TEX))
    ctx.write_text(GUI, "# Generado por tools/gen/emitters/politica_gui.py desde el del juego:\n"
                        f"# espíritus en {FILAS} filas a tamaño completo, lo de abajo {DY} px más abajo.\n" + texto)
    ctx.note(f"política: espíritus en {FILAS} filas a tamaño completo (hasta {6 * FILAS}); lo de abajo baja {DY} px")
    boton_lider(ctx)


GRAFICO = (270, 304, 100)   # x, y y lado del gráfico de popularidad en el .gui del juego (antes de bajar DY)


def boton_lider(ctx: BuildContext) -> None:
    """El botón de la Ficha del Líder donde estaba el gráfico (2026-11-12). Es una ventana del mod
    colgada de la pantalla de Política (parent_window_token = politics_tab), como los acentos."""
    from .ficha_lider import DISENO, _tags_or, paises
    tags = paises(ctx)
    if not tags or not (ctx.mod_root / "gfx/interface/meganations/ficha/boton_grande.dds").exists():
        return
    gx, gy, gl = GRAFICO
    lado = DISENO["boton_grande"]
    # 2026-11-12 (captura: "queda medio choto"): más chico que el lugar del gráfico, para no tocar
    # la facción de arriba ni los botones de abajo, y al lado el rótulo con el nombre del líder
    x, y = gx + (gl - lado) // 2, gy + DY + (gl - lado) // 2
    tx = lado + 14
    gui = ('guiTypes = {\n\tcontainerWindowType = {\n\t\tname = "mn_ficha_politica_window"\n'
           f'\t\tposition = {{ x = {x} y = {y} }}\n\t\tsize = {{ width = 270 height = {lado} }}\n'
           '\t\torientation = upper_left\n'
           '\t\tbuttonType = {\n\t\t\tname = "abrir"\n\t\t\tposition = { x = 0 y = 0 }\n'
           '\t\t\tspriteType = "GFX_mn_ficha_boton_grande"\n\t\t\tpdx_tooltip = "MN_FICHA_BOTON_TT"\n\t\t}\n'
           '\t\tinstantTextboxType = {\n\t\t\tname = "rotulo"\n'
           f'\t\t\tposition = {{ x = {tx} y = {lado // 2 - 26} }}\n'
           '\t\t\tfont = "hoi_24header"\n\t\t\ttext = "MN_FICHA_TITULO"\n\t\t\tmaxWidth = 160\n\t\t\tmaxHeight = 26\n'
           '\t\t\tfixedsize = yes\n\t\t}\n'
           '\t\tinstantTextboxType = {\n\t\t\tname = "lider"\n'
           f'\t\t\tposition = {{ x = {tx} y = {lado // 2 + 2} }}\n'
           '\t\t\tfont = "hoi_16mbs"\n\t\t\ttext = "[Root.GetLeader]"\n\t\t\tmaxWidth = 160\n\t\t\tmaxHeight = 36\n'
           '\t\t\tfixedsize = yes\n\t\t}\n\t}\n}\n')
    sg = ("scripted_gui = {\n\tmn_ficha_politica = {\n\t\tcontext_type = player_context\n"
          "\t\tparent_window_token = politics_tab\n\t\twindow_name = \"mn_ficha_politica_window\"\n"
          f"\t\tvisible = {{ {_tags_or(tags)} has_country_flag = MEGANATIONS_lider_listo }}\n"
          "\t\teffects = {\n\t\t\tabrir_click = {\n"
          "\t\t\t\tif = { limit = { has_country_flag = MEGANATIONS_ficha_abierta } clr_country_flag = MEGANATIONS_ficha_abierta }\n"
          "\t\t\t\telse = { set_country_flag = MEGANATIONS_ficha_abierta MEGANATIONS_ficha_actualizar = yes }\n"
          "\t\t\t}\n\t\t}\n\t\tai_enabled = { always = no }\n\t}\n}\n")
    ctx.write_text("interface/meganations_ficha_politica.gui", "# Generado por tools/gen/emitters/politica_gui.py\n" + gui)
    ctx.write_text("common/scripted_guis/meganations_ficha_politica.txt", "# Generado por tools/gen/emitters/politica_gui.py\n" + sg)
    ctx.note("política: el gráfico de popularidad sale; en su lugar, el botón grande de la Ficha del Líder")
