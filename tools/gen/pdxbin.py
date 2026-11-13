"""Lectura y escritura de los .mesh y .anim binarios de Clausewitz (formato "@@b@").

Estructura: tras la cabecera vienen propiedades `!<largo><nombre><tipo><cantidad><datos>` (tipo i, f o s)
y objetos `[`*profundidad + nombre terminado en NUL. Las propiedades de un objeto van antes que sus hijos.
Se guarda todo tal cual (las cadenas con sus bytes) para que leer y volver a escribir dé el mismo archivo.
"""

from __future__ import annotations

import struct


class Nodo:
    __slots__ = ("nombre", "props", "hijos")

    def __init__(self, nombre: str):
        self.nombre = nombre
        self.props: dict[str, tuple[str, list]] = {}
        self.hijos: list[Nodo] = []

    def hijo(self, nombre: str) -> "Nodo | None":
        return next((h for h in self.hijos if h.nombre == nombre), None)

    def todos(self):
        yield self
        for h in self.hijos:
            yield from h.todos()

    def get(self, clave: str, defecto=None):
        return self.props[clave][1] if clave in self.props else defecto

    def put(self, clave: str, valor: list, tipo: str | None = None) -> None:
        tipo = tipo or (self.props[clave][0] if clave in self.props else "f")
        self.props[clave] = (tipo, valor)


def leer(datos: bytes) -> Nodo:
    if datos[:4] != b"@@b@":
        raise ValueError("no es un archivo binario de Clausewitz")
    raiz = Nodo("")
    pila = [raiz]
    i = 4
    while i < len(datos):
        c = datos[i]
        if c == 0x21:                       # '!'
            n = datos[i + 1]
            nombre = datos[i + 2:i + 2 + n].decode("latin-1")
            i += 2 + n
            tipo = chr(datos[i])
            cnt = struct.unpack_from("<I", datos, i + 1)[0]
            i += 5
            if tipo in "if":
                v = list(struct.unpack_from(f"<{cnt}{tipo}", datos, i))
                i += 4 * cnt
            elif tipo == "s":
                v = []
                for _ in range(cnt):
                    largo = struct.unpack_from("<I", datos, i)[0]
                    v.append(datos[i + 4:i + 4 + largo])
                    i += 4 + largo
            else:
                raise ValueError(f"tipo de propiedad desconocido {tipo!r} en {i}")
            pila[-1].props[nombre] = (tipo, v)
        elif c == 0x5B:                     # '['
            prof = 0
            while datos[i] == 0x5B:
                prof += 1
                i += 1
            fin = datos.index(b"\0", i)
            nodo = Nodo(datos[i:fin].decode("latin-1"))
            i = fin + 1
            del pila[prof:]
            pila[-1].hijos.append(nodo)
            pila.append(nodo)
        else:
            raise ValueError(f"byte inesperado {c} en {i}")
    return raiz


def escribir(raiz: Nodo) -> bytes:
    out = bytearray(b"@@b@")

    def props(nodo: Nodo) -> None:
        for nombre, (tipo, v) in nodo.props.items():
            b = nombre.encode("latin-1")
            out.extend(b"!" + bytes([len(b)]) + b + tipo.encode() + struct.pack("<I", len(v)))
            if tipo in "if":
                out.extend(struct.pack(f"<{len(v)}{tipo}", *v))
            else:
                for s in v:
                    out.extend(struct.pack("<I", len(s)) + s)

    def nodo(n: Nodo, prof: int) -> None:
        out.extend(b"[" * prof + n.nombre.encode("latin-1") + b"\0")
        props(n)
        for h in n.hijos:
            nodo(h, prof + 1)

    props(raiz)
    for h in raiz.hijos:
        nodo(h, 1)
    return bytes(out)
