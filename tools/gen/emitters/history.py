"""history/countries/ — el estado de cada país el día uno.

Produce:
  history/countries/<TAG> - <Nombre>.txt

Contenido: slots de investigación, partido gobernante y popularidades,
ideas iniciales (05_ideas.yaml -> starting_ideas) y líder (recruit_character).

Capital: tiene que ser un state propio, así que sale del reparto que resolvió
el emisor de territorio (08_territory.yaml -> capital_state). Sin capital en el
spec se usa el state propio con más manpower (capital_fallback, invento
declarado). Un país sin states no lleva capital: existe como TAG pero no
aparece en el mapa.

Sujeciones (04_diplomacy.yaml): van en la historia del OVERLORD con
set_autonomy, una sola vez por par.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted
from . import characters as characters_mod
from . import ideas as ideas_mod

SOURCE = "spec/02_countries.yaml + 03_leaders.yaml + 05_ideas.yaml"

GROUPS = ("democratic", "communism", "fascism", "neutrality")


def emit(ctx: BuildContext) -> None:
    defaults = ctx.spec.raw["countries"].get("default_politics") or {}
    for c in ctx.spec.countries:
        politics = {**defaults, **(c.raw.get("politics") or {})}
        b = Block()
        capital = _capital(ctx, c)
        if capital is not None:
            b.add("capital", capital)
        oob = (ctx.data.get("oob") or {}).get(c.tag)
        if oob:
            b.add("oob", Quoted(oob))
        naval = (ctx.data.get("naval_oob") or {}).get(c.tag)
        if naval:
            b.add("set_naval_oob", Quoted(naval))
        air = (ctx.data.get("air_oob") or {}).get(c.tag)
        if air:
            b.add("set_air_oob", Quoted(air))
        b.add("set_research_slots", int(politics.get("research_slots", 3)))

        sp = Block()
        sp.add("ruling_party", c.ideology_group)
        sp.add("last_election", Quoted(str(politics.get("last_election", "2096.1.1"))))
        sp.add("election_frequency", int(politics.get("election_frequency", 48)))
        sp.add("elections_allowed", bool(politics.get("elections_allowed", False)))
        b.add("set_politics", sp)
        b.add("set_popularities", _popularities(c.ideology_group, int(politics.get("ruling_popularity", 70))))

        starting = list(ideas_mod.starting_idea_ids(ctx, c.tag))
        law = _conscription_law(ctx, c.tag)
        if law:
            starting.append(law)
        if starting:
            ideas = Block()
            for iid in starting:
                ideas.add(None, iid)
            b.add("add_ideas", ideas)

        # Contadores nacionales (06_mechanics.yaml -> variable), ej. BioSteel.
        for mech in ctx.spec.raw["mechanics"].get("mechanics", []) or []:
            variables = [mech["variable"]] if isinstance(mech.get("variable"), dict) else []
            variables += [v for v in mech.get("variables") or [] if isinstance(v, dict)]
            for var in variables:
                if var.get("country", mech.get("country")) != c.tag:
                    continue
                sv = Block()
                sv.add("var", var["name"])
                sv.add("value", var["start"])
                b.add("set_variable", sv)

        techs = (ctx.data.get("techs") or {}).get(c.tag)
        if techs:
            tb = Block()
            for tech in techs:
                tb.add(tech, 1)
            tb.add("popup", False)
            b.add("set_technology", tb)

        for item, amount in (ctx.data.get("stockpile") or {}).get(c.tag, []):
            eq = Block()
            eq.add("type", item)
            eq.add("amount", amount)
            eq.add("producer", c.tag)
            b.add("add_equipment_to_stockpile", eq)

        # Todos se reclutan acá (el juego avisa si recruit_character se usa
        # fuera de la historia). Los de `recruit_at_start: false` (líderes de
        # una revolución) van al final, y después se confirma al líder de
        # arranque con promote_character: un foco los asciende más tarde.
        chars = characters_mod.characters_of(ctx, c.tag)
        late = [ch for ch in chars if not ch.get("recruit_at_start", True)]
        for ch in [ch for ch in chars if ch.get("recruit_at_start", True)] + late:
            b.add("recruit_character", ch["id"])
        if late:
            first = next((ch for ch in chars if ch.get("recruit_at_start", True)
                          and isinstance((ch.get("roles") or {}).get("country_leader"), dict)), None)
            if first:
                b.add("promote_character", first["id"])

        for fb in _faction_blocks(ctx, c.tag):
            b.entries.append(fb)

        for entry in (ctx.data.get("diplomacy_history") or {}).get(c.tag, []):
            b.entries.append(entry)

        for rel in subjects_of(ctx, c.tag):
            sa = Block()
            sa.add("target", rel["subject"])
            sa.add("autonomy_state", rel["autonomy_level"])
            b.add("set_autonomy", sa)

        # HOI4 asocia el archivo al país por el prefijo "<TAG> - "; el resto del
        # nombre es libre. Sin apóstrofes para no complicar rutas en scripts.
        name = c.name_en.replace("'", "")
        ctx.write_script(f"history/countries/{c.tag} - {name}.txt", b, source=SOURCE)

    if "territory" not in ctx.data:
        ctx.skip(
            "history/countries -> capital",
            "la capital tiene que ser un state propio y el reparto territorial no esta generado",
            "Q035",
        )
    used = {"set_autonomy": "04_diplomacy.yaml"} if _any_subjects(ctx) else {}
    if ctx.data.get("naval_oob"):
        used["set_naval_oob"] = "forces.py"
    if ctx.data.get("air_oob"):
        used["set_air_oob"] = "forces.py"
    if faction_plan(ctx):
        used["create_faction"] = "04_diplomacy.yaml"
        used["add_to_faction"] = "04_diplomacy.yaml"
    if ctx.data.get("techs"):
        used["set_technology"] = "13_military.yaml"
    if any(isinstance(m.get("variable"), dict) or m.get("variables")
           for m in ctx.spec.raw["mechanics"].get("mechanics", []) or []):
        used["set_variable"] = "06_mechanics.yaml"
    if any(ctx.data.get("stockpile", {}).values()):
        used["add_equipment_to_stockpile"] = "13_military.yaml"
    ctx.verify_keys("effects", used)


def subjects_of(ctx: BuildContext, overlord: str) -> list[dict]:
    """Sujeciones con nivel de autonomía definido, validado contra el juego."""
    out = []
    known = ctx.vanilla.autonomy_ids() if ctx.vanilla else set()
    for rel in ctx.spec.raw["diplomacy"].get("subject_relations", []) or []:
        if rel.get("overlord") != overlord:
            continue
        level = rel.get("autonomy_level")
        if level in (None, "unknown"):
            ctx.skip(f"sujecion {overlord} -> {rel.get('subject')}", "falta el nivel de autonomia", "Q019")
            continue
        territory = ctx.data.get("territory")
        if territory is not None and rel["subject"] not in territory.values():
            ctx.warn(f"{rel['subject']} no tiene territorio: no se lo somete a {overlord}.")
            continue
        if known and level not in known:
            raise SpecError(
                f"autonomy_level '{level}' no existe en common/autonomous_states/ del juego",
                hint=f"existentes: {', '.join(sorted(known))}",
                where="04_diplomacy.yaml",
            )
        out.append(rel)
    return out


def faction_plan(ctx: BuildContext) -> list[tuple[dict, str, list[str]]]:
    """(facción, líder, miembros con territorio) de 04_diplomacy.yaml."""
    territory = ctx.data.get("territory") or {}
    counts: dict[str, int] = {}
    for tag in territory.values():
        counts[tag] = counts.get(tag, 0) + 1
    out = []
    for f in ctx.spec.raw["diplomacy"].get("factions", []) or []:
        if not isinstance(f, dict):
            continue
        members = [m for m in f["members"] if counts.get(m)]
        if not members:
            continue
        leader = max(members, key=lambda m: (counts[m], m)) if f.get("leader") == "largest" else f["leader"]
        out.append((f, leader, members))
    return out


def _faction_blocks(ctx: BuildContext, tag: str) -> list[tuple[str, object]]:
    """create_faction + add_to_faction, en la historia del líder."""
    out: list[tuple[str, object]] = []
    for f, leader, members in faction_plan(ctx):
        if leader != tag:
            continue
        key = ctx.loc.define_and_reference(
            f["id"], en=f["name"]["english"], es=f["name"]["spanish"],
            file="meganations_diplomacy", origin=f"factions:{f['id']}",
        )
        out.append(("create_faction", key))
        for m in members:
            if m != leader:
                out.append(("add_to_faction", m))
    return out


def _any_subjects(ctx: BuildContext) -> bool:
    return any(
        r.get("autonomy_level") not in (None, "unknown")
        for r in ctx.spec.raw["diplomacy"].get("subject_relations", []) or []
    )


_idea_cache: dict[int, set[str]] = {}


def _conscription_law(ctx: BuildContext, tag: str) -> str | None:
    """Ley de reclutamiento de arranque (15_balance.yaml), verificada contra
    las ideas vanilla: una que no existe se saltea con aviso."""
    laws = ((ctx.spec.raw.get("balance") or {}).get("conscription") or {}).get("laws") or {}
    law = laws.get(tag)
    if not law or ctx.vanilla is None:
        return None
    known = _idea_cache.setdefault(id(ctx), ctx.vanilla.idea_names())
    if known and law not in known:
        ctx.warn(f"reclutamiento: la ley '{law}' no existe en common/ideas/; {tag} arranca con la de defecto.")
        return None
    return law


def _capital(ctx: BuildContext, c) -> int | None:
    return (ctx.data.get("capitals") or {}).get(c.tag)


def _popularities(ruling: str, share: int) -> Block:
    """El grupo gobernante se lleva `share`; el resto se reparte y suma 100."""
    others = [g for g in GROUPS if g != ruling]
    rest = 100 - share
    base, extra = divmod(rest, len(others))
    b = Block()
    for g in GROUPS:
        if g == ruling:
            b.add(g, share)
        else:
            b.add(g, base + (1 if extra > 0 else 0))
            extra -= 1 if extra > 0 else 0
    return b
