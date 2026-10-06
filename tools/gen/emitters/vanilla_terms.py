"""Textos del juego base con las ideologías viejas (2026-10-03, captura del
usuario: "Entrenamiento paramilitar" decía "Apoyo fascista diario").

Los cuatro grupos vanilla del mod se renombraron (01_ideologies: Restauración,
Colectivismo, Orden de Mercado, Mandato Trascendente), pero muchos textos del
juego que siguen en uso (decisiones e ideas genéricas, modificadores, asesores,
tooltips) nombran "fascista", "comunista", "democrático" o "no alineado"
escritos a mano. También el carbón, que en 2100 se llama Torio (combustible de
los reactores que alimentan las fábricas). Acá se recorren todos los textos vanilla y se reescriben con
los nombres del mod (localisation/<idioma>/replace/). Lo que el mod ya define
no se toca, ni lo que va entre $...$, [...] o £...£.
"""

from __future__ import annotations

import re

from ..context import BuildContext

SOURCE = "spec/01_ideologies.yaml -> vanilla_terms"
FILE = "replace/meganations_ideology_terms"

# Palabra vanilla -> palabra del mod, respetando mayúsculas. Se aplican en orden.
TERMS = {
    "spanish": [
        (r"nacionalsocialis(mo|ta|tas)", lambda m: {"mo": "Restauración", "ta": "restauracionista", "tas": "restauracionistas"}[m.group(1)]),
        # el género cambia: el fascismo -> la Restauración, la democracia -> el Orden de Mercado
        (r"del fascismo", "de la Restauración"), (r"al fascismo", "a la Restauración"),
        (r"el fascismo", "la Restauración"), (r"un fascismo", "una Restauración"),
        (r"de la democracia", "del Orden de Mercado"), (r"a la democracia", "al Orden de Mercado"),
        (r"la democracia", "el Orden de Mercado"), (r"una democracia", "un Orden de Mercado"),
        (r"las democracias", "los órdenes de mercado"),
        (r"fascismo", "Restauración"), (r"fascistas", "restauracionistas"), (r"fascista", "restauracionista"),
        (r"comunismo", "Colectivismo"), (r"comunistas", "colectivistas"), (r"comunista", "colectivista"),
        (r"democracias", "órdenes de mercado"), (r"democracia", "Orden de Mercado"),
        (r"democráticos", "mercantiles"), (r"democráticas", "mercantiles"),
        (r"democrático", "mercantil"), (r"democrática", "mercantil"),
        (r"demócratas", "mercantilistas"), (r"demócrata", "mercantilista"),
        (r"no alineados", "trascendentes"), (r"no alineadas", "trascendentes"),
        (r"no alineado", "trascendente"), (r"no alineada", "trascendente"),
        (r"no alineamiento", "Mandato Trascendente"),
        # el carbón (energía de las fábricas desde 1.17) en 2100 es torio de reactor
        (r"carbones", "torio"), (r"carbón", "torio"), (r"carbon(?=\b)", "torio"),
    ],
    "english": [
        (r"fascism", "Restoration"), (r"fascists", "Restorationists"), (r"fascist", "Restorationist"),
        (r"communism", "Collectivism"), (r"communists", "Collectivists"), (r"communist", "Collectivist"),
        (r"democracies", "market orders"), (r"democracy", "Market Order"),
        (r"democratic", "Market"), (r"democrats", "Marketists"), (r"democrat", "Marketist"),
        (r"non-aligned", "Transcendent"), (r"non aligned", "Transcendent"),
        (r"coal", "thorium"),
    ],
}

_PROTECTED = re.compile(r"(\$[^$]*\$|\[[^\]]*\]|£[^£]*£|§.)")


def _case(src: str, new: str) -> str:
    if src.isupper() and len(src) > 1:
        return new.upper()
    if src[:1].isupper():
        return new[:1].upper() + new[1:]
    if new[:1].isupper() and " " not in new and src[:1].islower():
        return new[:1].lower() + new[1:]
    return new


def _compile(lang: str):
    out = []
    for pattern, repl in TERMS[lang]:
        rx = re.compile(rf"(?<![\w$]){pattern}(?!\w)", re.IGNORECASE)
        out.append((rx, repl))
    return out


def rewrite(text: str, rules) -> str:
    parts = _PROTECTED.split(text)
    for i, part in enumerate(parts):
        if i % 2:      # protegido
            continue
        for rx, repl in rules:
            part = rx.sub(lambda m: _case(m.group(0), repl(m) if callable(repl) else repl), part)
        parts[i] = part
    return "".join(parts)


def emit(ctx: BuildContext) -> None:
    if ctx.vanilla is None:
        return
    texts = {lang: ctx.vanilla.all_localisation(lang) for lang in ("english", "spanish")}
    rules = {lang: _compile(lang) for lang in texts}
    changed: dict[str, dict[str, str]] = {}
    for lang, table in texts.items():
        for key, value in table.items():
            new = rewrite(value, rules[lang])
            if new != value:
                changed.setdefault(key, {})[lang] = new
    taken = set(getattr(ctx.loc, "_defined", {}))
    done = 0
    for key, langs in sorted(changed.items()):
        if key in taken:
            continue
        en = langs.get("english") or texts["english"].get(key) or langs.get("spanish")
        es = langs.get("spanish") or texts["spanish"].get(key) or en
        if not (en and es and en.strip() and es.strip()):
            continue
        # error.log 2026-10-06 ("Illegal break character (utf32=39)"): las
        # comillas escapadas del juego (\") quedaban como \' al normalizar
        en, es = en.replace('\\"', '"'), es.replace('\\"', '"')
        ctx.loc.define_and_reference(key, en=en, es=es, file=FILE, origin="vanilla_terms")
        done += 1
    ctx.note(f"textos del juego: {done} con fascista/comunista/democratico/no alineado reescritos "
             "con los grupos del mod (Restauracion, Colectivismo, Orden de Mercado, Mandato Trascendente)")
