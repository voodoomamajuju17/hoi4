"""python3 -m tools.simulador [--corridas N] [--supuestos ARCHIVO] [--salida ARCHIVO]

Tira los dados de la IA muchas veces con los números del spec y escribe un
informe: qué rama política elige cada potencia, cuándo se termina el Rearme
Secreto, cuándo muere Aurelio IV y quién hereda, y cuánto se repite la crisis
del siglo. Mismo spec + mismos supuestos + misma semilla = mismo informe.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..gen import specload
from . import simular
from .informe import informe
from .motor import SupuestoFaltante


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m tools.simulador")
    ap.add_argument("--spec", default="spec")
    ap.add_argument("--supuestos", default=None)
    ap.add_argument("--corridas", type=int, default=None)
    ap.add_argument("--salida", default="SIMULADOR_IA.md")
    args = ap.parse_args(argv)

    raw = specload.load(args.spec).raw
    sup = simular.cargar_supuestos(args.supuestos)
    if args.corridas:
        sup["corridas"] = args.corridas
    try:
        focos = simular.simular_focos(raw, sup)
        mundo = simular.simular_mundo(raw, sup)
        crisis = simular.simular_crisis(raw, sup)
    except SupuestoFaltante as exc:
        print(f"simulador: {exc}", file=sys.stderr)
        return 2
    texto = informe(raw, sup, focos, mundo, crisis)
    Path(args.salida).write_text(texto + "\n", encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
