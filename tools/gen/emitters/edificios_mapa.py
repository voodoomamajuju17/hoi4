"""Los edificios del mapa en el mundo 2100 (2026-11-24).

Los 20 modelos de assets/mundo_2100/edificios/ (pedido arte/pedidos_fijos/60_modelos_3d_mundo_2100.txt, parte B)
reemplazan a los del juego de 1936. Cómo los busca el juego (gfx/entities/buildings.asset de 1.16, que mandó el
usuario): "Name must match 'building_' + building tag", o sea building_arms_factory, building_dockyard_1..3,
building_naval_base_1..3, etc.

El archivo del juego trae además las ciudades, las represas, los canales y los edificios destruidos. Para no
tocar nada de eso, el armado lee el archivo del juego (--vanilla-path), cambia solo las entidades de esta tabla
y escribe el archivo con el mismo nombre en el mod (el mod reemplaza el del juego). Sin el juego a mano no
escribe nada: los edificios quedan los de siempre.

Tamaño: las mallas vienen en metros reales; la escala de cada entidad lleva su lado mayor a una medida en el
mapa (unidades del mapa: un píxel del mapa de provincias; las fábricas del juego se separan 2 por estado).
Las medidas son estimadas: el juego no dice cuánto miden sus mallas.
"""

from __future__ import annotations

import re
from pathlib import Path

from .. import pdxbin
from ..context import BuildContext
from ..pdx import banner_for

CARPETA = ("assets", "mundo_2100", "edificios")
ARCHIVOS = ("buildings.asset", "MTG_buildings.asset")

# modelo -> (entidades del juego que reemplaza, lado mayor en el mapa)
MAPA: dict[str, tuple[tuple[str, ...], float]] = {
    "mundo_fabrica_civil": (("building_industrial_complex",), 1.6),
    "mundo_fabrica_militar": (("building_arms_factory",), 1.6),
    "mundo_astillero": (("building_dockyard_1", "building_dockyard_2", "building_dockyard_3"), 2.0),
    "mundo_puerto": (("building_naval_base_1", "building_naval_base_2", "building_naval_base_3",
                      "building_naval_base_spawn"), 2.4),
    "mundo_base_aerea": (("building_air_base",), 2.2),
    "mundo_fuerte": (("building_bunker",), 1.2),
    "mundo_fuerte_costero": (("building_coastal_bunker",), 1.4),
    "mundo_antiaerea": (("building_anti_air_building",), 0.9),
    "mundo_radar": (("building_radar_station",), 1.2),
    "mundo_sitio_cohetes": (("building_rocket_site", "building_rocket_site_spawn"), 1.6),
    # el de agua pesada es un clon de building_nuclear_reactor en el juego: sigue al nuestro solo
    "mundo_reactor": (("building_nuclear_reactor", "building_nuclear_reactor_spawn",
                       "building_commercial_nuclear_reactor"), 1.8),
    "mundo_refineria": (("building_synthetic_refinery",), 1.6),
    "mundo_silo": (("building_fuel_silo",), 1.4),
    "mundo_centro_suministro": (("building_supply_node",), 2.0),
    "mundo_proyecto_tierra": (("building_land_facility",), 2.0),
    "mundo_proyecto_aire": (("building_air_facility",), 2.0),
    "mundo_proyecto_mar": (("building_naval_facility",), 2.0),
    "mundo_proyecto_atomo": (("building_nuclear_facility",), 2.0),
}
# estados que el juego le pide a cada edificio (los de buildings.asset); sin animación propia, quieto
ESTADOS = {"building_anti_air_building": ("idle", "combat_idle", "attack", "damaged"),
           "building_radar_station": ("idle", "damaged")}
SIN_USO = ("mundo_puerto_flotante", "mundo_via_maglev")   # el juego no los dibuja como edificio

_ENTIDAD = re.compile(r'(?m)^entity\s*=\s*\{')


def bloques(texto: str) -> list[tuple[int, int, str | None]]:
    """(inicio, fin, nombre) de cada `entity = { ... }` del archivo, contando llaves fuera de comentarios."""
    out = []
    for m in _ENTIDAD.finditer(texto):
        i, prof, j = m.start(), 0, m.end() - 1
        while j < len(texto):
            c = texto[j]
            if c == "#":
                j = texto.find("\n", j)
                if j < 0:
                    break
                continue
            if c == "{":
                prof += 1
            elif c == "}":
                prof -= 1
                if prof == 0:
                    break
            j += 1
        cuerpo = texto[i:j + 1]
        n = re.search(r'name\s*=\s*"([^"]+)"', cuerpo)
        out.append((i, j + 1, n.group(1) if n else None))
    return out


def lado_mayor(malla: Path) -> float:
    raiz = pdxbin.leer(malla.read_bytes())
    lado = 0.0
    for n in raiz.todos() if hasattr(raiz, "todos") else []:
        if getattr(n, "nombre", "") == "aabb":
            mn, mx = n.props["min"][1], n.props["max"][1]
            lado = max(lado, mx[0] - mn[0], mx[2] - mn[2])
    return lado


def entidad(nombre: str, malla: str, escala: float, animada: bool) -> str:
    estados = ESTADOS.get(nombre, ("idle", "damaged"))
    anim = ' animation = "idle" looping = yes' if animada else ""
    lineas = [f'entity = {{', f'\tname = "{nombre}"', f'\tpdxmesh = "{malla}"', '\tdefault_state = "idle"']
    lineas += [f'\tstate = {{ name = "{e}"{anim} }}' for e in estados]
    lineas += [f'\tscale = {escala:.5f}', '}']
    return "\n".join(lineas)


def emit(ctx: BuildContext) -> None:
    base = ctx.spec.root.parent.joinpath(*CARPETA)
    if not base.is_dir():
        return
    juego = ctx.vanilla.root / "gfx" / "entities" if ctx.vanilla else None
    if juego is None or not (juego / "buildings.asset").is_file():
        ctx.warn("edificios del mapa 2100: sin gfx/entities/buildings.asset del juego (--vanilla-path); "
                 "quedan los edificios de siempre")
        return
    nuevas: dict[str, str] = {}
    mallas = []
    for pieza, (reemplaza, medida) in MAPA.items():
        carpeta = base / pieza
        malla = next(carpeta.glob("gfx/models/**/*.mesh"), None)
        gfx = carpeta / "gfx" / "entities" / f"{pieza}.gfx"
        if malla is None or not gfx.is_file():
            ctx.warn(f"edificios del mapa 2100: falta {pieza} (malla o .gfx); queda el del juego")
            continue
        lado = lado_mayor(malla)
        if lado <= 0:
            ctx.warn(f"edificios del mapa 2100: {pieza} sin caja de la malla; queda el del juego")
            continue
        texto_gfx = gfx.read_text(encoding="utf-8-sig")
        m = re.search(r'pdxmesh\s*=\s*\{\s*name\s*=\s*"([^"]+)"', texto_gfx)
        animada = "animation" in texto_gfx
        for nombre in reemplaza:
            nuevas[nombre] = entidad(nombre, m.group(1), medida / lado, animada)
        mallas.append(texto_gfx)
        # malla, texturas, animaciones y su .asset (las animaciones van junto a los .anim, con el nombre suelto)
        for f in sorted((carpeta / "gfx" / "models").rglob("*")):
            if f.is_file() and f.suffix != ".png":
                ctx.copy_asset(f.relative_to(ctx.spec.root.parent).as_posix(),
                               f.relative_to(carpeta).as_posix())
    hechas: set[str] = set()
    for nombre_archivo in ARCHIVOS:
        f = juego / nombre_archivo
        if not f.is_file():
            continue
        texto = f.read_text(encoding="utf-8-sig", errors="replace")
        salida, ultimo = [], 0
        for i, j, nombre in bloques(texto):
            if nombre in nuevas:
                salida += [texto[ultimo:i], nuevas[nombre]]
                ultimo = j
                hechas.add(nombre)
        salida.append(texto[ultimo:])
        ctx.write_text(f"gfx/entities/{nombre_archivo}",
                       banner_for(f"gfx/entities/{nombre_archivo} del juego con los edificios del mundo 2100 "
                                  "(assets/mundo_2100/edificios)") + "".join(salida))
    ctx.write_text("gfx/entities/meganations_edificios_2100.gfx",
                   banner_for("assets/mundo_2100/edificios (mallas de los edificios del mapa)")
                   + "\n".join(mallas))
    faltan = sorted(set(nuevas) - hechas)
    if faltan:
        ctx.warn(f"edificios del mapa 2100: el juego no tiene estas entidades (quedan sin usar): {', '.join(faltan)}")
    ctx.note(f"edificios del mapa 2100: {len(hechas)} entidades del juego con modelo propio "
             f"({len(mallas)} modelos)")
