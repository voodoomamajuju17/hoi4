"""La Biblioteca de 2100: la enciclopedia del mod, generada desde el spec (2026-11-07).

Pedido: "el readme y los documentos en general están recontra desactualizados.
Enciclopedias peladas, tutoriales no existentes, y es todo poco y feo. Quiero lore,
quiero leer, quiero merch, quiero buena literatura e información abundante."

Lo que se escribe a mano (la historia del mundo, las crónicas de cada nación, la guía,
los cuentos, el catálogo) vive en docs/ y no se toca acá. Este programa escribe solo
docs/enciclopedia/ y docs/img/: una página por nación con todo lo que el spec sabe de
ella (gobierno, líderes y su historia, gabinete y mandos, espíritus, el árbol de focos,
unidades únicas, aventuras, eventos, frases) y láminas con sus dibujos de verdad
(bandera, retratos, pines de foco y azulejos de espíritus). Como sale del spec, no se
desactualiza: se vuelve a correr con

    python -m tools.docs.biblioteca
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs"
ENC = DOCS / "enciclopedia"
IMG = DOCS / "img"

ORDEN = ["EFE", "ASC", "FCU", "HSN", "NAS", "SHD", "APF", "NRE", "ZJP", "ZAL",
         "ZWE", "ZWI", "ZWM", "ZWB", "ZAN", "JUNTA"]
GRANDES = ORDEN[:8]

ROL = {"country_leader": "Jefe de Estado", "field_marshal": "Mariscal de campo",
       "corps_commander": "General", "navy_leader": "Almirante", "advisor": "Asesor"}
SLOT = {"political_advisor": "Ministro", "high_command": "Alto mando", "theorist": "Teórico",
        "army_chief": "Jefe del Ejército", "navy_chief": "Jefe de la Armada", "air_chief": "Jefe de la Fuerza Aérea",
        "intelligence_minister": "Inteligencia", "head_of_government": "Jefe de Gobierno",
        "foreign_minister": "Canciller", "economy_minister": "Economía", "security_minister": "Seguridad"}


def _es(x, campo: str = "spanish") -> str:
    if isinstance(x, dict):
        return str(x.get(campo) or x.get("english") or "")
    return str(x or "")


def _capital(c: dict | None) -> str:
    v = _es((c or {}).get("capital"))
    return "" if v.strip().lower() in ("", "unknown", "none") else v


def _uno(t: str) -> str:
    t = str(t or "").replace("\\n", "\n")
    return " ".join(t.split())


def _parrafos(t: str) -> str:
    t = str(t or "").replace("\\n", "\n")
    return "\n\n".join(" ".join(p.split()) for p in t.split("\n\n") if p.strip())


def _nombre_personaje(c: dict) -> str:
    n = c.get("name") or {}
    if isinstance(n, dict):
        reg = n.get("regnal")
        if isinstance(reg, dict):
            return _es(reg)
        if reg:
            return str(reg)
        if n.get("spanish") or n.get("english"):
            return _es(n)
        return str(n.get("civil") or c["id"])
    return str(n or c["id"])


# ---------------------------------------------------------------- imágenes

def _abrir(path: Path):
    from PIL import Image
    try:
        im = Image.open(path)
        im.load()
        return im.convert("RGBA")
    except Exception:   # noqa: BLE001 (un dibujo roto no frena la biblioteca)
        return None


def _hoja(paths: list[Path], dest: Path, celda: tuple[int, int], cols: int, fondo=(24, 26, 30),
          agrandar: bool = False) -> bool:
    """Una lámina con varios dibujos en grilla; True si escribió algo."""
    from PIL import Image
    ims = [im for im in (_abrir(p) for p in paths) if im is not None]
    if not ims:
        return False
    w, h = celda
    pad = 6
    filas = (len(ims) + cols - 1) // cols
    cols = min(cols, len(ims))
    hoja = Image.new("RGBA", (cols * (w + pad) + pad, filas * (h + pad) + pad), fondo + (255,))
    for i, im in enumerate(ims):
        if agrandar and (im.width < w and im.height < h):
            f = min(w / im.width, h / im.height)
            im = im.resize((int(im.width * f), int(im.height * f)), Image.LANCZOS)
        im.thumbnail((w, h), Image.LANCZOS)
        x = pad + (i % cols) * (w + pad) + (w - im.width) // 2
        y = pad + (i // cols) * (h + pad) + (h - im.height) // 2
        hoja.alpha_composite(im, (x, y))
    dest.parent.mkdir(parents=True, exist_ok=True)
    hoja.convert("RGB").save(dest, quality=86, optimize=True, progressive=True)
    return True


def _bandera(tag: str) -> str | None:
    src = REPO / "assets" / tag / "flags" / f"{tag}.tga"
    if not src.exists():
        return None
    from PIL import Image
    im = _abrir(src)
    if im is None:
        return None
    im = im.resize((246, 156), Image.NEAREST)
    dest = IMG / "banderas" / f"{tag}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(dest, optimize=True)
    return f"../img/banderas/{tag}.png"


# ---------------------------------------------------------------- datos

def _cargar():
    sys.path.insert(0, str(REPO))
    from tools.gen import specload
    return specload.load(REPO / "spec").raw


def _paises(raw) -> dict[str, dict]:
    out = {c["tag"]: c for c in raw["countries"].get("major_powers") or []}
    for grupo in ("independents", "subjects", "minor", "others", "anarchies"):
        for c in raw["countries"].get(grupo) or []:
            out.setdefault(c["tag"], c)
    for c in raw.get("free_countries", {}).get("countries", []) if isinstance(raw.get("free_countries"), dict) else []:
        if isinstance(c, dict) and c.get("tag"):
            out.setdefault(c["tag"], c)
    return out


def _ideologia(raw, sub: str) -> tuple[str, str, str]:
    """(gobierno, sub-ideología, lore del grupo)"""
    for g in raw["ideologies"]["groups"]:
        for t in g.get("types") or g.get("sub_ideologies") or []:
            if isinstance(t, dict) and t.get("key") == sub:
                return _es(g.get("government")), _es(t.get("name") or t.get("loc")), _es(g.get("lore"))
    return "", sub.replace("_", " "), ""


def _espiritus(raw, tag: str) -> list[tuple[str, str, str]]:
    """(id, nombre, descripción) de cada espíritu de la nación."""
    out = []
    entry = (raw["ideas"].get("countries") or {}).get(tag) or {}
    if isinstance(entry, dict):
        for grupo in ("starting_ideas", "focus_ideas"):
            for i in entry.get(grupo) or []:
                if isinstance(i, dict):
                    out.append((i["id"], _es(i.get("name")), _uno(_es(i.get("desc")))))
    for dm in (raw.get("decisions") or {}).get("dynamic_modifiers") or []:
        if dm.get("country") == tag:
            out.append((dm["id"], _es(dm.get("name")), _uno(_es(dm.get("desc")))))
    return out


def _citas(raw, personas: dict[str, str]) -> dict[str, list[tuple[str, str]]]:
    out: dict[str, list[tuple[str, str]]] = {}
    for q in (raw["scenario"].get("loading_quotes") or {}).get("quotes") or []:
        autor = q.get("author", "")
        tag = personas.get(autor)
        if tag is None:
            for nombre, t in personas.items():
                if nombre and (nombre in autor or autor in nombre):
                    tag = t
                    break
        out.setdefault(tag or "MUNDO", []).append((autor, q.get("es", "")))
    return out


# ---------------------------------------------------------------- páginas

RASGOS: dict[str, str] = {}
VANILLA = {"logistics_wizard": "mago de la logística", "offensive_doctrine": "doctrina ofensiva",
           "defensive_doctrine": "doctrina defensiva", "organizer": "organizador", "trickster": "embaucador",
           "brilliant_strategist": "estratega brillante", "inflexible_strategist": "estratega inflexible",
           "politically_connected": "con contactos políticos", "skilled_staffer": "buen oficial de estado mayor",
           "old_guard": "vieja guardia", "panzer_leader": "líder de blindados", "infantry_leader": "líder de infantería",
           "commando": "comando", "cavalry_officer": "oficial de caballería", "naval_invader": "experto en desembarcos",
           "engineer_officer": "oficial de ingenieros", "career_officer": "oficial de carrera",
           "aggressive_assaulter": "asaltante agresivo", "media_personality": "figura mediática",
           "harsh_leader": "líder duro", "war_hero": "héroe de guerra", "infantry_officer": "oficial de infantería",
           "armor_officer": "oficial de blindados", "spotter": "observador", "air_controller": "control aéreo",
           "blockade_runner": "rompebloqueos", "superior_tactician": "táctico superior", "ironside": "acorazado",
           "seawolf": "lobo de mar", "air_controller": "control aéreo", "fly_swatter": "cazamoscas",
           "gentlemanly": "caballeroso", "bold": "audaz", "cautious": "cauteloso", "spotter": "observador"}


def pagina(raw, tag: str, pais: dict | None, personas: dict, citas: dict) -> str:
    L = []
    nombre = _es(pais.get("name")) if pais else {"JUNTA": "La Junta del Sol Negro"}.get(tag, tag)
    adj = _es(pais.get("adjective")) if pais else ""
    L.append(f"# {nombre}")
    L.append("")
    bandera = _bandera(tag)
    cron = DOCS / "cronicas" / (f"{tag}.md" if tag not in ("ZWE", "ZWI", "ZWM", "ZWB", "ZAN", "JUNTA")
                                else "TIERRAS_SIN_LEY.md")
    if bandera:
        L.append(f"![Bandera]({bandera})")
        L.append("")
    datos = []
    if pais:
        if _capital(pais):
            datos.append(f"**Capital:** {_capital(pais)}")
        if pais.get("ideology"):
            gob, sub, lore = _ideologia(raw, pais["ideology"])
            datos.append(f"**Gobierno:** {gob} ({sub})" if gob else f"**Ideología:** {sub}")
        if adj:
            datos.append(f"**Gentilicio:** {adj}")
    datos.append(f"**Código:** `{tag}`")
    L.append(" · ".join(datos))
    L.append("")
    if cron.exists():
        L.append(f"> 📜 Antes de los datos, la historia: **[leé la crónica](../cronicas/{cron.name})**.")
        L.append("")
    if pais and pais.get("ideology"):
        gob, sub, lore = _ideologia(raw, pais["ideology"])
        if lore:
            L += ["## De dónde sale su poder", "", f"*{lore}*", ""]

    # líderes
    gente = [c for c in raw["leaders"]["characters"] if c.get("country") == tag]
    jefes = [c for c in gente if (c.get("roles") or {}).get("country_leader")]
    if jefes:
        L += ["## Quién manda", ""]
        retratos = [REPO / c["portrait"]["asset"] for c in jefes
                    if isinstance(c.get("portrait"), dict) and c["portrait"].get("asset")
                    and (REPO / c["portrait"]["asset"]).exists()]
        if _hoja(retratos, IMG / "lideres" / f"{tag}.jpg", (156, 210), 6):
            L += [f"![Jefes de Estado](../img/lideres/{tag}.jpg)", ""]
        for c in jefes:
            n = _nombre_personaje(c)
            civil = (c.get("name") or {}).get("civil") if isinstance(c.get("name"), dict) else None
            nac = c.get("born")
            linea = f"### {n}"
            L.append(linea)
            extra = []
            if civil and civil != n:
                extra.append(f"nacido/a {civil}")
            if nac:
                extra.append(f"año {nac}")
            if extra:
                L.append(f"*{', '.join(extra)}*")
            if c.get("lore"):
                L += ["", _parrafos(c["lore"])]
            bio = [b for b in c.get("biography") or [] if isinstance(b, dict) and b.get("event")]
            if bio:
                L += ["", "Hitos: " + " → ".join(
                    f"{b['event']}" + (f" ({b['date']})" if b.get('date') not in (None, 'unknown') else "") for b in bio)]
            L.append("")

    # gabinete y mandos
    otros = [c for c in gente if c not in jefes]
    if otros:
        L += ["## Gabinete, generales y almirantes", "",
              "| Nombre | Cargo | Quién es |", "|---|---|---|"]
        for c in otros:
            roles = c.get("roles") or {}
            cargo = []
            for r, v in roles.items():
                if not v:
                    continue
                if r == "advisor" and isinstance(v, dict):
                    cargo.append(SLOT.get(v.get("slot"), "Asesor"))
                else:
                    cargo.append(ROL.get(r, r))
            lore = _uno(c.get("lore") or "").replace("|", "/")
            if not lore:
                rasgos = [RASGOS.get(t) for v in roles.values() if isinstance(v, dict) for t in v.get("traits") or []]
                rasgos = [r for r in rasgos if r]
                lore = ("Rasgo: " + ", ".join(rasgos)) if rasgos else ""
            L.append(f"| {_nombre_personaje(c)} | {', '.join(dict.fromkeys(cargo))} | {lore} |")
        L.append("")

    # espíritus
    esp = _espiritus(raw, tag)
    if esp:
        L += ["## Espíritus nacionales", "",
              "Lo que define a la nación en cada momento: ventajas, cargas y estados de ánimo.", ""]
        dibujos = [REPO / "assets" / tag / "ideas" / f"{i}.dds" for i, _n, _d in esp]
        dibujos = [p for p in dibujos if p.exists()]
        if _hoja(dibujos[:60], IMG / "espiritus" / f"{tag}.jpg", (72, 72), 12):
            L += [f"![Espíritus](../img/espiritus/{tag}.jpg)", ""]
        for _i, n, d in esp:
            L.append(f"- **{n}.** {d}" if d else f"- **{n}.**")
        L.append("")

    # focos
    arbol = (raw["focus_trees"]["trees"] or {}).get(tag)
    if isinstance(arbol, dict) and arbol.get("branches"):
        L += ["## El árbol de focos nacionales", ""]
        pines = [REPO / "assets" / tag / "goals" / f"{f['id']}.dds" for r in arbol["branches"] for f in r["focuses"]]
        pines = [p for p in pines if p.exists()]
        if _hoja(pines[:96], IMG / "focos" / f"{tag}.jpg", (95, 85), 12):
            L += [f"![Focos](../img/focos/{tag}.jpg)", ""]
        for r in arbol["branches"]:
            rn = _es(r.get("name")) or r.get("id", "").replace("_", " ").capitalize()
            L += [f"### {rn}", ""]
            for f in r["focuses"]:
                d = _uno(_es(f.get("desc")))
                L.append(f"- **{_es(f.get('name'))}** — {d}" if d else f"- **{_es(f.get('name'))}**")
            L.append("")

    # unidades únicas
    uu = [u for u in raw["unique_units"]["units"] if u.get("country") == tag]
    if uu:
        L += ["## Unidades únicas", ""]
        for u in uu:
            L += [f"### {_es(u.get('name'))}", "", _parrafos(_es(u.get("lore"))), ""]

    # aventuras
    sagas = [(k, s) for k, s in (raw.get("adventures") or {}).get("sagas", {}).items()
             if (s.get("country") or k) == tag or tag in (s.get("countries") or [])]
    if sagas:
        L += ["## Aventuras", "", "Historias de \"elegí tu propia aventura\": ver la [guía de aventuras](../guia/aventuras.md).", ""]
        for k, s in sagas:
            L += [f"### {_es(s.get('name'))}", "", f"*{_uno(_es(s['intro'].get('desc')))}*", ""]
            for ch in s.get("characters") or []:
                L.append(f"- {_uno(_es(ch.get('pick')))}")
            L += ["", f"{len(s.get('nodes') or [])} capítulos y {len(s.get('endings') or [])} finales.", ""]

    # eventos
    evs = []
    for ns, v in (raw["events"].get("namespaces") or {}).items():
        if v.get("country") == tag or ns.endswith("_" + tag.lower()):
            evs += [e for e in v.get("events") or [] if not e.get("hidden") and e.get("title")]
    if evs:
        L += ["## Lo que puede pasar: eventos", "",
              f"{len(evs)} eventos propios. Algunos títulos:", ""]
        vistos = []
        for e in evs:
            t = _uno(_es(e.get("title")))
            if t and t not in vistos and len(t) < 90:
                vistos.append(t)
        L.append(" · ".join(f"*{t}*" for t in vistos[:60]))
        L.append("")

    # frases
    if citas.get(tag):
        L += ["## Frases", ""]
        for autor, txt in citas[tag]:
            L += [f"> {txt}", f"> — *{autor}*", ""]

    L += ["---", "", "*Página generada desde el spec del mod por `tools/docs/biblioteca.py`. "
          "[Volver a la Biblioteca](../README.md).*", ""]
    return "\n".join(L)


def indice(raw, paises, hechas: list[str]) -> str:
    L = ["# Enciclopedia", "",
         "Una página por nación, con todo lo que el mod sabe de ella: quién manda, quién la acompaña, "
         "qué la define, qué puede llegar a ser y qué le puede pasar. Se genera desde el spec, así que "
         "siempre está al día.", "",
         "| | Nación | Qué es |", "|---|---|---|"]
    for tag in hechas:
        p = paises.get(tag) or {}
        b = f"![](../img/banderas/{tag}.png)" if (IMG / "banderas" / f"{tag}.png").exists() else ""
        tipo = ("Meganación" if tag in GRANDES else "Potencia que se levanta" if tag in ("ZJP", "ZAL")
                else "Régimen de guerra civil" if tag == "JUNTA" else "Tierra sin ley")
        nombre = _es(p.get("name")) or {"JUNTA": "La Junta del Sol Negro"}.get(tag, tag)
        L.append(f"| {b} | [{nombre}]({tag}.md) | {tipo} |")
    L += ["", "Además: [Satélites y países menores](SATELITES.md).", "", "[Volver a la Biblioteca](../README.md)", ""]
    return "\n".join(L).replace("![](", '<img width="48" src="').replace(".png) |", '.png"> |')


def satelites(raw, paises) -> str:
    """Los países satélite y libres que no tienen página propia."""
    L = ["# Satélites y países menores", "",
         "Los países que viven a la sombra de una meganación (o que todavía no eligieron cuál). "
         "Algunos se pueden jugar; casi todos se pueden liberar, anexar o perder.", "",
         "| | País | Capital | Bajo el ala de |", "|---|---|---|---|"]
    for c in raw["countries"].get("subjects") or []:
        tag = c["tag"]
        b = _bandera(tag)
        img = f'<img width="40" src="{b}">' if b else ""
        amo = c.get("overlord") or c.get("subject_of") or ""
        amo_n = _es((paises.get(amo) or {}).get("name")) if amo else ""
        L.append(f"| {img} | **{_es(c.get('name'))}** | {_capital(c) or '—'} | {amo_n} |")
    L += ["", "[Volver a la Enciclopedia](README.md)", ""]
    return "\n".join(L)


QUIEN = {"MN2110": "Las ocho meganaciones (y Japón y Albión si los juega una persona)",
         "ZAL_CORONA": "Albión, si elige Hacia el Pasado", "ZAL_SINCRONIA": "Albión, si elige Hacia el Futuro",
         "ZJP_ZAI_1": "Japón, si gobiernan los Zaibatsu", "ZJP_ZAI_2": "Japón, después de La Junta de Accionistas",
         "ZJP_YAK_1": "Japón, si gobierna la Yakuza", "ZJP_YAK_2": "Japón, después de La Fiesta del Puerto",
         "ZJP_SRS_1": "Japón, si gobierna SRS", "ZJP_SRS_2": "Japón, después de El Lote 2101"}


def aventuras(raw, paises) -> str:
    """La guía de aventuras: premisa, quiénes las juegan y cuántos finales (sin spoilers)."""
    L = ["# Guía de aventuras", "",
         "Las aventuras son historias de \"elegí tu propia aventura\" que corren en paralelo a la partida. "
         "Arrancan con una situación y dos o tres personajes; elegís en qué zapatos meterte, y cada "
         "algunos meses llega un capítulo nuevo con una decisión. Según lo que elijas, el héroe triunfa, "
         "fracasa, cambia el país o muere, y la nación se lleva premios, castigos o, a veces, una guerra.", "",
         "**Cómo se ven.** Los momentos grandes no son un evento más: se abre **la Lámina**, una ventana "
         "propia con una pintura de gran formato, el título, el nombre de la saga y un relato largo, con "
         "el marco de tu nación. Al tocar *Continuar* llega el evento con las opciones.", "",
         "**Lo que conviene saber:**", "",
         "- Si dejás de cumplir el requisito de un capítulo (perdés la región donde transcurre, tu capital, "
         "o pasás a ser satélite), la historia se corta.",
         "- En las de las anarquías, las opciones sangrientas suman **calaveras** a la cuenta del héroe.",
         "- En las de Albión y en las largas de Japón, la última decisión depende de algo que elegiste "
         "antes. El relato te lo recuerda; prestale atención.",
         "- La IA también juega sus aventuras, eligiendo al azar.", ""]
    for k, s in (raw.get("adventures") or {}).get("sagas", {}).items():
        tag = s.get("country") or (None if s.get("countries") else k)
        quien = QUIEN.get(k) or _es((paises.get(tag) or {}).get("name")) or k
        tipos = {}
        for e in s.get("endings") or []:
            tipos[e["kind"]] = tipos.get(e["kind"], 0) + 1
        nombres = {"objetivo": "de gloria", "positivo": "buenos", "neutral": "neutros",
                   "negativo": "malos", "muerte": "de muerte"}
        mezcla = ", ".join(f"{n} {nombres.get(t, t)}" for t, n in tipos.items() if n)
        L += [f"## {_es(s.get('name'))}", "", f"**Quién la juega:** {quien}.  ",
              f"**Personajes:** " + "; ".join(_es(c.get("name")) for c in s.get("characters") or []) + ".  ",
              f"**Tamaño:** {len(s.get('nodes') or [])} capítulos, {len(s.get('endings') or [])} finales ({mezcla}).", "",
              f"> *{_uno(_es(s['intro'].get('desc')))}*", ""]
    L += ["[Volver a la Biblioteca](../README.md)", ""]
    return "\n".join(L)


def frases(citas, paises=None) -> str:
    L = ["# Frases de 2100", "",
         "Las frases que aparecen en las pantallas de carga, ordenadas por quién las dijo.", ""]
    for tag in [t for t in ORDEN if t in citas] + [t for t in citas if t not in ORDEN]:
        titulo = "Del mundo" if tag == "MUNDO" else (_es(((paises or {}).get(tag) or {}).get("name")) or tag)
        L += [f"## {titulo}", ""]
        for autor, txt in citas[tag]:
            L += [f"> {txt}", f"> — *{autor}*", ""]
    L += ["[Volver a la Biblioteca](../README.md)", ""]
    return "\n".join(L)


def vitrinas() -> None:
    """Muestras para el catálogo de merch: pines y azulejos de todas las naciones."""
    import random
    rnd = random.Random(2100)
    pines, azulejos = [], []
    llegados = REPO / "arte" / "espiritus_azulejo_llegados.txt"
    hechos = {l.strip() for l in llegados.read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.startswith("#")} if llegados.exists() else set()
    for tag in ORDEN[:10]:
        ps = sorted((REPO / "assets" / tag / "goals").glob(f"{tag}_*.dds"))
        pines += rnd.sample(ps, min(3, len(ps)))
        az = [p for p in sorted((REPO / "assets" / tag / "ideas").glob("*.dds")) if p.stem in hechos]
        azulejos += rnd.sample(az, min(3, len(az)))
    _hoja(pines, IMG / "merch" / "pines.jpg", (140, 125), 10, fondo=(236, 232, 224))
    _hoja(azulejos, IMG / "merch" / "azulejos.jpg", (112, 112), 8, fondo=(236, 232, 224), agrandar=True)


def portada() -> None:
    """La franja de banderas de la portada (README)."""
    paths = [REPO / "assets" / t / "flags" / f"{t}.tga" for t in ORDEN[:10]]
    from PIL import Image
    ims = [im for im in (_abrir(p) for p in paths if p.exists()) if im is not None]
    if not ims:
        return
    w, h, pad = 164, 104, 10
    hoja = Image.new("RGB", (len(ims) * (w + pad) + pad, h + 2 * pad), (20, 22, 26))
    for i, im in enumerate(ims):
        hoja.paste(im.convert("RGB").resize((w, h), Image.NEAREST), (pad + i * (w + pad), pad))
    hoja.save(IMG / "portada_banderas.png", optimize=True)


def main() -> None:
    raw = _cargar()
    paises = _paises(raw)
    personas = {}
    for c in raw["leaders"]["characters"]:
        personas[_nombre_personaje(c)] = c.get("country")
        if isinstance(c.get("name"), dict) and c["name"].get("civil"):
            personas[c["name"]["civil"]] = c.get("country")
    citas = _citas(raw, personas)
    RASGOS.update(VANILLA)
    for key in ("leader_traits", "unit_leader_traits"):
        for t in raw["leaders"].get(key) or []:
            if isinstance(t, dict) and t.get("name"):
                RASGOS[t["id"]] = _es(t["name"])
    import yaml
    for f in sorted((REPO / "spec").glob("*.yaml")):
        d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for bloque in (d.get("advisor_traits"), (d.get("leaders") or {}).get("advisor_traits") if isinstance(d.get("leaders"), dict) else None,
                       (d.get("ideas") or {}).get("advisor_traits") if isinstance(d.get("ideas"), dict) else None):
            for t in bloque or []:
                if isinstance(t, dict) and t.get("id") and t.get("name"):
                    RASGOS[t["id"]] = _es(t["name"])
    ENC.mkdir(parents=True, exist_ok=True)
    hechas = []
    for tag in ORDEN:
        if tag not in paises and tag not in (raw["focus_trees"]["trees"] or {}):
            continue
        texto = pagina(raw, tag, paises.get(tag), personas, citas)
        (ENC / f"{tag}.md").write_text(texto, encoding="utf-8")
        hechas.append(tag)
    (ENC / "README.md").write_text(indice(raw, paises, hechas), encoding="utf-8")
    (ENC / "SATELITES.md").write_text(satelites(raw, paises), encoding="utf-8")
    (DOCS / "guia").mkdir(parents=True, exist_ok=True)
    (DOCS / "guia" / "aventuras.md").write_text(aventuras(raw, paises), encoding="utf-8")
    (DOCS / "literatura").mkdir(parents=True, exist_ok=True)
    (DOCS / "literatura" / "frases.md").write_text(frases(citas, paises), encoding="utf-8")
    vitrinas()
    portada()
    # frases del mundo (las que no son de una nación)
    mundo = citas.get("MUNDO", [])
    print(f"biblioteca: {len(hechas)} páginas de nación; {sum(len(v) for v in citas.values())} frases "
          f"({len(mundo)} sin nación)")


if __name__ == "__main__":
    main()
