"""Aventuras de las anarquías (spec/21_aventuras.yaml).

Pedido del usuario (2026-10-16): en vez de las decisiones del líder cada 6
meses, cada anarquía tiene una historia de "elegí tu propia aventura". A los
2 meses del arranque se presenta una situación y tres personajes; se elige en
qué zapatos meterse y cada 4 meses llega una decisión nueva en su ruta.

  - 20 finales por anarquía: 30% muerte, 20% el objetivo (grandes premios),
    20% otra cosa buena, 15% consecuencias malas, 15% neutros.
  - Ninguna muerte antes de 3 decisiones (un año).
  - 1 de cada 3 eventos con imagen propia (los más épicos), además de la
    presentación de la situación y de cada personaje.

Rutas catastróficas (pedido del usuario: "alguna ruta catastrófica para la
nación, alguna rebelión, algo más surreal, guerra"): un final (o una opción)
puede llevar `catastrophe`, que se traduce acá a efectos de verdad:
  war_by: TAG          -> esa meganación nos declara la guerra (si existe, no
                          está ya en guerra con nosotros y la maneja la IA:
                          la aventura de una anarquía de la IA nunca mete al
                          jugador en una guerra que no eligió)
  rebellion: {...}     -> guerra civil: se separa un bando con nombre y
                          bandera propios (cosmetic tag de 02_countries)
  rename: ID           -> el país entero pasa a llamarse distinto (cosmetic tag)

"Si deja de cumplirse un requisito (la anarquía pasa a ser satélite, pierde
su capital o la región donde transcurre el capítulo), se cancela la cadena":
cada capítulo exige esas condiciones al salir (trigger), y cada opción agenda,
un par de días después del capítulo, el evento de corte (id 3), que solo
aparece si el capítulo no llegó (la bandera <TAG>_av_llego la pone el
capítulo al salir).

Corre después de territory (capitales y regiones) y antes de ideas, focos,
eventos y decisiones: agrega los espíritus de las leyendas a 05_ideas y los
espacios de nombres de eventos a 12_events, en memoria.
"""

from __future__ import annotations

from collections import deque

from ..context import BuildContext
from ..errors import SpecError
from . import effects as effects_mod

SOURCE = "spec/21_aventuras.yaml"
KINDS = ("muerte", "objetivo", "positivo", "negativo", "neutral")


def namespace(tag: str) -> str:
    return f"meganations_aventura_{tag.lower()}"


def _flag(tag: str, what: str) -> str:
    return f"{tag}_av_{what}"


def emit(ctx: BuildContext) -> None:
    spec = ctx.spec.raw.get("adventures") or {}
    sagas = spec.get("sagas") or {}
    if not sagas:
        return
    cfg = spec.get("config") or {}
    effects_mod.use_states(ctx.data.get("state_ids_by_name"))
    namespaces = ctx.spec.raw["events"].setdefault("namespaces", {})
    cosmetic = {ct["id"]: ct.get("parent") for ct in ctx.spec.raw["countries"].get("cosmetic_tags") or []}
    summary = {}
    for tag, saga in sagas.items():
        ctx.spec.country(tag)  # falla si el TAG no existe
        _validate(tag, saga, cfg)
        _validate_catastrophes(tag, saga, cfg, cosmetic, {c.tag for c in ctx.spec.countries})
        _ideas(ctx, tag, saga)
        ns = namespace(tag)
        if ns in namespaces:
            raise SpecError(f"{ns}: ya existe en 12_events.yaml", where=SOURCE)
        namespaces[ns] = {"country": tag, "events": _events(ctx, tag, saga, cfg)}
        n_events = 2 + len(saga["nodes"]) + len(saga["endings"])
        n_art = sum(1 for e in [saga["intro"], *saga["nodes"], *saga["endings"]] if e.get("art"))
        mix = {k: sum(1 for e in saga["endings"] if e["kind"] == k) for k in KINDS}
        cats = _catastrophes(saga)
        summary[tag] = {"events": n_events, "art": n_art, "endings": len(saga["endings"]), "mix": mix,
                        "catastrophes": {k: sorted(v) for k, v in cats.items()}}
        ctx.note(f"aventura {tag} ({saga['name']['spanish']}): {len(saga['characters'])} personajes, "
                 f"{len(saga['nodes'])} capítulos, {len(saga['endings'])} finales "
                 f"({', '.join(f'{k} {v}' for k, v in mix.items())}), {n_art} imágenes de {n_events} eventos; "
                 f"catástrofes: {', '.join(f'{k} {len(v)}' for k, v in cats.items()) or 'ninguna'}")
    ctx.data["aventuras"] = summary


# ---------------------------------------------------------------- validación

def _validate(tag: str, saga: dict, cfg: dict) -> None:
    where = f"{SOURCE} -> {tag}"
    nodes = {n["id"]: n for n in saga["nodes"]}
    endings = {e["id"]: e for e in saga["endings"]}
    if set(nodes) & set(endings) or {1, 2, 3} & (set(nodes) | set(endings)):
        raise SpecError(f"{tag}: ids repetidos o reservados (1, 2 y 3 son del motor)", where=where)
    mix = cfg.get("ending_mix") or {}
    got = {k: sum(1 for e in saga["endings"] if e["kind"] == k) for k in KINDS}
    for e in saga["endings"]:
        if e["kind"] not in KINDS:
            raise SpecError(f"{tag}.{e['id']}: tipo de final '{e['kind']}' (usar {', '.join(KINDS)})", where=where)
    if len(endings) < int(cfg.get("min_endings", 20)):
        raise SpecError(f"{tag}: {len(endings)} finales, hacen falta {cfg.get('min_endings', 20)}", where=where)
    if mix and got != {k: int(mix.get(k, 0)) for k in KINDS}:
        raise SpecError(f"{tag}: mezcla de finales {got}, se pide {mix}", where=where)
    # recorrido: cada capítulo con su profundidad mínima (1 = la presentación)
    depth: dict[int, int] = {}
    queue = deque()
    for ch in saga["characters"]:
        if ch["first"] not in nodes:
            raise SpecError(f"{tag}: el personaje {ch['id']} empieza en {ch['first']}, que no es un capítulo", where=where)
        depth[ch["first"]] = 1
        queue.append(ch["first"])
    ending_depth: dict[int, int] = {}
    while queue:
        nid = queue.popleft()
        for opt in nodes[nid]["options"]:
            nxt = opt["next"]
            if nxt in nodes:
                if nxt not in depth or depth[nid] + 1 < depth[nxt]:
                    depth[nxt] = depth[nid] + 1
                    queue.append(nxt)
            elif nxt in endings:
                ending_depth[nxt] = min(ending_depth.get(nxt, 99), depth[nid])
            else:
                raise SpecError(f"{tag}.{nid}: la opción lleva a {nxt}, que no existe", where=where)
    lost = sorted(set(nodes) - set(depth)) + sorted(set(endings) - set(ending_depth))
    if lost:
        raise SpecError(f"{tag}: capítulos o finales a los que no se llega: {lost}", where=where)
    least = int(cfg.get("min_decisions_before_death", 3))
    early = [e for e, d in ending_depth.items() if endings[e]["kind"] == "muerte" and d < least]
    if early:
        raise SpecError(f"{tag}: muertes antes de {least} decisiones: {early}", where=where)
    if _cyclic(nodes):
        raise SpecError(f"{tag}: la historia vuelve sobre sí misma (ciclo)", where=where)
    firsts = {ch["first"] for ch in saga["characters"]}
    if not saga["intro"].get("art") or any(not nodes[f].get("art") for f in firsts):
        raise SpecError(f"{tag}: la presentación y el primer capítulo de cada personaje llevan imagen", where=where)
    total = 2 + len(nodes) + len(endings)
    arts = sum(1 for e in [saga["intro"], *nodes.values(), *endings.values()] if e.get("art"))
    if arts < total * float(cfg.get("min_art_share", 0.3)):
        raise SpecError(f"{tag}: {arts} imágenes para {total} eventos (se pide 1 de cada 3)", where=where)


def _catastrophes(saga: dict) -> dict[str, list]:
    """Tipo de catástrofe -> ids de los finales y capítulos que la traen."""
    out: dict[str, list] = {}
    places = [(e["id"], e) for e in saga["endings"]]
    places += [(n["id"], o) for n in saga["nodes"] for o in n["options"]]
    for eid, holder in places:
        for kind in (holder.get("catastrophe") or {}):
            out.setdefault(kind, []).append(eid)
    return out


def _validate_catastrophes(tag: str, saga: dict, cfg: dict, cosmetic: dict, tags) -> None:
    where = f"{SOURCE} -> {tag}"
    holders = list(saga["endings"]) + [o for n in saga["nodes"] for o in n["options"]]
    for h in holders:
        cat = h.get("catastrophe") or {}
        unknown = set(cat) - {"war_by", "rebellion", "rename"}
        if unknown:
            raise SpecError(f"{tag}: catástrofe desconocida {sorted(unknown)} (war_by, rebellion, rename)", where=where)
        if cat.get("war_by") and tags and cat["war_by"] not in tags:
            raise SpecError(f"{tag}: war_by '{cat['war_by']}' no es un país del mod", where=where)
        for ct in [(cat.get("rebellion") or {}).get("cosmetic_tag"), cat.get("rename")]:
            if ct and cosmetic.get(ct) != tag:
                raise SpecError(f"{tag}: '{ct}' tiene que estar en 02_countries.yaml -> cosmetic_tags "
                                f"con parent: {tag}", where=where)
    need = int(cfg.get("min_catastrophes", 0))
    got = sum(len(v) for v in _catastrophes(saga).values())
    if got < need:
        raise SpecError(f"{tag}: {got} rutas catastróficas, se piden {need}", where=where)


def _catastrophe_effects(tag: str, cat: dict | None) -> list[dict]:
    if not cat:
        return []
    out: list[dict] = []
    if cat.get("war_by"):
        by = cat["war_by"]
        # solo si la meganación la maneja la IA: si la juega una persona, una
        # aventura ajena (la de una anarquía de la IA) no la mete en una guerra
        out.append({"effect": "if",
                    "when": {"all": [{"country_exists": by}, {"not": {"war_with": by}},
                                     {"country": {"tag": by, "when": {"is_ai": True}}}]},
                    "then": [{"effect": "scope", "target": by, "effects": [
                        {"effect": "declare_war", "target": tag, "type": cat.get("war_type", "annex_everything")}]}]})
    if cat.get("rebellion"):
        reb = cat["rebellion"]
        rebels = {"cosmetic_tag": reb["cosmetic_tag"]}
        if reb.get("leader"):
            rebels["leader"] = {"name": reb["leader"]}
        out.append({"effect": "civil_war", "tag": tag, "ideology": reb.get("ideology", "fascism"),
                    "size": float(reb.get("size", 0.3)), "rebels": rebels,
                    **({"army_ratio": float(reb["army_ratio"])} if reb.get("army_ratio") is not None else {})})
    if cat.get("rename"):
        out.append({"effect": "cosmetic_tag", "value": cat["rename"]})
    return out


def _cyclic(nodes: dict) -> bool:
    state: dict[int, int] = {}

    def visit(n: int) -> bool:
        if state.get(n) == 1:
            return True
        if state.get(n) == 2 or n not in nodes:
            return False
        state[n] = 1
        if any(visit(o["next"]) for o in nodes[n]["options"]):
            return True
        state[n] = 2
        return False
    return any(visit(n) for n in nodes)


# ---------------------------------------------------------------- espíritus

def _ideas(ctx: BuildContext, tag: str, saga: dict) -> None:
    countries = ctx.spec.raw["ideas"].setdefault("countries", {})
    entry = countries.get(tag)
    if not isinstance(entry, dict):
        entry = countries[tag] = {"starting_ideas": [], "focus_ideas": []}
    lst = entry.setdefault("focus_ideas", [])
    have = {i["id"] for i in lst if isinstance(i, dict)}
    for idea in saga.get("ideas") or []:
        if idea["id"] not in have:
            lst.append({**idea, "src": "user_request"})


# ---------------------------------------------------------------- eventos

def _requirement(ctx: BuildContext, tag: str, place) -> dict:
    """La anarquía libre y con su capital; y la región del capítulo, si es suya."""
    req: dict = {"subject": False}
    cap = (ctx.data.get("capitals") or {}).get(tag)
    conds = []
    if cap is not None:
        conds.append({"controls_state": cap})
    if place:
        sid = effects_mod.resolve_state(place)
        owner = (ctx.data.get("territory") or {}).get(sid) if sid is not None else None
        if sid is None:
            ctx.warn(f"aventura {tag}: la región {place} no existe en el juego; el capítulo no la exige")
        elif owner not in (tag, None):
            ctx.warn(f"aventura {tag}: la región {place} arranca en manos de {owner}; el capítulo no la exige")
        elif sid != cap:
            conds.append({"controls_state": sid})
    if len(conds) == 1:
        req.update(conds[0])
    elif conds:
        req["all"] = conds
    return req


def _schedule(ns: str, tag: str, target: int, days: int, cancel_delay: int) -> list[dict]:
    return [
        {"effect": "clear_flag", "value": _flag(tag, "llego")},
        {"effect": "event", "id": f"{ns}.{target}", "days": days},
        {"effect": "event", "id": f"{ns}.3", "days": days + cancel_delay},
    ]


def _events(ctx: BuildContext, tag: str, saga: dict, cfg: dict) -> list[dict]:
    ns = namespace(tag)
    pic = cfg.get("picture", "GFX_report_event_generic_rally")
    first_days = int(cfg.get("first_days", 3))
    interval = int(cfg.get("interval_days", 120))
    cancel_delay = int(cfg.get("cancel_delay_days", 2))
    skulls = _flag(tag, "calaveras")
    nodes = {n["id"]: n for n in saga["nodes"]}
    endings = {e["id"]: e for e in saga["endings"]}
    arrive = [{"effect": "flag", "value": _flag(tag, "llego"), "days": 10}]
    base_req = _requirement(ctx, tag, None)
    out: list[dict] = []

    # 1: arranque (oculto) -> a los dos meses, la presentación
    out.append({
        "id": 1, "trigger": "on_startup", "hidden": True, "picture": pic, "src": "user_request",
        "title": {"english": "Adventure clock", "spanish": "Reloj de la aventura"},
        "desc": {"english": "Hidden.", "spanish": "Oculto."},
        "options": [{"name": {"english": "Go on.", "spanish": "Seguir."},
                     "effects": [{"effect": "event", "id": f"{ns}.2", "days": int(cfg.get("start_days", 59))}]}],
    })
    # 2: la situación y los personajes
    intro = saga["intro"]
    opts = []
    for ch in saga["characters"]:
        eff = [{"effect": "set_variable", "var": skulls, "value": 0},
               {"effect": "flag", "value": _flag(tag, ch["id"])},
               {"effect": "flag", "value": _flag(tag, "en_curso")}]
        eff += list(ch.get("effects") or [])
        eff += _schedule(ns, tag, ch["first"], first_days, cancel_delay)
        opts.append({"name": ch["pick"], "effects": eff, "ai_chance": 1})
    out.append({"id": 2, "trigger": "effect", "picture": pic, "src": "user_request", "when": dict(base_req),
                "title": intro["title"], "desc": intro["desc"], "options": opts})
    # 3: el corte (si el capítulo agendado no llegó)
    cut = cfg.get("cancel") or {}
    out.append({
        "id": 3, "trigger": "effect", "picture": pic, "src": "user_request",
        "when": {"all": [{"not_flag": _flag(tag, "llego")}, {"not_flag": _flag(tag, "fin")}],
                 "flag": _flag(tag, "en_curso")},
        "title": cut.get("title") or {"english": "The Thread Is Cut", "spanish": "El Hilo se Corta"},
        "desc": cut.get("desc") or {"english": "The story ends here.", "spanish": "La historia termina acá."},
        "options": [{"name": cut.get("close") or {"english": "So it goes.", "spanish": "Así son las cosas."},
                     "effects": [{"effect": "clear_flag", "value": _flag(tag, "en_curso")},
                                 {"effect": "flag", "value": _flag(tag, "cortada")}]}],
    })
    # los capítulos
    for nid, node in nodes.items():
        opts = []
        for opt in node["options"]:
            eff = list(opt.get("effects") or []) + _catastrophe_effects(tag, opt.get("catastrophe"))
            if opt.get("skulls"):
                eff.append({"effect": "add_variable", "var": skulls, "value": int(opt["skulls"])})
            eff += _schedule(ns, tag, opt["next"], interval, cancel_delay)
            o = {"name": opt["name"], "effects": eff, "ai_chance": opt.get("ai_chance", 1)}
            if opt.get("when"):
                o["when"] = opt["when"]
            opts.append(o)
        out.append({"id": nid, "trigger": "effect", "picture": pic, "src": "user_request",
                    "when": _requirement(ctx, tag, node.get("place")), "immediate": list(arrive),
                    "title": node["title"], "desc": node["desc"], "options": opts})
    # los finales
    tally = cfg.get("skull_line") or {
        "english": "\\n\\nSkulls on the hero's tally: [?{var}|0]",
        "spanish": "\\n\\nCalaveras en la cuenta del héroe: [?{var}|0]"}
    for eid, end in endings.items():
        desc = {lang: end["desc"][lang] + tally[lang].replace("{var}", skulls) for lang in ("english", "spanish")}
        eff = list(end.get("effects") or [])
        # la catástrofe va después de cerrar la historia: si es una guerra
        # civil, las banderas ya quedaron puestas en el país que juega
        eff += [{"effect": "flag", "value": _flag(tag, "fin")},
                {"effect": "flag", "value": _flag(tag, f"fin_{end['kind']}")},
                {"effect": "clear_flag", "value": _flag(tag, "en_curso")}]
        eff += _catastrophe_effects(tag, end.get("catastrophe"))
        out.append({"id": eid, "trigger": "effect", "picture": pic, "src": "user_request",
                    "when": _requirement(ctx, tag, end.get("place")), "immediate": list(arrive),
                    "title": end["title"], "desc": desc,
                    "options": [{"name": end["close"], "effects": eff}]})
    return out
