"""Arte del panel del recurso propio de cada nación (2026-11-15).

  pedidos   lee arte/paneles_recurso.yaml y escribe arte/pedidos_fijos/33_paneles_recurso.txt;
  importar  guarda las piezas que llegan (panel_<panel>_<pieza>.png) achicadas en
            assets/ui/paneles/<panel>/fuente/<pieza>.png;
  dibujar   arma lo que usa el juego en assets/ui/paneles/<panel>/:
              fondo.dds    720 x 800, la carcasa (las zonas claras, oscurecidas para la letra blanca);
              medidor.dds  CUADROS cuadros de LADO x LADO uno al lado del otro: del vacío al lleno,
                           cortando la imagen llena con la forma de `llenado` (vertical, radial,
                           aguja); el cuadro lo elige una variable (tools/gen/emitters/paneles.py);
              boton.dds    la placa de las acciones (boton_tamano: dos columnas en la zona de abajo);
              icono.dds    ICONO, el medidor lleno en miniatura (abre el panel).
            Las zonas de cada fondo (título, medidor, texto, acciones) están en ZONAS: las midió
            tools/arte/paneles.py sobre las piezas que llegaron (zonas lisas) y se corrigieron a mano.

Uso:  python3 -m tools.arte.paneles [pedidos | importar <carpeta> | dibujar [vista.png]]
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "arte" / "paneles_recurso.yaml"
SALIDA = REPO / "arte" / "pedidos_fijos" / "33_paneles_recurso.txt"
DESTINO = REPO / "assets" / "ui" / "paneles"
TAMANOS = {"fondo": (1440, 1600), "medidor": (1024, 1024), "medidor_lleno": (1024, 1024),
           "aguja": (1024, 1024), "boton": (1024, 160)}
QUE = {
    "fondo": "the whole panel frame, OPAQUE, fills the canvas edge to edge. Keep these zones plain and calm "
             "(no objects on them, the game draws there): title band y 0-160; gauge zone x 60-700 y 200-840; "
             "text zone x 760-1380 y 200-840; actions zone x 60-1380 y 900-1520",
    "medidor": "the main gauge of the panel in its EMPTY / OFF state, centred, transparent background",
    "medidor_lleno": "EXACTLY the same object, same position, size and framing pixel for pixel as the "
                     "'medidor' image, but FULL / fully lit; transparent background",
    "aguja": "only the needle, transparent background, pointing straight UP, its axle exactly at the canvas centre",
    "boton": "an empty button plate for an action, centred, transparent background, about 6:1",
}


def _linea(t: str) -> str:
    return " ".join(str(t).split())


def piezas() -> list[dict]:
    import yaml
    cfg = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    out = []
    for panel, p in cfg["paneles"].items():
        for pieza in ("fondo", "medidor", "medidor_lleno", "aguja", "boton"):
            if pieza not in p:
                continue
            out.append({"panel": panel, "pieza": pieza, "id": f"panel_{panel}_{pieza}", "size": TAMANOS[pieza],
                        "transparent": pieza != "fondo", "nombre": p["nombre"], "recurso": p["recurso"],
                        "texto": p[pieza], "comun": cfg["comun"],
                        "dest": DESTINO / panel / "fuente" / f"{pieza}.png"})
    return out


def pedidos() -> int:
    ps = [p for p in piezas() if not p["dest"].exists()]
    lineas = [f"# {len(ps)} PEDIDOS - PANELES DEL RECURSO PROPIO (2026-11-15)",
              "# Una ventana propia por nación (como la Ficha del Líder) con su recurso único: carcasa ilustrada,",
              "# el medidor grande (vacío y lleno, mismo encuadre) y la placa de los botones de acción.",
              "# Cada nación con su propio material y su propio instrumento; nada genérico.",
              "# Mandámelos con el nombre de 'filename'.", ""]
    for p in ps:
        w, h = p["size"]
        lineas += ["ASSET_REQUEST", "type: resource_panel", f"id: {p['id']}", f"filename: {p['id']}.png",
                   f"size: {w}x{h}", f"style: {_linea(p['comun'])}",
                   f"description: Panel \"{p['nombre']}\" ({p['recurso']}). WHAT: {QUE[p['pieza']]}. "
                   f"SUBJECT: {_linea(p['texto'])}",
                   f"transparent_background: {'true' if p['transparent'] else 'false'}", ""]
    SALIDA.write_text("\n".join(lineas), encoding="utf-8")
    return len(ps)


# -- lo que usa el juego ------------------------------------------------------------------

VENTANA = (720, 800)
CUADROS = 21          # 0 %, 5 %, ... 100 %
LADO = 256            # el medidor en el juego (DXT: múltiplo de 4)
ICONO = (64, 64)
FUENTE_LADO = {"fondo": (720, 800), "medidor": (512, 512), "medidor_lleno": (512, 512),
               "aguja": (512, 512), "boton": (512, 80)}
# zonas lisas de cada fondo a 720 x 800: título, medidor (izquierda), texto (derecha), acciones (abajo)
ZONAS = {
    "ASC": {"titulo": (68, 116, 652, 152), "medidor": (48, 188, 340, 480), "texto": (380, 188, 672, 480), "acciones": (28, 552, 688, 724)},
    "EFE": {"titulo": (32, 92, 688, 128), "medidor": (44, 176, 332, 480), "texto": (380, 176, 672, 480), "acciones": (28, 536, 692, 716)},
    "FCU": {"titulo": (28, 48, 692, 84), "medidor": (40, 232, 340, 496), "texto": (380, 232, 680, 496), "acciones": (32, 528, 688, 752)},
    # el mapa de la Alta Mar tiene una rosa de los vientos dibujada: las zonas se juntaron a mano
    "HSN": {"titulo": (92, 84, 628, 112), "medidor": (48, 156, 344, 476), "texto": (380, 156, 676, 476), "acciones": (44, 516, 676, 756)},
    "NAS": {"titulo": (32, 96, 688, 136), "medidor": (80, 184, 332, 472), "texto": (384, 184, 640, 472), "acciones": (28, 548, 692, 752)},
    "SHD": {"titulo": (48, 120, 676, 156), "medidor": (60, 196, 300, 500), "texto": (352, 196, 664, 500), "acciones": (44, 548, 680, 716)},
    "APF": {"titulo": (44, 16, 680, 80), "medidor": (44, 188, 344, 488), "texto": (376, 188, 680, 488), "acciones": (44, 516, 680, 752)},
    # Roma no trae franja de título (el águila ocupa el centro de arriba): el título va arriba del texto
    "NRE": {"titulo": None, "medidor": (68, 148, 320, 508), "texto": (356, 148, 652, 508), "acciones": (68, 548, 652, 756)},
    "ZAL_pompa": {"titulo": (92, 32, 632, 84), "medidor": (72, 140, 340, 520), "texto": (380, 140, 648, 520), "acciones": (36, 568, 684, 752)},
    # el Nodo de Londres parte la franja de arriba con el anillo de fibras: el título va a la izquierda
    "ZAL_sincronia": {"titulo": (44, 60, 332, 112), "medidor": (32, 140, 324, 444), "texto": (352, 140, 688, 444), "acciones": (32, 480, 688, 752)},
    "ZJP": {"titulo": (56, 88, 664, 128), "medidor": (56, 168, 340, 492), "texto": (380, 168, 664, 492), "acciones": (56, 528, 664, 716)},
}
# cómo se llena cada medidor: vertical (de abajo arriba), radial (desde arriba, en el sentido del
# reloj; `arco`: de izquierda a derecha por arriba) o aguja (barrido y aguja de -RANGO a +RANGO grados)
LLENADO = {
    "EFE": {"tipo": "vertical"}, "HSN": {"tipo": "vertical"}, "SHD": {"tipo": "vertical"}, "ZJP": {"tipo": "vertical"},
    "ASC": {"tipo": "radial"}, "NAS": {"tipo": "radial"}, "APF": {"tipo": "radial"}, "ZAL_sincronia": {"tipo": "radial"},
    "NRE": {"tipo": "arco", "centro": (512, 700)},
    "FCU": {"tipo": "aguja", "rango": 135}, "ZAL_pompa": {"tipo": "aguja", "rango": 110},
}
PASO_ACCION = 58      # alto de cada fila de acciones (botón de 52 + 6)


def boton_tamano(panel: str) -> tuple[int, int]:
    """Dos columnas de botones dentro de la zona de acciones (con lugar para la barra de desplazamiento)."""
    x0, _, x1, _ = ZONAS[panel]["acciones"]
    return ((x1 - x0 - 40) // 2 // 4 * 4, 52)


CLARO = 105           # brillo medio desde el que una zona se oscurece (la letra del panel es blanca)


def importar(carpeta: str) -> list[str]:
    """panel_<panel>_<pieza>.png de una carpeta (y sus subcarpetas) -> fuente/<pieza>.png achicada."""
    from PIL import Image
    hechas, raras = [], []
    paneles = sorted({p["panel"] for p in piezas()}, key=len, reverse=True)
    for f in sorted(Path(carpeta).rglob("panel_*.png")):
        nombre = f.stem[len("panel_"):]
        panel = next((p for p in paneles if nombre.startswith(p + "_")), None)
        pieza = nombre[len(panel) + 1:] if panel else None
        if pieza not in FUENTE_LADO:
            raras.append(f.name)
            continue
        img = Image.open(f).convert("RGBA")
        img = img.resize(FUENTE_LADO[pieza], Image.LANCZOS)
        if pieza == "fondo":
            img = img.convert("RGB")
        dest = DESTINO / panel / "fuente" / f"{pieza}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, optimize=True)
        hechas.append(f"{panel}/{pieza}")
    return [f"paneles: {len(hechas)} piezas importadas"] + ([f"no reconocidas: {', '.join(raras)}"] if raras else [])


def _fuente(panel: str, pieza: str):
    from PIL import Image
    p = DESTINO / panel / "fuente" / f"{pieza}.png"
    return Image.open(p).convert("RGBA") if p.exists() else None


def _guardar(img, dest: Path, formato: str = "DXT5") -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    (img.convert("RGB") if formato == "DXT1" else img.convert("RGBA")).save(dest, "DDS", pixel_format=formato)


def _brillo(img, caja) -> float:
    from PIL import ImageStat
    return ImageStat.Stat(img.convert("L").crop(caja)).mean[0]


def fondo(panel: str):
    """La carcasa a 720 x 800; las zonas claras (papel, ocre, jade) con un velo oscuro para la letra."""
    from PIL import Image, ImageDraw, ImageFilter
    img = _fuente(panel, "fondo").resize(VENTANA, Image.LANCZOS)
    mx0, my0, mx1, my1 = ZONAS[panel]["medidor"]
    cajas = {"texto": ZONAS[panel]["texto"], "acciones": ZONAS[panel]["acciones"], "titulo": ZONAS[panel]["titulo"],
             # la franja del número, debajo del medidor
             "valor": (mx0 + 10, my1 - 34, mx1 - 10, my1 - 2)}
    for clave in ("texto", "acciones", "titulo", "valor"):
        caja = cajas[clave]
        if not caja:
            continue
        b = _brillo(img, caja)
        if b < CLARO:
            continue
        velo = Image.new("L", img.size, 0)
        x0, y0, x1, y1 = caja
        ImageDraw.Draw(velo).rounded_rectangle((x0 + 2, y0 + 2, x1 - 2, y1 - 2), 6, fill=255)
        velo = velo.filter(ImageFilter.GaussianBlur(3))
        fuerza = min(0.72, (b - 60) / max(b, 1))   # deja la zona en ~60 de brillo, sin taparla
        negro = Image.new("RGBA", img.size, (12, 10, 8, 255))
        img = Image.composite(negro, img, velo.point(lambda v: int(v * fuerza)))
    return img


def _mascara(panel: str, f: float, lado: int, lleno):
    """La parte de la imagen llena que se ve con la fracción f (0 a 1)."""
    from PIL import Image, ImageChops, ImageDraw
    m = Image.new("L", (lado, lado), 0)
    if f <= 0:
        return m
    d = ImageDraw.Draw(m)
    cfg = LLENADO[panel]
    k = lado / 1024
    if cfg["tipo"] == "vertical":
        # de la base al tope de lo que cambia entre vacío y lleno
        x0, y0, x1, y1 = _cambia(panel, lado)
        y = y1 - (y1 - y0) * f
        d.rectangle((0, y, lado, lado), fill=255)
    elif cfg["tipo"] == "radial":
        d.pieslice((-lado, -lado, 2 * lado, 2 * lado), -90, -90 + 360 * f, fill=255)
    elif cfg["tipo"] == "arco":
        cx, cy = (v * k for v in cfg["centro"])
        r = 3 * lado
        d.pieslice((cx - r, cy - r, cx + r, cy + r), 180, 180 + 180 * f, fill=255)
        d.rectangle((0, cy, lado, lado), fill=255 if f >= 1 else 0)
    else:   # aguja: el arco iluminado barre desde -rango
        g = cfg["rango"]
        d.pieslice((-lado, -lado, 2 * lado, 2 * lado), -90 - g, -90 - g + 2 * g * f, fill=255)
    return ImageChops.multiply(m, lleno.getchannel("A"))


_CAMBIA: dict = {}


def _cambia(panel: str, lado: int):
    """Caja de lo que cambia entre el medidor vacío y el lleno (para el llenado vertical)."""
    from PIL import ImageChops
    if (panel, lado) not in _CAMBIA:
        a = _fuente(panel, "medidor").resize((lado, lado))
        b = _fuente(panel, "medidor_lleno").resize((lado, lado))
        d = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).convert("L").point(lambda v: 255 if v > 40 else 0)
        _CAMBIA[(panel, lado)] = d.getbbox() or (0, 0, lado, lado)
    return _CAMBIA[(panel, lado)]


def cuadro(panel: str, f: float, lado: int = LADO):
    from PIL import Image
    vacio = _fuente(panel, "medidor").resize((lado, lado), Image.LANCZOS)
    lleno = _fuente(panel, "medidor_lleno").resize((lado, lado), Image.LANCZOS)
    out = vacio.copy()
    out.paste(lleno, (0, 0), _mascara(panel, f, lado, lleno))
    aguja = _fuente(panel, "aguja")
    if aguja is not None and LLENADO[panel]["tipo"] == "aguja":
        g = LLENADO[panel]["rango"]
        a = aguja.resize((lado, lado), Image.LANCZOS).rotate(g - 2 * g * f, resample=Image.BICUBIC)
        out.alpha_composite(a)
    return out


def medidor(panel: str):
    from PIL import Image
    tira = Image.new("RGBA", (LADO * CUADROS, LADO), (0, 0, 0, 0))
    for i in range(CUADROS):
        tira.paste(cuadro(panel, i / (CUADROS - 1)), (i * LADO, 0))
    return tira


def boton(panel: str):
    """La placa de las acciones; si es clara, el centro se oscurece para la letra blanca."""
    from PIL import Image, ImageDraw, ImageFilter
    w, h = boton_tamano(panel)
    img = _fuente(panel, "boton").resize((w, h), Image.LANCZOS)
    caja = (w // 8, h // 4, w * 7 // 8, h * 3 // 4)
    b = _brillo(img, caja)
    if b >= CLARO:
        velo = Image.new("L", img.size, 0)
        ImageDraw.Draw(velo).rounded_rectangle((w // 14, h // 5, w - w // 14, h - h // 5), h // 5, fill=255)
        velo = velo.filter(ImageFilter.GaussianBlur(2))
        fuerza = min(0.7, (b - 55) / max(b, 1))
        img.paste(Image.new("RGBA", img.size, (14, 12, 10, 255)), (0, 0),
                  Image.composite(velo.point(lambda v: int(v * fuerza)), Image.new("L", img.size, 0), img.getchannel("A")))
    return img


def icono(panel: str):
    from PIL import Image
    img = cuadro(panel, 1.0, 256)
    img = img.crop(img.getbbox() or (0, 0, 256, 256))
    img.thumbnail(ICONO, Image.LANCZOS)
    out = Image.new("RGBA", ICONO, (0, 0, 0, 0))
    out.alpha_composite(img, ((ICONO[0] - img.width) // 2, (ICONO[1] - img.height) // 2))
    return out


def dibujar() -> list[str]:
    hechos, faltan = [], []
    for panel in ZONAS:
        need = ["fondo", "medidor", "medidor_lleno", "boton"] + (["aguja"] if LLENADO[panel]["tipo"] == "aguja" else [])
        if any(_fuente(panel, p) is None for p in need):
            faltan.append(panel)
            continue
        base = DESTINO / panel
        _guardar(fondo(panel), base / "fondo.dds", "DXT1")
        _guardar(medidor(panel), base / "medidor.dds")
        _guardar(boton(panel), base / "boton.dds")
        _guardar(icono(panel), base / "icono.dds")
        hechos.append(panel)
    return [f"paneles: {len(hechos)} armados ({', '.join(hechos)})"] + ([f"sin arte: {', '.join(faltan)}"] if faltan else [])


def vista_previa(dest: Path, panel: str = "ASC") -> None:
    """Un panel armado como en el juego, con un medidor a mitad y texto de prueba."""
    from PIL import Image, ImageDraw, ImageFont
    img = fondo(panel).convert("RGBA")
    z = ZONAS[panel]
    x0, y0, x1, y1 = z["medidor"]
    lado = min(x1 - x0, y1 - y0 - 34)
    g = cuadro(panel, 0.55).resize((lado, lado), Image.LANCZOS)
    img.alpha_composite(g, (x0 + (x1 - x0 - lado) // 2, y0))
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        t = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except OSError:
        f = t = ImageFont.load_default()
    d = ImageDraw.Draw(img)
    caja_t = z["titulo"] or (z["texto"][0], z["texto"][1], z["texto"][2], z["texto"][1] + 30)
    d.text(((caja_t[0] + caja_t[2]) // 2, (caja_t[1] + caja_t[3]) // 2), panel.upper(), font=f, fill=(232, 226, 210), anchor="mm")
    d.text((x0 + (x1 - x0) // 2, y1 - 16), "82 / 150", font=f, fill=(232, 226, 210), anchor="mm")
    tx0, ty0, tx1, ty1 = z["texto"]
    for k in range(14):
        d.text((tx0 + 10, ty0 + (36 if not z["titulo"] else 10) + k * 17), "Texto de prueba del recurso, línea %d" % k,
               font=t, fill=(232, 226, 210))
    b = boton(panel)
    bw, bh = b.size
    ax0, ay0, ax1, ay1 = z["acciones"]
    for k in range(6):
        x = ax0 + 8 + (k % 2) * (bw + 4)
        y = ay0 + 8 + (k // 2) * PASO_ACCION
        if y + bh > ay1:
            break
        img.alpha_composite(b, (x, y))
        d.text((x + bw // 2, y + bh // 2), "Acción %d (25 PP)" % (k + 1), font=t, fill=(232, 226, 210), anchor="mm")
    img.alpha_composite(icono(panel), (VENTANA[0] - 70, VENTANA[1] - 70))
    img.convert("RGB").save(dest)


if __name__ == "__main__":
    import sys
    orden = sys.argv[1] if len(sys.argv) > 1 else "pedidos"
    if orden == "pedidos":
        print(f"paneles: {pedidos()} pedidos en {SALIDA.relative_to(REPO)}")
    elif orden == "importar":
        print("\n".join(importar(sys.argv[2])))
    elif orden == "dibujar":
        print("\n".join(dibujar()))
        if len(sys.argv) > 2:
            for panel in ZONAS:
                vista_previa(Path(sys.argv[2]).with_name(f"{Path(sys.argv[2]).stem}_{panel}.png"), panel)
