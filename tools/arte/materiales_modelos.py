"""Mapas de material para los modelos 3D y el pase al formato del juego (2026-11-09).

Las convenciones salen de un tanque del juego (FIN_light_armor_*.dds, 512x512, DXT5):

  _diffuse   RGB el color, A = 255.
  _normal    R = G = inclinación hacia la derecha (X), B = 0, A = inclinación en Y con +Y hacia
             ABAJO de la imagen (estilo DirectX). Medido: R sigue a -d(luz)/dx y A a -d(luz)/dy.
  _specular  R = 0, G = intensidad del brillo (media ~71), B = parecido a G un poco más bajo
             (media ~58), A = lisura (media ~69: casi todo mate, con zonas pulidas).

Dos usos:

  python -m tools.arte.materiales_modelos blender <salida/>
      De cada muestra de assets/modelos/texturas/ arma lo que Blender necesita: color, normal
      (RGB estilo OpenGL, el que Blender lee), rugosidad y metal (color y rugosidad en jpg, normal y metal en png). Para asignar y hornear.

  python -m tools.arte.materiales_modelos paradox <carpeta con los png horneados> <salida/>
      Lo que vuelve de Blender (<id>_color.png, <id>_normal.png, <id>_roughness.png y, si hay,
      <id>_metallic.png) pasa a <id>_diffuse.dds, <id>_normal.dds y <id>_specular.dds del juego.

Solo Pillow, sin numpy. No probado en el juego: los valores del brillo copian los rangos del
tanque original, no una documentación.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps

REPO = Path(__file__).resolve().parents[2]
TEXTURAS = REPO / "assets" / "modelos" / "texturas"

# material -> (rugosidad 0-1, metal 0-1, fuerza del relieve)
PROPIEDADES = {
    "casco": (0.55, 0.0, 1.0),
    "detalle": (0.35, 0.9, 1.6),
    "cromo": (0.12, 1.0, 0.8),
    "laton": (0.35, 1.0, 1.3),
    "biometal": (0.3, 0.7, 1.4),
    "desgaste": (0.85, 0.0, 1.8),
    "circuito": (0.3, 0.0, 1.0),
    "piedra": (0.8, 0.0, 2.2),
    "jade": (0.15, 0.0, 0.6),
    "tejido": (0.6, 0.0, 1.2),
    "marmol": (0.2, 0.0, 0.6),
    "chatarra": (0.6, 0.6, 2.0),
    "parches": (0.6, 0.6, 2.0),
    "pintura": (0.7, 0.0, 1.4),
    "oxido": (0.9, 0.2, 2.0),
    "barro": (0.95, 0.0, 2.2),
}


def propiedades(nombre: str) -> tuple[float, float, float]:
    clave = nombre.rsplit("_", 1)[-1]
    return PROPIEDADES.get(clave, (0.6, 0.0, 1.0))


def _repetida(img: Image.Image) -> Image.Image:
    """La imagen rodeada de sí misma (3x3), para filtrar sin cortes en los bordes."""
    w, h = img.size
    t = Image.new(img.mode, (w * 3, h * 3))
    for i in range(3):
        for j in range(3):
            t.paste(img, (i * w, j * h))
    return t


def altura(color: Image.Image) -> Image.Image:
    """Relieve aproximado: lo claro sube. Se le saca la luz de fondo para quedarse con el detalle."""
    w, h = color.size
    lum = _repetida(ImageOps.grayscale(color.convert("RGB")))
    fondo = lum.filter(ImageFilter.GaussianBlur(max(4, w // 64)))
    detalle = ImageChops.add(ImageChops.subtract(lum, fondo, offset=128), Image.new("L", lum.size, 0))
    detalle = detalle.filter(ImageFilter.GaussianBlur(1))
    return detalle.crop((w, h, 2 * w, 2 * h))


def _derivadas(alt: Image.Image, fuerza: float) -> tuple[Image.Image, Image.Image]:
    """(dx, dy) centradas en 128, con +y hacia abajo."""
    w, h = alt.size
    rep = _repetida(alt)
    esc = 1.6 / fuerza   # calibrado: el relieve queda en el rango del tanque del juego
    kx = ImageFilter.Kernel((3, 3), (-1, 0, 1, -2, 0, 2, -1, 0, 1), scale=esc, offset=128)
    ky = ImageFilter.Kernel((3, 3), (-1, -2, -1, 0, 0, 0, 1, 2, 1), scale=esc, offset=128)
    return (rep.filter(kx).crop((w, h, 2 * w, 2 * h)), rep.filter(ky).crop((w, h, 2 * w, 2 * h)))


def normales(color: Image.Image, fuerza: float) -> tuple[Image.Image, Image.Image]:
    """(normal estilo OpenGL en RGB para Blender, X para el juego, Y hacia abajo para el juego).

    Normal = (-dh/dx, -dh/dy, 1) normalizada. Con +y abajo: OpenGL (y arriba) usa +dh/dy."""
    dx, dy = _derivadas(altura(color), fuerza)
    gx = list(dx.tobytes())
    gy = list(dy.tobytes())
    r, g, b, ydn = bytearray(len(gx)), bytearray(len(gx)), bytearray(len(gx)), bytearray(len(gx))
    for i, (a, c) in enumerate(zip(gx, gy)):
        nx = -(a - 128) / 128.0
        ny_abajo = (c - 128) / 128.0      # el Kernel de Pillow da -dh/dy en vertical
        inv = 1.0 / (1.0 + nx * nx + ny_abajo * ny_abajo) ** 0.5
        nx, ny_abajo, nz = nx * inv, ny_abajo * inv, inv
        r[i] = int(127.5 + nx * 127)
        g[i] = int(127.5 - ny_abajo * 127)      # OpenGL: +Y arriba
        b[i] = int(127.5 + nz * 127)
        ydn[i] = int(127.5 + ny_abajo * 127)    # juego: +Y abajo
    size = color.size
    rgb = Image.merge("RGB", [Image.frombytes("L", size, bytes(x)) for x in (r, g, b)])
    return rgb, Image.frombytes("L", size, bytes(r)), Image.frombytes("L", size, bytes(ydn))


def rugosidad(color: Image.Image, base: float) -> Image.Image:
    """La rugosidad del material, con algo de variación: lo oscuro (suciedad, huecos) más mate."""
    lum = ImageOps.grayscale(color.convert("RGB"))
    b = int(base * 255)
    return lum.point(lambda v: max(0, min(255, b + int((128 - v) * 0.25))))


def para_blender(salida: Path) -> list[str]:
    salida.mkdir(parents=True, exist_ok=True)
    hechos = []
    for f in sorted(TEXTURAS.glob("textura_*")):
        nombre = f.stem.replace("textura_", "")
        img = Image.open(f)
        img.load()
        if nombre.endswith("_calcos"):   # calcos: solo color con transparencia
            img.convert("RGBA").save(salida / f"{nombre}_color.png")
            hechos.append(nombre)
            continue
        rug, metal, fuerza = propiedades(nombre)
        img = img.convert("RGB")
        img.save(salida / f"{nombre}_color.jpg", quality=93, subsampling=0)   # liviano; Blender lo lee igual
        normales(img, fuerza)[0].save(salida / f"{nombre}_normal.png")
        rugosidad(img, rug).save(salida / f"{nombre}_roughness.jpg", quality=92)
        Image.new("L", img.size, int(metal * 255)).save(salida / f"{nombre}_metallic.png")
        hechos.append(nombre)
    return hechos


def _dds(img: Image.Image, dest: Path) -> None:
    from tools.gen import art
    img = img.convert("RGBA")
    raw = img.tobytes()
    art.write_dds(dest, img.width, img.height, [tuple(raw[k:k + 4]) for k in range(0, len(raw), 4)])


def a_paradox(color: Image.Image, normal_gl: Image.Image | None, rug: Image.Image | None,
              metal: Image.Image | None, salida: Path, nombre: str) -> list[Path]:
    """Los tres .dds del juego a partir de lo horneado en Blender."""
    w, h = color.size
    color = color.convert("RGB")
    dif = color.copy()
    dif.putalpha(255)
    if normal_gl is None:
        _, nx, ny = normales(color, 1.0)
    else:
        n = normal_gl.convert("RGB").resize((w, h))
        nx = n.getchannel("R")
        ny = ImageOps.invert(n.getchannel("G"))     # OpenGL (+Y arriba) -> juego (+Y abajo)
    nor = Image.merge("RGBA", (nx, nx, Image.new("L", (w, h), 0), ny))
    rug = (rug.convert("L").resize((w, h)) if rug is not None else Image.new("L", (w, h), 150))
    metal = (metal.convert("L").resize((w, h)) if metal is not None else Image.new("L", (w, h), 0))
    liso = ImageOps.invert(rug)
    # rangos del tanque del juego: brillo ~40-170, metal un poco por debajo, lisura ~10-130
    brillo = ImageChops.add(liso.point(lambda v: 30 + v * 70 // 255), metal.point(lambda v: v * 75 // 255))
    azul = brillo.point(lambda v: v * 82 // 100)
    lisura = liso.point(lambda v: 10 + v * 120 // 255)
    spec = Image.merge("RGBA", (Image.new("L", (w, h), 0), brillo, azul, lisura))
    salida.mkdir(parents=True, exist_ok=True)
    hechos = []
    for suf, img in (("diffuse", dif), ("normal", nor), ("specular", spec)):
        dest = salida / f"{nombre}_{suf}.dds"
        _dds(img, dest)
        hechos.append(dest)
    return hechos


def desde_blender(carpeta: Path, salida: Path) -> list[str]:
    hechos = []
    for c in sorted(carpeta.rglob("*_color.png")):
        nombre = c.name[: -len("_color.png")]
        def abrir(suf):
            p = c.with_name(f"{nombre}_{suf}.png")
            return Image.open(p) if p.exists() else None
        a_paradox(Image.open(c), abrir("normal"), abrir("roughness"), abrir("metallic"), salida, nombre)
        hechos.append(nombre)
    return hechos


if __name__ == "__main__":
    if sys.argv[1] == "blender":
        r = para_blender(Path(sys.argv[2]))
    else:
        r = desde_blender(Path(sys.argv[2]), Path(sys.argv[3]))
    print(f"{len(r)} materiales")
