"""Parte el tren de carga del mundo 2100 en motriz y vagones (2026-11-25).

    python -m tools.arte.partir_tren

El juego (DLC No Step Back, gfx/models/units/trains/) arma cada tren que circula por las vías con una locomotora
(<TAG>_train_locomotive_equipment_N_entity) y vagones (<TAG>_train_coal_equipment_N_entity) en fila, cada pieza
con la punta en el origen y el cuerpo hacia -Z. Nuestro mundo_tren_suministro vino entero (motriz y tres vagones
en una malla, cada coche pegado a su hueso: motriz, vagon_1, vagon_2, vagon_3). Esto lo separa: cada coche a su
propia malla fija (sin esqueleto), con la punta en el origen como los del juego, y deja las mallas junto a la
original en assets/mundo_2100/trenes/mundo_tren_suministro/gfx/models/units/trains/.
"""

from __future__ import annotations

import copy
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tools.gen import pdxbin  # noqa: E402

PIEZA = REPO / "assets" / "mundo_2100" / "trenes" / "mundo_tren_suministro"
COCHES = {"motriz": "mundo_tren_motriz", "vagon_1": "mundo_tren_vagon_1", "vagon_2": "mundo_tren_vagon_2",
          "vagon_3": "mundo_tren_vagon_3"}


def partir(datos: bytes) -> dict[str, bytes]:
    raiz = pdxbin.leer(datos)
    forma = next(n for n in raiz.todos() if n.nombre.endswith("Shape"))
    mesh = forma.hijo("mesh")
    skin = mesh.hijo("skin")
    esqueleto = forma.hijo("skeleton")
    huesos = {j.get("ix")[0]: j.nombre for j in esqueleto.hijos}
    bpv = skin.get("bones")[0]
    ix, w = skin.get("ix"), skin.get("w")
    p = mesh.get("p")
    nv = len(p) // 3
    coche = [huesos[ix[v * bpv + max(range(bpv), key=lambda k: w[v * bpv + k])]] for v in range(nv)]
    tri = mesh.get("tri")
    out = {}
    for hueso, nombre in COCHES.items():
        caras = [tri[i:i + 3] for i in range(0, len(tri), 3) if all(coche[v] == hueso for v in tri[i:i + 3])]
        usados = sorted({v for c in caras for v in c})
        nuevo = {v: k for k, v in enumerate(usados)}
        zmax = max(p[v * 3 + 2] for v in usados)
        r = copy.deepcopy(raiz)
        f2 = next(n for n in r.todos() if n.nombre.endswith("Shape"))
        f2.hijos = [h for h in f2.hijos if h.nombre != "skeleton"]
        m2 = f2.hijo("mesh")
        m2.hijos = [h for h in m2.hijos if h.nombre != "skin"]

        def sub(clave: str, ancho: int) -> None:
            if clave in m2.props:
                datos_v = m2.get(clave)
                m2.put(clave, [x for v in usados for x in datos_v[v * ancho:(v + 1) * ancho]])
        pos = [x for v in usados for x in (p[v * 3], p[v * 3 + 1], p[v * 3 + 2] - zmax)]   # la punta en z = 0
        m2.put("p", pos)
        for clave, ancho in (("n", 3), ("ta", 4), ("u0", 2), ("u1", 2)):
            sub(clave, ancho)
        m2.put("tri", [nuevo[v] for c in caras for v in c], "i")
        mn = [min(pos[a::3]) for a in range(3)]
        mx = [max(pos[a::3]) for a in range(3)]
        caja = m2.hijo("aabb")
        caja.put("min", mn)
        caja.put("max", mx)
        centro = [(a + b) / 2 for a, b in zip(mn, mx)]
        radio = max(math.dist(centro, pos[i:i + 3]) for i in range(0, len(pos), 3))
        if "boundingsphere" in m2.props:
            m2.put("boundingsphere", centro + [radio])
        out[nombre] = pdxbin.escribir(r)
    return out


def main() -> int:
    original = next(PIEZA.glob("gfx/models/**/mundo_tren_suministro.mesh"))
    for nombre, datos in partir(original.read_bytes()).items():
        destino = original.parent / f"{nombre}.mesh"
        destino.write_bytes(datos)
        print(f"{destino.relative_to(REPO)}: {len(datos)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
