"""Árboles de foco.

Produce:
  common/national_focus/<TAG>_focus.txt
  localisation de <id> y <id>_desc por foco (TN010)

Layout automático (07_focus_trees.yaml -> layout: auto):
  y = profundidad (el camino de prerequisitos más largo hasta el foco)
  x = una franja de columnas por rama, en el orden del spec
Así agregar o mover un foco no obliga a recalcular coordenadas a mano.

Prerequisitos: una lista en el spec significa "todos". En HOI4 eso es un
bloque `prerequisite` por foco; varios focos dentro del MISMO bloque
significarían "cualquiera de ellos".

Recompensas: lista de { effect, value } del spec (ver effects.py). Si un
evento de 12_events.yaml tiene `trigger: { focus: <id> }`, el foco lo dispara.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted
from . import events as events_mod
from . import ideas as ideas_mod
from . import resources as resources_mod
from .effects import EffectContext, scripted_effect_ids, render_conditions, render_effects

SOURCE = "spec/07_focus_trees.yaml"
LOC_FILE = "meganations_focus"

# Unidades de la grilla de focos entre dos focos vecinos.
X_STEP = 2
Y_STEP = 1

# Ícono vanilla que existe siempre; se usa si el pedido no está en el juego.
FALLBACK_ICON = "GFX_goal_unknown"

def root_focus_ids(ctx: BuildContext, tag: str) -> list[str]:
    """Focos sin prerequisitos del árbol de un país (los que se ven primero)."""
    tree = (ctx.spec.raw["focus_trees"].get("trees") or {}).get(tag)
    if not isinstance(tree, dict) or "branches" not in tree:
        return []
    return [
        f["id"] for branch in tree["branches"] for f in branch.get("focuses", []) or []
        if not _all_prereqs(f)
    ]


def _all_prereqs(f: dict) -> list[str]:
    """prerequisites (todos) + prerequisites_any (cualquiera de ellos)."""
    return list(f.get("prerequisites", []) or []) + list(f.get("prerequisites_any", []) or [])


def emit(ctx: BuildContext) -> None:
    trees = ctx.spec.raw["focus_trees"].get("trees") or {}
    for tag, tree in trees.items():
        if not isinstance(tree, dict) or "branches" not in tree:
            continue  # not_started: sin árbol, el país usa el genérico
        ctx.spec.country(tag)  # falla si el TAG no existe
        _emit_tree(ctx, tag, tree)


def _emit_tree(ctx: BuildContext, tag: str, tree: dict) -> None:
    focuses: list[tuple[str, dict]] = []  # (rama, foco)
    for branch in tree["branches"]:
        for focus in branch.get("focuses", []) or []:
            focuses.append((branch["id"], focus))

    by_id = {f["id"]: f for _, f in focuses}
    if len(by_id) != len(focuses):
        raise SpecError(f"{tag}: ids de foco duplicados", where="07_focus_trees.yaml")
    for _, f in focuses:
        for pre in _all_prereqs(f):
            if pre not in by_id:
                raise SpecError(f"{f['id']}: prerequisito '{pre}' no existe", where="07_focus_trees.yaml")
    if not any(not _all_prereqs(f) for _, f in focuses):
        raise SpecError(f"{tag}: ningun foco sin prerequisitos, el arbol es inaccesible (TN008)",
                        where="07_focus_trees.yaml")

    depth = _depths(by_id)
    positions = _layout(focuses, depth)
    known_ideas = ideas_mod.all_idea_ids(ctx)
    effect_ctx = EffectContext(
        known_ideas,
        {c.tag for c in ctx.spec.countries},
        ctx.vanilla.building_keys() if ctx.vanilla else None,
        ctx.vanilla.wargoal_types() if ctx.vanilla else None,
        capital=(ctx.data.get("capitals") or {}).get(tag),
        resources={m["resource"]["key"] for m in resources_mod.new_resources(ctx)},
        warn=ctx.warn,
        characters=character_ids(ctx),
        events=events_mod.all_event_ids(ctx),
        scripted=scripted_effect_ids(ctx.spec.raw),
        shared_slots=ctx.vanilla.shared_slot_buildings() if ctx.vanilla else None,
    )
    exclusive = _exclusive_pairs(focuses, by_id)
    custom = _emit_custom_icons(ctx, tag, focuses)
    icons = (ctx.vanilla.gfx_names() | custom) if ctx.vanilla else None
    effects_used: dict[str, str] = {}
    triggers_used = effect_ctx.triggers_used

    body = Block()
    body.add("id", tree["id"])
    country = Block()
    country.add("factor", 0)
    modifier = Block()
    modifier.add("add", 10)
    modifier.add("tag", tag)
    country.add("modifier", modifier)
    body.add("country", country)
    body.add("default", bool(tree.get("default", False)))

    for _, f in focuses:
        fid = f["id"]
        fb = Block()
        fb.add("id", ctx.loc.reference(fid, f"focus:{fid}"))
        fb.add("icon", _icon(ctx, f, icons))
        x, y = positions[fid]
        fb.add("x", x)
        fb.add("y", y)
        fb.add("cost", _cost(f))
        for pre in f.get("prerequisites", []) or []:
            p = Block()
            p.add("focus", pre)
            fb.add("prerequisite", p)
        if f.get("prerequisites_any"):
            p = Block()
            for pre in f["prerequisites_any"]:
                p.add("focus", pre)
            fb.add("prerequisite", p)
        if exclusive.get(fid):
            me = Block()
            for other in sorted(exclusive[fid]):
                me.add("focus", other)
            fb.add("mutually_exclusive", me)

        available = f.get("available")
        if isinstance(available, dict):
            fb.add("available", _available(ctx, tag, fid, available, triggers_used))

        reward = f.get("reward")
        if not isinstance(reward, list) or not reward:
            raise SpecError(f"{fid}: sin reward", where="07_focus_trees.yaml")
        completion = render_effects(fid, reward, effect_ctx, effects_used, where="07_focus_trees.yaml")
        for event_id in events_mod.fired_by_focus(ctx, fid):
            completion.add("country_event", event_id)
            effects_used.setdefault("country_event", fid)
        fb.add("completion_reward", completion)

        fb.add("ai_will_do", _ai(fid, f.get("ai"), triggers_used))
        body.add("focus", fb)

        desc = f.get("desc")
        if not isinstance(desc, dict):
            raise SpecError(f"{fid}: falta desc en EN y ES (TN010)", where="07_focus_trees.yaml")
        ctx.loc.define(fid, en=f["name"]["english"], es=f["name"]["spanish"],
                       file=LOC_FILE, origin=f"focus:{fid}")
        ctx.loc.define_and_reference(f"{fid}_desc", en=desc["english"], es=desc["spanish"],
                                     file=LOC_FILE, origin=f"focus:{fid}")

    ctx.verify_keys("effects", effects_used)
    ctx.verify_keys("triggers", triggers_used)

    root = Block()
    root.add("focus_tree", body)
    ctx.write_script(f"common/national_focus/{tag}_focus.txt", root, source=SOURCE)


# ---------------------------------------------------------------------------


def _exclusive_pairs(focuses, by_id) -> dict[str, set[str]]:
    """mutually_exclusive simétrico: si A excluye a B, B excluye a A."""
    out: dict[str, set[str]] = {}
    for _, f in focuses:
        for other in f.get("mutually_exclusive", []) or []:
            if other not in by_id:
                raise SpecError(f"{f['id']}: mutually_exclusive con '{other}', que no existe",
                                where="07_focus_trees.yaml")
            out.setdefault(f["id"], set()).add(other)
            out.setdefault(other, set()).add(f["id"])
    return out


def _depths(by_id: dict[str, dict]) -> dict[str, int]:
    depth: dict[str, int] = {}
    visiting: set[str] = set()

    def visit(fid: str) -> int:
        if fid in depth:
            return depth[fid]
        if fid in visiting:
            raise SpecError(f"ciclo de prerequisitos en {fid}", where="07_focus_trees.yaml")
        visiting.add(fid)
        pres = _all_prereqs(by_id[fid])
        d = 0 if not pres else 1 + max(visit(p) for p in pres)
        visiting.discard(fid)
        depth[fid] = d
        return d

    for fid in by_id:
        visit(fid)
    return depth


def _layout(focuses: list[tuple[str, dict]], depth: dict[str, int]) -> dict[str, tuple[int, int]]:
    """Una franja por rama; dentro de la franja, un casillero por foco y fila."""
    # Las raíces (profundidad 0) van centradas arriba, fuera de las franjas.
    branches: dict[str, dict[int, list[str]]] = {}
    roots: list[str] = []
    for branch, f in focuses:
        if depth[f["id"]] == 0:
            roots.append(f["id"])
        else:
            branches.setdefault(branch, {}).setdefault(depth[f["id"]], []).append(f["id"])

    positions: dict[str, tuple[int, int]] = {}
    column = 0
    for rows in branches.values():
        width = max(len(ids) for ids in rows.values())
        for d, ids in rows.items():
            # centra la fila dentro de la franja
            offset = (width - len(ids)) * X_STEP // 2
            for i, fid in enumerate(ids):
                positions[fid] = (column + offset + i * X_STEP, d * Y_STEP)
        column += width * X_STEP

    total = max(column - X_STEP, 0)
    for i, fid in enumerate(roots):
        start = (total - (len(roots) - 1) * X_STEP) // 2
        positions[fid] = (start + i * X_STEP, 0)
    return positions


def _emit_custom_icons(ctx: BuildContext, tag: str, focuses: list[tuple[str, dict]]) -> set[str]:
    """Íconos del usuario: copia el .dds y declara el sprite (normal y _shine).

    El _shine es el brillo que HOI4 muestra cuando el foco está disponible;
    sin él el foco se ve pero no brilla. Mismo formato que los goals vanilla.
    """
    sprites = Block()
    names: set[str] = set()
    for _, f in focuses:
        asset = f.get("icon_asset")
        if not asset:
            continue
        name = f["icon"]
        if name in names:
            continue
        texture = f"gfx/interface/goals/{asset.rsplit('/', 1)[-1]}"
        ctx.copy_asset(asset, texture)
        names.add(name)

        plain = Block()
        plain.add("name", Quoted(name))
        plain.add("texturefile", Quoted(texture))
        sprites.add("spriteType", plain)

        shine = Block()
        shine.add("name", Quoted(f"{name}_shine"))
        shine.add("texturefile", Quoted(texture))
        shine.add("effectFile", Quoted("gfx/FX/buttonstate.lua"))
        for rotation in (-90.0, 90.0):
            anim = Block()
            anim.add("animationmaskfile", Quoted(texture))
            anim.add("animationtexturefile", Quoted("gfx/interface/goals/shine_overlay.dds"))
            anim.add("animationrotation", rotation)
            anim.add("animationlooping", False)
            anim.add("animationtime", 0.75)
            anim.add("animationdelay", 0)
            anim.add("animationblendmode", Quoted("add"))
            anim.add("animationtype", Quoted("scrolling"))
            offset = Block()
            offset.add("x", 0.0)
            offset.add("y", 0.0)
            anim.add("animationrotationoffset", offset)
            scale = Block()
            scale.add("x", 1.0)
            scale.add("y", 1.0)
            anim.add("animationtexturescale", scale)
            shine.add("animation", anim)
        shine.add("legacy_lazy_load", False)
        sprites.add("spriteType", shine)

    if names:
        root = Block()
        root.add("spriteTypes", sprites)
        ctx.write_script(f"interface/meganations_{tag}_goals.gfx", root, source=SOURCE)
    return names


def _icon(ctx: BuildContext, focus: dict, icons: set[str] | None) -> str:
    icon = focus.get("icon") or FALLBACK_ICON
    if focus.get("icon_asset"):
        return icon
    if icons is None:
        ctx.warn("iconos de foco: no se validaron contra interface/*.gfx (falta --vanilla-path).")
        return icon
    if icon not in icons:
        ctx.warn(f"{focus['id']}: el icono '{icon}' no existe en el juego; uso {FALLBACK_ICON}.")
        return FALLBACK_ICON
    return icon


# Duraciones del diseño (21/35/42/56/70 días). HOI4 cuenta el costo en
# semanas: cost = días / 7.
def _cost(f: dict) -> int:
    if "days" in f:
        days = int(f["days"])
        if days % 7:
            raise SpecError(f"{f['id']}: days={days} no es multiplo de 7", where="07_focus_trees.yaml")
        return days // 7
    return int(f.get("cost", 10))


def _ai(fid: str, spec: dict | None, triggers_used: dict[str, str]) -> Block:
    """ai_will_do: factor base y modificadores condicionales.

    ai: { factor: 1, modifiers: [ { factor: 5, when: {condiciones} } ] }
    Así la IA elige una ruta por lo que le pasa (guerra, estabilidad...), no
    por una moneda al aire.
    """
    ai = Block()
    spec = spec or {}
    ai.add("factor", spec.get("factor", 1))
    for m in spec.get("modifiers") or []:
        mod = Block()
        mod.add("factor", m["factor"])
        mod.entries.extend(render_conditions(fid, m["when"], triggers_used, where="07_focus_trees.yaml").entries)
        ai.add("modifier", mod)
    return ai


def character_ids(ctx: BuildContext) -> set[str]:
    return {ch["id"] for ch in ctx.spec.raw["leaders"].get("characters", []) or [] if isinstance(ch, dict)}


def _available(ctx: BuildContext, tag: str, fid: str, spec: dict, triggers_used: dict[str, str]) -> Block:
    block = Block()
    for key, value in spec.items():
        if key == "country_exists":
            if value not in {c.tag for c in ctx.spec.countries}:
                raise SpecError(f"{fid}: country_exists '{value}' no es un pais del mod",
                                where="07_focus_trees.yaml")
            block.add("country_exists", value)
            triggers_used.setdefault("country_exists", fid)
        elif key == "biosteel_tier":
            # El contador de BioSteel es una variable del país (14_decisions.yaml).
            var, amount = _biosteel_threshold(ctx, int(value))
            inner = Block()
            inner.add("var", var)
            inner.add("value", amount)
            inner.add("compare", "greater_than_or_equals")
            block.add("check_variable", inner)
            triggers_used.setdefault("check_variable", fid)
        else:
            block.entries.extend(render_conditions(fid, {key: value}, triggers_used,
                                                   where="07_focus_trees.yaml").entries)
    return block


def _biosteel_threshold(ctx: BuildContext, tier: int) -> tuple[str, int]:
    for mech in ctx.spec.raw["mechanics"].get("mechanics", []) or []:
        if mech.get("id") == "biosteel":
            thresholds = mech["thresholds"]
            if not 1 <= tier <= len(thresholds):
                raise SpecError(f"biosteel_tier {tier} fuera de rango", where="07_focus_trees.yaml")
            return mech["variable"]["name"], int(thresholds[tier - 1])
    raise SpecError("no hay mecanica 'biosteel' en 06_mechanics.yaml", where="07_focus_trees.yaml")