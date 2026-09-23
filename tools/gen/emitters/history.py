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
from . import territory as territory_mod

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
        b.add("set_research_slots", int(politics.get("research_slots", 3)))

        sp = Block()
        sp.add("ruling_party", c.ideology_group)
        sp.add("last_election", Quoted(str(politics.get("last_election", "2096.1.1"))))
        sp.add("election_frequency", int(politics.get("election_frequency", 48)))
        sp.add("elections_allowed", bool(politics.get("elections_allowed", False)))
        b.add("set_politics", sp)
        b.add("set_popularities", _popularities(c.ideology_group, int(politics.get("ruling_popularity", 70))))

        starting = ideas_mod.starting_idea_ids(ctx, c.tag)
        if starting:
            ideas = Block()
            for iid in starting:
                ideas.add(None, iid)
            b.add("add_ideas", ideas)

        for leader in characters_mod.leaders_of(ctx, c.tag):
            b.add("recruit_character", leader["id"])

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
    ctx.verify_keys("effects", {"set_autonomy": "04_diplomacy.yaml"} if _any_subjects(ctx) else {})


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


def _any_subjects(ctx: BuildContext) -> bool:
    return any(
        r.get("autonomy_level") not in (None, "unknown")
        for r in ctx.spec.raw["diplomacy"].get("subject_relations", []) or []
    )


def _capital(ctx: BuildContext, c) -> int | None:
    assignment: dict[int, str] = ctx.data.get("territory") or {}
    owned = [sid for sid, tag in assignment.items() if tag == c.tag]
    if not owned:
        return None
    names = ctx.data.get("state_names") or {}
    by_id = {s.id: s for s in ctx.vanilla.states()} if ctx.vanilla else {}
    terr = (ctx.spec.raw["territory"].get("territories") or {}).get(c.tag) or {}
    wanted = terr.get("capital_state")
    if wanted:
        options = {territory_mod.normalize(w) for w in wanted}
        for sid in sorted(owned):
            shown = names.get(by_id[sid].name_key, "") if sid in by_id else ""
            if territory_mod.normalize(shown) in options:
                return sid
        ctx.warn(f"{c.tag}: la capital {' / '.join(wanted)} no esta entre sus states; uso la de mas manpower.")
    best = max(owned, key=lambda sid: (by_id[sid].manpower if sid in by_id else 0, -sid))
    if not wanted:
        shown = names.get(by_id[best].name_key, "?") if best in by_id else "?"
        ctx.note(f"{c.tag}: capital provisoria {shown} ({best}), la de mas manpower. Ver Q012.")
    return best


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
