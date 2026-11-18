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
from . import effects as effects_mod
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
    effects_mod.DESTINY_PICKS.clear()
    _emit(ctx)
    effects_mod.flush_tooltips(ctx)


def emit_destiny_ai(ctx: BuildContext) -> None:
    """MEGANATIONS_destino_ia (2026-10-15): el siguiente objetivo del destino de
    la IA, de a uno (effects.py -> wargoal_holders ai_one_at_a_time). Lo corre
    el pulso mensual (MEGANATIONS_renovar_casus_belli). Va después de las
    decisiones, que también lo arman; el archivo empieza con "a" para que el
    juego lo lea antes que meganations_casus_belli.txt, que lo llama."""
    body = Block()
    by_tag: dict[str, list] = {}
    for (tag, key), (when, pick) in sorted(effects_mod.DESTINY_PICKS.items(), key=lambda kv: kv[0]):
        by_tag.setdefault(tag, []).append((when, pick))
    for tag, picks in by_tag.items():
        inner = Block([("limit", Block([("tag", tag)]))])
        for when, pick in picks:
            # 2026-11-02: varias listas por país; la primera que elige un dueño deja
            # la marca y las demás ya no eligen ese mes
            if when is None:
                inner.entries.extend(pick.entries)
            else:
                inner.add("if", Block([("limit", when)] + pick.entries))
        inner.add("clr_country_flag", "MEGANATIONS_destino_elegido")
        body.add("if", inner)
    ctx.write_script("common/scripted_effects/meganations_a_destino_ia.txt",
                     Block([(effects_mod.DESTINY_EFFECT, body)]), source=SOURCE)
    ctx.note(f"destino de la IA de a uno: {', '.join(sorted(by_tag)) or 'ninguno'}")


def _emit(ctx: BuildContext) -> None:
    from . import effects as _effects
    _effects.KNOWN_FOCUSES.clear()
    _effects.KNOWN_FOCUSES.update(
        f["id"] for tree in ((ctx.spec.raw.get("focus_trees") or {}).get("trees") or {}).values()
        if isinstance(tree, dict) for branch in tree.get("branches") or [] for f in branch.get("focuses") or [])
    effects_mod.use_states(ctx.data.get("state_ids_by_name"))
    effects_mod.use_variable_names(ctx.spec.raw)
    effects_mod.use_territory(ctx.data.get("territory"))
    effects_mod.use_cores(ctx.data.get("state_cores"))
    effects_mod.use_equipment(ctx.vanilla)
    trees = ctx.spec.raw["focus_trees"].get("trees") or {}
    for tag, tree in trees.items():
        if not isinstance(tree, dict) or "branches" not in tree:
            continue  # not_started: sin árbol, el país usa el genérico
        if not tree.get("shared"):
            ctx.spec.country(tag)  # falla si el TAG no existe
        # shared (2026-10-11, la junta militar): sin país; lo carga un efecto
        # (load_focus_tree) en el país que nace en la partida
        _emit_tree(ctx, tag, tree)


def _emit_tree(ctx: BuildContext, tag: str, tree: dict) -> None:
    # Convención de arte: assets/<TAG>/goals/<id_del_foco>.dds se conecta solo.
    repo = ctx.spec.root.parent
    for branch in tree["branches"]:
        for f in branch.get("focuses", []) or []:
            own = repo / "assets" / tag / "goals" / f"{f['id']}.dds"
            # 2026-11-05 (captura: cuatro focos del EFE seguían con el ícono viejo): el ícono
            # propio del foco (los pines nuevos) gana también sobre un icon_asset viejo
            if own.exists():
                f["icon_asset"] = f"assets/{tag}/goals/{f['id']}.dds"
                f["icon"] = f"GFX_focus_{f['id']}"
    # Un icono propio es de un solo foco: repetirlo está prohibido.
    owner: dict[str, str] = {}
    for branch in tree["branches"]:
        for f in branch.get("focuses", []) or []:
            asset = f.get("icon_asset")
            if not asset:
                continue
            if asset in owner:
                raise SpecError(f"{f['id']}: el icono '{asset}' ya es de {owner[asset]}; "
                                "cada foco lleva su propio icono", where="07_focus_trees.yaml")
            owner[asset] = f["id"]
    # las potencias, la Anarquía (y el Santuario) y los árboles compartidos se
    # frenan con señor; los satélites de arranque no (nacen satélites)
    country = None if tree.get("shared") else next((c for c in ctx.spec.countries if c.tag == tag), None)
    freeze = bool((ctx.spec.raw["focus_trees"].get("policy") or {}).get("freeze_when_subject")) and (
        country is None or not country.is_subject)
    focuses: list[tuple[str, dict]] = []  # (rama, foco)
    branch_ai: dict[str, float] = {}
    for branch in tree["branches"]:
        if branch.get("ai_factor") is not None:
            branch_ai[branch["id"]] = branch["ai_factor"]  # peso de la IA para toda la rama
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
    # 2026-11-18 (Rediseño de los árboles de foco): un árbol con `forma` se dibuja con la suya
    positions = _layout_forma(focuses, depth, tree["forma"], ctx.warn) if tree.get("forma") else _layout(focuses, depth)
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
        scripted=scripted_effect_ids(ctx.spec.raw), dynamic_modifiers=effects_mod.dynamic_modifier_ids(ctx.spec.raw),
        tech_categories=ctx.vanilla.tech_categories() if ctx.vanilla else None,
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
    if not tree.get("shared"):
        modifier = Block()
        modifier.add("add", 10)
        modifier.add("tag", tag)
        country.add("modifier", modifier)
    body.add("country", country)
    body.add("default", bool(tree.get("default", False)))
    if tree.get("forma"):
        # el árbol se abre centrado en su foco raíz (los de forma propia crecen para todos lados)
        raiz = next((f["id"] for _, f in focuses if depth[f["id"]] == 0), None)
        if raiz:
            body.add("initial_show_position", Block([("focus", raiz)]))
    # El panel de enfoques continuos va debajo del último foco. En su lugar
    # por defecto tapa las filas de abajo (captura del usuario, 2026-09-23).
    # Cada fila del árbol mide 130 px en pantalla.
    last_row = max(y for _, y in positions.values())
    pos = Block()
    pos.add("x", 50)
    pos.add("y", (last_row + 2) * 130)
    body.add("continuous_focus_position", pos)

    for bid, f in focuses:
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
        if f.get("hidden_until_prereqs"):
            # foco secreto: no se ve hasta tener todos sus prerequisitos
            ab = Block([("has_completed_focus", pre) for pre in f.get("prerequisites") or []])
            fb.add("allow_branch", ab)
            triggers_used.setdefault("has_completed_focus", fid)
        if exclusive.get(fid):
            me = Block()
            for other in sorted(exclusive[fid]):
                me.add("focus", other)
            fb.add("mutually_exclusive", me)

        available = f.get("available")
        block = _available(ctx, tag, fid, available, triggers_used) if isinstance(available, dict) else Block()
        if freeze:
            # 2026-10-13: con señor, el árbol se frena (títere o satélite)
            block.entries.extend(render_conditions(fid, {"subject": False}, triggers_used,
                                                   where="07_focus_trees.yaml").entries)
        if block.entries:
            fb.add("available", block)

        reward = f.get("reward")
        if not isinstance(reward, list) or not reward:
            raise SpecError(f"{fid}: sin reward", where="07_focus_trees.yaml")
        completion = render_effects(fid, reward, effect_ctx, effects_used, where="07_focus_trees.yaml")
        for event_id in events_mod.fired_by_focus(ctx, fid):
            completion.add("country_event", event_id)
            effects_used.setdefault("country_event", fid)
        fb.add("completion_reward", completion)

        fb.add("ai_will_do", _ai(fid, _branch_weighted(f.get("ai"), branch_ai.get(bid)), triggers_used))
        body.add("focus", fb)

        desc = f.get("desc")
        if not isinstance(desc, dict):
            raise SpecError(f"{fid}: falta desc en EN y ES (TN010)", where="07_focus_trees.yaml")
        ctx.loc.define(fid, en=f["name"]["english"], es=f["name"]["spanish"],
                       file=LOC_FILE, origin=f"focus:{fid}")
        en, es = desc["english"], desc["spanish"]
        for alt in _or_cores(reward):
            en, es = f"{en}\\n\\n{_OR_CORES_TEXT[alt][0]}", f"{es}\\n\\n{_OR_CORES_TEXT[alt][1]}"
        ctx.loc.define_and_reference(f"{fid}_desc", en=en, es=es, file=LOC_FILE, origin=f"focus:{fid}")

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


def _layout_forma(focuses: list[tuple[str, dict]], depth: dict[str, int], forma: dict,
                  warn=None) -> dict[str, tuple[int, int]]:
    """2026-11-18 (Rediseño de los árboles de foco): cada árbol con su dibujo.

    2026-11-18, segunda versión ("Hay lineas q sobrepasan la imagen en los arboles de focos, corregir"): el
    juego dibuja cada línea saliendo por ABAJO del foco previo y entrando por ARRIBA del siguiente, así que
    una rama que crece hacia arriba o de costado arrastra líneas que dan la vuelta y cruzan otros focos. Ahora
    todo cuelga hacia abajo de lo que lo habilita; la forma de cada nación está en dónde va cada rama de
    izquierda a derecha y en las ramas que bajan en escalera.

    forma:
      raiz: x                          columna del foco raíz (va arriba de todo)
      at: {foco: x}                    focos sueltos (el tronco) en su columna
      grupos:                          cada grupo es una rama (`rama`), varias (`ramas`, juntas: para que dos
        - {rama: id, origen: x,        focos excluyentes queden lado a lado) o una lista de focos (`focos`)
           dir: abajo|derecha|izquierda}   derecha/izquierda: baja en escalera hacia ese lado
    Cada grupo baja justo debajo de lo que lo habilita (nunca más arriba que un previo). Si no entra donde se
    pidió, se corre de costado al lugar libre más cercano donde sus líneas no atraviesen otro foco. Los focos
    excluyentes de una misma capa quedan juntos.
    """
    orden = {f["id"]: i for i, (_, f) in enumerate(focuses)}
    rama_de = {f["id"]: b for b, f in focuses}
    previos = {f["id"]: _all_prereqs(f) for _, f in focuses}
    excl = {f["id"]: set(f.get("mutually_exclusive") or []) for _, f in focuses}
    roots = [f["id"] for _, f in focuses if depth[f["id"]] == 0]
    pos: dict[str, tuple[int, int]] = {}

    def _num(v):
        return int(v[0]) if isinstance(v, (list, tuple)) else int(v)

    x0 = _num(forma.get("raiz", 0))
    for i, r in enumerate(roots):
        pos[r] = (x0 + 2 * i, 0)
    grupos = [{"focos": [fid], "origen": x} for fid, x in (forma.get("at") or {}).items()]
    grupos += list(forma.get("grupos") or [])
    tomados = set(pos)
    specs = []
    for g in grupos:
        if g.get("focos"):
            ids = [fid for fid in g["focos"] if fid not in tomados]
        else:
            ramas = g["ramas"] if g.get("ramas") else [g["rama"]]
            ids = [fid for fid in orden if rama_de[fid] in ramas and fid not in tomados]
        tomados |= set(ids)
        if ids:
            specs.append((ids, _num(g["origen"]), g.get("dir", "abajo")))
    faltan = [fid for fid in orden if fid not in tomados]
    if faltan:
        raise SpecError(f"forma: focos sin lugar en el dibujo: {faltan}", where="45_arboles.yaml")

    def cruces(cand: dict[str, tuple[int, int]]) -> int:
        """Líneas verticales (en la columna del hijo, entre la fila del previo y la suya) que pasan por un
        foco, entre lo nuevo y lo ya puesto."""
        todo = {**pos, **cand}
        celdas = {}
        for fid, (x, y) in todo.items():
            celdas.setdefault(y, []).append((x, fid))
        n = 0
        for hijo, (cx, cy) in todo.items():
            for p in previos[hijo]:
                if p not in todo:
                    continue
                py = todo[p][1]
                for yy in range(py + 1, cy):
                    for (xx, otro) in celdas.get(yy, []):
                        if abs(xx - cx) <= 1 and (otro in cand or hijo in cand):
                            n += 1
        return n

    def armar(ids, ox, d, shift):
        base = min(depth[f] for f in ids)
        capas: dict[int, list[str]] = {}
        for fid in sorted(ids, key=lambda f: orden[f]):
            capas.setdefault(depth[fid] - base, []).append(fid)
        cand: dict[str, tuple[int, int]] = {}
        y_prev = None
        for capa, miembros in sorted(capas.items()):
            def centro(fid):
                ps = [(pos.get(p) or cand.get(p)) for p in previos[fid] if p in pos or p in cand]
                return sum(x for x, _ in ps) / len(ps) if ps else float(orden[fid])
            miembros = sorted(miembros, key=lambda f: (centro(f), orden[f]))
            # excluyentes juntos
            juntos: list[str] = []
            for fid in miembros:
                if fid in juntos:
                    continue
                juntos.append(fid)
                juntos += [o for o in miembros if o in excl[fid] and o not in juntos]
            miembros = juntos
            need = 1
            for fid in miembros:
                for p in previos[fid]:
                    q = pos.get(p) or cand.get(p)
                    if q:
                        need = max(need, q[1] + 1)
            y = need if y_prev is None else max(need, y_prev + 1)
            y_prev = y
            n = len(miembros)
            paso = 2 * capa if d == "derecha" else -2 * capa if d == "izquierda" else 0
            for i, fid in enumerate(miembros):
                cand[fid] = (ox + shift + paso + 2 * i - (n - 1), y)
        return cand

    ocupado = {v: k for k, v in pos.items()}
    pendientes = list(specs)
    while pendientes:
        listo = next((s for s in pendientes
                      if all(p in pos or p in s[0] for f in s[0] for p in previos[f])), pendientes[0])
        pendientes.remove(listo)
        ids, ox, d = listo
        mejor = None
        for k in range(0, 41):
            shift = (k + 1) // 2 * (2 if k % 2 else -2)
            cand = armar(ids, ox, d, shift)
            if any(c in ocupado for c in cand.values()) or len(set(cand.values())) < len(cand):
                continue
            costo = cruces(cand) * 60 + abs(shift)
            if mejor is None or costo < mejor[0]:
                mejor = (costo, cand, shift)
            if costo == abs(shift):
                break
        if mejor is None:
            raise SpecError(f"forma: no hay lugar para {ids[0]}", where="45_arboles.yaml")
        if mejor[2] and warn:
            warn(f"forma: {ids[0]} se corrió {mejor[2]} columnas para no chocar ni cruzar líneas")
        pos.update(mejor[1])
        ocupado.update({v: k for k, v in mejor[1].items()})
    # un previo que quedó en un grupo puesto después: el hijo baja (y todo lo que cuelga de él)
    cambio = True
    while cambio:
        cambio = False
        for fid, (x, y) in list(pos.items()):
            need = max([pos[p][1] + 1 for p in previos[fid]] or [0])
            if y < need:
                while (x, need) in ocupado:
                    x += 2
                del ocupado[pos[fid]]
                pos[fid] = (x, need)
                ocupado[(x, need)] = fid
                cambio = True
                if warn:
                    warn(f"forma: {fid} bajó a la fila {need} (un previo quedó más abajo)")
    # reparación: una línea vertical que pasa por un foco -> se corre de costado ese foco (o el hijo de la
    # línea) al lugar libre de su fila que más cruces saque; los excluyentes no se mueven (quedan juntos)
    hijos: dict[str, list[str]] = {}
    for fid in pos:
        for p in previos[fid]:
            hijos.setdefault(p, []).append(fid)

    def malos() -> list[tuple[str, str]]:
        filas: dict[int, list[tuple[int, str]]] = {}
        for fid, (x, y) in pos.items():
            filas.setdefault(y, []).append((x, fid))
        out = []
        for c, (cx, cy) in pos.items():
            for p in previos[c]:
                for yy in range(pos[p][1] + 1, cy):
                    out += [(c, o) for xx, o in filas.get(yy, []) if abs(xx - cx) <= 1]
        return out

    for _ in range(300):
        actuales = malos()
        if not actuales:
            break
        base = len(actuales)
        mejor = None
        for c, o in actuales:
            for mover in (o, c):
                if excl[mover]:
                    continue
                x, y = pos[mover]
                for dx in (2, -2, 4, -4, 6, -6, 8, -8, 10, -10):
                    if (x + dx, y) in ocupado:
                        continue
                    del ocupado[(x, y)]
                    pos[mover] = (x + dx, y)
                    ocupado[(x + dx, y)] = mover
                    n = len(malos())
                    del ocupado[(x + dx, y)]
                    pos[mover] = (x, y)
                    ocupado[(x, y)] = mover
                    if n < base and (mejor is None or (n, abs(dx)) < mejor[0]):
                        mejor = ((n, abs(dx)), mover, (x + dx, y))
        if mejor is None:
            if warn:
                warn(f"forma: quedan {base} líneas que pasan por un foco ({actuales[0][0]} / {actuales[0][1]})")
            break
        _, mover, nuevo = mejor
        del ocupado[pos[mover]]
        pos[mover] = nuevo
        ocupado[nuevo] = mover
    mx = min(x for x, _ in pos.values())
    return {fid: (x - mx, y) for fid, (x, y) in pos.items()}


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


# El camino alternativo de or_cores, dicho en la descripción del foco (el
# tooltip del juego solo muestra la rama del `if` que vale hoy).
_OR_CORES_TEXT = {
    "anarchy": ("If they have already fallen or are someone's satellite: cores on their land you hold and claims on "
                "the rest (if they are your satellite, they are annexed first).",
                "Si ya cayeron o son satélite de alguien: núcleos en lo que tengas de su tierra y reclamos sobre el "
                "resto (si son tu satélite, primero se anexan)."),
    "satellite": ("If it is no longer your satellite: cores on its land you hold and claims on the rest.",
                  "Si ya no es tu satélite: núcleos en lo que tengas de su tierra y reclamos sobre el resto."),
}


def _or_cores(reward: list) -> list[str]:
    return [r.get("kind", "anarchy") for r in reward if isinstance(r, dict) and r.get("effect") == "or_cores"]


def _branch_weighted(spec: dict | None, branch_factor: float | None) -> dict | None:
    """El peso de la rama multiplica el del foco (análisis 2026-10-01: la rama
    política pesaba 1 y la IA la hacía al final; un foco con `ai` propio
    ignoraba el peso de su rama). Las proporciones entre focos de una misma
    rama (statu quo contra revolución) no cambian."""
    if branch_factor is None:
        return spec
    if not spec:
        return {"factor": branch_factor}
    factor = round(float(spec.get("factor", 1)) * float(branch_factor), 2)
    return dict(spec, factor=int(factor) if factor == int(factor) else factor)


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