"""Circuito de arte con un generador de imágenes externo (ChatGPT u otro).

  python -m tools.arte.arte pedidos            escribe arte/pedidos/*.txt
  python -m tools.arte.arte importar <carpeta|zip>
                                              convierte y ubica las imágenes
  python -m tools.arte.arte piel [originales]  arma assets/ui/piel/ (tools/arte/piel.py)

El contrato: cada pedido es un bloque ASSET_REQUEST con un `id`. La imagen que
vuelve se llama exactamente `<id>.png` (o .jpg/.webp). El importador sabe por
el id qué es (foco, espíritu, retrato, evento), la lleva al tamaño del juego y
la guarda en assets/ con el nombre que el generador busca solo:

  foco      assets/<TAG>/goals/<id>.dds     95x85, fondo transparente
  espíritu  assets/<TAG>/ideas/<id>.dds     64x64, fondo transparente
  retrato   assets/<TAG>/leaders/<archivo>  156x210
  evento    assets/events/<id>.dds          210x176

Nada se conecta a mano: el próximo build encuentra el archivo y lo usa.
Necesita Pillow (solo quien importa; el instalador del usuario no).
"""

from __future__ import annotations

import re
import sys
import tempfile
import zipfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "spec"
OUT = REPO / "arte" / "pedidos"

KINDS = {
    "national_focus_icon": {"size": (95, 85), "transparent": True, "fit": "contain"},
    "national_spirit_icon": {"size": (64, 64), "transparent": True, "fit": "contain"},
    "leader_portrait": {"size": (156, 210), "transparent": False, "fit": "cover"},
    "event_picture": {"size": (210, 176), "transparent": False, "fit": "cover"},
    # banderas de las identidades nuevas (guerras civiles y formas finales): TGA
    # grande 82x52, mediana 41x26 y chica 10x7 en assets/<TAG>/flags/
    "country_flag": {"size": (82, 52), "transparent": False, "fit": "cover"},
    # íconos de las mejoras de la agencia; el generador los lleva al tamaño del juego
    "agency_upgrade_icon": {"size": (128, 128), "transparent": True, "fit": "contain"},
    # fondos de las pestañas (11_scenario -> tab_backgrounds): el tamaño es el
    # de la textura del juego, que va en cada pedido
    "ui_background": {"size": (192, 192), "transparent": False, "fit": "cover"},
    # fondos de cada rama de investigación (11_scenario -> research_backgrounds):
    # el generador los recorta al tamaño del juego
    # Lo negro se vuelve transparente (ver _fundir): si no, el juego dibuja un
    # rectángulo negro con borde duro sobre el fondo gris de la ventana.
    "research_background": {"size": (1024, 1024), "transparent": True, "fit": "cover"},
    # armas por facción (17_research -> by_faction, 2026-10-03): una imagen por
    # familia y facción, con descripción extensa (arte/armas_descripciones.yaml);
    # el generador la lleva al tamaño de cada ícono de equipo y de tecnología
    "weapon_icon": {"size": (600, 400), "transparent": True, "fit": "contain"},
    # 2026-10-06 ("pasame un txt solo con las unidades únicas; también los aviones
    # por cada facción"): mismo formato, cada uno en su propio archivo
    "unique_icon": {"size": (600, 400), "transparent": True, "fit": "contain"},
    "plane_icon": {"size": (600, 400), "transparent": True, "fit": "contain"},
    # equipo con una sola imagen para todos (17_research -> by_faction.shared)
    "shared_icon": {"size": (600, 400), "transparent": True, "fit": "contain"},
    # tecnologías comunes a todos (arte/tecnologias_descripciones.yaml, 2026-10-10)
    "tech_icon": {"size": (600, 400), "transparent": True, "fit": "contain"},
    # doctrinas (17_research -> doctrines, 2026-10-13): íconos simples como los
    # del juego; el generador los lleva al tamaño del ícono de cada doctrina
    "doctrine_icon": {"size": (256, 256), "transparent": True, "fit": "contain"},
    # leyes del menú del país (05_ideas -> laws, 2026-10-15); el generador las
    # lleva al tamaño del ícono de ley del juego
    "law_icon": {"size": (256, 256), "transparent": True, "fit": "contain"},
    # íconos de la piel de la interfaz (arte/piel_interfaz.yaml, 2026-10-16):
    # se guardan tal cual en assets/ui/piel_iconos/ y tools/arte/piel.py los
    # lleva a cada textura (placa del botón, cuadros, tamaño)
    "ui_icon": {"size": (512, 512), "transparent": True, "fit": "contain"},
    # aventuras de las anarquías (21_aventuras.yaml, 2026-10-16): un txt por
    # anarquía, estilo historieta (Moebius + Kill Six Billion Demons); van a
    # assets/events/<evento>.dds como cualquier imagen de evento
    "adventure_picture": {"size": (210, 176), "transparent": False, "fit": "cover"},
    # pantallas de carga (arte/pantallas_carga_descripciones.yaml, 2026-10-24): la vida
    # diaria de cada potencia y anarquía; 1920x1440 en DXT1, como las que ya hay
    "loading_screen": {"size": (1920, 1440), "transparent": False, "fit": "cover"},
}

# 2026-10-16, pedido del usuario: "el estilo tiene que ser un poco cómic/novela
# gráfica que se inspire en los trabajos de Moebius y Kill Six Billion Demons"
ADVENTURE_STYLE = (
    "graphic novel panel, one single image (not a comic page, no panel borders, no speech balloons), inspired by "
    "Moebius (Jean Giraud): clean ligne-claire ink lines, vast airy landscapes, luminous flat colour with soft "
    "gradients, strange serene skies; and by Kill Six Billion Demons (Tom Parkinson-Morgan): ornate, densely "
    "patterned mythic linework, cosmic grandeur, sacred-grotesque details and dramatic scale; bold readable "
    "silhouettes that still work at 210x176 pixels, a little gore is fine, slightly tongue-in-cheek, "
    "no text, no letters, no numbers unless the description asks for a glowing number shape, no watermark")

COMMON_STYLE = (
    "Hearts of Iron IV style, retrofuturist year 2100, painterly propaganda-poster look, "
    "strong silhouette readable at small size, no text, no letters, no watermark"
)

STYLE = {
    "EFE": "eco-fascist green empire of South America: jungle, living bio-steel, trees and laurels, "
           "green and gold, imperial and organic",
    "FCU": "corporate union of North America: chrome, glass towers, stock tickers, logos and "
           "contracts, navy blue and silver, cold and glossy",
    "ASC": "automated socialist commune of Europe: robots, circuits, data centres, constructivist "
           "red and white, clean geometry",
    "HSN": "high-seas market nation of Asia-Pacific: ships, containers, compasses, straits, "
           "teal and brass, maritime trade",
    "NAS": "neo-Andean sun kingdom: solar temples, Inca stone and gold, condors, mountains, "
           "gold and turquoise",
    "SHD": "sino-harmonious technocratic directorate: rivers, dams, hydraulic diagrams, measured "
           "order, jade green and steel grey",
    "APF": "African peoples' federation: village councils, savanna and rising industry, "
           "kente-like patterns, earth red, yellow and green",
    "NRE": "neo-Roman empire: eagles, legions, marble, laurels, SPQR standards, crimson and gold",
    # anarquías (2026-10-03: armas propias de cada una)
    "ZWE": "Eurasian warlords: looted Soviet-style steel, cossack and steppe motifs, scrap and rust, "
           "grey, olive and faded red",
    "ZWI": "Hindustan warlord realms: monsoon, temples and bazaars, improvised armour with ornate brass, "
           "saffron, crimson and dusty white",
    "ZWM": "desert emirates: dunes, oil wells, falcons and daggers, sand camouflage, ochre, black and gold",
    "ZWB": "Amazon warlords: jungle rivers, illegal gold mines and sawmills, mud and rubber, "
           "dark green, brown and orange",
    "ZAN": "the lawless lands: scavenged junk, welded scrap, raider graffiti without letters, "
           "rust, black and hazard yellow",
    # imágenes que comparten varias potencias (eventos con `art`): sin colores de nadie
    "COMPARTIDOS": "the 2100 world of rival megastates: officers of different armies, maps, borders and "
                   "flags without symbols, neutral grey and ochre palette",
}


SMALL_PORTRAIT = (65, 67)   # el retrato chico (casilla de asesor / alto mando), como un ícono de idea


def small_path(large: Path) -> Path:
    """assets/<TAG>/leaders/x.dds -> assets/<TAG>/leaders/small/x.dds"""
    return large.parent / "small" / large.name


def _small_portrait(img, dest: Path) -> None:
    """Versión chica del retrato: la cabeza (parte de arriba, cuadrada) a 65x67.
    Sin ella el juego arma el nombre de la chica solo y, con retratos que son
    archivos, queda vacío (error.log: Icon definition "_small", 2026-09-29)."""
    from PIL import Image
    sys.path.insert(0, str(REPO))
    from tools.gen import art
    w, h = SMALL_PORTRAIT
    side = min(img.width, round(img.width * h / w))
    head = img.crop((0, 0, img.width, min(img.height, side))).resize((w, h), Image.LANCZOS).convert("RGBA")
    raw = head.tobytes()
    art.write_dds(dest, w, h, [(raw[k], raw[k + 1], raw[k + 2], 255) for k in range(0, len(raw), 4)])


def chicos() -> None:
    """Genera el retrato chico de cada retrato grande que ya está en assets/."""
    from PIL import Image
    made = 0
    for large in sorted(REPO.glob("assets/*/leaders/*.dds")):
        dest = small_path(large)
        if dest.exists():
            continue
        _small_portrait(Image.open(large), dest)
        made += 1
    print(f"{made} retratos chicos generados")


def _load(name: str) -> dict:
    data = yaml.safe_load((SPEC / name).read_text(encoding="utf-8"))
    # 2026-10-27: lo nuevo del programa vive en archivos propios (specload.OVERLAY_FILES);
    # para el arte se suman árboles, personajes, banderas, espíritus y eventos
    try:
        from tools.gen.specload import OVERLAY_FILES
    except ImportError:
        OVERLAY_FILES = []
    for extra in OVERLAY_FILES:
        path = SPEC / extra
        if not path.exists() or not isinstance(data, dict):
            continue
        ov = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if name == "07_focus_trees.yaml":
            data.setdefault("trees", {}).update((ov.get("focus_trees") or {}).get("trees") or {})
        elif name == "03_leaders.yaml":
            data.setdefault("characters", []).extend((ov.get("leaders") or {}).get("characters") or [])
        elif name == "02_countries.yaml":
            data.setdefault("cosmetic_tags", []).extend(ov.get("cosmetic_tags") or [])
        elif name == "14_decisions.yaml":
            data.setdefault("dynamic_modifiers", []).extend((ov.get("decisions") or {}).get("dynamic_modifiers") or [])
        elif name == "12_events.yaml":
            for ns, block in ((ov.get("events") or {}).get("namespaces") or {}).items():
                if ns in data.setdefault("namespaces", {}):
                    data["namespaces"][ns].setdefault("events", []).extend(block.get("events") or [])
                else:
                    data["namespaces"][ns] = block
    return data


def _one_line(text: str) -> str:
    return " ".join(str(text or "").split())


def catalog() -> list[dict]:
    """Todo lo que puede llevar arte, con su destino y si ya lo tiene."""
    items: list[dict] = []
    trees = _load("07_focus_trees.yaml")["trees"]
    for tag, tree in trees.items():
        if not isinstance(tree, dict) or "branches" not in tree:
            continue
        for branch in tree["branches"]:
            for f in branch["focuses"]:
                dest = REPO / "assets" / tag / "goals" / f"{f['id']}.dds"
                items.append({
                    "type": "national_focus_icon", "tag": tag, "id": f["id"], "dest": dest,
                    "done": bool(f.get("icon_asset")) or dest.exists(),
                    "description": f"{f['name']['english']}: {_one_line(f['desc']['english'])}",
                })
    ideas = _load("05_ideas.yaml")["countries"]
    for tag, entry in ideas.items():
        if not isinstance(entry, dict):
            continue
        for group in ("starting_ideas", "focus_ideas"):
            for idea in entry.get(group) or []:
                if not isinstance(idea, dict):
                    continue
                dest = REPO / "assets" / tag / "ideas" / f"{idea['id']}.dds"
                name = idea.get("name", {}).get("english", idea["id"])
                desc = (idea.get("desc") or {}).get("english", "")
                items.append({
                    "type": "national_spirit_icon", "tag": tag, "id": idea["id"], "dest": dest,
                    "done": dest.exists(), "description": f"{name}: {_one_line(desc)}",
                })
    for dm in _load("14_decisions.yaml").get("dynamic_modifiers") or []:
        if dm.get("no_art"):   # 2026-10-17: "sin imágenes" (Bioacero v3 del EFE)
            continue
        tag = dm["country"] or "MEGANATIONS"   # sin país: sirve para todos (Leva Forzosa)
        dest = REPO / "assets" / tag / "ideas" / f"{dm['id']}.dds"
        items.append({
            "type": "national_spirit_icon", "tag": tag, "id": dm["id"], "dest": dest, "done": dest.exists(),
            "description": f"{dm['name']['english']}: {_one_line(dm['desc']['english'])}",
        })
    # Retratos (2026-10-06: "pasame un txt con pedidos de retratos de generales,
    # mariscales, ministros"): todos los personajes sin retrato, también los que
    # no tienen `portrait` en el spec; el generador conecta solo
    # assets/<TAG>/leaders/<id>.dds. Los de arte/retratos_descripciones.yaml
    # llevan el pedido detallado (encuadre, luz, ropa y fondo).
    looks = yaml.safe_load((REPO / "arte" / "retratos_descripciones.yaml").read_text(encoding="utf-8"))
    traits = _load("03_leaders.yaml").get("leader_traits") or {}
    traits = traits if isinstance(traits, dict) else {t["id"]: t for t in traits}
    for ch in _load("03_leaders.yaml").get("characters") or []:
        if not isinstance(ch, dict):
            continue
        portrait = ch.get("portrait") or {}
        tag = ch["country"]
        name = Path(portrait["path"]).name if portrait.get("path") else f"{ch['id']}.dds"
        dest = REPO / "assets" / tag / "leaders" / name
        regnal = (ch.get("name") or {}).get("regnal") or {}
        item = {
            "type": "leader_portrait", "tag": tag, "id": ch["id"], "dest": dest,
            "done": bool(portrait.get("asset") and (REPO / portrait["asset"]).exists()) or dest.exists(),
            "description": (f"{regnal.get('english', ch['id'])}, born {ch.get('born', '?')}: {_one_line(ch.get('lore'))}"
                            if ch.get("lore") else _one_line(portrait.get("description") or regnal.get("english", ch["id"])))
                           + " Head-and-shoulders portrait, facing the viewer.",
        }
        if ch["id"] in (looks.get("characters") or {}) and tag in (looks.get("looks") or {}):
            item["description"] = _portrait(ch, looks["looks"][tag], looks["characters"][ch["id"]], traits)
            item["style"] = PORTRAIT_STYLE
        items.append(item)
    for ct in _load("02_countries.yaml").get("cosmetic_tags") or []:
        tag = ct["parent"]
        dest = REPO / "assets" / tag / "flags" / f"{ct['id']}.tga"
        items.append({
            "type": "country_flag", "tag": tag, "id": ct["id"], "dest": dest, "done": dest.exists(),
            "description": f"National flag of {ct['name']['english']}: {_one_line(ct.get('art', ''))} "
                           "Flat flag design, simple bold shapes and 2-4 colours, readable when tiny, "
                           "fills the whole rectangle, no border, no text.",
        })
    # 2026-10-19: la bandera de base de cada país (antes solo se pedían las cosméticas;
    # los 5 africanos nuevos y el Santuario de Gaia no tenían ninguna)
    import yaml as _yaml
    flag_art = (_yaml.safe_load((REPO / "arte" / "banderas_descripciones.yaml").read_text(encoding="utf-8"))
                or {}).get("banderas") or {} if (REPO / "arte" / "banderas_descripciones.yaml").exists() else {}
    countries = _load("02_countries.yaml")
    for group in countries.values():
        if not isinstance(group, list):
            continue
        for c in group:
            if not isinstance(c, dict) or "tag" not in c or "name" not in c:
                continue
            tag = c["tag"]
            dest = REPO / "assets" / tag / "flags" / f"{tag}.tga"
            name = (c.get("name") or {}).get("english", tag)
            art = flag_art.get(tag) or f"a flag that fits this country: {_one_line(c.get('lore', ''))}"
            items.append({
                "type": "country_flag", "tag": tag, "id": tag, "dest": dest, "done": dest.exists(),
                "description": f"National flag of {name}: {_one_line(art)} "
                               "Flat flag design, simple bold shapes and 2-4 colours, readable when tiny, "
                               "fills the whole rectangle, no border, no text.",
            })
    intel = _load("18_intelligence.yaml")
    for up in intel.get("agency_upgrades") or []:
        dest = REPO / "assets" / "agency" / f"{up['id']}.dds"
        items.append({
            "type": "agency_upgrade_icon", "tag": "INTELIGENCIA", "id": up["id"], "dest": dest, "done": dest.exists(),
            "description": f"Intelligence agency upgrade icon, round badge: {up['english']}: {up['art']}.",
        })
    for bg in ((_load("11_scenario.yaml").get("tab_backgrounds") or {}).get("items") or []):
        dest = REPO / "assets" / "ui" / f"{bg['id']}.dds"
        tile = (" SEAMLESS TILE: the left edge must continue the right edge and the top the bottom."
                if bg.get("seamless") else "")
        items.append({
            "type": "ui_background", "tag": "INTERFAZ", "id": bg["id"], "dest": dest, "done": dest.exists(),
            "size": tuple(bg["size"]),
            "description": f"User interface background for Hearts of Iron IV ({bg['where']}): {bg['art']}. "
                           f"No text, no icons, no buttons; it sits behind the interface.{tile}",
        })
    for bg in ((_load("11_scenario.yaml").get("research_backgrounds") or {}).get("items") or []):
        dest = REPO / "assets" / "ui" / "investigacion" / f"{bg['id']}.dds"
        items.append({
            "type": "research_background", "tag": "INTERFAZ", "id": bg["id"], "dest": dest, "done": dest.exists(),
            "description": f"Background of a Hearts of Iron IV technology tab ({bg['where']}): {bg['art']}. "
                           "Black-and-white photograph look like the vanilla tech tree, detailed on the upper "
                           "left and fading smoothly to pure black towards the right and bottom edges, where "
                           "technology icons sit. No text, no icons, no frame.",
        })
    # Armas por facción, v2 (2026-10-03: "son lo mismo con distinto skin;
    # tienen que diferenciarse mucho más"). Cada pedido lleva la filosofía de
    # diseño de la facción, la descripción detallada del arma y cómo la hacen
    # las otras (para que no salga el mismo objeto con otra pintura).
    look = (_load("17_research.yaml").get("by_faction") or {})
    fams = look.get("families") or {}
    detail = yaml.safe_load((REPO / "arte" / "armas_descripciones.yaml").read_text(encoding="utf-8"))
    for tag, entries in (look.get("names") or {}).items():
        for fam, n in entries.items():
            dest = REPO / "assets" / tag / "armas" / f"{fam}.dds"
            own = _one_line((detail["art"].get(tag) or {}).get(fam, ""))
            others = "; ".join(f"{t}: {_one_line(v[fam])[:90]}..." for t, v in detail["art"].items()
                               if t != tag and fam in v)
            items.append({
                "type": "plane_icon" if fam in PLANE_FAMILIES else "weapon_icon", "tag": tag,
                "id": f"arma_{tag}_{fam}", "dest": dest, "done": dest.exists(),
                "description": (
                    f"WHAT: {fams.get(fam, {}).get('art', fam)} - the {n['en']} ({n['es']}). "
                    f"EXACT DESIGN: {own} "
                    f"FACTION {_one_line(detail['looks'].get(tag, ''))} "
                    "MUST BE UNMISTAKABLE: a player has to recognise the faction from the silhouette alone, without "
                    "colour. Do NOT draw a generic modern weapon with a different paint job; change the shape, the "
                    "materials, the mechanism and the proportions. For contrast, other factions build the same weapon "
                    f"like this (do NOT look like them): {others} "
                    "Single object, three-quarter or side view, centred, fills most of the frame, transparent "
                    "background, no text, no letters, no numbers."),
            })
    # 2026-10-24 (pedido del usuario: "las imágenes de los diseños no progresan; pedidos
    # nuevos para cada investigación, que cada nivel se note en una mejora tecnológica"):
    # una imagen por generación, de la 2 en adelante (la 1 es la de la familia).
    gens_path = REPO / "arte" / "generaciones_armas.yaml"
    gens = yaml.safe_load(gens_path.read_text(encoding="utf-8")) if gens_path.exists() else {}
    tank_like = {"light_tank", "medium_tank", "heavy_tank", "modern_tank", "super_heavy"}
    ship_like = {"destroyer", "cruiser", "capital", "carrier", "submarine"}
    for tag, entries in (look.get("names") or {}).items():
        for fam, n in entries.items():
            top = int((gens.get("generaciones") or {}).get(fam, 1))
            hint_key = "tank" if fam in tank_like else "ship" if fam in ship_like else \
                "plane" if fam in PLANE_FAMILIES else fam
            hint = (gens.get("mejoras") or {}).get(hint_key, "each generation is visibly more advanced")
            own = _one_line((detail["art"].get(tag) or {}).get(fam, ""))
            # 2026-10-24 (eligió el usuario, "criterio del punto 2"): solo la vieja (la de la
            # familia, ya está) y la última; las intermedias usan la más cercana
            for g in ([top] if top > 1 else []):
                dest = REPO / "assets" / tag / "armas" / f"{fam}_{g}.dds"
                stage = "the most advanced, final version"
                items.append({
                    "type": "plane_icon" if fam in PLANE_FAMILIES else "weapon_icon", "tag": tag,
                    "id": f"arma_{tag}_{fam}_{g}", "dest": dest, "done": dest.exists(),
                    "description": (
                        f"GENERATION {g} OF {top} of the {n['en']} ({n['es']}): {fams.get(fam, {}).get('art', fam)}. "
                        f"It is {stage} of the same weapon line, with the SAME faction design language as generation 1 "
                        f"(arma_{tag}_{fam}.png): {own} "
                        f"Show the technological progress so it is obviously far newer than generation 1: "
                        f"{hint}. Keep the faction materials, colours and silhouette family; only the technology level "
                        "changes, like Infantry Equipment I, II, III in Hearts of Iron IV. "
                        f"FACTION {_one_line(detail['looks'].get(tag, ''))} "
                        "Single object, three-quarter or side view, centred, fills most of the frame, transparent "
                        "background, no text, no letters, no numbers."),
                })
    # Equipo común (2026-10-07: "hace falta el pedido para la imagen del tren,
    # uno común para todos"): una imagen para todos los países.
    for fam, f in (look.get("shared") or {}).items():
        dest = REPO / "assets" / "COMUN" / "armas" / f"{fam}.dds"
        items.append({
            "type": "shared_icon", "tag": "COMUN", "id": f"arma_COMUN_{fam}", "dest": dest, "done": dest.exists(),
            "description": _one_line((detail.get("shared") or {}).get(fam) or f.get("art", fam)),
            "style": SHARED_STYLE,
        })
    # Tecnologías comunes (2026-10-10: "hacé el pedido para las imágenes de
    # todas las otras tecnologías que se comparten en común"): una imagen por
    # tecnología, la misma para todos los países.
    items += _tech_items()
    items += _doctrine_items()
    items += _law_items()
    items += _ui_icon_items()
    # Unidades únicas (2026-10-03: "¿no hay imagen única para el Gliptodonte y
    # otras tecnologías únicas?"): su ícono en producción y en sus tecnologías.
    for u in _load("20_unique_units.yaml").get("units") or []:
        tag = u["country"]
        dest = REPO / "assets" / tag / "armas" / f"{u['id']}.dds"
        items.append({
            "type": "unique_icon", "tag": tag, "id": f"arma_{u['id']}", "dest": dest, "done": dest.exists(),
            "description": (
                f"WHAT: the UNIQUE unit of this faction, the {u['name']['english']} ({u['name']['spanish']}); nobody "
                f"else in the world has it, it must look legendary and one of a kind. "
                f"{_one_line((detail.get('unique') or {}).get(u['id'], ''))} "
                f"LORE: {_one_line(u['lore']['english'])} "
                f"FACTION {_one_line(detail['looks'].get(tag, ''))} "
                "Show the machine itself (not soldiers posing), heroic three-quarter view, centred, fills most of the "
                "frame, transparent background, no text, no letters, no numbers."),
        })
        # Niveles de la unidad única (2026-10-27): assets/<TAG>/armas/<id>_<n>.dds
        for n in sorted(int(k) for k in (u.get("art_levels") or {})):
            dest = REPO / "assets" / tag / "armas" / f"{u['id']}_{n}.dds"
            items.append({
                "type": "unique_icon", "tag": tag, "id": f"arma_{u['id']}_{n}", "dest": dest, "done": dest.exists(),
                "description": (
                    f"WHAT: the UNIQUE unit of this faction, the {u['name']['english']} ({u['name']['spanish']}), "
                    f"a newer level of the same machine as arma_{u['id']}.png. "
                    f"{_one_line((detail.get('unique') or {}).get(u['id'] + f'_{n}', ''))} "
                    f"FACTION {_one_line(detail['looks'].get(tag, ''))} "
                    "Show the machine itself, heroic three-quarter view, centred with a margin around it, transparent "
                    "background, no people, no text, no letters, no numbers."),
            })
    spec_events = _load("12_events.yaml")
    shared = spec_events.get("shared_art") or {}
    # descripción larga a mano para algunos eventos (2026-10-13: capitales tomadas)
    long_path = REPO / "arte" / "eventos_descripciones.yaml"
    long_desc = yaml.safe_load(long_path.read_text(encoding="utf-8")) if long_path.exists() else {}
    long_events = long_desc.get("events") or {}
    asked: set[str] = set()
    for ns, block in spec_events["namespaces"].items():
        tag = block.get("country")
        for ev in block.get("events") or []:
            if ev.get("hidden") or ev.get("no_art"):   # no_art: "sin imágenes" (2026-10-17)
                continue
            # `art`: varios eventos casi iguales comparten una sola imagen (2026-09-29)
            art = ev.get("art")
            eid = art or f"{ns}.{ev['id']}"
            if eid in asked:
                continue
            asked.add(eid)
            dest = REPO / "assets" / "events" / f"{eid}.dds"
            desc = (f"{ev['title']['english']}: {_one_line(ev['desc']['english'])}" if not art
                    else _one_line(shared.get(art, ev['desc']['english'])))
            if eid in long_events:
                desc = f"{_one_line(long_events[eid])} {_one_line(long_desc.get('composition', ''))}".strip()
            items.append({
                "type": "event_picture", "tag": "COMPARTIDOS" if art or tag is None else tag, "id": eid, "dest": dest,
                "done": dest.exists(), "description": desc,
            })
    items += _adventure_items()
    items += _loading_items()
    _apply_icon_looks(items)
    return items


LOADING_STYLE = (
    "Hearts of Iron IV loading screen, wide cinematic painting, retrofuturist year 2100, rich painterly detail, "
    "everyday life of ordinary people (not a battle), atmospheric light, no text, no letters, no logos, no watermark"
)


def _loading_items() -> list[dict]:
    """Pantallas de carga de la vida diaria (2026-10-24): una por potencia y anarquía."""
    path = REPO / "arte" / "pantallas_carga_descripciones.yaml"
    if not path.exists():
        return []
    data = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("pantallas") or {}
    items = []
    for n, (tag, p) in enumerate(data.items(), start=20):
        iid = f"{n}_{tag}_vida_diaria"
        dest = REPO / "assets" / "menu" / "loading" / f"{iid}.dds"
        items.append({
            "type": "loading_screen", "tag": tag, "id": iid, "dest": dest, "done": dest.exists(),
            "style": f"{LOADING_STYLE}; {STYLE.get(tag, '')}",
            "description": f"{p['titulo']}: {_one_line(p['escena'])}",
        })
    return items


def _adventure_items() -> list[dict]:
    """Los eventos de las aventuras con `art` (21_aventuras.yaml): la
    presentación, el primer capítulo de cada personaje y los momentos épicos."""
    spec = _load("21_aventuras.yaml") if (SPEC / "21_aventuras.yaml").exists() else {}
    items = []
    for tag, saga in (spec.get("sagas") or {}).items():
        ns = f"meganations_aventura_{tag.lower()}"
        chars = {c["id"]: c["name"]["english"] for c in saga.get("characters") or []}
        intro = dict(saga["intro"], id=2)
        for kind_label, ev in ([("opening scene, the situation and the three characters", intro)]
                               + [("chapter", n) for n in saga.get("nodes") or []]
                               + [("ending: " + e["kind"], e) for e in saga.get("endings") or []]):
            if not ev.get("art"):
                continue
            eid = f"{ns}.{ev['id']}"
            dest = REPO / "assets" / "events" / f"{eid}.dds"
            who = chars.get(ev.get("who"), "")
            story = _one_line(ev["desc"]["english"].replace("\\n", " "))
            items.append({
                "type": "adventure_picture", "tag": tag, "id": eid, "dest": dest, "done": dest.exists(),
                "style": f"{ADVENTURE_STYLE}; palette and world: {saga.get('palette', '')}",
                "description": (f"Adventure '{saga['name']['english']}', {kind_label}"
                                + (f", hero: {who}" if who else "") + f" - {ev['title']['english']}. "
                                f"SCENE TO DRAW: {_one_line(ev['art'])}. "
                                f"STORY CONTEXT (do not write it in the image): {story}"),
            })
    return items


PORTRAIT_STYLE = (
    "photorealistic painted portrait matching the existing leader portraits of this Hearts of Iron IV mod: "
    "realistic skin pores, hair and fabric weave, subtle painterly softness, rich but natural colour grading, "
    "cinematic and believable near-future clothing of the year 2100 (not a sci-fi costume), no helmet or mask "
    "covering the face, no text, no letters, no numbers, no logos with words, no watermark, no frame, no border")

# el vestuario según el cargo (03_leaders -> roles)
_KIND = {"corps_commander": "army", "field_marshal": "army", "navy_leader": "navy",
         "army_chief": "army", "high_command": "army", "navy_chief": "navy", "air_chief": "air"}

# lo que lleva encima según su rasgo, para los que no tienen un detalle propio
_TRAIT_DETAIL = {
    "Master of Manoeuvre": "a leather map case on a strap and a riding crop held in one gloved hand",
    "Defence in Depth": "field glasses hanging at the chest and a folded map in one hand",
    "Flawless Organisation": "a slim folder of orders under the arm and a fountain pen in the breast pocket",
    "Iron Morale": "a ceremonial sword held upright with the hilt at shoulder height and a row of medals on the chest",
    "Rigorous Drill": "a whistle on a lanyard and white gloves held in one hand",
    "Relentless Offensive": "a pistol in a shoulder holster and dust on the face and collar",
    "Fortification Engineer": "an engineer's hard hat under the arm and concrete dust on the sleeves",
    "Logistician": "a clipboard of supply lists and a pencil behind the ear",
    "Elite Infantry": "a beret with an elite unit badge and the sling of a rifle on the shoulder",
    "Reserves and Replacements": "a thick roster folder held against the chest",
    "King of Artillery": "ear defenders hanging around the neck and a brass shell casing in one hand",
    "General Staff": "a folder of staff plans and reading glasses on a cord",
    "Guerrilla Warfare": "a scarf wrapped high around the neck and the sling of a carbine over the shoulder",
}


def _portrait(ch: dict, look: dict, me: dict, traits: dict) -> str:
    """Pedido detallado de un retrato: cara, ropa del cargo, encuadre, luz y fondo."""
    roles = {k: v for k, v in (ch.get("roles") or {}).items() if v}
    kind = me.get("kind")
    trait_names = []
    for role, body in roles.items():
        body = body if isinstance(body, dict) else {}
        kind = kind or _KIND.get(body.get("slot") or role)
        trait_names += [((traits.get(t) or {}).get("name") or {}).get("english", t.replace("_", " "))
                        for t in body.get("traits") or []]
    wear = look.get(kind or "civil") or look.get("army") or look.get("civil")
    regnal = (ch.get("name") or {}).get("regnal") or {}
    who = regnal.get("english") or ch["id"]
    detail = me.get("detail") or next((_TRAIT_DETAIL[t] for t in trait_names if t in _TRAIT_DETAIL), "")
    # que no miren todos hacia el mismo lado
    side, other = ("left", "right") if sum(map(ord, ch["id"])) % 2 else ("right", "left")
    parts = [
        f"WHO: {who} ({regnal.get('spanish', who)}), {look['nation']}.",
        f"Known for: {', '.join(trait_names)}." if trait_names else "",
        f"Lore: {ch['lore']}" if ch.get("lore") else "",
        f"PERSON: a {me['age']}-year-old {me['g']} ({look['faces']}): {me['face']}. "
        f"Expression: {me['expr']}.",
        f"CLOTHING: {wear}.",
        f"DETAIL: {detail}." if detail else "",
        "FRAMING: vertical 3:4 bust portrait (for example 624x840). The frame cuts at mid-chest; the top of the head "
        "sits about 7% below the top edge; the eyes are on the upper-third line; the person is centred and the "
        "shoulders fill about 70% of the width. Anything held stays inside the frame at chest height.",
        f"CAMERA: eye level, 85mm portrait lens at f/2.8; the body turned about 25 degrees to the {side}, the face "
        "turned back almost to the camera, the eyes looking straight into the lens.",
        f"LIGHT: soft key light from the upper {other} at 45 degrees, a gentle fill from the opposite side and a thin "
        f"rim light separating the hair and shoulders from the background; {look['light']}.",
        f"BACKGROUND: {me.get('bg') or look['background']}; recognisable but softer than the face (moderate depth of "
        "field), filling the space around the head and shoulders, in the colours of the nation.",
    ]
    return " ".join(_one_line(x) for x in parts if x)


def _tech_line(tech: str) -> str:
    """La línea de una tecnología: concentrated_industry3 -> concentrated_industry,
    improved_machine_tools -> machine_tools."""
    return re.sub(r"\d+$", "", re.sub(r"^(basic|improved|advanced)_", "", tech))


def _tech_items() -> list[dict]:
    path = REPO / "arte" / "tecnologias_descripciones.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    names = _load("17_research.yaml").get("techs") or {}
    style, comp = _one_line(data["style"]), _one_line(data["composition"])
    items = []
    for group, g in (data.get("groups") or {}).items():
        own = {t: d for t, d in (g.get("techs") or {}).items() if isinstance(d, str)}
        for tech, desc in own.items():
            n = names.get(tech) or {"en": tech, "es": tech}
            siblings = [names.get(t, {}).get("en", t) for t in own
                        if t != tech and _tech_line(t) == _tech_line(tech)]
            other = (f"OTHER ICONS OF THE SAME LINE (each one is a separate image; this one must look clearly "
                     f"different from all of them, never the same object again): {', '.join(siblings)}. "
                     if siblings else "")
            dest = REPO / "assets" / "COMUN" / "tecnologias" / f"{tech}.dds"
            items.append({
                "type": "tech_icon", "tag": group, "id": f"tec_{tech}", "dest": dest, "done": dest.exists(),
                "description": (f"WHAT: icon of the technology {n['en']} ({n['es']}), {_one_line(g['intro'])}. "
                                f"EXACT SUBJECT: {_one_line(desc)} {other}{comp}"),
                "style": style,
            })
    return items


# 2026-10-13 (captura de la pantalla de doctrinas: "fijate cómo son ahora los
# íconos, no pueden ser muy cargados"): los del juego son glifos simples, uno
# o dos objetos (un avión y una explosión), pocos colores, sin fondo.
DOCTRINE_STYLE = (
    "simple flat-shaded game icon in the exact style of the Hearts of Iron IV doctrine icons: ONE or TWO small "
    "subjects only (for example an aircraft and an explosion, or a soldier and a shield), bold clean silhouette, "
    "thin dark outline, soft cel shading, limited palette (blue-grey and steel for machines, orange-red for fire, "
    "white highlights), the near future of the year 2100 but restrained, NOT busy, no scenery, no background, "
    "transparent PNG, must read clearly at 48x48 pixels, no text, no letters, no numbers, no watermark"
)
_NAVAL_WORDS = ("cruiser", "battleship", "line_of_battle", "carrier", "convoy", "fleet", "boat", "torpedo", "naval",
                "jeune", "task_force", "screen", "airfield", "hunter_killer", "base_strike")


def _doctrine_items() -> list[dict]:
    spec = _load("17_research.yaml").get("doctrines") or {}
    items = []
    for kind, entries in (("grand", spec.get("grand") or {}), ("sub", spec.get("sub") or {})):
        for key, d in entries.items():
            if key.endswith("_no_lar"):
                continue      # la variante sin La Resistance usa la misma imagen
            if d.get("domain"):
                domain = d["domain"]
            elif key.startswith("air_subdoctrine") and not any(w in key for w in ("naval", "ocean", "carrier", "coastal")):
                domain = "air force"
            elif key.startswith("air_subdoctrine"):
                domain = "naval air arm"
            elif any(w in key for w in _NAVAL_WORDS):
                domain = "navy"
            elif key.startswith("special_forces"):
                domain = "special forces"
            else:
                domain = "land army"
            subject = d.get("art") or f"a simple emblem that shows the idea of '{d['en']}' for a {domain} of the year 2100"
            dest = REPO / "assets" / "COMUN" / "doctrinas" / f"{key}.dds"
            items.append({
                "type": "doctrine_icon", "tag": "DOCTRINAS", "id": f"doc_{key}", "dest": dest, "done": dest.exists(),
                "description": (f"WHAT: icon of the {'grand ' if kind == 'grand' else ''}military doctrine "
                                f"{d['en']} ({d['es']}), {domain}. EXACT SUBJECT: {subject}. Keep it as simple as "
                                f"the game's own doctrine icons: at most two objects, centred, filling about 80% "
                                f"of the canvas."),
                "style": DOCTRINE_STYLE,
            })
    return items


# 2026-10-15 ("haceme el pedido de imágenes para el menú de país, leyes
# económicas, reclutamiento"): una imagen por ley, la misma para todos los países.
LAW_STYLE = (
    "small painted icon in the style of the Hearts of Iron IV law and national spirit icons: one clear scene or "
    "object, bold readable silhouette, painterly propaganda-poster look, the near future of the year 2100 (not "
    "science-fantasy), neutral design that belongs to no nation (no flags, no national colours, no emblems), "
    "restrained palette of steel, concrete, graphite and muted earth tones with one accent light, no scenery beyond "
    "what the subject needs, transparent PNG background, must read clearly at 64x64 pixels, no text, no letters, "
    "no numbers, no watermark"
)
_LAW_CATEGORY = {"economy": "economy law", "trade_laws": "trade law", "mobilization_laws": "recruitment law"}


def _law_items() -> list[dict]:
    spec = _load("05_ideas.yaml").get("laws") or {}
    items = []
    for cat, what in _LAW_CATEGORY.items():
        laws = spec.get(cat) or {}
        siblings = [d["en"] for d in laws.values()]
        for key, d in laws.items():
            dest = REPO / "assets" / "COMUN" / "leyes" / f"{key}.dds"
            others = ", ".join(n for n in siblings if n != d["en"])
            items.append({
                "type": "law_icon", "tag": "LEYES", "id": f"ley_{key}", "dest": dest, "done": dest.exists(),
                "description": (f"WHAT: icon of the {what} {d['en']} ({d['es']}) in the country menu, the year 2100. "
                                f"EXACT SUBJECT: {_one_line(d['art'])} The other laws of the same menu are "
                                f"{others}: this icon must look clearly different from theirs. COMPOSITION: one "
                                f"subject centred, filling about 80% of the square canvas, little empty space."),
                "style": LAW_STYLE,
            })
    return items


def _ui_icon_items() -> list[dict]:
    """Íconos nuevos de la piel de la interfaz (arte/piel_interfaz.yaml)."""
    import yaml
    path = REPO / "arte" / "piel_interfaz.yaml"
    if not path.exists():
        return []
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = []
    for p in spec.get("iconos") or []:
        dest = REPO / "assets" / "ui" / "piel_iconos" / f"{p['id']}.dds"
        n = int(p.get("cuadros", 1))
        size = None
        if p.get("ancho") and p.get("alto"):
            size = (int(p["ancho"]), int(p["alto"]))
        photo = p.get("uso") == "foto"
        items.append({
            "type": "ui_icon", "tag": "INTERFAZ", "id": f"ui_{p['id']}", "dest": dest, "done": dest.exists(),
            "size": size or ((624, 840) if photo else (512, 512)),
            "transparent": not photo,
            "description": (f"WHAT: {p['donde']}, in the redesigned interface of a 2100 grand strategy game"
                            + (f" (the game shows it as {n} states; Claude makes them from this one image)" if n > 1 else "")
                            + f". EXACT SUBJECT: {_one_line(p['dibujo'])}"),
            "style": _one_line(p.get("estilo") or spec.get("estilo_iconos") or ""),
        })
    # tiras (2026-10-28): los íconos de edificios y recursos, pedidos a mano en
    # arte/pedidos_edificios.txt y arte/pedidos_recursos.txt; acá solo para que
    # `importar` los reconozca por su nombre de archivo
    vistos: set[str] = set()   # los recursos están en dos tiras (normal y "falta")
    for t in spec.get("tiras") or []:
        for ident in dict.fromkeys((t.get("iconos") or {}).values()):
            if ident in vistos:
                continue
            vistos.add(ident)
            dest = REPO / "assets" / "ui" / "piel_iconos" / f"{ident}.dds"
            items.append({
                "type": "ui_icon", "tag": "INTERFAZ", "id": ident, "dest": dest, "done": dest.exists(),
                "size": (512, 512), "transparent": True, "hand_written": True,
                "description": f"WHAT: {t.get('donde', '')}. EXACT SUBJECT: ver el pedido escrito a mano ({ident}).",
                "style": _one_line(spec.get("estilo_iconos") or ""),
            })
    return items


PLANE_FAMILIES = {"light_plane", "medium_plane", "carrier_plane", "heavy_plane"}
SINGLE_FILE = {"unique_icon", "plane_icon", "shared_icon", "loading_screen"}
TECH_GROUPS = ("INFANTERIA", "APOYO", "BLINDADOS", "ARTILLERIA", "NAVAL", "AVIACION", "INGENIERIA", "INDUSTRIA")

# 2026-10-19 ("¿la descripción de los espíritus alcanza para que ChatGPT las
# haga bien?" -> "reescribí la lista"): ícono = un solo objeto claro, sin escena.
ICON_STYLE = (
    "small painted icon in the style of the Hearts of Iron IV national spirit and focus icons: ONE clear central "
    "object or symbol, bold readable silhouette with a dark outline, painterly but simple, strong contrast, "
    "the year 2100, NO scenery and NO crowd, nothing small or fussy, transparent PNG background, must read clearly "
    "at {w}x{h} pixels, no text, no letters, no numbers, no watermark"
)


def _apply_icon_looks(items: list[dict]) -> None:
    """Reemplaza el texto del juego por un pedido visual (arte/iconos_descripciones.yaml)."""
    import yaml
    path = REPO / "arte" / "iconos_descripciones.yaml"
    if not path.exists():
        return
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    looks, palettes = spec.get("iconos") or {}, spec.get("paletas") or {}
    for item in items:
        look = looks.get(item["id"])
        if not look or item["type"] not in ("national_spirit_icon", "national_focus_icon"):
            continue
        w, h = KINDS[item["type"]]["size"]
        name = item["description"].split(":", 1)[0]
        what = "national spirit" if item["type"] == "national_spirit_icon" else "national focus"
        palette = look.get("paleta") or palettes.get(item["tag"]) or STYLE.get(item["tag"]) or palettes.get("MEGANATIONS", "")
        item["description"] = (f"WHAT: icon of the {what} '{name}'. EXACT SUBJECT: {_one_line(look['dibujo'])}. "
                               f"COMPOSITION: that single subject centred, filling about 80% of the canvas, "
                               f"little empty space, no background scene.")
        item["style"] = ICON_STYLE.format(w=w, h=h) + f"; palette: {palette}"


SHARED_STYLE = (
    "photorealistic 3D-rendered equipment icon matching the weapon icons of this Hearts of Iron IV mod: realistic "
    "materials, weathering and reflections, crisp detail that still reads at 150x55 pixels, neutral design that "
    "belongs to no faction (no national colours, no emblems), no text, no letters, no numbers, no watermark")

UI_STYLE = ("game user-interface background texture, subtle and low contrast so text and buttons stay readable, "
            "no text, no letters, no logos, no watermark, no frame")

FLAG_STYLE = ("flat national flag for Hearts of Iron IV, vexillology, clean flat shapes, no gradients, "
              "no painterly texture, no text, no letters, no watermark")


def _request(item: dict) -> str:
    kind = KINDS[item["type"]]
    w, h = item.get("size") or kind["size"]
    style = STYLE.get(item["tag"] or "", "shadowy espionage of the year 2100: dark teal and brass, dossiers, "
                      "circuitry and surveillance" if item["tag"] == "INTELIGENCIA" else
                      "clean dark user-interface texture for a 2100 grand strategy game, muted teal, graphite and brass"
                      if item["tag"] == "INTERFAZ" else "a ruined, fragmented 2100 world: improvised flags, bunkers, "
                                          "warlord or client-state officials, muted colours")
    common = (FLAG_STYLE if item["type"] == "country_flag"
              else UI_STYLE if item["type"] in ("ui_background", "research_background") else COMMON_STYLE)
    return "\n".join([
        "ASSET_REQUEST",
        f"type: {item['type']}",
        f"id: {item['id']}",
        f"filename: {item['id']}.png",
        f"size: {w}x{h} (o más grande con la misma proporción)",
        f"style: {item['style'] if item.get('style') else common + '; ' + style}",
        f"description: {item['description']}",
        f"transparent_background: {'true' if item.get('transparent', kind['transparent']) else 'false'}",
        "",
    ])


NEW_FILE = "0_NUEVOS_de_este_lote.txt"


def _previous_ids() -> set[str] | None:
    """Los ids que ya estaban pedidos en el zip anterior (para separar lo nuevo)."""
    if not ZIP.exists():
        return None
    ids: set[str] = set()
    with zipfile.ZipFile(ZIP) as z:
        for name in z.namelist():
            if name.endswith(NEW_FILE):
                continue
            for line in z.read(name).decode("utf-8").splitlines():
                if line.startswith("id: "):
                    ids.add(line[4:].strip())
    return ids


def pedidos() -> None:
    items = [i for i in catalog() if not i["done"] and not i.get("hand_written")]
    OUT.mkdir(parents=True, exist_ok=True)
    before = _previous_ids()
    old_new = (OUT / NEW_FILE).read_text(encoding="utf-8") if (OUT / NEW_FILE).exists() else None
    for old in OUT.glob("*.txt"):
        old.unlink()
    # Lo pedido por primera vez en esta corrida, junto en un archivo aparte
    # (2026-09-29: "hacer el txt para el pedido a chatgpt de las imágenes").
    fresh = [i for i in items if before is not None and i["id"] not in before]
    if fresh:
        (OUT / NEW_FILE).write_text(f"# {len(fresh)} pedidos nuevos de este lote (también están en los archivos por potencia)\n\n"
                                    + "\n".join(_request(i) for i in fresh), encoding="utf-8")
    elif old_new:
        # sin pedidos nuevos queda la lista anterior, sin lo que ya llegó
        # (2026-10-11: seguía listando banderas y retratos ya importados)
        old_ids = {line[4:].strip() for line in old_new.splitlines() if line.startswith("id: ")}
        still = [i for i in items if i["id"] in old_ids]
        if still:
            (OUT / NEW_FILE).write_text(f"# {len(still)} pedidos nuevos de este lote (también están en los archivos por potencia)\n\n"
                                        + "\n".join(_request(i) for i in still), encoding="utf-8")
    order = [("leader_portrait", "1_retratos"), ("national_spirit_icon", "2_espiritus"),
             ("national_focus_icon", "3_focos"), ("event_picture", "4_eventos"),
             ("country_flag", "5_banderas"), ("agency_upgrade_icon", "6_agencia"),
("ui_background", "7_fondos"),
             ("research_background", "8_investigacion"), ("weapon_icon", "9_armas"),
             ("unique_icon", "10_unidades_unicas"), ("plane_icon", "11_aviones"), ("shared_icon", "12_equipo_comun"),
             ("tech_icon", "13_tecnologias"), ("doctrine_icon", "14_doctrinas"), ("law_icon", "15_leyes"),
             ("ui_icon", "16_interfaz"), ("adventure_picture", "17_aventura"),
             ("loading_screen", "18_pantallas_de_carga")]
    summary = []
    for kind, prefix in order:
        by_tag: dict[str, list[dict]] = {}
        for i in items:
            if i["type"] == kind:
                by_tag.setdefault(i["tag"] if i["tag"] in STYLE or i["tag"] in ("INTELIGENCIA", "INTERFAZ", "DOCTRINAS") + TECH_GROUPS + ("LEYES",)
                                  else "SATELITES_Y_ANARQUIA", []).append(i)
        if kind in SINGLE_FILE and by_tag:
            # un solo archivo, ordenado por facción
            by_tag = {"": [i for _, g in sorted(by_tag.items()) for i in g]}
        for tag, group in sorted(by_tag.items()):
            path = OUT / (f"{prefix}.txt" if not tag else f"{prefix}_{tag}.txt")
            path.write_text(f"# {len(group)} pedidos - {kind} - {tag or 'todas las facciones'}\n\n"
                            + "\n".join(_request(i) for i in group), encoding="utf-8")
            summary.append(f"{path.name}: {len(group)}")
    (OUT / "0_LEEME.txt").write_text(_readme(summary), encoding="utf-8")
    _zip_pedidos()
    print(f"{len(items)} pedidos en {OUT} (y {ZIP.relative_to(REPO)})")
    for line in summary:
        print("  " + line)


ZIP = REPO / "arte" / "pedidos.zip"


def _zip_pedidos() -> None:
    """Todos los pedidos en un zip, para bajarlos con un solo link
    (2026-09-29: "pasame link para mod y para arte"). Fechas fijas: el zip
    solo cambia si cambian los pedidos."""
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(OUT.glob("*.txt")):
            info = zipfile.ZipInfo(f"pedidos/{path.name}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, path.read_bytes())


def _readme(summary: list[str]) -> str:
    return "\n".join([
        "PEDIDOS DE ARTE - 2100 MEGANATIONS",
        "==================================",
        "",
        "Para el generador de imágenes (ChatGPT):",
        "- Cada bloque ASSET_REQUEST es UNA imagen.",
        "- La imagen se entrega con el nombre de `filename` EXACTO (el id + .png).",
        "- Respetar la proporción de `size`; más grande está bien (se achica sola).",
        "- transparent_background: true -> PNG con fondo transparente.",
        "- Sin texto ni letras dentro de la imagen.",
        "- Mismo estilo dentro de cada potencia (ver `style`).",
        "",
        "Para devolver: juntar las imágenes en un .zip y pasárselo a Claude, que las",
        "convierte (tools/arte) y quedan conectadas solas en el próximo build.",
        "",
        "Orden sugerido: 1 retratos, 2 espíritus, 3 focos, 4 eventos, 5 banderas, 9 armas por facción.",
        "17_aventura_<TAG>: las aventuras de cada anarquía, estilo historieta (Moebius + Kill Six Billion",
        "Demons); conviene pedir cada archivo en una misma conversación para que los personajes se parezcan.",
        f"Lo nuevo de la última tanda está junto en {NEW_FILE}.",
        "",
        "Archivos:",
        *("  " + s for s in summary),
        "",
    ])


# ---------------------------------------------------------------------------


def _fundir(img):
    """Fondo de rama de investigación: el negro pasa a transparente y los
    bordes derecho e inferior se desvanecen del todo, así la foto se funde con
    el fondo de la ventana en vez de terminar en un rectángulo negro."""
    from PIL import Image, ImageChops, ImageFilter
    img = img.convert("RGBA")
    w, h = img.size
    luz = img.convert("L").filter(ImageFilter.GaussianBlur(max(2, w // 128)))
    alpha = luz.point(lambda v: min(255, v * 5))
    # rampa geométrica: el último 20% del ancho y del alto llega a cero
    ramp_x = Image.linear_gradient("L").rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT).resize((w, h))
    ramp_x = ramp_x.point(lambda v: min(255, v * 5))
    ramp_y = Image.linear_gradient("L").transpose(Image.FLIP_TOP_BOTTOM).resize((w, h))
    ramp_y = ramp_y.point(lambda v: min(255, v * 5))
    alpha = ImageChops.multiply(ImageChops.multiply(alpha, ramp_x), ramp_y)
    img.putalpha(alpha)
    return img


def _recortar(img, umbral=16, margen=0.03):
    """Recorta el aire transparente alrededor del arma.

    Cada imagen trae el arma con un margen distinto (un fusil fino ocupa el 40%
    del cuadro, un tanque el 95%); sin recortar, en el juego unas se ven
    diminutas y otras llenan el ícono. Recortado, todas llenan su ranura igual.
    """
    caja = img.getchannel("A").point(lambda a: 255 if a > umbral else 0).getbbox()
    if not caja:
        return img
    l, t, r, b = caja
    m = round(max(r - l, b - t) * margen)
    return img.crop((max(0, l - m), max(0, t - m), min(img.width, r + m), min(img.height, b + m)))


def importar(source: str) -> None:
    from PIL import Image  # solo acá: el instalador del usuario no lo necesita

    sys.path.insert(0, str(REPO))
    from tools.gen import art

    by_id = {i["id"]: i for i in catalog()}
    src = Path(source)
    tmp = None
    if src.suffix.lower() == ".zip":
        tmp = tempfile.TemporaryDirectory()
        with zipfile.ZipFile(src) as z:
            z.extractall(tmp.name)
        src = Path(tmp.name)
    done, unknown = [], []
    for path in sorted(src.rglob("*")):
        if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        item = by_id.get(path.stem)
        if item is None:
            unknown.append(path.name)
            continue
        kind = KINDS[item["type"]]
        w, h = item.get("size") or kind["size"]
        img = Image.open(path).convert("RGBA")
        if item["type"] == "loading_screen":
            # 2026-10-24: como las pantallas que ya hay (1920x1440, DXT1); sin comprimir pesarían 11 MB
            iw, ih = img.size
            scale = max(w / iw, h / ih)
            img = img.convert("RGB").resize((max(w, round(iw * scale)), max(h, round(ih * scale))), Image.LANCZOS)
            left, top = (img.width - w) // 2, (img.height - h) // 2
            item["dest"].parent.mkdir(parents=True, exist_ok=True)
            img.crop((left, top, left + w, top + h)).save(item["dest"], "DDS", pixel_format="DXT1")
            done.append(f"{item['type']:22} {item['id']} -> {item['dest'].relative_to(REPO)}")
            continue
        if item["type"] == "ui_icon":
            if item.get("transparent", True):
                img = _recortar(img)
            img.thumbnail((1024, 1024), Image.LANCZOS)
            raw = img.tobytes()
            art.write_dds(item["dest"], img.width, img.height, [tuple(raw[k:k + 4]) for k in range(0, len(raw), 4)])
            done.append(f"{item['type']:22} {item['id']} -> {item['dest'].relative_to(REPO)}")
            continue
        if item["type"] in ("weapon_icon", "plane_icon", "unique_icon", "shared_icon", "tech_icon", "doctrine_icon", "law_icon"):
            img = _recortar(img)
        if kind["fit"] == "cover":
            scale = max(w / img.width, h / img.height)
            img = img.resize((max(w, round(img.width * scale)), max(h, round(img.height * scale))), Image.LANCZOS)
            left, top = (img.width - w) // 2, (img.height - h) // 2
            img = img.crop((left, top, left + w, top + h))
        else:
            # también agranda: un arma recortada puede quedar más chica que la ranura
            scale = min(w / img.width, h / img.height)
            img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
            canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            canvas.paste(img, ((w - img.width) // 2, (h - img.height) // 2), img)
            img = canvas
        if item["type"] == "country_flag":
            # TGA en tres tamaños, junto a la bandera del país
            for sub, (fw, fh) in (("", (82, 52)), ("medium/", (41, 26)), ("small/", (10, 7))):
                flag = img.convert("RGB").resize((fw, fh), Image.LANCZOS)
                raw = flag.tobytes()
                art.write_tga(item["dest"].parent / sub / item["dest"].name, fw, fh,
                              [tuple(raw[k:k + 3]) for k in range(0, len(raw), 3)])
            done.append(f"{item['type']:22} {item['id']} -> {item['dest'].relative_to(REPO)}")
            continue
        if item["type"] == "research_background":
            img = _fundir(img)
        raw = img.tobytes()
        pixels = [tuple(raw[k:k + 4]) for k in range(0, len(raw), 4)]
        if not kind["transparent"]:
            pixels = [(r, g, b, 255) for r, g, b, _ in pixels]
        art.write_dds(item["dest"], w, h, pixels)
        if item["type"] == "leader_portrait":
            _small_portrait(img, small_path(item["dest"]))
        done.append(f"{item['type']:22} {item['id']} -> {item['dest'].relative_to(REPO)}")
    print(f"{len(done)} imagenes importadas")
    for line in done:
        print("  " + line)
    if any(line.startswith("ui_icon") for line in done):
        from tools.arte import piel
        for line in piel.aplicar():
            print(line)
    if unknown:
        print(f"{len(unknown)} sin id conocido (nombre de archivo distinto al pedido): {', '.join(unknown)}")
    if tmp:
        tmp.cleanup()


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "pedidos":
        pedidos()
    elif len(sys.argv) >= 3 and sys.argv[1] == "importar":
        importar(sys.argv[2])
    elif len(sys.argv) >= 2 and sys.argv[1] == "chicos":
        chicos()
    elif len(sys.argv) >= 2 and sys.argv[1] == "piel":
        from tools.arte import piel
        piel.main(sys.argv[2:])
    else:
        print(__doc__)
