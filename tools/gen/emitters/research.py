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
            for path in sorted((root / rel).glob("*.txt")):
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                new, n = pattern.subn(lambda m: f"{m.group(1)}{int(m.group(2)) + offset}", text)
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
