"""descriptor.mod y el .mod del launcher.

HOI4 quiere dos archivos:
  build/<mod>/descriptor.mod   — dentro de la carpeta del mod
  build/<mod>.mod              — el que lee el launcher, con `path=`

Los dos tienen el mismo contenido salvo que el del launcher agrega `path`.
"""

from __future__ import annotations

from ..context import BuildContext
from ..pdx import Block, Quoted, banner_for, render
from ..vanilla import Vanilla

SOURCE = "spec/00_project.yaml"


def _body(ctx: BuildContext, *, with_path: bool) -> Block:
    project = ctx.spec.project
    b = Block()
    # descriptor.mod entrecomilla los valores de texto, incluso los que serían
    # tokens válidos sin comillas.
    b.add("name", Quoted(project["name"]))
    b.add("version", Quoted(project["version"]))

    tags = Block()
    for tag in project.get("tags_used", []) or []:
        tags.add(None, Quoted(tag))
    if len(tags):
        b.add("tags", tags)

    supported = _supported_version(ctx)
    if supported:
        b.add("supported_version", Quoted(supported))

    if with_path:
        b.add("path", Quoted(f"mod/{ctx.spec.mod_folder}"))

    # replace_path hace que el mod REEMPLACE una carpeta vanilla entera en vez
    # de fusionarse con ella. Un total conversion lo termina necesitando (si no,
    # arrancan los 1936 paises vanilla junto a los nuestros), pero declararlo
    # antes de generar el contenido que lo reemplaza deja el mundo vacio.
    # Sale del spec, y hoy la lista esta vacia a proposito. Ver Q042.
    for path in project.get("replace_paths", []) or []:
        b.add("replace_path", Quoted(path))
    return b


_version_cache: dict[int, str | None] = {}


def _supported_version(ctx: BuildContext) -> str | None:
    """Nunca hardcodeado: sale de la instalación o del flag --game-version.

    Memoizado por contexto: se llama una vez por cada uno de los dos
    descriptores y el aviso tiene que salir una sola vez.
    """
    if id(ctx) in _version_cache:
        return _version_cache[id(ctx)]
    result = _resolve_version(ctx)
    _version_cache[id(ctx)] = result
    return result


def _resolve_version(ctx: BuildContext) -> str | None:
    if ctx.game_version:
        return Vanilla.supported_version(ctx.game_version)
    if ctx.vanilla:
        try:
            return Vanilla.supported_version(ctx.vanilla.version())
        except Exception as exc:  # noqa: BLE001 - se degrada, no se rompe
            ctx.warn(f"no pude leer la version del juego: {exc}")
    ctx.skip(
        "descriptor.supported_version",
        "sin --vanilla-path ni --game-version no se sabe la version del juego",
        "Q004",
    )
    ctx.warn(
        "descriptor.mod sale SIN supported_version. El launcher lo va a marcar "
        "como incompatible aunque el mod cargue. Corre con --vanilla-path."
    )
    return None


def emit(ctx: BuildContext) -> None:
    header = banner_for(SOURCE)

    ctx.write_text("descriptor.mod", header + render(_body(ctx, with_path=False)))

    launcher = ctx.out_root / f"{ctx.spec.mod_folder}.mod"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(header + render(_body(ctx, with_path=True)), encoding="utf-8", newline="\n")
    ctx.track(launcher)
