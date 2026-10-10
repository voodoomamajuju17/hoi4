"""La investigación de 2100 (spec/17_research.yaml).

1. Años: se reescriben los archivos de tecnologías y de equipo del juego
   instalado sumando `year_offset` a start_year / year (1936 -> 2100), y los
   años escritos como texto fijo en la pantalla de investigación. Se parte
   siempre del archivo vanilla de TU versión: el resto del contenido queda
   idéntico. En 2100 las tecnologías de "1936" dejaban de tener la penalidad
   por adelantarse; con los años corridos vuelve el ritmo del juego base.
2. Nombres: pisan el nombre de cada tecnología y equipo listado
   (localisation/<idioma>/replace/). Lo que el juego no tiene se ignora.
"""

from __future__ import annotations

import re

from ..context import BuildContext
from ..pdx import banner_for
from . import unique_units as unique_units_mod

SOURCE = "spec/17_research.yaml"
_START = re.compile(r"(\bstart_year\s*=\s*)(1[89]\d\d)\b")
_YEAR = re.compile(r"(\byear\s*=\s*)(1[89]\d\d)\b")
_GUI_YEAR = re.compile(r'(text\s*=\s*")(19[0-9]\d)(")')


def emit(ctx: BuildContext) -> None:
    spec = ctx.spec.raw.get("research_look") or {}
    if not spec:
        return
    if ctx.vanilla is None:
        ctx.skip("investigacion de 2100", "hay que leer el arbol del juego instalado", "Q035")
        return
    offset = int(spec.get("year_offset", 0) or 0)
    root = ctx.vanilla.root
    shifted = {"tecnologias": 0, "equipo": 0, "interfaz": 0}
    if offset:
        for rel, pattern, kind in (("common/technologies", _START, "tecnologias"),
                                   ("common/units/equipment", _YEAR, "equipo")):
            weights = _ai_weights(ctx) if kind == "tecnologias" else {}
            for path in sorted((root / rel).glob("*.txt")):
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                new, n = pattern.subn(lambda m: f"{m.group(1)}{int(m.group(2)) + offset}", text)
                if weights:
                    new, w = _inject_weights(new, weights)
                    shifted["ia"] = shifted.get("ia", 0) + w
                    n += w
                if kind == "tecnologias" and ctx.data.get("tech_locks"):
                    # unidades únicas (20_unique_units.yaml): solo un país las investiga
                    new, locked = unique_units_mod.lock_techs(new, ctx.data["tech_locks"],
                                                                ctx.data.get("tech_locks_visible") or set())
                    n += locked
                if n:
                    ctx.write_text(f"{rel}/{path.name}", banner_for(SOURCE + f" (+ {rel}/{path.name} vanilla)") + new)
                    shifted[kind] += n
        # Años escritos en la pantalla de investigación (solo interfaces de tecnología).
        for path in sorted((root / "interface").glob("**/*.gui")):
            if "tech" not in path.name.lower():
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            new, n = _GUI_YEAR.subn(lambda m: f"{m.group(1)}{int(m.group(2)) + offset}{m.group(3)}", text)
            if n:
                ctx.write_text(path.relative_to(root).as_posix(), banner_for(SOURCE) + new)
                shifted["interfaz"] += n
        if shifted.get("ia"):
            ctx.note(f"investigacion: la IA prioriza {shifted['ia']} tecnologias (su especialidad y lo naval)")
        ctx.note(f"investigacion: años +{offset} en {shifted['tecnologias']} tecnologias, "
                 f"{shifted['equipo']} equipos y {shifted['interfaz']} textos de la pantalla de investigacion")

    tree = ctx.vanilla.tech_tree()
    equipment = ctx.vanilla.equipment()
    missing = []
    done = {"tecnologias": 0, "equipo": 0}
    for kind, table, known in (("tecnologias", spec.get("techs") or {}, tree),
                               ("equipo", spec.get("equipment") or {}, equipment)):
        for key, names in table.items():
            if key not in known:
                missing.append(key)
                continue
            ctx.loc.define_and_reference(key, en=names["en"], es=names["es"],
                                         file="replace/meganations_research", origin=f"research:{key}")
            done[kind] += 1
    # Nombres cortos (_short): la ventana de producción y las casillas del
    # árbol usan éstos ("1934 ligero"). Si la entrada trae short_en/short_es se
    # usan; si no, el nombre completo.
    techs = spec.get("techs") or {}
    equip = spec.get("equipment") or {}
    wanted = {f"{k}_short" for k in equip if k in equipment} | {f"{k}_short" for k in techs if k in tree}
    shorts = ctx.vanilla.localisation("english", wanted)
    for key in sorted(shorts):
        base = key[:-len("_short")]
        names = techs.get(base) or equip.get(base)
        ctx.loc.define_and_reference(key, en=names.get("short_en", names["en"]), es=names.get("short_es", names["es"]),
                                     file="replace/meganations_research", origin=f"research:{key}")
    # Lo que no tiene nombre de 2100 pero lleva un año escrito ("Casco de
    # crucero (1936)", "1934 ligero"): se corre el año igual que en los archivos.
    # Y los términos de module_terms (2026-10-09): "Batería ligera básica" ->
    # "Batería de riel ligera básica", como el módulo en el diseñador.
    terms = _module_terms(spec)
    year = re.compile(r"\b(19[0-5]\d)\b")

    def bump(t: str) -> str:
        return year.sub(lambda m: str(int(m.group(1)) + offset), t) if offset else t

    if offset or terms:
        renamed = set(techs) | set(equip) | {f"{k}_short" for k in list(techs) + list(equip)}
        keys = {k for k in list(tree) + list(equipment) if k not in renamed}
        keys |= {f"{k}_short" for k in keys}
        keys -= renamed
        en_txt = ctx.vanilla.localisation("english", keys)
        es_txt = ctx.vanilla.localisation("spanish", keys)
        shifted_names = 0
        for key in sorted(set(en_txt) | set(es_txt)):
            en, es = en_txt.get(key) or es_txt.get(key), es_txt.get(key) or en_txt.get(key)
            new_en, new_es = bump(_terms(en, terms, "english")), bump(_terms(es, terms, "spanish"))
            if (new_en, new_es) == (en, es):
                continue
            ctx.loc.define_and_reference(key, en=new_en, es=new_es,
                                         file="replace/meganations_research", origin=f"research:year:{key}")
            shifted_names += 1
        ctx.note(f"investigacion: {shifted_names} nombres del juego sin nombre propio actualizados "
                 "(año escrito corrido a 2100+ o terminos de module_terms)")
    _modules(ctx, spec, terms)
    _special_projects(ctx, spec, terms)
    unnamed = sum(1 for t, info in tree.items() if t not in (spec.get("techs") or {}) and info["eligible"])
    ctx.note(f"investigacion: {done['tecnologias']} tecnologias y {done['equipo']} equipos renombrados; "
             f"{unnamed} tecnologias conservan el nombre vanilla")
    if missing:
        shown = sorted(missing)
        ctx.note(f"investigacion: {len(shown)} ids que este juego no tiene (se ignoran): {', '.join(shown[:40])}"
                 + (" ..." if len(shown) > 40 else ""))


def _module_terms(spec: dict) -> dict[str, list]:
    """module_terms (17_research.yaml) compilados por idioma, como vanilla_terms."""
    out = {}
    for lang, pairs in (spec.get("module_terms") or {}).items():
        out[lang] = [(re.compile(rf"(?<![\w$]){re.escape(str(a))}(?!\w)", re.IGNORECASE), str(b))
                     for a, b in pairs or []]
    return out


def _terms(text: str, terms: dict, lang: str) -> str:
    """Aplica los términos fuera de $...$, [...] y £...£. Mayúsculas: si el
    original va en mayúscula de título ("Heavy Machine Guns") el reemplazo
    también ("Pulse Guns"); si solo empieza en mayúscula, solo la primera."""
    rules = terms.get(lang)
    if not rules or not text:
        return text
    from .vanilla_terms import _PROTECTED

    words = re.findall(r"[^\W\d_]+", text)
    # mayúsculas de título solo en inglés (en español "Cañón ligero I" no lo es)
    title = lang == "english" and len(words) > 1 and sum(w[:1].isupper() for w in words) / len(words) >= 0.6

    def case(src: str, new: str, at_start: bool) -> str:
        if title and src[:1].isupper():
            return re.sub(r"(^|[\s-])(\w)", lambda m: m.group(1) + m.group(2).upper(), new)
        # mayúscula inicial solo al principio del nombre ("Motores Walter" ->
        # "Motores de pila de combustible", no "Motores De pila...")
        if src[:1].isupper() and at_start:
            return new[:1].upper() + new[1:]
        return new

    parts = _PROTECTED.split(text)
    for i, part in enumerate(parts):
        if i % 2:
            continue
        for rx, repl in rules:
            part = rx.sub(lambda m: case(m.group(0), repl, not m.string[:m.start()].strip(" 0-9x")), part)
        parts[i] = part
    return "".join(parts)


def _modules(ctx: BuildContext, spec: dict, terms: dict) -> None:
    """Módulos de los diseñadores de tanques, barcos y aviones (2026-10-09):
    el nombre de 2100 de `modules` o, si no hay, el del juego con module_terms.
    El juego no tiene nombres de módulo por país: valen para todos."""
    modules = ctx.vanilla.equipment_modules()
    if not modules:
        return
    own = spec.get("modules") or {}
    en_txt = ctx.vanilla.localisation("english", set(modules))
    es_txt = ctx.vanilla.localisation("spanish", set(modules))
    done, same = 0, []
    for key in sorted(modules):
        if key in own:
            en, es = own[key]["en"], own[key]["es"]
        else:
            old_en, old_es = en_txt.get(key) or es_txt.get(key), es_txt.get(key) or en_txt.get(key)
            if not old_en:
                continue
            en, es = _terms(old_en, terms, "english"), _terms(old_es, terms, "spanish")
            if (en, es) == (old_en, old_es):
                same.append(key)
                continue
        ctx.loc.define_and_reference(key, en=en, es=es, file="replace/meganations_research",
                                     origin=f"research:module:{key}")
        done += 1
    ctx.note(f"modulos de los disenadores: {done} de {len(modules)} con nombre de 2100"
             + (f"; sin cambio ({len(same)}): {', '.join(same[:30])}{' ...' if len(same) > 30 else ''}"
                if same else ""))


def _special_projects(ctx: BuildContext, spec: dict, terms: dict) -> None:
    """Proyectos especiales de investigación (2026-10-10, "cambiar los nombres a
    los proyectos de investigación especiales"): el nombre de 2100 de
    `special_projects` o, si no hay, el del juego con module_terms (reactor
    nuclear -> de fusión, helicópteros -> tiltrotores...). Lo que ya tiene
    nombre propio del mod no se toca."""
    projects = ctx.vanilla.special_projects()
    if not projects:
        return
    own = spec.get("special_projects") or {}
    taken = set(getattr(ctx.loc, "_defined", {}))
    en_txt = ctx.vanilla.localisation("english", set(projects))
    es_txt = ctx.vanilla.localisation("spanish", set(projects))
    done, same = 0, []
    for key in projects:
        if key in taken:
            continue
        if key in own:
            en, es = own[key]["en"], own[key]["es"]
        else:
            old_en, old_es = en_txt.get(key) or es_txt.get(key), es_txt.get(key) or en_txt.get(key)
            if not old_en:
                continue
            en, es = _terms(old_en, terms, "english"), _terms(old_es, terms, "spanish")
            if (en, es) == (old_en, old_es):
                same.append(f"{key} ({old_es})")
                continue
        ctx.loc.define_and_reference(key, en=en, es=es, file="replace/meganations_research",
                                     origin=f"research:special_project:{key}")
        taken.add(key)
        done += 1
    ctx.note(f"proyectos especiales: {done} de {len(projects)} con nombre de 2100"
             + (f"; sin cambio ({len(same)}): {', '.join(same[:40])}{' ...' if len(same) > 40 else ''}"
                if same else ""))


def _ai_weights(ctx: BuildContext) -> dict[str, list[tuple[str, float]]]:
    """Qué tecnologías prioriza la IA de cada meganación (16_ai.yaml ->
    military): las que siguen en su especialidad y lo naval básico.
    Se suma un modificador al ai_will_do de cada tecnología: factor = 1 +
    valor/20, solo para ese país (el reporte del 2026-09-27 descartó
    `research_tech`, que el juego no conoce). Las navales y los blindados
    además llevan `research_weight_factor` en la estrategia de IA (ai.py)."""
    mil = (ctx.spec.raw.get("ai") or {}).get("military") or {}
    out: dict[str, list[tuple[str, float]]] = {}
    value = mil.get("research_value")
    if value:
        for tag, techs in (ctx.data.get("specialty_next") or {}).items():
            for t in techs:
                out.setdefault(t, []).append((tag, 1 + float(value) / 20))
    majors = [c.tag for c in ctx.spec.countries if c.is_major]
    # lo naval (2026-09-27) y los blindados (2026-09-30), por país
    for key in ("naval_research", "armor_research"):
        block = mil.get(key) or {}
        for tag in majors:
            v = (block.get("by_country") or {}).get(tag, block.get("value"))
            if v:
                for t in block.get("techs") or []:
                    out.setdefault(t, []).append((tag, 1 + float(v) / 20))
    return out


def _skip(text: str, i: int, hi: int) -> int | None:
    """Si en `i` empieza un comentario o un texto entre comillas, dónde sigue."""
    if text[i] == "#":
        nl = text.find("\n", i)
        return hi if nl == -1 else nl
    if text[i] == '"':
        q = text.find('"', i + 1)
        return hi if q == -1 else q + 1
    return None


def _block_end(text: str, start: int) -> int:
    """Índice de la llave que cierra el bloque cuya llave abre en `start`."""
    depth = 0
    i = start
    while i < len(text):
        nxt = _skip(text, i, len(text))
        if nxt is not None:
            i = nxt
            continue
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


_KEY = re.compile(r"([A-Za-z0-9_@.:\-]+)\s*=\s*\{")


def _children(text: str, lo: int, hi: int) -> list[tuple[str, int, int]]:
    """Los bloques `clave = { ... }` que cuelgan directo de text[lo:hi]:
    (clave, llave que abre, llave que cierra). Lo anidado no cuenta."""
    out = []
    i = lo
    while i < hi:
        nxt = _skip(text, i, hi)
        if nxt is not None:
            i = nxt
            continue
        if text[i] == "{":
            end = _block_end(text, i)
            i = hi if end == -1 else end + 1
            continue
        m = _KEY.match(text, i)
        if m and m.end() <= hi and (i == 0 or not (text[i - 1].isalnum() or text[i - 1] in "_@.:-")):
            open_at = m.end() - 1
            end = _block_end(text, open_at)
            if end == -1:
                break
            out.append((m.group(1), open_at, end))
            i = end + 1
            continue
        i += 1
    return out


def _inject_weights(text: str, weights: dict[str, list[tuple[str, float]]]) -> tuple[str, int]:
    # Solo las tecnologías de verdad: hijas directas de `technologies = { }`, y
    # su propio ai_will_do (error.log 2026-09-29: "Unexpected token: ai_will_do"
    # en electronic_mechanical_engineering.txt; buscar la clave en cualquier
    # renglón podía caer en otro bloque con el mismo nombre).
    places = []
    for key, open_at, end in _children(text, 0, len(text)):
        if key == "technologies":
            places += [(o, e, tech) for tech, o, e in _children(text, open_at + 1, end) if tech in weights]
    for open_at, end, tech in sorted(places, reverse=True):   # de atrás para adelante: los índices no se corren
        # 2026-09-30 ("la HSN no investiga barcos"): el peso va AL FINAL del
        # ai_will_do. Al principio, un `factor = 0` o un `base =` del juego que
        # venga después lo anulaba (16 x 0 = 0). Además del factor, un `add`
        # del mismo tamaño: aunque el juego la haya dejado en cero, la
        # tecnología conserva un peso propio para esa potencia.
        mods = "".join(f"\n\t\t\tmodifier = {{ factor = {f:g} original_tag = {tag} }}  # 2100 Meganations"
                       f"\n\t\t\tmodifier = {{ add = {f:g} original_tag = {tag} }}  # 2100 Meganations"
                       for tag, f in weights[tech])
        own = next(((o, e) for k, o, e in _children(text, open_at + 1, end) if k == "ai_will_do"), None)
        if own is not None:
            # El salto antes de la llave importa: con `ai_will_do = { factor = 1 }`
            # en un solo renglón, la llave queda en su propio renglón.
            close = own[1]
            text = text[:close] + mods + "\n\t\t" + text[close:]
        else:
            text = text[:open_at + 1] + f"\n\t\tai_will_do = {{ factor = 1{mods}\n\t\t}}" + text[open_at + 1:]
    return text, len(places)
