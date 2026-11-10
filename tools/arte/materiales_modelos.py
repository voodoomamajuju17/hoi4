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

  python -m tools.arte.materiales_modelos normalizar <assets/modelos/<pieza>/>
      Un modelo ya horneado con sus .dds (de cualquier orden de canales) pasa al formato del juego.

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
    "andamio": (0.5, 0.8, 1.8),
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
    """DDS sin comprimir (A8R8G8B8) con todas sus versiones achicadas, como las del juego (que trae
    10 niveles): sin ellas el modelo titila de lejos."""
    import struct
    img = img.convert("RGBA")
    niveles = [img]
    while niveles[-1].width > 1 or niveles[-1].height > 1:
        a = niveles[-1]
        niveles.append(a.resize((max(1, a.width // 2), max(1, a.height // 2)), Image.BOX))
    w, h = img.size
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x8 | 0x20000      # caps, alto, ancho, formato, pitch, mipmaps
    cab = b"DDS " + struct.pack("<IIIIIII", 124, flags, h, w, w * 4, 0, len(niveles)) + b"\0" * 44
    cab += struct.pack("<IIIIIIII", 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    cab += struct.pack("<IIIII", 0x1000 | 0x8 | 0x400000, 0, 0, 0, 0)
    cuerpo = bytearray()
    for n in niveles:
        r, g, b, a = n.split()
        cuerpo += Image.merge("RGBA", (b, g, r, a)).tobytes()     # en el archivo va B G R A
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(cab + bytes(cuerpo))


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
        hechos_dds = a_paradox(Image.open(c), abrir("normal"), abrir("roughness"), abrir("metallic"), salida, nombre)
        # 2026-11-10 (NAS): algunas mallas nombran _diff/_spec en vez de _diffuse/_specular; se usan los nombres
        # que pide la malla que está al lado, si hay una
        import re as _re
        malla = next(iter(sorted(salida.glob("*.mesh"))), None)
        if malla is not None:
            pedidos = {n.decode() for n in _re.findall(rb"[A-Za-z0-9_]+\.dds", malla.read_bytes())}
            for f in hechos_dds:
                for alt in (f.name.replace("_diffuse.", "_diff."), f.name.replace("_specular.", "_spec."),
                            f.name.replace("_normal.", "_norm.")):
                    if alt != f.name and alt in pedidos and f.name not in pedidos:
                        f.replace(salida / alt)
        hechos.append(nombre)
    return hechos


def enriquecer_atlas(color: Image.Image, nacion: str, fuerza: float = 0.8) -> Image.Image:
    """Los modelos de ChatGPT vienen pintados con un atlas de bloques de color lisos (con un ruido
    parejo). Les pone el detalle de las muestras de material de la nación (paneles, remaches,
    vetas) y su desgaste, SIN cambiar el color de cada bloque: luz suave con el detalle centrado
    en gris, así cada parte del modelo sigue del color que eligió quien lo hizo (2026-11-09)."""
    w, h = color.size
    rgb = color.convert("RGB")
    def muestra(mat):
        for ext in (".jpg", ".png"):
            f = TEXTURAS / f"textura_{nacion}_{mat}{ext}"
            if f.exists():
                return Image.open(f).convert("RGB")
        return None
    detalle, desgaste = muestra("detalle"), muestra("desgaste")
    if detalle is None:
        return color
    lado = max(64, w // 2)          # la muestra se repite dos veces a lo ancho del atlas
    def mosaico(img):
        t = img.resize((lado, lado), Image.LANCZOS)
        out = Image.new("RGB", (w, h))
        for x in range(0, w, lado):
            for y in range(0, h, lado):
                out.paste(t, (x, y))
        return out
    def relieve(img):
        """Solo el detalle fino (placas, remaches, rayones), con la misma intensidad para todas
        las naciones: sin las franjas grandes de color de la muestra."""
        from PIL import ImageStat
        lum = ImageOps.grayscale(img)
        fondo = lum.filter(ImageFilter.GaussianBlur(3))
        d = ImageChops.subtract(lum, fondo, scale=1, offset=128)
        desv = max(1.0, ImageStat.Stat(d).stddev[0])
        k = 14.0 / desv
        return d.point(lambda v: max(0, min(255, 128 + int((v - 128) * k))))
    det = relieve(mosaico(detalle))
    if desgaste is not None:
        det = Image.blend(det, relieve(mosaico(desgaste)), 0.4)
    luz = ImageChops.soft_light(rgb, Image.merge("RGB", (det, det, det)))
    out = Image.blend(rgb, luz, fuerza)
    if color.mode == "RGBA":
        out.putalpha(color.getchannel("A"))
    return out


def _es_rgb_normal(img: Image.Image) -> bool:
    """Normal común (RGB, azul alto) y no la del juego (azul en 0)."""
    from PIL import ImageStat
    return ImageStat.Stat(img.convert("RGBA").getchannel("B")).mean[0] > 150


def normalizar_modelo(carpeta: Path, nacion: str | None = None, maximo: int = 0) -> list[str]:
    """Las texturas de un modelo entregado (…_diff, …_normal/_norm, …_spec .dds o .png) pasan al
    formato del juego, con los MISMOS nombres de archivo (el .mesh los nombra adentro):
      - normal común (RGB) -> la del juego; si viene plana (horneada sin relieve), el relieve sale
        del color, como en el tanque del juego (que tiene el relieve del color);
      - brillo en otro orden -> el del juego, armado desde el color (rugosidad media de pintura);
      - todas con sus versiones achicadas.
    Así los modelos ya horneados no se rehacen."""
    from PIL import ImageStat
    hechos = []
    for dif in sorted(carpeta.rglob("*_diff*.dds")):
        base = dif.name.split("_diff")[0]
        color = Image.open(dif).convert("RGBA")
        if maximo and color.width > maximo:
            # atlas de colores lisos: a 512 se ve igual y pesa la cuarta parte (como el tanque del juego)
            color = color.resize((maximo, maximo * color.height // color.width), Image.LANCZOS)
            hechos.append(f"{dif.name}: achicada a {maximo}")
        if nacion:
            color = enriquecer_atlas(color, nacion)
            hechos.append(f"{dif.name}: detalle de los materiales de {nacion}")
        nor = next(iter(sorted(dif.parent.glob(base + "_norm*.dds"))), None)
        spec = next(iter(sorted(dif.parent.glob(base + "_spec*.dds"))), None)
        rgb = color.convert("RGB")
        _dds(color, dif)
        if nor is not None:
            n = Image.open(nor).convert("RGBA")
            if n.size != color.size:
                n = n.resize(color.size, Image.LANCZOS)
            if _es_rgb_normal(n):
                plana = max(ImageStat.Stat(n.convert("RGB")).stddev[:2]) < 6
                if plana:
                    _, nx, ny = normales(rgb, 1.0)
                else:
                    nx, ny = n.getchannel("R"), ImageOps.invert(n.getchannel("G"))
                _dds(Image.merge("RGBA", (nx, nx, Image.new("L", n.size, 0), ny)), nor)
                hechos.append(f"{nor.name}: {'relieve sacado del color' if plana else 'canales reordenados'}")
            else:
                _dds(n, nor)
        if spec is not None:
            s = Image.open(spec).convert("RGBA")
            if s.size != color.size:
                s = s.resize(color.size, Image.LANCZOS)
            if s.getchannel("R").getextrema() != (0, 0):      # no es el orden del juego
                tmp = Path(str(spec) + ".tmp")
                a_paradox(rgb, None, rugosidad(rgb, 0.55), None, tmp, "x")
                sp = Image.open(tmp / "x_specular.dds").convert("RGBA")
                for f in tmp.iterdir():
                    f.unlink()
                tmp.rmdir()
                _dds(sp, spec)
                hechos.append(f"{spec.name}: brillo al orden del juego")
            else:
                _dds(s, spec)
    return hechos


if __name__ == "__main__":
    if sys.argv[1] == "blender":
        r = para_blender(Path(sys.argv[2]))
    elif sys.argv[1] == "normalizar":
        r = normalizar_modelo(Path(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None,
                              int(sys.argv[4]) if len(sys.argv) > 4 else 0)
        print("\n".join(r))
    else:
        r = desde_blender(Path(sys.argv[2]), Path(sys.argv[3]))
    print(f"{len(r)} materiales")
