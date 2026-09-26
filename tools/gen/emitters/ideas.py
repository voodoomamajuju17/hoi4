"""Ideas nacionales (national spirits).

Produce:
  common/ideas/<TAG>_ideas.txt
  localisation de <id> y <id>_desc (TN007)

Tres orígenes en 05_ideas.yaml, todos van al mismo archivo:
  starting_ideas   — las pone history/countries el día uno
  focus_ideas      — las da un foco (granted_by)
  biosteel_tiers   — los tiers del Bioacero, intercambiados por focos

Todas llevan `allowed = { always = no }`: ninguna se elige desde el panel de
política, solo entran por historia o por efecto. Las no removibles llevan
`removal_cost = -1`.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted

SOURCE = "spec/05_ideas.yaml"
LOC_FILE = "meganations_ideas"


def ideas_of(ctx: BuildContext, tag: str) -> list[dict]:
    """Todas las ideas definidas para un país, en orden estable."""
    entry = (ctx.spec.raw["ideas"].get("countries") or {}).get(tag)
    if not isinstance(entry, dict):
        return []
    out: list[dict] = []
    for group in ("starting_ideas", "focus_ideas"):
        value = entry.get(group)
        if isinstance(value, list):
            out.extend(value)
    tiers = entry.get("biosteel_tiers")
    if isinstance(tiers, dict):
        out.extend(tiers.get("tiers", []) or [])
    return out


def starting_idea_ids(ctx: BuildContext, tag: str) -> list[str]:
    entry = (ctx.spec.raw["ideas"].get("countries") or {}).get(tag)
    if not isinstance(entry, dict) or not isinstance(entry.get("starting_ideas"), list):
        return []
    return [i["id"] for i in entry["starting_ideas"]]


def all_idea_ids(ctx: BuildContext) -> set[str]:
    return {i["id"] for c in ctx.spec.countries for i in ideas_of(ctx, c.tag)}


# Si no hay dibujo propio, un ícono genérico del juego según el modificador
# que más pesa en la idea (así no sale "?"). Se busca por palabra clave entre
# los sprites GFX_idea_* del juego instalado.
_KEYWORDS = [
    (("industrial_capacity", "production_speed"), ("production", "industr", "factory")),
    (("research_speed",), ("research", "science", "scien")),
    (("political_power",), ("political", "propaganda")),
    (("stability",), ("stability", "unity", "national_unity")),
    (("war_support",), ("war_support", "propaganda", "militar")),
    (("army_", "experience_gain_army"), ("army", "infantry", "militar")),
    (("trade_opinion", "consumer_goods"), ("trade", "econom")),
    (("local_resources",), ("resource", "mining", "econom")),
    (("monthly_population",), ("manpower", "population")),
    (("dockyard", "navy", "naval"), ("naval", "navy")),
]


def _generic_picture(modifiers: dict, idea_sprites: list[str]) -> str | None:
    if not idea_sprites:
        return None
    key = max(modifiers, key=lambda k: abs(float(modifiers[k]))).lstrip("?")
    for prefixes, words in _KEYWORDS:
        if any(key.startswith(p) or p in key for p in prefixes):
            for word in words:
                hits = [n for n in idea_sprites if word in n.lower()]
                generic = [n for n in hits if "generic" in n.lower()]
                if generic or hits:
                    return (generic or hits)[0][len("GFX_idea_"):]
    return None


def emit(ctx: BuildContext) -> None:
    modifiers_used: dict[str, str] = {}
    seen: set[str] = set()
    gfx = ctx.vanilla.gfx_names() if ctx.vanilla else None
    idea_sprites = sorted(n for n in (gfx or ()) if n.startswith("GFX_idea_"))
    repo = ctx.spec.root.parent
    sprites = Block()
    pictures = {"propia": 0, "generica": 0, "ninguna": 0}

    for country in ctx.spec.countries:
        ideas = ideas_of(ctx, country.tag)
        if not ideas:
            continue

        group = Block()
        for idea in ideas:
            iid = idea["id"]
            if iid in seen:
                raise SpecError(f"idea duplicada: {iid}", where="05_ideas.yaml")
            seen.add(iid)
            if not iid.startswith(f"{country.tag}_"):
                raise SpecError(
                    f"la idea '{iid}' de {country.tag} no empieza con '{country.tag}_'",
                    where="05_ideas.yaml",
                )

            modifiers = idea.get("modifiers")
            if not isinstance(modifiers, dict) or not modifiers:
                raise SpecError(
                    f"{iid}: sin modificadores. HOI4 no acepta una idea vacia.",
                    where="05_ideas.yaml",
                )

            body = Block()
            allowed = Block()
            allowed.add("always", False)
            body.add("allowed", allowed)
            if idea.get("removable") is False:
                body.add("removal_cost", -1)
            mod = Block()
            for key, value in modifiers.items():
                if key.startswith("?"):
                    # modificador opcional: si el juego no lo documenta, se saltea con aviso
                    key = key[1:]
                    if ctx.vanilla is not None and ctx.vanilla.documented_keys("modifiers") is not None \
                            and not ctx.vanilla.is_documented("modifiers", key):
                        ctx.warn(f"{iid}: el modificador '{key}' no existe en este juego; se omite.")
                        continue
                    mod.add(key, float(value))
                    continue
                mod.add(key, float(value))
                modifiers_used.setdefault(key, iid)
            body.add("modifier", mod)
            # Dibujo: propio si está en assets/<TAG>/ideas/<id>.dds; si no, genérico del juego.
            own = repo / "assets" / country.tag / "ideas" / f"{iid}.dds"
            if own.exists():
                texture = f"gfx/interface/ideas/meganations/{iid}.dds"
                ctx.copy_asset(f"assets/{country.tag}/ideas/{iid}.dds", texture)
                sprite = Block()
                sprite.add("name", Quoted(f"GFX_idea_{iid}"))
                sprite.add("texturefile", Quoted(texture))
                sprites.add("spriteType", sprite)
                body.entries.insert(0, ("picture", iid))
                pictures["propia"] += 1
            else:
                generic = _generic_picture(modifiers, idea_sprites)
                if generic:
                    body.entries.insert(0, ("picture", generic))
                    pictures["generica"] += 1
                else:
                    pictures["ninguna"] += 1
            group.add(ctx.loc.reference(iid, f"ideas:{iid}"), body)

            desc = idea.get("desc")
            if not isinstance(desc, dict):
                raise SpecError(f"{iid}: falta desc en EN y ES (TN007)", where="05_ideas.yaml")
            ctx.loc.define(iid, en=idea["name"]["english"], es=idea["name"]["spanish"],
                           file=LOC_FILE, origin=f"ideas:{iid}")
            ctx.loc.define_and_reference(
                f"{iid}_desc", en=desc["english"], es=desc["spanish"],
                file=LOC_FILE, origin=f"ideas:{iid}",
            )

        root = Block()
        country_block = Block()
        country_block.add("country", group)
        root.add("ideas", country_block)
        ctx.write_script(f"common/ideas/{country.tag}_ideas.txt", root, source=SOURCE)

    if sprites.entries:
        root = Block()
        root.add("spriteTypes", sprites)
        ctx.write_script("interface/meganations_ideas.gfx", root, source=SOURCE)
    ctx.note(f"ideas: dibujo propio {pictures['propia']}, icono generico del juego {pictures['generica']}, "
             f"sin dibujo {pictures['ninguna']}")
    ctx.verify_keys("modifiers", modifiers_used)
