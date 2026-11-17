"""El panel del recurso propio de cada nación (2026-11-15).

Pedido: "Todo esto debería ir en un panel aparte como el del Líder, con su icono en la pantalla
de país principal y verse ahí, lo quiero con un diseño absolutamente original, bello y auténtico
para cada nación con un recurso único".

Cada nación tiene una ventana propia (scripted GUI, como la Ficha del Líder) con el arte que
llegó para ella (tools/arte/paneles.py -> assets/ui/paneles/<panel>/):
  - arriba, el nombre del panel;
  - a la izquierda, el instrumento del recurso (la cuba, el núcleo, el sol, la represa...): una
    tira de 21 cuadros del vacío al lleno; el cuadro lo elige MN_panel_cuadro (0 a 100 % del tope);
    debajo, el valor;
  - a la derecha, lo que explicaban los paneles de decisiones (con sus números en vivo), con
    barra de desplazamiento;
  - abajo, las acciones: las mismas decisiones de esas categorías, como botones (mismo costo,
    mismas condiciones, mismo efecto; la espera y el "una sola vez" con banderas propias).
Se abre con el botón del instrumento en miniatura en la pantalla de Política, al lado del botón
del Líder. Las decisiones de esas categorías quedan solo para la IA (como El Líder); las misiones
con reloj (los disturbios de la Unión) siguen en Decisiones, donde el juego las cuenta.

Sin probar en partida: la sintaxis sigue la de la Ficha y la de mods grandes, pero nadie abrió
todavía estas ventanas en el juego.
"""

from __future__ import annotations

from ..context import BuildContext
from ..pdx import Block, banner_for, render

SOURCE = "tools/gen/emitters/paneles.py (paneles del recurso propio, 2026-11-15)"
ARTE = "assets/ui/paneles"
TEX = "gfx/interface/meganations/paneles"
FLAG = "MN_panel_abierto"

# panel -> país, categorías de decisiones que absorbe, variable del medidor y su tope (número o variable)
PANELES = {
    "EFE": {"tag": "EFE", "categorias": ["EFE_biosteel_category"], "var": "EFE_biosteel", "max": 35,
            "nombre": ("The Bio-Steel Greenhouse", "El Invernadero del Bioacero"), "recurso": ("Bio-steel", "Bioacero")},
    "FCU": {"tag": "FCU", "categorias": ["FCU_dividendos_category", "FCU_directorio_category"], "var": "FCU_dividendos", "max": 100,
            "nombre": ("The Dividend Vault", "La Bóveda de los Dividendos"), "recurso": ("Dividends", "Dividendos")},
    "ASC": {"tag": "ASC", "categorias": ["ASC_computo_category", "ASC_plan_category"], "var": "ASC_computo", "max": 150,
            "nombre": ("The Core of the Plan", "El Núcleo del Plan"), "recurso": ("Compute", "Cómputo")},
    "HSN": {"tag": "HSN", "categorias": ["HSN_peaje_category", "HSN_nodos_category"], "var": "HSN_peaje", "max": 100,
            "nombre": ("The Toll Chamber", "La Cámara del Peaje"), "recurso": ("Toll", "Peaje")},
    "NAS": {"tag": "NAS", "categorias": ["NAS_inti_category"], "var": "NAS_inti", "max": "NAS_inti_max",
            "nombre": ("The Temple of Inti", "El Templo del Inti"), "recurso": ("Sacred light", "Luz sagrada")},
    "SHD": {"tag": "SHD", "categorias": ["SHD_mandato_category", "SHD_caudales_category"], "var": "SHD_mandato", "max": 100,
            "nombre": ("The Floodgate Hall", "La Sala de las Compuertas"), "recurso": ("Mandate of Heaven", "Mandato del Cielo")},
    "APF": {"tag": "APF", "categorias": ["APF_ubuntu_category"], "var": "APF_ubuntu", "max": 100,
            "nombre": ("The Ubuntu Circle", "El Círculo del Ubuntu"), "recurso": ("Ubuntu", "Ubuntu")},
    "NRE": {"tag": "NRE", "categorias": ["NRE_gloria_category", "NRE_legiones_category"], "var": "NRE_gloria", "max": 100,
            "nombre": ("The Tabularium of Glory", "El Tabulario de la Gloria"), "recurso": ("Glory", "Gloria")},
    "ZJP": {"tag": "ZJP", "categorias": ["ZJP_giri_category"], "var": "ZJP_giri", "max": 100,
            "nombre": ("The Book of Giri", "El Libro del Giri"), "recurso": ("Giri", "Giri")},
    "ZAL_pompa": {"tag": "ZAL", "ruta": 2, "categorias": ["ZAL_corona_category"], "var": "ZAL_pompa", "max": 100,
                  "nombre": ("The Hall of Pomp", "El Salón de la Pompa"), "recurso": ("Pomp", "Pompa")},
    "ZAL_sincronia": {"tag": "ZAL", "ruta": 1, "categorias": ["ZAL_red_category"], "var": "ZAL_sincronia", "max": 100,
                      "nombre": ("The London Node", "El Nodo de Londres"), "recurso": ("Synchrony", "Sincronía")},
}


def categorias() -> dict[str, str]:
    """Categoría de decisiones -> panel que la absorbe (la usa emitters/decisions.py)."""
    return {c: p for p, cfg in PANELES.items() for c in cfg["categorias"]}


def _quien(cfg: dict) -> str:
    s = f"original_tag = {cfg['tag']}"
    if cfg.get("ruta"):
        s += f" check_variable = {{ ZAL_ruta = {cfg['ruta']} }}"
    return s


def _cuerpo(b: Block | None) -> str:
    return " ".join(render(b).split()) if b is not None and b.entries else ""


def _arte_listo(ctx: BuildContext, panel: str) -> bool:
    base = ctx.spec.root.parent / ARTE / panel
    return all((base / f"{p}.dds").exists() for p in ("fondo", "medidor", "boton", "icono"))


def _estados(ctx: BuildContext) -> None:
    """2026-11-17 ("aca en ningun lado me dice donde tengo asignado el computo"): la prioridad del
    Cómputo de la Comuna en palabras, para el texto del panel ([ASC_prioridad_actual])."""
    prios = [("has_country_flag = ASC_prioridad_guerra", "GUERRA", "War", "la Guerra"),
             ("has_country_flag = ASC_prioridad_investigacion", "INVESTIGACION", "Research", "la Investigación"),
             ("has_country_flag = ASC_prioridad_logistica", "LOGISTICA", "Logistics", "la Logística"),
             ("always = yes", "ECONOMIA", "the Economy", "la Economía")]
    sl = ["defined_text = {\n\tname = ASC_prioridad_actual\n"]
    for recal in (True, False):
        for trig, clave, en, es in prios:
            k = f"ASC_PRIORIDAD_{clave}" + ("_RECAL" if recal else "")
            cond = ("has_country_flag = ASC_reasignando " if recal else "") + trig
            sl.append(f"\ttext = {{ trigger = {{ {cond} }} localization_key = {k} }}\n")
            ctx.loc.define_and_reference(
                k, en=f"§Y{en}§!" + (" (recalibrating: no bonus for up to 30 days)" if recal else ""),
                es=f"§Y{es}§!" + (" (recalibrando: sin bonus hasta 30 días)" if recal else ""),
                file="meganations_paneles", origin="paneles")
    sl.append("}\n")
    # 2026-11-17: el humor de las Cuatro de la Unión (tools/gen/cuatro_spec.py), en palabras, y el registro
    corps = ctx.spec.raw.get("cuatro_corps") or []
    palabras = [(80, "SOCIA", "§GPartner§!", "§GSocia§!"), (50, "CONFORME", "Content", "Conforme"),
                (25, "MOLESTA", "§YAnnoyed§!", "§YMolesta§!"), (0, "HOSTIL", "§RHostile§!", "§RHostil§!")]
    for _v, k, en, es in palabras:
        ctx.loc.define_and_reference(f"FCU_HUMOR_{k}", en=en, es=es, file="meganations_paneles", origin="paneles")
    for c in corps:
        sl.append(f"defined_text = {{\n\tname = FCU_humor_palabra_{c}\n")
        for v, k, _en, _es in palabras[:-1]:
            sl.append(f"\ttext = {{ trigger = {{ check_variable = {{ FCU_humor_{c} > {v - 1} }} }} localization_key = FCU_HUMOR_{k} }}\n")
        sl.append("\ttext = { localization_key = FCU_HUMOR_HOSTIL }\n}\n")
    razones = ctx.spec.raw.get("cuatro_razones") or []
    if razones:
        ctx.loc.define_and_reference("FCU_RAZON_0", en="-", es="-", file="meganations_paneles", origin="paneles")
        for code, en, es in razones:
            ctx.loc.define_and_reference(f"FCU_RAZON_{code}", en=en, es=es, file="meganations_paneles", origin="paneles")
        for i in (1, 2, 3):
            sl.append(f"defined_text = {{\n\tname = FCU_razon_txt_{i}\n")
            for code, _en, _es in razones:
                sl.append(f"\ttext = {{ trigger = {{ check_variable = {{ FCU_razon_{i} = {code} }} }} localization_key = FCU_RAZON_{code} }}\n")
            sl.append("\ttext = { localization_key = FCU_RAZON_0 }\n}\n")
    ctx.write_text("common/scripted_localisation/meganations_paneles_estado.txt", banner_for(SOURCE) + "".join(sl))


def emit(ctx: BuildContext) -> None:
    _estados(ctx)
    acciones: dict = ctx.data.get("paneles_acciones") or {}
    if not acciones:
        return
    from tools.arte import paneles as arte
    hay = [p for p in PANELES if _arte_listo(ctx, p) and any(c in acciones for c in PANELES[p]["categorias"])]
    if not hay:
        return
    W, H = arte.VENTANA
    gfx, gui, sg, se, loc_hechas = ["spriteTypes = {\n"], ["guiTypes = {\n"], ["scripted_gui = {\n"], [], 0
    # -- el cuadro del medidor (0 a 20, +1: los cuadros del juego empiezan en 1) --
    se.append("MN_panel_actualizar = {\n")
    for p in hay:
        cfg = PANELES[p]
        tope = cfg["max"]
        se.append(f"\tif = {{ limit = {{ {_quien(cfg)} }}\n"
                  f"\t\tset_variable = {{ MN_panel_cuadro = {cfg['var']} }}\n"
                  "\t\tmultiply_variable = { MN_panel_cuadro = 20 }\n"
                  + (f"\t\tif = {{ limit = {{ check_variable = {{ {tope} > 0 }} }} divide_variable = {{ MN_panel_cuadro = {tope} }} }}\n"
                     if isinstance(tope, str) else f"\t\tdivide_variable = {{ MN_panel_cuadro = {tope} }}\n")
                  + "\t\tround_variable = MN_panel_cuadro\n"
                  "\t\tclamp_variable = { var = MN_panel_cuadro min = 0 max = 20 }\n"
                  "\t\tadd_to_variable = { MN_panel_cuadro = 1 }\n\t}\n")
    se.append("}\n")
    # -- el botón en Política: el instrumento en miniatura, al lado del botón del Líder --
    from .politica_gui import posicion_ficha
    fx, fy, flado = posicion_ficha()
    ix, iy = arte.ICONO
    gui.append('\tcontainerWindowType = {\n\t\tname = "mn_panel_politica_window"\n'
               f'\t\tposition = {{ x = {fx + 200} y = {fy + (flado - iy) // 2} }}\n'
               f'\t\tsize = {{ width = {ix} height = {iy} }}\n\t\torientation = upper_left\n')
    for p in hay:
        gui.append(f'\t\tbuttonType = {{\n\t\t\tname = "abrir_{p}"\n\t\t\tposition = {{ x = 0 y = 0 }}\n'
                   f'\t\t\tspriteType = "GFX_mn_panel_{p}_icono"\n\t\t\tpdx_tooltip = "MN_PANEL_BOTON_TT_{p}"\n\t\t}}\n')
    gui.append("\t}\n")
    quien_alguno = " ".join(f"AND = {{ {_quien(PANELES[p])} }}" for p in hay)
    sg.append("\tmn_panel_politica = {\n\t\tcontext_type = player_context\n\t\tparent_window_token = politics_tab\n"
              '\t\twindow_name = "mn_panel_politica_window"\n'
              f"\t\tvisible = {{ OR = {{ {quien_alguno} }} }}\n\t\teffects = {{\n")
    for p in hay:
        sg.append(f"\t\t\tabrir_{p}_click = {{ if = {{ limit = {{ has_country_flag = {FLAG} }} clr_country_flag = {FLAG} }} "
                  f"else = {{ set_country_flag = {FLAG} MN_panel_actualizar = yes }} }}\n")
    sg.append("\t\t}\n\t\ttriggers = {\n")
    for p in hay:
        sg.append(f"\t\t\tabrir_{p}_visible = {{ {_quien(PANELES[p])} }}\n")
    sg.append("\t\t}\n\t\tai_enabled = { always = no }\n\t}\n")

    for p in hay:
        cfg = PANELES[p]
        z = arte.ZONAS[p]
        bw, bh = arte.boton_tamano(p)
        for pieza, cuadros in (("fondo", 1), ("medidor", arte.CUADROS), ("boton", 1), ("icono", 1)):
            ctx.copy_asset(f"{ARTE}/{p}/{pieza}.dds", f"{TEX}/{p}/{pieza}.dds")
            gfx.append(f'\tspriteType = {{\n\t\tname = "GFX_mn_panel_{p}_{pieza}"\n\t\ttexturefile = "{TEX}/{p}/{pieza}.dds"\n'
                       + (f"\t\tnoOfFrames = {cuadros}\n" if cuadros > 1 else "")
                       + ('\t\teffectFile = "gfx/FX/buttonstate.lua"\n' if pieza in ("boton", "icono") else "")
                       + "\t}\n")
        # -- textos --
        en_n, es_n = cfg["nombre"]
        en_r, es_r = cfg["recurso"]
        tope = cfg["max"]
        tope_txt = f"[?{tope}|0]" if isinstance(tope, str) else str(tope)
        defs = {
            f"MN_PANEL_TITULO_{p}": (en_n.upper(), es_n.upper()),
            f"MN_PANEL_BOTON_TT_{p}": (f"§Y{en_n}§!\n{en_r}: [?{cfg['var']}|0] / {tope_txt}. Open the panel.",
                                       f"§Y{es_n}§!\n{es_r}: [?{cfg['var']}|0] / {tope_txt}. Abrir el panel."),
            f"MN_PANEL_VALOR_{p}": (f"§Y{en_r}§!  [?{cfg['var']}|0] / {tope_txt}", f"§Y{es_r}§!  [?{cfg['var']}|0] / {tope_txt}"),
            f"MN_PANEL_TEXTO_{p}": tuple("\n\n".join(f"§Y${c}$§!\n${c}_desc$" for c in cfg["categorias"] if c in acciones)
                                         for _ in (0, 1)),
        }
        for clave, (en, es) in defs.items():
            # el salto de línea va escrito (\\n): uno de verdad se vuelve espacio en el .yml
            en, es = en.replace("\n", "\\n"), es.replace("\n", "\\n")
            ctx.loc.define_and_reference(clave, en=en, es=es, file="meganations_paneles", origin="paneles")
            loc_hechas += 1
        # -- la ventana --
        g = [f'\tcontainerWindowType = {{\n\t\tname = "mn_panel_{p}_window"\n'
             f'\t\tposition = {{ x = {-W // 2} y = {-H // 2} }}\n\t\tsize = {{ width = {W} height = {H} }}\n'
             '\t\torientation = center\n\t\tmoveable = yes\n'
             f'\t\ticonType = {{\n\t\t\tname = "fondo"\n\t\t\tspriteType = "GFX_mn_panel_{p}_fondo"\n\t\t\tposition = {{ x = 0 y = 0 }}\n\t\t}}\n']
        tx0, ty0, tx1, ty1 = z["texto"]
        if z["titulo"]:
            t0, t1, t2, t3 = z["titulo"]
        else:   # sin franja: el título encabeza la zona del texto
            t0, t1, t2, t3 = tx0, ty0, tx1, ty0 + 34
            ty0 += 36
        g.append(_texto("titulo", t0 + 8, t1 + (t3 - t1 - 28) // 2, f"MN_PANEL_TITULO_{p}", "hoi_24header", t2 - t0 - 16, 30, "centre"))
        g.append(f'\t\tbuttonType = {{\n\t\t\tname = "cerrar"\n\t\t\tposition = {{ x = {W - 46} y = 8 }}\n'
                 '\t\t\tspriteType = "GFX_closebutton"\n\t\t\tshortcut = "ESCAPE"\n\t\t}\n')
        # el instrumento
        mx0, my0, mx1, my1 = z["medidor"]
        lado = min(mx1 - mx0 - 8, my1 - my0 - 40)
        escala = round(lado / arte.LADO, 3)
        g.append(f'\t\ticonType = {{\n\t\t\tname = "medidor"\n\t\t\tspriteType = "GFX_mn_panel_{p}_medidor"\n'
                 f'\t\t\tposition = {{ x = {mx0 + (mx1 - mx0 - lado) // 2} y = {my0 + 4} }}\n\t\t\tscale = {escala}\n'
                 f'\t\t\tpdx_tooltip = "MN_PANEL_BOTON_TT_{p}"\n\t\t}}\n')
        g.append(_texto("valor", mx0 + 10, my1 - 30, f"MN_PANEL_VALOR_{p}", "hoi_18mbs", mx1 - mx0 - 20, 24, "centre"))
        # el texto, con barra de desplazamiento (2026-11-15, captura: el texto y los botones se salían
        # del marco): como las listas del juego, el contenedor con barra lleva fondo (transparente),
        # recorta (clipping) y adentro un contenedor del alto del contenido
        tw, th = tx1 - tx0 - 14, ty1 - ty0 - 12
        alto_texto = _alto_texto(ctx, cfg["categorias"], tw - 30)
        g.append(_caja_con_barra("texto_caja", tx0 + 8, ty0 + 6, tw, th, alto_texto,
                                 _texto("texto", 0, 0, f"MN_PANEL_TEXTO_{p}", "hoi_16mbs", tw - 30, alto_texto, "left",
                                        tab="\t\t\t\t")))
        # las acciones, en dos columnas: primero las que se ven siempre, al final las que aparecen
        # solo a veces (restaurar una productora...), así sus huecos quedan abajo
        ax0, ay0, ax1, ay1 = z["acciones"]
        lista = [a for c in cfg["categorias"] for a in acciones.get(c, [])]
        lista.sort(key=lambda a: bool(a.get("visible") is not None and a["visible"].entries) or bool(a.get("una_vez")))
        aw, ah = ax1 - ax0 - 12, ay1 - ay0 - 12
        filas = (len(lista) + 1) // 2
        botones = []
        for k, a in enumerate(lista):
            x, y = (k % 2) * (bw + 6), (k // 2) * arte.PASO_ACCION
            botones.append(f'\t\t\t\tbuttonType = {{\n\t\t\t\t\tname = "a_{a["id"]}"\n\t\t\t\t\tposition = {{ x = {x} y = {y} }}\n'
                           f'\t\t\t\t\tspriteType = "GFX_mn_panel_{p}_boton"\n\t\t\t\t\ttext = "MN_PANEL_ACC_{a["id"]}"\n'
                           f'\t\t\t\t\tbuttonFont = "hoi_16mbs"\n\t\t\t\t\tpdx_tooltip = "{a["id"]}_desc"\n\t\t\t\t}}\n')
            en, es = a["nombre"]
            costo = int(a.get("costo") or 0)
            if costo:
                en, es = f"{en}  ({costo} PP)", f"{es}  ({costo} PP)"
            ctx.loc.define_and_reference(f"MN_PANEL_ACC_{a['id']}", en=en, es=es, file="meganations_paneles", origin="paneles")
        g.append(_caja_con_barra("acciones", ax0 + 6, ay0 + 6, aw, ah, max(ah, filas * arte.PASO_ACCION), "".join(botones)))
        g.append("\t}\n")
        gui.append("".join(g))
        # -- su scripted GUI --
        s = [f"\tmn_panel_{p} = {{\n\t\tcontext_type = player_context\n\t\twindow_name = \"mn_panel_{p}_window\"\n"
             f"\t\tvisible = {{ {_quien(cfg)} has_country_flag = {FLAG} }}\n\t\teffects = {{\n"
             f"\t\t\tcerrar_click = {{ clr_country_flag = {FLAG} }}\n"]
        t = [f"\t\ttriggers = {{\n"]
        for a in lista:
            did, costo = a["id"], int(a.get("costo") or 0)
            pago = f"add_political_power = -{costo} " if costo else ""
            espera = (f"set_country_flag = {{ flag = MN_pcd_{did} value = 1 days = {int(a['espera'])} }} " if a.get("espera") else "")
            unica = f"set_country_flag = MN_phecho_{did} " if a.get("una_vez") else ""
            s.append(f"\t\t\ta_{did}_click = {{ {pago}{espera}{unica}{_cuerpo(a['efectos'])} MN_panel_actualizar = yes }}\n")
            ve = _cuerpo(a.get("visible"))
            if a.get("una_vez"):
                ve += f" NOT = {{ has_country_flag = MN_phecho_{did} }}"
            if ve.strip():
                t.append(f"\t\t\ta_{did}_visible = {{ {ve.strip()} }}\n")
            en = _cuerpo(a.get("disponible"))
            if costo:
                en += f" has_political_power > {costo - 1}"
            if a.get("espera"):
                en += f" NOT = {{ has_country_flag = MN_pcd_{did} }}"
            if en.strip():
                t.append(f"\t\t\ta_{did}_click_enabled = {{ {en.strip()} }}\n")
        s.append("\t\t}\n\t\tproperties = {\n\t\t\tmedidor = { frame = MN_panel_cuadro }\n\t\t}\n")
        s += t
        s.append("\t\t}\n\t\tai_enabled = { always = no }\n\t}\n")
        sg.append("".join(s))
    gfx.append("}\n")
    gui.append("}\n")
    sg.append("}\n")
    ctx.write_text("interface/meganations_paneles.gfx", banner_for(SOURCE) + "".join(gfx))
    ctx.write_text("interface/meganations_paneles.gui", banner_for(SOURCE) + "".join(gui))
    ctx.write_text("common/scripted_guis/meganations_paneles.txt", banner_for(SOURCE) + "".join(sg))
    ctx.write_text("common/scripted_effects/meganations_paneles.txt", banner_for(SOURCE) + "".join(se))
    # con el panel abierto, el medidor se pone al día cada mes
    ctx.write_text("common/on_actions/09_meganations_paneles.txt", banner_for(SOURCE)
                   + "on_actions = {\n\ton_monthly = {\n\t\teffect = {\n"
                   f"\t\t\tif = {{ limit = {{ has_country_flag = {FLAG} }} MN_panel_actualizar = yes }}\n"
                   "\t\t}\n\t}\n}\n")
    n = sum(len(acciones.get(c, [])) for p in hay for c in PANELES[p]["categorias"])
    ctx.note(f"paneles del recurso: {len(hay)} ventanas propias ({', '.join(hay)}), {n} acciones como botones")


def _caja_con_barra(nombre: str, x: int, y: int, w: int, h: int, alto: int, hijos: str) -> str:
    """Contenedor con barra de desplazamiento como los del juego: fondo, recorte y un contenedor
    interior del alto del contenido."""
    return (f'\t\tcontainerWindowType = {{\n\t\t\tname = "{nombre}"\n\t\t\tposition = {{ x = {x} y = {y} }}\n'
            f'\t\t\tsize = {{ width = {w} height = {h} }}\n\t\t\tclipping = yes\n'
            '\t\t\tverticalScrollbar = "right_vertical_slider"\n\t\t\tscroll_wheel_factor = 40\n\t\t\tsmooth_scrolling = yes\n'
            '\t\t\tbackground = {\n\t\t\t\tname = "Background"\n\t\t\t\tspriteType = "GFX_tiled_window_transparent"\n\t\t\t}\n'
            f'\t\t\tcontainerWindowType = {{\n\t\t\t\tname = "{nombre}_contenido"\n\t\t\t\tposition = {{ x = 0 y = 0 }}\n'
            f'\t\t\t\tsize = {{ width = {w - 24} height = {alto} }}\n'
            + hijos + "\t\t\t}\n\t\t}\n")


def _alto_texto(ctx: BuildContext, categorias: list[str], ancho: int) -> int:
    """Alto aproximado del texto del panel (letra de 16: ~7 px por letra, 19 por renglón), con margen."""
    import math
    cats = {c["id"]: c for c in (ctx.spec.raw.get("decisions") or {}).get("categories") or []}
    renglones = 0
    por_renglon = max(20, ancho // 7)
    for cid in categorias:
        texto = str(((cats.get(cid) or {}).get("desc") or {}).get("spanish", ""))
        for parrafo in texto.replace("\\n", "\n").split("\n"):
            renglones += max(1, math.ceil(len(parrafo) / por_renglon))
        renglones += 2
    return renglones * 19 + 40


def _texto(nombre: str, x: int, y: int, texto: str, font: str, w: int, h: int, fmt: str = "left",
           fijo: bool = True, tab: str = "\t\t") -> str:
    return (f'{tab}instantTextBoxType = {{\n{tab}\tname = "{nombre}"\n{tab}\tposition = {{ x = {x} y = {y} }}\n'
            f'{tab}\tfont = "{font}"\n{tab}\ttext = "{texto}"\n{tab}\tmaxWidth = {w}\n{tab}\tmaxHeight = {h}\n'
            f'{tab}\tformat = {fmt}\n' + (f"{tab}\tfixedsize = yes\n" if fijo else "") + f"{tab}}}\n")
