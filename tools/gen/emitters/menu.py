"""Fondo del menú principal (spec/11_scenario.yaml -> main_menu).

No se edita ninguna interfaz vanilla: se buscan en interface/**/*.gfx los
sprites de fondo del menú principal y se escribe nuestra imagen en la MISMA
ruta de textura (el archivo del mod pisa al vanilla). Si la textura vanilla
tiene otro tamaño, la nuestra se reescala a ese tamaño sin deformarla: se
ajusta al ancho, se centra y las franjas que sobran repiten el borde (vecino
más cercano, sin dependencias).

Candidatos: en 1.19 el fondo es GFX_frontend_bg (interface/frontendmainviewbg.gfx,
un corneredTileSpriteType que apunta a gfx/loadingscreens/load_5.dds). Además
se aceptan sprites cuyo nombre hable de menú principal y de fondo, por si una
versión futura lo renombra.

Como en 1.19.3 reemplazar solo GFX_frontend_bg no alcanzó (el menú siguió
igual), también se toman los sprites que usan las pantallas del menú
(interface/frontend*.gui y mainmenu*.gui) cuya textura es una imagen grande
(al menos 1280 px de ancho): esos son fondos, no botones. Todo lo que se
reemplaza y lo que se descartó va al reporte, para ver qué usa el juego.
"""

from __future__ import annotations

import re
import struct

from ..context import BuildContext

_NAME = re.compile(r"(?i)^GFX_frontend_(main_?)?bg$|(main_?menu|menu).*(bg|background)|(bg|background).*(main_?menu)")
_SPRITE = re.compile(r'name\s*=\s*"?(GFX_[A-Za-z0-9_]+)"?\s+texturefile\s*=\s*"([^"]+)"', re.S)
_GUI_SPRITE = re.compile(r'(?:spriteType|quadTextureSprite)\s*=\s*"?(GFX_[A-Za-z0-9_]+)"?')
_MIN_BG_WIDTH = 1280


def emit(ctx: BuildContext) -> None:
    spec = (ctx.spec.raw.get("scenario") or {}).get("main_menu")
    if not spec:
        return
    if ctx.vanilla is None:
        ctx.skip("fondo del menu principal", "hay que buscar la textura en el juego instalado", "Q035")
        return
    targets = _menu_textures(ctx)
    if not targets:
        ctx.warn("menu: no encontre el sprite de fondo del menu principal en interface/; no se cambia.")
        return
    src = (ctx.spec.root.parent / spec["background"]).read_bytes()
    width, height = _dims(src)
    for texture in sorted(targets):
        vanilla_file = ctx.vanilla.root / texture
        data = src
        if vanilla_file.exists():
            vw, vh = _dims(vanilla_file.read_bytes()[:128])
            if (vw, vh) != (width, height) and vw and vh:
                data = _resize(src, width, height, vw, vh)
        dest = ctx.mod_root / texture
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        ctx.track(dest)
    ctx.note(f"menu principal: fondo reemplazado en {', '.join(sorted(targets))}")


def _menu_textures(ctx: BuildContext) -> set[str]:
    sprites: dict[str, str] = {}
    for path in (ctx.vanilla.root / "interface").glob("**/*.gfx"):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        for name, texture in _SPRITE.findall(text):
            sprites.setdefault(name, texture.replace("\\", "/"))
    out = {t for n, t in sprites.items() if t.lower().endswith(".dds") and _NAME.search(n)}

    used: set[str] = set()
    for pattern in ("frontend*.gui", "mainmenu*.gui", "main_menu*.gui"):
        for path in (ctx.vanilla.root / "interface").glob(f"**/{pattern}"):
            try:
                used.update(_GUI_SPRITE.findall(path.read_text(encoding="utf-8-sig", errors="replace")))
            except OSError:
                continue
    small = []
    for name in sorted(used):
        texture = sprites.get(name)
        if not texture or not texture.lower().endswith(".dds"):
            continue
        width, height = _texture_dims(ctx, texture)
        if width >= _MIN_BG_WIDTH:
            out.add(texture)
        elif width and height and width * height >= 256 * 256:
            small.append(f"{name} {width}x{height}")
    if small:
        ctx.note("menu principal: imagenes medianas del menu que NO se tocan: " + ", ".join(small[:15]))
    return out


def _texture_dims(ctx: BuildContext, texture: str) -> tuple[int, int]:
    try:
        with (ctx.vanilla.root / texture).open("rb") as fh:
            return _dims(fh.read(128))
    except OSError:
        return 0, 0


def _dims(data: bytes) -> tuple[int, int]:
    if data[:4] != b"DDS ":
        return 0, 0
    height, width = struct.unpack_from("<II", data, 12)
    return width, height


def _resize(src: bytes, w: int, h: int, nw: int, nh: int) -> bytes:
    """Reescala un DDS A8R8G8B8 sin comprimir (el que escribe art.write_dds).

    Ajusta al ancho nuevo manteniendo la proporción y centra en vertical; las
    filas de arriba y abajo que no tienen imagen repiten la primera/última.
    """
    body = src[128:]
    header = bytearray(src[:128])
    struct.pack_into("<III", header, 12, nh, nw, nw * 4)
    scaled_h = max(1, round(h * nw / w))
    top = (nh - scaled_h) // 2
    rows = []
    xs = [min(w - 1, x * w // nw) * 4 for x in range(nw)]
    for y in range(nh):
        sy = min(h - 1, max(0, (y - top) * h // scaled_h))
        row = body[sy * w * 4:(sy + 1) * w * 4]
        rows.append(b"".join(row[x:x + 4] for x in xs))
    return bytes(header) + b"".join(rows)
