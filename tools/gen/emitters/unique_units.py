"""Unidades únicas (spec/20_unique_units.yaml).

Produce:
  common/scripted_effects/meganations_unique_units.txt   <id>_desbloqueo
  common/ideas/meganations_unique_units.txt              el espíritu de cada unidad
y deja para research.py:
  ctx.data["tech_locks"]   tech -> TAG: solo ese país la investiga (allow y
                           allow_branch con original_tag; ver lock_techs)

Nada se escribe de memoria: el chasis, sus casillas, las piezas y las
tecnologías que las habilitan se leen de la instalación. Una preferencia del
spec que no existe se saltea; lo que quedó en cada casilla va al reporte.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted, parse_file, text
from . import ideas as ideas_mod

SOURCE = "spec/20_unique_units.yaml"
LOC_FILE = "replace/meganations_unique_units"


def emit(ctx: BuildContext) -> None:
    units = (ctx.spec.raw.get("unique_units") or {}).get("units") or []
    if not units:
        return
    if ctx.vanilla is None:
        ctx.skip("unidades unicas", "el chasis, las piezas y las tecnologias salen del juego instalado", "Q035")
        return
    tree = ctx.vanilla.tech_tree()
    equip = _equipment_blocks(ctx.vanilla.root)
    modules = _module_blocks(ctx.vanilla.root)
    sub_units = ctx.vanilla.sub_units()
    renamed = set((ctx.spec.raw.get("research_look") or {}).get("techs") or {})
    gfx = ctx.vanilla.gfx_names()
    idea_sprites = ideas_mod.generic_candidates(gfx or (), ctx.vanilla.gfx_textures(), ctx.vanilla.root)

    locks: dict[str, str] = ctx.data.setdefault("tech_locks", {})
    effects = Block()
    ideas = Block()
    effects_used: dict[str, str] = {}
    for u in units:
        uid, tag = u["id"], u["country"]
        ctx.spec.country(tag)
        if not uid.startswith(f"{tag}_"):
            raise SpecError(f"la unidad '{uid}' de {tag} no empieza con '{tag}_'", where=SOURCE)

        # 1. Bloqueo de la investigación
        lock = u.get("lock") or {}
        words = lock.get("enables") or []
        locked = [t for t in lock.get("techs") or [] if t in tree]
        locked += [t for t, info in tree.items() if t not in locked and info["enables"]
                   and all(any(w in e for w in words) for e in info["enables"])]
        for t in locked:
            if locks.get(t, tag) != tag:
                raise SpecError(f"{uid}: la tecnologia '{t}' ya es unica de {locks[t]}", where=SOURCE)
            locks[t] = tag
        if not locked:
            ctx.warn(f"{uid}: ninguna tecnologia para bloquear en este juego; la unidad no es unica.")

        # 2. El diseño
        design = u.get("design") or {}
        variant, grant = _design(ctx, uid, design, equip, modules, tree)
        for t in locked:
            # la tecnología del chasis y lo que cuelga de ella en la misma línea
            if variant is not None and text(variant.get("type")) in tree[t]["enables"]:
                grant.insert(0, t)

        body = Block()
        if grant:
            tb = Block([(t, 1) for t in dict.fromkeys(grant)] + [("popup", False)])
            body.add("set_technology", tb)
            effects_used.setdefault("set_technology", uid)
        if variant is not None:
            body.add("create_equipment_variant", variant)
            effects_used.setdefault("create_equipment_variant", uid)
            amount = int((u.get("grant") or {}).get("equipment", 0))
            if amount:
                body.add("add_equipment_to_stockpile", Block([
                    ("type", text(variant.get("type"))), ("amount", amount), ("producer", tag),
                    ("variant_name", Quoted(design["name"]))]))
                effects_used.setdefault("add_equipment_to_stockpile", uid)
        tpl = u.get("template")
        if tpl:
            bad = [r for r in tpl["regiments"] + (tpl.get("support") or []) if r not in sub_units]
            if bad:
                raise SpecError(f"{uid}: batallones que el juego no tiene: {', '.join(bad)}", where=SOURCE)
            regs = Block()
            for i, r in enumerate(tpl["regiments"]):
                regs.add(r, Block([("x", i // 5), ("y", i % 5)]))
            tb = Block([("name", Quoted(tpl["name"])), ("regiments", regs)])
            if tpl.get("support"):
                sup = Block()
                for i, r in enumerate(tpl["support"]):
                    sup.add(r, Block([("x", 0), ("y", i)]))
                tb.add("support", sup)
            body.add("division_template", tb)
            effects_used.setdefault("division_template", uid)

        # 3. El espíritu (equipment_bonus sobre el arquetipo del chasis)
        spirit = u.get("spirit")
        if spirit and variant is not None:
            sid = spirit["id"]
            chassis = equip.get(text(variant.get("type"))) or Block()
            archetype = text(chassis.get("archetype")) or text(variant.get("type"))
            bonus = Block([(k, float(v)) for k, v in spirit["equipment_bonus"].items()] + [("instant", True)])
            idea = Block()
            picture = _picture(idea_sprites, spirit.get("picture_prefer") or [])
            if picture:
                idea.add("picture", picture)
            idea.add("allowed", Block([("always", False)]))
            idea.add("removal_cost", -1)
            idea.add("equipment_bonus", Block([(archetype, bonus)]))
            ideas.add(ctx.loc.reference(sid, f"unique:{sid}"), idea)
            ctx.loc.define(sid, en=spirit["name"]["english"], es=spirit["name"]["spanish"],
                           file="meganations_unique_units", origin=f"unique:{sid}")
            ctx.loc.define_and_reference(f"{sid}_desc", en=spirit["desc"]["english"], es=spirit["desc"]["spanish"],
                                         file="meganations_unique_units", origin=f"unique:{sid}")
            body.add("add_ideas", sid)
            effects_used.setdefault("add_ideas", uid)

        effects.add(f"{uid}_desbloqueo", body)

        # 4. Nombres: el batallón (pisa el del juego) y las tecnologías bloqueadas
        names = {}
        if u.get("sub_unit"):
            names[u["sub_unit"]] = u["sub_unit_name"]
            names[f"{u['sub_unit']}_desc"] = u["lore"]
        for t, n in (u.get("tech_names") or {}).items():
            if t in locked and t not in renamed:
                names[t] = {"english": n["en"], "spanish": n["es"]}
        have = ctx.vanilla.localisation("english", set(names))
        for key in sorted(have):
            n = names[key]
            ctx.loc.define_and_reference(key, en=n["english"], es=n["spanish"], file=LOC_FILE,
                                         origin=f"unique:{uid}")

        ctx.note(f"unidad unica {uid} ({tag}): {len(locked)} tecnologias bloqueadas para el resto "
                 f"({', '.join(sorted(locked)[:10])}); el desbloqueo da {', '.join(dict.fromkeys(grant)) or 'nada'}")

    ctx.write_script("common/scripted_effects/meganations_unique_units.txt", effects, source=SOURCE)
    if ideas.entries:
        ctx.write_script("common/ideas/meganations_unique_units.txt",
                         Block([("ideas", Block([("country", ideas)]))]), source=SOURCE)
    ctx.verify_keys("effects", effects_used)
    ctx.verify_keys("triggers", {"original_tag": "unique_units"})


def _design(ctx, uid: str, design: dict, equip: dict[str, Block], modules: dict[str, Block],
            tree: dict[str, dict]) -> tuple[Block | None, list[str]]:
    """El diseño armado con las piezas del juego y las tecnologías que pide."""
    if not design:
        return None, []
    words = design.get("chassis") or []
    by_year = sorted((_year(b), name) for name, b in equip.items()
                     if any(w in name for w in words) and text(b.get("is_archetype")) != "yes"
                     and _inherited(b, equip, "module_slots") is not None)
    if not by_year:
        ctx.warn(f"{uid}: el juego no tiene un chasis con casillas para {words}; sin diseño.")
        return None, []
    chassis = by_year[0][1]
    block = equip[chassis]
    slots = _inherited(block, equip, "module_slots")
    defaults = _inherited(block, equip, "default_modules")
    enabled_by = {}
    for t, info in sorted(tree.items(), key=lambda kv: (kv[1]["year"], kv[0])):
        for e in info["enables"]:
            enabled_by.setdefault(e, t)

    chosen: dict[str, str] = {}
    picked_from: dict[str, str] = {}
    prefs = design.get("modules") or {}
    slot_names = [k for k in prefs if k in slots.keys()] + [k for k in slots.keys() if k not in prefs]
    for slot in slot_names:
        sb = slots.get(slot)
        if not isinstance(sb, Block):
            continue
        cats = sb.get("allowed_module_categories")
        allowed = {text(v) for _, v in cats.entries} if isinstance(cats, Block) else set()
        fits = {m: b for m, b in modules.items() if text(b.get("category")) in allowed}
        pick = None
        for want in prefs.get(slot) or []:
            hits = [m for m in fits if m == want] or sorted(
                (m for m in fits if want in m),
                key=lambda m: (tree.get(enabled_by.get(m, ""), {}).get("year", 0), m))
            hits = [m for m in hits if not _conflicts(m, fits[m], chosen, modules)]
            if hits:
                pick, picked_from[slot] = hits[0], want
                break
        if pick is None and isinstance(defaults, Block) and text(defaults.get(slot)) in fits:
            pick, picked_from[slot] = text(defaults.get(slot)), "por defecto"
        if pick is not None:
            chosen[slot] = pick
        elif text(sb.get("required")) == "yes":
            ctx.warn(f"{uid}: la casilla obligatoria {slot} quedo vacia")

    variant = Block([("name", Quoted(design["name"])), ("type", chassis), ("parent_version", 0)])
    variant.add("modules", Block(list(chosen.items())))
    ups = _inherited(block, equip, "upgrades")
    if isinstance(ups, Block) and design.get("upgrades"):
        names = [text(v) for k, v in ups.entries if k is None] + [k for k, _ in ups.entries if k]
        levels = Block()
        for word, level in design["upgrades"].items():
            hit = next((n for n in names if n and word in n), None)
            if hit:
                levels.add(hit, int(level))
        if levels.entries:
            variant.add("upgrades", levels)
    variant.add("obsolete", False)
    grant = [enabled_by[m] for m in chosen.values() if m in enabled_by]
    ctx.note(f"{uid}: diseño '{design['name']}' sobre {chassis}: "
             + ", ".join(f"{s}={m} ({picked_from[s]})" for s, m in chosen.items()))
    return variant, grant


def _conflicts(mid: str, mb: Block, chosen: dict[str, str], modules: dict[str, Block]) -> bool:
    """Una pieza que prohíbe (o es prohibida por) alguna ya elegida."""
    def forbidden(b: Block) -> set[str]:
        out = set()
        for k, v in b.entries:
            if k and ("forbid" in k or "incompatible" in k) and isinstance(v, Block):
                out |= {text(x) for _, x in v.entries if not isinstance(x, Block)}
        return out
    mine = forbidden(mb)
    for other in chosen.values():
        ob = modules.get(other) or Block()
        if other in mine or text(ob.get("category")) in mine:
            return True
        theirs = forbidden(ob)
        if mid in theirs or text(mb.get("category")) in theirs:
            return True
    return False


def _inherited(block: Block, equip: dict[str, Block], key: str):
    """Un campo del equipo, o del arquetipo/padre si dice `inherit` o no está."""
    seen = set()
    while block is not None:
        value = block.get(key)
        if isinstance(value, Block):
            return value
        nxt = text(block.get("parent")) or text(block.get("archetype"))
        if not nxt or nxt in seen:
            return None
        seen.add(nxt)
        block = equip.get(nxt)
    return None


def _year(b: Block) -> int:
    y = text(b.get("year")) if b.get("year") is not None else None
    return int(y) if y and y.isdigit() else 1936


def _equipment_blocks(root) -> dict[str, Block]:
    out: dict[str, Block] = {}
    for path in sorted((root / "common" / "units" / "equipment").glob("*.txt")):
        try:
            blk = parse_file(path).get("equipments")
        except ValueError:
            continue
        if isinstance(blk, Block):
            out.update({k: v for k, v in blk.entries if k and isinstance(v, Block)})
    return out


def _module_blocks(root) -> dict[str, Block]:
    out: dict[str, Block] = {}
    for path in sorted((root / "common" / "units" / "equipment" / "modules").glob("*.txt")):
        try:
            blk = parse_file(path).get("equipment_modules")
        except ValueError:
            continue
        if isinstance(blk, Block):
            out.update({k: v for k, v in blk.entries if k and isinstance(v, Block) and not k.startswith("@")})
    return out


def _picture(idea_sprites: list[str], words: list[str]) -> str | None:
    for w in words:
        hits = [n for n in idea_sprites if w in n.lower()]
        if hits:
            generic = [n for n in hits if "generic" in n.lower()]
            return (generic or hits)[0][len("GFX_idea_"):]
    return idea_sprites[0][len("GFX_idea_"):] if idea_sprites else None


def lock_techs(src: str, locks: dict[str, str]) -> tuple[str, int]:
    """Suma `original_tag = TAG` al `allow` y al `allow_branch` de cada
    tecnología única (los crea si no están). allow: nadie más la investiga;
    allow_branch: nadie más la ve en el árbol. Si ya tenían condiciones (un
    DLC), la nuestra se suma a ellas (todas tienen que cumplirse)."""
    from .research import _children
    inserts: list[tuple[int, str]] = []
    count = 0
    for key, open_at, end in _children(src, 0, len(src)):
        if key != "technologies":
            continue
        for tech, t_open, t_end in _children(src, open_at + 1, end):
            tag = locks.get(tech)
            if not tag:
                continue
            count += 1
            own = {k: o for k, o, _ in _children(src, t_open + 1, t_end)}
            for field in ("allow", "allow_branch"):
                if field in own:
                    inserts.append((own[field] + 1, f"\n\t\t\toriginal_tag = {tag}  # 2100 unidad unica\n\t\t\t"))
                else:
                    inserts.append((t_open + 1, f"\n\t\t{field} = {{ original_tag = {tag} }}  # 2100 unidad unica"))
    for at, snippet in sorted(inserts, key=lambda x: x[0], reverse=True):
        src = src[:at] + snippet + src[at:]
    return src, count
