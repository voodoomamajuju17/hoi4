"""Las leyes del juego con el lore de 2100 (05_ideas.yaml -> laws).

Pedido del usuario (2026-10-15): "haceme el pedido de imágenes para el menú de
país, leyes económicas, reclutamiento, etc. Podés ajustar los nombres
también". Las leyes son las del juego instalado (common/ideas/: economy,
trade_laws, mobilization_laws): cambia lo que se ve, no lo que hacen.

  nombre  laws.<categoría>.<ley> {en, es} en la clave <ley> (la descripción
          sigue siendo la del juego)
  ícono   assets/COMUN/leyes/<ley>.dds (pedido de arte law_icon): se escribe,
          al tamaño del ícono del juego, en la ruta de la textura de su sprite
          (GFX_idea_<picture> o GFX_idea_<ley>), así el menú del país muestra
          la nueva

El reporte dice cuántas leyes del spec están en el juego y cuántas tienen ícono.
"""

from __future__ import annotations

from .. import pdx
from ..context import BuildContext

SOURCE = "spec/05_ideas.yaml -> laws"
LOC_FILE = "replace/meganations_laws"
CATEGORIES = ("economy", "trade_laws", "mobilization_laws")


def emit(ctx: BuildContext) -> None:
    spec = (ctx.spec.raw.get("ideas") or {}).get("laws") or {}
    if not spec or ctx.vanilla is None:
        return
    game = game_laws(ctx)
    taken = set(getattr(ctx.loc, "_defined", {}))
    named, unknown = 0, []
    for cat in CATEGORIES:
        for law, entry in (spec.get(cat) or {}).items():
            if law not in game:
                unknown.append(law)
                continue
            if law in taken:
                continue
            ctx.loc.define_and_reference(law, en=entry["en"], es=entry["es"], file=LOC_FILE, origin=f"law:{law}")
            taken.add(law)
            named += 1
    ctx.note(f"leyes con nombre de 2100: {named} de {len(game)} del juego"
             + (f"; en el spec pero no en este juego: {', '.join(unknown)}" if unknown else ""))
    _icons(ctx, game)


def game_laws(ctx: BuildContext) -> dict[str, str]:
    """Ley -> sprite de su ícono, de las categorías de leyes de common/ideas/."""
    out: dict[str, str] = {}
    for path in sorted((ctx.vanilla.root / "common" / "ideas").glob("*.txt")):
        try:
            root = pdx.parse_file(path)
        except ValueError:
            continue
        ideas = root.get("ideas")
        if not isinstance(ideas, pdx.Block):
            continue
        for cat_name, cat in ideas.entries:
            if cat_name not in CATEGORIES or not isinstance(cat, pdx.Block):
                continue
            for law, body in cat.entries:
                if not law or not isinstance(body, pdx.Block):
                    continue
                picture = body.get("picture")
                out.setdefault(law, f"GFX_idea_{picture if isinstance(picture, str) and picture else law}")
    return out


def _icons(ctx: BuildContext, game: dict[str, str]) -> None:
    from .faction_tech import _fit
    from .menu import _dims, _texture_dims
    folder = ctx.spec.root.parent / "assets" / "COMUN" / "leyes"
    if not folder.is_dir():
        return
    textures = ctx.vanilla.gfx_textures()
    done, no_sprite, shared = [], [], []
    used: dict[str, str] = {}
    for law, sprite in sorted(game.items()):
        art = folder / f"{law}.dds"
        if not art.exists():
            continue
        tex = textures.get(sprite)
        if not tex or not tex.lower().endswith(".dds"):
            no_sprite.append(f"{law} ({sprite})")
            continue
        if tex in used:
            # dos leyes con la misma textura: una sola imagen puede ir ahí
            shared.append(f"{law}={used[tex]}")
            continue
        used[tex] = law
        data = art.read_bytes()
        w, h = _dims(data)
        nw, nh = _texture_dims(ctx, tex)
        if nw and nh and w and h and (nw, nh) != (w, h):
            data = _fit(data, w, h, nw, nh)
        dest = ctx.mod_root / tex
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        ctx.track(dest)
        done.append(law)
    ctx.note(f"leyes: {len(done)} iconos nuevos"
             + (f"; sin sprite .dds del juego para reemplazar: {', '.join(no_sprite)}" if no_sprite else "")
             + (f"; comparten textura con otra ley (queda la primera): {', '.join(shared)}" if shared else ""))
