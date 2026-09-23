"""Listas de nombres para los personajes que el juego genera solo.

Produce:
  common/names/00_meganations_names.txt

HOI4 genera generales, almirantes y asesores al azar y les pone nombre desde
common/names/. Sin lista para el TAG, error.log se llena de "Failed to
generate a name for a character" (1.19.3, todos nuestros países). Cada país
del spec dice `names_from: <TAG vanilla>` y se copia esa lista tal cual.
"""

from __future__ import annotations

from ..context import BuildContext
from ..pdx import Block, parse_file

SOURCE = "spec/02_countries.yaml -> names_from (listas copiadas de common/names/ vanilla)"


def emit(ctx: BuildContext) -> None:
    wanted = {c.tag: c.raw.get("names_from") for c in ctx.spec.countries if c.raw.get("names_from")}
    if not wanted:
        return
    if ctx.vanilla is None:
        ctx.skip("common/names", "las listas se copian del juego instalado", "Q035")
        return
    vanilla: dict[str, Block] = {}
    for path in sorted((ctx.vanilla.root / "common" / "names").glob("*.txt")):
        try:
            root = parse_file(path)
        except ValueError:
            continue
        for key, value in root.entries:
            if key and isinstance(value, Block):
                vanilla.setdefault(key, value)
    out = Block()
    missing = []
    for tag, source in wanted.items():
        block = vanilla.get(source)
        if block is None:
            missing.append(f"{tag}<-{source}")
            continue
        out.add(tag, block)
    if missing:
        ctx.warn(f"nombres: no hay lista vanilla para {', '.join(missing)}; esos paises generan sin nombre.")
    if len(out):
        ctx.write_script("common/names/00_meganations_names.txt", out, source=SOURCE)
