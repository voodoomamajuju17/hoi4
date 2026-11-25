"""Auditoría de los modelos 3D nuevos (2026-11-24: "chequeá cada modelado nuevo 3D, que no haya posibilidad de que
den problemas").

    python -m tools.arte.auditar_modelos [carpeta ...]

Por cada pieza (una carpeta con gfx/): que cada .mesh se lea; que el sombreador sea uno del juego; que las tres
texturas que nombra el material existan junto a la malla y sean DDS que el juego lee (DXT1/DXT3/DXT5 o sin
comprimir, nunca DX10/BC7, lados potencia de 2); que el .gfx apunte a la malla que existe y que cada
`meshsettings` nombre un objeto de la malla; que cada animación del .gfx esté en un .asset con su .anim, que el
.anim mueva huesos que la malla tiene y que no pasen de 50 huesos; que las entidades usen mallas definidas; vértices
por objeto menos de 65.536. Sale con 1 si encuentra un error (las advertencias no cortan).
"""

from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tools.gen import pdxbin  # noqa: E402

# los del juego 1.20 (gfx/entities/*.gfx): PdxMeshAdvanced, PdxMeshAdvancedSnow (nieve en invierno), PdxMeshAdvancedAnim
SOMBREADORES = {"PdxMeshAdvanced", "PdxMeshAdvancedSnow", "PdxMeshAdvancedAnim", "PdxMeshStandard",
                "PdxMeshStandard_NoFoW_NoTI", "PdxMeshAlphaBlend"}
FOURCC_OK = {b"DXT1", b"DXT3", b"DXT5", b"\0\0\0\0"}


def dds(path: Path) -> list[str]:
    b = path.read_bytes()[:148]
    if b[:4] != b"DDS ":
        return [f"{path.name}: no es un DDS"]
    alto, ancho = struct.unpack("<II", b[12:20])
    fourcc = b[84:88]
    out = []
    if fourcc == b"DX10":
        out.append(f"{path.name}: DDS con cabecera DX10 (BC7/BC6): el juego no la lee")
    elif fourcc not in FOURCC_OK:
        out.append(f"{path.name}: compresión {fourcc!r} desconocida para el juego")
    for lado in (alto, ancho):
        if lado & (lado - 1):
            out.append(f"{path.name}: {ancho}x{alto} no es potencia de 2")
            break
    return out


def _s(v) -> str:
    x = v[1][0] if isinstance(v, tuple) else v
    return (x.decode("latin-1") if isinstance(x, bytes) else str(x)).rstrip("\0")


def auditar(pieza: Path) -> tuple[list[str], list[str]]:
    err, adv = [], []
    gfx_dir = pieza / "gfx"
    mallas_definidas: dict[str, Path] = {}
    textos = [f.read_text(encoding="utf-8-sig", errors="replace") for f in gfx_dir.rglob("*") if f.suffix in (".gfx", ".asset")]
    todo = "\n".join(textos)
    # mallas del .gfx
    for m in re.finditer(r'pdxmesh\s*=\s*\{(.*?)\n\s*\}\s*\n', todo, re.S):
        cuerpo = m.group(1)
        n = re.search(r'name\s*=\s*"([^"]+)"', cuerpo)
        f = re.search(r'file\s*=\s*"([^"]+)"', cuerpo)
        if not (n and f):
            continue
        ruta = pieza / f.group(1)
        mallas_definidas[n.group(1)] = ruta
        if not ruta.is_file():
            err.append(f"{n.group(1)}: el .gfx apunta a {f.group(1)}, que no está")
            continue
        try:
            raiz = pdxbin.leer(ruta.read_bytes())
        except Exception as e:  # noqa: BLE001
            err.append(f"{ruta.name}: no se lee ({e})")
            continue
        objetos = {h.nombre for o in raiz.hijos if o.nombre == "object" for h in o.hijos}
        for ms in re.findall(r'meshsettings\s*=\s*\{[^}]*name\s*=\s*"([^"]+)"', cuerpo):
            if ms not in objetos:
                err.append(f"{ruta.name}: meshsettings '{ms}' no es un objeto de la malla ({', '.join(sorted(objetos))})")
        huesos: set[str] = set()
        for nodo in raiz.todos():
            if nodo.nombre == "material":
                sh = _s(nodo.props.get("shader", ("s", [b""])))
                if sh not in SOMBREADORES:
                    err.append(f"{ruta.name}: sombreador '{sh}' desconocido")
                for k in ("diff", "n", "spec"):
                    if k in nodo.props:
                        tex = ruta.parent / _s(nodo.props[k])
                        if not tex.is_file():
                            err.append(f"{ruta.name}: falta la textura {tex.name}")
                        else:
                            err += dds(tex)
                    else:
                        adv.append(f"{ruta.name}: el material no nombra textura '{k}'")
            if nodo.nombre == "mesh" and "p" in nodo.props:
                nv = len(nodo.props["p"][1]) // 3
                if nv >= 65536:
                    err.append(f"{ruta.name}: {nv} vértices en un objeto (máximo 65.535)")
            if nodo.nombre == "skeleton":
                huesos |= {h.nombre for h in nodo.hijos}
        if len(huesos) > 50:
            adv.append(f"{ruta.name}: {len(huesos)} huesos (el armado los recorta a 50)")
        # animaciones
        for aid, tipo in re.findall(r'animation\s*=\s*\{\s*id\s*=\s*"([^"]+)"\s*type\s*=\s*"([^"]+)"', cuerpo):
            a = re.search(r'name\s*=\s*"' + re.escape(tipo) + r'"\s*file\s*=\s*"([^"]+)"', todo)
            if not a:
                err.append(f"{n.group(1)}: la animación '{tipo}' no está en ningún .asset")
                continue
            anim = next((p for p in [ruta.parent / Path(a.group(1)).name, pieza / a.group(1)] if p.is_file()), None)
            if anim is None:
                err.append(f"{n.group(1)}: falta el archivo {a.group(1)}")
                continue
            if not huesos:
                err.append(f"{n.group(1)}: tiene animación '{aid}' pero la malla no tiene esqueleto")
                continue
            try:
                ar = pdxbin.leer(anim.read_bytes())
                info = next(x for x in ar.todos() if x.nombre == "info")
                movidos = {j.nombre for j in info.hijos}
                if not movidos & huesos:
                    err.append(f"{anim.name}: no mueve ningún hueso de la malla")
            except Exception as e:  # noqa: BLE001
                err.append(f"{anim.name}: no se lee ({e})")
    # entidades
    for ent in re.finditer(r'entity\s*=\s*\{(.*?)\n\}', todo, re.S):
        pm = re.search(r'pdxmesh\s*=\s*"([^"]+)"', ent.group(1))
        if pm and pm.group(1) not in mallas_definidas:
            err.append(f"la entidad usa la malla '{pm.group(1)}', que ningún .gfx de la pieza define")
        for st in re.findall(r'animation\s*=\s*"([^"]+)"', ent.group(1)):
            if not re.search(r'id\s*=\s*"' + re.escape(st) + '"', todo):
                err.append(f"un estado pide la animación '{st}', que la malla no tiene")
    if not mallas_definidas:
        err.append("sin mallas definidas en un .gfx")
    return err, adv


def main(argv: list[str]) -> int:
    carpetas = [Path(a) for a in argv] or (
        sorted((REPO / "assets" / "modelos").glob("*_tren_*")) + sorted((REPO / "assets" / "mundo_2100").glob("*/*")))
    total = 0
    for c in carpetas:
        if not (c / "gfx").is_dir():
            continue
        err, adv = auditar(c)
        total += len(err)
        estado = "OK" if not err else "ERROR"
        print(f"{estado:5s} {c.relative_to(REPO) if c.is_relative_to(REPO) else c}" + (f"  ({len(adv)} avisos)" if adv else ""))
        for e in err:
            print(f"      X {e}")
        for a in adv:
            print(f"      ~ {a}")
    print(f"\n{len(carpetas)} piezas, {total} errores")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
