"""Muestras de material para la interfaz "de materiales reales" (2026-11-07).

Pedido: "eventualmente vamos a tener que migrar todo el GUI a 'material real vibes'... muestras
de material sin forma: sí, pasame el txt, pero ya con un foco a lo que queremos implementar,
más fácil de imaginar".

Plan acordado: el generador de imágenes hace el MATERIAL (una muestra cuadrada, repetible, sin
forma ni brillo pintado) y el código (como tools/arte/ficha.py) hace la FORMA: marcos, biseles,
remaches, brillos según el tamaño, los estados de cada botón, todo al píxel. Primero un piloto:
la barra superior, la ventana de eventos y la de decisiones. Materiales oscuros para que los
textos del juego (pensados para fondo oscuro) se sigan leyendo sin tocarlos.

Escribe arte/pedidos/0_MATERIALES_GUI.txt. Al volver van a assets/ui/materiales/<id>.png.
"""

from __future__ import annotations

from pathlib import Path

ESTILO = (
    "a SEAMLESS TILEABLE material texture swatch, photographed or scanned straight from above "
    "(orthographic, no perspective), perfectly even flat diffuse lighting: NO highlights, NO "
    "reflections of a light source, NO vignette, NO shadows, so it can be tiled and stretched "
    "without showing where the light was. The material fills the whole square edge to edge: no "
    "object, no border, no frame, no edge of the material visible, no background. Natural, honest "
    "detail at real scale, nothing that repeats visibly. It must tile perfectly in both directions. "
    "No text, no letters, no logos, no stamps, no watermark")

OSCURO = ("Overall DARK in value (mostly between 10% and 30% brightness) so white and gold game "
          "text stays perfectly readable on top of it.")

# (id, material, dónde va en el piloto, si es fondo oscuro para texto)
MUESTRAS = [
    ("mat_acero_ennegrecido",
     "blackened hot-rolled steel plate with a very fine brushed grain running horizontally, faint "
     "blue-black temper colours, tiny honest scratches",
     "the TOP BAR of the game: the long strip across the top of the screen with the country flag, "
     "resources and dates, made of blackened steel", True),
    ("mat_bronce_cepillado",
     "aged warm bronze with a fine horizontal brushed finish and a soft brown patina in places",
     "the trims and rims: thin bands that frame the top bar, window borders and the picture "
     "frame of events; also the base of the buttons", False),
    ("mat_laton_pulido",
     "polished yellow brass, slightly worn, with very subtle micro-scratches, warm and clean",
     "the bright accents: button hover state, the small plates behind numbers and the corner "
     "pieces of frames", False),
    ("mat_cobre_patina",
     "old copper sheet with patches of blue-green verdigris patina and darker oxidised areas",
     "accents that connect with the copper skin we already have: progress bars, small dividers "
     "and the edges of tabs", False),
    ("mat_nogal_oscuro",
     "dark walnut wood with a straight, tight grain, oiled and satin, rich brown, no knots",
     "the FRAME of the EVENT WINDOW: a heavy dark-walnut desk frame around the whole window", True),
    ("mat_cuero_verde",
     "dark bottle-green desk leather (like the inlay of an old ministry desk), fine natural grain, "
     "slightly worn",
     "the inside of the EVENT WINDOW, where the text of the event is read: a green leather desk "
     "blotter", True),
    ("mat_cuero_negro",
     "fine-grained black leather, matte, with a very subtle natural texture",
     "TOOLTIPS and small pop-up panels: a black leather card", True),
    ("mat_cuero_burdeos",
     "oxblood (deep burgundy) leather with a fine pebbled grain, matte",
     "military screens later (army, production): the inner panels; also the alternative for "
     "the decisions window", True),
    ("mat_fieltro_grafito",
     "dense graphite-grey wool felt like a billiard or map table, soft fibres, matte",
     "the inside of the DECISIONS WINDOW: a war-room map table covered in grey felt, where each "
     "decision is laid out", True),
    ("mat_pizarra",
     "dark grey-black natural slate with faint layered texture and very subtle mineral sparkle",
     "the background of LISTS and long panels (decision lists, ledgers, the diplomacy list)", True),
    ("mat_lona_militar",
     "dark olive military canvas, tight woven texture, slightly worn",
     "panels of the army and division screens later, and the back of the tabs", True),
    ("mat_vidrio_ahumado",
     "dark smoked glass seen from above over a black background, very subtle uneven tint and tiny "
     "bubbles, no reflections",
     "the small screens inside panels where numbers live (resource counters, the date in the top "
     "bar), like the glass of an old gauge", True),
]


def pedidos() -> list[str]:
    out = []
    for ident, mat, donde, oscuro in MUESTRAS:
        out.append("\n".join([
            "ASSET_REQUEST",
            "type: material_swatch",
            f"id: {ident}",
            f"filename: {ident}.png",
            "size: 1024x1024 (cuadrada, repetible sin costura)",
            f"style: {ESTILO}",
            f"material: {mat}",
            f"description: WHAT: a material sample for the user interface of a grand strategy game set in "
            f"2100. WHERE IT WILL BE USED (only for context, do NOT draw it): {donde}. Draw ONLY the "
            f"material, flat and endless."
            + (f" {OSCURO}" if oscuro else ""),
            "transparent_background: false",
            "",
        ]))
    return out


def escribir(salida: Path) -> str:
    cuerpo = pedidos()
    cabeza = [
        f"# {len(cuerpo)} pedidos - MUESTRAS DE MATERIAL para la interfaz de materiales reales (2026-11-07)",
        "# PILOTO: la barra superior, la ventana de eventos y la de decisiones.",
        "#   - Barra superior: acero ennegrecido, con bandas de bronce cepillado y números detrás de vidrio ahumado.",
        "#   - Ventana de eventos: marco de nogal oscuro, adentro cuero verde de escritorio de ministerio,",
        "#     la imagen enmarcada en bronce, los botones son placas de bronce (latón al pasar el mouse).",
        "#   - Ventana de decisiones: mesa de mapas con fieltro grafito, listas sobre pizarra.",
        "#   - Tooltips: tarjeta de cuero negro. Cobre con pátina para barras de progreso y separadores.",
        "#   - Para más adelante: cuero burdeos y lona militar (pantallas de ejército y producción).",
        "# Solo el MATERIAL: plano, de arriba, sin brillo ni sombras, repetible sin costura. La forma",
        "# (marcos, biseles, remaches, botones) la armo yo con código, al píxel.",
        "# Si una sale con brillo o se nota dónde se repite, pedile de nuevo con el `style`.",
        "",
    ]
    path = salida / "0_MATERIALES_GUI.txt"
    path.write_text("\n".join(cabeza) + "\n" + "\n".join(cuerpo), encoding="utf-8")
    return f"{path.name}: {len(cuerpo)}"
