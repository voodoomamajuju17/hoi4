"""La Ficha del Líder (2026-11-03): ventana propia en cristal y cobre.

Pedido del usuario, sobre la maqueta aprobada: "cristal y cobre de base con
marcos por facción", "también rediseñar las pantallas del juego", "Excelente
mockup. Me encanta [...] lo demás dale para adelante".

Es una ventana del mod (scripted GUI), no una pantalla del juego retocada: el
juego la dibuja encima del mapa cuando el país tiene la bandera
MEGANATIONS_ficha_abierta. Se abre con el botón hexagonal que se cuelga de la
barra superior (parent_window_token = top_bar, como hace Kaiserreich con la
popularidad del partido). Desde el 2026-11-03 el Chequeo y la Gira también
están acá, como botones; el panel El Líder de Decisiones queda solo para la IA.

Muestra lo que arma 27_lider_ck / 14_decisions (MEGANATIONS_lider_*):
  - el retrato del líder (cada líder detectado tiene su número,
    MEGANATIONS_lider_id; la imagen se elige con localización con guion,
    "[MN_ficha_retrato]", como Kaiserreich elige el ícono de ideología);
  - Carisma, Astucia y Prestigio en barras de 20 segmentos: en cobre lo del
    líder, en turquesa lo que suman los ministros (dos imágenes de 21 cuadros
    una encima de la otra; el cuadro lo elige una variable, como hace
    Equestria at War con sus medidores);
  - la Salud en un anillo de 21 cuadros (de a 5 puntos) y cuánto baja por año;
  - lo que pesa hoy: estabilidad, poder político y apoyo a la guerra;
  - el gabinete posible del país, con lo que suma o resta cada ministro;
    encendido el que está en el gobierno, apagado el que no (bandera
    MEGANATIONS_gabinete_<n> que ponen y sacan los propios ministros).
  - un marco por facción encima (EFE enredadera dorada, FCU cromo, ASC cuña
    roja, Albión bronce y vino, Japón laca y neón); el resto, cobre solo.

El arte lo dibuja tools/arte/ficha.py (con Pillow, una vez) en
assets/ui/ficha/; este emisor solo lo copia. Las medidas de todo están en
DISENO, que usan los dos.

Sin probar en partida: las piezas siguen la sintaxis de mods grandes
(Kaiserreich, Millennium Dawn, Equestria at War), pero nadie abrió todavía la
ventana en el juego.
"""

from __future__ import annotations

from ..context import BuildContext
from ..pdx import banner_for

SOURCE = "tools/gen/emitters/ficha_lider.py (maqueta aprobada 2026-11-03)"

ARTE = ("assets", "ui", "ficha")
TEX = "gfx/interface/meganations/ficha"

# Medidas de la ventana (las usa también tools/arte/ficha.py para dibujar)
DISENO = {
    "ventana": (1020, 740),
    "cabecera": 64,
    "retrato": (44, 94),            # 156 x 210, el retrato del juego
    "retrato_marco": (36, 86, 172, 226),
    "placa": (24, 312, 236, 382),   # la placa del nombre debajo del retrato
    "stats_x": 260, "stats_y": (110, 162, 214), "barra": (410, 300, 14),
    "anillo": (850, 96, 140),
    "secciones": {"atributos": 84, "pesa": 290, "gabinete": 432},
    "efectos_y": 312, "efectos_x": (260, 510, 760), "efecto": (230, 56),
    "gabinete": (36, 452, 5, 2, 182, 104, 8, 8),   # x, y, columnas, filas, ancho, alto, separación x, y
    "accion": (210, 30),   # botones Chequeo y Gira, abajo a la derecha (2026-11-03)
    "boton": 36,   # del alto de los botones de la barra (2026-11-03)
}
SEGMENTOS = 20
CUADROS_SALUD = 21

ESTILOS_POR_DEFECTO = {"EFE": "efe", "FCU": "fcu", "ASC": "asc", "ZAL": "zal", "ZJP": "zjp"}
ESTILOS = ("base", "efe", "fcu", "asc", "zal", "zjp")
PIEZAS = ["fondo", "retrato_marco", "barra_total", "barra_base", "salud", "boton", "boton_accion", "carta",
          "apagado", "sin_retrato"] + [f"marco_{e}" for e in ESTILOS]
CUADROS = {"barra_total": SEGMENTOS + 1, "barra_base": SEGMENTOS + 1, "salud": CUADROS_SALUD}

STATS = (("carisma", "car"), ("astucia", "ast"), ("prestigio", "pre"))


def config(ctx: BuildContext) -> dict:
    return (ctx.spec.raw.get("scenario") or {}).get("ficha_lider") or {}


def paises(ctx: BuildContext) -> list[str]:
    cats = [c for c in (ctx.spec.raw.get("decisions") or {}).get("categories") or []
            if c.get("id") == "MEGANATIONS_lider_category"]
    tags = config(ctx).get("countries") or (cats[0].get("country") if cats else [])
    return [t for t in tags if ctx.spec.country(t) is not None] if tags else []


def gabinete(ctx: BuildContext) -> dict[str, list[str]]:
    """País -> sus ministros con stats (27/31 lider_ck.ministros), en orden.
    El lugar en la lista es el número de su casilla en la ficha."""
    from .characters import defined_characters
    ministros = (ctx.spec.raw.get("lider_ck") or {}).get("ministros") or {}
    pais = {ch["id"]: ch["country"] for ch in defined_characters(ctx)}
    out: dict[str, list[str]] = {}
    for cid in ministros:
        tag = pais.get(cid)
        if tag:
            out.setdefault(tag, []).append(cid)
    return out


def casilla(ctx: BuildContext, cid: str) -> int | None:
    for lista in gabinete(ctx).values():
        if cid in lista:
            return lista.index(cid) + 1
    return None


def lideres(ctx: BuildContext) -> list[tuple[int, str]]:
    """(MEGANATIONS_lider_id, personaje) de MEGANATIONS_lider_detectar."""
    efectos = (ctx.spec.raw.get("decisions") or {}).get("scripted_effects") or []
    det = [e for e in efectos if e.get("id") == "MEGANATIONS_lider_detectar"]
    out = []
    for item in (det[0].get("effects") if det else []) or []:
        cond = (item.get("when") or {}).get("all") or []
        quien = next((c["leader_is"] for c in cond if isinstance(c, dict) and "leader_is" in c), None)
        num = next((x.get("value") for x in item.get("then") or []
                    if isinstance(x, dict) and x.get("var") == "MEGANATIONS_lider_id"), None)
        if quien and isinstance(num, int) and num > 0:
            out.append((num, quien))
    return out


def _tags_or(tags: list[str]) -> str:
    if len(tags) == 1:
        return f"tag = {tags[0]}"
    return "OR = { " + " ".join(f"tag = {t}" for t in tags) + " }"


def _sprite(name: str, tex: str, frames: int = 1) -> str:
    extra = f"\n\t\tnoOfFrames = {frames}" if frames > 1 else ""
    return f'\tspriteType = {{\n\t\tname = "{name}"\n\t\ttexturefile = "{tex}"{extra}\n\t}}\n'


def emit(ctx: BuildContext) -> None:
    tags = paises(ctx)
    if not tags:
        return
    repo = ctx.spec.root.parent
    base = repo.joinpath(*ARTE)
    faltan = [p for p in PIEZAS if not (base / f"{p}.dds").exists()]
    if faltan:
        ctx.warn(f"ficha del líder: falta el arte {', '.join(faltan)} (tools/arte/ficha.py); no se arma la ventana")
        return
    for p in PIEZAS:
        ctx.copy_asset(f"{'/'.join(ARTE)}/{p}.dds", f"{TEX}/{p}.dds")

    cfg = config(ctx)
    estilos = {**ESTILOS_POR_DEFECTO, **(cfg.get("styles") or {})}
    retratos: dict[str, str] = ctx.data.get("retratos") or {}
    gab = {t: l for t, l in gabinete(ctx).items() if t in tags}
    max_min = max((len(l) for l in gab.values()), default=0)
    cols, filas = DISENO["gabinete"][2], DISENO["gabinete"][3]
    if max_min > cols * filas:
        ctx.warn(f"ficha del líder: hay países con {max_min} ministros y la ficha tiene {cols * filas} casillas")
        max_min = cols * filas

    # -- sprites ------------------------------------------------------------
    gfx = ["spriteTypes = {\n"]
    for p in PIEZAS:
        gfx.append(_sprite(f"GFX_mn_ficha_{p}", f"{TEX}/{p}.dds", CUADROS.get(p, 1)))
    lid = lideres(ctx)
    for num, cid in lid:
        if cid in retratos:
            gfx.append(_sprite(f"GFX_mn_lider_{num}", retratos[cid]))
    for lista in gab.values():
        for cid in lista[:max_min]:
            if cid in retratos:
                gfx.append(_sprite(f"GFX_mn_min_{cid}", retratos[cid]))
    gfx.append("}\n")
    ctx.write_text("interface/meganations_ficha.gfx", banner_for(SOURCE) + "".join(gfx))

    # -- textos con guion (qué imagen y qué nombre va en cada lugar) -------
    sl = []
    sl.append("defined_text = {\n\tname = MN_ficha_retrato\n")
    for num, cid in lid:
        if cid in retratos:
            sl.append(f"\ttext = {{ trigger = {{ check_variable = {{ MEGANATIONS_lider_id = {num} }} }} "
                      f"localization_key = GFX_mn_lider_{num} }}\n")
    sl.append("\ttext = { localization_key = GFX_mn_ficha_sin_retrato }\n}\n")
    sl.append("defined_text = {\n\tname = MN_ficha_marco\n")
    for tag in tags:
        e = estilos.get(tag, "base")
        if e != "base" and e in ESTILOS:
            sl.append(f"\ttext = {{ trigger = {{ tag = {tag} }} localization_key = GFX_mn_ficha_marco_{e} }}\n")
    sl.append("\ttext = { localization_key = GFX_mn_ficha_marco_base }\n}\n")
    ministros = (ctx.spec.raw.get("lider_ck") or {}).get("ministros") or {}
    for k in range(1, max_min + 1):
        for que in ("retrato", "nombre", "bono"):
            sl.append(f"defined_text = {{\n\tname = MN_min_{que}_{k}\n")
            for tag, lista in gab.items():
                if len(lista) < k:
                    continue
                cid = lista[k - 1]
                if que == "retrato":
                    clave = f"GFX_mn_min_{cid}" if cid in retratos else "GFX_mn_ficha_sin_retrato"
                elif que == "nombre":
                    clave = ctx.loc.reference(cid, f"ficha:{cid}")
                else:
                    clave = f"MN_FICHA_BONO_{cid}"
                sl.append(f"\ttext = {{ trigger = {{ tag = {tag} }} localization_key = {clave} }}\n")
            sl.append("}\n")
    for lista in gab.values():
        for cid in lista[:max_min]:
            en, es = _bono(ministros.get(cid) or {})
            ctx.loc.define_and_reference(f"MN_FICHA_BONO_{cid}", en=en, es=es, file="meganations_ficha", origin="ficha")
    ctx.write_text("common/scripted_localisation/meganations_ficha.txt", banner_for(SOURCE) + "".join(sl))
    # los nombres de imagen que devuelven los textos con guion también existen
    # como texto (igual a sí mismos), así el juego no avisa "falta la clave"
    import re
    for clave in sorted(set(re.findall(r"localization_key = (GFX_\w+)", "".join(sl)))):
        ctx.loc.define_and_reference(clave, en=clave, es=clave, file="meganations_ficha", origin="ficha")

    # -- variables que lee la ventana (cuadro de cada barra, efectos en %) --
    se = ["MEGANATIONS_ficha_actualizar = {\n"]
    for stat, c in STATS:
        tot, bas = f"MEGANATIONS_gui_{c}_total", f"MEGANATIONS_gui_{c}_base"
        se.append(f"\tset_variable = {{ {tot} = MEGANATIONS_lider_total_{stat} }}\n"
                  f"\tadd_to_variable = {{ {tot} = 1 }}\n"
                  f"\tset_variable = {{ {bas} = MEGANATIONS_lider_{stat} }}\n"
                  f"\tif = {{ limit = {{ check_variable = {{ MEGANATIONS_lider_{stat} > MEGANATIONS_lider_total_{stat} }} }} "
                  f"set_variable = {{ {bas} = MEGANATIONS_lider_total_{stat} }} }}\n"
                  f"\tadd_to_variable = {{ {bas} = 1 }}\n")
    se.append("\tset_variable = { MEGANATIONS_gui_salud = MEGANATIONS_lider_total_salud }\n"
              "\tdivide_variable = { MEGANATIONS_gui_salud = 5 }\n"
              "\tround_variable = MEGANATIONS_gui_salud\n"
              "\tadd_to_variable = { MEGANATIONS_gui_salud = 1 }\n"
              "\tclamp_variable = { var = MEGANATIONS_gui_salud min = 1 max = 21 }\n"
              "\tset_variable = { MEGANATIONS_gui_estabilidad = MEGANATIONS_lider_ef_carisma }\n"
              "\tmultiply_variable = { MEGANATIONS_gui_estabilidad = 100 }\n"
              "\tset_variable = { MEGANATIONS_gui_guerra = MEGANATIONS_lider_ef_prestigio }\n"
              "\tmultiply_variable = { MEGANATIONS_gui_guerra = 100 }\n"
              "}\n")
    ctx.write_text("common/scripted_effects/meganations_ficha.txt", banner_for(SOURCE) + "".join(se))

    # -- la ventana ---------------------------------------------------------
    ctx.write_text("interface/meganations_ficha.gui", banner_for(SOURCE) + _gui(max_min, cfg))
    ctx.write_text("common/scripted_guis/meganations_ficha.txt",
                   banner_for(SOURCE) + _scripted_gui(tags, gab, max_min))
    _textos(ctx)
    ctx.note(f"ficha del líder: ventana propia para {len(tags)} países, {len(lid)} retratos de líder, "
             f"gabinete de hasta {max_min} ministros")


def _bono(cambios: dict) -> tuple[str, str]:
    abrev = {"carisma": ("CHA", "CAR"), "astucia": ("CUN", "AST"), "prestigio": ("PRE", "PRE"), "salud": ("HEA", "SAL")}
    en, es = [], []
    for stat in ("carisma", "astucia", "prestigio", "salud"):
        v = cambios.get(stat)
        if not v:
            continue
        color = "G" if v > 0 else "R"
        signo = f"+{v}" if v > 0 else f"-{abs(v)}"
        en.append(f"§{color}{signo} {abrev[stat][0]}§!")
        es.append(f"§{color}{signo} {abrev[stat][1]}§!")
    return ("  ".join(en) or "—", "  ".join(es) or "—")


def _icon(name: str, x: int, y: int, sprite: str | None = None, extra: str = "") -> str:
    sp = f'\n\t\t\tspriteType = "{sprite}"' if sprite else ""
    return (f'\t\ticonType = {{\n\t\t\tname = "{name}"{sp}\n\t\t\tposition = {{ x = {x} y = {y} }}{extra}\n\t\t}}\n')


def _text(name: str, x: int, y: int, text: str, font: str, w: int, h: int, fmt: str = "left") -> str:
    return (f'\t\tinstantTextBoxType = {{\n\t\t\tname = "{name}"\n\t\t\tposition = {{ x = {x} y = {y} }}\n'
            f'\t\t\tfont = "{font}"\n\t\t\ttext = "{text}"\n\t\t\tmaxWidth = {w}\n\t\t\tmaxHeight = {h}\n'
            f'\t\t\tformat = {fmt}\n\t\t\tfixedsize = yes\n\t\t}}\n')


def _gui(max_min: int, cfg: dict) -> str:
    W, H = DISENO["ventana"]
    g = ["guiTypes = {\n"]
    # botón de la barra superior
    b = cfg.get("button") or {}
    g.append('\tcontainerWindowType = {\n\t\tname = "mn_ficha_boton_window"\n'
             f'\t\tposition = {{ x = {int(b.get("x", 6))} y = {int(b.get("y", 112))} }}\n'
             f'\t\tsize = {{ width = {DISENO["boton"]} height = {DISENO["boton"]} }}\n'
             f'\t\torientation = {b.get("orientation", "upper_left")}\n'
             '\t\tbuttonType = {\n\t\t\tname = "abrir"\n\t\t\tposition = { x = 0 y = 0 }\n'
             '\t\t\tspriteType = "GFX_mn_ficha_boton"\n\t\t\tpdx_tooltip = "MN_FICHA_BOTON_TT"\n\t\t}\n\t}\n')
    # la ficha
    g.append('\tcontainerWindowType = {\n\t\tname = "mn_ficha_lider_window"\n'
             f'\t\tposition = {{ x = {-W // 2} y = {-H // 2} }}\n\t\tsize = {{ width = {W} height = {H} }}\n'
             '\t\torientation = center\n\t\tmoveable = yes\n')
    g.append(_icon("fondo", 0, 0, "GFX_mn_ficha_fondo"))
    # el marco de la facción va en los bordes: encima del fondo, debajo de todo lo demás
    g.append(_icon("marco_faccion", 0, 0, "GFX_mn_ficha_marco_base", "\n\t\t\talwaystransparent = yes"))
    rx, ry = DISENO["retrato"]
    g.append(_icon("retrato", rx, ry, "GFX_mn_ficha_sin_retrato"))
    mx, my, _, _ = DISENO["retrato_marco"]
    g.append(_icon("retrato_marco", mx, my, "GFX_mn_ficha_retrato_marco"))
    g.append(_text("titulo", 70, 14, "MN_FICHA_TITULO", "hoi_36header", 400, 40))
    g.append(_text("pais", W - 520, 22, "[Root.GetName]", "hoi_18mbs", 420, 24, "right"))
    g.append('\t\tbuttonType = {\n\t\t\tname = "cerrar"\n\t\t\tposition = { x = %d y = 14 }\n'
             '\t\t\tspriteType = "GFX_closebutton"\n\t\t\tshortcut = "ESCAPE"\n\t\t}\n' % (W - 84))
    px0, py0, px1, py1 = DISENO["placa"]
    g.append(_text("nombre", px0 + 14, py0 + 8, "[Root.GetLeader]", "hoi_24header", px1 - px0 - 28, py1 - py0 - 12, "centre"))
    g.append(_text("partido", px0, py1 + 6, "[Root.GetRulingParty]", "hoi_16mbs", px1 - px0, 20, "centre"))
    secc = DISENO["secciones"]
    g.append(_text("sec_atributos", DISENO["stats_x"], secc["atributos"] - 18, "MN_FICHA_ATRIBUTOS", "hoi_16mbs", 300, 18))
    g.append(_text("sec_pesa", DISENO["stats_x"], secc["pesa"] - 18, "MN_FICHA_PESA", "hoi_16mbs", 300, 18))
    g.append(_text("sec_gabinete", 36, secc["gabinete"] - 18, "MN_FICHA_GABINETE", "hoi_16mbs", 300, 18))
    bx, bw, bh = DISENO["barra"]
    for (stat, c), y in zip(STATS, DISENO["stats_y"]):
        g.append(_text(f"nom_{c}", DISENO["stats_x"], y - 4, f"MN_FICHA_{stat.upper()}", "hoi_24header", 140, 28))
        g.append(_text(f"sub_{c}", DISENO["stats_x"], y + 22, f"MN_FICHA_{stat.upper()}_SUB", "hoi_16mbs", 150, 18))
        g.append(_icon(f"barra_{c}_total", bx, y + 6, "GFX_mn_ficha_barra_total"))
        g.append(_icon(f"barra_{c}_base", bx, y + 6, "GFX_mn_ficha_barra_base"))
        g.append(_text(f"val_{c}", bx + bw + 14, y - 4, f"[?MEGANATIONS_lider_total_{stat}|0]/20", "hoi_24header", 70, 28))
        g.append(_text(f"min_{c}", bx + bw + 14, y + 22, f"MN_FICHA_{stat.upper()}_MIN", "hoi_16mbs", 70, 18))
    ax, ay, ad = DISENO["anillo"]
    g.append(_icon("salud_anillo", ax, ay, "GFX_mn_ficha_salud"))
    g.append(_text("salud_val", ax, ay + ad // 2 - 26, "[?MEGANATIONS_lider_total_salud|0]", "hoi_36header", ad, 40, "centre"))
    g.append(_text("salud_nom", ax, ay + ad // 2 + 12, "MN_FICHA_SALUD", "hoi_16mbs", ad, 18, "centre"))
    g.append(_text("salud_baja", ax - 20, ay + ad + 10, "MN_FICHA_DESGASTE", "hoi_16mbs", ad + 40, 18, "centre"))
    ew, eh = DISENO["efecto"]
    for (clave, texto), x in zip((("estab", "MN_FICHA_EF_ESTAB"), ("pp", "MN_FICHA_EF_PP"), ("guerra", "MN_FICHA_EF_GUERRA")),
                                 DISENO["efectos_x"]):
        g.append(_text(f"ef_{clave}", x + 16, DISENO["efectos_y"] + 6, texto, "hoi_24header", ew - 24, 28))
        g.append(_text(f"ef_{clave}_nom", x + 16, DISENO["efectos_y"] + 34, f"{texto}_NOM", "hoi_16mbs", ew - 24, 18))
    gx, gy, cols, _, cw, ch, sx, sy = DISENO["gabinete"]
    for k in range(1, max_min + 1):
        col, fila = (k - 1) % cols, (k - 1) // cols
        x, y = gx + col * (cw + sx), gy + fila * (ch + sy)
        g.append(_icon(f"carta_{k}", x, y, "GFX_mn_ficha_carta"))
        g.append(_icon(f"min_retrato_{k}", x + 6, y + 8, "GFX_mn_ficha_sin_retrato", "\n\t\t\tscale = 0.42"))
        g.append(_text(f"min_nombre_{k}", x + 76, y + 6, f"[MN_min_nombre_{k}]", "hoi_16mbs", cw - 80, 56))
        g.append(_text(f"min_bono_{k}", x + 76, y + 64, f"[MN_min_bono_{k}]", "hoi_16mbs", cw - 80, 36))
        g.append(_icon(f"min_apagado_{k}", x, y, "GFX_mn_ficha_apagado", "\n\t\t\talwaystransparent = yes"))
    g.append(_text("pie", 70, H - 34, "MN_FICHA_PIE", "hoi_16mbs", W - 580, 20))
    # 2026-11-03 ("la decisión de El Líder también migrarla a la pantalla del líder")
    aw, ah = DISENO["accion"]
    for i, (nombre, texto) in enumerate((("chequeo", "MN_FICHA_CHEQUEO"), ("gira", "MN_FICHA_GIRA"))):
        x = W - 70 - (2 - i) * (aw + 10) + 10
        g.append(f'\t\tbuttonType = {{\n\t\t\tname = "{nombre}"\n\t\t\tposition = {{ x = {x} y = {H - 44} }}\n'
                 f'\t\t\tspriteType = "GFX_mn_ficha_boton_accion"\n\t\t\ttext = "{texto}"\n'
                 f'\t\t\tbuttonFont = "hoi_18mbs"\n\t\t\tpdx_tooltip = "{texto}_TT"\n\t\t}}\n')
    g.append("\t}\n}\n")
    return "".join(g)


def _scripted_gui(tags: list[str], gab: dict[str, list[str]], max_min: int) -> str:
    quien = _tags_or(tags)
    s = ["scripted_gui = {\n"]
    s.append("\tmn_ficha_boton = {\n\t\tcontext_type = player_context\n\t\tparent_window_token = top_bar\n"
             '\t\twindow_name = "mn_ficha_boton_window"\n'
             f"\t\tvisible = {{ {quien} has_country_flag = MEGANATIONS_lider_listo }}\n"
             "\t\teffects = {\n\t\t\tabrir_click = {\n"
             "\t\t\t\tif = { limit = { has_country_flag = MEGANATIONS_ficha_abierta } clr_country_flag = MEGANATIONS_ficha_abierta }\n"
             "\t\t\t\telse = { set_country_flag = MEGANATIONS_ficha_abierta MEGANATIONS_ficha_actualizar = yes }\n"
             "\t\t\t}\n\t\t}\n\t\tai_enabled = { always = no }\n\t}\n")
    s.append('\tmn_ficha_lider = {\n\t\tcontext_type = player_context\n\t\twindow_name = "mn_ficha_lider_window"\n'
             f"\t\tvisible = {{ {quien} has_country_flag = MEGANATIONS_ficha_abierta }}\n"
             "\t\teffects = {\n\t\t\tcerrar_click = { clr_country_flag = MEGANATIONS_ficha_abierta }\n"
             "\t\t\tchequeo_click = { add_political_power = -50 set_country_flag = { flag = MEGANATIONS_chequeo_hecho value = 1 days = 365 } "
             "MEGANATIONS_lider_hacer_chequeo = yes MEGANATIONS_ficha_actualizar = yes }\n"
             "\t\t\tgira_click = { add_political_power = -75 set_country_flag = { flag = MEGANATIONS_gira_hecha value = 1 days = 365 } "
             "MEGANATIONS_lider_hacer_gira = yes MEGANATIONS_ficha_actualizar = yes }\n\t\t}\n")
    s.append("\t\tproperties = {\n\t\t\tretrato = { image = \"[MN_ficha_retrato]\" }\n"
             "\t\t\tmarco_faccion = { image = \"[MN_ficha_marco]\" }\n")
    for _, c in STATS:
        s.append(f"\t\t\tbarra_{c}_total = {{ frame = MEGANATIONS_gui_{c}_total }}\n"
                 f"\t\t\tbarra_{c}_base = {{ frame = MEGANATIONS_gui_{c}_base }}\n")
    s.append("\t\t\tsalud_anillo = { frame = MEGANATIONS_gui_salud }\n")
    for k in range(1, max_min + 1):
        s.append(f"\t\t\tmin_retrato_{k} = {{ image = \"[MN_min_retrato_{k}]\" }}\n")
    s.append("\t\t}\n\t\ttriggers = {\n")
    s.append("\t\t\tchequeo_click_enabled = { has_political_power > 49 NOT = { has_country_flag = MEGANATIONS_chequeo_hecho } "
             "check_variable = { MEGANATIONS_lider_salud < 100 } }\n"
             "\t\t\tgira_click_enabled = { has_political_power > 74 NOT = { has_country_flag = MEGANATIONS_gira_hecha } "
             "check_variable = { MEGANATIONS_lider_carisma < 20 } }\n")
    for k in range(1, max_min + 1):
        con = [t for t, l in gab.items() if len(l) >= k]
        hay = _tags_or(con) if con else "always = no"
        for el in ("carta", "min_retrato", "min_nombre", "min_bono"):
            s.append(f"\t\t\t{el}_{k}_visible = {{ {hay} }}\n")
        s.append(f"\t\t\tmin_apagado_{k}_visible = {{ {hay} NOT = {{ has_country_flag = MEGANATIONS_gabinete_{k} }} }}\n")
    s.append("\t\t}\n\t\tai_enabled = { always = no }\n\t}\n}\n")
    return "".join(s)


def _textos(ctx: BuildContext) -> None:
    T = {
        "MN_FICHA_TITULO": ("THE LEADER", "EL LÍDER"),
        "MN_FICHA_BOTON_TT": ("§YThe Leader§!\nCharisma, Cunning, Prestige, Health and the cabinet.",
                              "§YEl Líder§!\nCarisma, Astucia, Prestigio, Salud y el gabinete."),
        "MN_FICHA_ATRIBUTOS": ("§YATTRIBUTES§!", "§YATRIBUTOS§!"),
        "MN_FICHA_PESA": ("§YWHAT IT WEIGHS TODAY§!", "§YLO QUE PESA HOY§!"),
        "MN_FICHA_GABINETE": ("§YTHE CABINET§!  (lit: in government)", "§YEL GABINETE§!  (encendido: en el gobierno)"),
        "MN_FICHA_CARISMA": ("Charisma", "Carisma"),
        "MN_FICHA_CARISMA_SUB": ("stability", "estabilidad"),
        "MN_FICHA_ASTUCIA": ("Cunning", "Astucia"),
        "MN_FICHA_ASTUCIA_SUB": ("political power", "poder político"),
        "MN_FICHA_PRESTIGIO": ("Prestige", "Prestigio"),
        "MN_FICHA_PRESTIGIO_SUB": ("war support", "apoyo a la guerra"),
        "MN_FICHA_CARISMA_MIN": ("§C[?MEGANATIONS_lider_bono_carisma|0]§! min.", "§C[?MEGANATIONS_lider_bono_carisma|0]§! min."),
        "MN_FICHA_ASTUCIA_MIN": ("§C[?MEGANATIONS_lider_bono_astucia|0]§! min.", "§C[?MEGANATIONS_lider_bono_astucia|0]§! min."),
        "MN_FICHA_PRESTIGIO_MIN": ("§C[?MEGANATIONS_lider_bono_prestigio|0]§! min.", "§C[?MEGANATIONS_lider_bono_prestigio|0]§! min."),
        "MN_FICHA_SALUD": ("HEALTH / 100", "SALUD / 100"),
        "MN_FICHA_DESGASTE": ("§R-[?MEGANATIONS_lider_desgaste|0]§! a year", "§Rbaja [?MEGANATIONS_lider_desgaste|0]§! por año"),
        "MN_FICHA_EF_ESTAB": ("§C[?MEGANATIONS_gui_estabilidad|1]%§!", "§C[?MEGANATIONS_gui_estabilidad|1]%§!"),
        "MN_FICHA_EF_ESTAB_NOM": ("stability", "estabilidad"),
        "MN_FICHA_EF_PP": ("§C[?MEGANATIONS_lider_ef_astucia|2]§! a day", "§C[?MEGANATIONS_lider_ef_astucia|2]§! por día"),
        "MN_FICHA_EF_PP_NOM": ("political power", "poder político"),
        "MN_FICHA_EF_GUERRA": ("§C[?MEGANATIONS_gui_guerra|0]%§!", "§C[?MEGANATIONS_gui_guerra|0]%§!"),
        "MN_FICHA_EF_GUERRA_NOM": ("war support", "apoyo a la guerra"),
        "MN_FICHA_CHEQUEO": ("Check-up  50", "Chequeo médico  50"),
        "MN_FICHA_CHEQUEO_TT": ("§YThe Leader's Check-up§! (50 political power, once a year)\nA week in the military hospital, away from the cameras. +10 Health. One time in four someone sees the leader go in: -2 Prestige.",
                                "§YEl Chequeo del Líder§! (50 de poder político, una vez por año)\nUna semana en el hospital militar, lejos de las cámaras. +10 de Salud. Una de cada cuatro veces alguien lo ve entrar: -2 de Prestigio."),
        "MN_FICHA_GIRA": ("Grand Tour  75", "Gran Gira  75"),
        "MN_FICHA_GIRA_TT": ("§YThe Grand Tour§! (75 political power, once a year)\nEvery province, every factory, every hand to shake. +2 Charisma, -10 Health. One time in four the cameras catch a crowd booing: -2 Prestige.",
                             "§YLa Gran Gira§! (75 de poder político, una vez por año)\nCada provincia, cada fábrica, cada mano para estrechar. +2 de Carisma, -10 de Salud. Una de cada cuatro veces las cámaras agarran un abucheo: -2 de Prestigio."),
        "MN_FICHA_PIE": ("Each point above or below 10 counts.", "Cada punto sobre o bajo 10 cuenta."),
    }
    for k, (en, es) in T.items():
        ctx.loc.define_and_reference(k, en=en, es=es, file="meganations_ficha", origin="ficha")
