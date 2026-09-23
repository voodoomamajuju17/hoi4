"""Recursos propios del mod: BioSteel como séptimo recurso (Q021, Q043).

Produce:
  common/resources/<mismo archivo que vanilla>.txt   vanilla + nuestros recursos
  localisation de los nombres

Historia: la primera versión reskineaba el carbón y se lo sacaba al resto del
mundo. Desde 1.17 el carbón da la energía que consumen las fábricas, así que
eso dejaba a todos en déficit permanente. Ahora BioSteel es un recurso nuevo y
el carbón queda intacto.

Nada se escribe de memoria:
  - La definición se copia del recurso vanilla que dice `template` (icon_frame,
    cic, convoys...). El archivo vanilla se reescribe entero con la entrada
    nueva agregada, con el mismo nombre, para reemplazarlo sin duplicar.
  - Las claves de localisation se derivan de las del recurso plantilla: toda
    clave vanilla con "steel" en el nombre y "Steel" como texto se duplica
    cambiando steel -> biosteel.
Sin --vanilla-path no se puede hacer nada de esto: se salta y se avisa.
"""

from __future__ import annotations

import re

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, banner_for, parse_file, render

LOC_FILE = "meganations_resources"


def new_resources(ctx: BuildContext) -> list[dict]:
    out = []
    for mech in ctx.spec.raw["mechanics"].get("mechanics", []) or []:
        resource = mech.get("resource")
        if isinstance(resource, dict) and resource.get("strategy") == "new_resource":
            out.append(mech)
    return out


def emit(ctx: BuildContext) -> None:
    mechs = new_resources(ctx)
    if not mechs:
        return
    if ctx.vanilla is None:
        for mech in mechs:
            ctx.skip(f"recurso {mech['resource']['key']}",
                     "se define copiando un recurso vanilla y no hay --vanilla-path", "Q035")
        return

    path, root, block = _vanilla_resources(ctx)
    existing = set(block.keys())
    for mech in mechs:
        res = mech["resource"]
        key, template = res["key"], res["template"]
        if key in existing:
            raise SpecError(f"el recurso '{key}' ya existe en el juego", where="06_mechanics.yaml")
        source = block.get(template)
        if not isinstance(source, Block):
            raise SpecError(f"el recurso plantilla '{template}' no existe en {path.name}",
                            where="06_mechanics.yaml")
        block.add(key, Block(list(source.entries)))
        _localise(ctx, mech, key, res.get("loc_template", template))

    ctx.write_text(
        f"common/resources/{path.name}",
        banner_for(f"common/resources/{path.name} vanilla + 06_mechanics.yaml") + render(root),
    )


def _vanilla_resources(ctx: BuildContext):
    for path in sorted((ctx.vanilla.root / "common" / "resources").glob("*.txt")):
        try:
            root = parse_file(path)
        except ValueError:
            continue
        block = root.get("resources")
        if isinstance(block, Block):
            return path, root, block
    raise SpecError("no encontre common/resources/ con un bloque 'resources' en el juego",
                    where="06_mechanics.yaml")


def _localise(ctx: BuildContext, mech: dict, key: str, template: str) -> None:
    shown = template.capitalize()
    keys = [k for k in ctx.vanilla.loc_keys_with_text(shown) if template in k.lower()]
    if not keys:
        ctx.warn(f"no encontre claves de localisation del recurso '{template}'; "
                 f"'{key}' puede verse sin nombre en pantalla.")
    pattern = re.compile(re.escape(template), re.IGNORECASE)
    for vkey in keys:
        new_key = pattern.sub(lambda m: key.upper() if m.group(0).isupper() else key, vkey, count=1)
        ctx.loc.define_and_reference(
            new_key, en=mech["name"]["english"], es=mech["name"]["spanish"],
            file=LOC_FILE, origin=f"resources:{key}",
        )
