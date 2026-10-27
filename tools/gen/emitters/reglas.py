"""Reglas de la partida (2026-10-27, captura del usuario: "fijate cómo cambiar
las reglas para adaptarlas al mod").

1. "Major Nation Buffs" (common/difficulty_settings): el juego trae un deslizador
   por cada potencia de 1936 (Alemania, Italia, la URSS...). Se reemplazan por
   uno por meganación, con el mismo modificador y multiplicador del juego. Cada
   archivo del juego se pisa con el mismo nombre; el primero lleva los ocho.
2. El reporte lista las reglas de common/game_rules que nombran países del juego
   base (comportamiento de la IA de Alemania, etc.): ahí no cambia nada sin
   preguntar, porque los scripts del juego las consultan.
"""

from __future__ import annotations

import re
from collections import Counter

from ..context import BuildContext
from ..pdx import Block, Quoted, parse_file, text as ptext

SOURCE = "tools/gen/emitters/reglas.py (pedido del usuario 2026-10-27)"
LOC_FILE = "meganations_reglas"


def emit(ctx: BuildContext) -> None:
    if ctx.vanilla is None:
        return
    _difficulty(ctx)
    _game_rules_report(ctx)


def _difficulty(ctx: BuildContext) -> None:
    folder = ctx.vanilla.root / "common" / "difficulty_settings"
    files = sorted(folder.glob("*.txt")) if folder.is_dir() else []
    if not files:
        ctx.warn("reglas: el juego no trae common/difficulty_settings; las potencias quedan sin deslizador propio")
        return
    modifiers, mults = Counter(), Counter()
    for path in files:
        try:
            root = parse_file(path)
        except ValueError:
            continue
        block = root.get("difficulty_settings")
        if not isinstance(block, Block):
            continue
        for k, v in block.entries:
            if k == "difficulty_setting" and isinstance(v, Block):
                if v.get("modifier") is not None:
                    modifiers[ptext(v.get("modifier"))] += 1
                if v.get("multiplier") is not None:
                    mults[ptext(v.get("multiplier"))] += 1
    modifier = modifiers.most_common(1)[0][0] if modifiers else "diff_strong_ai_generic"
    mult = float(mults.most_common(1)[0][0]) if mults else 2.0
    settings = Block()
    megas = [c for c in ctx.spec.countries if c.is_major]
    for c in megas:
        key = f"MEGANATIONS_fortalecer_{c.tag}"
        settings.add("difficulty_setting", Block([
            ("key", Quoted(key)), ("modifier", modifier), ("countries", Block([(None, c.tag)])),
            ("multiplier", mult)]))
        ctx.loc.define_and_reference(key, en=f"Strengthen {c.name_en}", es=f"Fortalecer: {c.name_es}",
                                     file=LOC_FILE, origin="reglas")
    for i, path in enumerate(files):
        body = settings if i == 0 else Block()
        ctx.write_script(f"common/difficulty_settings/{path.name}", Block([("difficulty_settings", body)]),
                         source=SOURCE + f" (pisa {path.name} del juego)")
    ctx.note(f"reglas: 'Major Nation Buffs' con las {len(megas)} meganaciones ({modifier} x{mult:g}); "
             f"{len(files)} archivo(s) del juego reemplazado(s)")


def _game_rules_report(ctx: BuildContext) -> None:
    folder = ctx.vanilla.root / "common" / "game_rules"
    if not folder.is_dir():
        return
    tags = set(ctx.vanilla.country_history_files()) - {c.tag for c in ctx.spec.countries}
    found = []
    for path in sorted(folder.glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for rid in re.findall(r"^([A-Za-z0-9_]+)\s*=\s*\{", text, re.MULTILINE):
            prefix = rid.split("_")[0]
            if prefix in tags:
                found.append(rid)
    if found:
        ctx.note(f"reglas: {len(found)} reglas del juego nombran paises de 1936 (quedan como estan): "
                 + ", ".join(found[:60]) + (" ..." if len(found) > 60 else ""))
