"""Mejoras de la agencia de inteligencia con nombres de 2100 (spec/18_intelligence.yaml).

La Guerra en las Sombras (operaciones propias, contrainteligencia y puntaje de
infiltración) se sacó el 2026-10-04 a pedido del usuario ("abortar": siempre
en 0, no se entendía y no era divertida). Queda el espionaje del juego base,
con las mejoras de la agencia renombradas y con ícono propio si llegó el arte.
"""

from __future__ import annotations

from ..context import BuildContext

SOURCE = "spec/18_intelligence.yaml"
LOC_FILE = "meganations_intelligence"


def emit(ctx: BuildContext) -> None:
    spec = ctx.spec.raw.get("intelligence")
    if not spec or ctx.vanilla is None:
        return
    _agency_upgrades(ctx, spec.get("agency_upgrades") or [])


def _agency_upgrades(ctx: BuildContext, items: list[dict]) -> None:
    """Nombres de 2100 para las mejoras de la agencia (se buscan por el texto que
    muestra el juego en español) y, si llegó el dibujo, su ícono."""
    import re
    from .menu import _dims, _resize, _texture_dims
    repo = ctx.spec.root.parent
    files = sorted((ctx.vanilla.root / "common" / "intelligence_agency_upgrades").glob("*.txt"))
    texts = []
    for f in files:
        try:
            texts.append(f.read_text(encoding="utf-8-sig", errors="replace"))
        except OSError:
            continue
    blob = "\n".join(texts)
    textures = ctx.vanilla.gfx_textures()
    renamed, icons, missing = 0, 0, []
    for it in items:
        keys = ctx.vanilla.loc_keys_with_text_in(it["was"], "spanish")
        # solo las claves de la agencia (el mismo texto puede estar en otro lado)
        keys = [k for k in keys if re.search(r"(?i)upgrade|agency|branch|intel|crypt|operative|defen", k)] or keys[:1]
        if not keys:
            missing.append(it["was"])
            continue
        for k in keys:
            ctx.loc.define_and_reference(k, en=it["english"], es=it["spanish"],
                                         file="replace/meganations_intelligence", origin=f"agency:{it['id']}")
        renamed += 1
        # ícono: la primera referencia GFX_ cerca de la clave en common/intelligence_agency_upgrades
        sprite = None
        for k in keys:
            m = re.search(rf"\b{re.escape(k)}\b", blob)
            if m:
                g = re.search(r"GFX_[A-Za-z0-9_]+", blob[m.end():m.end() + 800])
                if g:
                    sprite = g.group(0)
                    break
        own = repo / "assets" / "agency" / f"{it['id']}.dds"
        tex = textures.get(sprite or "")
        if sprite is None or tex is None:
            ctx.note(f"agencia: '{it['was']}' -> claves {', '.join(keys[:3])}; icono sin ubicar")
            continue
        if not own.exists():
            continue
        data = own.read_bytes()
        w, h = _dims(data)
        vw, vh = _texture_dims(ctx, tex)
        if vw and vh and (w, h) != (vw, vh):
            data = _resize(data, w, h, vw, vh)
        dest = ctx.mod_root / tex
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        ctx.track(dest)
        icons += 1
    ctx.note(f"agencia: {renamed} mejoras con nombre de 2100, {icons} iconos propios"
             + (f"; no encontre: {', '.join(missing)}" if missing else ""))
