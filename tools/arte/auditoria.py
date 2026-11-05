"""Auditoría de los íconos del juego que siguen siendo los de 1936 (2026-11-03).

Pedido: "estoy seguro que todavía hay mil íconos y cositas para cambiar,
averiguá eso y hacé el pedido".

Lee el inventario y las texturas originales del ui_para_claude.zip y arma
arte/iconos_juego.yaml con las familias que se ven todo el tiempo:
  - decisiones: los íconos genéricos de decisión y de categoría (las casi 700
    decisiones del mod usan 13 de ellos);
  - alertas: la tira de alertas, la de pedidos diplomáticos y la de teatros;
  - diseñador: los módulos y huecos del diseñador de tanques, aviones y barcos;
  - ideas: los dos íconos genéricos que el mod todavía usa.
Por cada ícono deja una imagen de referencia (arte/referencias/<id>.png, el
original agrandado): el pedido le dice al generador "el mismo motivo que la
referencia, dibujado de nuevo en el estilo del mod". Así se pueden pedir
cientos sin describir cada uno a mano.

    python3 -m tools.arte.arte auditar <carpeta del ui_para_claude.zip>

El resultado lo usan tools/arte/arte.py (pedidos, 19_iconos_juego) y
tools/arte/piel.py (los pone en su lugar cuando llegan).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
YAML = REPO / "arte" / "iconos_juego.yaml"
REFS = REPO / "arte" / "referencias"

ESTILO = (
    "game user-interface icon for a grand strategy game set in the year 2100, matching the existing "
    "'2100 Meganations' icon set: aged bronze and warm copper metal (#c27a45 highlights #f0b585, shadows "
    "#6b3a1c), crisp art-deco engraving, at most one small coloured accent (teal #4fd6c8, or the colour the "
    "reference uses to mean something: red for danger, green for good). Solid dark outline about 3% of the "
    "canvas wide. Flat straight-on front view, light from the top left, no cast shadow. One bold simple "
    "silhouette with at most three inner details: it must read at 30 pixels. Transparent background, nothing "
    "around the subject: no plate, no circle, no frame. No text, no letters, no numbers, no watermark.")

FAMILIAS = {
    "decisiones": "decision icon of the Decisions panel",
    "categorias": "decision category icon of the Decisions panel",
    "alertas": "alert icon of the top bar (the game shows it when something needs attention)",
    "diplomacia": "diplomatic request icon of the top bar",
    "teatros": "theatre alert icon next to the army groups",
    "disenador": "module icon of the equipment designer (tanks, planes, ships)",
    "ideas": "national spirit icon",
}


def _que(nombre: str) -> str:
    """Lo que muestra, a partir del nombre de la textura o del sprite."""
    n = re.sub(r"^(GFX_)?(EMI_|EMSI_)?(decision_category_generic_|decision_generic_|idea_generic_)?", "", nombre)
    n = re.sub(r"(_icon|_icn|\.dds)$", "", n)
    return n.replace("_", " ").strip()


def armar(zipdir: str) -> list[str]:
    import yaml
    from PIL import Image
    root = Path(zipdir)
    inv = (root / "ui_inventario.txt").read_text(encoding="utf-8").splitlines()
    orig = root / "originales"
    REFS.mkdir(parents=True, exist_ok=True)
    iconos, tiras, vistos = [], [], set()

    def ref(img, ident):
        img = img.convert("RGBA")
        k = max(1, 256 // max(img.size))
        img.resize((img.width * k, img.height * k), Image.LANCZOS).save(REFS / f"{ident}.png")

    for linea in inv:
        if not linea.startswith("  gfx"):
            continue
        tex = re.sub("/+", "/", linea.split()[0])
        if tex in vistos or not (orig / tex).exists():
            continue
        m = re.search(r"\((\d+) cuadros", linea)
        n = int(m.group(1)) if m else 1
        sprites = re.findall(r"GFX_\w+", linea)
        fam = None
        if re.search(r"decisions/decision_generic_", tex) and not re.search(r"_flag|PLACEHOLDER|belgian|GER|USA", tex):
            fam = "decisiones"
        elif "decision_category_generic" in tex:
            fam = "categorias"
        elif tex.endswith(("alerts/global_alert_icons.dds", "alerts/global_alert_icons_no_backgrounds.dds")):
            fam = "alertas"
        elif tex.endswith("alerts/global_diplorequest_icons.dds"):
            fam = "diplomacia"
        elif tex.endswith("alerts/theater_alerts_strip.dds"):
            fam = "teatros"
        elif "equipmentdesigner" in tex and any(s.startswith(("GFX_EMI_", "GFX_EMSI_")) for s in sprites):
            fam = "disenador"
        elif re.search(r"ideas/idea_generic_(army_support|production_bonus)\.dds$", tex):
            fam = "ideas"
        if fam is None:
            continue
        vistos.add(tex)
        img = Image.open(orig / tex)
        base = re.sub(r"[^a-z0-9]+", "_", Path(tex).stem.lower()).strip("_")
        if n > 1 and fam in ("alertas", "diplomacia", "teatros"):
            if "no_backgrounds" in tex:
                continue   # misma tira sin placa: usa los mismos dibujos
            fw = img.width // n
            mapa = {}
            for k in range(n):
                ident = f"juego_{fam}_{k + 1:02d}"
                ref(img.crop((k * fw, 0, (k + 1) * fw, img.height)), ident)
                mapa[k + 1] = ident
            tiras.append({"textura": tex, "cuadros": n, "uso": "barra", "borde": 4, "familia": fam,
                          "iconos": mapa, "donde": FAMILIAS[fam]})
            continue
        ident = f"juego_{fam}_{base}"
        fw = img.width // n
        ref(img.crop((0, 0, fw, img.height)), ident)
        iconos.append({"id": ident, "textura": tex, "uso": "directo", "cuadros": n, "familia": fam,
                       "donde": FAMILIAS[fam], "que": _que(sprites[0] if sprites else base)})
    datos = {"estilo": ESTILO, "iconos": iconos, "tiras": tiras}
    YAML.write_text("# Generado por tools/arte/auditoria.py (2026-11-03): íconos del juego que siguen siendo\n"
                    "# los de 1936, con su imagen de referencia en arte/referencias/. No editar a mano.\n"
                    + yaml.safe_dump(datos, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
    from collections import Counter
    c = Counter(i["familia"] for i in iconos)
    for t in tiras:
        c[t["familia"]] += len(t["iconos"])
    return [f"auditoría: {sum(c.values())} íconos del juego por cambiar ({', '.join(f'{k} {v}' for k, v in c.items())})",
            f"  {YAML.relative_to(REPO)} y {len(list(REFS.glob('*.png')))} referencias en {REFS.relative_to(REPO)}"]


def cargar() -> dict:
    import yaml
    return yaml.safe_load(YAML.read_text(encoding="utf-8")) if YAML.exists() else {}
