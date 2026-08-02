"""Lectura y escritura de Paradox script (el formato .txt de HOI4).

Se necesitan las dos direcciones:

  - ESCRITURA: es lo que produce el mod.
  - LECTURA:   hace falta para la estrategia reskin_groups de ideologías, que
               parte del archivo vanilla en vez de escribirlo de cero, y para
               resolver nombres de state a IDs numéricos.

El formato es simple pero tiene trampas: los duplicados de clave son legales y
significativos (`types = {}` puede aparecer varias veces), así que el modelo de
datos es una lista de pares, nunca un dict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, Union

Value = Union[str, int, float, "Block"]


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------


@dataclass
class Block:
    """Un bloque `{ ... }`.

    `entries` es una lista de pares (clave, valor). Clave `None` significa un
    elemento suelto de lista, como en `color = { 45 84 41 }`.
    """

    entries: list[tuple[str | None, Value]] = field(default_factory=list)

    def add(self, key: str | None, value: Value) -> "Block":
        self.entries.append((key, value))
        return self

    def add_all(self, key: str | None, values) -> "Block":
        for v in values:
            self.entries.append((key, v))
        return self

    def get(self, key: str) -> Value | None:
        for k, v in self.entries:
            if k == key:
                return v
        return None

    def get_all(self, key: str) -> list[Value]:
        return [v for k, v in self.entries if k == key]

    def keys(self) -> list[str]:
        return [k for k, _ in self.entries if k is not None]

    def __contains__(self, key: str) -> bool:
        return key in self.keys()

    def __iter__(self) -> Iterator[tuple[str | None, Value]]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)


def text(value) -> str | None:
    """Desenvuelve un valor a str plano, venga entrecomillado o no."""
    if value is None:
        return None
    if isinstance(value, Quoted):
        return str(value.text)
    if isinstance(value, Block):
        raise TypeError("un Block no es un escalar")
    return str(value)


def block(*entries: tuple[str | None, Value]) -> Block:
    return Block(list(entries))


def inline_list(*values) -> Block:
    """`{ 45 84 41 }` — un bloque de elementos sueltos sin clave."""
    b = Block()
    for v in values:
        b.add(None, v)
    return b


# ---------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------

_BARE_TOKEN = re.compile(r"^[A-Za-z0-9_.:@\[\]-]+$")


@dataclass
class Quoted:
    """Fuerza comillas aunque el valor sea un token válido sin ellas.

    descriptor.mod entrecomilla name, version y supported_version incluso
    cuando no haría falta.
    """

    text: str


def _fmt_scalar(value) -> str:
    if isinstance(value, Quoted):
        return '"' + str(value.text).replace('"', '\\"') + '"'
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        # HOI4 quiere punto decimal y sin notación científica.
        text = f"{value:.3f}".rstrip("0")
        return text + "0" if text.endswith(".") else text
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if _BARE_TOKEN.match(text):
        return text
    return '"' + text.replace('"', '\\"') + '"'


def _is_short_inline(b: Block) -> bool:
    """Bloques cortos de escalares sueltos van en una línea: `{ 45 84 41 }`."""
    if len(b) == 0 or len(b) > 6:
        return False
    return all(k is None and not isinstance(v, Block) for k, v in b.entries)


def write_block(b: Block, indent: int = 0) -> str:
    """Serializa el contenido de un bloque (sin las llaves externas)."""
    pad = "\t" * indent
    lines: list[str] = []
    for key, value in b.entries:
        if isinstance(value, Block):
            if _is_short_inline(value):
                inner = " ".join(_fmt_scalar(v) for _, v in value.entries)
                lines.append(f"{pad}{key} = {{ {inner} }}" if key else f"{pad}{{ {inner} }}")
            elif len(value) == 0:
                lines.append(f"{pad}{key} = {{ }}" if key else f"{pad}{{ }}")
            else:
                lines.append(f"{pad}{key} = {{" if key else f"{pad}{{")
                lines.append(write_block(value, indent + 1))
                lines.append(f"{pad}}}")
        elif key is None:
            lines.append(f"{pad}{_fmt_scalar(value)}")
        elif isinstance(value, Comment):
            lines.append(f"{pad}# {value.text}")
        else:
            lines.append(f"{pad}{key} = {_fmt_scalar(value)}")
    return "\n".join(lines)


@dataclass
class Comment:
    text: str


def comment(text: str) -> tuple[None, "Comment"]:
    return (None, Comment(text))


def _write_entry_line(pad: str, key, value) -> str:
    return f"{pad}{key} = {_fmt_scalar(value)}"


def render(b: Block) -> str:
    """Serializa un bloque raíz a texto listo para escribir a disco."""
    out: list[str] = []
    for key, value in b.entries:
        if isinstance(value, Comment):
            out.append(f"# {value.text}" if value.text else "")
            continue
        sub = Block([(key, value)])
        out.append(write_block(sub, 0))
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"""
      \#[^\n]*                 # comentario
    | "(?:[^"\\]|\\.)*"        # string entre comillas
    | [{}]                     # llaves
    | [<>!]?=|<|>              # operadores
    | [^\s{}=<>#"]+            # token pelado
    """,
    re.VERBOSE,
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text) if not t.startswith("#")]


def parse(text: str) -> Block:
    """Parsea Paradox script a un Block.

    Deliberadamente tolerante: acepta los operadores de comparación (`<`, `>=`)
    tratándolos como `=`, porque no necesitamos evaluarlos, solo preservarlos al
    releer archivos vanilla.
    """
    tokens = tokenize(text)
    pos = 0

    def unquote(tok: str):
        """Preserva si el token venía entrecomillado.

        Importa para el merge de ideologías: reescribimos contenido vanilla que
        no escribimos nosotros, y quitarle las comillas a algo como
        `dynamic_faction_names = { "FACTION_NAME_FASCIST_1" }` cambia un archivo
        del juego sin necesidad. Al releer, un valor entrecomillado vuelve como
        Quoted y se re-emite igual que estaba.
        """
        if len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"':
            return Quoted(tok[1:-1].replace('\\"', '"'))
        return tok

    def parse_block(depth: int) -> Block:
        nonlocal pos
        b = Block()
        while pos < len(tokens):
            tok = tokens[pos]
            if tok == "}":
                if depth == 0:
                    raise ValueError("'}' sin apertura")
                pos += 1
                return b
            if tok == "{":
                pos += 1
                b.add(None, parse_block(depth + 1))
                continue
            # ¿es `clave = valor` o un elemento suelto?
            if pos + 1 < len(tokens) and tokens[pos + 1] in ("=", "==", ">=", "<=", "<", ">", "!="):
                key = unquote(tok)
                pos += 2
                if pos >= len(tokens):
                    raise ValueError(f"'{key} =' sin valor")
                if tokens[pos] == "{":
                    pos += 1
                    b.add(key, parse_block(depth + 1))
                else:
                    b.add(key, unquote(tokens[pos]))
                    pos += 1
            else:
                b.add(None, unquote(tok))
                pos += 1
        if depth != 0:
            raise ValueError("'{' sin cerrar")
        return b

    return parse_block(0)


def parse_file(path) -> Block:
    from pathlib import Path

    raw = Path(path).read_bytes()
    # Los archivos de Paradox vienen en UTF-8, a veces con BOM, a veces en
    # latin-1 heredado. Degradamos con cuidado en vez de reventar.
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return parse(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"no se pudo decodificar {path}")


BANNER = (
    "########################################################################\n"
    "#  ARCHIVO GENERADO - NO EDITAR A MANO\n"
    "#\n"
    "#  Producido por tools/gen a partir de spec/. Cualquier cambio manual\n"
    "#  se pierde en la proxima regeneracion.\n"
    "#  Para cambiar esto, edita el spec y corre:  make build\n"
    "#\n"
    "#  Fuente: {source}\n"
    "########################################################################\n\n"
)


def banner_for(source: str) -> str:
    return BANNER.format(source=source)
