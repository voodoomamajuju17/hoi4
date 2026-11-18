"""Rediseño de los árboles de foco (2026-11-18): verificación y vistas previas.

  rutas(arbol)              duración de cada ruta (cada combinación de disyuntivas): la suma de los días de
                            todo lo que esa ruta puede completar, sin pausas. Una ruta cuyo foco elegido ya no
                            se puede completar (la economía atada al otro lado político) no existe.
  comparar()                rutas de hoy (sin 45_arboles.yaml) contra las del rediseño, potencia por potencia.
  vista(tag, png)           el árbol dibujado como lo arma el juego (casilleros y líneas), para revisar la forma.

Uso:  python3 -m tools.arboles            (tabla de duraciones)
      python3 -m tools.arboles EFE x.png  (vista previa)
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
POTENCIAS = ["EFE", "ASC", "FCU", "HSN", "NAS", "SHD", "APF", "NRE"]


def _spec(con_rediseno: bool = True):
    sys.path.insert(0, str(REPO))
    from tools.gen import specload
    if con_rediseno:
        return specload.load(REPO / "spec")
    viejo = list(specload.OVERLAY_FILES)
    try:
        specload.OVERLAY_FILES[:] = [f for f in viejo if f != "45_arboles.yaml"]
        return specload.load(REPO / "spec")
    finally:
        specload.OVERLAY_FILES[:] = viejo


def focos(spec, tag: str) -> list[dict]:
    return [f for b in spec.raw["focus_trees"]["trees"][tag]["branches"] for f in b.get("focuses") or []]


def _completables(fs: list[dict], fuera: set[str]) -> set[str]:
    hechos: set[str] = set()
    cambio = True
    while cambio:
        cambio = False
        for f in fs:
            fid = f["id"]
            if fid in hechos or fid in fuera:
                continue
            todos = f.get("prerequisites") or []
            alguno = f.get("prerequisites_any") or []
            if all(p in hechos for p in todos) and (not alguno or any(p in hechos for p in alguno)):
                hechos.add(fid)
                cambio = True
    return hechos


def rutas(fs: list[dict]) -> dict[tuple[str, ...], int | None]:
    """{elecciones: días} (None si esa combinación ya no existe)."""
    pares = sorted({tuple(sorted((f["id"], o))) for f in fs for o in f.get("mutually_exclusive") or []})
    dias = {f["id"]: int(f.get("days", 70)) for f in fs}
    out: dict[tuple[str, ...], int | None] = {}
    for eleccion in itertools.product(*pares):
        fuera = {x for par, e in zip(pares, eleccion) for x in par if x != e}
        hechos = _completables(fs, fuera)
        out[tuple(eleccion)] = sum(dias[f] for f in hechos) if all(e in hechos for e in eleccion) else None
    return out


def comparar() -> dict[str, list[tuple[tuple[str, ...], int, int | None]]]:
    antes, despues = _spec(False), _spec(True)
    res = {}
    for tag in POTENCIAS:
        a, d = rutas(focos(antes, tag)), rutas(focos(despues, tag))
        res[tag] = [(k, a[k], d.get(k)) for k in a]
    return res


def vista(tag: str, png: Path) -> None:
    from PIL import Image, ImageDraw
    from tools.gen.emitters.focus_trees import _depths, _layout, _layout_forma
    spec = _spec(True)
    tree = spec.raw["focus_trees"]["trees"][tag]
    fl = [(b["id"], f) for b in tree["branches"] for f in b.get("focuses") or []]
    by_id = {f["id"]: f for _, f in fl}
    depth = _depths(by_id)
    pos = _layout_forma(fl, depth, tree["forma"], print) if tree.get("forma") else _layout(fl, depth)
    cx, cy = 46, 70
    w = (max(x for x, _ in pos.values()) + 3) * cx
    h = (max(y for _, y in pos.values()) + 2) * cy
    im = Image.new("RGB", (w, h), (24, 26, 30))
    d = ImageDraw.Draw(im)
    centro = {fid: (x * cx + cx, y * cy + cy // 2 + 10) for fid, (x, y) in pos.items()}
    colores = {}
    paleta = [(214, 120, 90), (120, 180, 220), (150, 210, 120), (230, 200, 90), (190, 140, 220), (230, 150, 180),
              (120, 210, 200), (200, 200, 200), (240, 170, 90), (160, 160, 240), (200, 120, 120), (140, 200, 160)]
    for b, _f in fl:
        colores.setdefault(b, paleta[len(colores) % len(paleta)])
    for _b, f in fl:
        for p in list(f.get("prerequisites") or []):
            d.line([centro[p], centro[f["id"]]], fill=(200, 200, 200), width=2)
        for p in list(f.get("prerequisites_any") or []):
            d.line([centro[p], centro[f["id"]]], fill=(120, 120, 120), width=1)
    for b, f in fl:
        x, y = centro[f["id"]]
        d.rectangle((x - 20, y - 16, x + 20, y + 16), fill=colores[b], outline=(0, 0, 0))
        d.text((x - 19, y - 6), f["id"].split("_", 1)[1][:7], fill=(0, 0, 0))
    im.save(png)


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        vista(sys.argv[1], Path(sys.argv[2]))
    else:
        for tag, filas in comparar().items():
            for k, a, d in filas:
                cambio = "desaparece" if d is None else f"{(d - a) / a * 100:+.1f}%"
                print(f"{tag} {' / '.join(x.split('_', 1)[1] for x in k):60s} {a:5d} -> {d if d is not None else '-':>5} {cambio}")
