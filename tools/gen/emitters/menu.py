"""Fondo del menú principal (spec/11_scenario.yaml -> main_menu).

No se edita ninguna interfaz vanilla: se buscan en interface/**/*.gfx los
sprites de fondo del menú principal y se escribe nuestra imagen en la MISMA
ruta de textura (el archivo del mod pisa al vanilla). Si la textura vanilla
tiene otro tamaño, la nuestra se reescala a ese tamaño (vecino más cercano,
sin dependencias).

Candidatos: sprites cuyo nombre o textura hablan de menú principal y de fondo
(main_menu / mainmenu / menu + bg / background). Se reportan en reporte.txt;
si no aparece ninguno, se avisa y no se escribe nada.
"""

from __future__ import annotations

import re
import struct

from ..context import BuildContext

_NAME = re.compile(r"(?i)(main_?menu|menu).*(bg|background)|(bg|background).*(main_?menu)")
_SPRITE = re.compile(r'name\s*=\s*"?(GFX_[A-Za-z0-9_]+)"?\s+texturefile\s*=\s*"([^"]+)"', re.S)


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
    out: set[str] = set()
    for path in (ctx.vanilla.root / "interface").glob("**/*.gfx"):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        for name, texture in _SPRITE.findall(text):
            texture = texture.replace("\\", "/")
            if texture.lower().endswith(".dds") and (_NAME.search(name) or _NAME.search(texture)):
                out.add(texture)
    return out


def _dims(data: bytes) -> tuple[int, int]:
    if data[:4] != b"DDS ":
        return 0, 0
    height, width = struct.unpack_from("<II", data, 12)
    return width, height


def _resize(src: bytes, w: int, h: int, nw: int, nh: int) -> bytes:
    """Reescala un DDS A8R8G8B8 sin comprimir (el que escribe art.write_dds)."""
    body = src[128:]
    header = bytearray(src[:128])
    struct.pack_into("<III", header, 12, nh, nw, nw * 4)
    rows = []
    xs = [min(w - 1, x * w // nw) * 4 for x in range(nw)]
    for y in range(nh):
        sy = min(h - 1, y * h // nh)
        row = body[sy * w * 4:(sy + 1) * w * 4]
        rows.append(b"".join(row[x:x + 4] for x in xs))
    return bytes(header) + b"".join(rows)
