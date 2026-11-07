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
from pathlib import Path

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
    stubs = 0
    vd = ctx.spec.raw["scenario"].get("vanilla_decisions") or {}
    whole = set(vd.get("remove_files") or [])
    for path in sorted((ctx.vanilla.root / "common" / "decisions").glob("*.txt")):
        m = _TAG_FILE.match(path.name)
        if path.name in whole and not (m and m.group(1) in vanilla_tags):
            stub, n = _stub_decisions(path)
            ctx.write_text(f"common/decisions/{path.name}",
                           banner_for("spec/11_scenario.yaml -> vanilla_decisions")
                           + "# Vaciado a proposito: no tiene sentido en 2100 (pedido del usuario, 2026-10-24).\n"
                           + (stub if stub else ""))
            stubs += n
            silenced.append(path.name)
            continue
        if m and m.group(1) in vanilla_tags:
            stub, n = _stub_decisions(path)
            ctx.write_text(f"common/decisions/{path.name}",
                           banner_for(SOURCE) + "# Vaciado a proposito: el pais no existe en 2100.\n"
                           + (stub if stub else ""))
            stubs += n
            silenced.append(m.group(1))
    _partial_and_renames(ctx, vd, whole)
    if silenced:
        ctx.note(f"limpieza: {len(silenced)} archivos de decisiones de paises vanilla vaciados "
                 f"({', '.join(sorted(set(silenced))[:12])}{'...' if len(set(silenced)) > 12 else ''}); "
                 f"{stubs} decisiones quedan como cascaras inertes")


def _stub_decisions(path) -> tuple[str, int]:
    """Las decisiones del archivo vaciado, como cáscaras que nunca se cargan.

    Otros scripts del juego las siguen nombrando (has_active_mission,
    has_decision...) y, si no existen, error.log se llena de "Invalid decision"
    (2026-09-29). Cada una queda con allowed = no (ningún país la carga) y, si
    era una misión, con su duración, para que siga contando como misión."""
    from ..pdx import parse_file
    try:
        root = parse_file(path)
    except (ValueError, OSError):
        return "", 0
    out = Block()
    n = 0
    for cat, body in root.entries:
        if not cat or not isinstance(body, Block):
            continue
        cb = Block()
        for did, dec in body.entries:
            if not did or not isinstance(dec, Block) or str(did).startswith("@"):
                continue
            db = Block([("allowed", Block([("always", False)]))])
            if dec.get("days_mission_timeout") is not None:
                db.add("activation", Block([("always", False)]))
                db.add("days_mission_timeout", 30)
            db.add("available", Block([("always", False)]))
            cb.add(did, db)
            n += 1
        if cb.entries:
            out.add(cat, cb)
    return (render(out) if out.entries else ""), n


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
    mio_size = re.compile(r"\badd_mio_size\s*=\s*\d+(?:\.\d+)?")
    written = {p.resolve() for p in ctx.written}
    touched, monroe_files = [], []
    folders = ["common/on_actions", "common/scripted_effects"]
    # Con events/ reemplazado (replace_path) los eventos vanilla ya no cargan:
    # copiarlos acá los volvía a cargar enteros (MTG_USA, WUW_Germany...).
    if "events" not in (ctx.spec.project.get("replace_paths") or []):
        folders.append("events")
    for folder in folders:
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
            if folder == "common/on_actions":
                # OIM (2026-10-01): 09_aat_on_actions les suma tamaño al arrancar
                # según la fecha (add_mio_size = 3 y 4) y en 2100 todas arrancaban
                # con 4. El juego no deja restarlo después ("value for
                # add_mio_size is negative"): se saca acá, en el origen.
                new = mio_size.sub("", new)
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



SOURCE_EVENTS = "eventos genericos del juego que siguen haciendo falta (00_project.yaml -> keep_vanilla_events)"
_NAMESPACE = re.compile(r"^\s*add_namespace\s*=\s*([A-Za-z0-9_]+)", re.M)


def emit_kept_events(ctx: BuildContext) -> None:
    """events/ se reemplaza entero (replace_path), pero los on_actions del juego
    siguen llamando a eventos genéricos: elecciones, avisos de justificación de
    guerra, ases, bomba nuclear. Sin ellos el error.log los marca ("Malformed
    token: war_justification.1") y esos avisos no aparecen. Se copian los
    archivos del juego que solo declaran esos namespaces; de un archivo mixto
    se copian solo los eventos de esos namespaces."""
    if ctx.vanilla is None:
        return
    keep = set(ctx.spec.project.get("keep_vanilla_events") or [])
    if not keep or "events" not in (ctx.spec.project.get("replace_paths") or []):
        return
    from .. import pdx
    copied, found = [], set()
    for path in sorted((ctx.vanilla.root / "events").glob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        spaces = set(_NAMESPACE.findall(text))
        hit = spaces & keep
        if not hit:
            continue
        rel = f"events/{path.name}"
        if spaces <= keep:
            ctx.write_text(rel, banner_for(SOURCE_EVENTS) + text)
        else:
            try:
                root = pdx.parse(text)
            except Exception as exc:  # noqa: BLE001 - un archivo del juego que no parsea se avisa
                ctx.warn(f"eventos del juego: {rel} no parsea ({exc}); no se recuperan {', '.join(sorted(hit))}.")
                continue
            out = Block()
            for key, value in root.entries:
                if key == "add_namespace":
                    if pdx.text(value) in keep:
                        out.add(key, value)
                    continue
                if isinstance(value, Block) and value.get("id") is not None:
                    if pdx.text(value.get("id")).split(".")[0] in keep:
                        out.add(key, value)
            ctx.write_text(rel, banner_for(SOURCE_EVENTS) + render(out))
        found |= hit
        copied.append(path.name)
    if copied:
        ctx.note(f"eventos del juego que se conservan ({', '.join(sorted(found))}): {', '.join(copied)}")
    missing = keep - found
    if missing:
        ctx.warn(f"eventos del juego: no se encontraron los namespaces {', '.join(sorted(missing))}.")


def _partial_and_renames(ctx: BuildContext, vd: dict, whole: set) -> None:
    """Decisiones sueltas de vainilla que se vacían (el resto del archivo queda
    igual, cortado a mano para no reescribir lo que no se toca) y las que se
    quedan con nombre y descripción de 2100 (2026-10-24)."""
    folder = ctx.vanilla.root / "common" / "decisions"
    gone = 0
    for fname, ids in (vd.get("remove") or {}).items():
        path = folder / fname
        if fname in whole or not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        new, found = _blank_decisions(text, set(ids))
        missing = sorted(set(ids) - found)
        if missing:
            ctx.warn(f"limpieza: en {fname} no estan: {', '.join(missing)}")
        if found:
            ctx.write_text(f"common/decisions/{fname}",
                           banner_for("spec/11_scenario.yaml -> vanilla_decisions")
                           + f"# Copia del archivo del juego sin {len(found)} decisiones de 1936 (pedido del usuario, 2026-10-24).\n"
                           + new)
            gone += len(found)
    renamed = 0
    for key, langs in (vd.get("rename") or {}).items():
        (en_name, en_desc), (es_name, es_desc) = langs["en"], langs["es"]
        for k, en, es in ((key, en_name, es_name), (f"{key}_desc", en_desc, es_desc)):
            ctx.loc.define_and_reference(k, en=en, es=es, file="replace/meganations_decisiones_vanilla",
                                         origin="vanilla_decisions")
        renamed += 1
    if gone or renamed:
        ctx.note(f"limpieza: {gone} decisiones genericas de 1936 vaciadas; {renamed} con nombre de 2100")


def _blank_decisions(text: str, ids: set) -> tuple[str, set]:
    """Reemplaza el cuerpo de cada decisión `id = { ... }` (dentro de una
    categoría, profundidad 1) por una cáscara que nunca se carga."""
    out, found = [], set()
    i, n, depth = 0, len(text), 0
    last = 0
    while i < n:
        c = text[i]
        if c == "#":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == '"':
            j = text.find('"', i + 1)
            i = n if j < 0 else j + 1
            continue
        if c == "{":
            if depth == 1:
                # ¿qué clave abre este bloque?
                k = i - 1
                while k >= 0 and text[k] in " \t\r\n=":
                    k -= 1
                e = k + 1
                while k >= 0 and (text[k].isalnum() or text[k] == "_"):
                    k -= 1
                key = text[k + 1:e]
                if key in ids:
                    # buscar el cierre
                    d, j = 0, i
                    while j < n:
                        ch = text[j]
                        if ch == "#":
                            q = text.find("\n", j)
                            j = n if q < 0 else q
                            continue
                        if ch == '"':
                            q = text.find('"', j + 1)
                            j = n if q < 0 else q + 1
                            continue
                        if ch == "{":
                            d += 1
                        elif ch == "}":
                            d -= 1
                            if d == 0:
                                break
                        j += 1
                    out.append(text[last:i])
                    out.append("{ allowed = { always = no } available = { always = no } }")
                    last = j + 1
                    i = j + 1
                    found.add(key)
                    continue
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    out.append(text[last:])
    return "".join(out), found


# ---------------------------------------------------------------------------
# Asesores genéricos del juego base (2026-11-01)
# ---------------------------------------------------------------------------
# Pedido del usuario: "sacá todos estos ministros, están al pedo" (Gaspar
# Mitre, Manuel Flores, Ramón de Urquiza, Máximo Rojas). "Están en todas las
# naciones: todas tienen sus 4 ministros default de ideología". El juego base
# los crea en history/general/*.txt con generate_character (nombre al azar de
# la lista del país), uno por ideología. Se pisa cada archivo de esa carpeta
# que los crea con una copia sin esos bloques; lo demás queda igual.

GENERIC_SOURCE = "history/general vanilla sin los asesores políticos genéricos (pedido del usuario 2026-11-01)"


def _block_end(text: str, start: int) -> int:
    """Índice de la llave que cierra el bloque que abre text[start] == '{'."""
    d, j, n = 0, start, len(text)
    while j < n:
        ch = text[j]
        if ch == "#":
            q = text.find("\n", j)
            j = n if q < 0 else q
            continue
        if ch == '"':
            q = text.find('"', j + 1)
            j = n if q < 0 else q + 1
            continue
        if ch == "{":
            d += 1
        elif ch == "}":
            d -= 1
            if d == 0:
                return j
        j += 1
    return n - 1


def drop_generated_advisors(text: str, slot: str = "political_advisor") -> tuple[str, int]:
    """Saca cada `generate_character = { ... }` que crea un asesor de `slot`."""
    out, last, dropped = [], 0, 0
    for m in re.finditer(r"(?m)^[^#\n]*?\bgenerate_character\s*=\s*\{", text):
        start = m.end() - 1
        if start < last:
            continue
        end = _block_end(text, start)
        body = text[start:end + 1]
        if re.search(rf"\bslot\s*=\s*{slot}\b", body):
            key_at = text.rfind("generate_character", m.start(), start)
            out.append(text[last:key_at])
            out.append("# (asesor genérico quitado por el mod)")
            last = end + 1
            dropped += 1
    out.append(text[last:])
    return "".join(out), dropped


def emit_generic_advisors(ctx: BuildContext) -> None:
    if ctx.vanilla is None:
        ctx.skip("history/general", "los asesores genéricos se sacan leyendo el juego instalado")
        return
    folder = ctx.vanilla.root / "history" / "general"
    total, files = 0, []
    for path in sorted(folder.glob("*.txt")) if folder.exists() else []:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        new, n = drop_generated_advisors(text)
        if n:
            ctx.write_text(f"history/general/{path.name}", banner_for(GENERIC_SOURCE) + new)
            total += n
            files.append(path.name)
    if files:
        ctx.note(f"asesores genéricos: {total} quitados de history/general ({', '.join(files)})")
    else:
        ctx.note("asesores genéricos: history/general no crea asesores políticos (nada que sacar)")


# ---------------------------------------------------------------------------
# 2026-11-07 (auditoría estática: "replace_path = events, pero archivos heredados siguen
# invocando eventos no presentes"): las copias de scripts del juego que escribe el mod
# (on_actions sin espíritus vanilla, decisiones genéricas recortadas, eventos genéricos que
# se conservan) todavía llaman a eventos de 1936 que con events/ reemplazado no existen.
# Al final del armado: en on_actions, efectos y eventos se borra la llamada; una decisión
# que depende de un evento que no existe queda como cáscara (nunca se carga).

_LLAMADA = re.compile(r"\b(country_event|news_event|state_event|unit_leader_event|operative_leader_event)"
                      r"\s*=\s*(\{|[A-Za-z0-9_]+\.[0-9]+)")
_ID_EVENTO = re.compile(r"(?m)^\s*id\s*=\s*([A-Za-z0-9_]+\.[0-9]+)")
_PESO_EVENTO = re.compile(r"(?<![A-Za-z0-9_.])([0-9]+(?:\.[0-9]+)?)\s*=\s*([A-Za-z][A-Za-z0-9_]*\.[0-9]+)\b")


def _cierre(text: str, i: int) -> int:
    """Índice del '}' que cierra el '{' en i (respeta comentarios y comillas)."""
    d, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "#":
            q = text.find("\n", i)
            i = n if q < 0 else q
            continue
        if c == '"':
            q = text.find('"', i + 1)
            i = n if q < 0 else q + 1
            continue
        if c == "{":
            d += 1
        elif c == "}":
            d -= 1
            if d == 0:
                return i
        i += 1
    return n - 1


def _sin_comentarios(text: str) -> str:
    """El texto con los comentarios en blanco (mismo largo, mismas posiciones)."""
    return re.sub(r"#[^\n]*", lambda m: " " * len(m.group(0)), text)


def llamadas_rotas(text: str, existen: set[str]) -> list[tuple[int, int, str]]:
    """(inicio, fin, id) de cada llamada a un evento que no está en `existen`."""
    limpio = _sin_comentarios(text)
    out = []
    for m in _LLAMADA.finditer(limpio):
        if m.group(2) == "{":
            a = m.start(2)
            b = _cierre(limpio, a)
            ident = _ID_EVENTO.search(limpio[a:b + 1].replace("{", "\n"))
            if ident and ident.group(1) not in existen:
                out.append((m.start(), b + 1, ident.group(1)))
        elif m.group(2) not in existen:
            out.append((m.start(), m.end(), m.group(2)))
    return out


def quitar_llamadas(text: str, existen: set[str]) -> tuple[str, list[str]]:
    """Borra las llamadas rotas y las entradas `peso = evento` rotas de random_events."""
    rotas = llamadas_rotas(text, existen)
    ids = [r[2] for r in rotas]
    for a, b, _ in sorted(rotas, reverse=True):
        text = text[:a] + text[b:]
    limpio = _sin_comentarios(text)
    for m in reversed(list(_PESO_EVENTO.finditer(limpio))):
        if m.group(2) not in existen and "random_events" in limpio[max(0, m.start() - 400):m.start()]:
            ids.append(m.group(2))
            text = text[:m.start()] + text[m.end():]
    return text, ids


def _decisiones_con_rotas(text: str, existen: set[str]) -> set[str]:
    """Los ids de las decisiones (profundidad 2: categoría > decisión) que llaman eventos rotos."""
    limpio = _sin_comentarios(text)
    rotas = [a for a, _b, _i in llamadas_rotas(text, existen)]
    if not rotas:
        return set()
    out, pila = set(), []
    clave = re.compile(r"([A-Za-z0-9_@.]+)\s*=\s*$")
    for i, c in enumerate(limpio):
        if c == "{":
            m = clave.search(limpio[max(0, i - 120):i])
            pila.append((m.group(1) if m else "", i))
        elif c == "}" and pila:
            k, a = pila.pop()
            if len(pila) == 1 and any(a < r < i for r in rotas):
                out.add(k)
    return out


def emit_event_refs(ctx: BuildContext) -> None:
    """Saca de los scripts que escribe el mod las llamadas a eventos que no existen."""
    if "events" not in (ctx.spec.project.get("replace_paths") or []):
        return
    existen: set[str] = set()
    for p in sorted((ctx.mod_root / "events").glob("*.txt")):
        existen |= set(_ID_EVENTO.findall(_sin_comentarios(p.read_text(encoding="utf-8-sig", errors="replace"))))
    carpetas = ("common/on_actions", "common/scripted_effects", "common/decisions", "events")
    tocados, quitadas, apagadas = [], 0, []
    for p in sorted({w for w in ctx.written}):
        p = p if hasattr(p, "relative_to") else None
        if p is None or p.suffix != ".txt" or not p.exists():
            continue
        try:
            rel = p.relative_to(ctx.mod_root).as_posix()
        except ValueError:
            continue
        if not rel.startswith(carpetas):
            continue
        text = p.read_text(encoding="utf-8-sig", errors="replace")
        if rel.startswith("common/decisions"):
            ids = _decisiones_con_rotas(text, existen)
            if not ids:
                continue
            nuevo, encontradas = _blank_decisions(text, ids)
            apagadas += sorted(encontradas)
        else:
            nuevo, rotas = quitar_llamadas(text, existen)
            if not rotas:
                continue
            quitadas += len(rotas)
        p.write_text(nuevo, encoding="utf-8")
        tocados.append(rel)
    # 2026-11-07 (error.log del usuario: "Malformed token: usa.6" en 00_on_actions.txt): los
    # on_actions del juego que el mod no copia también llaman a eventos que ya no cargan. Si
    # tienen alguna, va una copia limpia con el mismo nombre (pisa a la del juego).
    if ctx.vanilla is not None:
        propios = {Path(t).name.lower() for t in tocados} | {
            p.name.lower() for p in (ctx.mod_root / "common" / "on_actions").glob("*.txt")}
        for src in sorted((ctx.vanilla.root / "common" / "on_actions").glob("*.txt")):
            if src.name.lower() in propios:
                continue
            try:
                text = src.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            nuevo, rotas = quitar_llamadas(text, existen)
            if not rotas:
                continue
            rel = f"common/on_actions/{src.name}"
            ctx.write_text(rel, banner_for(f"copia de {rel} del juego sin las llamadas a eventos que el mod no carga")
                           + nuevo)
            tocados.append(rel)
            quitadas += len(rotas)
    ctx.data["eventos_rotos"] = {"archivos": tocados, "llamadas": quitadas, "decisiones": apagadas}
    if tocados:
        ctx.note(f"limpieza: {quitadas} llamadas a eventos del juego que el mod no carga (events/ reemplazado), "
                 f"sacadas de {len(tocados)} archivos"
                 + (f"; {len(apagadas)} decisiones que dependían de ellas quedan como cáscara "
                    f"({', '.join(apagadas[:8])}{'...' if len(apagadas) > 8 else ''})" if apagadas else ""))
