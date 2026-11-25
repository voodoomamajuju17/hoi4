"""Los trenes que circulan por las vías, del mundo 2100 (2026-11-25).

Captura del usuario: "se ve todo excepto los trenes". Los trenes del mapa son del DLC No Step Back
(dlc/dlc034_no_step_back/gfx/models/units/trains/, que mandó el usuario): cada tren es una locomotora
<TAG>_train_locomotive_equipment_N_entity y vagones <TAG>_train_coal_equipment_N_entity (N = el nivel del
equipo de tren), cada pieza con la punta en el origen y el cuerpo hacia -Z, con escala de entidad 0,5 (locomotora
de unas 13 unidades de malla, vagón de 6 a 9).

Acá: nuestro tren de carga partido en motriz y tres vagones (tools/arte/partir_tren.py) es la locomotora y el
vagón de todos los países, un vagón distinto por nivel (portacontenedores, cisterna, cerrado). Las entidades que el
DLC ya define (GER, SOV, USA...) se reemplazan escribiendo el mismo archivo del DLC en el mod; las demás van en un
archivo propio. Sin el DLC en la instalación no se escribe nada (el juego no dibuja trenes sin él).
"""

from __future__ import annotations

import re

from ..context import BuildContext
from ..pdx import banner_for
from .edificios_mapa import bloques, lado_mayor

PIEZA = ("assets", "mundo_2100", "trenes", "mundo_tren_suministro")
DLC = ("dlc", "dlc034_no_step_back")
CARPETA_MOD = "gfx/models/units/trains_2100"
TEXTURAS = ("mundo_tren_suministro_diffuse.dds", "mundo_tren_suministro_normal_pdx.dds",
            "mundo_tren_suministro_specular.dds")
VAGON_POR_NIVEL = {1: "mundo_tren_vagon_1", 2: "mundo_tren_vagon_2", 3: "mundo_tren_vagon_3"}
# medida del vagón del juego en el mapa (GER_train_coal_equipment_1: 7,72 de malla x 0,5): una sola escala para la
# motriz y los vagones (que no se deformen) y que ningún coche sea más largo que el del juego (no se encimen)
VAGON_JUEGO = 7.72 * 0.5
_RE_LOCO = re.compile(r"^[A-Z]{3}_train_locomotive_(?:\d_)?equipment_\d_entity$")
_RE_VAGON = re.compile(r"^[A-Z]{3}_train_coal_equipment_(\d)_entity$")


def _entidad(nombre: str, malla: str, escala: float) -> str:
    return "\n".join([f'entity = {{', f'\tname = "{nombre}"', f'\tpdxmesh = "{malla}"', '\tdefault_state = "idle"',
                      '\tstate = { name = "idle" }', '\tstate = { name = "move" }', f'\tscale = {escala:.5f}', '}'])


def _malla(nombre: str) -> str:
    return "\n".join([
        "\tpdxmesh = {", f'\t\tname = "{nombre}_mesh"', f'\t\tfile = "{CARPETA_MOD}/{nombre}.mesh"',
        "\t\tmeshsettings = {", '\t\t\tname = "mundo_tren_suministroShape"', "\t\t\tindex = 0",
        f'\t\t\ttexture_diffuse = "{TEXTURAS[0]}"', f'\t\t\ttexture_normal = "{TEXTURAS[1]}"',
        f'\t\t\ttexture_specular = "{TEXTURAS[2]}"', '\t\t\tshader = "PdxMeshAdvanced"', "\t\t}", "\t}"])


def emit(ctx: BuildContext) -> None:
    base = ctx.spec.root.parent.joinpath(*PIEZA)
    carpeta = next(base.glob("gfx/models/**/mundo_tren_motriz.mesh"), None) if base.is_dir() else None
    if carpeta is None:
        return
    carpeta = carpeta.parent
    dlc = ctx.vanilla.root.joinpath(*DLC) if ctx.vanilla else None
    trenes_dlc = dlc / "gfx" / "models" / "units" / "trains" if dlc else None
    if trenes_dlc is None or not trenes_dlc.is_dir():
        ctx.note("trenes del mapa 2100: sin el DLC No Step Back en la instalación; quedan los del juego")
        return
    mallas = ["mundo_tren_motriz"] + list(VAGON_POR_NIVEL.values())
    largo = max(lado_mayor(carpeta / f"{m}.mesh") for m in VAGON_POR_NIVEL.values())
    escala = VAGON_JUEGO / largo
    for m in mallas:
        ctx.copy_asset((carpeta / f"{m}.mesh").relative_to(ctx.spec.root.parent).as_posix(),
                       f"{CARPETA_MOD}/{m}.mesh")
    for t in TEXTURAS:
        ctx.copy_asset((carpeta / t).relative_to(ctx.spec.root.parent).as_posix(), f"{CARPETA_MOD}/{t}")
    ctx.write_text("gfx/entities/meganations_trenes_2100.gfx",
                   banner_for("assets/mundo_2100/trenes (tren de carga partido en motriz y vagones)")
                   + "objectTypes = {\n" + "\n".join(_malla(m) for m in mallas) + "\n}\n")

    def nueva(nombre: str) -> str | None:
        if _RE_LOCO.match(nombre):
            return _entidad(nombre, "mundo_tren_motriz_mesh", escala)
        v = _RE_VAGON.match(nombre)
        if v:
            return _entidad(nombre, f"{VAGON_POR_NIVEL.get(int(v.group(1)), 'mundo_tren_vagon_1')}_mesh", escala)
        return None

    # las del DLC: el mismo archivo en el mod (lo reemplaza) con nuestra entidad del mismo nombre
    del_dlc: set[str] = set()
    for f in sorted(trenes_dlc.glob("*.asset")):
        texto = f.read_text(encoding="utf-8-sig", errors="replace")
        ents = [nueva(n) for _i, _j, n in bloques(texto) if n]
        nombres = [n for _i, _j, n in bloques(texto) if n and nueva(n)]
        if not nombres:
            continue
        del_dlc |= set(nombres)
        ctx.write_text(f"gfx/models/units/trains/{f.name}",
                       banner_for(f"{f.name} del DLC No Step Back con el tren del mundo 2100")
                       + "\n\n".join(e for e in ents if e) + "\n")
    # las mallas del DLC piden animaciones que estaban en esos archivos: sin ellas, el archivo de mallas vacío
    if (dlc / "gfx" / "entities" / "NSB_units_trains_meshes.gfx").is_file():
        ctx.write_text("gfx/entities/NSB_units_trains_meshes.gfx",
                       banner_for("NSB_units_trains_meshes.gfx del DLC: los trenes del juego ya no se usan")
                       + "objectTypes = {\n}\n")
    # el resto de los países: sus propias entidades (el juego busca primero las de su etiqueta)
    propias = []
    for c in ctx.spec.countries:
        for n in (1, 2, 3):
            for nombre in (f"{c.tag}_train_locomotive_equipment_{n}_entity", f"{c.tag}_train_coal_equipment_{n}_entity"):
                if nombre not in del_dlc:
                    propias.append(nueva(nombre))
    ctx.write_text("gfx/entities/meganations_trenes_2100.asset",
                   banner_for("assets/mundo_2100/trenes: el tren de carga de cada país") + "\n\n".join(propias) + "\n")
    ctx.note(f"trenes del mapa 2100: {len(del_dlc)} entidades del DLC reemplazadas y {len(propias)} propias, "
             f"escala {escala:.3f} (vagón de {VAGON_JUEGO:.2f} en el mapa, como el del juego)")
