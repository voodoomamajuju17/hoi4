"""Unidades únicas (spec/20_unique_units.yaml).

Produce:
  common/scripted_effects/meganations_unique_units.txt   <id>_desbloqueo
  common/ideas/meganations_unique_units.txt              el espíritu de cada unidad
y deja para otros emisores:
  ctx.data["tech_locks"]        tech -> TAG: solo ese país la investiga (research.py
                                la bloquea con allow/allow_branch; ver lock_techs)
  ctx.data["unique_ai_plans"]   planes de IA que se activan con el desbloqueo (ai.py)
Además saca de las tecnologías de arranque de cada país (military.py) las
que son únicas de otro.

Nada se escribe de memoria: el chasis, sus casillas, las piezas, el equipo y
las tecnologías que los habilitan se leen de la instalación. Una preferencia
del spec que no existe se saltea; lo que quedó va al reporte.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted, parse_file, text
from . import ideas as ideas_mod
from .effects import EffectContext, render_effects

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
    look = ctx.spec.raw.get("research_look") or {}
    renamed = set(look.get("techs") or {}) | set(look.get("equipment") or {})
    gfx = ctx.vanilla.gfx_names()
    idea_sprites = ideas_mod.generic_candidates(gfx or (), ctx.vanilla.gfx_textures(), ctx.vanilla.root)
    enabled_by: dict[str, str] = {}
    for t, info in sorted(tree.items(), key=lambda kv: (kv[1]["year"], kv[0])):
        for e in info["enables"]:
            enabled_by.setdefault(e, t)

    locks: dict[str, str] = ctx.data.setdefault("tech_locks", {})
    visible: set[str] = ctx.data.setdefault("tech_locks_visible", set())
    plans: list[dict] = ctx.data.setdefault("unique_ai_plans", [])
    effects = Block()
    ideas = Block()
    effects_used: dict[str, str] = {}
    modifiers_used: dict[str, str] = {}
    ec = EffectContext(set(), {c.tag for c in ctx.spec.countries})
    for u in units:
        uid, tag = u["id"], u["country"]
        ctx.spec.country(tag)
        if not uid.startswith(f"{tag}_"):
            raise SpecError(f"la unidad '{uid}' de {tag} no empieza con '{tag}_'", where=SOURCE)

        # 1. Bloqueo de la investigación. Explícitas (las que existan) y las
        # que SOLO habilitan cosas con alguna de las palabras de `enables`.
        lock = u.get("lock") or {}
        words = lock.get("enables") or []
        locked = [t for t in lock.get("techs") or [] if t in tree]
        locked += [t for t, info in tree.items() if t not in locked and words and info["enables"]
                   and all(any(w in e for w in words) for e in info["enables"])]
        for t in locked:
            if locks.get(t, tag) != tag:
                raise SpecError(f"{uid}: la tecnologia '{t}' ya es unica de {locks[t]}", where=SOURCE)
            locks[t] = tag
            if lock.get("hide_branch") is False:
                visible.add(t)
        if not locked:
            ctx.warn(f"{uid}: ninguna tecnologia para bloquear en este juego; la unidad no es unica.")

        # 2. El equipo de la unidad: un diseño armado o un equipo fijo
        design = u.get("design") or {}
        grant: list[str] = []
        variant, version = None, None
        if design:
            variant, grant = _design(ctx, uid, design, equip, modules, tree, enabled_by)
            eq_type = text(variant.get("type")) if variant is not None else None
            version = design["name"] if variant is not None else None
        else:
            eq_type = _fixed_equipment(u.get("equipment") or [], equip, enabled_by)
            if u.get("equipment") and not eq_type:
                ctx.warn(f"{uid}: el juego no tiene equipo para {u['equipment']}")
        if eq_type and eq_type in enabled_by:
            grant.insert(0, enabled_by[eq_type])
        g = u.get("grant") or {}
        grant = [t for t in g.get("techs") or [] if t in tree] + grant
        for word in g.get("techs_enabling") or []:
            hit = next((t for e, t in sorted(enabled_by.items(), key=lambda kv: (tree[kv[1]]["year"], kv[0]))
                        if word in e), None)
            if hit:
                grant.append(hit)
        grant = list(dict.fromkeys(grant))

        body = Block()
        if grant:
            body.add("set_technology", Block([(t, 1) for t in grant] + [("popup", False)]))
            effects_used.setdefault("set_technology", uid)
        if variant is not None:
            body.add("create_equipment_variant", variant)
            effects_used.setdefault("create_equipment_variant", uid)
        stock = [(eq_type, int(g.get("equipment", 0)), version)] if eq_type and g.get("equipment") else []
        for extra in g.get("extra_equipment") or []:
            t = _fixed_equipment([extra["like"]], equip, enabled_by)
            if t:
                stock.append((t, int(extra["amount"]), None))
        for t, amount, ver in stock:
            sb = Block([("type", t), ("amount", amount), ("producer", tag)])
            if ver:
                sb.add("variant_name", Quoted(ver))
            body.add("add_equipment_to_stockpile", sb)
            effects_used.setdefault("add_equipment_to_stockpile", uid)

        # plantilla y divisiones de arranque (el DSL de focos/eventos: el
        # nombre sale como una sola palabra, create_unit lo necesita así)
        tpl = u.get("template")
        dsl: list[dict] = [{"effect": "flag", "value": f"{uid}_desbloqueado"}]
        bad = [r for r in (tpl or {}).get("regiments", []) + ((tpl or {}).get("support") or []) if r not in sub_units]
        if bad:
            ctx.warn(f"{uid}: batallones que el juego no tiene ({', '.join(bad)}): sin plantilla ni divisiones")
        if tpl and not bad:
            # lo que el juego trata como apoyo va en `support` aunque el spec lo
            # ponga como batallón (el superpesado es apoyo en 1.19.3)
            support_type = ctx.vanilla.support_sub_units()
            regs = [r for r in tpl["regiments"] if r not in support_type]
            sup = list(tpl.get("support") or []) + [r for r in tpl["regiments"] if r in support_type]
            if len(sup) > 5:
                ctx.warn(f"{uid}: mas de 5 compañias de apoyo; se dejan 5")
                sup = sup[:5]
            if not regs:
                regs = ["infantry"]
            dsl.append({"effect": "division_template", "name": tpl["name"], "regiments": regs,
                        "support": sup})
            if int(u.get("divisions", 0) or 0):
                dsl.append({"effect": "create_units", "template": tpl["name"], "count": int(u["divisions"]),
                            "experience": 0.3})
        body.entries.extend(render_effects(uid, dsl, ec, effects_used, where=SOURCE).entries)

        # cola de producción: arranca fabricándola (jugador e IA)
        prod = u.get("production")
        if prod and eq_type:
            eb = Block([("type", eq_type), ("creator", Quoted(tag))])
            if version:
                eb.add("version_name", Quoted(version))
            body.add("add_equipment_production", Block([
                ("equipment", eb), ("requested_factories", int(prod.get("factories", 1))),
                ("progress", float(prod.get("progress", 0))), ("amount", int(prod.get("amount", 1)))]))
            effects_used.setdefault("add_equipment_production", uid)

        # 3. El espíritu
        spirit = u.get("spirit")
        if spirit and not eq_type and not spirit.get("modifiers"):
            ctx.warn(f"{uid}: sin equipo en este juego, el espiritu {spirit['id']} no se crea")
            spirit = None
        if spirit:
            sid = spirit["id"]
            idea = Block()
            picture = _picture(idea_sprites, spirit.get("picture_prefer") or [])
            if picture:
                idea.add("picture", picture)
            idea.add("allowed", Block([("always", False)]))
            idea.add("removal_cost", -1)
            mods = Block()
            for key, value in (spirit.get("modifiers") or {}).items():
                if key.startswith("?"):
                    key = key[1:]
                    if ctx.vanilla.documented_keys("modifiers") is not None \
                            and not ctx.vanilla.is_documented("modifiers", key):
                        ctx.warn(f"{sid}: el modificador '{key}' no existe en este juego; se omite.")
                        continue
                else:
                    modifiers_used.setdefault(key, sid)
                mods.add(key, float(value))
            if mods.entries:
                idea.add("modifier", mods)
            if spirit.get("equipment_bonus") and eq_type:
                chassis = equip.get(eq_type) or Block()
                archetype = text(chassis.get("archetype")) or eq_type
                bonus = Block([(k, float(v)) for k, v in spirit["equipment_bonus"].items()] + [("instant", True)])
                idea.add("equipment_bonus", Block([(archetype, bonus)]))
            if not mods.entries and idea.get("equipment_bonus") is None:
                idea.add("modifier", Block([("army_org_factor", 0.0)]))   # el juego no acepta una idea vacía
            ideas.add(ctx.loc.reference(sid, f"unique:{sid}"), idea)
            ctx.loc.define(sid, en=spirit["name"]["english"], es=spirit["name"]["spanish"],
                           file="meganations_unique_units", origin=f"unique:{sid}")
            ctx.loc.define_and_reference(f"{sid}_desc", en=spirit["desc"]["english"], es=spirit["desc"]["spanish"],
                                         file="meganations_unique_units", origin=f"unique:{sid}")
            body.add("add_ideas", sid)
            effects_used.setdefault("add_ideas", uid)

        effects.add(f"{uid}_desbloqueo", body)

        # Estadísticas del batallón que no son del equipo (ej. uso de
        # suministros): se cambia la definición del juego (solo la tiene esta
        # potencia). Factor: 1.05 = +5%.
        if u.get("sub_unit_stats"):
            _sub_unit_stats(ctx, uid, u["sub_unit_stats"])

        # 4. IA: después del desbloqueo, que la fabrique (sin exagerar)
        if u.get("ai"):
            plans.append({"id": f"{uid}_produccion", "country": tag, "strategies": list(u["ai"]),
                          "enable": {"flag": f"{uid}_desbloqueado"}})

        # Para el arte (faction_tech): su ícono en el equipo y las tecnologías propias
        ctx.data.setdefault("uu_art", []).append({"id": uid, "tag": tag, "equipment": eq_type,
                                                   "techs": sorted(locked)})

        # 5. Nombres: el batallón (pisa el del juego) y las tecnologías bloqueadas
        names = {}
        if u.get("sub_unit"):
            names[u["sub_unit"]] = u["sub_unit_name"]
            names[f"{u['sub_unit']}_desc"] = u["lore"]
        for t, n in (u.get("tech_names") or {}).items():
            if t in locked and t not in renamed:
                names[t] = {"english": n["en"], "spanish": n["es"]}
        for key, n in (u.get("names") or {}).items():
            if key not in renamed:
                names[key] = {"english": n["en"], "spanish": n["es"]}
        # 2026-10-02 (captura del usuario: "Tanque moderno Mk2"): el juego le
        # pone a cada diseño nuevo el nombre del ARQUETIPO + Mk N. Si el equipo
        # es solo de esta potencia (bloqueado al resto), el arquetipo lleva el
        # nombre de la unidad única: "Gliptodonte Mk2".
        arche = None
        if eq_type and enabled_by.get(eq_type) in locked:
            arche = text((equip.get(eq_type) or Block()).get("archetype")) or eq_type
            if arche in names or arche in renamed:
                arche = None
            else:
                ctx.note(f"unidad unica {uid}: los disenos nuevos se llaman '{u['name']['spanish']} MkN' ({arche})")
        have = ctx.vanilla.localisation("english", set(names))
        if arche:
            names[arche] = u["name"]
            have = set(have) | {arche}   # aunque el juego de prueba no lo tenga
        for key in sorted(have):
            n = names[key]
            ctx.loc.define_and_reference(key, en=n["english"], es=n["spanish"], file=LOC_FILE,
                                         origin=f"unique:{uid}")

        ctx.note(f"unidad unica {uid} ({tag}): {len(locked)} tecnologias bloqueadas para el resto "
                 f"({', '.join(sorted(locked)[:10])}); equipo {eq_type or 'ninguno'}; "
                 f"el desbloqueo da {', '.join(grant) or 'nada'}")

    # Nadie arranca con la tecnología única de otro (las especialidades de
    # 13_military eligen por pestaña y podían caer en una).
    for tag, techs in (ctx.data.get("techs") or {}).items():
        gone = [t for t in techs if locks.get(t, tag) != tag]
        if gone:
            techs[:] = [t for t in techs if t not in gone]
            ctx.note(f"unidades unicas: {tag} ya no arranca con {', '.join(gone)} (son de otra potencia)")

    ctx.write_script("common/scripted_effects/meganations_unique_units.txt", effects, source=SOURCE)
    if ideas.entries:
        ctx.write_script("common/ideas/meganations_unique_units.txt",
                         Block([("ideas", Block([("country", ideas)]))]), source=SOURCE)
    ctx.verify_keys("effects", effects_used)
    ctx.verify_keys("modifiers", modifiers_used)
    ctx.verify_keys("triggers", {"original_tag": "unique_units"})


def _fixed_equipment(words: list[str], equip: dict[str, Block], enabled_by: dict[str, str]) -> str | None:
    """El equipo más viejo (no arquetipo) cuyo id tenga alguna de las palabras,
    prefiriendo los que habilita una tecnología."""
    hits = [(n not in enabled_by, _year(b), n) for n, b in equip.items()
            if any(w in n for w in words) and text(b.get("is_archetype")) != "yes"]
    return sorted(hits)[0][2] if hits else None


def _design(ctx, uid: str, design: dict, equip: dict[str, Block], modules: dict[str, Block],
            tree: dict[str, dict], enabled_by: dict[str, str]) -> tuple[Block | None, list[str]]:
    """El diseño armado con las piezas del juego y las tecnologías que pide."""
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
    max_year = design.get("max_module_year")

    def year_of(m: str) -> int:
        return tree.get(enabled_by.get(m, ""), {}).get("year", 0)

    chosen: dict[str, str] = {}
    picked_from: dict[str, str] = {}
    prefs = design.get("modules") or {}

    def prefs_for(slot: str) -> list[str]:
        if slot in prefs:
            return prefs[slot]
        return next((v for k, v in prefs.items() if k in slot), [])

    order = [k for k in prefs if k in slots.keys()]
    order += [k for k in slots.keys() if k not in order]
    for slot in order:
        sb = slots.get(slot)
        if not isinstance(sb, Block):
            continue
        cats = sb.get("allowed_module_categories")
        allowed = {text(v) for _, v in cats.entries} if isinstance(cats, Block) else set()
        fits = {m: b for m, b in modules.items() if text(b.get("category")) in allowed
                and (max_year is None or year_of(m) <= int(max_year))
                and not _conflicts(m, b, chosen, modules)}
        pick = None
        for want in prefs_for(slot):
            hits = [m for m in fits if m == want] or sorted((m for m in fits if want in m), key=lambda m: (year_of(m), m))
            if hits:
                pick, picked_from[slot] = hits[0], want
                break
        if pick is None and isinstance(defaults, Block) and text(defaults.get(slot)) in fits:
            pick, picked_from[slot] = text(defaults.get(slot)), "por defecto"
        if pick is None and text(sb.get("required")) == "yes" and fits:
            pick = sorted(fits, key=lambda m: (year_of(m), m))[0]
            picked_from[slot] = "la primera que entra"
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


def lock_techs(src: str, locks: dict[str, str], visible: set[str] | frozenset = frozenset()) -> tuple[str, int]:
    """Suma `original_tag = TAG` al `allow` y al `allow_branch` de cada
    tecnología única (los crea si no están). allow: nadie más la investiga;
    allow_branch: nadie más la ve en el árbol (salvo las de `visible`, que
    se ven pero no se pueden investigar: una línea de la que cuelgan otras).
    Si ya tenían condiciones (un DLC), la nuestra se suma a ellas."""
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
            fields = ("allow",) if tech in visible else ("allow", "allow_branch")
            for field in fields:
                if field in own:
                    inserts.append((own[field] + 1, f"\n\t\t\toriginal_tag = {tag}  # 2100 unidad unica\n\t\t\t"))
                else:
                    inserts.append((t_open + 1, f"\n\t\t{field} = {{ original_tag = {tag} }}  # 2100 unidad unica"))
    for at, snippet in sorted(inserts, key=lambda x: x[0], reverse=True):
        src = src[:at] + snippet + src[at:]
    return src, count


def _sub_unit_stats(ctx: BuildContext, uid: str, wanted: dict) -> None:
    """Multiplica estadísticas de batallones del juego (common/units), en una
    copia del archivo con el mismo nombre (pisa al original)."""
    from ..pdx import text as ptext
    for path in sorted((ctx.vanilla.root / "common" / "units").glob("*.txt")):
        try:
            root = parse_file(path)
        except ValueError:
            continue
        subs = root.get("sub_units")
        if not isinstance(subs, Block):
            continue
        changed = []
        for key, body in subs.entries:
            if key not in wanted or not isinstance(body, Block):
                continue
            for stat, factor in wanted[key].items():
                old = body.get(stat)
                try:
                    val = float(ptext(old))
                except (TypeError, ValueError):
                    ctx.warn(f"{uid}: el batallon {key} no tiene '{stat}' en el juego; no se cambia.")
                    continue
                new = round(val * float(factor), 4)
                body.entries = [(k, new if k == stat else v) for k, v in body.entries]
                changed.append(f"{key}.{stat} {val:g} -> {new:g}")
        if changed:
            ctx.write_script(f"common/units/{path.name}", root,
                             source=f"{path.name} del juego con {', '.join(changed)} ({SOURCE})")
            ctx.note(f"{uid}: {', '.join(changed)}")
