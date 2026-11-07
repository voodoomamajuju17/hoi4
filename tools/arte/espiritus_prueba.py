"""Prueba de estilo para los espíritus nacionales (2026-11-07).

Pedido: "Che va a haber que cambiar los espíritus... están como muy chatgpt (obvio), creo
que pueden tener un mejor diseño... sin copiar el estilo de los focos, quisiera algo
análogo" -> propuesta: estampillas de correo; "Dale, hacé un txt con 2 por nación. Pero
agregá también los azulejos de cerámica esmaltada".

Arma arte/pedidos/0_ESPIRITUS_PRUEBA.txt: dos espíritus por nación, cada uno pedido dos
veces (estampilla y azulejo), con la tinta o el esmalte propios de la nación. Los archivos
llevan __estampilla / __azulejo al final: `arte importar` no los conecta todavía (no
coinciden con ningún espíritu); cuando se elija un estilo se arma el pedido de todos.
"""

from __future__ import annotations

ESTAMPILLA = (
    "macro photograph of ONE real postage stamp, photorealistic, as if issued by this nation in the "
    "year 2100: real paper with visible fibres, comb-perforated edges with teeth all around, "
    "intaglio engraved printing with fine line hatching and a slight ink relief, printed in at most "
    "two inks (see INK), a narrow paper margin around a simple printed frame. ONE simple, bold "
    "central image (the subject), engraved like a classic stamp vignette. A faint partial "
    "cancellation postmark may cross one corner (only rings and wavy lines). Shot straight-on, flat, "
    "soft even light, sharp focus. Square stamp filling about 90% of the canvas. Fully transparent "
    "background around the perforations: no album page, no tweezers, no shadow. Absolutely no text, "
    "no letters, no numbers, no denomination, no country name: where a real stamp has text, use "
    "plain ornamental bands. It must read at 64x64 pixels: big shapes and strong contrast")

AZULEJO = (
    "macro photograph of ONE real hand-made glazed ceramic tile, photorealistic: a square tile with "
    "softly rounded edges and corners, glossy vitreous glaze with real reflections, slight pooling "
    "and fine crackle (craquelure), raised cuerda-seca outlines separating flat fields of colour "
    "(see GLAZE), tiny honest kiln imperfections. ONE simple, bold central motif (the subject) inside "
    "a simple border band. Shot straight-on, soft studio light from the top left giving one gentle "
    "highlight on the glaze, sharp focus. The tile fills about 90% of the square canvas. Fully "
    "transparent background around the tile: no wall, no grout, no table, no shadow. No text, no "
    "letters, no numbers. It must read at 64x64 pixels: big flat colour areas and strong contrast")

# nación: (tinta de la estampilla, esmalte del azulejo)
MATERIALES = {
    "EFE": ("imperial green and gold ink, engraved like an old imperial banknote, guilloche border",
            "deep emerald and leaf-green glazes with gold lustre outlines on a cream ground"),
    "ASC": ("black and electric cyan ink on bright white paper, clean technical line engraving",
            "matte graphite and glossy electric-cyan glazes on white, crisp geometric outlines"),
    "FCU": ("navy blue and corporate gold ink on smooth glossy paper, sharp modern engraving",
            "navy blue and white glazes with gold lustre, sleek corporate art-deco lines"),
    "HSN": ("sea teal and brass-yellow ink, nautical engraving with fine wave hatching",
            "Portuguese-style cobalt blue and white glazes with a teal accent, nautical"),
    "NAS": ("sun gold and Andean terracotta red ink, bold Inca-pattern border",
            "sun-yellow, terracotta red and turquoise glazes, Andean step-fret border"),
    "SHD": ("a single dull red ink on cheap grey recycled paper, slightly misaligned print, bureaucratic",
            "flat slate grey and signal red glazes, rigid grid border, austere and industrial"),
    "APF": ("ochre and forest green ink on warm paper, bold woodcut-like engraving, kente-pattern border",
            "ochre, forest green and deep red glazes on cream, bold geometric kente border"),
    "NRE": ("imperial purple and gold ink, classical Roman engraving with laurel border",
            "imperial purple, gold lustre and marble-white glazes, Roman mosaic border"),
    "ZJP": ("two-colour Japanese woodblock print on rice paper: indigo and crimson, visible wood grain",
            "black and crimson glazes with gold lustre outlines, like Japanese cloisonne enamel"),
    "ZAL": ("wine red ink with embossed relief, Victorian 1840s penny-black style engraving",
            "Victorian encaustic tile: oxblood red, cream and navy glazes, ornate border"),
    "ZWE": ("a stamp of a vanished country overprinted by hand with a rough black stencil of the subject, "
            "faded blue original ink, torn perforations",
            "a cracked and chipped old tile repainted by hand in rust red and soot black over a faded blue "
            "pattern, survivor-made"),
}

# dos espíritus por nación: (id, nombre, qué dibujar)
ESPIRITUS = [
    ("EFE_mandato_verde", "The Green Mandate", "a jaguar head in profile crowned with a laurel of leaves"),
    ("EFE_cubas_de_la_pampa", "The Vats of the Pampas",
     "a tall glass vat of glowing living metal with a sprout of steel leaves growing out of it"),
    ("ASC_ejercito_de_maquinas", "The Machine Army", "a four-legged walking combat drone in profile"),
    ("ASC_espiritu_mente_colectiva", "The Collective Mind",
     "a human head in profile made of a network of connected dots"),
    ("FCU_directorio_de_las_cuatro", "The Board of Four",
     "four chairs around a round boardroom table seen from above, a gavel in the middle"),
    ("FCU_canal_abierto", "The Open Canal", "a container ship passing through an open canal lock gate"),
    ("HSN_espiritu_talasocracia", "The Thalassocracy", "a trident rising from a wave in front of a ship's wheel"),
    ("HSN_desembarcos_asegurados", "Underwritten Landings", "a landing craft dropping its ramp onto a beach"),
    ("NAS_espiritu_hijos_del_sol", "Children of the Sun", "a radiant Inca sun face (Inti) with straight rays"),
    ("NAS_condores_del_sol", "The Condors of the Sun", "a condor with spread wings in front of snowy Andean peaks"),
    ("SHD_burocracia_del_caudal", "The Flow Bureaucracy", "a tall stack of official papers with a rubber stamp on top"),
    ("SHD_espiritu_caudal_eterno", "The Eternal Flow", "a great dam with water pouring through its sluice gates"),
    ("APF_espiritu_radios_comunitarias", "Community Radio",
     "an old radio microphone on a carved wooden stool, sound waves around it"),
    ("APF_hijos_de_la_sabana", "Children of the Savanna", "a lone acacia tree under a huge low sun"),
    ("NRE_senado", "The Restored Senate", "a Roman temple front with columns under a laurel wreath"),
    ("NRE_legiones_veteranas", "Veteran Legions", "a Roman legion eagle standard (aquila) with a laurel wreath"),
    ("ZJP_casas_en_paz", "The Three Houses at Peace",
     "three family crests (mon) joined in a circle: a diamond, a coiled dragon and a double helix"),
    ("ZJP_linea_mechas", "The Mecha Line", "a giant samurai-helmeted mecha head inside a shipyard crane frame"),
    ("ZAL_imperio_neovictoriano", "The Neo-Victorian Empire", "a small crown above two crossed brass cogwheels"),
    ("ZAL_implantes", "The Implants", "a human ear with a small glowing port behind it, a circuit line leaving it"),
    ("ZWE_senores_de_la_guerra", "The Eurasian Warlords",
     "a fortified stone village tower with a ragged warlord's banner on top"),
    ("ZWE_caudillo_supremo", "The Supreme Warlord", "a lone horseman with a long banner on a steppe hill"),
]


def pedidos() -> list[str]:
    out = []
    for ident, nombre, que in ESPIRITUS:
        tinta, esmalte = MATERIALES[ident.split("_", 1)[0]]
        for forma, estilo, campo, mat in (("estampilla", ESTAMPILLA, "INK", tinta),
                                          ("azulejo", AZULEJO, "GLAZE", esmalte)):
            out.append("\n".join([
                "ASSET_REQUEST",
                "type: national_spirit_icon",
                f"id: {ident}__{forma}",
                f"filename: {ident}__{forma}.png",
                "size: 1024x1024 (cuadrada; prueba de estilo)",
                f"style: {estilo}",
                f"material: {campo}: {mat}",
                f"description: WHAT: national spirit '{nombre}'. EXACT SUBJECT: {que}. "
                f"Reduce it to ONE simple, bold image.",
                "transparent_background: true",
                "",
            ]))
    return out


def escribir(salida) -> str:
    cuerpo = pedidos()
    cabeza = [
        f"# {len(cuerpo)} pedidos - PRUEBA DE ESTILO de los espíritus nacionales (2026-11-07)",
        f"# {len(ESPIRITUS)} espíritus (2 por nación), cada uno dos veces: como ESTAMPILLA de correo y como",
        "# AZULEJO de cerámica esmaltada, con la tinta o el esmalte de su nación. Elegí el que más te guste",
        "# (o uno por nación) y armo el pedido de todos. Los archivos terminan en __estampilla / __azulejo:",
        "# todavía no reemplazan nada en el juego. Sin imagen de referencia.",
        "",
    ]
    path = salida / "0_ESPIRITUS_PRUEBA.txt"
    path.write_text("\n".join(cabeza) + "\n" + "\n".join(cuerpo), encoding="utf-8")
    return f"{path.name}: {len(cuerpo)}"
