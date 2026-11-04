"""Chequeo del inglés contra el glosario (spec/34_glosario.yaml).

Corre después de que todos los emisores definieron su texto y antes de
escribir los .yml. No frena el build: deja avisos en el reporte para que el
inglés no se atrase ni se desparrame en variantes.

  - variante a evitar: el inglés usa una traducción vieja de un término;
  - números distintos: los números del inglés y del castellano no coinciden
    (casi siempre, uno se cambió y el otro quedó viejo);
  - sin traducir: un texto de varias palabras es idéntico en los dos idiomas
    y tiene palabras del castellano.

Los textos del juego base que reescribe vanilla_terms (archivos replace/) no
se revisan: no son nuestros.
"""

from __future__ import annotations

import re
from collections import Counter

import yaml

from .context import BuildContext

GLOSARIO_FILE = "34_glosario.yaml"

# Lo que no es texto: colores, variables, comandos y saltos de línea.
_MARKUP = re.compile(r"§.|\$[^$]*\$|\[[^\]]*\]|£[^£]*£|\\n")
_NUMBER = re.compile(r"\d[\d.,]*\d|\d")
_SPANISH = re.compile(r"\b(de|del|los|las|que|para|con|una|pero|cuando)\b", re.IGNORECASE)
MAX_EJEMPLOS = 5


def load(spec_root) -> dict:
    path = spec_root / GLOSARIO_FILE
    if not path.exists():
        return {}
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("glosario") or {}


def _numbers(text: str) -> Counter:
    plain = _MARKUP.sub(" ", text)
    return Counter(n.replace(",", "").replace(".", "") for n in _NUMBER.findall(plain))


def revisar(textos, glosario: dict) -> dict[str, list[str]]:
    """textos: iterable de (clave, archivo, inglés, castellano).

    Devuelve {tipo de problema: [claves]}; vacío si todo está en orden.
    """
    evitar = []
    for t in glosario.get("terminos") or []:
        variantes = t.get("evitar") or []
        if isinstance(variantes, list):
            variantes = {v: t["en"] for v in variantes}
        for variante, oficial in variantes.items():
            rx = re.compile(rf"(?<![\w-]){re.escape(variante)}(?![\w-])")
            evitar.append((variante, oficial, rx))
    a_proposito = set(glosario.get("numeros_distintos_a_proposito") or [])
    iguales = set(glosario.get("iguales_a_proposito") or [])

    problemas: dict[str, list[str]] = {}
    for key, archivo, en, es in textos:
        if archivo.startswith("replace/"):
            continue
        for variante, oficial, rx in evitar:
            if rx.search(en):
                problemas.setdefault(f"'{variante}' en vez de '{oficial}'", []).append(key)
        if key not in a_proposito and _numbers(en) != _numbers(es):
            problemas.setdefault("números distintos entre inglés y castellano", []).append(key)
        plain = _MARKUP.sub(" ", en).strip()
        if en == es and key not in iguales and len(plain.split()) >= 4 and _SPANISH.search(plain):
            problemas.setdefault("texto sin traducir (igual en los dos idiomas)", []).append(key)
    return problemas


def check(ctx: BuildContext) -> None:
    glosario = load(ctx.spec.root)
    if not glosario:
        return
    problemas = revisar(ctx.loc.texts(), glosario)
    n_terminos = len(glosario.get("terminos") or [])
    if not problemas:
        ctx.note(f"glosario: {n_terminos} términos, el inglés no tiene variantes viejas ni números distintos")
        return
    for tipo, claves in sorted(problemas.items()):
        ejemplos = ", ".join(sorted(claves)[:MAX_EJEMPLOS])
        mas = f" y {len(claves) - MAX_EJEMPLOS} más" if len(claves) > MAX_EJEMPLOS else ""
        ctx.warn(f"glosario: {tipo} en {len(claves)} texto(s): {ejemplos}{mas}")
