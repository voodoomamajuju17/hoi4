"""Ventanas de eventos sin el «informe con el clip» (2026-11-15, opción 2 elegida por Maxi).

  - Eventos propios (EventWindow y EventWindow_leader): el Receptor. Marco de cobre, vidrio
    ahumado, la imagen en una pantalla con bisel, el título en una placa de latón y las opciones
    como teclas de canal con su piloto.
  - Noticias del mundo (EventWindow_News): el «cable de Ginebra». Papel térmico de teletipo con
    agujeros de arrastre, la franja del sello de Ginebra y el borde cortado; la letra de máquina
    (negra) del juego se lee bien sobre el papel.
  - La Lámina (tools/gen/emitters/laminas.py) sigue para los momentos grandes.

Medidas y posiciones: interface/eventwindow.gui del juego (ver tools/gen/emitters/eventos_gui.py,
que pone la letra clara sobre el vidrio). Se dibuja al doble y se achica. Salida: DDS en
assets/ui/eventos_piel/<ruta del juego>, que ui_skin aplica encima de la piel y de los materiales.

Uso:  python3 -m tools.arte.eventos [vista_previa.png]
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from .selector import (BRONCE, COBRE_LUZ, GRAFITO, TURQUESA, _bisel, _dds, _material, _mascara_redonda,
                       _pegar, _sombra_interior, _tono, _tornillo)
from . import selector as _sel

REPO = Path(__file__).resolve().parents[2]
SALIDA = REPO / "assets" / "ui" / "eventos_piel" / "gfx" / "interface"
K = 2
MARCO = 14          # ancho del marco de cobre a cada lado
LETRA_CABLE = "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf"
PAPEL = (226, 228, 218)
TINTA = (40, 44, 52)
SELLO = (150, 36, 32)

PIEZAS = {
    "event_report_top_win": (581, 121),
    "event_report_tileable_midsection": (580, 66),
    "event_report_bottom_win": (581, 206),
    "event_report_bottom_win_2": (581, 59),
    "event_option_entry": (352, 48),
    "event_pic_clip": (55, 30),
    "event_leader_frame": (172, 232),
    "event_news_bg": (528, 595),
    "event_news_pic_overlay": (399, 155),
}


def _lienzo(w, h):
    from PIL import Image
    return Image.new("RGBA", (w * K, h * K), (0, 0, 0, 0))


def _final(img, w, h):
    from PIL import Image
    return img.resize((w, h), Image.LANCZOS)


def _vidrio(w, h):
    """Vidrio ahumado parejo de arriba abajo (la pieza del medio se estira en alto)."""
    from PIL import Image
    src = _sel._fuente("selector_vidrio")
    if src is not None:
        franja = src.crop((src.width // 4, src.height // 2, src.width * 3 // 4, src.height // 2 + 4))
        g = franja.resize((w, 1), Image.LANCZOS).resize((w, h), Image.NEAREST)
    else:
        g = _material("mat_vidrio_ahumado", w, h, 0.5)
    g = _tono(g, 0.55, (12, 22, 26), 0.45)
    return g


def _cobre(w, h, factor=1.0):
    return _tono(_material("mat_cobre_patina", w, h, 0.35), factor, (120, 70, 40), 0.35)


def _marco_lateral(img, y0, y1, ancho):
    """Los dos costados de cobre entre y0 e y1 (en píxeles al doble)."""
    w = img.width
    m = MARCO * K
    for x0 in (0, w - m):
        tira = _cobre(m, y1 - y0, 0.95)
        img.alpha_composite(tira, (x0, y0))
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    # filo de luz por dentro y sombra por fuera
    d.line((m - K, y0, m - K, y1), fill=(20, 12, 8, 220), width=K)
    d.line((w - m, y0, w - m, y1), fill=(20, 12, 8, 220), width=K)
    d.line((K, y0, K, y1), fill=COBRE_LUZ + (150,), width=K)
    d.line((w - 2 * K, y0, w - 2 * K, y1), fill=(40, 24, 14, 220), width=K)


def _placa_laton(w, h):
    img = _lienzo(w, h)
    cuerpo = _tono(_material("mat_laton_pulido", w * K, h * K, 0.4), 0.62, (60, 40, 20), 0.25)
    _pegar(img, cuerpo, 0, 0, 6 * K)
    _bisel(img, (0, 0, w * K - 1, h * K - 1), 6 * K, 3 * K, hundido=False)
    _sombra_interior(img, (5 * K, 5 * K, w * K - 5 * K, h * K - 5 * K), 4 * K, 2 * K)
    for cx in (12 * K, w * K - 12 * K):
        _tornillo(img, cx, h * K // 2, 4 * K)
    return img


def tope():
    """581 x 121: canto superior, rejilla con pilotos y la placa de latón del título (y 70-102)."""
    from PIL import ImageDraw
    w, h = PIEZAS["event_report_top_win"]
    img = _lienzo(w, h)
    W, H = w * K, h * K
    _pegar(img, _vidrio(W, H), 0, 8 * K, 0)
    _marco_lateral(img, 8 * K, H, MARCO)
    # canto de arriba, redondeado
    canto = _cobre(W, 46 * K, 1.05)
    from PIL import Image
    m = Image.new("L", (W, 46 * K), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, W - 1, 46 * K + 30 * K), 12 * K, fill=255)
    img.paste(canto, (0, 0), m)
    _bisel(img, (0, 0, W - 1, 46 * K), 12 * K, 3 * K, hundido=False)
    # la rejilla del parlante, a la derecha del botón de minimizar (10,45 de 32x33)
    rej = _sel._rejilla_dibujada(int(30 * K))
    for x in range(60 * K, W - 120 * K, rej.width):
        tira = rej.crop((0, 0, min(rej.width, W - 120 * K - x), 18 * K))
        img.alpha_composite(tira, (x, 14 * K))
    _sombra_interior(img, (60 * K, 14 * K, W - 120 * K, 32 * K), 2 * K, 2 * K)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((60 * K - K, 14 * K - K, W - 120 * K + K, 32 * K + K), 2 * K, outline=BRONCE + (230,), width=K)
    # pilotos: uno turquesa encendido (transmisión entrante) y dos apagados
    for k, encendido in enumerate((True, False, False)):
        cx, cy, r = W - 100 * K + k * 20 * K, 23 * K, 4 * K
        if encendido:
            from PIL import ImageFilter
            br = _lienzo(w, h)
            ImageDraw.Draw(br).ellipse((cx - 3 * r, cy - 3 * r, cx + 3 * r, cy + 3 * r), fill=TURQUESA + (120,))
            img.alpha_composite(br.filter(ImageFilter.GaussianBlur(3 * K)))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(TURQUESA if encendido else (30, 52, 50)) + (255,),
                  outline=(20, 16, 12, 255), width=K)
    for cx in (22 * K, W - 22 * K):
        _tornillo(img, cx, 30 * K, 4 * K)
    # el hueco del botón minimizar: un nicho hundido
    _sombra_interior(img, (8 * K, 43 * K, 44 * K, 80 * K), 4 * K, 2 * K)
    # placa de latón del título (el texto va en x 14-565, y 70-102)
    placa = _placa_laton(w - 2 * MARCO - 8, 38)
    img.alpha_composite(placa, ((MARCO + 4) * K, 67 * K))
    d.line(((MARCO + 6) * K, H - K, W - (MARCO + 6) * K, H - K), fill=(0, 0, 0, 90), width=K)
    return _final(img, w, h)


def medio():
    """580 x 66, se estira en alto (borde 290 x 16): costados de cobre y vidrio."""
    w, h = PIEZAS["event_report_tileable_midsection"]
    img = _lienzo(w, h)
    img.alpha_composite(_vidrio(w * K, h * K))
    _marco_lateral(img, 0, h * K, MARCO)
    return _final(img, w, h)


def _pantalla(img, x, y, w, h):
    """El bisel de la pantalla donde cae la imagen del evento (x, y, w, h al tamaño final)."""
    from PIL import ImageDraw
    caja = ((x - 6) * K, (y - 6) * K, (x + w + 6) * K, (y + h + 6) * K)
    aro = _tono(_material("mat_bronce_cepillado", caja[2] - caja[0], caja[3] - caja[1], 0.4), 0.8)
    _pegar(img, aro, caja[0], caja[1], 8 * K)
    _bisel(img, caja, 8 * K, 3 * K, hundido=False)
    ImageDraw.Draw(img).rectangle((x * K, y * K, (x + w) * K, (y + h) * K), fill=(6, 10, 12, 255))
    for cx, cy in ((caja[0] + 5 * K, caja[1] + 5 * K), (caja[2] - 5 * K, caja[1] + 5 * K),
                   (caja[0] + 5 * K, caja[3] - 5 * K), (caja[2] - 5 * K, caja[3] - 5 * K)):
        _tornillo(img, cx, cy, 2 * K)


def fondo_abajo():
    """581 x 206: la pantalla de la imagen (20,12; 210x176 a 0.9) y el lugar de las teclas, con el canto de abajo."""
    from PIL import ImageDraw
    w, h = PIEZAS["event_report_bottom_win"]
    img = _lienzo(w, h)
    W, H = w * K, h * K
    img.alpha_composite(_vidrio(W, H - 14 * K))
    _marco_lateral(img, 0, H - 14 * K, MARCO)
    _pantalla(img, 20, 12, 189, 158)   # la imagen va a 0.9 (eventos_gui)
    _canto_abajo(img, H - 16 * K)
    return _final(img, w, h)


def _canto_abajo(img, y):
    from PIL import Image, ImageDraw
    W = img.width
    alto = img.height - y
    canto = _cobre(W, alto, 1.0)
    m = Image.new("L", (W, alto), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, -30 * K, W - 1, alto - 1), 10 * K, fill=255)
    img.paste(canto, (0, y), m)
    _bisel(img, (0, y - 10 * K, W - 1, img.height - 1), 10 * K, 3 * K, hundido=False)
    ImageDraw.Draw(img).line((MARCO * K, y, W - MARCO * K, y), fill=(18, 10, 6, 230), width=K)
    for cx in (22 * K, W - 22 * K):
        _tornillo(img, cx, y + alto // 2, 3 * K)


def fondo_fin():
    """581 x 59: el cierre de abajo (ventanas con líder y opciones en mosaico)."""
    w, h = PIEZAS["event_report_bottom_win_2"]
    img = _lienzo(w, h)
    img.alpha_composite(_vidrio(w * K, h * K))
    _marco_lateral(img, 0, h * K, MARCO)
    _canto_abajo(img, h * K - 20 * K)
    return _final(img, w, h)


def tecla_opcion():
    """352 x 48: tecla de canal con su piloto (el texto va centrado, hoi_20bs claro)."""
    from PIL import ImageDraw
    w, h = PIEZAS["event_option_entry"]
    img = _lienzo(w, h)
    W, H = w * K, h * K
    cuerpo = _tono(_material("mat_acero_ennegrecido", W - 4 * K, H - 6 * K, 0.4), 1.1)
    _pegar(img, cuerpo, 2 * K, 3 * K, 7 * K)
    _bisel(img, (2 * K, 3 * K, W - 3 * K, H - 4 * K), 7 * K, 3 * K, hundido=False)
    placa = _tono(_material("mat_fieltro_grafito", W - 70 * K, H - 18 * K, 0.35), 0.7)
    _pegar(img, placa, 34 * K, 9 * K, 4 * K)
    _sombra_interior(img, (34 * K, 9 * K, W - 36 * K, H - 9 * K), 4 * K, 2 * K)
    d = ImageDraw.Draw(img)
    cx, cy, r = 18 * K, H // 2, 4 * K
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(150, 112, 50, 255), outline=(20, 16, 12, 255), width=K)
    d.ellipse((cx - r // 2, cy - r // 2 - K, cx, cy - K), fill=(255, 226, 160, 200))
    d.rounded_rectangle((3 * K, 4 * K, W - 4 * K, H - 5 * K), 7 * K, outline=BRONCE + (255,), width=2 * K)
    return _final(img, w, h)


def clip_vacio():
    """55 x 30: sin clip."""
    w, h = PIEZAS["event_pic_clip"]
    from PIL import Image
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def marco_lider():
    """172 x 232: aro de bronce con el hueco del retrato (retrato en 8,9 dentro del marco)."""
    from PIL import Image, ImageChops, ImageDraw
    w, h = PIEZAS["event_leader_frame"]
    img = _lienzo(w, h)
    W, H = w * K, h * K
    aro = _tono(_material("mat_bronce_cepillado", W, H, 0.4), 0.8)
    _pegar(img, aro, 0, 0, 10 * K)
    _bisel(img, (0, 0, W - 1, H - 1), 10 * K, 3 * K, hundido=False)
    hx0, hy0, hx1, hy1 = 9 * K, 10 * K, W - 9 * K, H - 12 * K
    hueco = Image.new("L", (W, H), 255)
    ImageDraw.Draw(hueco).rounded_rectangle((hx0, hy0, hx1, hy1), 4 * K, fill=0)
    img.putalpha(ImageChops.multiply(img.getchannel("A"), hueco))
    _sombra_interior(img, (hx0, hy0, hx1, hy1), 4 * K, 3 * K)
    for cx, cy in ((5 * K, 5 * K), (W - 5 * K, 5 * K), (5 * K, H - 5 * K), (W - 5 * K, H - 5 * K)):
        _tornillo(img, cx, cy, 2 * K)
    return _final(img, w, h)


# -- el cable de Ginebra ---------------------------------------------------------------------

def _letra(tam):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(LETRA_CABLE, tam)
    except OSError:
        return ImageFont.load_default()


def _papel(w, h, semilla=7):
    """Papel térmico: grano fino y alguna raya tenue del cabezal (todo opaco)."""
    from PIL import Image, ImageDraw, ImageFilter
    rnd = random.Random(semilla)
    img = Image.new("RGBA", (w, h), PAPEL + (255,))
    ruido = Image.effect_noise((w, h), 40).convert("L").filter(ImageFilter.GaussianBlur(0.7))
    gris = Image.new("RGBA", (w, h), (196, 198, 186, 255))
    img = Image.composite(gris, img, ruido.point(lambda v: min(255, max(0, v - 110))))
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for _ in range(h // 40):
        y = rnd.randrange(h)
        d.line((0, y, w, y), fill=(150, 152, 140, 26), width=1)
    img.alpha_composite(capa)
    return img


def fondo_cable():
    """528 x 595: tira de papel térmico con margen de arrastre, franja del sello y borde cortado.

    Imagen en 59,91 (397x153); título en y 260 (alto 32); texto en 39,291 (460 x 230);
    las opciones abajo."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    w, h = PIEZAS["event_news_bg"]
    W, H = w * K, h * K
    img = _lienzo(w, h)
    x0, x1 = 14 * K, W - 14 * K
    papel = _papel(x1 - x0, H, 11)
    # borde cortado abajo (dientes) y arriba levemente ondulado
    m = Image.new("L", papel.size, 255)
    d = ImageDraw.Draw(m)
    paso = 9 * K
    pts = [(0, papel.height - 8 * K)]
    for i, x in enumerate(range(0, papel.width + paso, paso)):
        pts.append((x, papel.height - (2 * K if i % 2 else 9 * K)))
    pts += [(papel.width, papel.height), (0, papel.height)]
    d.polygon(pts, fill=0)
    papel.putalpha(ImageChops.multiply(papel.getchannel("A"), m))
    # sombra del papel
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sm = Image.new("L", papel.size, 0)
    sm.paste(papel.getchannel("A"))
    sombra.paste((0, 0, 0, 140), (x0 + 3 * K, 4 * K), sm)
    img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(5 * K)))
    img.alpha_composite(papel, (x0, 0))
    d = ImageDraw.Draw(img)
    # agujeros de arrastre a los costados
    for y in range(14 * K, H - 20 * K, 18 * K):
        for cx in (x0 + 11 * K, x1 - 11 * K):
            d.ellipse((cx - 4 * K, y - 4 * K, cx + 4 * K, y + 4 * K), fill=(0, 0, 0, 0))
            d.ellipse((cx - 4 * K, y - 4 * K, cx + 4 * K, y + 4 * K), outline=(150, 150, 140, 255), width=K)
    for cx in (x0 + 22 * K, x1 - 22 * K):
        for y in range(0, H - 14 * K, 6 * K):
            d.line((cx, y, cx, y + 3 * K), fill=(150, 152, 142, 200), width=K)
    # la franja del sello de Ginebra (arriba): cabecera del cable
    f1, f2 = _letra(13 * K), _letra(10 * K)
    d.rectangle((x0 + 30 * K, 14 * K, x1 - 30 * K, 15 * K), fill=TINTA + (200,))
    d.text((x0 + 34 * K, 20 * K), "CABLE  ·  AGENCIA DE GINEBRA  ·  SERVICIO MUNDIAL", font=f1, fill=TINTA + (240,))
    d.text((x0 + 34 * K, 40 * K), "PRIORIDAD: URGENTE   VÍA: SATÉLITE LEMAN-3   COPIA: CANCILLERÍAS",
           font=f2, fill=TINTA + (200,))
    d.rectangle((x0 + 30 * K, 58 * K, x1 - 30 * K, 59 * K), fill=TINTA + (200,))
    d.line((x0 + 30 * K, 62 * K, x1 - 30 * K, 62 * K), fill=TINTA + (120,), width=K)
    # el sello: círculo rojo con la cruz de Ginebra y las llaves, un poco girado
    sello = _lienzo(70, 70)
    ds = ImageDraw.Draw(sello)
    c, r = 35 * K, 31 * K
    ds.ellipse((c - r, c - r, c + r, c + r), outline=SELLO + (210,), width=3 * K)
    ds.ellipse((c - r + 6 * K, c - r + 6 * K, c + r - 6 * K, c + r - 6 * K), outline=SELLO + (180,), width=K)
    ds.rectangle((c - 3 * K, c - 12 * K, c + 3 * K, c + 12 * K), fill=SELLO + (200,))
    ds.rectangle((c - 12 * K, c - 3 * K, c + 12 * K, c + 3 * K), fill=SELLO + (200,))
    sello = sello.rotate(-14, resample=Image.BICUBIC)
    ruido = Image.effect_noise(sello.size, 60).convert("L").point(lambda v: 255 if v > 90 else 120)
    sello.putalpha(ImageChops.multiply(sello.getchannel("A"), ruido))
    img.alpha_composite(sello, (x1 - 96 * K, 6 * K))
    # renglón del despacho bajo la imagen y antes del título
    d.text((x0 + 45 * K, 247 * K), "DESPACHO Nº ____   HORA ZULÚ ____   CONTROL ____", font=f2, fill=TINTA + (150,))
    d.line((x0 + 30 * K, 292 * K, x1 - 30 * K, 292 * K), fill=TINTA + (90,), width=K)
    # pie: fin de transmisión, sobre las opciones
    d.text((x0 + 34 * K, H - 32 * K), "— FIN DE TRANSMISIÓN —   GVA/MN/2100", font=f2, fill=TINTA + (170,))
    return _final(img, w, h)


def marco_foto_cable():
    """399 x 155: la foto como telefoto pegada: borde fino, cinta en las puntas, centro transparente."""
    from PIL import Image, ImageDraw
    w, h = PIEZAS["event_news_pic_overlay"]
    img = _lienzo(w, h)
    W, H = w * K, h * K
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W - 1, H - 1), outline=(250, 250, 244, 255), width=3 * K)
    d.rectangle((3 * K, 3 * K, W - 3 * K, H - 3 * K), outline=(60, 60, 60, 160), width=K)
    # tramado de telefoto: líneas horizontales muy suaves
    for y in range(4 * K, H - 4 * K, 3 * K):
        d.line((4 * K, y, W - 4 * K, y), fill=(220, 230, 225, 22), width=K)
    cinta = Image.new("RGBA", (40 * K, 12 * K), (214, 206, 170, 170))
    for (x, y, a) in ((-8 * K, 4 * K, 35), (W - 32 * K, 4 * K, -35)):
        c = cinta.rotate(a, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(c, (max(0, x), y))
    return _final(img, w, h)


DIBUJOS = {
    "event_report_top_win": tope,
    "event_report_tileable_midsection": medio,
    "event_report_bottom_win": fondo_abajo,
    "event_report_bottom_win_2": fondo_fin,
    "event_option_entry": tecla_opcion,
    "event_pic_clip": clip_vacio,
    "event_leader_frame": marco_lider,
    "event_news_bg": fondo_cable,
    "event_news_pic_overlay": marco_foto_cable,
}


def dibujar() -> list[str]:
    hechas = []
    for nombre, fn in DIBUJOS.items():
        img = fn()
        assert img.size == PIEZAS[nombre], (nombre, img.size)
        _dds(img, SALIDA / f"{nombre}.dds")
        hechas.append(nombre)
    return [f"eventos: {len(hechas)} piezas (Receptor y cable de Ginebra) en {SALIDA.relative_to(REPO)}"]


def vista_previa(dest: Path) -> None:
    """Las dos ventanas armadas como en el juego, con texto de prueba."""
    from PIL import Image, ImageDraw, ImageFont
    piezas = {n: fn() for n, fn in DIBUJOS.items()}
    lienzo = Image.new("RGBA", (581 + 40 + 528, 640), (60, 70, 60, 255))
    # informe: tope + medio estirado a 100 + abajo
    medio_img = piezas["event_report_tileable_midsection"]
    m = Image.new("RGBA", (580, 100))
    m.alpha_composite(medio_img.crop((0, 0, 580, 16)), (0, 0))
    m.alpha_composite(medio_img.crop((0, 16, 580, 50)).resize((580, 68)), (0, 16))
    m.alpha_composite(medio_img.crop((0, 50, 580, 66)), (0, 84))
    lienzo.alpha_composite(piezas["event_report_top_win"], (0, 0))
    lienzo.alpha_composite(m, (0, 121))
    lienzo.alpha_composite(piezas["event_report_bottom_win"], (0, 221))
    foto = Image.new("RGBA", (210, 176), (90, 110, 120, 255))
    lienzo.alpha_composite(foto.resize((189, 158)), (20, 233))
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        g = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    except OSError:
        f = g = ImageFont.load_default()
    d = ImageDraw.Draw(lienzo)
    d.text((290, 86), "La Tierra Firma", font=f, fill=(201, 173, 120), anchor="mm")
    d.text((31, 128), "El Senado de Roma votó el Pacto de las Restauraciones.\nLas delegaciones del Imperio Verde "
                      "aplaudieron de pie.", font=g, fill=(232, 226, 210))
    for k, t in enumerate(("Que se cumpla.", "Pedir garantías.", "Archivarlo.")):
        lienzo.alpha_composite(piezas["event_option_entry"], (217, 225 + k * 47))
        d.text((217 + 176, 225 + k * 47 + 24), t, font=g, fill=(232, 226, 210), anchor="mm")
    x = 621
    lienzo.alpha_composite(piezas["event_news_bg"], (x, 0))
    lienzo.alpha_composite(Image.new("RGBA", (397, 153), (120, 120, 110, 255)), (x + 59, 91))
    lienzo.alpha_composite(piezas["event_news_pic_overlay"], (x + 58, 90))
    d.text((x + 264, 276), "EL MUNDO MIRA A ROMA", font=f, fill=(20, 20, 20), anchor="mm")
    d.text((x + 39, 300), "Ginebra confirma la firma del pacto entre\nRoma y el Imperio Verde.", font=g, fill=(20, 20, 20))
    lienzo.alpha_composite(piezas["event_option_entry"], (x + 80, 520))
    d.text((x + 80 + 176, 544), "Interesante.", font=g, fill=(232, 226, 210), anchor="mm")
    lienzo.convert("RGB").save(dest)


if __name__ == "__main__":
    for linea in dibujar():
        print(linea)
    if len(sys.argv) > 1:
        vista_previa(Path(sys.argv[1]))
