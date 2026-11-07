"""La Lámina de las aventuras (2026-11-06).

Pedido: "necesito que cuando la aventura, cualquiera sea de las meganaciones, se note
que NO es un evento más: cuadro más grande, más texto, más personalidad, imagen
impactante en tono obra de arte creada sobre el hecho."

Un capítulo (o la presentación, o un final) con `plate` en spec/37_aventuras_*.yaml
no salta directo: primero se abre la Lámina, una ventana propia de 1020x740 (como la
Ficha del Líder) con la pintura grande (960x408, un óleo de gran formato), el título,
el nombre de la saga, el relato largo y el marco de la nación. "Continuar" la cierra
y recién ahí llega el evento con las opciones. La IA no ve la Lámina: le llega el
evento directo.

  - el evento que abre la Lámina es el del capítulo + ABRE (oculto): fija
    MN_lamina = k y la bandera MN_lamina_abierta;
  - MN_lamina_continuar (efecto con guion) manda el evento k y cierra;
  - la pintura: assets/aventuras/laminas/<espacio>.<id>.dds si llegó, si no
    assets/ui/laminas/vacia.dds (una tela oscura, sin dibujo).
Arte de la ventana: tools/arte/ficha.py laminas (fondo, marcos, vacía).
"""

from __future__ import annotations

from ..context import BuildContext
from ..pdx import banner_for

SOURCE = "tools/gen/emitters/laminas.py (la Lámina de las aventuras, 2026-11-06)"
ABRE = 5000          # id del evento que abre la Lámina = id del capítulo + ABRE
W, H = 1020, 740
PINTURA = (30, 96, 960, 408)
TEXTO = (40, 516, 900, 168)
TEX = "gfx/interface/meganations/laminas"
ESTILOS = {"EFE": "efe", "FCU": "fcu", "ASC": "asc", "ZAL": "zal", "ZJP": "zjp",
           "HSN": "hsn", "NAS": "nas", "SHD": "shd", "APF": "apf", "NRE": "nre"}


def arte_de(ns: str, eid: int) -> str:
    """Dónde va la pintura de esa lámina (tools/arte la pide con ese nombre)."""
    return f"assets/aventuras/laminas/{ns}.{eid}.dds"


def opener(ns: str, eid: int, k: int, when: dict, arrive: list[dict]) -> dict:
    """El evento oculto que abre la Lámina k (o, en la IA, manda el capítulo directo)."""
    return {
        "id": eid + ABRE, "trigger": "effect", "hidden": True, "src": "user_request",
        "when": dict(when), "immediate": list(arrive),
        "title": {"english": "The Plate", "spanish": "La Lámina"},
        "desc": {"english": "Hidden.", "spanish": "Oculto."},
        "options": [{"name": {"english": "Go on.", "spanish": "Seguir."}, "effects": [
            {"effect": "if", "when": {"is_ai": True},
             "then": [{"effect": "event", "id": f"{ns}.{eid}", "days": 0}],
             "else": [{"effect": "set_variable", "var": "MN_lamina", "value": k},
                      {"effect": "flag", "value": "MN_lamina_abierta"}]}]}],
    }


def emit(ctx: BuildContext, plates: list[dict]) -> None:
    """plates: [{k, ns, eid, title, text, saga}] de todas las sagas con Lámina."""
    if not plates:
        return
    repo = ctx.spec.root.parent
    base = repo / "assets" / "ui" / "laminas"
    if not (base / "fondo.dds").exists():
        ctx.warn("Lámina: falta el arte de la ventana (tools/arte/ficha.py laminas); las aventuras van sin Lámina")
        return
    gfx = ["spriteTypes = {\n"]

    def sprite(name: str, tex: str) -> None:
        gfx.append(f'\tspriteType = {{\n\t\tname = "{name}"\n\t\ttexturefile = "{tex}"\n\t}}\n')

    for pieza in sorted(p.stem for p in base.glob("*.dds")):
        ctx.copy_asset(f"assets/ui/laminas/{pieza}.dds", f"{TEX}/{pieza}.dds")
        sprite(f"GFX_mn_lamina_{pieza}", f"{TEX}/{pieza}.dds")
    con_arte = 0
    for p in plates:
        own = arte_de(p["ns"], p["eid"])
        if (repo / own).exists():
            ctx.copy_asset(own, f"{TEX}/pinturas/{p['ns']}.{p['eid']}.dds")
            sprite(f"GFX_mn_lamina_{p['k']}", f"{TEX}/pinturas/{p['ns']}.{p['eid']}.dds")
            p["gfx"] = f"GFX_mn_lamina_{p['k']}"
            con_arte += 1
        else:
            p["gfx"] = "GFX_mn_lamina_vacia"
    gfx.append("}\n")
    ctx.write_text("interface/meganations_laminas.gfx", banner_for(SOURCE) + "".join(gfx))

    # textos: título, saga y relato de cada lámina
    sl = []
    for campo in ("img", "titulo", "saga", "texto"):
        sl.append(f"defined_text = {{\n\tname = MN_lamina_{campo}\n")
        for p in plates:
            if campo == "img":
                clave = p["gfx"]
            else:
                clave = f"MN_LAMINA_{p['k']}_{campo.upper()}"
                src = {"titulo": p["title"], "saga": p["saga"], "texto": p["text"]}[campo]
                ctx.loc.define_and_reference(clave, en=src["english"], es=src["spanish"],
                                             file="meganations_laminas", origin="laminas")
            sl.append(f"\ttext = {{ trigger = {{ check_variable = {{ MN_lamina = {p['k']} }} }} "
                      f"localization_key = {clave} }}\n")
        sl.append("\ttext = { localization_key = %s }\n}\n" % ("GFX_mn_lamina_vacia" if campo == "img" else "MN_LAMINA_VACIA"))
    sl.append("defined_text = {\n\tname = MN_lamina_marco\n")
    for tag, est in ESTILOS.items():
        if (base / f"marco_{est}.dds").exists():
            sl.append(f"\ttext = {{ trigger = {{ tag = {tag} }} localization_key = GFX_mn_lamina_marco_{est} }}\n")
    sl.append("\ttext = { localization_key = GFX_mn_lamina_sin_marco }\n}\n")
    ctx.write_text("common/scripted_localisation/meganations_laminas.txt", banner_for(SOURCE) + "".join(sl))
    import re
    for clave in sorted(set(re.findall(r"localization_key = (GFX_\w+)", "".join(sl)))):
        ctx.loc.define_and_reference(clave, en=clave, es=clave, file="meganations_laminas", origin="laminas")
    ctx.loc.define_and_reference("MN_LAMINA_VACIA", en="...", es="...", file="meganations_laminas", origin="laminas")
    ctx.loc.define_and_reference("MN_LAMINA_CONTINUAR", en="Continue", es="Continuar",
                                 file="meganations_laminas", origin="laminas")
    # la ventana
    px, py, pw, ph = PINTURA
    tx, ty, tw, th = TEXTO

    def icon(name, x, y, sp, extra=""):
        return (f'\t\ticonType = {{\n\t\t\tname = "{name}"\n\t\t\tspriteType = "{sp}"\n'
                f'\t\t\tposition = {{ x = {x} y = {y} }}{extra}\n\t\t}}\n')

    def text(name, x, y, t, font, w, h, fmt="left"):
        return (f'\t\tinstantTextBoxType = {{\n\t\t\tname = "{name}"\n\t\t\tposition = {{ x = {x} y = {y} }}\n'
                f'\t\t\tfont = "{font}"\n\t\t\ttext = "{t}"\n\t\t\tmaxWidth = {w}\n\t\t\tmaxHeight = {h}\n'
                f'\t\t\tformat = {fmt}\n\t\t\tfixedsize = yes\n\t\t}}\n')

    g = ['guiTypes = {\n\tcontainerWindowType = {\n\t\tname = "mn_lamina_window"\n'
         f'\t\tposition = {{ x = {-W // 2} y = {-H // 2} }}\n\t\tsize = {{ width = {W} height = {H} }}\n'
         '\t\torientation = center\n\t\tmoveable = yes\n',
         icon("fondo", 0, 0, "GFX_mn_lamina_fondo"),
         icon("pintura", px, py, "GFX_mn_lamina_vacia"),
         icon("marco", 0, 0, "GFX_mn_lamina_sin_marco", "\n\t\t\talwaystransparent = yes"),
         text("titulo", 40, 18, "[MN_lamina_titulo]", "hoi_36header", W - 80, 44, "centre"),
         text("saga", 40, 62, "[MN_lamina_saga]", "hoi_18mbs", W - 80, 22, "centre"),
         text("relato", tx, ty, "[MN_lamina_texto]", "hoi_18mbs", tw, th),
         '\t\tbuttonType = {\n\t\t\tname = "continuar"\n'
         f'\t\t\tposition = {{ x = {W - 250} y = {H - 50} }}\n'
         '\t\t\tspriteType = "GFX_mn_ficha_boton_accion"\n\t\t\ttext = "MN_LAMINA_CONTINUAR"\n'
         '\t\t\tbuttonFont = "hoi_18mbs"\n\t\t\tshortcut = "RETURN"\n\t\t}\n',
         "\t}\n}\n"]
    ctx.write_text("interface/meganations_laminas.gui", banner_for(SOURCE) + "".join(g))

    # seguir: manda el capítulo de la lámina abierta y cierra
    cont = ["MN_lamina_continuar = {\n"]
    for p in plates:
        cont.append(f"\tif = {{ limit = {{ check_variable = {{ MN_lamina = {p['k']} }} }} "
                    f"country_event = {{ id = {p['ns']}.{p['eid']} }} }}\n")
    cont.append("\tclr_country_flag = MN_lamina_abierta\n\tset_variable = { MN_lamina = 0 }\n}\n")
    ctx.write_text("common/scripted_effects/meganations_laminas.txt", banner_for(SOURCE) + "".join(cont))
    sg = ("scripted_gui = {\n\tmn_lamina = {\n\t\tcontext_type = player_context\n"
          '\t\twindow_name = "mn_lamina_window"\n\t\tvisible = { has_country_flag = MN_lamina_abierta }\n'
          "\t\teffects = {\n\t\t\tcontinuar_click = { MN_lamina_continuar = yes }\n\t\t}\n"
          '\t\tproperties = {\n\t\t\tpintura = { image = "[MN_lamina_img]" }\n'
          '\t\t\tmarco = { image = "[MN_lamina_marco]" }\n\t\t}\n'
          "\t\tai_enabled = { always = no }\n\t}\n}\n")
    ctx.write_text("common/scripted_guis/meganations_laminas.txt", banner_for(SOURCE) + sg)
    ctx.note(f"Lámina de las aventuras: {len(plates)} láminas ({con_arte} con su pintura; el resto con la tela vacía)")
