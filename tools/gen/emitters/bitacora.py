"""Bitácora anual en el game.log (2026-10-27).

Pedido del usuario antes de una partida de observador: que lo que pasa en el
mundo quede anotado solo, sin que él tenga que mirarlo. Los eventos del mod ya
dejan su línea en el game.log ("MEGANATIONS evento X para TAG"); esto suma una
foto por año de cada meganación y cada Tierra Sin Ley: regiones, divisiones,
fábricas, satélites y estabilidad, o que ya no existe.

Produce:
  events/meganations_bitacora.txt              evento oculto que se repite cada 365 días
  common/on_actions/07_meganations_bitacora.txt  lo arranca en cada meganación

Lo corren las ocho meganaciones (si una desaparece, las otras siguen), pero
escribe una sola: cada una lleva su cuenta de años y solo anota la primera que
pasa la cuenta global.

Líneas en el game.log (buscar "MEGANATIONS bitacora"):
  [fecha] MEGANATIONS bitacora EFE regiones 48 divisiones 92 civiles 60 militares 35 satelites 2 estabilidad 62
  [fecha] MEGANATIONS bitacora ZWE ya no existe
"""

from __future__ import annotations

from ..context import BuildContext
from ..pdx import Block, Quoted, banner_for, render

SOURCE = "tools/gen/emitters/bitacora.py (pedido del usuario 2026-10-27)"
NS = "meganations_bitacora"
EVENT = f"{NS}.1"
ANARQUIAS = ("ZAN", "ZWE", "ZWI", "ZWM", "ZWB")
VALORES = (
    ("regiones", "num_of_controlled_states"),
    ("divisiones", "num_divisions"),
    ("civiles", "num_of_civilian_factories"),
    ("militares", "num_of_military_factories"),
    ("satelites", "num_subjects"),
    ("estabilidad", "stability"),
)


def emit(ctx: BuildContext) -> None:
    megas = [c.tag for c in ctx.spec.countries if c.is_major]
    tags = [c.tag for c in ctx.spec.countries]
    if not megas:
        return
    seguidos = megas + [t for t in ANARQUIAS if t in tags]

    option = Block()
    option.add("name", f"{EVENT}.a")
    option.add("add_to_variable", Block([("MN_bitacora_n", 1)]))
    hacer = Block()
    hacer.add("limit", Block([("check_variable", Block([
        ("var", "MN_bitacora_n"), ("value", "global.MN_bitacora_n"), ("compare", "greater_than")]))]))
    hacer.add("set_variable", Block([("global.MN_bitacora_n", "MN_bitacora_n")]))
    for tag in seguidos:
        vivo = Block()
        vivo.add("limit", Block([("country_exists", tag)]))
        scope = Block()
        for nombre, var in VALORES:
            scope.add("set_temp_variable", Block([(f"mn_b_{nombre}", var)]))
        scope.add("multiply_temp_variable", Block([("mn_b_estabilidad", 100)]))   # en %
        texto = " ".join(f"{nombre} [?mn_b_{nombre}]" for nombre, _ in VALORES)
        scope.add("log", Quoted(f"[GetDateText] MEGANATIONS bitacora {tag} {texto}"))
        vivo.add(tag, scope)
        hacer.add("if", vivo)
        hacer.add("else", Block([("log", Quoted(f"[GetDateText] MEGANATIONS bitacora {tag} ya no existe"))]))
    option.add("if", hacer)
    option.add("country_event", Block([("id", EVENT), ("days", 365)]))

    event = Block()
    event.add("id", EVENT)
    event.add("title", f"{EVENT}.t")
    event.add("desc", f"{EVENT}.d")
    event.add("is_triggered_only", True)
    event.add("hidden", True)
    event.add("option", option)
    root = Block([("add_namespace", NS), ("country_event", event)])
    ctx.write_text(f"events/{NS}.txt", banner_for(SOURCE) + render(root))
    for key, en, es in ((f"{EVENT}.t", "Yearly log", "Bitácora anual"),
                        (f"{EVENT}.d", "Writes the state of the world to the game log.",
                         "Escribe el estado del mundo en el registro del juego."),
                        (f"{EVENT}.a", "OK", "OK")):
        ctx.loc.define_and_reference(key, en=en, es=es, file="meganations_bitacora", origin="bitacora")

    start = Block()
    for tag in megas:
        start.add(tag, Block([("country_event", Block([("id", EVENT), ("days", 1)]))]))
    on = Block([("on_actions", Block([("on_startup", Block([("effect", start)]))]))])
    ctx.write_text("common/on_actions/07_meganations_bitacora.txt", banner_for(SOURCE) + render(on))
    ctx.note(f"bitacora: foto anual en el game.log de {len(seguidos)} paises ({', '.join(seguidos)})")
