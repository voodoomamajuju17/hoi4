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
    emit_monumentos(ctx)


# ---------------------------------------------------------------------------- los monumentos de las capitales
# 2026-11-24: los 10 de assets/mundo_2100/monumentos (parte E). Un monumento del juego es un edificio de provincia
# (common/buildings/01_landmark_buildings.txt: spawn_point = landmark_spawn, only_display_if_exists, is_buildable = no)
# que la historia del estado pone en una provincia, y el juego lo dibuja en el punto `landmark_spawn` de
# map/buildings.txt que cae en esa provincia. Acá: uno por capital, en la provincia de su punto de victoria; si en
# esa provincia no hay punto de aparición, se agrega uno (map/buildings.txt del juego + nuestras líneas). Si la
# provincia tenía un monumento del juego (el Coliseo en Roma), lo reemplaza el nuestro.
MONUMENTOS = {
    "EFE": ("The Iguazú Citadel", "La Ciudadela del Iguazú"),
    "ASC": ("The Brandenburg Datacentre", "El Datacenter de Brandeburgo"),
    "FCU": ("The Board Tower", "La Torre del Directorio"),
    "HSN": ("The Lighthouse of the Straits", "El Faro de los Estrechos"),
    "NAS": ("The Temple of the Sun", "El Templo del Sol"),
    "SHD": ("The Great Dam", "La Gran Represa"),
    "APF": ("The House of Councils", "La Casa de los Consejos"),
    "NRE": ("The New Colosseum", "El Nuevo Coliseo"),
    "ZJP": ("The Great Dry Dock of Yokosuka", "El Gran Dique Seco de Yokosuka"),
    "ZAL": ("The Palace of the Two Eras", "El Palacio de las Dos Eras"),
}
MEDIDA_MONUMENTO = 2.4
_TIPOS_PROVINCIA = ("landmark_spawn", "bunker", "supply_node", "special_project_facility_spawn")


def clave_monumento(tag: str) -> str:
    return f"landmark_mn_{tag}"


def plan_monumentos(ctx: BuildContext, capitals: dict[str, int], by_state: dict) -> dict[int, tuple[int, str]]:
    """Estado -> (provincia, edificio) para la historia; guarda en ctx.data["monumentos"] dónde va cada uno."""
    base = ctx.spec.root.parent / "assets" / "mundo_2100" / "monumentos"
    if not ctx.vanilla or not base.is_dir():
        return {}
    lineas = ctx.vanilla.map_buildings()
    if not lineas:
        return {}
    por_estado: dict[int, list[list[str]]] = {}
    for p in lineas:
        if p[0].strip().isdigit():
            por_estado.setdefault(int(p[0]), []).append(p)
    plan, datos = {}, {}
    for tag in MONUMENTOS:
        sid = capitals.get(tag)
        st = by_state.get(sid)
        if st is None or not (base / f"{tag}_monumento").is_dir():
            continue
        quiero = st.vp_provinces[0] if st.vp_provinces else None
        elegida = None          # (provincia, línea, ya_es_landmark_spawn)
        for tipo in _TIPOS_PROVINCIA:
            for p in por_estado.get(sid, []):
                if p[1] != tipo:
                    continue
                prov = ctx.vanilla.province_at(float(p[2]), float(p[4]))
                if prov is None:
                    continue
                if prov == quiero or (elegida is None and quiero is None):
                    elegida = (prov, p, tipo == "landmark_spawn")
                    break
            if elegida:
                break
        if elegida is None:
            # sin punto en la provincia del punto de victoria: el primero del estado que caiga en una provincia
            for p in por_estado.get(sid, []):
                if p[1] in _TIPOS_PROVINCIA:
                    prov = ctx.vanilla.province_at(float(p[2]), float(p[4]))
                    if prov in st.provinces:
                        elegida = (prov, p, p[1] == "landmark_spawn")
                        break
        if elegida is None:
            ctx.warn(f"monumentos: {tag} (estado {sid}) sin un punto del mapa en una provincia suya; queda sin monumento")
            continue
        prov, p, existe = elegida
        plan[sid] = (prov, clave_monumento(tag))
        datos[tag] = {"state": sid, "province": prov, "linea": None if existe else
                      f"{sid};landmark_spawn;{p[2]};{p[3]};{p[4]};0.00;0"}
    ctx.data["monumentos"] = datos
    return plan


def emit_monumentos(ctx: BuildContext) -> None:
    datos = ctx.data.get("monumentos") or {}
    if not datos:
        return
    base = ctx.spec.root.parent / "assets" / "mundo_2100" / "monumentos"
    defs, ents, mallas = [], [], []
    for tag, d in sorted(datos.items()):
        carpeta = base / f"{tag}_monumento"
        malla = next(carpeta.glob("gfx/models/**/*.mesh"))
        gfx = (carpeta / "gfx" / "entities" / f"{tag}_monumento.gfx").read_text(encoding="utf-8-sig")
        nombre_malla = re.search(r'pdxmesh\s*=\s*\{\s*name\s*=\s*"([^"]+)"', gfx).group(1)
        clave = clave_monumento(tag)
        en, es = MONUMENTOS[tag]
        defs.append(f"""\t{clave} = {{
\t\tshow_on_map = 1
\t\tbase_cost = 20000
\t\tdamage_factor = 0
\t\ticon_frame = 22
\t\tvalue = 5
\t\tis_buildable = no
\t\tdisable_grow_animation = yes
\t\tspawn_point = landmark_spawn
\t\tonly_display_if_exists = yes
\t\tlevel_cap = {{
\t\t\tprovince_max = 1
\t\t}}
\t\talways_shown = yes
\t\tdrawn_at_distance = yes
\t}}""")
        ents.append(f"""entity = {{
\tname = "building_{clave}"
\tpdxmesh = "{nombre_malla}"
\tdefault_state = "idle"
\tstate = {{ name = "idle" }}
\tscale = {MEDIDA_MONUMENTO / max(lado_mayor(malla), 1e-6):.5f}
}}""")
        mallas.append(gfx)
        for f in sorted((carpeta / "gfx" / "models").rglob("*")):
            if f.is_file() and f.suffix != ".png":
                ctx.copy_asset(f.relative_to(ctx.spec.root.parent).as_posix(), f.relative_to(carpeta).as_posix())
        # el juego nombra el edificio con su clave (como landmark_big_ben): la usa él, no un archivo nuestro
        ctx.loc.define_and_reference(clave, en=en, es=es, file="meganations_monumentos", origin="edificios_mapa")
    ctx.write_text("common/buildings/meganations_monumentos.txt",
                   banner_for("assets/mundo_2100/monumentos (un monumento por capital)")
                   + "buildings = {\n" + "\n\n".join(defs) + "\n}\n")
    ctx.write_text("gfx/entities/meganations_monumentos.asset",
                   banner_for("assets/mundo_2100/monumentos") + "\n\n".join(ents) + "\n")
    ctx.write_text("gfx/entities/meganations_monumentos.gfx",
                   banner_for("assets/mundo_2100/monumentos (mallas)") + "\n".join(mallas))
    nuevas = [d["linea"] for d in datos.values() if d["linea"]]
    if nuevas:
        texto = (ctx.vanilla.root / "map" / "buildings.txt").read_text(encoding="utf-8-sig", errors="replace")
        ctx.write_text("map/buildings.txt", texto.rstrip("\n") + "\n" + "\n".join(nuevas) + "\n")
    ctx.note(f"monumentos: {len(datos)} en sus capitales ({', '.join(sorted(datos))}); "
             f"{len(nuevas)} puntos de aparición nuevos en map/buildings.txt")
