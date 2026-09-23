"""Recursos reskineados: BioSteel sobre el carbón vanilla (Q021, Q043).

Produce:
  localisation/<idioma>/replace/meganations_resources_l_<idioma>.yml

No se crea un recurso nuevo en common/resources/. El recurso interno sigue
siendo el vanilla, así que el mercado, los convoyes, los costos de equipo y
cualquier trigger vanilla lo siguen encontrando. Solo cambia lo que ve el
jugador.

Las claves a pisar NO se escriben de memoria: se buscan en la localisation
vanilla todas las que muestran exactamente el nombre del recurso ("Coal"). Van
en la carpeta replace/, que es la que le gana a vanilla en claves repetidas.
"""

from __future__ import annotations

from ..context import BuildContext

LOC_FILE = "replace/meganations_resources"


def reskinned_resources(ctx: BuildContext) -> list[dict]:
    """Mecánicas del spec que se implementan como reskin de un recurso."""
    out = []
    for mech in ctx.spec.raw["mechanics"].get("mechanics", []) or []:
        resource = mech.get("resource")
        if isinstance(resource, dict) and resource.get("strategy") == "localisation_reskin":
            out.append(mech)
    return out


def emit(ctx: BuildContext) -> None:
    for mech in reskinned_resources(ctx):
        resource = mech["resource"]
        shown = resource["vanilla_display_name"]
        if ctx.vanilla is None:
            ctx.skip(
                f"renombre del recurso '{resource['vanilla_key']}' a {mech['name']['english']}",
                "las claves a pisar se buscan en la localisation vanilla y no hay --vanilla-path",
                "Q035",
            )
            continue

        keys = ctx.vanilla.loc_keys_with_text(shown)
        if not keys:
            ctx.warn(
                f"no encontre en la localisation vanilla ninguna clave con el texto "
                f"'{shown}'. El recurso '{resource['vanilla_key']}' se va a seguir "
                f"llamando asi en pantalla."
            )
            continue

        for key in keys:
            ctx.loc.define_and_reference(
                key,
                en=mech["name"]["english"],
                es=mech["name"]["spanish"],
                file=LOC_FILE,
                origin=f"resources:{mech['id']}",
            )
