"""Modelos 3D propios (2026-11-08: el Gliptodonte del EFE, hecho por el usuario en Blender).

Cada carpeta de assets/modelos/<pieza>/ trae su árbol gfx/ (gfx/models/..., gfx/entities/*.asset,
gfx/interface/equipmentdesigner/graphic_db/*.txt) tal como va en el mod: se copia igual. El
.blend y la vista previa quedan en assets/ (son para editar, el juego no los usa).
"""

from __future__ import annotations

import re

from ..context import BuildContext
from ..pdx import Block, banner_for

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
        ctx.note(f"modelos 3D propios: {len(piezas)} piezas")
    respaldo(ctx)


# ---------------------------------------------------------------------------
# 2026-11-11: modelos de respaldo. Cada país usa su modelo propio; si no tiene, el de su
# meganación (los satélites) o, si tampoco, el juego COMÚN (assets/modelos/COMUN_*). Se escriben
# entidades con el nombre que busca el juego (<TAG>_<sprite>_entity) y, para tanques, aviones y
# barcos, la lista del diseñador (peso alto, archivo al final: gana a las copiadas del juego).
# ---------------------------------------------------------------------------

# sprite del juego -> nombres de entidad propios que lo cubren (en orden)
SPRITES = {
    "infantry": ["infantry"], "cavalry": ["cavalry"], "motorized": ["motorized"],
    # la marina y los montañeros tienen sprite propio (unique_units); sin modelo, su infantería
    "marine": ["marine", "infantry"], "mountaineers": ["mountaineers", "infantry"],
    "mechanized": ["mechanized"], "armored_car": ["armored_car"], "light_armor": ["light_armor"],
    "medium_armor": ["medium_armor"], "artillery": ["artillery"], "anti_tank": ["anti_tank"],
    "anti_air": ["anti_air"], "light_plane": ["light_plane", "fighter"],
    "medium_plane": ["medium_plane", "tactical_bomber"], "cas": ["cas"], "naval_bomber": ["naval_bomber"],
    "fighter": ["fighter"], "tactical_bomber": ["tactical_bomber"],
    "destroyer": ["destroyer"], "light_cruiser": ["light_cruiser"], "heavy_cruiser": ["heavy_cruiser"],
    "battleship": ["battleship"], "carrier": ["carrier"], "submarine": ["submarine"], "convoy": ["convoy"],
}
# lista del diseñador -> (sprite, filtro de batallón)
DISENADOR = [
    ("light_tank_chassis", "light_armor", None), ("medium_tank_chassis", "medium_armor", None),
    ("small_plane_airframe", "fighter", None), ("cv_small_plane_airframe", "fighter", None),
    ("small_plane_cas_airframe", "cas", None), ("cv_small_plane_cas_airframe", "cas", None),
    ("small_plane_naval_bomber_airframe", "naval_bomber", None),
    ("cv_small_plane_naval_bomber_airframe", "naval_bomber", None),
    ("medium_plane_airframe", "tactical_bomber", None), ("ship_hull_light", "destroyer", None),
    ("ship_hull_cruiser", "light_cruiser", "light_cruiser"), ("ship_hull_cruiser", "heavy_cruiser", "heavy_cruiser"),
    ("ship_hull_heavy", "battleship", None), ("ship_hull_carrier", "carrier", None),
    ("ship_hull_submarine", "submarine", None),
]
ANARQUIAS = ("ZWE", "ZWI", "ZWM", "ZWB", "ZAN")
_ENTIDAD = re.compile(r'entity\s*=\s*\{\s*name\s*=\s*"([^"]+)"')


def _bloques_entidad(texto: str) -> list[str]:
    out, i = [], 0
    while True:
        j = texto.find("entity", i)
        if j < 0:
            return out
        m = re.match(r'entity\s*=\s*\{', texto[j:])
        if not m:
            i = j + 6
            continue
        d, k = 0, j + m.end() - 1
        for p in range(k, len(texto)):
            d += {"{": 1, "}": -1}.get(texto[p], 0)
            if d == 0:
                break
        out.append(texto[j:p + 1])
        i = p + 1


def respaldo(ctx: BuildContext) -> None:
    base = ctx.spec.root.parent.joinpath(*CARPETA)
    if not base.is_dir():
        return
    definidas: dict[str, str] = {}      # nombre de entidad -> su bloque
    for f in sorted(base.glob("*/gfx/entities/*.asset")):
        for b in _bloques_entidad(f.read_text(encoding="utf-8-sig")):
            m = _ENTIDAD.match(b)
            if m:
                definidas.setdefault(m.group(1), b)
    if not any(n.startswith("COMUN_") for n in definidas) and not definidas:
        return

    def propia(tag: str, sprite: str) -> str | None:
        for s in SPRITES[sprite]:
            if f"{tag}_{s}_entity" in definidas:
                return f"{tag}_{s}_entity"
        return None

    salida, lista, usos = [], Block(), {"meganación": 0, "anarquía": 0, "común": 0}
    for c in ctx.spec.countries:
        bloque_pais = Block()
        for sprite in SPRITES:
            nombre = f"{c.tag}_{sprite}_entity"
            fuente, de = None, None
            if propia(c.tag, sprite):
                fuente = propia(c.tag, sprite) if nombre not in definidas else None
                de = "propia"
            elif c.is_subject and c.overlord and propia(c.overlord, sprite):
                fuente, de = propia(c.overlord, sprite), "meganación"
            elif c.tag in ANARQUIAS and propia("ANARQUIA", sprite):
                fuente, de = propia("ANARQUIA", sprite), "anarquía"
            elif propia("COMUN", sprite):
                fuente, de = propia("COMUN", sprite), "común"
            if fuente and nombre not in definidas:
                b = definidas[fuente].replace(f'"{fuente}"', f'"{nombre}"', 1)
                salida.append(b)
                definidas[nombre] = b
                if de in usos:
                    usos[de] += 1
        if c.is_major:
            continue    # las meganaciones ya tienen sus listas en cada pieza
        for eq, sprite, sub in DISENADOR:
            ent = propia(c.tag, sprite)
            if not ent:
                continue
            pool = Block([("weight", 100)])
            if sub:
                pool.add("sub_units", Block([(None, sub)]))
            pool.add("models", Block([(None, ent)]))
            bloque_pais.add(eq, Block([("pool", pool)]))
        if bloque_pais.entries:
            lista.add(c.tag, bloque_pais)
    if salida:
        ctx.write_text("gfx/entities/zz_meganations_modelos_respaldo.asset",
                       banner_for("assets/modelos (respaldo: meganación o común)") + "\n".join(salida) + "\n")
    if lista.entries:
        ctx.write_script("gfx/interface/equipmentdesigner/graphic_db/zz_meganations_modelos_respaldo.txt",
                         lista, source="assets/modelos")
    if salida:
        ctx.note(f"modelos de respaldo: {usos['meganación']} entidades de satélites con el modelo de su meganación, "
                 f"{usos['anarquía']} de anarquías con el de anarquía, {usos['común']} con el común")
