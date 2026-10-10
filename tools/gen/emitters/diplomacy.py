"""Diplomacia de arranque (spec/04_diplomacy.yaml): mundo vivo.

Produce:
  common/opinion_modifiers/meganations_opinion_modifiers.txt
y deja en ctx.data["diplomacy_history"][TAG] entradas que la historia del país
agrega tal cual:
  add_opinion_modifier   rivalidades (en los dos sentidos)
  declare_war_on         guerras activas al arranque
  add_named_threat       tensión mundial inicial (en el país por defecto)

Los reclamos sobre la Anarquía los calcula territory.py (necesita el mapa).
Tipos de wargoal verificados contra common/wargoals; efectos contra
documentation/. Un país sin territorio no entra en guerras ni rivalidades.
"""

from __future__ import annotations

from collections import defaultdict

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Compare

SOURCE = "spec/04_diplomacy.yaml"
LOC_FILE = "meganations_diplomacy"


def emit(ctx: BuildContext) -> None:
    spec = ctx.spec.raw["diplomacy"]
    territory = ctx.data.get("territory") or {}
    alive = set(territory.values())
    out: dict[str, list] = defaultdict(list)
    effects: dict[str, str] = {}

    mods = spec.get("opinion_modifiers") or []
    if mods:
        body = Block()
        for m in mods:
            mb = Block()
            mb.add("value", int(m["value"]))
            body.add(ctx.loc.reference(m["id"], f"diplomacy:{m['id']}"), mb)
            ctx.loc.define(m["id"], en=m["name"]["english"], es=m["name"]["spanish"],
                           file=LOC_FILE, origin=f"diplomacy:{m['id']}")
        root = Block()
        root.add("opinion_modifiers", body)
        ctx.write_script("common/opinion_modifiers/meganations_opinion_modifiers.txt", root, source=SOURCE)
    known_mods = {m["id"] for m in mods}

    for r in spec.get("rivalries", []) or []:
        a, b = r["between"]
        if r["modifier"] not in known_mods:
            raise SpecError(f"rivalidad {a}-{b}: modificador '{r['modifier']}' no definido", where=SOURCE)
        if a not in alive or b not in alive:
            continue
        for x, y in ((a, b), (b, a)):
            om = Block()
            om.add("target", y)
            om.add("modifier", r["modifier"])
            out[x].append(("add_opinion_modifier", om))
        effects["add_opinion_modifier"] = SOURCE

    wargoals = ctx.vanilla.wargoal_types() if ctx.vanilla else set()
    for w in spec.get("wars_at_start", []) or []:
        if not isinstance(w, dict):
            continue
        att, dfd = w["attacker"], w["defender"]
        if att not in alive or dfd not in alive:
            ctx.warn(f"guerra {att} -> {dfd}: alguno no tiene territorio; no se declara.")
            continue
        if wargoals and w["wargoal"] not in wargoals:
            raise SpecError(f"wargoal '{w['wargoal']}' no existe en common/wargoals/", where=SOURCE)
        dw = Block()
        dw.add("target", dfd)
        dw.add("type", w["wargoal"])
        out[att].append(("declare_war_on", dw))
        effects["declare_war_on"] = SOURCE
        ctx.note(f"guerra al arranque: {att} contra {dfd}")

    # Justificaciones de guerra ya hechas: el país arranca con el objetivo de
    # guerra listo y decide él cuándo declarar.
    for w in spec.get("wargoals_at_start", []) or []:
        if not isinstance(w, dict):
            continue
        holder, target = w["holder"], w["target"]
        if holder not in alive or target not in alive:
            ctx.warn(f"justificacion {holder} -> {target}: alguno no tiene territorio; no se crea.")
            continue
        if wargoals and w["wargoal"] not in wargoals:
            raise SpecError(f"wargoal '{w['wargoal']}' no existe en common/wargoals/", where=SOURCE)
        cw = Block()
        cw.add("type", w["wargoal"])
        cw.add("target", target)
        out[holder].append(("create_wargoal", cw))
        effects["create_wargoal"] = SOURCE
        ctx.note(f"justificacion al arranque: {holder} contra {target}")

    _anarchy_hostility(ctx, spec, alive, out, effects, wargoals, known_mods)

    tension = spec.get("world_tension")
    if isinstance(tension, dict) and tension.get("threat"):
        host = ctx.spec.raw["scenario"]["bookmark"]["default_country"]
        key = ctx.loc.define_and_reference(
            "MEGANATIONS_THREAT_COLLAPSE", en=tension["name"]["english"], es=tension["name"]["spanish"],
            file=LOC_FILE, origin="diplomacy:world_tension",
        )
        nt = Block()
        nt.add("threat", int(tension["threat"]))
        nt.add("name", key)
        out[host].append(("add_named_threat", nt))
        effects["add_named_threat"] = SOURCE

    ctx.data["diplomacy_history"] = dict(out)
    ctx.verify_keys("effects", effects)


HOSTILITY_EFFECT = "MEGANATIONS_renovar_casus_belli"
ANNEX_EFFECT = "MEGANATIONS_anexar_anarquias_titere"
CAPTURE_EFFECT = "MEGANATIONS_capitales_tomadas"
CAPTURE_TARGET = "meganations_capital_caida"


def anarchy_pairs(ctx: BuildContext) -> list[tuple[str, str]]:
    """(meganación, anarquía) que se tocan en el mapa: sale de los reclamos
    (territory.py) — un state de la Anarquía reclamado por una meganación es
    frontera entre las dos. Las excluidas (04_diplomacy -> anarchy_hostility.exclude) no cuentan."""
    spec = (ctx.spec.raw["diplomacy"].get("anarchy_hostility") or {})
    if not spec:
        return []
    exclude = set(spec.get("exclude") or [])
    territory = ctx.data.get("territory") or {}
    pairs = set()
    for sid, who in (ctx.data.get("claims") or {}).items():
        owner = territory.get(sid)
        if owner is None or owner in exclude:
            continue
        for mega in who:
            pairs.add((mega, owner))
    return sorted(pairs)


def _annex_anarchy_puppets(ctx: BuildContext, hs: dict, effects: dict) -> Block | None:
    """Una anarquía que quedó como títere de un país de la IA pasa a ser
    suya del todo (annex_country). La conferencia de paz de la IA elegía
    títere demasiado seguido (pedido del usuario, 2026-10-08). Corre en el
    pulso mensual; el jugador decide solo; `keep_flag` en la anarquía la salva."""
    ap = hs.get("annex_puppets") or {}
    if not ap:
        return None
    tags = {c.tag for c in ctx.spec.countries}
    anarchies = list(ap.get("tags") or [])
    for a in anarchies:
        if a not in tags:
            raise SpecError(f"anarchy_hostility.annex_puppets: '{a}' no es un pais del mod", where=SOURCE)
    keep = ap.get("keep_flag")
    overlords = [c.tag for c in ctx.spec.countries if c.tag not in anarchies]
    body = Block()
    for a in anarchies:
        cond = Block([("exists", True), ("is_subject", True)])
        if keep:
            cond.add("NOT", Block([("has_country_flag", keep)]))
        inner = Block([("limit", Block([(a, cond)]))])
        for i, o in enumerate(overlords):
            inner.add("if" if i == 0 else "else_if", Block([
                ("limit", Block([(a, Block([("is_subject_of", o)])), (o, Block([("is_ai", True)]))])),
                (o, Block([("annex_country", Block([("target", a), ("transfer_troops", True)]))]))]))
        body.add("if", inner)
    effects["annex_country"] = SOURCE
    ctx.verify_keys("triggers", {"exists": SOURCE, "is_subject": SOURCE, "is_subject_of": SOURCE,
                                 "has_country_flag": SOURCE, "is_ai": SOURCE})
    ctx.note(f"anarquias titere de la IA se anexan: {', '.join(anarchies)} ({len(overlords)} posibles senores)")
    return body


def _capital_capture(ctx: BuildContext, anarchies: list[str], effects: dict) -> Block | None:
    """Botín de capital (2026-10-10): cuando una meganación controla la
    capital de arranque de una meganación o anarquía con la que está en
    guerra, le salta su evento (20_unique_units -> capital_spoils.event), una
    vez por cada enemigo. Se mira la capital de ARRANQUE: el juego muda la
    capital apenas cae, así que la actual nunca está ocupada. El enemigo queda
    guardado como event target (meganations_capital_caida) para el texto."""
    spoils = ctx.data.get("capital_spoils") or {}
    capitals = ctx.data.get("capitals") or {}
    if not spoils:
        return None
    majors = [c.tag for c in ctx.spec.countries if c.is_major]
    targets = [t for t in majors + anarchies if t in capitals]
    body = Block()
    for tag, event in sorted(spoils.items()):
        checks = Block([("limit", Block([("tag", tag)]))])
        for t in targets:
            if t == tag:
                continue
            flag = f"MEGANATIONS_capital_{t}"
            checks.add("if", Block([
                ("limit", Block([("has_war_with", t), ("controls_state", capitals[t]),
                                 ("NOT", Block([("has_country_flag", flag)]))])),
                ("set_country_flag", flag),
                (t, Block([("save_event_target_as", CAPTURE_TARGET)])),
                ("country_event", Block([("id", event), ("days", 1)]))]))
        body.add("if", checks)
    for k in ("set_country_flag", "save_event_target_as", "country_event"):
        effects[k] = SOURCE
    ctx.verify_keys("triggers", {"has_war_with": SOURCE, "controls_state": SOURCE, "has_country_flag": SOURCE,
                                 "tag": SOURCE})
    ctx.note(f"botin de capital: {len(spoils)} meganaciones; capitales enemigas vigiladas: {', '.join(targets)}")
    return body


def _anarchy_hostility(ctx, spec, alive, out, effects, wargoals, known_mods) -> None:
    """Todos arrancan en paz, pero cada meganación que toca una anarquía tiene
    un casus belli contra ella que no vence (se renueva cada mes si se perdió)
    y se odian (opinión en los dos sentidos). Pedido del usuario, 2026-09-28."""
    hs = spec.get("anarchy_hostility") or {}
    if not hs:
        return
    kind = hs.get("wargoal", "annex_everything")
    if wargoals and kind not in wargoals:
        raise SpecError(f"anarchy_hostility: wargoal '{kind}' no existe en common/wargoals/", where=SOURCE)
    mod = hs.get("opinion")
    if mod and mod not in known_mods:
        raise SpecError(f"anarchy_hostility: modificador '{mod}' no definido", where=SOURCE)
    pairs = [(m, a) for m, a in anarchy_pairs(ctx) if m in alive and a in alive]
    # Fecha desde la que la IA puede ir a la guerra (16_ai.yaml -> anarchy_wars.declare_after).
    # Con el casus belli desde el día uno la IA declaraba sola en 2100 aunque su plan
    # esperara (2026-09-29: "Panáfrica le declara la guerra demasiado rápido a los
    # Emiratos"). El jugador lo tiene desde el primer pulso; la IA, desde su fecha.
    after = ((ctx.spec.raw.get("ai") or {}).get("anarchy_wars") or {}).get("declare_after") or {}
    renew = Block()
    for mega, anar in pairs:
        cw = Block([("type", kind), ("target", anar)])
        if not after.get(mega):
            out[mega].append(("create_wargoal", cw))
        if mod:
            out[mega].append(("add_opinion_modifier", Block([("target", anar), ("modifier", mod)])))
            out[anar].append(("add_opinion_modifier", Block([("target", mega), ("modifier", mod)])))
        cond = Block([("tag", mega),
                      (anar, Block([("exists", True), ("NOT", Block([("has_country_flag", f"{anar}_intocable")]))])),
                      ("NOT", Block([("has_war_with", anar)])),
                      ("NOT", Block([("has_wargoal_against", anar)]))])
        if after.get(mega):
            y, m, d = (int(x) for x in str(after[mega]).split(".")[:3])
            cond.add("OR", Block([("is_ai", False), ("date", Compare(">", f"{y}.{m}.{d}"))]))
        renew.add("if", Block([("limit", cond), ("create_wargoal", Block([("type", kind), ("target", anar)]))]))
    annex = _annex_anarchy_puppets(ctx, hs, effects)
    if annex is not None:
        renew.add(ANNEX_EFFECT, True)
    capture = _capital_capture(ctx, list((hs.get("annex_puppets") or {}).get("tags") or []), effects)
    if capture is not None:
        renew.add(CAPTURE_EFFECT, True)
    # el archivo se escribe siempre: los pulsos de 14_decisions lo llaman
    # el que se llama va primero: el juego lee los scripted_effects en orden
    script = Block([(ANNEX_EFFECT, annex)] if annex is not None else [])
    if capture is not None:
        script.add(CAPTURE_EFFECT, capture)
    script.add(HOSTILITY_EFFECT, renew)
    ctx.write_script("common/scripted_effects/meganations_casus_belli.txt", script,
                     source=SOURCE + " -> anarchy_hostility")
    if not pairs:
        return
    effects["create_wargoal"] = SOURCE
    if mod:
        effects["add_opinion_modifier"] = SOURCE
    ctx.verify_keys("triggers", {"has_wargoal_against": SOURCE, "exists": SOURCE, "has_war_with": SOURCE,
                                 "has_country_flag": SOURCE, "tag": SOURCE, "is_ai": SOURCE, "date": SOURCE})
    ctx.data["anarchy_pairs"] = pairs
    ctx.note("casus belli permanentes contra la Anarquia: " + ", ".join(f"{m}->{a}" for m, a in pairs))
