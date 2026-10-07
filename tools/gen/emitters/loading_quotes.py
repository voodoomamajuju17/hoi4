"""Frases de la pantalla de carga (spec/11_scenario.yaml -> loading_quotes).

2026-10-07 (pedido del usuario): las citas del juego (Patton, Churchill...) se
reemplazan por voces de 2100. No se adivina el nombre de las claves: se buscan
en el juego instalado las claves de pantalla de carga (con "loading" o "quote"
en el nombre) cuyo texto termina en una firma ("\\n- Autor"), y se pisan todas
repitiendo la lista del spec. El reporte dice cuántas y cuáles.
"""

from __future__ import annotations

import re

from ..context import BuildContext

FILE = "replace/meganations_loading_quotes"
_NAME = re.compile(r"(?i)(loading|quote)")
_SIGNED = re.compile(r"(\\n|\n)\s*-\s*\S")


def emit(ctx: BuildContext) -> None:
    spec = ctx.spec.raw.get("scenario", {}).get("loading_quotes") or {}
    quotes = spec.get("quotes") or []
    if not quotes or ctx.vanilla is None:
        return
    en_names = spec.get("authors_en") or {}
    english = ctx.vanilla.all_localisation("english")
    keys = sorted(k for k, v in english.items() if _NAME.search(k) and _SIGNED.search(v))
    taken = set(getattr(ctx.loc, "_defined", {}))
    keys = [k for k in keys if k not in taken]
    if not keys:
        ctx.warn("pantalla de carga: no encontre las citas del juego (claves con 'loading'/'quote' firmadas); quedan las originales.")
        return
    # orden mezclado (fijo entre builds) para que no salgan seguidas las del mismo autor
    import random
    quotes = list(quotes)
    random.Random(2100).shuffle(quotes)
    for i, key in enumerate(keys):
        q = quotes[i % len(quotes)]
        author = q["author"]
        ctx.loc.define_and_reference(
            key, en=f"{q['en']}\\n- {q.get('author_en') or en_names.get(author, author)}", es=f"{q['es']}\\n- {author}",
            file=FILE, origin="loading_quotes")
    ctx.note(f"pantalla de carga: {len(keys)} citas del juego reemplazadas por {len(quotes)} frases de 2100 "
             f"(ej. {', '.join(keys[:3])})")
