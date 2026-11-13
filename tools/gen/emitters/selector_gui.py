"""Selector de país como receptor de transmisiones: PROTOTIPO (2026-11-13).

Pedido (Receptor 2100, prototipo): monitor de vidrio a la izquierda con los datos del país elegido,
botonera de canales a la derecha (dos columnas de hasta seis teclas de 230 x 60, paso 240 x 68),
filtros y menores debajo, pie con volver y confirmar. Coordenadas locales a
gamesetup_interesting_countries_window (1225 x 717).

Se parte del frontendgamesetupview.gui del juego instalado y solo se mueven y redimensionan los
controles que el motor ya rellena (no se agregan controles con nombres nuevos, que el motor no
actualizaría):
  - fila de destacados (countries / countries_grid) -> el banco de teclas;
  - plantilla country_entry -> tecla horizontal con bandera y nombre; el retrato de la tecla queda
    fuera de la vista (existe, pero no se ve ni recibe clics);
  - datos del país elegido (minor_country_leader, nation_title, info, spirit con ideas y focos,
    history) -> dentro del monitor; las ideas pasan a 5 x 2 (el EFE trae siete);
  - filtros y menores -> la zona de abajo del banco.
El arte (carcasa y tecla) lo arma tools/arte/selector.py con materiales reales y las piezas
ilustradas de arte/pedidos_fijos/30_selector_receptor.txt. Si el .gui de esta versión no
tiene alguno de estos controles, se avisa y la pantalla queda como en el juego.
"""

from __future__ import annotations

import re

from ..context import BuildContext

GUI = "interface/frontendgamesetupview.gui"
VENTANA = "gamesetup_interesting_countries_window"
ARTE = "assets/ui/selector"
TEX = "gfx/interface/meganations/selector"
FUERA = -3000
LETRA, LETRA_TITULO = '"hoi_16mbs"', '"hoi_20bs"'   # claras: el monitor es oscuro


def _bloque(texto: str, nombre: str, desde: int = 0, hasta: int | None = None) -> tuple[int, int] | None:
    """(inicio, fin) del bloque { ... } con name = "nombre" exacto, buscando entre desde y hasta."""
    hasta = len(texto) if hasta is None else hasta
    m = re.compile(r'name\s*=\s*"%s"' % re.escape(nombre)).search(texto, desde, hasta)
    if not m:
        return None
    ini = texto.rfind("{", 0, m.start())
    d, i = 1, ini + 1
    while i < len(texto) and d:
        d += {"{": 1, "}": -1}.get(texto[i], 0)
        i += 1
    return ini, i


def _propio(cuerpo: str, clave: str) -> re.Match | None:
    """La clave `clave = ...` del bloque, sin entrar en sus hijos."""
    d = 0
    for m in re.finditer(r"[{}]|\b%s\s*=\s*(\{[^{}]*\}|\"[^\"]*\"|[^\s{}]+)" % re.escape(clave), cuerpo):
        t = m.group(0)
        if t == "{":
            d += 1
        elif t == "}":
            d -= 1
        elif d == 1:
            return m
    return None


class _Parche:
    def __init__(self, texto: str):
        self.texto = texto
        self.faltan: list[str] = []

    def fijar(self, ruta: list[str], cambios: dict[str, str]) -> None:
        """Cambia (o agrega) claves del bloque al final de `ruta` (nombres de padre a hijo)."""
        desde, hasta = 0, None
        b = None
        for nombre in ruta:
            b = _bloque(self.texto, nombre, desde, hasta)
            if b is None:
                self.faltan.append("/".join(ruta))
                return
            desde, hasta = b
        ini, fin = b
        cuerpo = self.texto[ini:fin]
        for clave, valor in cambios.items():
            m = _propio(cuerpo, clave)
            if m:
                cuerpo = cuerpo[:m.start()] + f"{clave} = {valor}" + cuerpo[m.end():]
            else:
                cuerpo = cuerpo[:1] + f"\n\t\t\t{clave} = {valor}" + cuerpo[1:]
        self.texto = self.texto[:ini] + cuerpo + self.texto[fin:]


def pos(x: int, y: int) -> str:
    return f"{{ x = {x} y = {y} }}"


def parchar(texto: str) -> tuple[str | None, list[str]]:
    p = _Parche(texto)
    v = [VENTANA]
    # la carcasa provisional y la cabecera
    p.fijar(v + ["single_player_country_bg"], {"quadTextureSprite": '"GFX_mn_selector_fondo"'})
    p.fijar(v + ["title"], {"position": pos(435, 24)})
    # el banco de canales: dos columnas, hasta seis filas
    p.fijar(v + ["countries"], {"position": pos(730, 76), "size": "{ width = 471 height = 408 }"})
    p.fijar(v + ["countries", "countries_grid"], {"slotsize": "{ width = 240 height = 68 }",
                                                  "max_slots_horizontal": "2", "max_slots_vertical": "6"})
    # filtros y menores, debajo del banco
    p.fijar(v + ["filters"], {"position": pos(730, 490), "size": "{ x = 471 y = 32 }"})
    p.fijar(v + ["countries_medium"], {"position": pos(730, 526), "size": "{ width = 471 height = 80 }"})
    p.fijar(v + ["countries_medium", "countries_grid"], {"max_slots_horizontal": "3"})
    p.fijar(v + ["countries_mini"], {"position": pos(730, 528), "size": "{ width = 471 height = 80 }"})
    p.fijar(v + ["countries_mini", "countries_grid"], {"max_slots_horizontal": "9"})
    p.fijar(v + ["more_countries"], {"position": pos(10, 596)})
    # volver y elegir dentro del pie (y 626 a 694); el juego los tenía a 42 del borde, medio afuera
    p.fijar(v + ["back_button"], {"position": pos(-158, -74)})
    p.fijar(v + ["select_button"], {"position": pos(10, -74)})
    # el monitor: columna izquierda retrato y datos políticos; derecha nombre, ideas, focos e historia
    p.fijar(v + ["minor_country_leader"], {"position": pos(44, 96), "scale": "1.0", "rotation": "0"})
    p.fijar(v + ["minor_portrait_overlay"], {"position": pos(FUERA, 96)})
    # 2026-11-13 (capturas: "no se lee nada el texto del panel izquierdo"): el juego escribe los datos
    # con hoi4_typewriter, que es tinta negra (color = 0xff000000 en core.gfx) para su papel claro;
    # sobre el vidrio oscuro del monitor van con letra clara (hoi_16mbs y hoi_20bs son blancas)
    p.fijar(v + ["info_title"], {"position": pos(44, 316), "maxWidth": "190", "format": "left", "font": LETRA_TITULO})
    p.fijar(v + ["info"], {"position": pos(44, 352)})
    for campo in ("leader_label", "leader", "ideology_label", "ideology", "government_label", "government",
                  "elections_label", "elections", "party_label", "party"):
        p.fijar(v + ["info", campo], {"maxWidth": "190", "font": LETRA})
    p.fijar(v + ["nation_title"], {"position": pos(256, 92), "maxWidth": "444", "format": "left"})
    p.fijar(v + ["spirit"], {"position": pos(256, 150)})
    p.fijar(v + ["spirit", "ideas"], {"size": "{ width = 360 height = 136 }"})
    p.fijar(v + ["spirit", "ideas", "ideas_grid"], {"size": "{ width = 100% height = 136 }",
                                                    "max_slots": "{ x = 5 y = 2 }"})
    p.fijar(v + ["spirit", "focus"], {"position": pos(0, 145)})
    p.fijar(v + ["history_title"], {"position": pos(256, 405), "maxWidth": "444", "format": "left", "font": LETRA_TITULO})
    p.fijar(v + ["history"], {"position": pos(256, 437), "maxWidth": "444", "maxHeight": "168", "font": LETRA})
    # la tecla: bandera y nombre; el retrato existe pero queda fuera de la vista
    t = ["country_entry"]
    p.fijar(t + ["country"], {"quadTextureSprite": '"GFX_mn_selector_tecla"', "position": pos(0, 0)})
    p.fijar(t + ["country_leader"], {"position": pos(FUERA, 0)})
    p.fijar(t + ["country_flag"], {"position": pos(10, 9), "scale": "0.75"})
    # nombres largos ("Reino Celeste Neoandino"): dos renglones con letra de 16
    p.fijar(t + ["country_name"], {"position": pos(76, 10), "maxWidth": "146", "maxHeight": "40",
                                   "format": "left", "font": '"hoi_16mbs"'})
    p.fijar(t + ["new_content"], {"position": pos(204, 2)})
    return (None if p.faltan else p.texto), p.faltan


def emit(ctx: BuildContext) -> None:
    if ctx.vanilla is None:
        return
    src = ctx.vanilla.root / GUI
    repo = ctx.spec.root.parent
    if not src.exists() or not (repo / ARTE / "fondo.dds").exists():
        return
    texto, faltan = parchar(src.read_text(encoding="utf-8-sig", errors="replace"))
    if texto is None:
        ctx.warn(f"selector: {GUI} de este juego no es el esperado ({', '.join(faltan)}); queda como en el juego")
        return
    for pieza in ("fondo", "tecla"):
        ctx.copy_asset(f"{ARTE}/{pieza}.dds", f"{TEX}/{pieza}.dds")
    ctx.write_text("interface/meganations_selector.gfx",
                   "# Generado por tools/gen/emitters/selector_gui.py (arte del receptor: tools/arte/selector.py)\n"
                   "spriteTypes = {\n"
                   f'\tspriteType = {{\n\t\tname = "GFX_mn_selector_fondo"\n\t\ttexturefile = "{TEX}/fondo.dds"\n\t}}\n'
                   f'\tspriteType = {{\n\t\tname = "GFX_mn_selector_tecla"\n\t\ttexturefile = "{TEX}/tecla.dds"\n'
                   '\t\tnoOfFrames = 2\n\t\teffectFile = "gfx/FX/buttonstate_nodowneffect.lua"\n\t}\n}\n')
    ctx.write_text(GUI, "# Generado por tools/gen/emitters/selector_gui.py desde el del juego: selector como receptor\n"
                        "# (prototipo: monitor a la izquierda, dos columnas de teclas a la derecha).\n" + texto)
    ctx.note("selector: prototipo del receptor (monitor y dos columnas de teclas)")
