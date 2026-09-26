"""Limpieza de contenido vanilla que ya no tiene a quién aplicarse.

En 2100 ningún país vanilla tiene territorio. Sus decisiones nacionales
(common/decisions/<TAG>*.txt: China, Congo...) se siguen evaluando todo el
tiempo y llenan error.log (miles de líneas por partida: "invalid event
target", "is not a valid Idea", guerras de frontera sin eventos) además de
costar rendimiento.

Se pisa cada archivo de decisiones cuyo nombre empieza con el TAG de un país
vanilla con un archivo vacío del mismo nombre. Las decisiones genéricas (sin
TAG en el nombre) y las categorías quedan intactas: otras decisiones las usan.
"""

from __future__ import annotations

import re

from ..context import BuildContext
from ..pdx import Block, banner_for, render

SOURCE = "decisiones nacionales vanilla de paises que en 2100 no existen"

_TAG_FILE = re.compile(r"^([A-Z][A-Z0-9]{2})(?:[ _.\-]|$)")


def emit(ctx: BuildContext) -> None:
    if ctx.vanilla is None:
        return
    ours = {c.tag for c in ctx.spec.countries}
    vanilla_tags = (ctx.vanilla.country_tags() | set(ctx.vanilla.country_history_files())) - ours
    silenced = []
    for path in sorted((ctx.vanilla.root / "common" / "decisions").glob("*.txt")):
        m = _TAG_FILE.match(path.name)
        if m and m.group(1) in vanilla_tags:
            ctx.write_text(f"common/decisions/{path.name}",
                           banner_for(SOURCE) + "# Vaciado a proposito: el pais no existe en 2100.\n")
            silenced.append(m.group(1))
    if silenced:
        ctx.note(f"limpieza: {len(silenced)} archivos de decisiones de paises vanilla vaciados "
                 f"({', '.join(sorted(set(silenced))[:12])}{'...' if len(set(silenced)) > 12 else ''})")


def emit_spirits(ctx: BuildContext) -> None:
    """Espíritus vanilla que los scripts genéricos del juego reparten por
    región o continente (ej. la "Doctrina Monroe" a todo país americano):
    un evento oculto se los saca a los países del mod al día 1 y cada mes."""
    if ctx.vanilla is None:
        return
    ours = sorted(c.tag for c in ctx.spec.countries)
    spirits = sorted(ctx.vanilla.country_spirits() & ctx.vanilla.ideas_given_by_scripts())
    if not spirits:
        return
    _neutralize_scripts(ctx, spirits)
    eff = Block()
    for idea in spirits:
        b = Block()
        b.add("limit", Block([("has_idea", idea)]))
        b.add("remove_ideas", idea)
        eff.add("if", b)
    root = Block()
    root.add("MEGANATIONS_quitar_espiritus_vanilla", eff)
    ctx.write_script("common/scripted_effects/meganations_limpieza.txt", root, source=SOURCE_SPIRITS)

    ev = Block()
    ev.add("id", "meganations_limpieza.1")
    ev.add("hidden", True)
    ev.add("is_triggered_only", True)
    imm = Block()
    imm.add("MEGANATIONS_quitar_espiritus_vanilla", True)
    again = Block()
    again.add("id", "meganations_limpieza.1")
    again.add("days", 7)
    imm.add("country_event", again)
    ev.add("immediate", imm)
    events = Block()
    events.add("add_namespace", "meganations_limpieza")
    events.add("country_event", ev)
    ctx.write_script("events/meganations_limpieza.txt", events, source=SOURCE_SPIRITS)

    who = Block()
    who.add("limit", Block([("OR", Block([("tag", t) for t in ours]))]))
    first = Block()
    first.add("id", "meganations_limpieza.1")
    first.add("days", 1)
    who.add("country_event", first)
    effect = Block()
    effect.add("every_country", who)
    startup = Block()
    startup.add("effect", effect)
    on = Block()
    on.add("on_startup", startup)
    root = Block()
    root.add("on_actions", on)
    ctx.write_script("common/on_actions/02_meganations_limpieza.txt", root, source=SOURCE_SPIRITS)
    ctx.note(f"limpieza: {len(spirits)} espiritus vanilla que el juego reparte por region se sacan al dia 1 "
             f"({', '.join(s for s in spirits if 'monroe' in s.lower()) or 'ninguno con monroe en el nombre'})")
    ctx.verify_keys("effects", {"remove_ideas": SOURCE_SPIRITS, "every_country": SOURCE_SPIRITS,
                                "country_event": SOURCE_SPIRITS})
    ctx.verify_keys("triggers", {"has_idea": SOURCE_SPIRITS, "tag": SOURCE_SPIRITS})


SOURCE_SPIRITS = "espiritus vanilla que el juego reparte por region o continente"


def _neutralize_scripts(ctx: BuildContext, spirits: list[str]) -> None:
    """Sacar el espíritu una vez por semana no alcanza si un script del juego
    lo vuelve a dar (el usuario siguió viendo la Doctrina Monroe). Acá se
    copian los scripts genéricos del juego (on_actions, scripted_effects) sin
    los add_ideas / add_timed_idea de esos espíritus, con el mismo nombre de
    archivo para que pisen al original. En events/ solo se tocan los que dan
    la Doctrina Monroe (los demás eventos son de países que en 2100 no existen)."""
    names = "|".join(re.escape(s) for s in spirits)
    single = re.compile(rf"\badd_ideas\s*=\s*(?:{names})\b")
    timed = re.compile(rf"\badd_timed_idea\s*=\s*\{{[^{{}}]*?\bidea\s*=\s*(?:{names})\b[^{{}}]*\}}")
    group = re.compile(r"\badd_ideas\s*=\s*\{([^{}]*)\}")
    token = re.compile(rf"(?<![A-Za-z0-9_.])(?:{names})(?![A-Za-z0-9_.])")
    written = {p.resolve() for p in ctx.written}
    touched, monroe_files = [], []
    for folder in ("common/on_actions", "common/scripted_effects", "events"):
        for path in sorted((ctx.vanilla.root / folder).glob("*.txt")):
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            if folder == "events" and "monroe" not in text.lower():
                continue
            new = single.sub("", text)
            new = timed.sub("", new)
            new = group.sub(lambda m: "add_ideas = {" + token.sub("", m.group(1)) + "}", new)
            if new == text:
                continue
            rel = f"{folder}/{path.name}"
            if (ctx.mod_root / rel).resolve() in written:
                continue
            if "monroe" in text.lower():
                monroe_files.append(rel)
            ctx.write_text(rel, banner_for(f"copia de {rel} del juego sin los espiritus de paises que en 2100 no existen") + new)
            touched.append(rel)
    if touched:
        ctx.note(f"limpieza: {len(touched)} scripts del juego ya no reparten espiritus vanilla"
                 + (f" (la Doctrina Monroe salia de: {', '.join(monroe_files)})" if monroe_files else ""))

