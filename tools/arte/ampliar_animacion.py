"""Exagera una animación de un modelo 3D propio para que se lea en el mapa (2026-11-23).

    python -m tools.arte.ampliar_animacion <archivo.anim> <factor> [hueso ...] [--tras <factor>]

El usuario (2026-11-23, EFE): "veo las animaciones de ataque viejas (esas casi estáticas)". Las .anim
nuevas sí estaban en el mod, pero el ataque es sutil: la torreta gira 7-9 grados y el cañón retrocede
0,2-0,26 de la malla (a la escala del mapa, 0,1), y en la infantería los brazos se mueven 4-11 grados.
A la distancia del mapa eso no se ve.

Cada hueso nombrado (o todos si no se nombra ninguno; un nombre que termina en * toma el prefijo
o el sufijo, ej. *_weapon) se aparta de su pose del primer cuadro `factor` veces más: giro
q' = q0 · (q0⁻¹ · q)^factor y traslado t' = t0 + factor_tras · (t − t0). El primer cuadro no cambia,
así que el ciclo sigue cerrando (el último cuadro es igual al primero).
"""

from __future__ import annotations

import fnmatch
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.gen import modelo3d  # noqa: E402


def _conj(q):
    x, y, z, w = q
    return (-x, -y, -z, w)


def _mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def _pot(q, f):
    """q^f para un cuaternión unitario (por el camino corto)."""
    x, y, z, w = q
    if w < 0:
        x, y, z, w = -x, -y, -z, -w
    s = math.sqrt(x * x + y * y + z * z)
    if s < 1e-9:
        return (0.0, 0.0, 0.0, 1.0)
    ang = math.atan2(s, w) * f
    k = math.sin(ang) / s
    return (x * k, y * k, z * k, math.cos(ang))


def ampliar(datos: bytes, factor: float, huesos: list[str] | None = None,
            factor_tras: float | None = None) -> tuple[bytes, list[str]]:
    a = modelo3d.Anim(datos)
    ft = factor if factor_tras is None else factor_tras
    nombres = [j.nombre for j in a.juntas()]
    elegidos = {n for n in nombres if not huesos or any(fnmatch.fnmatch(n, h) for h in huesos)}
    ancho = {"t": 3, "q": 4}
    for canal in ("t", "q"):
        if a.muestras is None or canal not in a.muestras.props:
            continue
        con = [j for j in a.juntas() if canal in modelo3d._sa(j)]
        n, w = len(con), ancho[canal]
        v = list(a.muestras.get(canal))
        for k, j in enumerate(con):
            if j.nombre not in elegidos:
                continue
            base = tuple(v[k * w:k * w + w])
            for f in range(1, a.cuadros):
                i = (f * n + k) * w
                cur = tuple(v[i:i + w])
                if canal == "t":
                    nuevo = [b + ft * (c - b) for b, c in zip(base, cur)]
                else:
                    nuevo = list(_mul(base, _pot(_mul(_conj(base), cur), factor)))
                v[i:i + w] = nuevo
        a.muestras.put(canal, v)
    return a.bytes(), sorted(elegidos)


if __name__ == "__main__":
    args = sys.argv[1:]
    ft = None
    if "--tras" in args:
        i = args.index("--tras")
        ft = float(args[i + 1])
        del args[i:i + 2]
    ruta, factor, huesos = Path(args[0]), float(args[1]), args[2:] or None
    nuevo, elegidos = ampliar(ruta.read_bytes(), factor, huesos, ft)
    ruta.write_bytes(nuevo)
    print(f"{ruta.name}: x{factor} en {len(elegidos)} huesos")
