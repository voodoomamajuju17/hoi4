"""Modelos 3D propios (2026-11-08: el Gliptodonte del EFE, hecho por el usuario en Blender).

Cada carpeta de assets/modelos/<pieza>/ trae su árbol gfx/ (gfx/models/..., gfx/entities/*.asset,
gfx/interface/equipmentdesigner/graphic_db/*.txt) tal como va en el mod: se copia igual. El
.blend y la vista previa quedan en assets/ (son para editar, el juego no los usa).
"""

from __future__ import annotations

from ..context import BuildContext
from ..pdx import banner_for

CARPETA = ("assets", "modelos")


def emit(ctx: BuildContext) -> None:
    base = ctx.spec.root.parent.joinpath(*CARPETA)
    if not base.is_dir():
        return
    piezas = []
    for pieza in sorted(p for p in base.iterdir() if p.is_dir()):
        gfx = pieza / "gfx"
        if not gfx.is_dir():
            continue
        n = 0
        for f in sorted(gfx.rglob("*")):
            if f.is_file():
                rel = f.relative_to(pieza).as_posix()
                if f.suffix in (".txt", ".asset", ".gfx"):
                    # los de texto llevan el encabezado de archivo generado, como todo el mod
                    ctx.write_text(rel, banner_for(f"assets/modelos/{pieza.name} (modelo 3D propio)")
                                   + f.read_text(encoding="utf-8-sig"))
                else:
                    ctx.copy_asset(f.relative_to(ctx.spec.root.parent).as_posix(), rel)
                n += 1
        piezas.append(f"{pieza.name} ({n} archivos)")
    if piezas:
        ctx.note(f"modelos 3D propios: {', '.join(piezas)}")
