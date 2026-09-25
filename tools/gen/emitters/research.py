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
    # Los equipos tienen además un nombre corto (_short) en la ventana de producción.
    shorts = ctx.vanilla.localisation("english", {f"{k}_short" for k in (spec.get("equipment") or {}) if k in equipment})
    for key in sorted(shorts):
        base = key[:-len("_short")]
        names = spec["equipment"][base]
        ctx.loc.define_and_reference(key, en=names["en"], es=names["es"],
                                     file="replace/meganations_research", origin=f"research:{key}")
    unnamed = sum(1 for t, info in tree.items() if t not in (spec.get("techs") or {}) and info["eligible"])
    ctx.note(f"investigacion: {done['tecnologias']} tecnologias y {done['equipo']} equipos renombrados; "
             f"{unnamed} tecnologias conservan el nombre vanilla")
    if missing:
        shown = sorted(missing)
        ctx.note(f"investigacion: {len(shown)} ids que este juego no tiene (se ignoran): {', '.join(shown[:40])}"
                 + (" ..." if len(shown) > 40 else ""))
