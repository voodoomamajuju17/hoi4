"""Medallas de la Ficha del Líder (2026-11-12, spec/40_medallas.yaml).

Pedido: "para no desperdiciar tanto tile hermoso: en la pantalla del líder 3 slots para poner
esos tiles, de toda una pila para elegir. Son medallas, bonus para el líder o la facción, se
desbloquean con decisiones, eventos, focos y tecnología. También uno reservado a cada vez que se
conquista una capital (solo de meganaciones)". Respuestas: bonus del 2% al 6%; los trofeos se
acumulan y se elige cuál mostrar (con un azulejo de la nación conquistada); cambiar cuesta 25 de
poder político y 30 días de espera; 10 medallas por nación como máximo, sin contar trofeos.

En la Ficha (debajo del gabinete): 3 casillas de medalla y la del trofeo; tocar una abre la
colección (otra ventana): las 10 medallas de la nación, a color las ganadas y apagadas con
candado las que faltan (al pasar el mouse: qué dan y cómo se ganan), y los trofeos de las
otras meganaciones. Poner una medalla en una casilla vacía es gratis; cambiarla, 25 de poder
político y después 30 días sin poder cambiar.

El bonus no ocupa lugar en el panel de Política: se suma al espíritu El Líder
(MEGANATIONS_el_lider), que ya es un modificador con valores variables (MN_med_<clave>).
La IA pone las que tiene ganadas en las casillas vacías (en el pulso del líder).

Sin probar en partida: misma sintaxis que la Ficha (scripted GUI, imágenes elegidas con texto
con guion), que tampoco se abrió todavía en el juego.
"""

from __future__ import annotations

import re

from ..context import BuildContext
from ..pdx import Block, banner_for, render, parse_file
from .ficha_lider import DISENO, TEX, _icon, _sprite, _text, paises

SOURCE = "spec/40_medallas.yaml (medallas de la Ficha del Líder)"
SLOTS = 3
LIDER = "MEGANATIONS_el_lider"
MAX_MEDALLAS = 10

NOMBRES = {  # clave -> (inglés, español)
    "stability_factor": ("Stability", "Estabilidad"),
    "war_support_factor": ("War support", "Apoyo a la guerra"),
    "political_power_factor": ("Political power", "Poder político"),
    "industrial_capacity_factory": ("Factory output", "Producción de fábricas"),
    "industrial_capacity_dockyard": ("Dockyard output", "Producción de astilleros"),
    "production_speed_buildings_factor": ("Construction speed", "Velocidad de construcción"),
    "research_speed_factor": ("Research speed", "Velocidad de investigación"),
    "army_attack_factor": ("Army attack", "Ataque del ejército"),
    "army_defence_factor": ("Army defence", "Defensa del ejército"),
    "army_org_factor": ("Army organisation", "Organización del ejército"),
    "air_attack_factor": ("Air attack", "Ataque aéreo"),
    "naval_damage_factor": ("Naval damage", "Daño naval"),
    "consumer_goods_factor": ("Consumer goods", "Bienes de consumo"),
}
DEL_LIDER = {"stability_factor", "war_support_factor", "political_power_factor"}


def _cfg(ctx: BuildContext) -> dict:
    return ctx.spec.raw.get("medallas") or {}


def catalogo(ctx: BuildContext) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    """(medallas por país de la Ficha, trofeos por meganación), solo con azulejo que exista."""
    cfg = _cfg(ctx)
    repo = ctx.spec.root.parent
    tags = paises(ctx)
    meds = {}
    for tag, lista in (cfg.get("medallas") or {}).items():
        if tag not in tags:
            continue
        ok = [m for m in lista if (repo / "assets" / tag / "ideas" / f"{m['tile']}.dds").exists()]
        meds[tag] = ok[:MAX_MEDALLAS]
    majors = {c.tag for c in ctx.spec.countries if c.is_major}
    trof = {t: v for t, v in (cfg.get("trofeos") or {}).items()
            if t in majors and (repo / "assets" / t / "ideas" / f"{v['tile']}.dds").exists()}
    return meds, trof


def _bonus_texto(bonus: dict) -> tuple[str, str]:
    (k, v), = bonus.items()
    en_n, es_n = NOMBRES.get(k, (k, k))
    pct = f"{v * 100:+.0f}%"
    return f"§G{pct}§! {en_n}", f"§G{pct}§! {es_n}"


def _tech(ctx: BuildContext, alternativas) -> str | None:
    alts = alternativas if isinstance(alternativas, list) else [alternativas]
    if ctx.vanilla is None:
        return alts[0]
    arbol = ctx.vanilla.tech_tree()
    return next((t for t in alts if t in arbol), None)


def _condicion(ctx: BuildContext, tag: str, m: dict, dinamicos: set[str]) -> tuple[str | None, tuple[str, str]]:
    """Trigger de desbloqueo y el texto de cómo se gana (en, es)."""
    (tipo, valor), = m["unlock"].items()
    tile = m["tile"]
    tiene = (f"has_dynamic_modifier = {{ modifier = {tile} }}" if tile in dinamicos else f"has_idea = {tile}")
    if tipo == "foco":
        return (f"OR = {{ has_completed_focus = {valor} {tiene} }}",
                (f"Earned with the focus §Y${valor}$§!.", f"Se gana con el foco §Y${valor}$§!."))
    if tipo == "decision":
        return tiene, (f"Earned with the decision §Y${valor}$§!.", f"Se gana con la decisión §Y${valor}$§!.")
    if tipo == "evento":
        return tiene, (f"Earned in the event §Y${valor}.t$§!.", f"Se gana en el evento §Y${valor}.t$§!.")
    if tipo == "tecnologia":
        t = _tech(ctx, valor)
        if t is None:
            return None, ("", "")
        return f"has_tech = {t}", (f"Earned by researching §Y${t}$§!.", f"Se gana al investigar §Y${t}$§!.")
    return None, ("", "")


def en_ficha(ctx: BuildContext) -> dict:
    """Las casillas dentro de la Ficha (gui, triggers, effects, properties para ficha_lider)."""
    meds, trof = catalogo(ctx)
    if not meds:
        return {}
    x0, y0, paso, lado = DISENO["medallas"]
    tx = DISENO["trofeo_x"]
    sec = DISENO["secciones"]["medallas"]
    g = [_text("sec_medallas", 36, sec - 18, "MN_MED_SECCION", "hoi_16mbs", 380, 18)]
    xs = [x0 + k * paso for k in range(SLOTS)] + [tx]
    for s, x in enumerate(xs, start=1):
        marco = "GFX_mn_ficha_medalla_trofeo" if s == SLOTS + 1 else "GFX_mn_ficha_medalla_marco"
        g.append(_icon(f"med_slot_icono_{s}", x + (lado - 64) // 2, y0 + (lado - 64) // 2, "GFX_mn_ficha_medalla_vacia"))
        g.append(f'\t\tbuttonType = {{\n\t\t\tname = "med_slot_{s}"\n\t\t\tposition = {{ x = {x} y = {y0} }}\n'
                 f'\t\t\tspriteType = "{marco}"\n\t\t\tpdx_tooltip = "MN_MED_SLOT_TT_{s}"\n\t\t}}\n')
    g.append(_text("med_trofeo_rotulo", tx - 6, y0 - 18, "MN_MED_TROFEO", "hoi_16mbs", lado + 12, 18, "centre"))
    mx, my, mw, mh = DISENO["medallas_texto"]
    for s in range(1, SLOTS + 2):
        g.append(_text(f"med_linea_{s}", mx, my + (s - 1) * mh, f"[MN_med_linea_{s}]", "hoi_16mbs", mw, mh))
    props = "".join(f'\t\t\tmed_slot_icono_{s} = {{ image = "[MN_slot_img_{s}]" }}\n' for s in range(1, SLOTS + 2))
    eff = "".join(f"\t\t\tmed_slot_{s}_click = {{ set_variable = {{ MN_med_sel = {s} }} "
                  f"set_country_flag = MN_medallas_abierta MN_medallas_revisar = yes }}\n" for s in range(1, SLOTS + 2))
    con = " ".join(f"tag = {t}" for t in meds)
    trig = "".join(f"\t\t\t{el}_visible = {{ OR = {{ {con} }} }}\n"
                   for el in ["sec_medallas", "med_trofeo_rotulo"]
                   + [f"med_slot_{s}" for s in range(1, SLOTS + 2)]
                   + [f"med_slot_icono_{s}" for s in range(1, SLOTS + 2)]
                   + [f"med_linea_{s}" for s in range(1, SLOTS + 2)])
    return {"gui": "".join(g), "effects": eff, "properties": props, "triggers": trig}


def emit(ctx: BuildContext) -> None:
    meds, trof = catalogo(ctx)
    if not meds:
        return
    from .effects import dynamic_modifier_ids
    dinamicos = dynamic_modifier_ids(ctx.spec.raw)
    cfg = _cfg(ctx)
    costo = int((cfg.get("cambio") or {}).get("costo", 25))
    dias = int((cfg.get("cambio") or {}).get("dias", 30))
    orden_trof = sorted(trof)
    n_max = max(len(v) for v in meds.values())

    # -- arte: cada azulejo como medalla -----------------------------------------
    gfx = ["spriteTypes = {\n"]
    for tag, lista in meds.items():
        for m in lista:
            tex = f"{TEX}/medallas/{m['tile']}.dds"
            ctx.copy_asset(f"assets/{tag}/ideas/{m['tile']}.dds", tex)
            gfx.append(_sprite(f"GFX_mn_med_{tag}_{m['n']}", tex))
    for t in orden_trof:
        tex = f"{TEX}/medallas/{trof[t]['tile']}.dds"
        if not (ctx.mod_root / tex).exists():
            ctx.copy_asset(f"assets/{t}/ideas/{trof[t]['tile']}.dds", tex)
        gfx.append(_sprite(f"GFX_mn_trofeo_{t}", tex))
    gfx.append("}\n")
    ctx.write_text("interface/meganations_medallas.gfx", banner_for(SOURCE) + "".join(gfx))

    # -- desbloqueos, suma del bonus, poner y la IA (efectos y condiciones) --------
    claves = sorted({k for l in meds.values() for m in l for k in m["bonus"]}
                    | {k for v in trof.values() for k in v["bonus"]})
    if ctx.vanilla is not None and ctx.vanilla.documented_keys("modifiers") is not None:
        for k in claves:
            if not ctx.vanilla.is_documented("modifiers", k):
                ctx.warn(f"medallas: el modificador '{k}' no está en este juego; esas medallas no darán nada")
    st, se = [], []
    for i in range(1, n_max + 1):
        quien = " ".join(f"AND = {{ tag = {t} has_country_flag = MN_med_{t}_{i} }}"
                         for t, l in meds.items() if len(l) >= i)
        st.append(f"MN_med_ok_{i} = {{ OR = {{ {quien} }} }}\n")
        st.append(f"MN_med_en_uso_{i} = {{ OR = {{ " + " ".join(
            f"check_variable = {{ MN_medalla_{s} = {i} }}" for s in range(1, SLOTS + 1)) + " } }\n")
    puede = []
    for s in range(1, SLOTS + 2):
        var = f"MN_medalla_{s}" if s <= SLOTS else "MN_trofeo"
        puede.append(f"AND = {{ check_variable = {{ MN_med_sel = {s} }} OR = {{ check_variable = {{ {var} = 0 }} "
                     f"AND = {{ has_political_power > {costo - 1} NOT = {{ has_country_flag = MN_med_espera }} }} }} }}")
    st.append("MN_med_puede_cambiar = { OR = { " + " ".join(puede) + " } }\n")
    ctx.write_text("common/scripted_triggers/meganations_medallas.txt", banner_for(SOURCE) + "".join(st))

    # desbloquear
    rev = ["MN_medallas_revisar = {\n"]
    textos_gana: dict[tuple[str, int], tuple[str, str]] = {}
    for tag, lista in meds.items():
        partes = []
        for m in lista:
            cond, como = _condicion(ctx, tag, m, dinamicos)
            textos_gana[(tag, m["n"])] = como
            if cond is None:
                ctx.warn(f"medallas: {tag} {m['tile']} no tiene cómo ganarse en este juego")
                continue
            partes.append(f"\t\tif = {{ limit = {{ NOT = {{ has_country_flag = MN_med_{tag}_{m['n']} }} {cond} }} "
                          f"set_country_flag = MN_med_{tag}_{m['n']} }}\n")
        rev.append(f"\tif = {{ limit = {{ tag = {tag} }}\n" + "".join(partes) + "\t}\n")
    rev.append("}\n")
    se.extend(rev)
    # sumar lo puesto
    sumar = ["MN_medallas_sumar = {\n"]
    for k in claves:
        sumar.append(f"\tset_variable = {{ MN_med_{k} = 0 }}\n")
    for tag, lista in meds.items():
        for m in lista:
            (k, v), = m["bonus"].items()
            usa = " ".join(f"check_variable = {{ MN_medalla_{s} = {m['n']} }}" for s in range(1, SLOTS + 1))
            sumar.append(f"\tif = {{ limit = {{ tag = {tag} OR = {{ {usa} }} }} add_to_variable = {{ MN_med_{k} = {v} }} }}\n")
    for j, t in enumerate(orden_trof, start=1):
        (k, v), = trof[t]["bonus"].items()
        sumar.append(f"\tif = {{ limit = {{ check_variable = {{ MN_trofeo = {j} }} }} add_to_variable = {{ MN_med_{k} = {v} }} }}\n")
    sumar.append("\tMN_lider_sumar = yes\n}\n")
    se.extend(sumar)
    # poner (la medalla mn_i en la casilla MN_med_sel)
    poner = ["MN_med_poner = {\n"]
    for s in range(1, SLOTS + 1):
        otras = "".join(f"\t\tif = {{ limit = {{ check_variable = {{ MN_medalla_{o} = mn_i }} }} set_variable = {{ MN_medalla_{o} = 0 }} }}\n"
                        for o in range(1, SLOTS + 1) if o != s)
        poner.append(f"\tif = {{ limit = {{ check_variable = {{ MN_med_sel = {s} }} }}\n"
                     f"\t\tif = {{ limit = {{ check_variable = {{ MN_medalla_{s} > 0 }} }} add_political_power = -{costo} "
                     f"set_country_flag = {{ flag = MN_med_espera value = 1 days = {dias} }} }}\n"
                     + otras + f"\t\tset_variable = {{ MN_medalla_{s} = mn_i }}\n\t}}\n")
    poner.append(f"\tif = {{ limit = {{ check_variable = {{ MN_med_sel = {SLOTS + 1} }} }}\n"
                 f"\t\tif = {{ limit = {{ check_variable = {{ MN_trofeo > 0 }} }} add_political_power = -{costo} "
                 f"set_country_flag = {{ flag = MN_med_espera value = 1 days = {dias} }} }}\n"
                 "\t\tset_variable = { MN_trofeo = mn_i }\n\t}\n")
    poner.append("\tMN_medallas_sumar = yes\n\tclr_country_flag = MN_medallas_abierta\n}\n")
    se.extend(poner)
    # la IA: llena las casillas vacías con lo que ganó (nunca cambia, así no paga)
    ia = ["MN_medallas_ia = {\n"]
    for s in range(1, SLOTS + 1):
        cadena = []
        for i in range(1, n_max + 1):
            kw = "if" if not cadena else "else_if"
            cadena.append(f"\t\t{kw} = {{ limit = {{ MN_med_ok_{i} = yes NOT = {{ MN_med_en_uso_{i} = yes }} }} "
                          f"set_variable = {{ MN_medalla_{s} = {i} }} }}\n")
        ia.append(f"\tif = {{ limit = {{ check_variable = {{ MN_medalla_{s} = 0 }} }}\n" + "".join(cadena) + "\t}\n")
    cadena = []
    for j, t in enumerate(orden_trof, start=1):
        kw = "if" if not cadena else "else_if"
        cadena.append(f"\t\t{kw} = {{ limit = {{ has_country_flag = MEGANATIONS_absorbido_{t} }} "
                      f"set_variable = {{ MN_trofeo = {j} }} }}\n")
    ia.append("\tif = { limit = { check_variable = { MN_trofeo = 0 } }\n" + "".join(cadena) + "\t}\n")
    ia.append("\tMN_medallas_sumar = yes\n}\n")
    se.extend(ia)
    se.append("MN_medallas_pulso = {\n\tif = { limit = { OR = { " + " ".join(f"tag = {t}" for t in meds) + " } }\n"
              "\t\tMN_medallas_revisar = yes\n\t\tif = { limit = { is_ai = yes } MN_medallas_ia = yes }\n\t}\n}\n")

    # el bonus va dentro de El Líder: cada clave suma lo del líder (si ya la usaba) y lo de las medallas
    dm_path = ctx.mod_root / "common/dynamic_modifiers/meganations_dynamic_modifiers.txt"
    lider_sumar = ["MN_lider_sumar = {\n"]
    if dm_path.exists():
        dm = parse_file(dm_path)
        cuerpo = dm.get(LIDER)
        if isinstance(cuerpo, Block):
            usadas = {str(k): str(v) for k, v in cuerpo.entries if not isinstance(v, Block) and k != "icon"}
            for k in claves:
                if k in usadas:
                    lider_sumar.append(f"\tset_variable = {{ MN_tot_{k} = {usadas[k]} }}\n"
                                       f"\tadd_to_variable = {{ MN_tot_{k} = MN_med_{k} }}\n")
                    cuerpo.entries = [(kk, (f"MN_tot_{k}" if kk == k else vv)) for kk, vv in cuerpo.entries]
                else:
                    cuerpo.add(k, f"MN_med_{k}")
            dm_path.write_text(banner_for("spec/14_decisions.yaml (+ medallas, 40_medallas.yaml)") + render(dm),
                               encoding="utf-8", newline="\n")
        else:
            ctx.warn("medallas: no está el espíritu El Líder; las medallas no dan bonus")
    lider_sumar.append(f"\tif = {{ limit = {{ NOT = {{ has_dynamic_modifier = {{ modifier = {LIDER} }} }} }} "
                       f"add_dynamic_modifier = {{ modifier = {LIDER} }} }}\n}}\n")
    se.extend(lider_sumar)
    ctx.write_text("common/scripted_effects/meganations_medallas.txt", banner_for(SOURCE) + "".join(se))

    # cuando el líder recalcula sus números, también la suma con las medallas; el pulso del
    # líder revisa desbloqueos y deja que la IA elija; abrir la Ficha también revisa
    efx = ctx.mod_root / "common/scripted_effects/meganations_effects.txt"
    if efx.exists():
        t = efx.read_text(encoding="utf-8")
        lider = re.compile(r"(if\s*=\s*\{\s*limit\s*=\s*\{\s*NOT\s*=\s*\{\s*has_dynamic_modifier\s*=\s*\{\s*modifier\s*=\s*"
                           + LIDER + r"\s*\}\s*\}\s*\}\s*add_dynamic_modifier\s*=\s*\{\s*modifier\s*=\s*" + LIDER + r"\s*\}\s*\})")
        t, n1 = lider.subn(r"\1\n\tMN_lider_sumar = yes", t)
        t, n2 = re.subn(r"(\bMEGANATIONS_lider_pulso\s*=\s*\{)", r"\1\n\tMN_medallas_pulso = yes", t, count=1)
        efx.write_text(t, encoding="utf-8", newline="\n")
        if not n1 or not n2:
            ctx.warn(f"medallas: no encontré dónde engancharlas (líder {n1}, pulso {n2})")
    fe = ctx.mod_root / "common/scripted_effects/meganations_ficha.txt"
    if fe.exists():
        t = fe.read_text(encoding="utf-8")
        fe.write_text(t.replace("MEGANATIONS_ficha_actualizar = {\n", "MEGANATIONS_ficha_actualizar = {\n\tMN_medallas_revisar = yes\n", 1),
                      encoding="utf-8", newline="\n")
    ctx.data["medallas"] = True

    # -- textos con guion: qué imagen, qué nombre y qué dice cada lugar ----------
    sl = []

    def dt(nombre: str, casos: list[tuple[str, str]], defecto: str) -> None:
        sl.append(f"defined_text = {{\n\tname = {nombre}\n")
        for trig, clave in casos:
            sl.append(f"\ttext = {{ trigger = {{ {trig} }} localization_key = {clave} }}\n")
        sl.append(f"\ttext = {{ localization_key = {defecto} }}\n}}\n")

    for i in range(1, n_max + 1):
        dt(f"MN_med_img_{i}", [(f"tag = {t}", f"GFX_mn_med_{t}_{i}") for t, l in meds.items() if len(l) >= i],
           "GFX_mn_ficha_medalla_vacia")
        dt(f"MN_med_nom_{i}", [(f"tag = {t}", f"MN_MED_{t}_{i}_NOM") for t, l in meds.items() if len(l) >= i], "MN_MED_VACIO")
        dt(f"MN_med_tt_{i}", [(f"tag = {t}", f"MN_MED_{t}_{i}_TT") for t, l in meds.items() if len(l) >= i], "MN_MED_VACIO")
    for s in range(1, SLOTS + 1):
        casos_img, casos_txt = [], []
        for t, l in meds.items():
            for m in l:
                c = f"tag = {t} check_variable = {{ MN_medalla_{s} = {m['n']} }}"
                casos_img.append((c, f"GFX_mn_med_{t}_{m['n']}"))
                casos_txt.append((c, f"MN_MED_{t}_{m['n']}_LINEA"))
        dt(f"MN_slot_img_{s}", casos_img, "GFX_mn_ficha_medalla_vacia")
        dt(f"MN_med_linea_{s}", casos_txt, "MN_MED_LIBRE")
    dt(f"MN_slot_img_{SLOTS + 1}", [(f"check_variable = {{ MN_trofeo = {j} }}", f"GFX_mn_trofeo_{t}")
                                    for j, t in enumerate(orden_trof, start=1)], "GFX_mn_ficha_medalla_vacia")
    dt(f"MN_med_linea_{SLOTS + 1}", [(f"check_variable = {{ MN_trofeo = {j} }}", f"MN_TROFEO_{t}_LINEA")
                                     for j, t in enumerate(orden_trof, start=1)], "MN_MED_TROFEO_LIBRE")
    dt("MN_med_titulo", [(f"check_variable = {{ MN_med_sel = {s} }}", f"MN_MED_TITULO_{s}") for s in range(1, SLOTS + 2)],
       "MN_MED_TITULO_1")
    dt("MN_med_espera", [("has_country_flag = MN_med_espera", "MN_MED_ESPERA_SI")], "MN_MED_ESPERA_NO")
    ctx.write_text("common/scripted_localisation/meganations_medallas.txt", banner_for(SOURCE) + "".join(sl))
    for clave in sorted(set(re.findall(r"localization_key = (GFX_\w+)", "".join(sl)))):
        ctx.loc.define_and_reference(clave, en=clave, es=clave, file="meganations_medallas", origin="medallas")

    # -- textos -------------------------------------------------------------------
    def loc(k: str, en: str, es: str) -> None:
        ctx.loc.define_and_reference(k, en=en, es=es, file="meganations_medallas", origin="medallas")

    for tag, lista in meds.items():
        for m in lista:
            k = f"MN_MED_{tag}_{m['n']}"
            ben, bes = _bonus_texto(m["bonus"])
            (clave_b, _), = m["bonus"].items()
            de_en, de_es = (("Leader medal", "Medalla del Líder") if clave_b in DEL_LIDER
                            else ("National medal", "Medalla de la Nación"))
            gen, ges = textos_gana[(tag, m["n"])]
            loc(f"{k}_NOM", f"${m['tile']}$", f"${m['tile']}$")
            loc(f"{k}_TT", f"§Y${m['tile']}$§!  ({de_en})\\n{ben}\\n{gen}", f"§Y${m['tile']}$§!  ({de_es})\\n{bes}\\n{ges}")
            loc(f"{k}_LINEA", f"§Y${m['tile']}$§!: {ben}", f"§Y${m['tile']}$§!: {bes}")
    for t in orden_trof:
        ben, bes = _bonus_texto(trof[t]["bonus"])
        loc(f"MN_TROFEO_{t}_LINEA", f"§YTrophy: capital of ${t}$§!: {ben}", f"§YTrofeo: capital de ${t}$§!: {bes}")
        loc(f"MN_TROFEO_{t}_TT", f"§YTrophy: capital of ${t}$§!\\n{ben}\\nEarned by taking its starting capital in a war.",
            f"§YTrofeo: capital de ${t}$§!\\n{bes}\\nSe gana al tomar su capital de arranque en una guerra.")
    loc("MN_MED_SECCION", "§YMEDALS§!  (click a slot to choose)", "§YMEDALLAS§!  (tocá una casilla para elegir)")
    loc("MN_MED_TROFEO", "§YTrophy§!", "§YTrofeo§!")
    loc("MN_MED_VACIO", "—", "—")
    loc("MN_MED_LIBRE", "§gEmpty slot: click it to choose a medal.§!", "§gCasilla libre: tocala para elegir una medalla.§!")
    loc("MN_MED_TROFEO_LIBRE", "§gNo trophy: take the capital of a meganation in a war.§!",
        "§gSin trofeo: tomá la capital de una meganación en una guerra.§!")
    for s in range(1, SLOTS + 1):
        loc(f"MN_MED_SLOT_TT_{s}", f"§YMedal slot {s}§!\\n[MN_med_linea_{s}]\\nClick to choose. Empty slot: free. "
            f"Changing it: {costo} political power, then {dias} days to wait.",
            f"§YCasilla de medalla {s}§!\\n[MN_med_linea_{s}]\\nTocala para elegir. Casilla vacía: gratis. "
            f"Cambiarla: {costo} de poder político y después {dias} días de espera.")
        loc(f"MN_MED_TITULO_{s}", f"§YMEDALS§!  choosing for slot {s}", f"§YMEDALLAS§!  eligiendo para la casilla {s}")
    s4 = SLOTS + 1
    loc(f"MN_MED_SLOT_TT_{s4}", f"§YTrophy§!\\n[MN_med_linea_{s4}]\\nClick to choose among the capitals you took.",
        f"§YTrofeo§!\\n[MN_med_linea_{s4}]\\nTocalo para elegir entre las capitales que tomaste.")
    loc(f"MN_MED_TITULO_{s4}", "§YTROPHIES§!  choosing the trophy", "§YTROFEOS§!  eligiendo el trofeo")
    loc("MN_MED_TROFEOS", "§YTROPHIES§!  (one per meganation capital taken)",
        "§YTROFEOS§!  (uno por capital de meganación tomada)")
    loc("MN_MED_ESPERA_SI", f"§RYou changed a medal recently: wait {dias} days to change again.§!",
        f"§RCambiaste una medalla hace poco: esperá {dias} días para volver a cambiar.§!")
    loc("MN_MED_ESPERA_NO", f"Empty slot: free. Changing a medal: {costo} political power and {dias} days to wait.",
        f"Casilla vacía: gratis. Cambiar una medalla: {costo} de poder político y {dias} días de espera.")

    # -- la colección (otra ventana) ----------------------------------------------
    W, H = DISENO["coleccion"]
    cx, cy, cw, ch = DISENO["coleccion_celda"]
    trx, try_, trp = DISENO["coleccion_trofeos"]
    lado = DISENO["medallas"][3]
    g = ['guiTypes = {\n\tcontainerWindowType = {\n\t\tname = "mn_medallas_window"\n'
         f'\t\tposition = {{ x = {-W // 2} y = {-H // 2 + 40} }}\n\t\tsize = {{ width = {W} height = {H} }}\n'
         '\t\torientation = center\n\t\tmoveable = yes\n']
    g.append(_icon("fondo", 0, 0, "GFX_mn_ficha_coleccion_fondo"))
    g.append(_text("titulo", 24, 16, "[MN_med_titulo]", "hoi_24header", W - 120, 30))
    g.append('\t\tbuttonType = {\n\t\t\tname = "cerrar"\n\t\t\tposition = { x = %d y = 12 }\n'
             '\t\t\tspriteType = "GFX_closebutton"\n\t\t\tshortcut = "ESCAPE"\n\t\t}\n' % (W - 56))
    trig, eff, props = [], [], []
    for i in range(1, n_max + 1):
        col, fila = (i - 1) % 5, (i - 1) // 5
        x, y = cx + col * cw, cy + fila * ch
        bx = x + (cw - lado) // 2
        g.append(_icon(f"med_icono_{i}", bx + (lado - 64) // 2, y + (lado - 64) // 2, "GFX_mn_ficha_medalla_vacia"))
        g.append(_icon(f"med_bloq_{i}", bx + (lado - 64) // 2, y + (lado - 64) // 2, "GFX_mn_ficha_medalla_bloqueada",
                       "\n\t\t\talwaystransparent = yes"))
        g.append(f'\t\tbuttonType = {{\n\t\t\tname = "med_{i}"\n\t\t\tposition = {{ x = {bx} y = {y} }}\n'
                 f'\t\t\tspriteType = "GFX_mn_ficha_medalla_marco"\n\t\t\tpdx_tooltip = "MN_MED_TT_{i}"\n\t\t}}\n')
        g.append(_icon(f"med_uso_{i}", bx + lado - 14, y - 4, "GFX_mn_ficha_medalla_en_uso", "\n\t\t\talwaystransparent = yes"))
        g.append(_text(f"med_nombre_{i}", x + 2, y + lado + 2, f"[MN_med_nom_{i}]", "hoi_16mbs", cw - 4, 30, "centre"))
        loc(f"MN_MED_TT_{i}", f"[MN_med_tt_{i}]", f"[MN_med_tt_{i}]")
        props.append(f'\t\t\tmed_icono_{i} = {{ image = "[MN_med_img_{i}]" }}\n')
        hay = " ".join(f"tag = {t}" for t, l in meds.items() if len(l) >= i)
        for el in ("med_icono", "med_nombre", "med_bloq", "med_uso", "med"):
            extra = {"med_bloq": " NOT = { MN_med_ok_%d = yes }" % i,
                     "med_uso": " MN_med_en_uso_%d = yes" % i}.get(el, "")
            trig.append(f"\t\t\t{el}_{i}_visible = {{ OR = {{ {hay} }}{extra} }}\n")
        trig.append(f"\t\t\tmed_{i}_click_enabled = {{ MN_med_ok_{i} = yes check_variable = {{ MN_med_sel < {SLOTS + 1} }} "
                    f"MN_med_puede_cambiar = yes NOT = {{ OR = {{ " + " ".join(
                        f"AND = {{ check_variable = {{ MN_med_sel = {s} }} check_variable = {{ MN_medalla_{s} = {i} }} }}"
                        for s in range(1, SLOTS + 1)) + " } } }\n")
        eff.append(f"\t\t\tmed_{i}_click = {{ set_temp_variable = {{ mn_i = {i} }} MN_med_poner = yes }}\n")
    g.append(_text("trofeos_rotulo", trx, try_ - 24, "MN_MED_TROFEOS", "hoi_16mbs", W - 60, 18))
    for j, t in enumerate(orden_trof, start=1):
        x = trx + (j - 1) * trp
        g.append(_icon(f"trofeo_icono_{j}", x + (lado - 64) // 2, try_ + (lado - 64) // 2, f"GFX_mn_trofeo_{t}"))
        g.append(_icon(f"trofeo_bloq_{j}", x + (lado - 64) // 2, try_ + (lado - 64) // 2, "GFX_mn_ficha_medalla_bloqueada",
                       "\n\t\t\talwaystransparent = yes"))
        g.append(f'\t\tbuttonType = {{\n\t\t\tname = "trofeo_{j}"\n\t\t\tposition = {{ x = {x} y = {try_} }}\n'
                 f'\t\t\tspriteType = "GFX_mn_ficha_medalla_trofeo"\n\t\t\tpdx_tooltip = "MN_TROFEO_{t}_TT"\n\t\t}}\n')
        g.append(_icon(f"trofeo_uso_{j}", x + lado - 14, try_ - 4, "GFX_mn_ficha_medalla_en_uso", "\n\t\t\talwaystransparent = yes"))
        gano = f"has_country_flag = MEGANATIONS_absorbido_{t}"
        trig.append(f"\t\t\ttrofeo_icono_{j}_visible = {{ NOT = {{ tag = {t} }} }}\n")
        trig.append(f"\t\t\ttrofeo_{j}_visible = {{ NOT = {{ tag = {t} }} }}\n")
        trig.append(f"\t\t\ttrofeo_bloq_{j}_visible = {{ NOT = {{ tag = {t} }} NOT = {{ {gano} }} }}\n")
        trig.append(f"\t\t\ttrofeo_uso_{j}_visible = {{ check_variable = {{ MN_trofeo = {j} }} }}\n")
        trig.append(f"\t\t\ttrofeo_{j}_click_enabled = {{ {gano} check_variable = {{ MN_med_sel = {SLOTS + 1} }} "
                    f"MN_med_puede_cambiar = yes NOT = {{ check_variable = {{ MN_trofeo = {j} }} }} }}\n")
        eff.append(f"\t\t\ttrofeo_{j}_click = {{ set_temp_variable = {{ mn_i = {j} }} MN_med_poner = yes }}\n")
    g.append(_text("espera", 24, H - 32, "[MN_med_espera]", "hoi_16mbs", W - 48, 20))
    g.append("\t}\n}\n")
    ctx.write_text("interface/meganations_medallas.gui", banner_for(SOURCE) + "".join(g))
    quien = " ".join(f"tag = {t}" for t in meds)
    sg = ("scripted_gui = {\n\tmn_medallas = {\n\t\tcontext_type = player_context\n"
          '\t\twindow_name = "mn_medallas_window"\n'
          f"\t\tvisible = {{ OR = {{ {quien} }} has_country_flag = MN_medallas_abierta has_country_flag = MEGANATIONS_ficha_abierta }}\n"
          "\t\teffects = {\n\t\t\tcerrar_click = { clr_country_flag = MN_medallas_abierta }\n" + "".join(eff) + "\t\t}\n"
          "\t\tproperties = {\n" + "".join(props) + "\t\t}\n"
          "\t\ttriggers = {\n" + "".join(trig) + "\t\t}\n\t\tai_enabled = { always = no }\n\t}\n}\n")
    ctx.write_text("common/scripted_guis/meganations_medallas.txt", banner_for(SOURCE) + sg)
    total = sum(len(v) for v in meds.values())
    ctx.note(f"medallas: {total} en {len(meds)} países (máx. {MAX_MEDALLAS} cada uno), {len(orden_trof)} trofeos; "
             f"cambiar cuesta {costo} de poder político y {dias} días")
