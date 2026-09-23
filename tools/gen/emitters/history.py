"""history/countries/ — el estado de cada país el día uno.

Produce:
  history/countries/<TAG> - <Nombre>.txt

Contenido: slots de investigación, partido gobernante y popularidades,
ideas iniciales (05_ideas.yaml -> starting_ideas) y líder (recruit_character).

Lo que NO se emite todavía: `capital`. Una capital tiene que ser un state que
el país posee, y el reparto territorial está bloqueado por Q007. Sin states el
país existe como TAG pero no aparece en el mapa; eso es lo esperado hasta que
se genere history/states/.
"""

from __future__ import annotations

from ..context import BuildContext
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

        # HOI4 asocia el archivo al país por el prefijo "<TAG> - "; el resto del
        # nombre es libre. Sin apóstrofes para no complicar rutas en scripts.
        name = c.name_en.replace("'", "")
        ctx.write_script(f"history/countries/{c.tag} - {name}.txt", b, source=SOURCE)

    ctx.skip(
        "history/countries -> capital",
        "la capital tiene que ser un state propio y el reparto territorial no esta generado",
        "Q007",
    )


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
