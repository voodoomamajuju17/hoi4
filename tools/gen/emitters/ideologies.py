"""common/ideologies/00_ideologies.txt — estrategia reskin_groups.

Decisión Q006: se conservan los cuatro grupos internos vanilla (fascism,
communism, democratic, neutrality) y nuestras ideologías entran como `types`
dentro de ellos. El jugador nunca ve la clave interna; ve la localisation.

El archivo NO se escribe de cero. Se lee el vanilla, se le inyectan los types y
se reescribe entero. Escribirlo de memoria significaría reproducir los bloques
`rules`, `ai` y `dynamic_faction_names` de los cuatro grupos: cualquier campo
olvidado o inventado rompe la carga, y son bloques largos que cambian entre
parches. Leerlos es gratis y siempre correcto.

Consecuencia: este emisor EXIGE --vanilla-path. Sin eso se salta, y lo dice.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block

SOURCE = "spec/01_ideologies.yaml (fusionado con common/ideologies/ vanilla)"
LOC_FILE = "meganations_ideologies"


def emit(ctx: BuildContext) -> None:
    groups_spec = ctx.spec.raw["ideologies"].get("groups", []) or []

    # La localisation se define siempre, haya vanilla o no: las claves las
    # consume el juego por nombre de ideología, no por este archivo.
    _emit_localisation(ctx, groups_spec)

    if ctx.vanilla is None:
        ctx.skip(
            "common/ideologies/00_ideologies.txt",
            "la estrategia reskin_groups parte del archivo vanilla y no hay --vanilla-path",
            "Q035",
        )
        ctx.warn(
            "SIN IDEOLOGIAS: las 8 sub-ideologias del mod no se generaron. Los paises "
            "apuntan a ideologias que no existen y el mod NO va a cargar. "
            "Corre con --vanilla-path para generar este archivo."
        )
        return

    vanilla_block = ctx.vanilla.parse_ideologies()
    merged = _merge(ctx, vanilla_block, groups_spec)

    root = Block()
    root.add("ideologies", merged)
    ctx.write_script("common/ideologies/00_ideologies.txt", root, source=SOURCE)


def _merge(ctx: BuildContext, vanilla: Block, groups_spec: list[dict]) -> Block:
    """Inyecta nuestros types en los grupos vanilla, conservando todo lo demás."""
    by_key = {key: value for key, value in vanilla.entries if isinstance(value, Block)}

    for group in groups_spec:
        key = group["key"]
        if key not in by_key:
            raise SpecError(
                f"el grupo ideologico '{key}' no existe en el archivo vanilla",
                hint=(
                    "reskin_groups asume los cuatro grupos vanilla "
                    "(fascism, communism, democratic, neutrality). "
                    f"El vanilla tiene: {', '.join(sorted(by_key))}"
                ),
                where="01_ideologies.yaml",
            )
        target = by_key[key]
        types_block = target.get("types")
        if not isinstance(types_block, Block):
            raise SpecError(
                f"el grupo vanilla '{key}' no tiene bloque 'types'",
                hint="puede que la estructura del archivo haya cambiado en esta version del juego",
                where="vanilla",
            )

        existing = set(types_block.keys())
        for t in group.get("types", []) or []:
            tkey = t["key"]
            if tkey in existing:
                ctx.warn(
                    f"la sub-ideologia '{tkey}' ya existe en el grupo vanilla '{key}'; "
                    f"se conserva la vanilla y no se duplica"
                )
                continue
            types_block.add(tkey, Block())

        # Nuestro color de grupo pisa el vanilla: es parte del reskin.
        color = group.get("color_rgb")
        if color:
            _replace(target, "color", Block([(None, c) for c in color]))

    return vanilla


def _replace(b: Block, key: str, value) -> None:
    for i, (k, _) in enumerate(b.entries):
        if k == key:
            b.entries[i] = (key, value)
            return
    b.add(key, value)


def _emit_localisation(ctx: BuildContext, groups_spec: list[dict]) -> None:
    """Nombres de grupos y sub-ideologías, en EN y ES.

    Claves que consume HOI4 por ideología:
      <ideologia>             nombre
      <ideologia>_desc        descripcion
      <ideologia>_leader_desc titulo del lider
    Las tres se emiten juntas para no dejar huecos.
    """
    for group in groups_spec:
        gloc = group.get("loc") or {}
        key = group["key"]
        ctx.loc.define_and_reference(
            key,
            en=gloc.get("english", key),
            es=gloc.get("spanish", key),
            file=LOC_FILE,
            origin="ideologies:group",
        )
        ctx.loc.define_and_reference(
            f"{key}_desc",
            en=_group_desc(group, "english"),
            es=_group_desc(group, "spanish"),
            file=LOC_FILE,
            origin="ideologies:group_desc",
        )

        for t in group.get("types", []) or []:
            tkey = t["key"]
            tloc = t.get("loc") or {}
            name_en = tloc.get("english", tkey)
            name_es = tloc.get("spanish", tkey)
            ctx.loc.define_and_reference(
                tkey, en=name_en, es=name_es, file=LOC_FILE, origin="ideologies:type"
            )
            ctx.loc.define_and_reference(
                f"{tkey}_desc",
                en=_type_desc(t, name_en, "english"),
                es=_type_desc(t, name_es, "spanish"),
                file=LOC_FILE,
                origin="ideologies:type_desc",
            )


def _group_desc(group: dict, language: str) -> str:
    from_doc = group.get("from_doc")
    if from_doc:
        return " ".join(str(from_doc).split())
    label = (group.get("loc") or {}).get(language, group["key"])
    return (
        f"Ideological family: {label}."
        if language == "english"
        else f"Familia ideologica: {label}."
    )


def _type_desc(t: dict, name: str, language: str) -> str:
    """Descripción placeholder honesta.

    El documento no da descripciones de ideología. En vez de inventar prosa que
    despues nadie sabe si es canon, se marca como placeholder en el propio texto.
    """
    if language == "english":
        return f"{name}. [Placeholder: the design bible does not define this ideology's text.]"
    return f"{name}. [Placeholder: la biblia de diseno no define el texto de esta ideologia.]"
