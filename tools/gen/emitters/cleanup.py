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
from ..pdx import banner_for

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
