"""Agencias de inteligencia propias de las meganaciones (2026-10-29).

Captura del usuario: al crear la agencia salía el "Research and Analysis Wing"
de la India de 1936. create_intelligence_agency elige entre las agencias de
common/intelligence_agencies; el mod no tenía ninguna, así que el juego daba
una de las suyas. Pedido: "usá la imagen del espíritu" (el Servicio de
Inteligencia de cada potencia, assets/<TAG>/ideas/<TAG>_servicio_de_inteligencia.dds).

Produce:
  common/intelligence_agencies/meganations_agencias.txt
  interface/meganations_agencias.gfx
  gfx/interface/intelligence_agency_logos/meganations/<TAG>.dds
"""

from __future__ import annotations

from ..context import BuildContext
from ..pdx import Block, Quoted, banner_for, render

SOURCE = "tools/gen/emitters/agencias.py (pedido del usuario 2026-10-29)"

NOMBRES = {
    "EFE": "Las Raíces del Imperio",
    "ASC": "Dirección de Vigilancia Algorítmica",
    "FCU": "Consultora de Riesgo Consolidado",
    "HSN": "Oficina de Seguros y Manifiestos",
    "NAS": "Los Ojos del Inti",
    "SHD": "Oficina del Caudal Oculto",
    "APF": "Consejo de las Voces Lejanas",
    "NRE": "Frumentarii",
}


def emit(ctx: BuildContext) -> None:
    repo = ctx.spec.root.parent
    agencias = Block()
    sprites = Block()
    hechas = []
    for c in ctx.spec.countries:
        if not c.is_major:
            continue
        src = repo / "assets" / c.tag / "ideas" / f"{c.tag}_servicio_de_inteligencia.dds"
        if not src.exists():
            continue
        tex = f"gfx/interface/intelligence_agency_logos/meganations/{c.tag}.dds"
        ctx.copy_asset(f"assets/{c.tag}/ideas/{c.tag}_servicio_de_inteligencia.dds", tex)
        gfx = f"GFX_intelligence_agency_logo_MEGANATIONS_{c.tag}"
        sprites.add("spriteType", Block([("name", Quoted(gfx)), ("texturefile", Quoted(tex))]))
        nombre = NOMBRES.get(c.tag, f"Servicio de Inteligencia de {c.tag}")
        agencias.add("intelligence_agency", Block([
            ("picture", gfx),
            ("names", Block([(None, Quoted(nombre))])),
            ("default", Block([("original_tag", c.tag)])),
            ("available", Block([("original_tag", c.tag)])),
        ]))
        hechas.append(c.tag)
    if not hechas:
        return
    ctx.write_text("common/intelligence_agencies/meganations_agencias.txt", banner_for(SOURCE) + render(agencias))
    ctx.write_text("interface/meganations_agencias.gfx",
                   banner_for(SOURCE) + render(Block([("spriteTypes", sprites)])))
    ctx.note(f"agencias: propias con el emblema del Servicio de Inteligencia ({', '.join(hechas)})")
