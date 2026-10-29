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

Una imagen por país (2026-10-29, pedido del usuario: "todos estos eventos
necesitan su propia imagen, completamente originales"): arte/mapa_paises.yaml
pide mapa_ido_<TAG>, mapa_nace_<TAG>, mapa_forma_<TAG> y mapa_civil_<TAG>.
Cuando la imagen está en assets/events/, el país usa una copia del evento con
esa imagen (namespace meganations_mapa_p, mismo texto); si no, el genérico.
La Forma Final y la guerra civil pasan por los efectos programados
MEGANATIONS_mapa_forma_final y MEGANATIONS_mapa_guerra_civil (ROOT = el país).
"""

from __future__ import annotations

import datetime

import yaml

from ..context import BuildContext
from ..pdx import Block, Compare, Quoted

SOURCE = "tools/gen/emitters/mapa.py (pedido del usuario 2026-10-28)"
NS = "meganations_mapa"
GONE, BORN = f"{NS}.1", f"{NS}.2"
FLAG = "MN_mapa_contado"
NS_P = "meganations_mapa_p"
# tipo de imagen -> evento genérico
KINDS = {"ido": f"{NS}.1", "nace": f"{NS}.2", "forma": f"{NS}.3", "civil": f"{NS}.4"}
SCRIPTED = {"forma": "MEGANATIONS_mapa_forma_final", "civil": "MEGANATIONS_mapa_guerra_civil"}


def _after_start(ctx: BuildContext) -> str:
    start = str(ctx.spec.project.get("start_date") or "2100.1.1")
    y, m, d = (int(x) for x in start.split("."))
    t = datetime.date(y, m, d) + datetime.timedelta(days=7)
    return f"{t.year}.{t.month}.{t.day}"


def _news(event: str, extra_limit: list | None = None, days: int | None = None) -> Block:
    ev = Block([("id", event)])
    if days:
        ev.add("days", days)
    return Block([("every_country", Block([("limit", Block([("is_ai", False)] + (extra_limit or []))),
                                           ("country_event", ev)]))])


def _variants(ctx: BuildContext) -> dict[str, dict[str, str]]:
    """tipo -> {TAG: id del evento con su imagen}, y escribe esos eventos."""
    repo = ctx.spec.root.parent
    path = repo / "arte" / "mapa_paises.yaml"
    pedidas = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("imagenes") or {} if path.exists() else {}
    out: dict[str, dict[str, str]] = {k: {} for k in KINDS}
    root = Block([("add_namespace", NS_P)])
    sprites = Block()
    n = 0
    for key in pedidas:
        _, kind, tag = key.split("_", 2)
        if kind not in KINDS or not (repo / "assets" / "events" / f"{key}.dds").exists():
            continue
        n += 1
        eid = f"{NS_P}.{n}"
        base = KINDS[kind]
        ctx.copy_asset(f"assets/events/{key}.dds", f"gfx/event_pictures/meganations/{key}.dds")
        sprites.add("spriteType", Block([("name", Quoted(f"GFX_{key}")),
                                         ("texturefile", Quoted(f"gfx/event_pictures/meganations/{key}.dds"))]))
        ev = Block()
        ev.add("id", eid)
        ev.add("title", f"{base}.t")
        ev.add("desc", f"{base}.d")
        ev.add("picture", f"GFX_{key}")
        ev.add("is_triggered_only", True)
        ev.add("immediate", Block([("log", Quoted(f"[GetDateText] MEGANATIONS evento {eid} ({key}) para [Root.GetTag]"))]))
        ev.add("option", Block([("name", f"{base}.a")]))
        root.add("country_event", ev)
        out[kind][tag] = eid
    if n:
        ctx.write_script(f"events/{NS_P}.txt", root, source=SOURCE)
        ctx.write_script("interface/meganations_mapa_paises.gfx", Block([("spriteTypes", sprites)]), source=SOURCE)
    ctx.note(f"mapa: {n} de {len(pedidas)} imágenes propias por país ya están (las demás usan la genérica)")
    return out


def _dispatch(scope: str, variants: dict[str, str], generic: str, extra_limit=None, days=None) -> Block:
    """Si el país de la noticia (scope) tiene imagen propia, su evento; si no, el genérico."""
    body = Block()
    first = True
    for tag, eid in sorted(variants.items()):
        b = Block([("limit", Block([(scope, Block([("original_tag", tag)]))]))])
        b.entries.extend(_news(eid, extra_limit, days).entries)
        body.add("if" if first else "else_if", b)
        first = False
    if first:
        return _news(generic, extra_limit, days)
    body.add("else", _news(generic, extra_limit, days))
    return body


def emit(ctx: BuildContext) -> None:
    events = ((ctx.spec.raw.get("events") or {}).get("namespaces") or {}).get(NS)
    if not events:
        return
    after = _after_start(ctx)
    var = _variants(ctx)

    def gone() -> Block:
        b = Block()
        b.add("limit", Block([("date", _gt(after)),
                              ("FROM", Block([("NOT", Block([("has_country_flag", FLAG)]))]))]))
        b.add("FROM", Block([("set_country_flag", Block([("flag", FLAG), ("days", 30)])),
                             ("save_global_event_target_as", "MN_mapa_ido")]))
        b.entries.extend(_dispatch("FROM", var["ido"], GONE).entries)
        return Block([("if", b)])

    def born() -> Block:
        b = Block()
        b.add("limit", Block([("date", _gt(after))]))
        b.add("FROM", Block([("save_global_event_target_as", "MN_mapa_padre")]))
        b.entries.extend(_dispatch("ROOT", var["nace"], BORN).entries)
        return Block([("if", b)])

    on = Block()
    for hook, body in (("on_annex", gone()), ("on_civil_war_end", gone()),
                       ("on_release_as_free", born()), ("on_release_as_puppet", born())):
        on.add(hook, Block([("effect", body)]))
    ctx.write_script("common/on_actions/09_meganations_mapa.txt", Block([("on_actions", on)]), source=SOURCE)
    # la Forma Final: a los jugadores de países que no son potencias (las potencias tienen su evento)
    majors = [c.tag for c in ctx.spec.countries if c.is_major]
    not_major = [("NOT", Block([("OR", Block([("tag", t) for t in majors]))]))] if majors else []
    se = Block()
    se.add(SCRIPTED["forma"], _dispatch("ROOT", var["forma"], f"{NS}.3", not_major, 2))
    se.add(SCRIPTED["civil"], _dispatch("ROOT", var["civil"], f"{NS}.4", None, 1))
    ctx.write_script("common/scripted_effects/meganations_mapa.txt", se, source=SOURCE)
    ctx.verify_keys("effects", {k: SOURCE for k in ("every_country", "country_event", "set_country_flag",
                                                     "save_global_event_target_as")})
    ctx.verify_keys("triggers", {k: SOURCE for k in ("is_ai", "has_country_flag", "date", "original_tag", "tag")})
    ctx.note("mapa: noticias para los jugadores al desaparecer un país (on_annex, on_civil_war_end) y al nacer "
             "uno (on_release_as_free, on_release_as_puppet); si el juego no conoce alguno, lo dice error.log")


def _gt(value: str) -> Compare:
    return Compare(">", value)
