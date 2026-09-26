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
    if offset:
        renamed = set(techs) | set(equip) | {f"{k}_short" for k in list(techs) + list(equip)}
        keys = {k for k in list(tree) + list(equipment) if k not in renamed}
        keys |= {f"{k}_short" for k in keys}
        keys -= renamed
        en_txt = ctx.vanilla.localisation("english", keys)
        es_txt = ctx.vanilla.localisation("spanish", keys)
        year = re.compile(r"\b(19[0-5]\d)\b")
        shifted_names = 0
        for key in sorted(set(en_txt) | set(es_txt)):
            en, es = en_txt.get(key) or es_txt.get(key), es_txt.get(key) or en_txt.get(key)
            if not (year.search(en) or year.search(es)):
                continue
            bump = lambda t: year.sub(lambda m: str(int(m.group(1)) + offset), t)  # noqa: E731
            ctx.loc.define_and_reference(key, en=bump(en), es=bump(es),
                                         file="replace/meganations_research", origin=f"research:year:{key}")
            shifted_names += 1
        ctx.note(f"investigacion: {shifted_names} nombres del juego con año escrito corridos a 2100+")
    unnamed = sum(1 for t, info in tree.items() if t not in (spec.get("techs") or {}) and info["eligible"])
    ctx.note(f"investigacion: {done['tecnologias']} tecnologias y {done['equipo']} equipos renombrados; "
             f"{unnamed} tecnologias conservan el nombre vanilla")
    if missing:
        shown = sorted(missing)
        ctx.note(f"investigacion: {len(shown)} ids que este juego no tiene (se ignoran): {', '.join(shown[:40])}"
                 + (" ..." if len(shown) > 40 else ""))


def _ai_weights(ctx: BuildContext) -> dict[str, list[tuple[str, float]]]:
    """Qué tecnologías prioriza la IA de cada meganación (16_ai.yaml ->
    military): las que siguen en su especialidad y lo naval básico.
    El juego no tiene una estrategia de IA para investigar (el reporte del
    2026-09-27 descartó `research_tech`), así que se suma un modificador al
    ai_will_do de cada tecnología: factor = 1 + valor/20, solo para ese país."""
    mil = (ctx.spec.raw.get("ai") or {}).get("military") or {}
    out: dict[str, list[tuple[str, float]]] = {}
    value = mil.get("research_value")
    if value:
        for tag, techs in (ctx.data.get("specialty_next") or {}).items():
            for t in techs:
                out.setdefault(t, []).append((tag, 1 + float(value) / 20))
    naval = mil.get("naval_research") or {}
    majors = [c.tag for c in ctx.spec.countries if c.is_major]
    for tag in majors:
        v = (naval.get("by_country") or {}).get(tag, naval.get("value"))
        if v:
            for t in naval.get("techs") or []:
                out.setdefault(t, []).append((tag, 1 + float(v) / 20))
    return out


def _block_end(text: str, start: int) -> int:
    """Índice de la llave que cierra el bloque cuya llave abre en `start`."""
    depth = 0
    i = start
    while i < len(text):
        c = text[i]
        if c == "#":
            nl = text.find("\n", i)
            i = len(text) if nl == -1 else nl
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _inject_weights(text: str, weights: dict[str, list[tuple[str, float]]]) -> tuple[str, int]:
    count = 0
    for tech, pairs in weights.items():
        m = re.search(rf"(?m)^[ \t]*{re.escape(tech)}\s*=\s*\{{", text)
        if not m:
            continue
        open_at = m.end() - 1
        end = _block_end(text, open_at)
        if end == -1:
            continue
        mods = "".join(f"\n\t\t\tmodifier = {{ factor = {f:g} original_tag = {tag} }}  # 2100 Meganations" for tag, f in pairs)
        body = text[open_at:end]
        a = re.search(r"\bai_will_do\s*=\s*\{", body)
        if a:
            at = open_at + a.end()
            text = text[:at] + mods + text[at:]
        else:
            text = text[:open_at + 1] + f"\n\t\tai_will_do = {{ factor = 1{mods}\n\t\t}}" + text[open_at + 1:]
        count += 1
    return text, count
