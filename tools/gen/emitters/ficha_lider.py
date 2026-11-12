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
    # 2026-11-12 (medallas): 90 px más alta para la fila de medallas debajo del gabinete
    "ventana": (1020, 830),
    "cabecera": 64,
    "retrato": (44, 94),            # 156 x 210, el retrato del juego
    "retrato_marco": (36, 86, 172, 226),
    "placa": (24, 312, 236, 382),   # la placa del nombre debajo del retrato
    "stats_x": 260, "stats_y": (110, 162, 214), "barra": (410, 300, 14),
    "anillo": (850, 96, 140),
    "secciones": {"atributos": 84, "pesa": 290, "gabinete": 432, "medallas": 694},
    "efectos_y": 312, "efectos_x": (260, 510, 760), "efecto": (230, 56),
    "gabinete": (36, 452, 5, 2, 182, 104, 8, 8),   # x, y, columnas, filas, ancho, alto, separación x, y
    "accion": (210, 30),
    "heredero": (226, 564, 247, 104, 8),   # x, y, ancho, alto, separación: la Sucesión en la 2.ª fila del gabinete
    "boton_chico": (160, 24),   # botones Chequeo y Gira, abajo a la derecha (2026-11-03)
    "emblema": (20, 10),        # 44 px, el recurso propio junto a "EL LÍDER" (2026-11-05)
    "marca": (430, 70),         # 260 px, el recurso propio en marca de agua detrás de los atributos
    "boton": 30,   # del alto de la fila de arriba de la barra, junto al recurso propio (2026-11-03)
    # 2026-11-12: las medallas (3 casillas y el trofeo) y la ventana de la colección
    "medallas": (36, 700, 88, 76),       # x, y, paso entre casillas, lado del marco
    "trofeo_x": 316,
    "medallas_texto": (430, 700, 560, 19),   # x, y, ancho, alto de renglón (lo que da cada una)
    "coleccion": (700, 476),
    "coleccion_celda": (30, 92, 128, 112),   # x, y de la grilla, ancho y alto de celda (5 x 2)
    "coleccion_trofeos": (30, 352, 80),      # x, y, paso (8 trofeos)
}
SEGMENTOS = 20
CUADROS_SALUD = 21

ESTILOS_POR_DEFECTO = {"EFE": "efe", "FCU": "fcu", "ASC": "asc", "ZAL": "zal", "ZJP": "zjp",
                       "HSN": "hsn", "NAS": "nas", "SHD": "shd", "APF": "apf", "NRE": "nre"}
ESTILOS = ("base", "efe", "fcu", "asc", "zal", "zjp", "hsn", "nas", "shd", "apf", "nre")
PIEZAS = ["fondo", "retrato_marco", "barra_total", "barra_base", "salud", "boton", "boton_accion", "boton_chico",
          "carta_ancha", "carta",
          "apagado", "sin_retrato",
          # 2026-11-12: medallas (casillas, candado, "puesta" y la ventana de la colección)
          "medalla_marco", "medalla_trofeo", "medalla_vacia", "medalla_bloqueada", "medalla_en_uso",
          "coleccion_fondo"] + [f"marco_{e}" for e in ESTILOS]
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
    lemas = {t: l for t, l in (cfg.get("mottos") or {}).items() if t in tags}
    sl.append("defined_text = {\n\tname = MN_ficha_lema\n")
    for tag, lema in lemas.items():
        ctx.loc.define_and_reference(f"MN_FICHA_LEMA_{tag}", en=lema["english"], es=lema["spanish"],
                                     file="meganations_ficha", origin="ficha")
        sl.append(f"\ttext = {{ trigger = {{ tag = {tag} }} localization_key = MN_FICHA_LEMA_{tag} }}\n")
    sl.append("\ttext = { localization_key = MN_FICHA_PIE }\n}\n")
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
    extra = _sucesion(ctx, lid, retratos)
    emb = _emblemas(ctx)
    for clave in ("gfx", "triggers"):
        extra[clave] = extra.get(clave, "") + emb.get(clave, "")
    # 2026-11-12: las casillas de medallas debajo del gabinete (emitters/medallas.py)
    from .medallas import en_ficha
    med = en_ficha(ctx)
    for clave in ("gui", "effects", "properties", "triggers"):
        extra[clave] = extra.get(clave, "") + med.get(clave, "")
    if extra.get("gfx"):
        gfx_path = ctx.mod_root / "interface/meganations_ficha.gfx"
        txt = gfx_path.read_text(encoding="utf-8")
        gfx_path.write_text(txt[:txt.rindex("}")] + extra["gfx"] + "}\n", encoding="utf-8")
    gui = _gui(max_min, cfg, emb.get("items"))
    gui = gui[:gui.rindex("\t}\n}\n")] + extra.get("gui", "") + "\t}\n}\n"
    ctx.write_text("interface/meganations_ficha.gui", banner_for(SOURCE) + gui)
    ctx.write_text("common/scripted_guis/meganations_ficha.txt",
                   banner_for(SOURCE) + _scripted_gui(tags, gab, max_min, extra))
    _textos(ctx)
    _barra_recurso(ctx)
    _acentos(ctx)
    ctx.note(f"ficha del líder: ventana propia para {len(tags)} países, {len(lid)} retratos de líder, "
             f"gabinete de hasta {max_min} ministros")


def _sucesion(ctx: BuildContext, lid: list[tuple[int, str]], retratos: dict[str, str]) -> dict:
    """La Sucesión dentro de la Ficha (2026-11-03, "dale con la opción 1"): una carta por
    candidato en la 2.ª fila del gabinete, con retrato, nombre, qué trae y "Nombrar"; el
    elegido muestra "Revocar". Costo, requisitos y efectos salen de su decisión."""
    from ..pdx import render
    from .effects import render_conditions
    cfg = config(ctx).get("succession") or {}
    if not cfg or ctx.spec.country(cfg.get("country", "")) is None:
        return {}
    decs = {d["id"]: d for c in (ctx.spec.raw.get("decisions") or {}).get("categories") or []
            for d in c.get("decisions") or []}
    tag = cfg["country"]
    usados: dict[str, str] = {}

    def cond(spec) -> str:
        if not spec:
            return ""
        return " ".join(render(render_conditions("ficha_sucesion", spec, usados, where=SOURCE)).split())

    visible = f"tag = {tag} " + cond(cfg.get("visible"))
    hx, hy, hw, hh, hs = DISENO["heredero"]
    bw, bh = DISENO["boton_chico"]
    num = {cid: n for n, cid in lid}
    gui, gfx, eff, trig, props = [], [], [], [], []
    rev = cfg.get("revoke") or {}
    rd = decs.get(rev.get("decision", ""), {})
    rcost = int(rd.get("cost", 150))
    flags = [c["decision"] for c in cfg["candidates"]]
    for i, c in enumerate(cfg["candidates"]):
        d = decs.get(c["decision"])
        if d is None:
            ctx.warn(f"ficha del líder: la sucesión pide la decisión {c['decision']}, que no existe")
            continue
        k = i + 1
        x, y = hx + i * (hw + hs), hy
        cid = c["character"]
        cost = int(d.get("cost", 0))
        sprite = f"GFX_mn_lider_{num[cid]}" if cid in num and cid in retratos else None
        if sprite is None and cid in retratos:
            sprite = f"GFX_mn_cand_{cid}"
            gfx.append(_sprite(sprite, retratos[cid]))
        gui.append(_icon(f"her_carta_{k}", x, y, "GFX_mn_ficha_carta_ancha"))
        gui.append(_icon(f"her_retrato_{k}", x + 6, y + 8, sprite or "GFX_mn_ficha_sin_retrato", "\n\t\t\tscale = 0.42"))
        gui.append(_text(f"her_nombre_{k}", x + 78, y + 6, ctx.loc.reference(cid, f"ficha:{cid}"), "hoi_16mbs", hw - 84, 20))
        clave = f"MN_FICHA_HER_{k}"
        ctx.loc.define_and_reference(clave, en=c["summary"]["english"], es=c["summary"]["spanish"],
                                     file="meganations_ficha", origin="ficha")
        gui.append(_text(f"her_resumen_{k}", x + 78, y + 28, clave, "hoi_16mbs", hw - 84, 40))
        for nombre, texto in ((f"her_nombrar_{k}", f"MN_FICHA_NOMBRAR_{k}"), (f"her_revocar_{k}", "MN_FICHA_REVOCAR")):
            gui.append(f'\t\tbuttonType = {{\n\t\t\tname = "{nombre}"\n\t\t\tposition = {{ x = {x + 78} y = {y + hh - bh - 6} }}\n'
                       f'\t\t\tspriteType = "GFX_mn_ficha_boton_chico"\n\t\t\ttext = "{texto}"\n'
                       f'\t\t\tbuttonFont = "hoi_16mbs"\n\t\t\tpdx_tooltip = "{texto}_TT"\n\t\t}}\n')
        ctx.loc.define_and_reference(f"MN_FICHA_NOMBRAR_{k}", en=f"Name  {cost}", es=f"Nombrar  {cost}",
                                     file="meganations_ficha", origin="ficha")
        dn = d.get("name") or {}
        dd = d.get("desc") or {}
        ctx.loc.define_and_reference(f"MN_FICHA_NOMBRAR_{k}_TT",
                                     en=f"§Y{dn.get('english', '')}§! ({cost} political power)\n{dd.get('english', '')}",
                                     es=f"§Y{dn.get('spanish', '')}§! ({cost} de poder político)\n{dd.get('spanish', '')}",
                                     file="meganations_ficha", origin="ficha")
        otros = " ".join(f"NOT = {{ has_country_flag = {f} }}" for f in flags)
        req = cond(d.get("available"))
        eff.append(f"\t\t\ther_nombrar_{k}_click = {{ add_political_power = -{cost} {c['effect']} = yes }}\n")
        eff.append(f"\t\t\ther_revocar_{k}_click = {{ add_political_power = -{rcost} set_country_flag = "
                   f"{{ flag = MEGANATIONS_revocar_hecho value = 1 days = 365 }} {rev.get('effect')} = yes }}\n")
        for el in ("her_carta", "her_retrato", "her_nombre", "her_resumen"):
            trig.append(f"\t\t\t{el}_{k}_visible = {{ {visible} }}\n")
        trig.append(f"\t\t\ther_nombrar_{k}_visible = {{ {visible} NOT = {{ has_country_flag = {c['decision']} }} }}\n")
        trig.append(f"\t\t\ther_nombrar_{k}_click_enabled = {{ has_political_power > {cost - 1} {otros} {req} }}\n")
        trig.append(f"\t\t\ther_revocar_{k}_visible = {{ {visible} has_country_flag = {c['decision']} }}\n")
        trig.append(f"\t\t\ther_revocar_{k}_click_enabled = {{ has_political_power > {rcost - 1} "
                    f"NOT = {{ has_country_flag = MEGANATIONS_revocar_hecho }} }}\n")
    ctx.loc.define_and_reference("MN_FICHA_REVOCAR", en=f"Revoke  {rcost}", es=f"Revocar  {rcost}",
                                 file="meganations_ficha", origin="ficha")
    rn, rdsc = rd.get("name") or {}, rd.get("desc") or {}
    ctx.loc.define_and_reference("MN_FICHA_REVOCAR_TT",
                                 en=f"§G{'Named heir'}§!\n§Y{rn.get('english', '')}§! ({rcost} political power, once a year)\n{rdsc.get('english', '')}",
                                 es=f"§GEs el heredero elegido§!\n§Y{rn.get('spanish', '')}§! ({rcost} de poder político, una vez por año)\n{rdsc.get('spanish', '')}",
                                 file="meganations_ficha", origin="ficha")
    return {"gui": "".join(gui), "gfx": "".join(gfx), "effects": "".join(eff), "triggers": "".join(trig)}


def _items_recurso(ctx: BuildContext, carpeta: str = "chicos") -> list[dict]:
    """Los recursos principales de la barra (11_scenario.yaml -> resource_bar), en orden,
    de países que existen y con su arte en assets/ui/recursos/<carpeta>."""
    cfg = config(ctx).get("resource_bar") or {}
    repo = ctx.spec.root.parent
    return [i for i in cfg.get("items") or [] if ctx.spec.country(i.get("country", "")) is not None
            and (repo / "assets/ui/recursos" / carpeta / f"{i['icon']}.dds").exists()]


def _emblemas(ctx: BuildContext) -> dict:
    """El recurso propio en la Ficha (2026-11-05, "ponele un toque más de personalidad a
    la ventana del líder"): emblema junto al título y marca de agua tenue en el color de
    la facción. Usa los mismos números que la barra (MN_RECURSO_TT_k) y las mismas
    condiciones (Albión cambia de Pompa a Sincronía según la ruta)."""
    from ..pdx import render
    from .effects import render_conditions
    todos = _items_recurso(ctx)
    items = [(k, i) for k, i in enumerate(todos, start=1)
             if all((ctx.spec.root.parent / "assets/ui/recursos" / c / f"{i['icon']}.dds").exists()
                    for c in ("emblema", "marca"))]
    if not items:
        return {}
    gfx, trig, usados = [], [], {}
    for ic in sorted({i["icon"] for _, i in items}):
        for c in ("emblema", "marca"):
            tex = f"{TEX}/{c}/{ic}.dds"
            ctx.copy_asset(f"assets/ui/recursos/{c}/{ic}.dds", tex)
            gfx.append(_sprite(f"GFX_mn_ficha_{c}_{ic}", tex))
    for k, it in items:
        cuando = f"tag = {it['country']}"
        if it.get("when"):
            cuando += " " + " ".join(render(render_conditions("ficha_emblema", it["when"], usados, where=SOURCE)).split())
        for el in ("emblema", "marca"):
            trig.append(f"\t\t\t{el}_{k}_visible = {{ {cuando} }}\n")
    return {"gfx": "".join(gfx), "triggers": "".join(trig), "items": [(k, i["icon"]) for k, i in items]}


def _barra_recurso(ctx: BuildContext) -> None:
    """El recurso propio de cada nación en la barra superior (2026-11-03, maqueta de la
    barra; íconos de arte/recursos_propios.yaml): ícono y número; al pasar el mouse, el
    nombre y los medidores secundarios. Va colgado de top_bar, como el botón del Líder."""
    from ..pdx import render
    from .effects import render_conditions
    cfg = config(ctx).get("resource_bar") or {}
    items = _items_recurso(ctx)
    if not items:
        return
    usados: dict[str, str] = {}
    gfx, gui, trig = ["spriteTypes = {\n"], [], []
    iconos = sorted({i["icon"] for i in items})
    for ic in iconos:
        tex = f"{TEX}/recursos/{ic}.dds"
        ctx.copy_asset(f"assets/ui/recursos/chicos/{ic}.dds", tex)
        gfx.append(_sprite(f"GFX_mn_recurso_{ic}", tex))
    gfx.append("}\n")
    pos = cfg.get("position") or {}
    gui.append('guiTypes = {\n\tcontainerWindowType = {\n\t\tname = "mn_recurso_window"\n'
               f'\t\tposition = {{ x = {int(pos.get("x", 975))} y = {int(pos.get("y", 4))} }}\n'
               '\t\tsize = { width = 130 height = 30 }\n\t\torientation = upper_left\n')
    for k, it in enumerate(items, start=1):
        clave = f"MN_RECURSO_TT_{k}"
        en = f"§Y{it['name']['english']}§!: [?{it['var']}|0]"
        es = f"§Y{it['name']['spanish']}§!: [?{it['var']}|0]"
        for ex in it.get("extra") or []:
            en += f"\\n{ex['name']['english']}: [?{ex['var']}|0]"
            es += f"\\n{ex['name']['spanish']}: [?{ex['var']}|0]"
        ctx.loc.define_and_reference(clave, en=en, es=es, file="meganations_ficha", origin="recursos")
        gui.append(f'\t\ticonType = {{\n\t\t\tname = "rec_icono_{k}"\n\t\t\tspriteType = "GFX_mn_recurso_{it["icon"]}"\n'
                   f'\t\t\tposition = {{ x = 0 y = 0 }}\n\t\t\tpdx_tooltip = "{clave}"\n\t\t}}\n')
        gui.append(f'\t\tinstantTextBoxType = {{\n\t\t\tname = "rec_valor_{k}"\n\t\t\tposition = {{ x = 32 y = 5 }}\n'
                   f'\t\t\tfont = "hoi_18mbs"\n\t\t\ttext = "[?{it["var"]}|0]"\n\t\t\tmaxWidth = 90\n'
                   f'\t\t\tmaxHeight = 22\n\t\t\tformat = left\n\t\t\tfixedsize = yes\n'
                   f'\t\t\tpdx_tooltip = "{clave}"\n\t\t}}\n')
        cuando = f"tag = {it['country']}"
        if it.get("when"):
            cuando += " " + " ".join(render(render_conditions("barra_recurso", it["when"], usados, where=SOURCE)).split())
        for el in ("rec_icono", "rec_valor"):
            trig.append(f"\t\t\t{el}_{k}_visible = {{ {cuando} }}\n")
    gui.append("\t}\n}\n")
    tags = sorted({i["country"] for i in items})
    sg = ("scripted_gui = {\n\tmn_recurso_barra = {\n\t\tcontext_type = player_context\n"
          "\t\tparent_window_token = top_bar\n\t\twindow_name = \"mn_recurso_window\"\n"
          f"\t\tvisible = {{ {_tags_or(tags)} }}\n\t\ttriggers = {{\n" + "".join(trig) +
          "\t\t}\n\t\tai_enabled = { always = no }\n\t}\n}\n")
    ctx.write_text("interface/meganations_recursos.gfx", banner_for(SOURCE) + "".join(gfx))
    ctx.write_text("interface/meganations_recursos.gui", banner_for(SOURCE) + "".join(gui))
    ctx.write_text("common/scripted_guis/meganations_recursos.txt", banner_for(SOURCE) + sg)
    ctx.note(f"barra: recurso propio para {len(tags)} países ({len(items)} recursos)")


def _acentos(ctx: BuildContext) -> None:
    """El color de cada facción, sin abusar (2026-11-03): un hilo de luz bajo la barra
    superior (top_bar) y escuadras en las esquinas de arriba de Política (politics_tab).
    Arte de tools/arte/ficha.py acentos; colores en 11_scenario.yaml -> faction_accents."""
    cfg = config(ctx).get("faction_accents") or {}
    repo = ctx.spec.root.parent
    tags = [t for t in (cfg.get("colors") or {}) if ctx.spec.country(t) is not None
            and (repo / ARTE[0] / ARTE[1] / ARTE[2] / "acentos" / f"hilo_{t}.dds").exists()]
    if not tags:
        return
    gfx, sg = ["spriteTypes = {\n"], ["scripted_gui = {\n"]
    for t in tags:
        for pieza in (f"hilo_{t}", f"escuadra_izq_{t}", f"escuadra_der_{t}"):
            ctx.copy_asset(f"{'/'.join(ARTE)}/acentos/{pieza}.dds", f"{TEX}/acentos/{pieza}.dds")
            gfx.append(_sprite(f"GFX_mn_acento_{pieza}", f"{TEX}/acentos/{pieza}.dds"))
    gfx.append("}\n")
    tb, pol = cfg.get("topbar") or {}, cfg.get("politics") or {}
    gui = ['guiTypes = {\n\tcontainerWindowType = {\n\t\tname = "mn_acento_barra_window"\n'
           f'\t\tposition = {{ x = {int(tb.get("x", 0))} y = {int(tb.get("y", 77))} }}\n'
           f'\t\tsize = {{ width = {int(tb.get("width", 690))} height = 7 }}\n\t\torientation = upper_left\n']
    for t in tags:
        gui.append(_icon(f"hilo_{t}", 0, 0, f"GFX_mn_acento_hilo_{t}", "\n\t\t\talwaystransparent = yes"))
    gui.append("\t}\n")
    pw = int(pol.get("width", 540))
    gui.append('\tcontainerWindowType = {\n\t\tname = "mn_acento_politica_window"\n'
               f'\t\tposition = {{ x = {int(pol.get("x", 0))} y = {int(pol.get("y", 0))} }}\n'
               f'\t\tsize = {{ width = {pw} height = 40 }}\n\t\torientation = upper_left\n')
    for t in tags:
        gui.append(_icon(f"esq_izq_{t}", 0, 0, f"GFX_mn_acento_escuadra_izq_{t}", "\n\t\t\talwaystransparent = yes"))
        gui.append(_icon(f"esq_der_{t}", pw - 38, 0, f"GFX_mn_acento_escuadra_der_{t}", "\n\t\t\talwaystransparent = yes"))
    gui.append("\t}\n")
    # 2026-11-05 ("expandir el uso del color único"): las mismas escuadras en otras
    # pantallas (faction_accents.windows; nombres de ventana del validador tiger-lib).
    # Cada esquina es su propia ventana: la derecha se ancla a la esquina de arriba a la
    # derecha de la pantalla del juego, así no hace falta saber su ancho.
    validas = {"decision_tab", "technology_tab", "trade_tab", "construction_tab", "production_tab",
               "deployment_tab", "logistics_tab", "diplomacy_tab", "national_focus"}
    pantallas = []
    off = cfg.get("windows_offset") or {}
    for token in cfg.get("windows") or []:
        if token not in validas:
            ctx.warn(f"acentos de facción: '{token}' no es una ventana que acepte scripted GUI")
            continue
        for lado, orient, x in (("izq", "upper_left", int(off.get("x", 0))),
                                ("der", "upper_right", int(off.get("right_x", -38)))):
            ventana = f"mn_acento_{token}_{lado}_window"
            gui.append(f'\tcontainerWindowType = {{\n\t\tname = "{ventana}"\n'
                       f'\t\tposition = {{ x = {x} y = {int(off.get("y", 0))} }}\n\t\tsize = {{ width = 38 height = 38 }}\n'
                       f'\t\torientation = {orient}\n')
            for t in tags:
                gui.append(_icon(f"esq_{lado}_{t}", 0, 0, f"GFX_mn_acento_escuadra_{lado}_{t}",
                                 "\n\t\t\talwaystransparent = yes"))
            gui.append("\t}\n")
            pantallas.append((f"mn_acento_{token}_{lado}", token, ventana, (f"esq_{lado}",)))
    gui.append("}\n")
    for nombre, token, ventana, elems in [("mn_acento_barra", "top_bar", "mn_acento_barra_window", ("hilo",)),
                                          ("mn_acento_politica", "politics_tab", "mn_acento_politica_window",
                                           ("esq_izq", "esq_der"))] + pantallas:
        sg.append(f"\t{nombre} = {{\n\t\tcontext_type = player_context\n\t\tparent_window_token = {token}\n"
                  f'\t\twindow_name = "{ventana}"\n\t\tvisible = {{ {_tags_or(tags)} }}\n\t\ttriggers = {{\n')
        for t in tags:
            for el in elems:
                sg.append(f"\t\t\t{el}_{t}_visible = {{ tag = {t} }}\n")
        sg.append("\t\t}\n\t\tai_enabled = { always = no }\n\t}\n")
    sg.append("}\n")
    ctx.write_text("interface/meganations_acentos.gfx", banner_for(SOURCE) + "".join(gfx))
    ctx.write_text("interface/meganations_acentos.gui", banner_for(SOURCE) + "".join(gui))
    ctx.write_text("common/scripted_guis/meganations_acentos.txt", banner_for(SOURCE) + "".join(sg))
    ctx.note(f"acentos de facción: {len(tags)} países (barra superior, Política y {len(pantallas) // 2} pantallas más)")


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


def _gui(max_min: int, cfg: dict, emblemas: list | None = None) -> str:
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
    # el recurso propio de la nación: marca de agua detrás de los atributos (2026-11-05)
    mx_, my_ = DISENO["marca"]
    for k, icono in emblemas or []:
        g.append(_icon(f"marca_{k}", mx_, my_, f"GFX_mn_ficha_marca_{icono}", "\n\t\t\talwaystransparent = yes"))
    rx, ry = DISENO["retrato"]
    g.append(_icon("retrato", rx, ry, "GFX_mn_ficha_sin_retrato"))
    mx, my, _, _ = DISENO["retrato_marco"]
    g.append(_icon("retrato_marco", mx, my, "GFX_mn_ficha_retrato_marco"))
    g.append(_text("titulo", 70, 14, "MN_FICHA_TITULO", "hoi_36header", 400, 40))
    ex, ey = DISENO["emblema"]
    for k, icono in emblemas or []:
        g.append(_icon(f"emblema_{k}", ex, ey, f"GFX_mn_ficha_emblema_{icono}", "\n\t\t\tpdx_tooltip = \"MN_RECURSO_TT_%d\"" % k))
    g.append(_text("pais", W - 520, 22, "[Root.GetName]", "hoi_18mbs", 420, 24, "right"))
    g.append('\t\tbuttonType = {\n\t\t\tname = "cerrar"\n\t\t\tposition = { x = %d y = 14 }\n'
             '\t\t\tspriteType = "GFX_closebutton"\n\t\t\tshortcut = "ESCAPE"\n\t\t}\n' % (W - 84))
    px0, py0, px1, py1 = DISENO["placa"]
    g.append(_text("nombre", px0 + 14, py0 + 8, "[Root.GetLeader]", "hoi_18mbs", px1 - px0 - 28, py1 - py0 - 12, "centre"))
    g.append(_text("partido", px0, py1 + 6, "[Root.GetRulingParty]", "hoi_16mbs", px1 - px0, 20, "centre"))
    secc = DISENO["secciones"]
    g.append(_text("sec_atributos", DISENO["stats_x"], secc["atributos"] - 18, "MN_FICHA_ATRIBUTOS", "hoi_16mbs", 300, 18)
             .replace("\t\t\tfixedsize = yes\n", "\t\t\tfixedsize = yes\n\t\t\tpdx_tooltip = \"MN_FICHA_ATRIBUTOS_TT\"\n"))
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
    # el lema de la nación (2026-11-05); sin lema, la ayuda de siempre
    g.append(_text("pie", 70, H - 34, "[MN_ficha_lema]", "hoi_16mbs", W - 580, 20))
    # 2026-11-03 ("la decisión de El Líder también migrarla a la pantalla del líder")
    aw, ah = DISENO["accion"]
    for i, (nombre, texto) in enumerate((("chequeo", "MN_FICHA_CHEQUEO"), ("gira", "MN_FICHA_GIRA"))):
        x = W - 70 - (2 - i) * (aw + 10) + 10
        g.append(f'\t\tbuttonType = {{\n\t\t\tname = "{nombre}"\n\t\t\tposition = {{ x = {x} y = {H - 44} }}\n'
                 f'\t\t\tspriteType = "GFX_mn_ficha_boton_accion"\n\t\t\ttext = "{texto}"\n'
                 f'\t\t\tbuttonFont = "hoi_18mbs"\n\t\t\tpdx_tooltip = "{texto}_TT"\n\t\t}}\n')
    g.append("\t}\n}\n")
    return "".join(g)


def _scripted_gui(tags: list[str], gab: dict[str, list[str]], max_min: int, extra: dict | None = None) -> str:
    extra = extra or {}
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
             "MEGANATIONS_lider_hacer_gira = yes MEGANATIONS_ficha_actualizar = yes }\n"
             + extra.get("effects", "") + "\t\t}\n")
    s.append("\t\tproperties = {\n\t\t\tretrato = { image = \"[MN_ficha_retrato]\" }\n"
             "\t\t\tmarco_faccion = { image = \"[MN_ficha_marco]\" }\n")
    for _, c in STATS:
        s.append(f"\t\t\tbarra_{c}_total = {{ frame = MEGANATIONS_gui_{c}_total }}\n"
                 f"\t\t\tbarra_{c}_base = {{ frame = MEGANATIONS_gui_{c}_base }}\n")
    s.append("\t\t\tsalud_anillo = { frame = MEGANATIONS_gui_salud }\n")
    for k in range(1, max_min + 1):
        s.append(f"\t\t\tmin_retrato_{k} = {{ image = \"[MN_min_retrato_{k}]\" }}\n")
    s.append(extra.get("properties", ""))
    s.append("\t\t}\n\t\ttriggers = {\n")
    s.append(extra.get("triggers", ""))
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
        "MN_FICHA_ATRIBUTOS_TT": ("Each point above or below 10 counts: Charisma moves stability, Cunning political power, Prestige war support.",
                                  "Cada punto sobre o bajo 10 cuenta: el Carisma mueve la estabilidad, la Astucia el poder político y el Prestigio el apoyo a la guerra."),
    }
    for k, (en, es) in T.items():
        ctx.loc.define_and_reference(k, en=en, es=es, file="meganations_ficha", origin="ficha")
