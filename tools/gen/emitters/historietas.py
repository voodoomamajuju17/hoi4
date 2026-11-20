"""La Historieta (spec/46_historietas.yaml, 2026-11-18): la introducción de cada nación en 8 viñetas.

Pedido: "Toda esta pantalla es horrible, fijate si podes diseñar una historia grafica/comic, distinta
para cada nacion, con muy pocas palabras explicando todo esto, panel original, pedi toda el arte que
quieras. Maximo 8 paneles".

Una ventana propia por nación (1160x740, como la Lámina): la página entera es UNA imagen
(assets/historietas/paginas/<TAG>.dds, armada por tools/arte/historietas.py con las viñetas, los
bordes de la nación y los recuadros vacíos) y el juego escribe encima el título, el texto de cada
viñeta (negro, en su recuadro), el lema y el botón. La geometría la comparten los dos:
tools/gen/historietas_geo.py. Se abre con la bandera MN_historieta_abierta (la pone la introducción
oculta, ver tools/gen/historietas_spec.py); Continuar la cierra y manda los avisos que esperaban.
"""

from __future__ import annotations

from .. import historietas_geo as geo
from ..context import BuildContext
from ..pdx import banner_for

SOURCE = "tools/gen/emitters/historietas.py (la Historieta, 2026-11-18)"
TEX = "gfx/interface/meganations/historietas"
FLAG = "MN_historieta_abierta"
LOC = "meganations_historietas"


def _icon(name, x, y, sp):
    return (f'\t\ticonType = {{\n\t\t\tname = "{name}"\n\t\t\tspriteType = "{sp}"\n'
            f'\t\t\tposition = {{ x = {x} y = {y} }}\n\t\t\talwaystransparent = yes\n\t\t}}\n')


def _text(name, x, y, t, font, w, h, fmt="left"):
    return (f'\t\tinstantTextBoxType = {{\n\t\t\tname = "{name}"\n\t\t\tposition = {{ x = {x} y = {y} }}\n'
            f'\t\t\tfont = "{font}"\n\t\t\ttext = "{t}"\n\t\t\tmaxWidth = {w}\n\t\t\tmaxHeight = {h}\n'
            f'\t\t\tformat = {fmt}\n\t\t\tfixedsize = yes\n\t\t\talwaystransparent = yes\n\t\t}}\n')


def emit(ctx: BuildContext) -> None:
    hist = ctx.spec.raw.get("historietas") or {}
    activas = {t: c for t, c in hist.items() if c.get("activa")}
    if not hist:
        return
    sin = sorted(set(hist) - set(activas))
    if sin:
        ctx.warn(f"Historieta: falta la página de {', '.join(sin)} (tools/arte/historietas.py); "
                 "esas naciones siguen con la introducción vieja")
    if not activas:
        return
    gfx = ["spriteTypes = {\n"]
    gui = ["guiTypes = {\n"]
    sg = ["scripted_gui = {\n"]
    efx = []
    ctx.loc.define_and_reference("MN_HISTORIETA_CONTINUAR", en="Continue", es="Continuar", file=LOC,
                                 origin="historietas")
    ctx.loc.define_and_reference("MN_HISTORIETA_SALTAR", en="I don't care about lore", es="No me interesa el lore",
                                 file=LOC, origin="historietas")
    for tag, cfg in sorted(activas.items()):
        ctx.copy_asset(f"assets/historietas/paginas/{tag}.dds", f"{TEX}/{tag}.dds")
        sprite = f"GFX_mn_historieta_{tag}"
        gfx.append(f'\tspriteType = {{\n\t\tname = "{sprite}"\n\t\ttexturefile = "{TEX}/{tag}.dds"\n\t}}\n')
        pag = geo.pagina(cfg)
        k = f"MN_HIST_{tag}"
        ctx.loc.define_and_reference(f"{k}_TITULO", en=cfg["titulo"]["english"], es=cfg["titulo"]["spanish"],
                                     file=LOC, origin="historietas")
        ctx.loc.define_and_reference(f"{k}_LEMA", en=f"“{cfg['boton']['english']}”",
                                     es=f"“{cfg['boton']['spanish']}”", file=LOC, origin="historietas")
        win = f"mn_historieta_{tag}_window"
        g = [f'\tcontainerWindowType = {{\n\t\tname = "{win}"\n'
             f'\t\tposition = {{ x = {-geo.W // 2} y = {-geo.H // 2} }}\n'
             f'\t\tsize = {{ width = {geo.W} height = {geo.H} }}\n'
             '\t\torientation = center\n\t\tmoveable = yes\n',
             _icon("pagina", 0, 0, sprite)]
        tx, ty, tw, th = geo.TITULO
        g.append(_text("titulo", tx, ty, f"{k}_TITULO", "hoi_36header", tw, th, "centre"))
        for n, (v, (cx, cy, cw, ch)) in enumerate(zip(cfg["vinetas"], pag["recuadros"]), 1):
            clave = f"{k}_{n}"
            ctx.loc.define_and_reference(clave, en="§b" + v["texto"]["english"] + "§!",
                                         es="§b" + v["texto"]["spanish"] + "§!", file=LOC, origin="historietas")
            g.append(_text(f"vineta_{n}", cx + 8, cy + 6, clave, "hoi_18b", cw - 16, ch - 8))
        lx, ly, lw, lh = geo.LEMA_TEXTO
        g.append(_text("lema", lx, ly, f"{k}_LEMA", "hoi_20bs", lw, lh))
        bx, by = geo.BOTON
        g.append('\t\tbuttonType = {\n\t\t\tname = "continuar"\n'
                 f'\t\t\tposition = {{ x = {bx} y = {by} }}\n'
                 '\t\t\tspriteType = "GFX_mn_ficha_boton_accion"\n\t\t\ttext = "MN_HISTORIETA_CONTINUAR"\n'
                 '\t\t\tbuttonFont = "hoi_18mbs"\n\t\t\tshortcut = "RETURN"\n\t\t}\n')
        sx, sy = geo.SALTAR
        g.append('\t\tbuttonType = {\n\t\t\tname = "saltar"\n'
                 f'\t\t\tposition = {{ x = {sx} y = {sy} }}\n'
                 '\t\t\tspriteType = "GFX_mn_ficha_boton_accion"\n\t\t\ttext = "MN_HISTORIETA_SALTAR"\n'
                 '\t\t\tbuttonFont = "hoi_16mbs"\n\t\t\tshortcut = "ESCAPE"\n\t\t}\n')
        g.append("\t}\n")
        gui += g
        cerrar = f"MN_historieta_cerrar_{tag}"
        efx.append(f"{cerrar} = {{\n\tclr_country_flag = {FLAG}\n"
                   + "".join(f"\tcountry_event = {{ id = {e} }}\n" for e in cfg["sigue"]) + "}\n")
        # 2026-11-20 ("debería haber un botón 'no me interesa el lore' y saltar todo"): cierra sin los
        # avisos que siguen, pero con lo que daban
        saltar = f"MN_historieta_saltar_{tag}"
        efx.append(f"{saltar} = {{\n\tclr_country_flag = {FLAG}\n"
                   + (f"\tadd_political_power = {cfg['sigue_pp']}\n" if cfg.get("sigue_pp") else "") + "}\n")
        sg.append(f"\tmn_historieta_{tag} = {{\n\t\tcontext_type = player_context\n"
                  f'\t\twindow_name = "{win}"\n'
                  f"\t\tvisible = {{ original_tag = {tag} has_country_flag = {FLAG} }}\n"
                  f"\t\teffects = {{\n\t\t\tcontinuar_click = {{ {cerrar} = yes }}\n"
                  f"\t\t\tsaltar_click = {{ {saltar} = yes }}\n\t\t}}\n"
                  "\t\tai_enabled = { always = no }\n\t}\n")
    gfx.append("}\n")
    gui.append("}\n")
    sg.append("}\n")
    ctx.write_text("interface/meganations_historietas.gfx", banner_for(SOURCE) + "".join(gfx))
    ctx.write_text("interface/meganations_historietas.gui", banner_for(SOURCE) + "".join(gui))
    ctx.write_text("common/scripted_guis/meganations_historietas.txt", banner_for(SOURCE) + "".join(sg))
    ctx.write_text("common/scripted_effects/meganations_historietas.txt", banner_for(SOURCE) + "".join(efx))
    ctx.note(f"Historieta: {len(activas)} naciones con su página de viñetas "
             f"({sum(len(c['vinetas']) for c in activas.values())} viñetas)")
