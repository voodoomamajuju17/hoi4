"""El mapa cambia: noticias cuando nace o desaparece un país (2026-10-28).

Pedido del usuario: "creá eventos para todos los países cada vez que se forme
una nueva nación o desaparezca otra". Le llegan a cada país jugador (la IA no
lee el diario, como las noticias de guerra de diplomacy.py).

Produce common/on_actions/09_meganations_mapa.txt:
  on_annex             ROOT anexa a FROM            -> meganations_mapa.1 (desaparece FROM)
  on_civil_war_end     ROOT ganó, FROM perdió       -> meganations_mapa.1 (desaparece FROM)
  on_release_as_free   ROOT es el país liberado     -> meganations_mapa.2 (nace ROOT)
  on_release_as_puppet ROOT es el satélite liberado -> meganations_mapa.2 (nace ROOT)
Los otros dos los disparan la Forma Final (.3, 14_decisions) y el efecto
civil_war (.4, effects.py).

En el evento, FROM es el ROOT del on_action; el otro país va en un event target
global (MN_mapa_ido, MN_mapa_padre) para el texto. Una bandera de 30 días en el
país que desaparece evita la noticia doble (anexado al terminar una guerra civil).
Nada en la primera semana: el arranque acomoda países y no es noticia.
"""

from __future__ import annotations

import datetime

from ..context import BuildContext
from ..pdx import Block, Compare

SOURCE = "tools/gen/emitters/mapa.py (pedido del usuario 2026-10-28)"
NS = "meganations_mapa"
GONE, BORN = f"{NS}.1", f"{NS}.2"
FLAG = "MN_mapa_contado"


def _after_start(ctx: BuildContext) -> str:
    start = str(ctx.spec.project.get("start_date") or "2100.1.1")
    y, m, d = (int(x) for x in start.split("."))
    t = datetime.date(y, m, d) + datetime.timedelta(days=7)
    return f"{t.year}.{t.month}.{t.day}"


def _news(event: str) -> Block:
    return Block([("every_country", Block([("limit", Block([("is_ai", False)])),
                                           ("country_event", Block([("id", event)]))]))])


def emit(ctx: BuildContext) -> None:
    events = ((ctx.spec.raw.get("events") or {}).get("namespaces") or {}).get(NS)
    if not events:
        return
    after = _after_start(ctx)

    def gone() -> Block:
        b = Block()
        b.add("limit", Block([("date", _gt(after)),
                              ("FROM", Block([("NOT", Block([("has_country_flag", FLAG)]))]))]))
        b.add("FROM", Block([("set_country_flag", Block([("flag", FLAG), ("days", 30)])),
                             ("save_global_event_target_as", "MN_mapa_ido")]))
        b.entries.extend(_news(GONE).entries)
        return Block([("if", b)])

    def born() -> Block:
        b = Block()
        b.add("limit", Block([("date", _gt(after))]))
        b.add("FROM", Block([("save_global_event_target_as", "MN_mapa_padre")]))
        b.entries.extend(_news(BORN).entries)
        return Block([("if", b)])

    on = Block()
    for hook, body in (("on_annex", gone()), ("on_civil_war_end", gone()),
                       ("on_release_as_free", born()), ("on_release_as_puppet", born())):
        on.add(hook, Block([("effect", body)]))
    ctx.write_script("common/on_actions/09_meganations_mapa.txt", Block([("on_actions", on)]), source=SOURCE)
    ctx.verify_keys("effects", {k: SOURCE for k in ("every_country", "country_event", "set_country_flag",
                                                     "save_global_event_target_as")})
    ctx.verify_keys("triggers", {k: SOURCE for k in ("is_ai", "has_country_flag", "date")})
    ctx.note("mapa: noticias para los jugadores al desaparecer un país (on_annex, on_civil_war_end) y al nacer "
             "uno (on_release_as_free, on_release_as_puppet); si el juego no conoce alguno, lo dice error.log")


def _gt(value: str) -> Compare:
    return Compare(">", value)
