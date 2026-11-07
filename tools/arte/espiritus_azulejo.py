"""Los espíritus nacionales como azulejos de cerámica esmaltada (2026-11-07).

Pedido: "la cerámica me gustó más que todos. Hacé el pedido sin incluir los que ya me
pasaste" -> todos los espíritus (ideas de 05_ideas y modificadores dinámicos con imagen),
menos los 22 de la prueba (espiritus_prueba.py), como azulejos con el esmalte de su nación.

Escribe arte/pedidos/0_ESPIRITUS_AZULEJO.txt. Al volver, la imagen tiene el id del espíritu
y `arte importar` la pone en assets/<TAG>/ideas/ (reemplaza la vieja); `arte azulejos
<carpeta>` anota los que llegaron en arte/espiritus_azulejo_llegados.txt para no volver a
pedirlos (las imágenes viejas ya existían, así que el archivo es lo que dice qué se rehizo).
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.arte import espiritus_prueba as prueba

REPO = Path(__file__).resolve().parents[2]
LLEGADOS = REPO / "arte" / "espiritus_azulejo_llegados.txt"

ESTILO = prueba.AZULEJO

# el esmalte de cada nación (las de la prueba, más las que no estaban)
ESMALTE = {tag: esmalte for tag, (_tinta, esmalte) in prueba.MATERIALES.items()}
ESMALTE.update({
    "MEGANATIONS": "neutral glazes that belong to no nation: steel grey, graphite and muted ochre on cream, "
                   "one small accent of teal",
    "ZWB": ESMALTE["ZWE"], "ZWI": ESMALTE["ZWE"], "ZWM": ESMALTE["ZWE"], "ZAN": ESMALTE["ZWE"],
    "ZST": ESMALTE["ZWE"],
    "ZSG": "deep jungle green, moss and amber glazes, a tile from a forest sanctuary",
    "PTA": "white, pale ice blue and slate grey glazes with one touch of imperial green",
    "YYG": "red-earth terracotta, forest green and river blue glazes with a touch of gold lustre",
    "ZAS": "deep navy and weathered teal glazes with brass-coloured outlines, a sailor's tile",
    "JUNTA": "black and bone-white glazes with one eclipse-orange ring",
})


def _llegados() -> set[str]:
    if not LLEGADOS.exists():
        return set()
    return {l.strip() for l in LLEGADOS.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def _uno(texto: str) -> str:
    return " ".join(str(texto or "").split())


def _que(item: dict) -> tuple[str, str]:
    """(nombre, qué dibujar) a partir de la descripción del catálogo."""
    d = item["description"]
    m = re.match(r"WHAT: icon of the national spirit '(.+?)'\. EXACT SUBJECT: (.+?)\. COMPOSITION", d)
    if m:
        return m.group(1), f"EXACT SUBJECT: {m.group(2)}."
    nombre, _, texto = d.partition(":")
    partes = re.split(r"(?<=[.!?])\s+", _uno(texto))
    resumen = " ".join(partes[:2]).strip()
    # lo de "Removed by the focus ..." es regla de juego, no algo que dibujar
    resumen = re.sub(r"\s*Removed by .*$", "", resumen).strip()
    return nombre.strip(), f"what it is about: {resumen or nombre.strip()}"


def items(todos: bool = False) -> list[dict]:
    from tools.arte import arte
    # 2026-11-07: los de la prueba están en la lista de llegados; los que se rehacen (colores
    # corregidos) se sacan de esa lista y vuelven a pedirse
    excluir: set[str] = set()
    hechos = set() if todos else _llegados()
    out = []
    for i in arte.catalog():
        if i["type"] != "national_spirit_icon" or i["id"] in excluir or i["id"] in hechos:
            continue
        nombre, que = _que(i)
        out.append({"tag": i["tag"], "id": i["id"], "nombre": nombre, "que": que,
                    "esmalte": ESMALTE.get(i["tag"], ESMALTE["MEGANATIONS"])})
    return out


def pedido(i: dict) -> str:
    return "\n".join([
        "ASSET_REQUEST",
        "type: national_spirit_icon",
        f"id: {i['id']}",
        f"filename: {i['id']}.png",
        "size: 64x64 (o más grande con la misma proporción, cuadrada)",
        f"style: {ESTILO}",
        f"material: GLAZE: {i['esmalte']}",
        f"description: WHAT: national spirit '{i['nombre']}'; {i['que']} Reduce it to ONE simple, bold motif "
        f"for the tile.",
        "transparent_background: true",
        "",
    ])


def escribir(salida: Path) -> str:
    todos = items()
    por_tag: dict[str, int] = {}
    for i in todos:
        por_tag[i["tag"]] = por_tag.get(i["tag"], 0) + 1
    cabeza = [
        f"# {len(todos)} pedidos - los ESPÍRITUS NACIONALES como AZULEJOS de cerámica esmaltada (2026-11-07)",
        "# Sin los 22 de la prueba (0_ESPIRITUS_PRUEBA.txt). Cada uno con el esmalte de su nación (material).",
        "# Al volver reemplazan a los espíritus viejos. Sin imagen de referencia.",
        "# Consejo: un chat nuevo cada 15 pedidos; si deja de parecer un azulejo de verdad, pegale de nuevo",
        "# el `style` y el `material`.",
        "# Por nación: " + ", ".join(f"{t} {n}" for t, n in sorted(por_tag.items())),
        "",
    ]
    path = salida / "0_ESPIRITUS_AZULEJO.txt"
    path.write_text("\n".join(cabeza) + "\n" + "\n".join(pedido(i) for i in todos), encoding="utf-8")
    # 2026-11-07: los de la prueba que se rehacen con los colores corregidos, también aparte
    de_prueba = {ident for ident, _n, _q in prueba.ESPIRITUS}
    otra = [i for i in todos if i["id"] in de_prueba]
    extra = salida / "0_ESPIRITUS_AZULEJO_REHACER.txt"
    if otra:
        extra.write_text(
            f"# {len(otra)} pedidos - azulejos de la prueba que se rehacen con el color de su nación corregido\n"
            "# (también están dentro de 0_ESPIRITUS_AZULEJO.txt; este archivo es por si ese ya está corriendo)\n\n"
            + "\n".join(pedido(i) for i in otra), encoding="utf-8")
    elif extra.exists():
        extra.unlink()
    return f"{path.name}: {len(todos)}" + (f" ({extra.name}: {len(otra)})" if otra else "")


def anotar_llegados(carpeta: str) -> list[str]:
    from tools.fabrica import control
    todos = {i["id"] for i in items(todos=True)} | {ident for ident, _n, _q in prueba.ESPIRITUS}
    previos = _llegados()
    buenos = control.mejores_por_nombre(p for p in Path(carpeta).rglob("*.png") if "revisar" not in p.parts)
    nuevos = {s for s in buenos if s in todos} - previos
    cabeza = "# Espíritus que ya llegaron como azulejo (tools/arte/espiritus_azulejo.py no los vuelve a pedir)."
    LLEGADOS.write_text(cabeza + "\n" + "\n".join(sorted(previos | nuevos)) + "\n", encoding="utf-8")
    return [f"azulejos: {len(nuevos)} espíritus nuevos anotados ({len(previos | nuevos)} de {len(todos)})"]
