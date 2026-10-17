"""Piel de la interfaz (2026-10-15, pedido del usuario: "cambiar la UI, solo
piel"; "empecemos por la barra superior y el panel de Política").

Solo se cambian imágenes: los .gui (dónde va cada cosa) quedan los del juego,
así un parche no rompe nada. Dos partes:

  1. Inventario: por cada pantalla de SCREENS se leen sus .gui del juego
     instalado, los sprites que usan, su textura, su tamaño, cuántos cuadros
     tiene (los botones traen normal/encima/apretado uno al lado del otro) y
     el borde que el juego no estira. Va a build/ui_inventario.txt y
     empezar.py lo empaqueta con las texturas originales en
     ui_para_claude.zip: con eso se piden las imágenes nuevas a medida.

  2. Aplicar: cada assets/ui/piel/<ruta del juego>.dds se escribe sobre la
     textura del juego en esa misma ruta, llevada a su tamaño.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..context import BuildContext

# pantalla -> nombres de los .gui del juego que la dibujan (se buscan en
# interface/ y sus subcarpetas; los que no existan en la versión instalada
# se informan y se saltean)
SCREENS: dict[str, list[str]] = {
    "barra_superior": ["topbar.gui"],
    "politica": ["countrypoliticsview.gui"],
    # la fila de pestañas debajo de la barra (captura del 2026-10-15): la
    # dibujan las ventanas de producción, despliegue y logística
    "pestanas_militares": ["countryproductionview.gui", "countrydeploymentview.gui",
                           "countrylogisticsview.gui"],
}
# Pantallas armadas por nombre de sprite, para lo que el juego elige por
# código y no aparece en ningún .gui (2026-10-17, captura del usuario: "las
# leyes, los placeholders, las notificaciones y las imágenes de la ideología;
# falta el ícono de mercado internacional"). Se buscan en todos los .gfx de
# interface/, solo texturas de gfx/interface/.
PATTERNS: dict[str, list[str]] = {
    "ideologias": [r"ideology", r"ideologies", r"pol_.*party"],
    "notificaciones": [r"alert", r"notification"],
    "mercado": [r"market", r"trade"],
    "huecos_vacios": [r"empty", r"slot", r"placeholder", r"advisor", r"unknown"],
    "leyes": [r"^GFX_idea_(?:.*economic|.*mobilisation|.*conscription|.*export|.*trade|.*isolation|"
              r"civilian_economy|war_economy|free_trade|closed_economy|volunteer_only|disarmed_nation|"
              r"service_by_requirement|all_adults_serve|scraping_the_barrel)"],
}
# .gui que se suman a sus pantallas si existen (nombres no confirmados: los
# que no estén se informan y se saltean)
EXTRA_GUI: dict[str, list[str]] = {
    "notificaciones": ["alerts.gui", "topbar_alerts.gui", "alertsview.gui"],
    "mercado": ["internationalmarket.gui", "international_market.gui", "marketview.gui", "tradeview.gui"],
}
SKIN_DIR = ("assets", "ui", "piel")
SPRITE_KINDS = ("spriteType", "corneredTileSpriteType", "frameAnimatedSpriteType",
                "progressbartype", "textSpriteType", "maskedShieldType")
_GFX_REF = re.compile(r'"?(GFX_[A-Za-z0-9_]+)"?')
_TEX_REF = re.compile(r'"((?:gfx|GFX)/[^"]+\.(?:dds|tga|png))"')
_KEYVAL = re.compile(r'(\w+)\s*=\s*"?([^"\s{}]+)"?')


def _blocks(text: str, keys: tuple[str, ...]):
    """(clave, cuerpo) de cada `clave = { ... }` con llaves anidadas."""
    pat = re.compile(r'\b(' + "|".join(keys) + r')\s*=\s*\{', re.I)
    pos = 0
    while True:
        m = pat.search(text, pos)
        if not m:
            return
        depth, i = 1, m.end()
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        yield m.group(1), text[m.end():i - 1]
        pos = i


def sprite_table(root: Path) -> dict[str, dict]:
    """Sprite -> {tipo, texturas, cuadros, borde, mosaico} de interface/**/*.gfx."""
    out: dict[str, dict] = {}
    for path in sorted((root / "interface").glob("**/*.gfx")):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        for kind, body in _blocks(text, SPRITE_KINDS):
            name = re.search(r'\bname\s*=\s*"?(GFX_[A-Za-z0-9_]+)', body)
            if not name or name.group(1) in out:
                continue
            texs = [t.replace("\\", "/") for t in re.findall(r'texture[Ff]ile\d?\s*=\s*"([^"]+)"', body)]
            frames = re.search(r'noOfFrames\s*=\s*(\d+)', body, re.I)
            border = re.search(r'borderSize\s*=\s*\{\s*x\s*=\s*(\d+)\s*y\s*=\s*(\d+)', body)
            tiling = re.search(r'tilingCenter\s*=\s*(yes|no)', body, re.I)
            out[name.group(1)] = {
                "kind": kind, "textures": texs, "frames": int(frames.group(1)) if frames else 1,
                "border": (int(border.group(1)), int(border.group(2))) if border else None,
                "tiling": bool(tiling and tiling.group(1).lower() == "yes"),
                "file": path.name,
            }
    return out


def inventory(ctx: BuildContext) -> dict[str, list[dict]]:
    """Pantalla -> piezas (una por textura) con sprite, tamaño, cuadros y borde."""
    from .menu import _texture_dims
    root = ctx.vanilla.root
    sprites = sprite_table(root)
    guis = {p.name.lower(): p for p in (root / "interface").glob("**/*.gui")}
    out: dict[str, list[dict]] = {}
    for screen, names in SCREENS.items():
        seen: dict[str, dict] = {}
        for gname in names:
            path = guis.get(gname.lower())
            if path is None:
                ctx.note(f"piel: {screen}: el juego no trae {gname}")
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            for sp in dict.fromkeys(_GFX_REF.findall(text)):
                info = sprites.get(sp)
                if not info:
                    continue
                for tex in info["textures"]:
                    piece = seen.setdefault(tex.lower(), {"texture": tex, "sprites": [], "gui": set(), **info})
                    piece["sprites"].append(sp)
                    piece["gui"].add(path.name)
            for tex in dict.fromkeys(_TEX_REF.findall(text)):
                tex = tex.replace("\\", "/")
                piece = seen.setdefault(tex.lower(), {"texture": tex, "sprites": [], "gui": set(), "kind": "directa",
                                                      "frames": 1, "border": None, "tiling": False})
                piece["gui"].add(path.name)
        pieces = []
        for piece in seen.values():
            w, h = _texture_dims(ctx, piece["texture"])
            piece["size"] = (w, h)
            piece["gui"] = sorted(piece["gui"])
            pieces.append(piece)
        out[screen] = sorted(pieces, key=lambda p: p["texture"].lower())
    for screen, pats in PATTERNS.items():
        seen = {}
        rx = re.compile("|".join(pats), re.I)
        for sp, info in sprites.items():
            if not rx.search(sp):
                continue
            for tex in info["textures"]:
                if not re.sub("/+", "/", tex).lower().startswith("gfx/interface/"):
                    continue
                piece = seen.setdefault(tex.lower(), {"texture": tex, "sprites": [], "gui": {info["file"]}, **info})
                piece["sprites"].append(sp)
        for gname in EXTRA_GUI.get(screen, []):
            path = guis.get(gname.lower())
            if path is None:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            for sp in dict.fromkeys(_GFX_REF.findall(text)):
                info = sprites.get(sp)
                for tex in (info or {}).get("textures", []):
                    piece = seen.setdefault(tex.lower(), {"texture": tex, "sprites": [], "gui": set(), **info})
                    piece["sprites"].append(sp)
                    piece["gui"].add(path.name)
        pieces = []
        for piece in seen.values():
            piece["size"] = _texture_dims(ctx, piece["texture"])
            piece["gui"] = sorted(piece["gui"])
            pieces.append(piece)
        out[screen] = sorted(pieces, key=lambda p: p["texture"].lower())
    return out


def _line(p: dict) -> str:
    w, h = p["size"]
    extra = []
    if p["frames"] > 1:
        extra.append(f"{p['frames']} cuadros de {w // p['frames']}x{h}")
    if p["border"]:
        extra.append(f"borde {p['border'][0]}x{p['border'][1]} " + ("(centro en mosaico)" if p["tiling"] else "(centro estirado)"))
    size = f"{w}x{h}" if w else "tamaño ?"
    return f"  {p['texture']}  {size}  [{p['kind']}]  {', '.join(p['sprites'][:4])}" + \
        (f"  ({'; '.join(extra)})" if extra else "")


def apply_skin(ctx: BuildContext) -> int:
    """assets/ui/piel/<ruta del juego> -> la misma ruta en el mod, a su tamaño."""
    from .menu import _dims, _resize, _texture_dims
    base = ctx.spec.root.parent.joinpath(*SKIN_DIR)
    done = 0
    missing: list[str] = []
    for art in sorted(base.glob("**/*.dds")) if base.exists() else []:
        rel = art.relative_to(base).as_posix()
        vw, vh = _texture_dims(ctx, rel)
        if not (vw and vh):
            missing.append(rel)
            continue
        data = art.read_bytes()
        w, h = _dims(data)
        if (w, h) != (vw, vh):
            if not (w and h):
                ctx.warn(f"piel: {rel} no es un DDS válido; no se usa")
                continue
            data = _resize(data, w, h, vw, vh)
        dest = ctx.mod_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        ctx.track(dest)
        done += 1
    if missing:
        # una sola línea: con un parche que renombra texturas pueden ser muchas
        ctx.warn(f"piel: {len(missing)} texturas no existen en el juego instalado (¿cambiaron de nombre?), "
                 f"no se usan: {', '.join(missing[:12])}{' ...' if len(missing) > 12 else ''}")
    return done


def emit(ctx: BuildContext) -> None:
    if ctx.vanilla is None:
        return
    inv = inventory(ctx)
    lines = ["INVENTARIO DE LA INTERFAZ (piel) — generado por tools/gen/emitters/ui_skin.py",
             "Cada línea: textura del juego, tamaño en píxeles, tipo de sprite, sprites que la usan.",
             "Los botones con N cuadros traen los estados uno al lado del otro (normal, encima, apretado...).",
             "Los de borde: el juego no estira las esquinas; el resto se estira o se repite.", ""]
    files: dict[str, str] = {}
    for screen, pieces in inv.items():
        lines.append(f"== {screen} ({len(pieces)} texturas; {', '.join(sorted({g for p in pieces for g in p['gui']})) or 'sin .gui'})")
        lines += [_line(p) for p in pieces]
        lines.append("")
        for p in pieces:
            src = ctx.vanilla.root / p["texture"]
            if src.exists():
                files.setdefault(p["texture"], str(src))
        ctx.note(f"piel: {screen}: {len(pieces)} texturas")
    path = ctx.out_root / "ui_inventario.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ctx.track(path)
    ctx.data["ui_inventory_path"] = str(path)
    ctx.data["ui_textures"] = files
    done = apply_skin(ctx)
    ctx.note(f"piel: {done} texturas de la interfaz reemplazadas (assets/ui/piel)")
