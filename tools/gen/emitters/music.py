"""Música propia (spec/11_scenario.yaml -> music, 2026-10-24).

Una estación del reproductor de música del juego con los temas de
assets/music/*.ogg. El nombre del archivo dice a quién le suena (ver el spec):
cada facción y sus satélites escuchan sus temas (los de paz en paz, los de
guerra en guerra, el himno siempre) y los que empiezan con mn_ suenan para
todos, así ningún país se queda sin música en la estación.

Produce (en music/ directamente: el juego no lee subcarpetas):
  music/<id>.ogg                     los temas
  music/<estacion>_music.asset       qué archivo es cada tema
  music/<estacion>_songs.txt         la estación y cuándo suena cada uno
  interface/<estacion>_music.gfx     la tapa del disco de la estación
  localisation                       nombre de la estación y de cada tema
"""

from __future__ import annotations

import re

from ..context import BuildContext
from ..pdx import Block, Quoted, banner_for, render

SOURCE = "spec/11_scenario.yaml -> music"
_TAG = re.compile(r"^([A-Z][A-Z0-9]{2})_(.+)$")


def classify(song: str) -> tuple[str | None, str]:
    """id -> (TAG o None para todos, 'paz' | 'guerra' | 'himno' | 'otro')."""
    if song.startswith("mn_"):
        return None, "otro"
    m = _TAG.match(song)
    if not m:
        return None, "otro"
    rest = m.group(2)
    kind = "paz" if rest.endswith("paz") else "guerra" if rest.endswith("guerra") else \
        "himno" if rest.startswith("himno") else "otro"
    return m.group(1), kind


def emit(ctx: BuildContext) -> None:
    spec = ctx.spec.raw["scenario"].get("music") or {}
    if not spec:
        return
    folder = ctx.spec.root.parent / "assets" / "music"
    songs = sorted(p.stem for p in folder.glob("*.ogg")) if folder.is_dir() else []
    if not songs:
        ctx.note("musica: todavia no hay temas en assets/music")
        return
    station = spec.get("station", "meganations")
    tags = {c.tag for c in ctx.spec.countries}
    subjects = {c.tag: c.overlord for c in ctx.spec.countries if c.is_subject and c.overlord}
    w = {"own_state": 3, "own_anthem": 1, "own_other": 1.5, "everyone": 0.4} | (spec.get("weights") or {})
    titles = spec.get("titles") or {}

    asset = []
    songs_block = Block([("music_station", Quoted(station))])
    unknown = []
    for song in songs:
        # 2026-10-25 ("la estación de radio no aparece"; archivos del juego que mandó el
        # usuario): el juego lee las estaciones de music/ directamente, no de subcarpetas,
        # y cada tema suena solo si se cumplen las condiciones de su `modifier`
        ctx.copy_asset(f"assets/music/{song}.ogg", f"music/{song}.ogg")
        asset.append(f'music = {{\n\tname = "{song}"\n\tfile = "{song}.ogg"\n\tvolume = 0.65\n}}\n')
        tag, kind = classify(song)
        mod = Block()
        if tag is None:
            mod.add("factor", w["everyone"])
        else:
            if tag not in tags:
                unknown.append(song)
                continue
            base = w["own_state"] if kind in ("paz", "guerra") else w["own_anthem"] if kind == "himno" else w["own_other"]
            mod.add("factor", base)
            sats = [s for s, o in subjects.items() if o == tag]
            if sats:
                mod.add("OR", Block([("original_tag", x) for x in [tag] + sats]))
            else:
                mod.add("original_tag", tag)
            if kind == "paz":
                mod.add("has_war", False)
            elif kind == "guerra":
                mod.add("has_war", True)
        songs_block.add("music", Block([("song", Quoted(song)), ("chance", Block([("modifier", mod)]))]))
        ctx.loc.define_and_reference(song, en=titles.get(song, song), es=titles.get(song, song),
                                     file="meganations_music", origin="music")
    ctx.write_text(f"music/{station}_music.asset", banner_for(SOURCE) + "".join(asset))
    ctx.write_text(f"music/{station}_songs.txt", banner_for(SOURCE) + render(songs_block))
    name = spec.get("name") or {"english": "2100 Meganations", "spanish": "2100 Meganations"}
    ctx.loc.define_and_reference(f"{station}_TITLE", en=name["english"], es=name["spanish"],
                                 file="meganations_music", origin="music")
    art = spec.get("album_art")
    if art and (ctx.spec.root.parent / art).is_file():
        tex = f"gfx/interface/topbar/musicplayer/{station}_album_art.dds"
        ctx.copy_asset(art, tex)
        gfx = Block([("spriteTypes", Block([("spriteType", Block([("name", Quoted(f"GFX_{station}_album_art")),
                                                                  ("texturefile", Quoted(tex))]))]))])
        ctx.write_script(f"interface/{station}_music.gfx", gfx, source=SOURCE)
    _station_gui(ctx, station)
    if unknown:
        ctx.warn(f"musica: temas de paises que no existen en el mod (no se usan): {', '.join(unknown)}")
    by_tag: dict[str, int] = {}
    for s in songs:
        t, _ = classify(s)
        by_tag[t or "todos"] = by_tag.get(t or "todos", 0) + 1
    ctx.note(f"musica: estacion '{name['spanish']}' con {len(songs)} temas ("
             + ", ".join(f"{k} {v}" for k, v in sorted(by_tag.items())) + ")")


def _station_gui(ctx: BuildContext, station: str) -> None:
    """La estación necesita dos piezas de interfaz (error.log 2026-10-25: "Missing
    music_station faceplate GUI component ... meganations_faceplate" y "Undefined
    GUI_TYPE: meganations_stations_entry - This will most likely crash the game"):
    <estacion>_faceplate y <estacion>_stations_entry. Se copian las de una estación
    del juego (la base primero), con el nombre de la nuestra."""
    import copy
    from ..pdx import parse_file
    roots = [ctx.vanilla.root / "interface"] + sorted((ctx.vanilla.root / "dlc").glob("*/interface")) \
        if ctx.vanilla else []
    found: dict[str, dict[str, Block]] = {}
    for root in roots:
        for path in sorted(root.glob("**/*.gui")):
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            if "_faceplate" not in text and "_stations_entry" not in text:
                continue
            try:
                parsed = parse_file(path)
            except ValueError:
                continue
            for _, types in parsed.entries:
                if not isinstance(types, Block):
                    continue
                for key, win in types.entries:
                    if key != "containerWindowType" or not isinstance(win, Block):
                        continue
                    from ..pdx import text as _text
                    name = (_text(win.get("name")) or "").strip('"')
                    for suffix in ("_faceplate", "_stations_entry"):
                        if name.endswith(suffix):
                            found.setdefault(name[: -len(suffix)], {})[suffix] = win
    complete = [s for s, parts in found.items() if len(parts) == 2 and s != station]
    if not complete:
        ctx.warn("musica: no encontre en interface/ del juego las piezas de una estacion (<x>_faceplate y "
                 "<x>_stations_entry); la estacion puede no verse")
        return
    src = "base_music" if "base_music" in complete else sorted(complete)[0]
    out = Block()
    for suffix in ("_faceplate", "_stations_entry"):
        win = copy.deepcopy(found[src][suffix])
        _rename(win, src, station)
        out.add("containerWindowType", win)
    ctx.write_script(f"interface/{station}_music.gui", Block([("guiTypes", out)]), source=SOURCE)
    ctx.note(f"musica: piezas de la estacion copiadas de '{src}' ({src}_faceplate, {src}_stations_entry)")


def _rename(block: Block, old: str, new: str) -> None:
    """Cambia `old` por `new` en los nombres de las piezas y en la tapa del disco
    (GFX_<estacion>_album_art, que el mod define). Los demás sprites de la estación
    del juego quedan como están: existen en el juego y los nuestros no."""
    from ..pdx import Quoted
    for i, (k, v) in enumerate(block.entries):
        if isinstance(v, Block):
            _rename(v, old, new)
            continue
        raw = v.text if isinstance(v, Quoted) else v if isinstance(v, str) else None
        if raw is None or old not in raw:
            continue
        if k == "name" or raw.endswith("_album_art"):
            fixed = raw.replace(old, new)
            block.entries[i] = (k, Quoted(fixed) if isinstance(v, Quoted) else fixed)
