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
from ..pdx import Block, Quoted
from . import ideas as ideas_mod
from . import effects as effects_mod
from .effects import EffectContext, scripted_effect_ids, render_conditions, render_effects

SOURCE = "spec/12_events.yaml"
LOC_FILE = "meganations_events"
# sin "d" ni "t": son las claves del texto y el título (<id>.d, <id>.t)
OPTION_LETTERS = "abcefghi"


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
    _emit(ctx)
    effects_mod.flush_tooltips(ctx)


def _emit(ctx: BuildContext) -> None:
    effects_mod.use_states(ctx.data.get("state_ids_by_name"))
    effects_mod.use_variable_names(ctx.spec.raw)
    effects_mod.use_territory(ctx.data.get("territory"))
    known_ideas = ideas_mod.all_idea_ids(ctx)
    icons = ctx.vanilla.gfx_names() if ctx.vanilla else None
    effects_used: dict[str, str] = {}
    startup: list[tuple[str, str]] = []  # (tag, id)
    capitulations: list[tuple[str, str, str]] = []  # (quien capitula, dueño del evento, id)
    by_ns: dict[str, Block] = {}
    seen: set[str] = set()
    own_sprites = Block()
    focus_ids = _all_focus_ids(ctx)
    from .focus_trees import character_ids
    effect_ctx = EffectContext(
        known_ideas, {c.tag for c in ctx.spec.countries},
        wargoals=ctx.vanilla.wargoal_types() if ctx.vanilla else None,
        warn=ctx.warn, characters=character_ids(ctx), events=all_event_ids(ctx),
        scripted=scripted_effect_ids(ctx.spec.raw), dynamic_modifiers=effects_mod.dynamic_modifier_ids(ctx.spec.raw),
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
        elif isinstance(trig, dict) and "capitulation" in trig:
            # on_capitulation: cuando `loser` capitula y el dueño del evento está en guerra con él
            loser = trig["capitulation"]["loser"]
            ctx.spec.country(loser)
            capitulations.append((loser, tag, eid))
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
        own = ctx.spec.root.parent / "assets" / "events" / f"{eid}.dds"
        if own.exists():
            # convención de arte (tools/arte): assets/events/<id>.dds reemplaza la imagen genérica
            sprite_name = f"GFX_{eid.replace('.', '_')}"
            ctx.copy_asset(f"assets/events/{eid}.dds", f"gfx/event_pictures/meganations/{eid}.dds")
            sp = Block()
            sp.add("name", Quoted(sprite_name))
            sp.add("texturefile", Quoted(f"gfx/event_pictures/meganations/{eid}.dds"))
            own_sprites.add("spriteType", sp)
            b.add("picture", sprite_name)
            picture = None
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
            if opt.get("when"):
                # opción que solo aparece si se cumple la condición
                ob.entries.insert(1, ("trigger", render_conditions(
                    eid, opt["when"], effect_ctx.triggers_used, where="12_events.yaml")))
            if "ai_chance" in opt:
                ob.add("ai_chance", Block([("factor", opt["ai_chance"])]))
            b.add("option", ob)

        by_ns.setdefault(ns, Block()).add("country_event", b)

    if own_sprites.entries:
        gfx_root = Block()
        gfx_root.add("spriteTypes", own_sprites)
        ctx.write_script("interface/meganations_events.gfx", gfx_root, source=SOURCE)

    for ns, events in by_ns.items():
        root = Block()
        root.add("add_namespace", ns)
        root.entries.extend(events.entries)
        ctx.write_script(f"events/{ns}.txt", root, source=SOURCE)

    if startup:
        _emit_on_actions(ctx, startup)
        effects_used.setdefault("country_event", "on_startup")
    if capitulations:
        _emit_capitulations(ctx, capitulations, effect_ctx.triggers_used)
        effects_used.setdefault("country_event", "on_capitulation")
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


def _emit_capitulations(ctx: BuildContext, items: list[tuple[str, str, str]], triggers_used: dict) -> None:
    """on_capitulation: ROOT es el país que capitula. El evento le llega al
    dueño si en ese momento está en guerra con él."""
    if ctx.vanilla is not None:
        found = any(
            "on_capitulation" in p.read_text(encoding="utf-8-sig", errors="replace")
            for p in (ctx.vanilla.root / "common" / "on_actions").glob("*.txt")
        )
        if not found:
            ctx.warn("on_capitulation no aparece en common/on_actions/ del juego: los eventos de capitulacion no se conectan.")
            return
    effect = Block()
    for loser, owner, eid in items:
        cond = Block([("tag", loser), (owner, Block([("has_war_with", loser)]))])
        body = Block([("limit", cond), (owner, Block([("country_event", eid)]))])
        effect.add("if", body)
    triggers_used.setdefault("tag", "on_capitulation")
    triggers_used.setdefault("has_war_with", "on_capitulation")
    root = Block([("on_actions", Block([("on_capitulation", Block([("effect", effect)]))]))])
    ctx.write_script("common/on_actions/03_meganations_capitulation.txt", root, source=SOURCE)


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
