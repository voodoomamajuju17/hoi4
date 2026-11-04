"""Agentes de inteligencia propios de cada potencia (2026-11-03).

Pedido del usuario: "pedidos de arte para agentes de inteligencia/espías por
cada facción, unos 5". Con los retratos ya hechos (spec/33_agentes.yaml):
cada potencia arranca con sus agentes en la lista de reclutables de su
agencia, con nombre, rasgos y retrato propios.

Los agentes no son personajes de common/characters: el juego los crea con
create_operative_leader (gfx = sprite del retrato). Se crean una sola vez,
en el evento de arranque de cada potencia, después de crear la agencia
(effects.py, efecto intelligence_agency), y solo con La Résistance.
Gran Bretaña y Japón (2026-11-04): MEGANATIONS_agentes_<TAG>, desde su pulso
mensual, cuando ya tienen agencia; los británicos según su camino.

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


def _operativo(ctx: BuildContext, tag: str, a: dict, sprites: Block) -> Block | None:
    aid = a["id"]
    if a.get("genero") not in GENEROS:
        raise SpecError(f"agentes: '{aid}' sin genero male/female", where="33_agentes.yaml")
    asset = f"assets/{tag}/agentes/{aid}.dds"
    if not (ctx.spec.root.parent / asset).exists():
        # el retrato todavía no llegó: sin él saldría con uno genérico
        ctx.note(f"agentes: {aid} espera su retrato ({asset})")
        return None
    tex = f"gfx/leaders/{tag}/agentes/{aid}.dds"
    ctx.copy_asset(asset, tex)
    gfx = f"GFX_portrait_{aid}"
    sprites.add("spriteType", Block([("name", Quoted(gfx)), ("texturefile", Quoted(tex))]))
    op = Block()
    op.add("name", Quoted(a["nombre"]))
    op.add("gfx", gfx)
    op.add("gender", a["genero"])
    op.add("traits", Block([(None, r) for r in a.get("rasgos") or []]))
    op.add("nationalities", Block([(None, tag)]))
    op.add("bypass_recruitment", False)   # a la lista de reclutables
    op.add("available_to_spy_master", True)
    return op


def emit(ctx: BuildContext) -> None:
    _effects.CREAR_AGENTES = False
    agentes = ctx.spec.raw.get("agentes") or {}
    if not agentes:
        return
    grupos_spec = ctx.spec.raw.get("agentes_grupos") or {}
    sprites = Block()
    arranque = Block()          # meganaciones: en el evento de arranque
    tardios: dict[str, dict[str, list[Block]]] = {}   # TAG -> grupo -> agentes (pulso mensual)
    vistos: set[str] = set()
    total = 0
    for tag, lista in agentes.items():
        ctx.spec.country(tag)   # el TAG tiene que existir
        al_arrancar = []
        for a in lista or []:
            aid = a["id"]
            if aid in vistos:
                raise SpecError(f"agentes: '{aid}' repetido", where="33_agentes.yaml")
            vistos.add(aid)
            grupo = a.get("grupo")
            if grupo is not None and grupo not in grupos_spec:
                raise SpecError(f"agentes: '{aid}' en el grupo '{grupo}', que no está en agentes_grupos",
                                where="33_agentes.yaml")
            op = _operativo(ctx, tag, a, sprites)
            if grupo is not None:
                tardios.setdefault(tag, {}).setdefault(grupo, [])
            if op is None:
                continue
            total += 1
            if grupo is None:
                al_arrancar.append(("create_operative_leader", op))
            else:
                tardios[tag][grupo].append(op)
        if al_arrancar:
            arranque.add("if", Block([("limit", Block([("original_tag", tag)]))] + al_arrancar))
    if not total and not tardios:
        return
    triggers_used: dict[str, str] = {}
    efectos = Block()
    if arranque.entries:
        _effects.CREAR_AGENTES = True
        efectos.add(EFECTO, Block([
            ("if", Block([
                ("limit", Block([("has_dlc", Quoted("La Resistance")),
                                 ("NOT", Block([("has_country_flag", FLAG)]))])),
                ("set_country_flag", FLAG),
            ] + arranque.entries)),
        ]))
    # Gran Bretaña y Japón (2026-11-04): los corre el pulso mensual del país
    # (33_agentes.yaml -> extend_scripted_effects). Cada grupo una vez, cuando
    # ya hay agencia y se cumple su condición (el camino de Albión).
    for tag, grupos in tardios.items():
        cuerpo = Block()
        for grupo, ops in grupos.items():
            flag = f"MN_agentes_{grupo}"
            limit = Block([("NOT", Block([("has_country_flag", flag)]))])
            cuando = (grupos_spec.get(grupo) or {}).get("cuando")
            if cuando:
                limit.entries.extend(_effects.render_conditions(
                    f"agentes_grupos.{grupo}", cuando, triggers_used, where="33_agentes.yaml").entries)
            if not ops:
                continue
            cuerpo.add("if", Block([("limit", limit), ("set_country_flag", flag)]
                                   + [("create_operative_leader", op) for op in ops]))
        efectos.add(f"MEGANATIONS_agentes_{tag}", Block([
            ("if", Block([("limit", Block([("has_dlc", Quoted("La Resistance")),
                                           ("has_intelligence_agency", True)]))] + cuerpo.entries)),
        ]))
    ctx.write_text("common/scripted_effects/meganations_agentes.txt",
                   banner_for(SOURCE) + render(efectos))
    ctx.write_text("interface/meganations_agentes.gfx",
                   banner_for(SOURCE) + render(Block([("spriteTypes", sprites)])))
    ctx.note(f"agentes: {total} agentes con retrato propio")
    ctx.verify_keys("effects", {"create_operative_leader": SOURCE, "set_country_flag": SOURCE})
    ctx.verify_keys("triggers", {"has_dlc": SOURCE, "has_country_flag": SOURCE, "original_tag": SOURCE,
                                 "has_intelligence_agency": SOURCE, **triggers_used})
