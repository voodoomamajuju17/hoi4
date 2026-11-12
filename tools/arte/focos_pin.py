"""Pedidos de íconos de foco en estilo "pin" (2026-11-05).

Pedido: "rehacé los pedidos faltantes de focos para encajar con el nuevo estilo...
tienen que parecer fotos de pines posta. Materiales verdaderos... sencillo, poco
elemento y bien claro. Como los del EFE."

Lee arte/focos_pin.yaml (estilo común y material por nación y rama) y arma un
pedido por foco de cada nación que todavía no está en el estilo nuevo. El ícono
viejo va como imagen de referencia del motivo (arte/referencias_focos/<id>.png):
"el mismo motivo, reducido a un emblema simple, hecho pin". Al volver, la imagen
tiene el mismo id que el foco y `arte importar` la pone en su lugar.

Lo llama tools/arte/arte.py pedidos (archivos 20_focos_pin_<TAG>.txt).
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
YAML = REPO / "arte" / "focos_pin.yaml"
REFS = REPO / "arte" / "referencias_focos"
CON_REFERENCIA = False   # 2026-11-06: sin referencia (ver _pedido)


def _uno(texto: str) -> str:
    return " ".join(str(texto or "").split())


def _corto(texto: str, maximo: int = 320) -> str:
    """Las dos primeras oraciones de la descripción, sin pasar de `maximo` letras."""
    import re
    t = _uno(texto)
    partes = re.split(r"(?<=[.!?])\s+", t)
    t = " ".join(partes[:2])
    if len(t) > maximo:
        t = t[:maximo].rsplit(" ", 1)[0] + "..."
    return t if t.endswith((".", "!", "?", "...")) else t + "."


def items() -> list[dict]:
    """Un pedido por foco de las naciones que faltan, con su material."""
    import yaml
    from tools.arte import arte
    if not YAML.exists():
        return []
    cfg = yaml.safe_load(YAML.read_text(encoding="utf-8")) or {}
    mats = cfg.get("materiales") or {}
    hechas = set(cfg.get("hechas") or [])
    rehacer = set(cfg.get("rehacer") or [])
    llegados_path = REPO / "arte" / "focos_pin_llegados.txt"
    llegados = {l.strip() for l in llegados_path.read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")} if llegados_path.exists() else set()
    looks = {}
    desc_path = REPO / "arte" / "iconos_descripciones.yaml"
    if desc_path.exists():
        looks = (yaml.safe_load(desc_path.read_text(encoding="utf-8")) or {}).get("iconos") or {}
    out = []
    # 2026-11-12: los árboles con todo lo agregado después (las ramas nuevas de add_branches, como
    # Quedarse Luditas de Albión, no estaban en 07_focus_trees.yaml y nunca se pidieron)
    from tools.gen.specload import Spec
    arboles = Spec(REPO / "spec").raw["focus_trees"]["trees"]
    for tag, tree in arboles.items():
        if tag in hechas or tag not in mats or not isinstance(tree, dict) or "branches" not in tree:
            continue
        m = mats[tag]
        for rama in tree["branches"]:
            material = _uno((m.get("ramas") or {}).get(rama.get("id"), m["base"]))
            for f in rama["focuses"]:
                if f["id"] in llegados and tag not in rehacer:
                    continue
                propio = (m.get("focos") or {}).get(f["id"])
                nombre = f["name"]["english"]
                if f["id"] in looks:
                    que = f"the emblem shows: {_uno(looks[f['id']]['dibujo']).rstrip('.')}."
                else:
                    que = f"what the focus is about: {_corto(f['desc']['english'])}"
                ref = REPO / "assets" / tag / "goals" / f"{f['id']}.dds"
                out.append({"tag": tag, "id": f["id"], "rama": rama.get("id"), "material": _uno(propio) if propio else material,
                            "descripcion": f"WHAT: national focus '{nombre}' ({_uno(f['name'].get('spanish', ''))}); "
                                           f"{que} Reduce it to ONE simple, bold emblem.",
                            "origen": ref if ref.exists() else None})
    return out


def _pedido(i: dict, estilo: str) -> str:
    lineas = [
        "ASSET_REQUEST",
        "type: national_focus_icon",
        f"id: {i['id']}",
        f"filename: {i['id']}.png",
        "size: 95x85 (o más grande con la misma proporción)",
        f"style: {estilo}",
        f"material: {i['material']}",
        f"description: {i['descripcion']}",
    ]
    # 2026-11-06 ("no los hice con referencia"): los pines que salieron bien se hicieron sin la
    # imagen vieja; el pedido va solo con la descripción y el material
    if i.get("referencia") and CON_REFERENCIA:
        lineas.append(f"reference_image: {i['referencia']} (adjuntar: es el ícono viejo; tomar solo el motivo, "
                      f"no su estilo ni su fondo)")
    lineas += ["transparent_background: true", ""]
    return "\n".join(lineas)


def escribir(salida: Path) -> tuple[list[str], list[str]]:
    """Escribe 20_focos_pin_<TAG>.txt en `salida` y las referencias en arte/referencias_focos.
    Devuelve (resumen, referencias relativas a arte/)."""
    import yaml
    from PIL import Image
    todos = items()
    if not todos:
        return [], []
    estilo = _uno((yaml.safe_load(YAML.read_text(encoding="utf-8")) or {}).get("estilo"))
    refs = []
    for i in todos:
        if i["origen"] is None or not CON_REFERENCIA:
            continue
        REFS.mkdir(parents=True, exist_ok=True)
        destino = REFS / f"{i['id']}.png"
        if not destino.exists():
            Image.open(i["origen"]).convert("RGBA").save(destino, optimize=True)
        i["referencia"] = f"referencias_focos/{destino.name}"
        refs.append(i["referencia"])
    por_tag: dict[str, list[dict]] = {}
    for i in todos:
        por_tag.setdefault(i["tag"], []).append(i)
    resumen = []
    for tag, grupo in por_tag.items():
        path = salida / f"20_focos_pin_{tag}.txt"
        materiales = sorted({i["material"] for i in grupo})
        cabeza = [f"# {len(grupo)} pedidos - íconos de foco en estilo PIN - {tag}",
                  *(["# SE REHACEN TODOS (2026-11-07): los anteriores estaban bien pero no excelentes.",
                     "# Materiales nuevos de joyería japonesa; cuidá el brillo del metal y del esmalte."]
                    if tag in (yaml.safe_load(YAML.read_text(encoding="utf-8")) or {}).get("rehacer", []) else []),
                  "# Consejo: un chat nuevo cada 15 pedidos más o menos. Si empieza a hacer monedas",
                  "# redondas llenas de cosas, pegale de nuevo el `style` y el `material` del pedido.",
                  "# Como los del Imperio Ecofascista: foto de un pin de verdad, un solo emblema simple.",
                  "# Cada pedido trae su material (cambia según la rama del árbol). Sin imagen de referencia.",
                  f"# Materiales de esta nación: {len(materiales)}", ""]
        path.write_text("\n".join(cabeza) + "\n" + "\n".join(_pedido(i, estilo) for i in grupo), encoding="utf-8")
        resumen.append(f"{path.name}: {len(grupo)}")
    return resumen, refs


def anotar_llegados(carpeta: str) -> list[str]:
    """Anota en arte/focos_pin_llegados.txt los focos de una carpeta recién importada
    (2026-11-06: a mano se perdía una línea) y borra sus referencias, que ya no hacen falta."""
    path = REPO / "arte" / "focos_pin_llegados.txt"
    cabeza = "# Focos que ya llegaron en estilo pin (2026-11-05); tools/arte/focos_pin.py no los vuelve a pedir."
    previos = {l.strip() for l in path.read_text(encoding="utf-8").splitlines()
               if l.strip() and not l.startswith("#")} if path.exists() else set()
    focos = {i["id"] for i in items()} | previos
    from tools.fabrica import control
    buenos = control.mejores_por_nombre(p for p in Path(carpeta).rglob("*.png") if "revisar" not in p.parts)
    nuevos = {s for s in buenos if s in focos} - previos   # los rotos no cuentan como llegados
    path.write_text(cabeza + "\n" + "\n".join(sorted(previos | nuevos)) + "\n", encoding="utf-8")
    for ident in nuevos:
        (REFS / f"{ident}.png").unlink(missing_ok=True)
    return [f"pines: {len(nuevos)} focos nuevos anotados ({len(previos | nuevos)} en total)"]
