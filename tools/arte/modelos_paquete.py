"""Modelos 3D que llegan en el formato del juego (2026-11-21, La Red 01 a 04).

El paquete trae gfx/models/units/<pieza>/ (malla, .anim, DDS, PNG sueltos, .blend, vista previa) y
gfx/entities/<pieza>.gfx (la malla en objectTypes) + <pieza>.asset (la entidad). Esto lo pasa al
formato de assets/modelos/<pieza>/ que usa el armado (tools/gen/emitters/modelos.py): un solo
gfx/entities/<pieza>.asset con animaciones, malla y entidad, para que el armado arregle huesos y
giro, y escale. Los PNG de color, metal, rugosidad y normal no van (el juego usa los DDS).

    python3 -m tools.arte.modelos_paquete <carpeta del zip descomprimido> [fecha]
"""
import datetime
import pathlib
import re
import shutil
import sys

from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[2]
src = pathlib.Path(sys.argv[1])
dst = REPO / "assets" / "modelos"
fecha = sys.argv[2] if len(sys.argv) > 2 else datetime.date.today().isoformat()
hechas = []
for carpeta in sorted((src / "gfx/models/units").iterdir()):
    pieza = carpeta.name                      # ZRD_infanteria
    if not re.match(r"^[A-Z]{3}_", pieza):
        continue
    out = dst / pieza
    unidades = out / "gfx/models/units" / pieza
    if out.exists():
        shutil.rmtree(out)
    unidades.mkdir(parents=True)
    anims = sorted(carpeta.glob("*.anim"))
    for f in [carpeta / f"{pieza}.mesh", *anims,
              carpeta / f"{pieza}_diffuse.dds", carpeta / f"{pieza}_normal.dds", carpeta / f"{pieza}_specular.dds"]:
        shutil.copy2(f, unidades / f.name)
    shutil.copy2(carpeta / f"{pieza}.blend", out / f"{pieza}.blend")
    vista = Image.open(carpeta / f"{pieza}_preview.png").convert("RGB")
    vista.thumbnail((800, 800))
    vista.save(out / "vista.png", optimize=True)
    # la entidad tal como vino; la malla y las animaciones con la ruta desde la raíz
    ent_txt = (src / "gfx/entities" / f"{pieza}.asset").read_text(encoding="utf-8-sig")
    gfx_txt = (src / "gfx/entities" / f"{pieza}.gfx").read_text(encoding="utf-8-sig")
    malla = re.search(r'name\s*=\s*"([^"]+)"', gfx_txt).group(1)
    ids = re.findall(r'animation\s*=\s*\{\s*id\s*=\s*"(\w+)"\s*type\s*=\s*"(\w+)"\s*\}', gfx_txt)
    nombres = {a.stem.removeprefix(pieza + "_"): a.name for a in anims}
    partes = [f"# {fecha}: modelo animado {pieza} ({', '.join(nombres)})"]
    for clip, archivo in nombres.items():
        partes.append(f'animation = {{\n    name = "{pieza}_{clip}_animation"\n'
                      f'    file = "gfx/models/units/{pieza}/{archivo}"\n}}\n')
    lineas = [f'pdxmesh = {{\n    name = "{malla}"\n    file = "gfx/models/units/{pieza}/{pieza}.mesh"\n    scale = 1.0']
    for i, t in ids:
        assert t == f"{pieza}_{i}_animation", (pieza, i, t)
        lineas.append(f'    animation = {{ id = "{i}" type = "{t}" }}')
    lineas.append("}\n")
    partes.append("\n".join(lineas))
    partes.append(ent_txt.strip() + "\n")
    (out / "gfx/entities").mkdir(parents=True)
    (out / "gfx/entities" / f"{pieza}.asset").write_text("\n".join(partes), encoding="utf-8")
    hechas.append(pieza)
print("piezas:", ", ".join(hechas))
