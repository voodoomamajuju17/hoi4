"""Modelos 3D propios (2026-11-08: el Gliptodonte del EFE, hecho por el usuario en Blender).

Cada carpeta de assets/modelos/<pieza>/ trae su árbol gfx/ (gfx/models/..., gfx/entities/*.asset,
gfx/interface/equipmentdesigner/graphic_db/*.txt) tal como va en el mod: se copia igual. El
.blend y la vista previa quedan en assets/ (son para editar, el juego no los usa).
"""

from __future__ import annotations

import re

from .. import modelo3d
from ..context import BuildContext
from ..pdx import Block, banner_for

CARPETA = ("assets", "modelos")

# 2026-11-13 (captura del usuario: "la infanteria es miniatura y los barcos gigantescos"): las mallas
# vienen en metros y el juego no dibuja a escala real. Medida final en el mapa, tomada de las unidades
# del juego (malla x escala de la malla x escala de la entidad, gfx/entities/*.gfx y *.asset de 1.19):
# infantería GER 5,9 de alto; tanques GER 3,0 / 4,2 / 5,1 de largo; mecanizada 5,4; aviones ENG 4,0 /
# 5,7 / 8,1 de envergadura; barcos: destructor 13,3, crucero ligero 17,4, pesado 17,6, acorazado 21,9,
# portaaviones 25,1, submarino 12,5. (eje, medida): "alto" = Y, "largo" = Z, "ancho" = el mayor de X y Z.
HUMANO = 3.2        # la gente a 3,2 veces el tamaño real: 1,85 m -> 5,9 como el juego
ESCALA = {
    "infantry": ("humano", 0), "marine": ("humano", 0), "mountaineers": ("humano", 0),
    "cavalry": ("largo", 7.0),     # las nuestras son motos y bestias de 3 a 5 m: a 3,2x pasaban de 15
    "light_armor": ("largo", 3.6), "medium_armor": ("largo", 4.4), "heavy_armor": ("largo", 5.2),
    "mecha": ("largo", 5.2), "gliptodonte": ("largo", 5.2), "onagro": ("largo", 5.2),
    "armored_car": ("largo", 3.6), "mechanized": ("largo", 4.6), "amphibious_mechanized": ("largo", 4.6),
    "kiboko": ("largo", 4.6), "motorized": ("largo", 4.6), "centinela": ("largo", 4.0),
    "centinela_2": ("largo", 4.0), "centinela_3": ("largo", 4.4), "artillery": ("largo", 4.2),
    "anti_tank": ("largo", 3.8), "anti_air": ("largo", 3.8), "railway_gun": ("largo", 9.0),
    "dragon_del_canal": ("largo", 9.0),
    "fighter": ("ancho", 4.0), "light_plane": ("ancho", 4.0), "cas": ("ancho", 4.3),
    "naval_bomber": ("ancho", 4.6), "medium_plane": ("ancho", 5.7), "tactical_bomber": ("ancho", 5.7),
    "heavy_plane": ("ancho", 8.1), "ala_de_obsidiana": ("ancho", 8.1), "transport_plane": ("ancho", 6.0),
    "hijos_del_condor": ("ancho", 5.0),
    "destroyer": ("largo", 13.3), "light_cruiser": ("largo", 17.4), "heavy_cruiser": ("largo", 18.5),
    "battleship": ("largo", 22.0), "carrier": ("largo", 25.0), "submarine": ("largo", 12.5),
    "convoy": ("largo", 13.0), "leviatan": ("largo", 28.0),
}


def escala_para(sprite: str, medida: tuple[float, float, float], escala_malla: float = 1.0) -> float | None:
    if sprite not in ESCALA or not any(medida):
        return None
    eje, objetivo = ESCALA[sprite]
    x, y, z = (v * escala_malla for v in medida)
    if eje == "humano":
        return round(HUMANO / escala_malla, 4)
    base = {"alto": y, "largo": z, "ancho": max(x, z)}[eje]
    return round(objetivo / base, 4) if base else None


def _sin_escala_propia(bloque: str) -> str:
    """El bloque de entidad sin su `scale` de primer nivel (los de los estados quedan)."""
    out, d, i = [], 0, 0
    for m in re.finditer(r"[{}]|\bscale\s*=\s*[-\d.]+", bloque):
        if m.group(0) == "{":
            d += 1
        elif m.group(0) == "}":
            d -= 1
        elif d == 1:
            out.append(bloque[i:m.start()])
            i = m.end()
    out.append(bloque[i:])
    return "".join(out)


def escalar(entidades: str, medidas: dict[str, tuple[tuple[float, float, float], float]]) -> tuple[str, list[str]]:
    """Pone a cada entidad la escala de su tipo (por el nombre, <TAG>_<sprite>_entity) según la
    medida de su malla. Devuelve el texto y las entidades que quedaron sin tocar."""
    sin = []

    def una(b: str) -> str:
        m = re.match(r'entity\s*=\s*\{\s*name\s*=\s*"([^"]+)"', b)
        pm = re.search(r'\bpdxmesh\s*=\s*"([^"]+)"', b)
        if not m or not pm or pm.group(1) not in medidas:
            return b
        sprite = re.sub(r"^[A-Z]+_", "", m.group(1)).removesuffix("_entity")
        medida, escala_malla = medidas[pm.group(1)]
        e = escala_para(sprite, medida, escala_malla)
        if e is None:
            sin.append(m.group(1))
            return b
        b = _sin_escala_propia(b)
        return b[:pm.end()] + f"\n    scale = {e}" + b[pm.end():]
    return "\n".join(una(b) for b in _bloques_entidad(entidades)) + "\n", sin


def emit(ctx: BuildContext) -> None:
    base = ctx.spec.root.parent.joinpath(*CARPETA)
    if not base.is_dir():
        return
    piezas = []
    ESCALADAS.clear()
    resumen = {"huesos": [], "signos": 0, "sombreado": 0, "sin_escala": []}
    for pieza in sorted(p for p in base.iterdir() if p.is_dir()):
        gfx = pieza / "gfx"
        if not gfx.is_dir():
            continue
        n = 0
        medidas = arreglar_mallas(ctx, pieza, resumen)
        for f in sorted(gfx.rglob("*")):
            if f.is_file():
                rel = f.relative_to(pieza).as_posix()
                if f.suffix in (".mesh", ".anim"):
                    n += 1          # ya escritos por arreglar_mallas
                    continue
                if f.suffix == ".asset" and rel.startswith("gfx/entities/"):
                    # 2026-11-12 (error.log del usuario: "Unexpected token: pdxmesh" en gfx/entities/ y
                    # "Could not load animation file gfx/entities/gfx/models/..."): el juego solo acepta
                    # entidades en gfx/entities/; mallas y animaciones van en un .asset junto a la malla,
                    # con los archivos nombrados desde esa carpeta (como el juego)
                    fuente = banner_for(f"assets/modelos/{pieza.name} (modelo 3D propio)")
                    # 2026-11-13 (captura: "siguen sin haber modelos"; mirado en los archivos del juego,
                    # gfx/entities/tanks.gfx y gfx/models/units/animation.asset): las mallas van en un .gfx
                    # dentro de objectTypes, con la ruta desde la raíz; las animaciones, en un .asset junto
                    # a los .anim con el nombre suelto; las entidades, en gfx/entities/*.asset
                    entidades, animaciones, mallas, carpeta = separar_asset(f.read_text(encoding="utf-8-sig"))
                    entidades, sin = escalar(entidades, medidas)
                    resumen["sin_escala"] += sin
                    for b in _bloques_entidad(entidades):
                        m = _ENTIDAD.match(b)
                        if m:
                            ESCALADAS[m.group(1)] = b
                    ctx.write_text(rel, fuente + entidades)
                    if animaciones:
                        ctx.write_text(f"{carpeta}/{f.name}", fuente + animaciones)
                    if mallas:
                        ctx.write_text(rel[:-len(".asset")] + ".gfx", fuente + mallas)
                    n += 1
                    continue
                if rel.startswith("gfx/interface/equipmentdesigner/graphic_db/") and pieza.name.startswith("COMUN_"):
                    # "COMUN" no es un país ("Expected 'default', a continent name or a country tag");
                    # la lista de los que usan el común la arma respaldo()
                    continue
                if f.suffix in (".txt", ".asset", ".gfx"):
                    # los de texto llevan el encabezado de archivo generado, como todo el mod
                    texto = f.read_text(encoding="utf-8-sig")
                    if rel.startswith("gfx/interface/equipmentdesigner/graphic_db/"):
                        texto = arquetipos(texto)
                    ctx.write_text(rel, banner_for(f"assets/modelos/{pieza.name} (modelo 3D propio)") + texto)
                else:
                    ctx.copy_asset(f.relative_to(ctx.spec.root.parent).as_posix(), rel)
                n += 1
        piezas.append(f"{pieza.name} ({n} archivos)")
    if piezas:
        ctx.note(f"modelos 3D propios: {len(piezas)} piezas")
        ctx.note(f"modelos 3D: {resumen['sombreado']} mallas pasadas a PdxMeshAdvanced, "
                 f"{resumen['signos']} giros de animación enderezados, "
                 f"{len(resumen['huesos'])} mallas recortadas a {modelo3d.MAX_HUESOS} huesos"
                 + (f" ({', '.join(resumen['huesos'])})" if resumen["huesos"] else ""))
        if resumen["sin_escala"]:
            ctx.warn(f"modelos 3D sin tamaño de referencia (quedan como vinieron): {', '.join(resumen['sin_escala'])}")
    respaldo(ctx)


# 2026-11-13 (error.log 1.19.5: "Unknown equipment type: ship_hull_super_heavy"): la lista del
# diseñador va por arquetipo, y el casco superpesado (ship_hull_super_heavy_1) es del arquetipo
# ship_hull_heavy; se separa de los acorazados por el tipo de barco, como los cruceros.
ARQUETIPOS = {"ship_hull_super_heavy": ("ship_hull_heavy", "SH_battleship")}


def arquetipos(texto: str) -> str:
    for viejo, (nuevo, sub) in ARQUETIPOS.items():
        texto = re.sub(r"\b%s(\s*=\s*\{\s*pool\s*=\s*\{)(\s*)weight\s*=\s*\d+" % viejo,
                       lambda m: f"{nuevo}{m.group(1)}{m.group(2)}weight = 1000{m.group(2)}sub_units = {{ {sub} }}",
                       texto)
    return texto


ESCALADAS: dict[str, str] = {}      # entidad -> bloque ya escalado (respaldo copia estos)


def arreglar_mallas(ctx: BuildContext, pieza, resumen: dict) -> dict[str, tuple[tuple[float, float, float], float]]:
    """Escribe los .mesh y .anim de la pieza arreglados (modelo3d) y devuelve la medida de cada
    pdxmesh (por su nombre en el .asset) con la escala que ya trae la malla."""
    import posixpath
    hechos: dict[str, tuple[float, float, float]] = {}
    for malla in sorted(pieza.joinpath("gfx").rglob("*.mesh")):
        anims = {a: a.read_bytes() for a in sorted(malla.parent.glob("*.anim"))}
        datos, nuevas, info = modelo3d.arreglar_carpeta(malla.read_bytes(), {a.name: b for a, b in anims.items()})
        for ruta, contenido in [(malla, datos)] + [(malla.parent / k, v) for k, v in nuevas.items()]:
            dest = ctx.mod_root / ruta.relative_to(pieza)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(contenido)
            ctx.track(dest)
        antes, despues = info["huesos"]
        if antes != despues:
            resumen["huesos"].append(f"{malla.stem} {antes}->{despues}")
        resumen["signos"] += info["signos"]
        resumen["sombreado"] += int(info["sombreado"])
        hechos[malla.relative_to(pieza).as_posix()] = info["medida"]
    # las anim sueltas (sin malla en su carpeta) van tal cual
    for a in sorted(pieza.joinpath("gfx").rglob("*.anim")):
        if not any(a.parent.glob("*.mesh")):
            ctx.copy_asset(a.relative_to(ctx.spec.root.parent).as_posix(), a.relative_to(pieza).as_posix())
    medidas = {}
    for f in pieza.joinpath("gfx", "entities").glob("*.asset"):
        texto = re.sub(r"#[^\n]*", "", f.read_text(encoding="utf-8-sig"))
        for k, b in _bloques(texto):
            if k != "pdxmesh":
                continue
            nombre = re.search(r'name\s*=\s*"([^"]+)"', b)
            archivo = re.search(r'file\s*=\s*"([^"]+)"', b)
            escala = re.search(r"\bscale\s*=\s*([\d.]+)", b)
            if not nombre or not archivo:
                continue
            ruta = archivo.group(1)
            if "/" not in ruta:     # suelta: en la carpeta de la malla (como separar_asset)
                ruta = next((r for r in hechos if posixpath.basename(r) == ruta), ruta)
            if ruta in hechos:
                medidas[nombre.group(1)] = (hechos[ruta], float(escala.group(1)) if escala else 1.0)
    return medidas


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


def _bloques(texto: str) -> list[tuple[str, str]]:
    """Bloques de primer nivel (clave, texto) de un .asset, sin comentarios."""
    texto = re.sub(r"#[^\n]*", "", texto)
    out, i = [], 0
    for m in re.finditer(r"(\w+)\s*=\s*\{", texto):
        if m.start() < i:
            continue
        d = 0
        for p in range(m.end() - 1, len(texto)):
            d += {"{": 1, "}": -1}.get(texto[p], 0)
            if d == 0:
                break
        out.append((m.group(1), texto[m.start():p + 1]))
        i = p + 1
    return out


def separar_asset(texto: str) -> tuple[str, str, str, str | None]:
    """(entidades, animaciones con el nombre suelto del .anim, mallas en objectTypes con la ruta
    desde la raíz, carpeta de la malla). Como el juego: gfx/entities/tanks.gfx tiene
    `objectTypes = { pdxmesh = { file = "gfx/models/units/tanks/ENG_tank_light.mesh" ... } }` y
    gfx/models/units/animation.asset tiene `animation = { name file = "GER_infantry_idle_rifle.anim" }`."""
    import posixpath
    bloques = _bloques(texto)
    archivos = re.findall(r'file\s*=\s*"([^"]+)"', texto)
    mesh = [a for a in archivos if a.endswith(".mesh")]
    carpeta = posixpath.dirname((mesh or archivos)[0]) if archivos else None
    entidades = [b for k, b in bloques if k == "entity"]
    animaciones, mallas = [], []
    for k, b in bloques:
        if k == "animation" and carpeta:
            animaciones.append(re.sub(r'(file\s*=\s*")([^"]+)"',
                                      lambda m: m.group(1) + posixpath.relpath(m.group(2), carpeta) + '"', b))
        elif k == "pdxmesh":
            # la ruta del .mesh desde la raíz del mod (si vino suelta, se completa con su carpeta)
            mallas.append(re.sub(r'(file\s*=\s*")([^"/]+)"',
                                 lambda m: m.group(1) + (f"{carpeta}/" if carpeta else "") + m.group(2) + '"', b))
    gfx = ("objectTypes = {\n" + "\n\n".join(mallas) + "\n}\n") if mallas else ""
    return ("\n".join(entidades) + "\n", ("\n\n".join(animaciones) + "\n") if animaciones else "", gfx, carpeta)


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
                definidas.setdefault(m.group(1), ESCALADAS.get(m.group(1), b))
    if not any(n.startswith("COMUN_") for n in definidas) and not definidas:
        return

    def propia(tag: str, sprite: str) -> str | None:
        for s in SPRITES[sprite]:
            if f"{tag}_{s}_entity" in definidas:
                return f"{tag}_{s}_entity"
        return None

    salida, lista, usos = [], Block(), {"meganación": 0, "anarquía": 0, "común": 0}
    prestadas: set[str] = set()     # entidades que un país toma de otro (meganación, anarquía, común)
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
                if de != "propia":
                    prestadas.add(nombre)
                if de in usos:
                    usos[de] += 1
        for eq, sprite, sub in DISENADOR:
            ent = propia(c.tag, sprite)
            # las meganaciones ya tienen la lista de sus modelos propios en cada pieza; acá van solo
            # los que toman prestados (2026-11-12: el crucero pesado de la NAS usa el común)
            if not ent or (c.is_major and f"{c.tag}_{sprite}_entity" not in prestadas):
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
