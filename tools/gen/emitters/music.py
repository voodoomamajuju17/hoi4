"""Música propia (spec/11_scenario.yaml -> music, 2026-10-24).

Una estación del reproductor de música del juego con los temas de
assets/music/*.ogg. El nombre del archivo dice a quién le suena (ver el spec):
cada facción y sus satélites escuchan sus temas (los de paz en paz, los de
guerra en guerra, el himno siempre) y los que empiezan con mn_ suenan para
todos, así ningún país se queda sin música en la estación.

Produce:
  music/<estacion>/<id>.ogg          los temas
  music/<estacion>/<estacion>.asset  qué archivo es cada tema
  music/<estacion>/<estacion>_songs.txt  la estación y cuándo suena cada uno
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
        ctx.copy_asset(f"assets/music/{song}.ogg", f"music/{station}/{song}.ogg")
        asset.append(f'music = {{\n\tname = "{song}"\n\tfile = "{song}.ogg"\n\tvolume = 0.65\n}}\n')
        tag, kind = classify(song)
        chance = Block()
        if tag is None:
            chance.add("factor", w["everyone"])
        else:
            if tag not in tags:
                unknown.append(song)
                continue
            base = w["own_state"] if kind in ("paz", "guerra") else w["own_anthem"] if kind == "himno" else w["own_other"]
            chance.add("factor", base)
            sats = [s for s, o in subjects.items() if o == tag]
            who = Block([("original_tag", tag)] + [("original_tag", s) for s in sats])
            chance.add("modifier", Block([("factor", 0), ("NOT", Block([("OR", who)]) if len(who.entries) > 1
                                                          else Block([("original_tag", tag)]))]))
            if kind == "paz":
                chance.add("modifier", Block([("factor", 0), ("has_war", True)]))
            elif kind == "guerra":
                chance.add("modifier", Block([("factor", 0), ("has_war", False)]))
        songs_block.add("music", Block([("song", Quoted(song)), ("chance", chance)]))
        ctx.loc.define_and_reference(song, en=titles.get(song, song), es=titles.get(song, song),
                                     file="meganations_music", origin="music")
    ctx.write_text(f"music/{station}/{station}.asset", banner_for(SOURCE).replace("#", "#") + "".join(asset))
    ctx.write_text(f"music/{station}/{station}_songs.txt", banner_for(SOURCE) + render(songs_block))
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
    if unknown:
        ctx.warn(f"musica: temas de paises que no existen en el mod (no se usan): {', '.join(unknown)}")
    by_tag: dict[str, int] = {}
    for s in songs:
        t, _ = classify(s)
        by_tag[t or "todos"] = by_tag.get(t or "todos", 0) + 1
    ctx.note(f"musica: estacion '{name['spanish']}' con {len(songs)} temas ("
             + ", ".join(f"{k} {v}" for k, v in sorted(by_tag.items())) + ")")
