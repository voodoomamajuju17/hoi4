"""El Desolador (2026-11-20): la unidad única de Eurasia, un batallón nuevo desde cero.

Pedido: "Gana una unidad unica: El desolador, inspirado en el personaje iraqui de redalert2. Automaticamente
gana 3 divisiones desolators" / "Desolador de cero". Diseño propio: un soldado en traje de plomo, con
máscara de gas y un cañón de radiación; no pisa ninguna unidad del juego.

  - common/units/meganations_desolador.txt: el batallón `desolador` (infantería pesada: mucho ataque contra
    blandos, buena perforación, poca organización, caro en manpower). `active = no`: nadie lo tiene.
  - common/technologies/meganations_desolador.txt: ZWE_desolador, una tecnología sin carpeta que no se
    investiga (`allow = { always = no }`); la da el foco Los Desoladores (set_technology) y habilita el batallón.
  - interface: sus íconos (designer, mapa, texto y los de cuartel general, para no repetir el
    "Couldnt find texticon" del auto blindado). Usan los de la infantería hasta que llegue su arte
    (assets/ZWE/unidades/desolador_icono.dds y desolador_mapa.dds).
El modelo 3D es el de la infantería de Eurasia (sprite = infantry).
"""

from __future__ import annotations

from ..context import BuildContext
from ..pdx import banner_for

SOURCE = "tools/gen/emitters/desolador.py (el Desolador de Eurasia, 2026-11-20)"
LOC = "meganations_desolador"

UNIDAD = """sub_units = {
	desolador = {
		sprite = infantry
		map_icon_category = infantry
		priority = 600
		ai_priority = 200
		active = no
		affects_speed = yes
		type = { infantry }
		group = infantry
		categories = { category_front_line category_light_infantry category_all_infantry category_army }
		combat_width = 2
		max_strength = 22
		max_organisation = 25
		default_morale = 0.3
		manpower = 1500
		training_time = 150
		suppression = 1
		weight = 0.6
		supply_consumption = 0.09
		soft_attack = 0.6
		hard_attack = 0.3
		ap_attack = 0.4
		breakthrough = 0.3
		need = {
			infantry_equipment = 150
			support_equipment = 10
		}
	}
}
"""

TECNOLOGIA = """technologies = {
	ZWE_desolador = {
		enable_subunits = { desolador }
		research_cost = 1
		start_year = 2100
		allow = { always = no }
		ai_will_do = { factor = 0 }
	}
}
"""


def emit(ctx: BuildContext) -> None:
    repo = ctx.spec.root.parent
    ctx.write_text("common/units/meganations_desolador.txt", banner_for(SOURCE) + UNIDAD)
    ctx.write_text("common/technologies/meganations_desolador.txt", banner_for(SOURCE) + TECNOLOGIA)
    icono = "gfx/interface/counters/divisions_large/unit_infantry_icon.dds"
    mapa = "gfx/interface/counters/divisions_small/onmap_unit_infantry_icon.dds"
    chico = "gfx/texticons/unit_infantry_icon_small.dds"
    for propio, cual in (("desolador_icono", "icono"), ("desolador_mapa", "mapa")):
        if (repo / "assets" / "ZWE" / "unidades" / f"{propio}.dds").exists():
            dest = f"gfx/interface/meganations/unidades/{propio}.dds"
            ctx.copy_asset(f"assets/ZWE/unidades/{propio}.dds", dest)
            if cual == "icono":
                icono = dest
            else:
                mapa = dest
    sprites = []
    for pre in ("unit", "unit_hq"):
        sprites += [(f"GFX_{pre}_desolador_icon_medium", icono, 2), (f"GFX_{pre}_desolador_icon_medium_white", mapa, 2),
                    (f"GFX_{pre}_desolador_icon_small", chico, 2)]
    ctx.write_text("interface/meganations_desolador.gfx", banner_for(SOURCE) + "spriteTypes = {\n" + "".join(
        f'\tspriteType = {{\n\t\tname = "{n}"\n\t\ttexturefile = "{t}"\n\t\tlegacy_lazy_load = no\n'
        f"\t\tnoOfFrames = {k}\n\t}}\n" for n, t, k in sprites) + "}\n")
    for clave, en, es in (
            ("desolador", "Desolator", "Desolador"),
            ("desolador_desc", "Volunteers in lead armour with a radiation cannon. Where they pass, nothing grows for a hundred years. "
             "Huge attack against infantry, little organisation, expensive in manpower.",
             "Voluntarios con armadura de plomo y un cañón de radiación. Por donde pasan, no crece nada en cien años. "
             "Mucho ataque contra infantería, poca organización y caros en manpower."),
            ("ZWE_desolador", "The Desolators", "Los Desoladores"),
            ("ZWE_desolador_desc", "Only the Eurasian steppe builds them.", "Solo los construye la estepa de Eurasia.")):
        ctx.loc.define_and_reference(clave, en=en, es=es, file=LOC, origin="desolador")
    ctx.note("Desolador: batallón nuevo `desolador` y tecnología ZWE_desolador (la da el foco Los Desoladores, "
             "con 3 divisiones)")
