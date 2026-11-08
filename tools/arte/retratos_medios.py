"""Retratos en medios reales: cada nación con su formato (2026-11-08).

Pedido: "Odio las imágenes esas realistas. Cada uno en un medio distinto, materiales reales,
más artístico, más cool... siempre en estilo foto de este objeto". Después de la prueba (un
líder por nación, arte/pedidos_fijos/25_retratos_prueba.txt): "el TCG del HSN debería ser de
verdad un TCG; cada personaje de esa nación va a tener ese formato. La del FCU no me gusta,
preferiría una tarjeta de presentación televisiva, casi WWE. Hacé el pedido para todos los
retratos, con excepción de los agentes de inteligencia". Y de los murales de la APF: "alguna
persona parada adelante o caminando, algo que indique que es una pared en una calle".

Cada personaje usa el medio de su nación (MEDIOS); la persona sale de la descripción del
catálogo (quién es, cara, ropa, detalles) sin las instrucciones de cámara y luz de la foto de
estudio. Escribe arte/pedidos/0_RETRATOS_MEDIOS.txt; los que ya llegaron en el formato nuevo se
anotan en arte/retratos_medios_llegados.txt (`python -m tools.arte.arte retratos <carpeta>`).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LLEGADOS = REPO / "arte" / "retratos_medios_llegados.txt"

ESTILO = (
    "photorealistic PHOTOGRAPH OF A REAL PHYSICAL OBJECT that is itself a portrait of one person: the object "
    "(described in MEDIUM) is shot straight-on and fills almost the whole frame, portrait orientation 3:4, so it "
    "works as a character portrait in a strategy game. The person's head and shoulders are big in the middle of "
    "the object and the face must stay readable when the image is shrunk to 156x210 pixels: clear features, "
    "strong expression, lots of personality. Bold, saturated, deliberate colour (never grey or washed out). "
    "True materials with honest texture and wear, real light on the object. Year 2100, but the medium is real "
    "and hand-made or printed. Unless MEDIUM says otherwise: no readable text, no letters, no numbers, no logos, "
    "no watermark (any writing on the object is blurred or illegible)")

# tag -> (medio, cómo varía entre los personajes de la nación)
MEDIOS: dict[str, tuple[str, str]] = {
    "EFE": ("RELIGIOUS IMAGE: a hand-painted wooden retablo / holy icon from a jungle chapel: gold leaf halo and "
            "background, slightly cracked egg-tempera paint, a carved wooden frame with vines and small wooden "
            "orchids; a few real dried flowers or a burnt-down candle at the bottom edge. The person painted like a "
            "saint of the Green Mandate. Palette: emerald, gold leaf, deep jungle green, a touch of blood red.",
            "each character a different saint: their own gesture, attribute and halo shape that fits their role"),
    "ASC": ("PROPAGANDA POSTER: a big screen-printed constructivist poster pasted on a factory brick wall, partly "
            "torn and re-pasted, glue wrinkles, rain streaks, a corner flapping. Printed in three inks (signal red, "
            "black, cream) with halftone and misregistered edges; bold flat shapes, heroic low angle, radiating "
            "lines, gears or the red machine eye of the Plan in the background.",
            "each poster a different composition (diagonal, close-up, with a crowd, with machines) that fits the role"),
    "FCU": ("TELEVISION ENTRANCE CARD: a photograph of a big glossy TV screen (or an arena jumbotron) showing a "
            "pro-wrestling style broadcast entrance title card of this person: dramatic power pose, pyrotechnics, "
            "smoke and spotlights, chrome-and-gold 3D lettering with the person's NAME (spelled exactly as given in "
            "WHO, the only text allowed), a corporate emblem glowing behind them, neon navy and silver graphics, "
            "lens flares, a slight screen glare and visible pixels. Loud, glamorous, corporate showbiz.",
            "each card with its own pose, signature move vibe and corporate colour accent (navy, silver, "
            "turquoise, obsidian black, gold) matching their company or role"),
    "HSN": ("TRADING CARD GAME CARD: a REAL, complete collectible card from a trading card game, photographed flat "
            "on a ship's chart table, slightly worn edges: a full card layout like a real TCG - a title bar at the "
            "top with the person's NAME (spelled exactly as given in WHO), a round cost gem in the top corner, a big "
            "art window with the portrait, a type line under it, a rules box with two short abilities in small "
            "print and a flavour line in italics (the small print may be illegible), a set symbol and a rarity "
            "mark, a collector number, and two stat boxes in the bottom corners (attack and defence numbers). "
            "Ornate brass-and-rope border with anchors, holographic rainbow foil on the art window. Palette: deep "
            "sea teal, brass gold, ocean blue, holographic rainbow.",
            "frame colour by role: leaders gold, admirals deep blue, generals rust red, ministers sea green; the "
            "rarity higher for the most important characters"),
    "NAS": ("TAROT CARD: one large hand-painted tarot card with gilded edges, lying on a woven Andean aguayo cloth "
            "of red, pink and orange stripes. Gouache and gold paint with real gloss and slight relief: the sun, "
            "mountain peaks, stepped terraces, condors or pumas around the person. No title, no numeral.",
            "each character a different major arcana reinvented for the Celestial Kingdom (the Emperor, the "
            "Chariot, Justice, the Star, the Hermit, Strength...) chosen to fit their role"),
    "SHD": ("SPY PHOTO: a clandestine long-lens surveillance photograph, grainy and slightly blurred, printed on "
            "glossy photo paper and paper-clipped to a beige intelligence dossier folder; a red grease-pencil "
            "circle around the face, a strip of black redaction tape, a coffee ring or a fingerprint on the folder. "
            "The person caught in their world (a dam, a control room, a corridor of servers, a rainy street) and "
            "looking straight into the camera. Palette: jade green, steel grey, sodium-lamp orange, pencil red.",
            "each photo a different place and moment (getting out of a car, at a window, at a parade, in a canteen)"),
    "APF": ("GRAFFITI MURAL: a huge spray-paint and brush mural of this person on a sun-baked plastered wall on a "
            "real street of an African city: bold outlines, drips, layered stencils, wild geometric patterns behind. "
            "At the bottom of the photo the STREET is clearly visible: a stretch of pavement, and one or two real "
            "people walking past or standing in front of the wall (small, at the bottom edge, never covering the "
            "painted face), plus a detail of the street (a bicycle, a market umbrella, a motorbike, a plastic chair, "
            "a shop sign). Real cracks in the plaster, an older faded tag under the paint. Palette: ochre, cobalt, "
            "orange, leaf green, white highlights.",
            "each mural on a different street and wall, with different passers-by and patterns"),
    "NRE": ("CAMEO: a large carved cameo brooch, the figure carved in milky white stone over a deep imperial "
            "purple layer, set in an ornate gold frame with a laurel border and small garnets, lying on red velvet. "
            "Strong raised relief, real stone translucency and polish, tiny tool marks; the portrait carved three-"
            "quarter to the front, not a flat profile, so the face reads.",
            "the stone and frame vary with the role: sardonyx for the Imperator's circle, shell or agate for the "
            "others, bronze or silver frames for generals and admirals"),
    "ZJP": ("WOODBLOCK PRINT: a ukiyo-e style woodblock print on soft washi paper, pinned flat, with visible wood "
            "grain in the flat colour areas, slight misregistration, embossed details and hand-pressed mica "
            "sparkles; a dramatic kabuki-actor pose, waves, cranes of the dry docks, submarines or neon Osaka "
            "streets behind. A blank red seal stamp with no characters. Palette: Prussian blue, crimson, black, "
            "cream paper.",
            "each print a different kabuki pose and background that fits the character's house and role"),
    "ZAL": ("NEWSPAPER CLIPPING: a photo cut out of a yellowed newspaper with scissors, ragged edges, pinned with a "
            "brass tack to a cork board, coarse halftone dots, ink bleed, a fold line; the columns of text around "
            "it blurred and illegible; hand-tinted later with watercolour (brick red, tweed brown, a brass gleam). "
            "The photo shows the person in a real moment of the revolution or the court (a rally, a factory, a "
            "palace step, a broken server room).",
            "each clipping from a different moment and with a different crop"),
    # países menores: un medio propio cada uno
    "PTA": ("POSTAGE STAMP: a large commemorative postage stamp with perforated edges, engraved and printed in "
            "white, ice blue, slate and imperial green, stuck on an old envelope with a round postmark and a "
            "glacier vignette around the portrait.", "each stamp a different frame and value-less design"),
    "YYG": ("TIN EX-VOTO: a small votive painting on a sheet of tin, painted by hand in oil like a folk retablo: red "
            "earth, forest green, river blue, a touch of gold, a dented edge and nail holes in the corners.",
            "each ex-voto a different little miracle scene around the person"),
    "ZNG": ("CHIVA BUS ART: a hand-painted portrait on the wooden side panel of a colourful Colombian chiva bus, "
            "bright enamel colours, decorative stripes and flowers, a bit of the bus window and a wheel arch "
            "visible.", "each panel a different colour scheme"),
    "ZLL": ("EMBROIDERY: a portrait embroidered by hand in coloured thread on cloth, stretched on a wooden "
            "embroidery hoop, visible stitches, flowers of the plains around the face.",
            "each embroidery with a different thread palette"),
    "ZNR": ("COMPANY ID BADGE: a laminated mining-corporation employee ID badge on a lanyard, a photo of the person "
            "on it, a hologram strip, a magnetic stripe, scratched plastic, lying on a dusty metal desk.",
            "each badge a different access colour band"),
    "ZSE": ("BUSINESS MAGAZINE COVER: the glossy cover of a business magazine with the person in a confident power "
            "pose, the masthead and cover lines blurred and illegible, lying on a glass desk with a coffee cup.",
            "each cover a different pose and background colour"),
    "ZAF": ("RUM BOTTLE LABEL: a vintage illustrated label on a bottle of Caribbean rum with the person's portrait in "
            "an oval, palm leaves, ships and gold borders, the glass and the amber rum behind the label.",
            "each label a different shape and colour"),
    "ZAS": ("SCRIMSHAW: a portrait engraved in fine black lines on a polished replica of a sperm-whale tooth "
            "(scrimshaw), sailor's style, with ships and waves around it, on a dark wooden shelf.",
            "each piece with a different nautical border"),
    "ZBC": ("LINOCUT PRINT: a bold red-and-black linocut print on rough paper, carved lines and gouge marks, Baltic "
            "waves and cranes of the port around the person, the carved lino block lying beside the print.",
            "each print a different carving style"),
    "ZKR": ("K-POP PHOTOCARD: a glossy collectible photocard in a clear sleeve, the person posed like an idol "
            "with pastel lighting, stickers and a heart doodle on the sleeve, lying on a decorated desk.",
            "each card a different pastel colour and pose"),
    "ZST": ("SILK SCROLL: a hanging scroll painted on silk, the person in the middle of the steppe with horses and "
            "an eagle, brocade mounting, the wooden roller at the bottom.",
            "each scroll a different landscape"),
    "ZET": ("ETHIOPIAN CHURCH PAINTING: the person painted in the bright Ethiopian church style on goatskin "
            "parchment, big almond eyes, red, yellow and green, geometric borders.",
            "each painting a different border and colours"),
    "ZSA": ("GLASS BEADWORK: a portrait made of thousands of small glass beads sewn on cloth in the South African "
            "beadwork tradition, bold geometric bands around it, shining beads.",
            "each beadwork a different geometric pattern"),
    "ZCO": ("BARBERSHOP SIGN: a hand-painted barbershop sign board from a Kinshasa street, glossy enamel paint, "
            "the person with a sharp haircut and a sapeur's elegance, the board a bit sun-faded.",
            "each sign a different colour and frame"),
    "ZAO": ("RECORD SLEEVE: the cover of a vinyl record of a semba band, printed cardboard, worn edges, the person "
            "in the middle in bold graphic colours, the black vinyl peeking out.", "each sleeve a different design"),
    "ZMZ": ("PRINTED CAPULANA CLOTH: a printed African wax cloth (capulana) with the person's portrait repeated in a "
            "big medallion in the middle, bright patterns, fabric folds.", "each cloth a different pattern"),
    "ZMG": ("CARVED WOOD PANEL: a relief portrait carved in a wooden panel in the Zafimaniry style of Madagascar, "
            "geometric carved borders, warm polished wood.", "each panel a different carved border"),
    "ZKE": ("MATATU ART: an airbrushed portrait on the side of a Nairobi matatu minibus, glossy paint, neon "
            "colours, chrome trim, a bit of the window and the wheel.", "each matatu a different colour"),
    "ZHI": ("AZULEJO PANEL: a portrait painted on a wall panel of glazed blue-and-white tiles, the grout lines "
            "visible, a decorative border, in an Iberian courtyard.", "each panel a different border"),
    "ZDA": ("GLASS ICON: a Romanian folk icon painted on the back of glass, bright naive colours, black outlines, a "
            "simple wooden frame.", "each icon a different set of folk motifs"),
    "ZWE": ("MATRYOSHKA: the outer doll of a painted wooden matryoshka set, the person painted on it in lacquer, "
            "fur hat or uniform, gold and red flowers, standing on a wooden table with the smaller dolls beside it.",
            "each doll with a different pattern"),
    "ZWI": ("BOLLYWOOD POSTER: a hand-painted Indian cinema poster pasted on a wall, wild saturated colours, "
            "dramatic close-up of the person with smoke and fire behind, peeling paper; no readable titles.",
            "each poster a different drama"),
    "ZWM": ("KNOTTED CARPET: a portrait woven into a hand-knotted wool carpet, visible knots and fringe, desert "
            "colours (madder red, indigo, saffron), geometric borders.", "each carpet a different border"),
    "ZWB": ("WANTED POSTER: a printed wanted poster nailed to a tree trunk in the jungle, the person's portrait "
            "printed in two colours, paper swollen by humidity, a rusty nail; the text blurred and illegible.",
            "each poster on a different tree"),
    "ZAN": ("MUGSHOT: a police booking photograph with a height chart behind the person, printed on photo paper "
            "and stapled to a file, a thumbprint card beside it.", "each mugshot a different attitude"),
    "ZSG": ("HERBARIUM SHEET: a pressed-plant herbarium sheet where real pressed leaves, petals and moss form the "
            "person's portrait, with a small handwritten label (illegible) and tape strips.",
            "each sheet with different plants"),
    "JUNTA": ("STAINED GLASS: a stained-glass window of a black-sun cult chapel, the person in leaded glass, black, "
              "bone white and eclipse orange, light shining through.", "each window a different pose"),
}


def _llegados() -> set[str]:
    if not LLEGADOS.exists():
        return set()
    return {l.strip() for l in LLEGADOS.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def _uno(texto: str) -> str:
    return " ".join(str(texto or "").split())


def persona(descripcion: str) -> tuple[str, str]:
    """(quién es y cómo es, el lugar) desde la descripción del catálogo, sin la cámara ni la
    luz de la foto de estudio."""
    d = _uno(descripcion)
    lugar = ""
    m = re.search(r"BACKGROUND: (.+?)(?:;|$)", d)
    if m:
        lugar = m.group(1).strip().rstrip(".")
    d = re.split(r" (?:FRAMING|CAMERA|LIGHT|BACKGROUND):", d)[0]
    d = d.replace("Head-and-shoulders portrait, facing the viewer.", "").strip()
    d = re.sub(r"^WHO:\s*", "", d)
    return d, lugar


def items(todos: bool = False) -> list[dict]:
    """Un pedido por retrato (menos los agentes de inteligencia y los que ya llegaron)."""
    from tools.arte import arte
    hechos = set() if todos else _llegados()
    out = []
    for i in arte.catalog():
        if i["type"] != "leader_portrait" or i["id"] in hechos:
            continue
        tag = i["tag"] if i["tag"] in MEDIOS else ("JUNTA" if "junta" in i["id"].lower() else i["tag"])
        if tag not in MEDIOS:
            continue
        out.append({**i, "medio_tag": tag})
    return out


def pedido(i: dict) -> str:
    medio, varia = MEDIOS[i["medio_tag"]]
    quien, lugar = persona(i["description"])
    desc = (f"WHO (keep this person's face, age, ethnicity, hair, clothing and details): {quien} "
            + (f"SETTING to use inside the artwork if it fits the medium: {lugar}. " if lugar else "")
            + f"MEDIUM: {medio} VARIATION: {varia}.")
    return "\n".join(["ASSET_REQUEST", "type: leader_portrait", f"id: {i['id']}", f"filename: {i['id']}.png",
                      "size: 624x840 (proporción 156x210; más grande con la misma proporción está bien)",
                      f"style: {ESTILO}", f"description: {desc}", "transparent_background: false", ""])


def anotar_llegados(carpeta: str) -> list[str]:
    from tools.fabrica import control
    todos = {i["id"] for i in items(todos=True)}
    previos = _llegados()
    buenos = control.mejores_por_nombre(p for p in Path(carpeta).rglob("*.png") if "revisar" not in p.parts)
    nuevos = {s for s in buenos if s in todos} - previos
    cabeza = "# Retratos que ya llegaron en su medio nuevo (tools/arte/retratos_medios.py no los vuelve a pedir)."
    LLEGADOS.write_text(cabeza + "\n" + "\n".join(sorted(previos | nuevos)) + "\n", encoding="utf-8")
    return [f"retratos: {len(nuevos)} nuevos anotados ({len(previos | nuevos)} de {len(todos)})"]


def escribir(salida: Path) -> str:
    lista = items()
    path = salida / "0_RETRATOS_MEDIOS.txt"
    if not lista:
        path.unlink(missing_ok=True)
        return "0_RETRATOS_MEDIOS.txt: 0 (llegaron todos)"
    por_tag: dict[str, int] = {}
    for i in lista:
        por_tag[i["medio_tag"]] = por_tag.get(i["medio_tag"], 0) + 1
    cabeza = [
        f"# {len(lista)} pedidos - TODOS LOS RETRATOS en su medio real, uno por nación (2026-11-08)",
        "# Cada nación tiene su formato; la foto es del OBJETO (retablo, afiche, carta, mural...).",
        "#   EFE retablo con pan de oro | ASC afiche constructivista | FCU presentación de TV estilo lucha libre",
        "#   HSN carta de TCG completa | NAS tarot | SHD foto de espía | APF mural en una calle con gente",
        "#   NRE camafeo | ZJP grabado ukiyo-e | ZAL recorte de diario | los menores, uno propio cada uno",
        "# Sin los agentes de inteligencia (más adelante). La FCU y la HSN son los únicos con texto: el",
        "# NOMBRE del personaje, tal cual está en WHO (revisar que no le cambie letras).",
        "# Por nación: " + ", ".join(f"{t} {n}" for t, n in sorted(por_tag.items())),
        "# Al importar: python -m tools.arte.arte importar <carpeta> y después",
        "#              python -m tools.arte.arte retratos <carpeta> (anota los que llegaron).",
        "",
    ]
    path.write_text("\n".join(cabeza) + "\n".join(pedido(i) for i in lista), encoding="utf-8")
    return f"{path.name}: {len(lista)}"
