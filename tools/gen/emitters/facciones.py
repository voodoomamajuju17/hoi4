"""Emblemas de las ocho facciones de las meganaciones (2026-11-15, llegaron los 8 medallones).

assets/ui/facciones/faccion_<TAG>.dds (100 x 100, dos cuadros, como los del juego) y
faccion_<TAG>_mini.dds (32 x 32, la barra de arriba) -> sprites GFX_faction_logo_mn_<TAG> y
GFX_faction_logo_mn_<TAG>_miniature (el mismo esquema de nombres que interface/factions/factions.gfx).

PENDIENTE: que cada facción los use. En esta versión del juego el emblema lo elige la plantilla de
la facción (common/factions); falta ver esa carpeta del juego instalado para escribir las plantillas
sin adivinar. Mientras tanto los sprites existen y no cambian nada.
"""

from __future__ import annotations

from ..context import BuildContext

ARTE = "assets/ui/facciones"
TEX = "gfx/interface/factions/faction_logos/meganations"
TAGS = ("EFE", "FCU", "ASC", "HSN", "NAS", "SHD", "APF", "NRE")


def emit(ctx: BuildContext) -> None:
    base = ctx.spec.root.parent / ARTE
    hay = [t for t in TAGS if (base / f"faccion_{t}.dds").exists() and (base / f"faccion_{t}_mini.dds").exists()]
    if not hay:
        return
    g = ["# Generado por tools/gen/emitters/facciones.py: emblemas de facción de las meganaciones\nspriteTypes = {\n"]
    for t in hay:
        for suf, nombre, cuadros in (("", f"GFX_faction_logo_mn_{t}", 2), ("_mini", f"GFX_faction_logo_mn_{t}_miniature", 1)):
            ctx.copy_asset(f"{ARTE}/faccion_{t}{suf}.dds", f"{TEX}/faccion_{t}{suf}.dds")
            g.append(f'\tspriteType = {{\n\t\tname = "{nombre}"\n\t\ttexturefile = "{TEX}/faccion_{t}{suf}.dds"\n'
                     + (f"\t\tnoOfFrames = {cuadros}\n" if cuadros > 1 else "") + "\t}\n")
    g.append("}\n")
    ctx.write_text("interface/meganations_facciones.gfx", "".join(g))
    ctx.note(f"facciones: {len(hay)} emblemas listos (falta engancharlos a las plantillas de facción)")
