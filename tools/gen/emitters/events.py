"""Eventos y on_actions.

Produce:
  events/<namespace>.txt
  common/on_actions/00_meganations_on_actions.txt   (si algún evento es on_startup)
  localisation: <ns>.<n>.t, <ns>.<n>.d y <ns>.<n>.<letra> por opción

Los eventos con `trigger: { focus: X }` no se disparan desde acá: los agrega
el emisor de focos a la recompensa del foco (fired_by_focus). Todos son
`is_triggered_only`: nunca saltan solos por MTTH.

Imagen: se verifica contra interface/*.gfx. Si no existe se omite (el evento
carga sin imagen) y se avisa.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block
from . import ideas as ideas_mod
from . import effects as effects_mod
from .effects import EffectContext, scripted_effect_ids, render_effects

SOURCE = "spec/12_events.yaml"
LOC_FILE = "meganations_events"
OPTION_LETTERS = "abcdefgh"


def _events(ctx: BuildContext):
    """(namespace, tag, evento) para cada evento del spec."""
    namespaces = ctx.spec.raw["events"].get("namespaces") or {}
    for ns, body in namespaces.items():
        for ev in body.get("events", []) or []:
            yield ns, body["country"], ev


def event_id(ns: str, ev: dict) -> str:
    return f"{ns}.{ev['id']}"


def fired_by_focus(ctx: BuildContext, focus_id: str) -> list[str]:
    out = []
    for ns, _, ev in _events(ctx):
        trig = ev.get("trigger")
        if isinstance(trig, dict) and trig.get("focus") == focus_id:
            out.append(event_id(ns, ev))
    return out


def all_event_ids(ctx: BuildContext) -> set[str]:
    return {event_id(ns, ev) for ns, _, ev in _events(ctx)}


def emit(ctx: BuildContext) -> None:
    effects_mod.use_states(ctx.data.get("state_ids_by_name"))
    known_ideas = ideas_mod.all_idea_ids(ctx)
    icons = ctx.vanilla.gfx_names() if ctx.vanilla else None
    effects_used: dict[str, str] = {}
    startup: list[tuple[str, str]] = []  # (tag, id)
    by_ns: dict[str, Block] = {}
    seen: set[str] = set()
    focus_ids = _all_focus_ids(ctx)
    from .focus_trees import character_ids
    effect_ctx = EffectContext(
        known_ideas, {c.tag for c in ctx.spec.countries},
        wargoals=ctx.vanilla.wargoal_types() if ctx.vanilla else None,
        warn=ctx.warn, characters=character_ids(ctx), events=all_event_ids(ctx),
        scripted=scripted_effect_ids(ctx.spec.raw),
        tech_categories=ctx.vanilla.tech_categories() if ctx.vanilla else None,
    )

    for ns, tag, ev in _events(ctx):
        ctx.spec.country(tag)
        eid = event_id(ns, ev)
        if eid in seen:
            raise SpecError(f"evento duplicado: {eid}", where="12_events.yaml")
        seen.add(eid)

        trig = ev.get("trigger")
        if trig == "on_startup":
            startup.append((tag, eid))
        elif trig == "effect":
            pass  # lo dispara el efecto `event` de un foco, decisión u otro evento
        elif isinstance(trig, dict) and "focus" in trig:
            if trig["focus"] not in focus_ids:
                raise SpecError(f"{eid}: el foco '{trig['focus']}' no existe", where="12_events.yaml")
        else:
            raise SpecError(f"{eid}: trigger desconocido {trig!r}", where="12_events.yaml")

        b = Block()
        b.add("id", eid)
        b.add("title", _loc(ctx, f"{eid}.t", ev["title"]))
        b.add("desc", _loc(ctx, f"{eid}.d", ev["desc"]))
        picture = ev.get("picture")
        if picture:
            if icons is None:
                ctx.warn("imagenes de eventos: no se validaron contra interface/*.gfx (falta --vanilla-path).")
                b.add("picture", picture)
            elif picture in icons:
                b.add("picture", picture)
            else:
                ctx.warn(f"{eid}: la imagen '{picture}' no existe en el juego; el evento sale sin imagen.")
        b.add("is_triggered_only", True)
        if ev.get("hidden"):
            b.add("hidden", True)  # evento de mantenimiento: corre sin ventana (hide_window no existe en HOI4)

        options = ev.get("options") or []
        if not options or len(options) > len(OPTION_LETTERS):
            raise SpecError(f"{eid}: entre 1 y {len(OPTION_LETTERS)} opciones", where="12_events.yaml")
        for letter, opt in zip(OPTION_LETTERS, options):
            ob = render_effects(eid, opt.get("effects") or [], effect_ctx, effects_used, where="12_events.yaml")
            ob.entries.insert(0, ("name", _loc(ctx, f"{eid}.{letter}", opt["name"])))
            if "ai_chance" in opt:
                ob.add("ai_chance", Block([("factor", opt["ai_chance"])]))
            b.add("option", ob)

        by_ns.setdefault(ns, Block()).add("country_event", b)

    for ns, events in by_ns.items():
        root = Block()
        root.add("add_namespace", ns)
        root.entries.extend(events.entries)
        ctx.write_script(f"events/{ns}.txt", root, source=SOURCE)

    if startup:
        _emit_on_actions(ctx, startup)
        effects_used.setdefault("country_event", "on_startup")
    ctx.verify_keys("effects", effects_used)
    ctx.verify_keys("triggers", effect_ctx.triggers_used)


def _emit_on_actions(ctx: BuildContext, startup: list[tuple[str, str]]) -> None:
    if ctx.vanilla is not None:
        found = any(
            "on_startup" in p.read_text(encoding="utf-8-sig", errors="replace")
            for p in (ctx.vanilla.root / "common" / "on_actions").glob("*.txt")
        )
        if not found:
            raise SpecError("on_startup no aparece en common/on_actions/ del juego", where="12_events.yaml")

    effect = Block()
    for tag, eid in startup:
        scope = Block()
        scope.add("country_event", eid)
        effect.add(tag, scope)
    on_startup = Block()
    on_startup.add("effect", effect)
    actions = Block()
    actions.add("on_startup", on_startup)
    root = Block()
    root.add("on_actions", actions)
    ctx.write_script("common/on_actions/00_meganations_on_actions.txt", root, source=SOURCE)


def _all_focus_ids(ctx: BuildContext) -> set[str]:
    out = set()
    for tree in (ctx.spec.raw["focus_trees"].get("trees") or {}).values():
        if isinstance(tree, dict):
            for branch in tree.get("branches", []) or []:
                out.update(f["id"] for f in branch.get("focuses", []) or [])
    return out


def _loc(ctx: BuildContext, key: str, texts: dict) -> str:
    return ctx.loc.define_and_reference(
        key, en=texts["english"], es=texts["spanish"], file=LOC_FILE, origin=f"events:{key}"
    )
