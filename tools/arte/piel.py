"""Piel de la interfaz: arma assets/ui/piel/ desde las texturas originales.

Pedido (2026-10-15): "cambiar la UI, solo piel", empezando por la barra
superior, el panel de Política y las pestañas militares. El usuario corre el
build, que arma ui_para_claude.zip con el inventario y las texturas del juego;
con eso se hace todo esto (2026-10-16).

Dos caminos, los dos en arte/piel_interfaz.yaml:

  retexturar  marcos, barras, paneles y botones: se conserva la forma, el
              relieve y la transparencia del original (así todo sigue
              calzando con los .gui del juego) y se le pone el material del
              mod (el mismo metal grafito de fondo_ventanas). Los dorados y
              bronces pasan al acento verde azulado; los demás colores
              (rojos, verdes, azules) significan algo y quedan como están.
  iconos      dibujos nuevos pedidos a ChatGPT (tipo ui_icon): los de la
              barra de herramientas van sobre la placa del botón, sin el
              dibujo viejo; los de recursos reemplazan al ícono entero.

    python3 -m tools.arte.arte piel [carpeta con originales/]

El build no necesita nada de esto: solo copia assets/ui/piel/ (ui_skin.py).
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "arte" / "piel_interfaz.yaml"
SKIN = REPO / "assets" / "ui" / "piel"
ICONS = REPO / "assets" / "ui" / "piel_iconos"
# donde quedó el zip del usuario descomprimido (carpeta compartida del proyecto)
ORIGINALES = Path("/mnt/project-files/arte/ui_originales")

# paleta: sombras grafito azuladas, medios acero, luces acero claro
BASE = {"black": (6, 9, 12), "mid": (62, 72, 80), "white": (205, 220, 228), "midpoint": 96}
ACENTO = {"black": (0, 18, 22), "mid": (20, 140, 150), "white": (165, 250, 240), "midpoint": 90}
# tonos dorados, bronces y marrones (H de PIL, 0-255): esos pasan al acento
DORADO = (8, 42)

# 2026-11-03 (maquetas aprobadas: "cristal y cobre de base"): sobre lo de arriba
# (grafito + verde azulado) va un segundo paso, cristal_y_cobre(): lo oscuro
# pasa a cristal (negro azulado verdoso), los bordes y relieves claros a cobre
# y el verde azulado del acento también a cobre. Los demás colores (rojo,
# verde, azul: significan algo) quedan.
# rampa por brillo: (brillo del grafito, color nuevo)
# 2026-11-03 (captura: el cobre de los íconos salía naranja fuego): cobre más metálico
CRISTAL = [(0, (3, 8, 11)), (30, (14, 25, 31)), (50, (30, 40, 44)), (64, (78, 56, 40)),
           (85, (138, 100, 72)), (110, (184, 140, 106)), (150, (214, 182, 152)),
           (185, (230, 214, 192)), (255, (246, 240, 230))]
COBRE = [(0, (22, 12, 6)), (60, (84, 54, 34)), (120, (156, 112, 80)), (190, (214, 178, 146)),
         (255, (246, 228, 208))]
TURQUESA = (100, 150)   # H de PIL del acento verde azulado que pasa a cobre


def cargar() -> dict:
    import yaml
    return yaml.safe_load(SPEC.read_text(encoding="utf-8")) or {}


def _material(path: Path):
    from PIL import Image, ImageStat
    mat = Image.open(path).convert("L")
    m = ImageStat.Stat(mat).mean[0]
    return mat.point(lambda v: max(0, min(255, int(128 + (v - m) * 1.6))))


def _tile(img, w: int, h: int):
    from PIL import Image
    out = Image.new(img.mode, (w, h))
    for y in range(0, h, img.height):
        for x in range(0, w, img.width):
            out.paste(img, (x, y))
    return out


def retexturar(img, material):
    """Misma forma y relieve, material del mod; dorado -> acento."""
    from PIL import Image, ImageChops, ImageOps
    img = img.convert("RGBA")
    w, h = img.size
    alpha = img.getchannel("A")
    rgb = img.convert("RGB")
    lum = rgb.convert("L")
    base = ImageOps.colorize(lum, **BASE)
    base = ImageChops.soft_light(base, _tile(material, w, h).convert("RGB"))
    hsv = rgb.convert("HSV")
    hue, sat, val = hsv.split()
    m_sat = sat.point(lambda s: 0 if s < 50 else min(255, (s - 50) * 3))
    m_val = val.point(lambda v: 0 if v < 35 else min(255, (v - 35) * 4))
    color = ImageChops.multiply(m_sat, m_val)
    gold = hue.point(lambda x: 255 if DORADO[0] <= x <= DORADO[1] else 0)
    m_gold = ImageChops.multiply(color, gold)
    m_other = ImageChops.multiply(color, ImageChops.invert(gold))
    accent = ImageOps.colorize(lum, **ACENTO)
    out = Image.composite(rgb, base, m_other)
    out = Image.composite(accent, out, m_gold).convert("RGBA")
    out.putalpha(alpha)
    return out


def _rampa(puntos):
    """Tabla de 256 colores interpolando la rampa (brillo -> color)."""
    tabla = []
    for v in range(256):
        for (a, ca), (b, cb) in zip(puntos, puntos[1:]):
            if a <= v <= b:
                t = (v - a) / (b - a) if b > a else 0
                tabla.append(tuple(round(ca[i] + (cb[i] - ca[i]) * t) for i in range(3)))
                break
    return tabla


def cristal_y_cobre(img, todo: bool = False):
    """Grafito -> cristal, relieves claros y acento verde azulado -> cobre.
    Misma forma y transparencia; los colores que dicen algo quedan."""
    from PIL import Image, ImageChops
    img = img.convert("RGBA")
    alpha = img.getchannel("A")
    rgb = img.convert("RGB")
    lum = rgb.convert("L")
    if min(img.size) >= 48:
        # el cristal es liso: se borran las rayitas del grafito, los bordes quedan
        from PIL import ImageFilter
        lum = lum.filter(ImageFilter.MedianFilter(3))
    def pintar(rampa):
        t = _rampa(rampa)
        return Image.merge("RGB", [lum.point([c[i] for c in t]) for i in range(3)])
    vidrio = pintar(CRISTAL)
    cobre = pintar(COBRE)
    hue, sat, val = rgb.convert("HSV").split()
    color = ImageChops.multiply(sat.point(lambda x: 0 if x < 45 else min(255, (x - 45) * 3)),
                                val.point(lambda x: 0 if x < 30 else min(255, (x - 30) * 4)))
    turq = ImageChops.multiply(color, hue.point(lambda x: 255 if TURQUESA[0] <= x <= TURQUESA[1] else 0))
    otro = ImageChops.multiply(color, ImageChops.invert(hue.point(lambda x: 255 if TURQUESA[0] <= x <= TURQUESA[1] else 0)))
    if todo:
        # retexturar_todo (2026-11-03): los botones verdes del juego también pasan a cobre
        turq, otro = color, Image.new("L", img.size, 0)
    out = Image.composite(rgb, vidrio, otro)
    out = Image.composite(cobre, out, turq).convert("RGBA")
    out.putalpha(alpha)
    return out


def boton_nuevo(original, n: int):
    """Botón dibujado de cero como en la maqueta (2026-11-03): vidrio azul petróleo con
    borde de cobre, en la forma (transparencia) del original y con sus cuadros: el
    primero normal, el segundo (mouse encima) más claro, el tercero (apretado) más oscuro."""
    from PIL import Image, ImageChops, ImageFilter
    frames = _frames(original.convert("RGBA"), n)
    out = []
    for i, f in enumerate(frames):
        w, h = f.size
        alpha = f.getchannel("A")
        k = 1.0 if i == 0 else (1.35 if i == 1 else 0.75)
        cuerpo = Image.new("RGB", (w, h))
        px = cuerpo.load()
        for y in range(h):
            t = y / max(1, h - 1)
            top, bot = (40, 58, 66), (12, 21, 27)
            c = tuple(min(255, round((top[j] + (bot[j] - top[j]) * t) * k)) for j in range(3))
            for x in range(w):
                px[x, y] = c
        # borde de cobre: el contorno de la forma (2 px), más claro arriba
        duro = alpha.point(lambda a: 255 if a > 100 else 0)
        adentro = duro.filter(ImageFilter.MinFilter(5))
        borde = ImageChops.subtract(duro, adentro)
        cobre = Image.new("RGB", (w, h))
        cp = cobre.load()
        for y in range(h):
            t = y / max(1, h - 1)
            c = (round(240 + (107 - 240) * t), round(181 + (58 - 181) * t), round(133 + (28 - 133) * t))
            for x in range(w):
                cp[x, y] = c
        img = Image.composite(cobre, cuerpo, borde).convert("RGBA")
        # un brillo fino arriba, adentro del borde
        brillo = ImageChops.subtract(adentro, adentro.transform((w, h), Image.AFFINE, (1, 0, 0, 0, 1, 1)))
        luz = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        luz.putalpha(brillo.point(lambda a: 40 if a else 0))
        img.alpha_composite(luz)
        img.putalpha(alpha)
        out.append(img)
    return _join(out)


def convertir_a_cobre() -> list[str]:
    """Una sola vez (2026-11-03): pasa a cristal y cobre lo que ya está en
    assets/ui/piel/ (hecho en grafito el 2026-10-16), sin necesitar los
    originales. Lo ya convertido se anota en .cobre y no se repite. Las tiras de
    íconos (edificios, recursos: sus colores dicen algo) y la foto del líder
    sin retrato quedan como están."""
    from PIL import Image
    spec = cargar()
    fuera = {p["textura"] for p in spec.get("tiras") or []}
    fuera |= {p["textura"] for p in spec.get("iconos") or [] if p.get("uso") == "foto"}
    marca = SKIN / ".cobre"
    hechas = set(marca.read_text(encoding="utf-8").split()) if marca.exists() else set()
    nuevas = []
    for path in sorted(SKIN.glob("**/*.dds")):
        rel = path.relative_to(SKIN).as_posix()
        if rel in fuera or rel in hechas:
            continue
        _escribir(cristal_y_cobre(Image.open(path)), rel)
        nuevas.append(rel)
    marca.write_text("\n".join(sorted(hechas | set(nuevas))) + "\n", encoding="utf-8")
    return [f"piel: {len(nuevas)} texturas pasadas a cristal y cobre ({len(hechas)} ya estaban)"]


def _icono_path(ident: str):
    """La versión nueva del ícono (<id>_v2.dds, rediseño 2026-11-03) si llegó; si no, la de antes."""
    nuevo = ICONS / f"{ident}_v2.dds"
    return nuevo if nuevo.exists() else ICONS / f"{ident}.dds"


def _frames(img, n: int):
    fw = img.width // n
    return [img.crop((i * fw, 0, (i + 1) * fw, img.height)) for i in range(n)]


def _join(frames):
    from PIL import Image
    out = Image.new("RGBA", (sum(f.width for f in frames), frames[0].height), (0, 0, 0, 0))
    x = 0
    for f in frames:
        out.paste(f, (x, 0))
        x += f.width
    return out


def _fit(icon, w: int, h: int, fill: float = 1.0):
    """Ícono entero dentro de w x h, centrado, recortado su aire transparente."""
    from PIL import Image
    box = icon.getchannel("A").point(lambda a: 255 if a > 16 else 0).getbbox()
    if box:
        icon = icon.crop(box)
    s = min(w * fill / icon.width, h * fill / icon.height)
    icon = icon.resize((max(1, round(icon.width * s)), max(1, round(icon.height * s))), Image.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(icon, ((w - icon.width) // 2, (h - icon.height) // 2))
    return out


def _brillo(img, k: float):
    from PIL import ImageEnhance
    a = img.getchannel("A")
    out = ImageEnhance.Brightness(img.convert("RGB")).enhance(k).convert("RGBA")
    out.putalpha(a)
    return out


def _placa(frame, borde: int):
    """La placa del botón de la barra sin el dibujo: el interior se rellena
    con la transparencia de la columna de adentro del borde, fila por fila."""
    out = frame.copy()
    w, h = out.size
    px = out.load()
    for y in range(borde, h - borde):
        a = frame.getpixel((borde - 1, y))[3] if frame.getpixel((borde - 1, y))[:3] == (0, 0, 0) else 40
        for x in range(borde, w - borde):
            px[x, y] = (0, 0, 0, min(a, 60))
    return out


def _chevrones(w: int, h: int, color, arriba: bool):
    """Dos flechas chicas (sube / baja) para los estados del combustible."""
    from PIL import Image, ImageDraw
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    cw, ch = max(4, w // 3), max(3, h // 5)
    x0 = w // 2 - cw // 2 - 3
    for i in range(2):
        y = h - 2 - (i + 1) * (ch + 1)
        pts = ([(x0, y + ch), (x0 + cw // 2, y), (x0 + cw, y + ch)] if arriba
               else [(x0, y), (x0 + cw // 2, y + ch), (x0 + cw, y)])
        d.line(pts, fill=(0, 0, 0, 255), width=3)
        d.line(pts, fill=color + (255,), width=1)
    return out


def _caja(frame):
    """Dónde está el dibujo en el cuadro original (lo opaco y no negro): el
    nuevo va en esa misma caja, así queda del tamaño y en el lugar del juego
    (2026-10-17: "corregir escala de los íconos (y posición), están grandes")."""
    w, h = frame.size
    px = frame.load()
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 128 and max(r, g, b) > 40:
                xs.append(x)
                ys.append(y)
    if not xs:
        return (2, 2, w - 2, h - 2)
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def _en_caja(icon, size, caja):
    """El ícono nuevo dentro de la caja del original, centrado en ella."""
    from PIL import Image
    l, t, r, b = caja
    dib = _fit(icon, r - l, b - t)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.alpha_composite(dib, (l, t))
    return out


def _icono(pieza: dict, original, material):
    """Textura final de una pieza con ícono nuevo (o None si todavía no llegó)."""
    from PIL import Image, ImageFilter
    path = _icono_path(pieza['id'])
    if not path.exists():
        return None
    icon = Image.open(path).convert("RGBA")
    n = int(pieza.get("cuadros", 1))
    frames = _frames(original, n)
    uso = pieza.get("uso", "directo")
    fw, fh = frames[0].size
    if uso == "barra":
        out = []
        caja = _caja(frames[0])   # la misma caja en los dos cuadros: el dibujo no salta al pasar el mouse
        for i, f in enumerate(frames):
            placa = retexturar(_placa(f, 4), material)
            dib = _en_caja(icon, (fw, fh), caja)
            placa.alpha_composite(_brillo(dib, 0.82 if i == 0 else 1.12))
            out.append(placa)
        return _join(out)
    if uso == "foto":
        s = max(fw / icon.width, fh / icon.height)
        icon = icon.resize((max(fw, round(icon.width * s)), max(fh, round(icon.height * s))), Image.LANCZOS)
        left, top = (icon.width - fw) // 2, (icon.height - fh) // 2
        return _join([icon.crop((left, top, left + fw, top + fh))] * n)
    dib = _en_caja(icon, (fw, fh), _caja(frames[0]))
    if uso == "combustible":
        # 0 estable, 1 subiendo (flechas verdes), 2 bajando (rojas), como el juego
        out = [dib]
        for color, up in (((80, 220, 90), True), ((230, 60, 50), False))[: n - 1]:
            f = dib.copy()
            f.alpha_composite(_chevrones(fw, fh, color, up))
            out.append(f)
        return _join(out)
    if uso == "resaltado":
        # cuadro 2: el mismo con un contorno claro
        halo = dib.getchannel("A").filter(ImageFilter.MaxFilter(3))
        lit = Image.new("RGBA", (fw, fh), (190, 250, 245, 0))
        lit.putalpha(halo.point(lambda a: min(200, a)))
        lit.alpha_composite(dib)
        return _join([dib, lit] + [dib] * (n - 2))
    return _join([dib] * n)


def _tira(pieza: dict, original, material):
    """Una tira de íconos (2026-10-28: edificios y recursos): cada cuadro con
    ícono nuevo se arma; los demás quedan como el original. None si no llegó ninguno."""
    from PIL import Image
    n = int(pieza["cuadros"])
    frames = _frames(original, n)
    uso = pieza.get("uso", "directo")
    out, puestos = [], 0
    for k, f in enumerate(frames, start=1):
        ident = (pieza.get("iconos") or {}).get(k)
        path = _icono_path(ident) if ident else None
        if not path or not path.exists():
            out.append(f)
            continue
        icon = Image.open(path).convert("RGBA")
        caja = _caja(f)
        if uso != "barra":
            # los recursos del juego son finos (la gota del petróleo): el nuevo,
            # cuadrado, quedaba chiquito; va en todo el cuadro con 1 px de aire
            caja = (1, 1, f.width - 1, f.height - 1)
        if uso == "barra":
            placa = retexturar(_placa(f, int(pieza.get("borde", 4))), material)
            placa.alpha_composite(_en_caja(icon, f.size, caja))
            out.append(placa)
        else:
            dib = _en_caja(icon, f.size, caja)
            if uso == "falta":
                # como el juego: un resplandor de fuego alrededor y el dibujo
                # apenas teñido (2026-10-28: el teñido entero quedaba rosa)
                from PIL import ImageFilter
                a = dib.getchannel("A").filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
                fuego = Image.new("RGBA", f.size, (240, 90, 20, 0))
                fuego.putalpha(a.point(lambda v: min(255, v * 2)))
                rojo = Image.new("RGBA", f.size, (230, 60, 40, 0))
                rojo.putalpha(dib.getchannel("A").point(lambda v: v * 25 // 100))
                dib.alpha_composite(rojo)
                fuego.alpha_composite(dib)
                dib = fuego
            out.append(dib)
        puestos += 1
    return _join(out) if puestos else None


def _escribir(img, rel: str) -> None:
    from tools.gen import art
    dest = SKIN / rel
    raw = img.convert("RGBA").tobytes()
    art.write_dds(dest, img.width, img.height, [tuple(raw[k:k + 4]) for k in range(0, len(raw), 4)])


def aplicar(originales: str | None = None) -> list[str]:
    from PIL import Image
    root = Path(originales) if originales else ORIGINALES
    if (root / "originales").is_dir():
        root = root / "originales"
    spec = cargar()
    material = _material(REPO / spec.get("material", "assets/ui/fondo_ventanas.dds"))
    iconos = {p["textura"]: p for p in spec.get("iconos") or []}
    # cuadros y mosaico de cada textura, del inventario que viene en el zip
    import re as _re
    cuadros: dict[str, tuple[int, bool]] = {}
    inv = (root.parent / "ui_inventario.txt") if (root.parent / "ui_inventario.txt").exists() else root / "ui_inventario.txt"
    if inv.exists():
        for linea in inv.read_text(encoding="utf-8").splitlines():
            if not linea.startswith("  gfx"):
                continue
            rel_ = _re.sub("/+", "/", linea.split()[0])
            m = _re.search(r"\((\d+) cuadros", linea)
            # las que el juego estira o repite por partes (borde fijo) no llevan escuadras propias
            cuadros[rel_] = (int(m.group(1)) if m else 1, "centro en mosaico" in linea, "borde " in linea)
    # las que tienen un dibujo que hay que conservar (alertas, íconos): solo cambian de color
    conservar = set(spec.get("conservar_dibujo") or [])
    hechas, faltan, con_icono = [], [], []
    for rel in list(dict.fromkeys((spec.get("retexturar") or []) + list(iconos))):
        src = root / rel
        if not src.exists():
            faltan.append(rel)
            continue
        original = Image.open(src).convert("RGBA")
        img = None
        if rel in iconos:
            img = _icono(iconos[rel], original, material)
            if img is not None:
                con_icono.append(rel)
        if img is None:
            if rel not in (spec.get("retexturar") or []):
                continue
            nuevos = {b["textura"]: b for b in spec.get("botones_nuevos") or []}
            if rel in nuevos:
                img = boton_nuevo(original, int(nuevos[rel].get("cuadros", 1)))
                _escribir(img, rel)
                hechas.append(rel)
                continue
            info = cuadros.get(rel, (1, False, False))
            if (min(original.size) >= 20 and max(original.size) >= 48 and rel not in conservar):
                # 2026-11-03 ("cambiar radicalmente TODO el GUI [...] seguir los primeros mockups"):
                # la pieza se dibuja de nuevo en cristal y cobre (tools/arte/rediseno.py)
                from tools.arte.rediseno import redibujar_cuadros
                esq = False if ("midsection" in rel or "middle" in rel or "tileable" in rel
                                or "event_report" in rel) else None
                _escribir(redibujar_cuadros(original, info[0], mosaico=info[1], esquinas=esq), rel)
                hechas.append(rel)
                continue
            img = retexturar(original, material)
        if not (rel in iconos and iconos[rel].get("uso") == "foto"):
            img = cristal_y_cobre(img, rel in set(spec.get("retexturar_todo") or []))
        _escribir(img, rel)
        hechas.append(rel)
    marca = SKIN / ".cobre"   # lo hecho desde los originales ya está en cobre
    previas = set(marca.read_text(encoding="utf-8").split()) if marca.exists() else set()
    marca.write_text("\n".join(sorted(previas | set(hechas))) + "\n", encoding="utf-8")
    for pieza in spec.get("tiras") or []:
        rel = pieza["textura"]
        src = root / rel
        if not src.exists():
            faltan.append(rel)
            continue
        img = _tira(pieza, Image.open(src).convert("RGBA"), material)
        if img is not None:
            _escribir(img, rel)
            hechas.append(rel)
            con_icono.append(rel)
    lines = [f"piel: {len(hechas)} texturas escritas en {SKIN.relative_to(REPO)} ({len(con_icono)} con ícono nuevo)"]
    if faltan:
        lines.append(f"piel: sin original en {root}: {', '.join(faltan)}")
    return lines


def main(argv: list[str]) -> None:
    import sys
    sys.path.insert(0, str(REPO))
    if argv and argv[0] == "cobre":
        for line in convertir_a_cobre():
            print(line)
        return
    for line in aplicar(argv[0] if argv else None):
        print(line)
