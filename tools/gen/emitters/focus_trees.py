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

Recompensas: lista de { effect, value } del spec. Los efectos se validan
contra documentation/ del juego si hay --vanilla-path. `add_ideas` y
`swap_ideas` además se validan contra las ideas de 05_ideas.yaml.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block
from . import ideas as ideas_mod

SOURCE = "spec/07_focus_trees.yaml"
LOC_FILE = "meganations_focus"

# Unidades de la grilla de focos entre dos focos vecinos.
X_STEP = 2
Y_STEP = 1

# Ícono vanilla que existe siempre; se usa si el pedido no está en el juego.
FALLBACK_ICON = "GFX_goal_unknown"

# Efectos cuyo valor es un número o un id suelto: `efecto = valor`.
SCALAR_EFFECTS = {
    "add_political_power",
    "add_stability",
    "add_war_support",
    "army_experience",
    "navy_experience",
    "air_experience",
    "add_manpower",
    "add_ideas",
}


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
        for pre in f.get("prerequisites", []) or []:
            if pre not in by_id:
                raise SpecError(f"{f['id']}: prerequisito '{pre}' no existe", where="07_focus_trees.yaml")
    if not any(not f.get("prerequisites") for _, f in focuses):
        raise SpecError(f"{tag}: ningun foco sin prerequisitos, el arbol es inaccesible (TN008)",
                        where="07_focus_trees.yaml")

    depth = _depths(by_id)
    positions = _layout(focuses, depth)
    known_ideas = ideas_mod.all_idea_ids(ctx)
    icons = ctx.vanilla.gfx_names() if ctx.vanilla else None
    effects_used: dict[str, str] = {}
    triggers_used: dict[str, str] = {}

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
        fb.add("cost", int(f.get("cost", 10)))
        for pre in f.get("prerequisites", []) or []:
            p = Block()
            p.add("focus", pre)
            fb.add("prerequisite", p)

        available = f.get("available")
        if isinstance(available, dict):
            fb.add("available", _available(ctx, fid, available, triggers_used))

        reward = f.get("reward")
        if not isinstance(reward, list) or not reward:
            raise SpecError(f"{fid}: sin reward", where="07_focus_trees.yaml")
        fb.add("completion_reward", _reward(fid, reward, known_ideas, effects_used))

        ai = Block()
        ai.add("factor", 1)
        fb.add("ai_will_do", ai)
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


def _depths(by_id: dict[str, dict]) -> dict[str, int]:
    depth: dict[str, int] = {}
    visiting: set[str] = set()

    def visit(fid: str) -> int:
        if fid in depth:
            return depth[fid]
        if fid in visiting:
            raise SpecError(f"ciclo de prerequisitos en {fid}", where="07_focus_trees.yaml")
        visiting.add(fid)
        pres = by_id[fid].get("prerequisites", []) or []
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


def _icon(ctx: BuildContext, focus: dict, icons: set[str] | None) -> str:
    icon = focus.get("icon") or FALLBACK_ICON
    if icons is None:
        ctx.warn("iconos de foco: no se validaron contra interface/*.gfx (falta --vanilla-path).")
        return icon
    if icon not in icons:
        ctx.warn(f"{focus['id']}: el icono '{icon}' no existe en el juego; uso {FALLBACK_ICON}.")
        return FALLBACK_ICON
    return icon


def _available(ctx: BuildContext, fid: str, spec: dict, triggers_used: dict[str, str]) -> Block:
    block = Block()
    for key, value in spec.items():
        if key == "biosteel_tier":
            trigger_key, resource, amount = _biosteel_threshold(ctx, int(value))
            inner = Block()
            inner.add("resource", resource)
            inner.add("amount", amount)
            block.add(trigger_key, inner)
            triggers_used.setdefault(trigger_key, fid)
        else:
            raise SpecError(f"{fid}: condicion desconocida '{key}' en available",
                            where="07_focus_trees.yaml")
    return block


def _biosteel_threshold(ctx: BuildContext, tier: int) -> tuple[str, str, int]:
    for mech in ctx.spec.raw["mechanics"].get("mechanics", []) or []:
        if mech.get("id") == "biosteel":
            thresholds = mech["thresholds"]
            if not 1 <= tier <= len(thresholds):
                raise SpecError(f"biosteel_tier {tier} fuera de rango", where="07_focus_trees.yaml")
            return (
                mech["counter_trigger"]["key"],
                mech["resource"]["vanilla_key"],
                int(thresholds[tier - 1]),
            )
    raise SpecError("no hay mecanica 'biosteel' en 06_mechanics.yaml", where="07_focus_trees.yaml")


def _reward(fid: str, reward: list[dict], known_ideas: set[str], effects_used: dict[str, str]) -> Block:
    block = Block()
    for item in reward:
        effect = item.get("effect")
        if effect == "swap_ideas":
            for role in ("remove", "add"):
                if item.get(role) not in known_ideas:
                    raise SpecError(f"{fid}: swap_ideas.{role} '{item.get(role)}' no es una idea del spec",
                                    where="07_focus_trees.yaml")
            inner = Block()
            inner.add("remove_idea", item["remove"])
            inner.add("add_idea", item["add"])
            block.add("swap_ideas", inner)
        elif effect in SCALAR_EFFECTS:
            value = item.get("value")
            if effect == "add_ideas" and value not in known_ideas:
                raise SpecError(f"{fid}: add_ideas '{value}' no es una idea del spec",
                                where="07_focus_trees.yaml")
            block.add(effect, value)
        else:
            raise SpecError(
                f"{fid}: efecto '{effect}' no soportado por el generador",
                hint=f"soportados: swap_ideas, {', '.join(sorted(SCALAR_EFFECTS))}",
                where="07_focus_trees.yaml",
            )
        effects_used.setdefault(effect, fid)
    return block
