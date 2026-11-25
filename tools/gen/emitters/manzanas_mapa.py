"""Las ciudades del mapa en el mundo 2100 (2026-11-25).

El juego llena cada zona urbana con "manzanas" chicas repetidas (map/cities.txt, que mandó el usuario): un grupo por
color de map/cities.bmp (15 occidental, 1 francesa, 0 asiática, 2 no civilizada) con cuatro niveles, `distance` 1
(borde de la ciudad) a 4 (centro), cada uno con su lista de mallas (entidades de gfx/entities/buildings.asset, como
westerngfx_house_1_1 o french_city_4_04_entity). Pedido arte/pedidos_fijos/61_manzanas_ciudades.txt: 4 estilos x 4
niveles x 2 variantes (assets/mundo_2100/manzanas/).

Acá: el map/cities.txt del juego con la lista de cada nivel cambiada por nuestras dos variantes (el juego elige una
al azar en cada lugar). Cada manzana se lleva al tamaño de la del juego que reemplaza (se mide su malla en la
instalación, como los edificios); un grupo cuya malla no se puede medir queda como en el juego.
"""

from __future__ import annotations

import re

from ..context import BuildContext
from ..pdx import banner_for
from .edificios_mapa import lado_mayor, medidas_juego

CARPETA = ("assets", "mundo_2100", "manzanas")
ESTILO = {15: "occidental", 1: "francesa", 0: "asiatica", 2: "periferia"}


def grupos(texto: str) -> list[tuple[int, int, int | None]]:
    """(inicio, fin, color_index) de cada city_group del archivo."""
    out = []
    for m in re.finditer(r"city_group\s*=\s*\{", texto):
        prof, i = 0, m.end() - 1
        while i < len(texto):
            c = texto[i]
            if c == "#":
                i = texto.find("\n", i)
                if i < 0:
                    break
                continue
            prof += {"{": 1, "}": -1}.get(c, 0)
            if prof == 0:
                break
            i += 1
        cuerpo = re.sub(r"#[^\n]*", "", texto[m.start():i + 1])
        ci = re.search(r"color_index\s*=\s*(\d+)", cuerpo)
        out.append((m.start(), i + 1, int(ci.group(1)) if ci else None))
    return out


def niveles(cuerpo: str) -> list[tuple[int, int, int, list[str]]]:
    """(inicio, fin, distance, mallas) de cada `mesh = { ... }` de un grupo, con la distancia de su building."""
    out = []
    for b in re.finditer(r"building\s*=\s*\{.*?distance\s*=\s*(\d+).*?(mesh\s*=\s*\{(.*?)\})", cuerpo, re.S):
        mallas = re.findall(r'"([^"]+)"', re.sub(r"#[^\n]*", "", b.group(3)))
        out.append((b.start(2), b.end(2), int(b.group(1)), mallas))
    return out


def _entidad(nombre: str, malla: str, escala: float) -> str:
    return "\n".join([f'entity = {{', f'\tname = "{nombre}"', f'\tpdxmesh = "{malla}"', '\tdefault_state = "idle"',
                      '\tstate = { name = "idle" }', '\tstate = { name = "damaged" }', '\tstate = { name = "burning" }',
                      f'\tscale = {escala:.5f}', '}'])


def emit(ctx: BuildContext) -> None:
    base = ctx.spec.root.parent.joinpath(*CARPETA)
    archivo = ctx.vanilla.root / "map" / "cities.txt" if ctx.vanilla else None
    if not base.is_dir() or archivo is None or not archivo.is_file():
        return
    texto = archivo.read_text(encoding="utf-8-sig", errors="replace")
    # las mallas del juego que se reemplazan, para medirlas
    originales = set()
    for i, j, color in grupos(texto):
        if color in ESTILO:
            for _a, _b, _d, mallas in niveles(texto[i:j]):
                originales |= set(mallas)
    mide = medidas_juego(ctx.vanilla.root, originales)
    ents, objetos, usadas, medidas, quedan = [], [], set(), [], []
    salida, ultimo = [], 0
    for i, j, color in grupos(texto):
        estilo = ESTILO.get(color)
        if not estilo:
            continue
        cuerpo = texto[i:j]
        nuevo, ult = [], 0
        for a, b, dist, mallas in niveles(cuerpo):
            tam = [mide[m] for m in mallas if m in mide]
            piezas = sorted(p for p in base.glob(f"mundo_manzana_{estilo}_{dist}_*") if p.is_dir())
            if not tam or not piezas:
                quedan.append(f"{estilo} {dist}")
                continue
            objetivo = sum(tam) / len(tam)
            nombres = []
            for p in piezas:
                malla = next(p.glob("gfx/models/**/*.mesh"))
                gfx = next(p.glob("gfx/entities/*.gfx")).read_text(encoding="utf-8-sig")
                nombre_malla = re.search(r'pdxmesh\s*=\s*\{\s*name\s*=\s*"([^"]+)"', gfx).group(1)
                ent = f"{p.name}_entity"
                if ent not in usadas:
                    usadas.add(ent)
                    ents.append(_entidad(ent, nombre_malla, objetivo / max(lado_mayor(malla), 1e-6)))
                    objetos.append(re.search(r"objectTypes\s*=\s*\{(.*)\}", gfx, re.S).group(1))
                    for f in sorted((p / "gfx" / "models").rglob("*")):
                        if f.is_file() and f.suffix != ".png":
                            ctx.copy_asset(f.relative_to(ctx.spec.root.parent).as_posix(), f.relative_to(p).as_posix())
                nombres.append(ent)
            medidas.append(f"{estilo} {dist}: {objetivo:.2f}")
            nuevo += [cuerpo[ult:a], "mesh = {\n\t\t\t" + "\n\t\t\t".join(f'"{n}"' for n in nombres) + "\n\t\t}"]
            ult = b
        nuevo.append(cuerpo[ult:])
        salida += [texto[ultimo:i], "".join(nuevo)]
        ultimo = j
    salida.append(texto[ultimo:])
    if not ents:
        ctx.warn("ciudades 2100: no se pudo medir ninguna manzana del juego; quedan las ciudades de siempre")
        return
    ctx.write_text("map/cities.txt", banner_for("map/cities.txt del juego con las manzanas del mundo 2100")
                   + "".join(salida))
    ctx.write_text("gfx/entities/meganations_manzanas_2100.asset",
                   banner_for("assets/mundo_2100/manzanas") + "\n\n".join(ents) + "\n")
    ctx.write_text("gfx/entities/meganations_manzanas_2100.gfx",
                   banner_for("assets/mundo_2100/manzanas (mallas)") + "objectTypes = {" + "\n".join(objetos) + "\n}\n")
    ctx.note(f"ciudades 2100: {len(ents)} manzanas en {len(medidas)} niveles; medida en el mapa (la de la manzana "
             f"del juego): {', '.join(medidas)}")
    if quedan:
        ctx.warn(f"ciudades 2100: quedan como en el juego (sin medida o sin manzana): {', '.join(quedan)}")
