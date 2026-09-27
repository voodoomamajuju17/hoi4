"""Doctrinas de arranque (13_military.yaml -> doctrines).

Pedido del usuario (2026-09-29): cada meganación arranca con una doctrina
propia ya iniciada (gran doctrina + subdoctrina, con algo de maestría), que
comparten sus satélites; la Anarquía comparte una.

Los nombres se buscan en common/doctrines/ del juego instalado (sistema de
1.17 en adelante). Para cada bloque se prueba cada candidato; si ninguno
existe, se busca por palabra clave dentro de la carpeta (tierra, mar o aire);
si tampoco, se usa la primera de la carpeta, con aviso. El reporte lista las
doctrinas que trae el juego para poder afinar los nombres.

Se aplican al arrancar la partida (on_startup), con set_grand_doctrine,
set_sub_doctrine y add_mastery.
"""

from __future__ import annotations

from ..context import BuildContext
from ..pdx import Block

SOURCE = "spec/13_military.yaml"


def _grand(spec: dict, grands: dict[str, dict]) -> tuple[str | None, bool]:
    """(gran doctrina, si hubo que caer a la primera de la carpeta)."""
    folder = spec.get("folder", "land")
    here = {k: v for k, v in grands.items() if v["folder"] == folder}
    for key in spec.get("grand") or []:
        if key in here:
            return key, False
    for kw in spec.get("grand_kw") or []:
        hit = next((k for k in sorted(here) if kw in k), None)
        if hit:
            return hit, False
    return (sorted(here)[0], True) if here else (None, True)


def _sub(spec: dict, tracks: list[str], subs: dict[str, dict]) -> tuple[str | None, bool]:
    """(subdoctrina de un track de la gran doctrina, si hubo que caer a la primera).
    Orden: los nombres de `sub`; las palabras de `sub_kw` en el track pedido
    (o en todos, si el track no existe); la primera del track; la primera."""
    usable = {k: v for k, v in subs.items() if not tracks or set(v["tracks"]) & set(tracks)}
    for key in spec.get("sub") or []:
        if key in usable:
            return key, False
    want = spec.get("track")
    track = next((t for t in tracks if want and want in t), None)
    in_track = {k: v for k, v in usable.items() if track is not None and track in v["tracks"]}
    # el track pedido manda; recién si no existe se busca en todos
    pool = in_track or usable
    for kw in spec.get("sub_kw") or []:
        hit = next((k for k in sorted(pool) if kw in k), None)
        if hit:
            return hit, False
    if in_track:
        return sorted(in_track)[0], False
    return (sorted(usable)[0], True) if usable else (None, True)


def emit(ctx: BuildContext) -> None:
    spec = (ctx.spec.raw.get("military") or {}).get("doctrines") or {}
    if not spec:
        return
    if ctx.vanilla is None:
        ctx.skip("doctrinas de arranque", "hay que leer common/doctrines/ del juego instalado")
        return
    catalog = ctx.vanilla.doctrines()
    if not catalog or not catalog["grand"]:
        ctx.warn("doctrinas: el juego no tiene common/doctrines/ (sistema anterior a 1.17); se omiten.")
        return
    folders = sorted({v["folder"] for v in catalog["grand"].values()})
    ctx.note("doctrinas del juego: " + " | ".join(
        f"{f}: {', '.join(sorted(k for k, v in catalog['grand'].items() if v['folder'] == f))}" for f in folders))
    ctx.note(f"subdoctrinas del juego ({len(catalog['sub'])}): " + ", ".join(sorted(catalog["sub"])))
    bad = getattr(ctx.vanilla, "unparsed_doctrines", [])
    if bad:
        ctx.warn(f"doctrinas: archivos del juego que no se pudieron leer: {', '.join(bad)}")

    owners = set((ctx.data.get("territory") or {}).values())
    mastery = int(spec.get("mastery", 100))
    blocs = spec.get("blocs") or {}
    chosen: dict[str, tuple[str, str | None]] = {}
    warned: set[str] = set()
    effect = Block()
    for c in ctx.spec.countries:
        leader = c.tag if c.is_major else c.overlord if c.is_subject else "anarchy"
        bspec = blocs.get(leader)
        if not bspec or (owners and c.tag not in owners):
            continue
        grand, fell = _grand(bspec, catalog["grand"])
        if grand is None:
            ctx.warn(f"doctrinas: {c.tag}: no hay grandes doctrinas en la carpeta '{bspec.get('folder')}'; se omite.")
            continue
        sub, fell_sub = _sub(bspec, catalog["grand"][grand]["tracks"], catalog["sub"])
        if (fell or fell_sub) and leader not in warned:
            warned.add(leader)
            ctx.warn(f"doctrinas: {leader}: no encontré la pedida; arranca con {grand} / {sub or '-'} (ver 13_military.yaml).")
        body = Block([("set_grand_doctrine", grand)])
        if sub:
            body.add("set_sub_doctrine", sub)
            body.add("add_mastery", Block([("amount", mastery), ("sub_doctrine", sub)]))
        effect.add("if", Block([("limit", Block([("country_exists", c.tag)])), (c.tag, body)]))
        chosen[c.tag] = (grand, sub)
    if not chosen:
        return
    ctx.data["doctrines"] = chosen
    root = Block([("on_actions", Block([("on_startup", Block([("effect", effect)]))]))])
    ctx.write_script("common/on_actions/01_meganations_doctrines.txt", root, source=SOURCE)
    ctx.verify_keys("effects", {k: "doctrinas" for k in ("set_grand_doctrine", "set_sub_doctrine", "add_mastery")})
    ctx.verify_keys("triggers", {"country_exists": "doctrinas"})
    by_leader: dict[tuple[str, str | None], list[str]] = {}
    for tag, pair in chosen.items():
        by_leader.setdefault(pair, []).append(tag)
    ctx.note("doctrinas de arranque: " + "; ".join(f"{g}/{s or '-'} ({', '.join(t)})" for (g, s), t in by_leader.items()))
