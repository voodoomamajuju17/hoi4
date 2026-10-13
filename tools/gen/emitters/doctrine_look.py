"""Doctrinas con el lore de 2100 (17_research.yaml -> doctrines).

Pedido del usuario (2026-10-13): "cambiar las doctrinas por cosas más acordes
al lore y el juego, y actualizar las imágenes". Las doctrinas son las del
juego instalado (common/doctrines/, sistema de 1.17+): cambia lo que se ve, no
lo que hacen.

  nombre       doctrines.grand/sub.<clave> {en, es}; las que no están, el
               nombre del juego con module_terms (cañón -> cañón de riel...)
  descripción  <clave>_desc: la de `desc_en/desc_es` en las grandes; en las
               demás, la del juego con module_terms
  ícono        assets/COMUN/doctrinas/<clave>.dds (pedido de arte
               doctrine_icon): se escribe, al tamaño del ícono del juego, en la
               ruta de la textura de su sprite (`icon` de la doctrina), así la
               pantalla de doctrinas muestra la nueva

El reporte dice cuántas claves del juego se encontraron, para saber que se ven.
"""

from __future__ import annotations

from ..context import BuildContext
from .research import _module_terms, _terms

SOURCE = "spec/17_research.yaml -> doctrines"
LOC_FILE = "replace/meganations_doctrines"


def emit(ctx: BuildContext) -> None:
    look = ctx.spec.raw.get("research_look") or {}
    spec = look.get("doctrines") or {}
    if not spec or ctx.vanilla is None:
        return
    catalog = ctx.vanilla.doctrines()
    if not catalog:
        return
    terms = _module_terms(look)
    own = {**(spec.get("grand") or {}), **(spec.get("sub") or {})}
    keys = sorted(set(catalog["grand"]) | set(catalog["sub"]))
    en_all = ctx.vanilla.all_localisation("english")
    es_all = ctx.vanilla.all_localisation("spanish")
    taken = set(getattr(ctx.loc, "_defined", {}))
    named, by_terms, found = 0, 0, 0
    missing_names, patterns = [], {}
    for key in keys:
        name_key, desc_key = _loc_keys(key, en_all)
        found += name_key in en_all
        if name_key != key:
            patterns.setdefault(name_key.replace(key, "<doctrina>"), key)
        entry = own.get(key)
        texts = {}
        if entry:
            # la clave del juego y, por las dudas, la del id pelado
            for k in dict.fromkeys((name_key, key)):
                texts[k] = (entry["en"], entry["es"])
            if entry.get("desc_en"):
                for k in dict.fromkeys((desc_key, f"{key}_desc")):
                    texts[k] = (entry["desc_en"], entry["desc_es"])
            named += 1
        else:
            missing_names.append(key)
        en_txt, es_txt = en_all, es_all
        for k in (name_key, desc_key):
            if k in texts:
                continue
            en, es = en_txt.get(k) or es_txt.get(k), es_txt.get(k) or en_txt.get(k)
            if not en:
                continue
            new = (_terms(en, terms, "english"), _terms(es, terms, "spanish"))
            if new != (en, es):
                texts[k] = new
                by_terms += k == key
        for k, (en, es) in texts.items():
            if k in taken:
                continue
            ctx.loc.define_and_reference(k, en=en, es=es, file=LOC_FILE, origin=f"doctrine:{k}")
            taken.add(k)
    unknown = sorted(set(own) - set(keys))
    ctx.note(f"doctrinas con nombre de 2100: {named} de {len(keys)} (+{by_terms} con module_terms); "
             f"el juego tiene nombre para {found}"
             + (f"; claves del juego: {', '.join(f'{p} ({k})' for p, k in list(patterns.items())[:4])}" if patterns else "")
             + (f"; sin nombre propio: {', '.join(missing_names[:20])}" if missing_names else "")
             + (f"; en el spec pero no en este juego: {', '.join(unknown[:20])}" if unknown else ""))
    _icons(ctx, catalog)


def _loc_keys(key: str, loc: dict[str, str]) -> tuple[str, str]:
    """La clave del nombre y la de la descripción que usa el juego para la
    doctrina: la del id si existe; si no, la más corta que lo contiene (el
    formato de 1.17+ no está documentado)."""
    if key in loc:
        name = key
    else:
        cands = sorted((k for k in loc if key in k and "desc" not in k.lower()), key=len)
        name = cands[0] if cands else key
    for desc in (f"{name}_desc", f"{key}_desc", f"{name}_DESC"):
        if desc in loc:
            return name, desc
    cands = sorted((k for k in loc if key in k and "desc" in k.lower()), key=len)
    return name, cands[0] if cands else f"{key}_desc"


def _icons(ctx: BuildContext, catalog: dict) -> None:
    from .faction_tech import _fit
    from .menu import _dims, _texture_dims
    folder = ctx.spec.root.parent / "assets" / "COMUN" / "doctrinas"
    if not folder.is_dir():
        return
    textures = ctx.vanilla.gfx_textures()
    done, no_sprite = [], []
    for kind in ("grand", "sub"):
        for key, info in sorted(catalog[kind].items()):
            art = folder / f"{key}.dds"
            if not art.exists():
                # la variante sin La Resistance (armored_cavalry_no_lar) usa la misma
                art = folder / f"{key.removesuffix('_no_lar')}.dds"
            if not art.exists():
                continue
            sprite = info.get("icon") or ""
            tex = textures.get(sprite) if sprite else None
            if not tex or not tex.lower().endswith(".dds"):
                no_sprite.append(key)
                continue
            data = art.read_bytes()
            w, h = _dims(data)
            nw, nh = _texture_dims(ctx, tex)
            if nw and nh and (nw, nh) != (w, h) and w and h:
                data = _fit(data, w, h, nw, nh)
            dest = ctx.mod_root / tex
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            ctx.track(dest)
            done.append(key)
    ctx.note(f"doctrinas: {len(done)} iconos nuevos"
             + (f"; sin sprite .dds del juego para reemplazar: {', '.join(no_sprite[:15])}" if no_sprite else ""))
