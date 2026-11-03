"""Agentes de inteligencia propios de cada potencia (2026-11-03).

Pedido del usuario: "pedidos de arte para agentes de inteligencia/espías por
cada facción, unos 5". Con los retratos ya hechos (spec/33_agentes.yaml):
cada potencia arranca con sus agentes en la lista de reclutables de su
agencia, con nombre, rasgos y retrato propios.

Los agentes no son personajes de common/characters: el juego los crea con
create_operative_leader (gfx = sprite del retrato). Se crean una sola vez,
en el evento de arranque de cada potencia, después de crear la agencia
(effects.py, efecto intelligence_agency), y solo con La Résistance.

Produce:
  common/scripted_effects/meganations_agentes.txt  (MEGANATIONS_crear_agentes)
  interface/meganations_agentes.gfx                 (GFX_portrait_<id>)
  gfx/leaders/<TAG>/agentes/<id>.dds
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted, banner_for, render
from . import effects as _effects

SOURCE = "tools/gen/emitters/agentes.py (pedido del usuario 2026-11-03)"
EFECTO = "MEGANATIONS_crear_agentes"
FLAG = "MN_agentes_creados"
GENEROS = {"male", "female"}


def emit(ctx: BuildContext) -> None:
    _effects.CREAR_AGENTES = False
    agentes = ctx.spec.raw.get("agentes") or {}
    if not agentes:
        return
    repo = ctx.spec.root.parent
    sprites = Block()
    por_pais = Block()
    vistos: set[str] = set()
    total = 0
    for tag, lista in agentes.items():
        if ctx.spec.country(tag) is None:
            raise SpecError(f"agentes: el país '{tag}' no existe", where="33_agentes.yaml")
        crear = Block([("original_tag", tag)])
        for a in lista or []:
            aid = a["id"]
            if aid in vistos:
                raise SpecError(f"agentes: '{aid}' repetido", where="33_agentes.yaml")
            vistos.add(aid)
            if a.get("genero") not in GENEROS:
                raise SpecError(f"agentes: '{aid}' sin genero male/female", where="33_agentes.yaml")
            asset = f"assets/{tag}/agentes/{aid}.dds"
            if not (repo / asset).exists():
                # el retrato todavía no llegó: sin él saldría con uno genérico
                ctx.note(f"agentes: {aid} espera su retrato ({asset})")
                continue
            tex = f"gfx/leaders/{tag}/agentes/{aid}.dds"
            ctx.copy_asset(asset, tex)
            gfx = f"GFX_portrait_{aid}"
            sprites.add("spriteType", Block([("name", Quoted(gfx)), ("texturefile", Quoted(tex))]))
            op = Block()
            op.add("name", Quoted(a["nombre"]))
            op.add("gfx", gfx)
            op.add("gender", a["genero"])
            rasgos = Block()
            for r in a.get("rasgos") or []:
                rasgos.add(None, r)
            op.add("traits", rasgos)
            op.add("nationalities", Block([(None, tag)]))
            op.add("bypass_recruitment", False)   # a la lista de reclutables
            op.add("available_to_spy_master", True)
            crear.add("create_operative_leader", op)
            total += 1
        por_pais.add("if", Block([("limit", Block([("original_tag", tag)]))]
                                 + [e for e in crear.entries if e[0] != "original_tag"]))
    if not total:
        return
    _effects.CREAR_AGENTES = True
    cuerpo = Block([
        ("if", Block([
            ("limit", Block([("has_dlc", Quoted("La Resistance")),
                             ("NOT", Block([("has_country_flag", FLAG)]))])),
            ("set_country_flag", FLAG),
        ] + por_pais.entries)),
    ])
    ctx.write_text("common/scripted_effects/meganations_agentes.txt",
                   banner_for(SOURCE) + render(Block([(EFECTO, cuerpo)])))
    ctx.write_text("interface/meganations_agentes.gfx",
                   banner_for(SOURCE) + render(Block([("spriteTypes", sprites)])))
    ctx.note(f"agentes: {total} agentes con retrato propio")
    ctx.verify_keys("effects", {"create_operative_leader": SOURCE, "set_country_flag": SOURCE})
    ctx.verify_keys("triggers", {"has_dlc": SOURCE, "has_country_flag": SOURCE, "original_tag": SOURCE})
