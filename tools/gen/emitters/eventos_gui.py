"""Ventanas de eventos sin el clip (2026-11-15, opción 2): el Receptor y el cable de Ginebra.

Las texturas las dibuja tools/arte/eventos.py (assets/ui/eventos_piel, aplicadas por ui_skin).
Acá se parte del interface/eventwindow.gui del juego instalado y se cambia lo justo:
  - EventWindow y EventWindow_leader (eventos propios, vidrio oscuro): título y descripción con
    letra clara (la de máquina del juego es negra y no se leería sobre el vidrio);
  - EventWindow: la imagen entra en su pantalla con bisel (un poco más chica) y las teclas de
    opción quedan dentro del marco;
  - EventWindow_News (el cable) y EventWindow_Operative quedan como están: letra de máquina
    sobre papel.
Si el .gui de esta versión no trae alguno de esos controles, se avisa y queda como en el juego.
"""

from __future__ import annotations

from ..context import BuildContext
from .selector_gui import _Parche, pos

GUI = "interface/eventwindow.gui"
ARTE = "assets/ui/eventos_piel/gfx/interface/event_report_top_win.dds"
TITULO = {"font": '"hoi_20bs"', "text_color_code": '"W"'}
TEXTO = {"font": '"hoi_16mbs"', "text_color_code": '"W"'}


def parchar(texto: str) -> tuple[str | None, list[str]]:
    p = _Parche(texto)
    for v in ("EventWindow", "EventWindow_leader"):
        p.fijar([v, "top_Window", "Title"], TITULO)
        p.fijar([v, "midsection", "Description"], TEXTO)
    p.fijar(["EventWindow", "bottom_Window", "event_picture"], {"position": pos(20, 12), "scale": "0.9"})
    p.fijar(["EventWindow", "bottom_Window", "options_grid"], {"position": pos(217, 4)})
    # 2026-11-21 (captura: "el texto se va de los botones"): la opción del juego es letra 20 en una caja más
    # ancha que el botón (340 en 300); con letra 16 y el ancho del botón entran dos renglones
    if "event_option_entry" in texto:   # (si esta versión no la trae, queda como en el juego)
        p.fijar(["event_option_entry", "Name"], {"font": '"hoi_16mbs"', "maxWidth": "288", "maxHeight": "42",
                                                 "position": pos(6, 2)})
    return (None if p.faltan else p.texto), p.faltan


def emit(ctx: BuildContext) -> None:
    if ctx.vanilla is None:
        return
    src = ctx.vanilla.root / GUI
    if not src.exists() or not (ctx.spec.root.parent / ARTE).exists():
        return
    texto, faltan = parchar(src.read_text(encoding="utf-8-sig", errors="replace"))
    if texto is None:
        ctx.warn(f"eventos: {GUI} de este juego no es el esperado ({', '.join(faltan)}); queda la letra del juego")
        return
    ctx.write_text(GUI, "# Generado por tools/gen/emitters/eventos_gui.py desde el del juego: eventos propios\n"
                        "# en el Receptor (letra clara sobre vidrio), noticias en el cable de Ginebra.\n" + texto)
    ctx.note("eventos: ventana del Receptor y cable de Ginebra (sin el informe con clip)")
