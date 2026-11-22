"""Los marcos de la pantalla de carga (2026-11-22).

Pedido: "Esos marcos quiero cambiarlos completamente, podés hacer los pedidos que hagan falta" (captura de
la pantalla de carga: la barra de arriba con "Cargando bases de datos" y su barra de progreso, y la caja de
la frase de abajo).

Son del juego: interface/load_screen.gui (dónde va cada cosa) y load_screen.gfx (GFX_loadingstatus_bg,
GFX_loadingtip_bg y la barra GFX_loadingstatus_progress). Acá:
  - interface/load_screen.gfx: el del juego entero (logos, fondos viejos, la barra vieja) MÁS nuestros
    sprites (GFX_mn_carga_*) y nuestra barra. Tienen que estar en ESTE archivo: la pantalla de carga se
    dibuja antes de que el juego lea los demás .gfx de interface/ (crash 2026-11-22: "Could not find
    sprite type [GFX_mn_carga_marco_estado]" y después "No [GFX_default_fallback_texture] defined",
    con los sprites en un meganations_marcos_carga.gfx aparte).
  - interface/load_screen.gui: el mismo archivo del juego con nuestros sprites y las posiciones de
    tools/gen/carga_geo.py (la placa del título, la ranura de la barra y la caja de la frase).
Solo si están las cuatro piezas (assets/menu/carga_marcos/<pieza>.dds, las importa tools/arte/arte.py
desde el pedido arte/pedidos_marcos_pantalla_carga.txt): con una sola faltando, la pantalla
mezclaría marcos viejos y nuevos, así que queda la del juego y el reporte dice cuáles faltan.
"""

from __future__ import annotations

from .. import carga_geo as G
from ..context import BuildContext
from ..pdx import banner_for

SOURCE = "tools/gen/emitters/marcos_carga.py (marcos de la pantalla de carga, 2026-11-22)"
DIR = "gfx/interface/meganations/carga"


def _gui() -> str:
    ew, eh = G.ESTADO
    tx, ty, tw, th = G.ESTADO_TITULO
    rx, ry, _, _ = G.ESTADO_RANURA
    fw, fh = G.FRASE
    qx, qy, qw, qh = G.FRASE_TEXTO
    fy = -fh - G.FRASE_MARGEN_ABAJO
    return f"""guiTypes = {{
	windowType = {{
		name = "load_screen"
		backGround = ""
		position = {{ x = 0 y = 0 }}
		size = {{ x = 1024 y = 768 }}
		moveable = 0
		dontRender = ""
		horizontalBorder = "0"
		verticalBorder = ""
		fullScreen = yes
		Orientation = "UPPER_LEFT"

		iconType = {{
			name = "bg_clausewitz_logo"
			spriteType = "GFX_clausewitz_logo"
			position = {{ x = 23 y = -152 }}
			Orientation = "LOWER_LEFT"
		}}

		iconType = {{
			name = "bg_pdx_int_logo"
			spriteType = "GFX_frontend_dev_logo_s"
			position = {{ x = -130 y = -158 }}
			Orientation = "LOWER_RIGHT"
		}}

		windowType = {{
			name = "status"
			backGround = ""
			position = {{ x = 0 y = 0 }}
			size = {{ x = 1024 y = 768 }}
			moveable = 0
			dontRender = ""
			horizontalBorder = "0"
			verticalBorder = ""
			fullScreen = no
			Orientation = "CENTER_UP"

			iconType = {{
				name = "bg_load_screen2"
				spriteType = "GFX_mn_carga_marco_estado"
				position = {{ x = {-ew // 2} y = 0 }}
			}}

			instantTextBoxType = {{
				name = "text"
				position = {{ x = {-ew // 2 + tx} y = {ty} }}
				textureFile = ""
				font = "loadscreen_header"
				borderSize = {{ x = 0 y = 0 }}
				text = ""
				maxWidth = {tw}
				maxHeight = {th}
				fixedsize = yes
				format = centre
				vertical_alignment = center
			}}

			iconType = {{
				name = "progressbar"
				spriteType = "GFX_mn_carga_progreso"
				position = {{ x = {-ew // 2 + rx} y = {ry} }}
			}}
		}}

		windowType = {{
			name = "tip"
			backGround = ""
			position = {{ x = 0 y = 0 }}
			size = {{ x = 1024 y = 200 }}
			moveable = 0
			dontRender = ""
			horizontalBorder = "0"
			verticalBorder = ""
			fullScreen = no
			Orientation = "CENTER_DOWN"

			iconType = {{
				name = "bg_load_screen"
				spriteType = "GFX_mn_carga_marco_frase"
				position = {{ x = {-fw // 2} y = {fy} }}
			}}

			instantTextBoxType = {{
				name = "text"
				position = {{ x = {-fw // 2 + qx} y = {fy + qy} }}
				textureFile = ""
				font = "loadscreen_tip"
				borderSize = {{ x = 0 y = 0 }}
				text = ""
				maxWidth = {qw}
				maxHeight = {qh}
				fixedsize = yes
				format = centre
				vertical_alignment = center
			}}
		}}
	}}
}}
"""


# Las definiciones de interface/load_screen.gfx del juego (1.20), tal cual: como pisamos el archivo,
# todo lo que el juego espera encontrar ahí tiene que seguir estando.
_VANILLA = """	spriteType = {
		name = "GFX_nullobject"
		texturefile = "gfx//interface//thisisdog.dds"
	}
	spriteType = {
		name = "GFX_frontend_dev_logo_s"
		texturefile = "gfx/interface/pdx_dev_logo_s.dds"
	}
	spriteType = {
		name = "GFX_loadingstatus_bg"
		texturefile = "gfx/interface/Loadingscreen_loadingstatus.dds"
	}
	spriteType = {
		name = "GFX_loadingtip_bg"
		texturefile = "gfx/interface/Loadingscreen_loadingtip.dds"
	}
	spriteType = {
		name = "GFX_pdx_int_logo"
		texturefile = "gfx/interface/pdx_int_logo.dds"
	}
	spriteType = {
		name = "GFX_clausewitz_logo"
		texturefile = "gfx/interface/clausewitz_logo.dds"
	}
	progressbartype = {
		name = "GFX_loadingstatus_progress"
		color = { 0.0 0.5 0.0 }
		colortwo = { 1.0 0.0 0.0 }
		textureFile1 = "gfx//interface//LoadingScreen_Progress_2.dds"
		textureFile2 = "gfx//interface//LoadingScreen_Progress_1.dds"
		size = { x = 934 y = 35 }
		effectFile = "gfx//FX//progress.lua"
		horizontal = yes
		steps = 1000000
	}
"""

VANILLA_SPRITES = ("GFX_nullobject", "GFX_frontend_dev_logo_s", "GFX_loadingstatus_bg", "GFX_loadingtip_bg",
                   "GFX_pdx_int_logo", "GFX_clausewitz_logo", "GFX_loadingstatus_progress")


def _gfx() -> str:
    bw, bh = G.BARRA
    return "spriteTypes = {\n" + _VANILLA + f"""\t# Meganations 2100: los marcos nuevos
	spriteType = {{
		name = "GFX_mn_carga_marco_estado"
		texturefile = "{DIR}/carga_marco_estado.dds"
		legacy_lazy_load = no
	}}
	spriteType = {{
		name = "GFX_mn_carga_marco_frase"
		texturefile = "{DIR}/carga_marco_frase.dds"
		legacy_lazy_load = no
	}}
	progressbartype = {{
		name = "GFX_mn_carga_progreso"
		color = {{ 1.0 1.0 1.0 }}
		colortwo = {{ 1.0 1.0 1.0 }}
		textureFile1 = "{DIR}/carga_barra_llena.dds"
		textureFile2 = "{DIR}/carga_barra_vacia.dds"
		size = {{ x = {bw} y = {bh} }}
		effectFile = "gfx/FX/progress.lua"
		horizontal = yes
		steps = 1000000
	}}
}}
"""


def emit(ctx: BuildContext) -> None:
    repo = ctx.spec.root.parent
    faltan = [p for p in G.PIEZAS if not (repo / "assets" / "menu" / "carga_marcos" / f"{p}.dds").exists()]
    if faltan:
        ctx.note(f"pantalla de carga: marcos del juego (faltan {len(faltan)} de {len(G.PIEZAS)} piezas: "
                 f"{', '.join(faltan)}; pedido en arte/pedidos_marcos_pantalla_carga.txt)")
        return
    for p in G.PIEZAS:
        ctx.copy_asset(f"assets/menu/carga_marcos/{p}.dds", f"{DIR}/{p}.dds")
    ctx.write_text("interface/load_screen.gfx", banner_for(SOURCE) + _gfx())
    ctx.write_text("interface/load_screen.gui", banner_for(SOURCE) + _gui())
    ctx.note("pantalla de carga: marcos nuevos (barra de arriba, barra de progreso y caja de la frase)")
