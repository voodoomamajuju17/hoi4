"""Circuito de arte con un generador de imágenes externo (ChatGPT u otro).

  python -m tools.arte.arte pedidos            escribe arte/pedidos/*.txt
  python -m tools.arte.arte importar <carpeta|zip>
                                              convierte y ubica las imágenes

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
}

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
}


def _load(name: str) -> dict:
    return yaml.safe_load((SPEC / name).read_text(encoding="utf-8"))


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
    for ch in _load("03_leaders.yaml").get("characters") or []:
        portrait = (ch.get("portrait") or {}) if isinstance(ch, dict) else {}
        if not portrait.get("path"):
            continue
        tag = ch["country"]
        dest = REPO / "assets" / tag / "leaders" / Path(portrait["path"]).name
        regnal = (ch.get("name") or {}).get("regnal") or {}
        items.append({
            "type": "leader_portrait", "tag": tag, "id": ch["id"], "dest": dest,
            "done": bool(portrait.get("asset")) or dest.exists(),
            "description": f"{regnal.get('english', ch['id'])}, born {ch.get('born', '?')}: "
                           f"{_one_line(ch.get('lore'))} Head-and-shoulders portrait, facing the viewer.",
        })
    events = _load("12_events.yaml")["namespaces"]
    for ns, block in events.items():
        tag = block.get("country")
        for ev in block.get("events") or []:
            if ev.get("hidden"):
                continue
            eid = f"{ns}.{ev['id']}"
            dest = REPO / "assets" / "events" / f"{eid}.dds"
            items.append({
                "type": "event_picture", "tag": tag, "id": eid, "dest": dest, "done": dest.exists(),
                "description": f"{ev['title']['english']}: {_one_line(ev['desc']['english'])}",
            })
    return items


def _request(item: dict) -> str:
    kind = KINDS[item["type"]]
    w, h = kind["size"]
    style = STYLE.get(item["tag"] or "", "a ruined, fragmented 2100 world: improvised flags, bunkers, "
                                          "warlord or client-state officials, muted colours")
    return "\n".join([
        "ASSET_REQUEST",
        f"type: {item['type']}",
        f"id: {item['id']}",
        f"filename: {item['id']}.png",
        f"size: {w}x{h} (o más grande con la misma proporción)",
        f"style: {COMMON_STYLE}; {style}",
        f"description: {item['description']}",
        f"transparent_background: {'true' if kind['transparent'] else 'false'}",
        "",
    ])


def pedidos() -> None:
    items = [i for i in catalog() if not i["done"]]
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.txt"):
        old.unlink()
    order = [("leader_portrait", "1_retratos"), ("national_spirit_icon", "2_espiritus"),
             ("national_focus_icon", "3_focos"), ("event_picture", "4_eventos")]
    summary = []
    for kind, prefix in order:
        by_tag: dict[str, list[dict]] = {}
        for i in items:
            if i["type"] == kind:
                by_tag.setdefault(i["tag"] if i["tag"] in STYLE else "SATELITES_Y_ANARQUIA", []).append(i)
        for tag, group in sorted(by_tag.items()):
            path = OUT / f"{prefix}_{tag}.txt"
            path.write_text(f"# {len(group)} pedidos - {kind} - {tag}\n\n"
                            + "\n".join(_request(i) for i in group), encoding="utf-8")
            summary.append(f"{path.name}: {len(group)}")
    (OUT / "0_LEEME.txt").write_text(_readme(summary), encoding="utf-8")
    print(f"{len(items)} pedidos en {OUT}")
    for line in summary:
        print("  " + line)


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
        "Orden sugerido: 1 retratos, 2 espíritus, 3 focos, 4 eventos.",
        "",
        "Archivos:",
        *("  " + s for s in summary),
        "",
    ])


# ---------------------------------------------------------------------------


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
        w, h = kind["size"]
        img = Image.open(path).convert("RGBA")
        if kind["fit"] == "cover":
            scale = max(w / img.width, h / img.height)
            img = img.resize((max(w, round(img.width * scale)), max(h, round(img.height * scale))), Image.LANCZOS)
            left, top = (img.width - w) // 2, (img.height - h) // 2
            img = img.crop((left, top, left + w, top + h))
        else:
            img.thumbnail((w, h), Image.LANCZOS)
            canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            canvas.paste(img, ((w - img.width) // 2, (h - img.height) // 2), img)
            img = canvas
        raw = img.tobytes()
        pixels = [tuple(raw[k:k + 4]) for k in range(0, len(raw), 4)]
        if not kind["transparent"]:
            pixels = [(r, g, b, 255) for r, g, b, _ in pixels]
        art.write_dds(item["dest"], w, h, pixels)
        done.append(f"{item['type']:22} {item['id']} -> {item['dest'].relative_to(REPO)}")
    print(f"{len(done)} imagenes importadas")
    for line in done:
        print("  " + line)
    if unknown:
        print(f"{len(unknown)} sin id conocido (nombre de archivo distinto al pedido): {', '.join(unknown)}")
    if tmp:
        tmp.cleanup()


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "pedidos":
        pedidos()
    elif len(sys.argv) >= 3 and sys.argv[1] == "importar":
        importar(sys.argv[2])
    else:
        print(__doc__)
