"""Pedidos de arte del panel del recurso propio de cada nación (2026-11-15).

Lee arte/paneles_recurso.yaml y escribe arte/pedidos_fijos/33_paneles_recurso.txt.
Las piezas llegan a assets/ui/paneles/<panel>/<pieza>.png (importar con tools/arte/arte.py).

Uso:  python3 -m tools.arte.paneles
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "arte" / "paneles_recurso.yaml"
SALIDA = REPO / "arte" / "pedidos_fijos" / "33_paneles_recurso.txt"
DESTINO = REPO / "assets" / "ui" / "paneles"
TAMANOS = {"fondo": (1440, 1600), "medidor": (1024, 1024), "medidor_lleno": (1024, 1024),
           "aguja": (1024, 1024), "boton": (1024, 160)}
QUE = {
    "fondo": "the whole panel frame, OPAQUE, fills the canvas edge to edge. Keep these zones plain and calm "
             "(no objects on them, the game draws there): title band y 0-160; gauge zone x 60-700 y 200-840; "
             "text zone x 760-1380 y 200-840; actions zone x 60-1380 y 900-1520",
    "medidor": "the main gauge of the panel in its EMPTY / OFF state, centred, transparent background",
    "medidor_lleno": "EXACTLY the same object, same position, size and framing pixel for pixel as the "
                     "'medidor' image, but FULL / fully lit; transparent background",
    "aguja": "only the needle, transparent background, pointing straight UP, its axle exactly at the canvas centre",
    "boton": "an empty button plate for an action, centred, transparent background, about 6:1",
}


def _linea(t: str) -> str:
    return " ".join(str(t).split())


def piezas() -> list[dict]:
    import yaml
    cfg = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    out = []
    for panel, p in cfg["paneles"].items():
        for pieza in ("fondo", "medidor", "medidor_lleno", "aguja", "boton"):
            if pieza not in p:
                continue
            out.append({"panel": panel, "pieza": pieza, "id": f"panel_{panel}_{pieza}", "size": TAMANOS[pieza],
                        "transparent": pieza != "fondo", "nombre": p["nombre"], "recurso": p["recurso"],
                        "texto": p[pieza], "comun": cfg["comun"],
                        "dest": DESTINO / panel / f"{pieza}.png"})
    return out


def pedidos() -> int:
    ps = [p for p in piezas() if not p["dest"].exists()]
    lineas = [f"# {len(ps)} PEDIDOS - PANELES DEL RECURSO PROPIO (2026-11-15)",
              "# Una ventana propia por nación (como la Ficha del Líder) con su recurso único: carcasa ilustrada,",
              "# el medidor grande (vacío y lleno, mismo encuadre) y la placa de los botones de acción.",
              "# Cada nación con su propio material y su propio instrumento; nada genérico.",
              "# Mandámelos con el nombre de 'filename'.", ""]
    for p in ps:
        w, h = p["size"]
        lineas += ["ASSET_REQUEST", "type: resource_panel", f"id: {p['id']}", f"filename: {p['id']}.png",
                   f"size: {w}x{h}", f"style: {_linea(p['comun'])}",
                   f"description: Panel \"{p['nombre']}\" ({p['recurso']}). WHAT: {QUE[p['pieza']]}. "
                   f"SUBJECT: {_linea(p['texto'])}",
                   f"transparent_background: {'true' if p['transparent'] else 'false'}", ""]
    SALIDA.write_text("\n".join(lineas), encoding="utf-8")
    return len(ps)


if __name__ == "__main__":
    print(f"paneles: {pedidos()} pedidos en {SALIDA.relative_to(REPO)}")
