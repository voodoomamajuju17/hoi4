"""Arreglos de los modelos 3D propios al armar el mod (2026-11-13).

Del error.log y las capturas del usuario (1.19.5): "Mesh "NRE_tanque_medio_mesh" has too many joints!
( 100 / 50 )", la infantería que "flashea", todo muy oscuro y tamaños fuera de escala. Acá:

- huesos: el juego no anima mallas con más de 50 huesos. Se juntan con su padre los huesos hoja que
  menos se apartan de él en las animaciones (ruedas, pernos, antenas) hasta quedar en 50; los vértices
  pasan al padre y el hueso sale también de las animaciones de la misma carpeta.
- animaciones: los cuaterniones de un hueso que cambian de signo entre un cuadro y el siguiente
  (q y -q son el mismo giro, pero al interpolar dan una vuelta entera de golpe) quedan del mismo signo.
- sombreado: las texturas siguen la convención de PdxMeshAdvanced (normal en RRxG, especular en G,
  metal en B, brillo en A), como la infantería del juego. Con PdxMeshStandard la normal sale invertida y
  el modelo se ve negro; se pasa a PdxMeshAdvanced.
- tamaño: medida mayor de la malla (alto, largo o envergadura según el tipo) para la escala.
"""

from __future__ import annotations

import math
import re

from . import pdxbin

MAX_HUESOS = 50
SHADERS = {b"PdxMeshStandard\0": b"PdxMeshAdvanced\0", b"PdxMeshStandard": b"PdxMeshAdvanced"}


# -- álgebra mínima (sin numpy: el armado corre en la máquina del usuario) ---------------------

def _inv(m):
    """Inversa de una afín 3x4 dada como 4 columnas de 3 (como guarda el .mesh la inversa de bind)."""
    (a, d, g), (b, e, h), (c, f, i), t = m[0:3], m[3:6], m[6:9], m[9:12]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-12:
        return None
    r = [[(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
         [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
         [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det]]
    tt = [-sum(r[k][j] * t[j] for j in range(3)) for k in range(3)]
    return [r[0][0], r[1][0], r[2][0], r[0][1], r[1][1], r[2][1], r[0][2], r[1][2], r[2][2]] + tt


def _mul(a, b):
    """a * b para afines en columnas."""
    def col(m, j):
        return m[3 * j:3 * j + 3]
    ra = [[a[3 * j + k] for j in range(3)] for k in range(3)]   # filas de a
    out = []
    for j in range(3):
        c = col(b, j)
        out += [sum(ra[k][x] * c[x] for x in range(3)) for k in range(3)]
    t = b[9:12]
    out += [sum(ra[k][x] * t[x] for x in range(3)) + a[9 + k] for k in range(3)]
    return out


def _quat(m):
    """Cuaternión (x, y, z, w) de la parte de giro (normalizada) de una afín en columnas."""
    cols = [m[0:3], m[3:6], m[6:9]]
    esc = [math.sqrt(sum(v * v for v in c)) or 1.0 for c in cols]
    r = [[cols[j][k] / esc[j] for j in range(3)] for k in range(3)]
    tr = r[0][0] + r[1][1] + r[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        return ((r[2][1] - r[1][2]) / s, (r[0][2] - r[2][0]) / s, (r[1][0] - r[0][1]) / s, 0.25 * s), esc
    if r[0][0] > r[1][1] and r[0][0] > r[2][2]:
        s = math.sqrt(1.0 + r[0][0] - r[1][1] - r[2][2]) * 2
        return (0.25 * s, (r[0][1] + r[1][0]) / s, (r[0][2] + r[2][0]) / s, (r[2][1] - r[1][2]) / s), esc
    if r[1][1] > r[2][2]:
        s = math.sqrt(1.0 + r[1][1] - r[0][0] - r[2][2]) * 2
        return ((r[0][1] + r[1][0]) / s, 0.25 * s, (r[1][2] + r[2][1]) / s, (r[0][2] - r[2][0]) / s), esc
    s = math.sqrt(1.0 + r[2][2] - r[0][0] - r[1][1]) * 2
    return ((r[0][2] + r[2][0]) / s, (r[1][2] + r[2][1]) / s, 0.25 * s, (r[1][0] - r[0][1]) / s), esc


def _angulo(q1, q2) -> float:
    d = abs(sum(a * b for a, b in zip(q1, q2)))
    n = math.sqrt(sum(a * a for a in q1) * sum(b * b for b in q2)) or 1.0
    return 2 * math.acos(min(1.0, d / n))


# -- animaciones -----------------------------------------------------------------------------

def _sa(junta: pdxbin.Nodo) -> str:
    v = junta.get("sa", [b""])
    return v[0].rstrip(b"\0").decode("latin-1") if v else ""


class Anim:
    def __init__(self, datos: bytes):
        self.raiz = pdxbin.leer(datos)
        self.info = next(n for n in self.raiz.todos() if n.nombre == "info")
        self.muestras = next((n for n in self.raiz.todos() if n.nombre == "samples"), None)
        self.cuadros = int(self.info.get("sa", [0])[0])

    def juntas(self):
        return self.info.hijos

    def pistas(self):
        """{nombre: {"t": [(x,y,z) por cuadro], "q": ..., "s": ...}} con los valores fijos si no hay pista."""
        out = {j.nombre: {} for j in self.juntas()}
        datos = {k: (self.muestras.get(k, []) if self.muestras else []) for k in "tqs"}
        ancho = {"t": 3, "q": 4, "s": 1}
        for canal in "tqs":
            con = [j for j in self.juntas() if canal in _sa(j)]
            n, w = len(con), ancho[canal]
            for k, j in enumerate(con):
                out[j.nombre][canal] = [tuple(datos[canal][(f * n + k) * w:(f * n + k) * w + w])
                                        for f in range(self.cuadros)]
            for j in self.juntas():
                if canal not in out[j.nombre]:
                    out[j.nombre][canal] = [tuple(j.get(canal, [0, 0, 0, 1][:w] if canal != "s" else [1]))]
        return out

    def arreglar_signos(self) -> int:
        """Mismo signo de cuaternión entre cuadros seguidos de cada hueso. Devuelve cuántos cambió."""
        if not self.muestras or "q" not in self.muestras.props:
            return 0
        q = list(self.muestras.get("q"))
        con = [j for j in self.juntas() if "q" in _sa(j)]
        n, cambios = len(con), 0
        for k in range(n):
            for f in range(1, self.cuadros):
                a, b = (f - 1) * n + k, f * n + k
                if sum(q[a * 4 + i] * q[b * 4 + i] for i in range(4)) < 0:
                    for i in range(4):
                        q[b * 4 + i] = -q[b * 4 + i]
                    cambios += 1
        self.muestras.put("q", q)
        return cambios

    def quitar(self, nombres: set[str]) -> None:
        if not nombres:
            return
        ancho = {"t": 3, "q": 4, "s": 1}
        if self.muestras:
            for canal in "tqs":
                if canal not in self.muestras.props:
                    continue
                con = [j for j in self.juntas() if canal in _sa(j)]
                n, w = len(con), ancho[canal]
                quedan = [k for k, j in enumerate(con) if j.nombre not in nombres]
                v = self.muestras.get(canal)
                nuevo = []
                for f in range(self.cuadros):
                    for k in quedan:
                        nuevo += v[(f * n + k) * w:(f * n + k) * w + w]
                self.muestras.put(canal, nuevo)
        self.info.hijos = [j for j in self.juntas() if j.nombre not in nombres]
        if "j" in self.info.props:
            self.info.put("j", [len(self.info.hijos)], "i")

    def bytes(self) -> bytes:
        return pdxbin.escribir(self.raiz)


FAMILIA = 6     # desde cuántas piezas iguales se toma como familia (orugas, ruedas)


def familia(nombre: str) -> str:
    """'shoeR12', 'shoeL3' -> 'shoe'; 'LRoll_2' -> 'roll'; 'track40' -> 'track'."""
    s = re.sub(r"[\d_.]+$", "", nombre)
    s = re.sub(r"(?<=[a-z])[LR]$", "", s)
    s = re.sub(r"^[LR](?=[A-Z])", "", s)
    return s.lower()


# -- mallas ----------------------------------------------------------------------------------

class Malla:
    def __init__(self, datos: bytes):
        self.raiz = pdxbin.leer(datos)

    def esqueletos(self):
        return [n for n in self.raiz.todos() if n.nombre == "skeleton"]

    def formas(self):
        """(malla, piel) de cada pieza de la malla."""
        for n in self.raiz.todos():
            if n.nombre == "mesh":
                yield n, n.hijo("skin")

    def huesos(self) -> int:
        return max((len(s.hijos) for s in self.esqueletos()), default=0)

    def medida(self) -> tuple[float, float, float]:
        mn, mx = [math.inf] * 3, [-math.inf] * 3
        for m, _ in self.formas():
            caja = m.hijo("aabb")
            if caja is None:
                continue
            for i in range(3):
                mn[i] = min(mn[i], caja.get("min")[i])
                mx[i] = max(mx[i], caja.get("max")[i])
        return tuple((mx[i] - mn[i]) if mx[i] > mn[i] else 0.0 for i in range(3))

    def sombreado_avanzado(self) -> bool:
        cambio = False
        for n in self.raiz.todos():
            if n.nombre == "material" and "shader" in n.props:
                v = [SHADERS.get(s, s) for s in n.get("shader")]
                if v != n.get("shader"):
                    n.put("shader", v, "s")
                    cambio = True
        return cambio

    def bytes(self) -> bytes:
        return pdxbin.escribir(self.raiz)

    # el recorte -------------------------------------------------------------------------------

    def recortar(self, anims: list[Anim], maximo: int = MAX_HUESOS) -> list[str]:
        """Junta huesos hoja con su padre hasta dejar `maximo`. Devuelve los nombres quitados."""
        quitados: list[str] = []
        pistas = [a.pistas() for a in anims]
        for esq in self.esqueletos():
            if len(esq.hijos) <= maximo:
                continue
            juntas = esq.hijos
            por_ix = {int(j.get("ix")[0]): j for j in juntas}
            padre = {int(j.get("ix")[0]): int(j.get("pa")[0]) for j in juntas if "pa" in j.props}
            inv = {i: j.get("tx") for i, j in por_ix.items()}
            mundo = {i: _inv(m) for i, m in inv.items()}
            # vértices de cada hueso (de todas las piezas que usan este esqueleto)
            pos_por_hueso: dict[int, list[tuple[float, float, float]]] = {i: [] for i in por_ix}
            for m, piel in self.formas():
                if piel is None:
                    continue
                p, ix, w = m.get("p"), piel.get("ix"), piel.get("w")
                for v in range(len(p) // 3):
                    for k in range(4):
                        b = ix[v * 4 + k]
                        if b >= 0 and w[v * 4 + k] > 0 and b in pos_por_hueso:
                            pos_por_hueso[b].append(tuple(p[v * 3:v * 3 + 3]))

            def radio(i: int) -> float:
                o = mundo[i][9:12] if mundo[i] else (0, 0, 0)
                return max((math.dist(o, q) for q in pos_por_hueso[i]), default=0.0)

            def desvio(i: int) -> float:
                """Lo más que el hueso se aparta de su lugar de reposo respecto del padre."""
                if i not in padre or mundo[i] is None:
                    return math.inf
                local = _mul(inv[padre[i]], mundo[i])
                qb, eb = _quat(local)
                tb = local[9:12]
                nombre = por_ix[i].nombre
                r, peor = radio(i), 0.0
                for pi in pistas:
                    if nombre not in pi:
                        continue
                    ts, qs, ss = pi[nombre]["t"], pi[nombre]["q"], pi[nombre]["s"]
                    for f in range(max(len(ts), len(qs), len(ss))):
                        t, q, s = ts[min(f, len(ts) - 1)], qs[min(f, len(qs) - 1)], ss[min(f, len(ss) - 1)]
                        e = math.dist(t, tb) + _angulo(q, qb) * r + abs(s[0] - eb[0]) * r
                        peor = max(peor, e)
                return peor

            costo = {i: desvio(i) for i in por_ix}
            arrastre = {i: 0.0 for i in por_ix}      # error que ya cargan los vértices del hueso
            vivos = set(por_ix)
            destino = {i: i for i in por_ix}

            def juntar(i: int) -> None:
                p = padre[i]
                arrastre[p] = max(arrastre[p], arrastre[i] + costo[i])
                pos_por_hueso[p] += pos_por_hueso[i]
                vivos.discard(i)
                destino[i] = p
                quitados.append(por_ix[i].nombre)

            # primero las piezas repetidas (eslabones de oruga, ruedas): la familia entera queda quieta
            # respecto de su padre; con algunos eslabones moviéndose y otros no, se pisarían
            while len(vivos) > maximo:
                hijos = {padre[i] for i in vivos if i in padre}
                familias: dict[str, list[int]] = {}
                for i in vivos:
                    if i in padre and i not in hijos:
                        familias.setdefault(familia(por_ix[i].nombre), []).append(i)
                grandes = [f for f in familias.values() if len(f) >= FAMILIA]
                if not grandes:
                    break
                for i in max(grandes, key=lambda f: (len(f), -min(f))):
                    juntar(i)
            while len(vivos) > maximo:
                hijos = {padre[i] for i in vivos if i in padre}
                hojas = [i for i in vivos if i in padre and i not in hijos]
                if not hojas:
                    break
                juntar(min(hojas, key=lambda h: (costo[h] + arrastre[h], len(pos_por_hueso[h]), h)))

            def final(i: int) -> int:
                while destino[i] != i:
                    i = destino[i]
                return i
            nuevo = {viejo: k for k, viejo in enumerate(sorted(vivos))}
            for m, piel in self.formas():
                if piel is None:
                    continue
                ix, w = list(piel.get("ix")), list(piel.get("w"))
                for v in range(len(ix) // 4):
                    vistos: dict[int, int] = {}
                    for k in range(v * 4, v * 4 + 4):
                        if ix[k] < 0 or ix[k] not in destino:
                            continue
                        b = nuevo[final(ix[k])]
                        if b in vistos:              # el padre ya estaba: se suman los pesos
                            w[vistos[b]] += w[k]
                            w[k] = 0.0
                        else:
                            vistos[b] = k
                        ix[k] = b
                piel.put("ix", ix, "i")
                piel.put("w", w, "f")
            esq.hijos = [j for j in juntas if int(j.get("ix")[0]) in vivos]
            for j in esq.hijos:
                j.put("ix", [nuevo[int(j.get("ix")[0])]], "i")
                if "pa" in j.props:
                    j.put("pa", [nuevo[int(j.get("pa")[0])]], "i")
        for a in anims:
            a.quitar(set(quitados))
        return quitados


def arreglar_carpeta(malla: bytes, anims: dict[str, bytes], maximo: int = MAX_HUESOS) -> tuple[bytes, dict[str, bytes], dict]:
    """Malla y animaciones de una carpeta, arregladas. Devuelve también un resumen."""
    m = Malla(malla)
    a = {k: Anim(v) for k, v in anims.items()}
    antes = m.huesos()
    quitados = m.recortar(list(a.values()), maximo)
    signos = sum(x.arreglar_signos() for x in a.values())
    sombra = m.sombreado_avanzado()
    return m.bytes(), {k: v.bytes() for k, v in a.items()}, {
        "huesos": (antes, m.huesos()), "quitados": quitados, "signos": signos, "sombreado": sombra,
        "medida": m.medida()}
