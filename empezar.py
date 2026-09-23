#!/usr/bin/env python3
"""EMPEZAR AQUI.

Este script hace todo solo: busca tu Hearts of Iron IV, genera el mod, lo copia
a tu carpeta de mods, y escribe un reporte.txt para que me lo pases.

No necesitas saber Python ni git. Corrélo asi:

    Windows:  py empezar.py
    Mac/Linux: python3 empezar.py

Si algo falla, el error te dice exactamente que hacer. Nada de esto toca tu
instalacion de HOI4: solo la LEE.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent
REPORT = REPO / "reporte.txt"

_log_lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    _log_lines.append(text)


def titulo(text: str) -> None:
    say()
    say("=" * 68)
    say(f"  {text}")
    say("=" * 68)


def bien(text: str) -> None:
    say(f"  [OK] {text}")


def mal(text: str) -> None:
    say(f"  [X]  {text}")


def ojo(text: str) -> None:
    say(f"  [!]  {text}")


# ---------------------------------------------------------------------------
# Paso 1 — Python y dependencias
# ---------------------------------------------------------------------------


def paso_python() -> bool:
    titulo("PASO 1 de 5  —  Revisando Python")

    version = sys.version_info
    say(f"  Python {version.major}.{version.minor}.{version.micro}")
    if version < (3, 10):
        mal(f"Necesito Python 3.10 o mas nuevo. Tenes {version.major}.{version.minor}.")
        say()
        say("  QUE HACER: instala Python desde https://www.python.org/downloads/")
        say("  En Windows, marca la casilla 'Add Python to PATH' durante la instalacion.")
        return False
    bien("Version de Python suficiente")

    try:
        import yaml  # noqa: F401

        bien("PyYAML ya esta instalado")
        return True
    except ImportError:
        pass

    ojo("Falta PyYAML (la unica libreria que hace falta). Instalando...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "pyyaml"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        mal("No pude instalar PyYAML automaticamente.")
        say(f"  Detalle: {(exc.stderr or exc.stdout or '').strip()[:400]}")
        say()
        say("  QUE HACER: abri una terminal y corré:")
        say(f"    {sys.executable} -m pip install pyyaml")
        return False
    except FileNotFoundError:
        mal("No encontre pip en esta instalacion de Python.")
        say("  QUE HACER: instala Python desde python.org, que ya lo trae.")
        return False

    try:
        import yaml  # noqa: F401,F811

        bien("PyYAML instalado")
        return True
    except ImportError:
        mal("PyYAML se instalo pero no lo puedo importar. Reinicia la terminal y probá de nuevo.")
        return False


# ---------------------------------------------------------------------------
# Paso 2 — Encontrar HOI4
# ---------------------------------------------------------------------------


RUTA_GUARDADA = REPO / "ruta_del_juego.txt"


def _limpiar_ruta(texto: str) -> str:
    """Acepta la ruta como venga pegada: con comillas, espacios o apuntando al .exe."""
    ruta = texto.strip().strip('"').strip("'").strip()
    if ruta.lower().endswith(".exe"):
        ruta = str(Path(ruta).parent)
    return ruta


def paso_buscar_juego(ruta_manual: str | None) -> object | None:
    titulo("PASO 2 de 5  —  Buscando tu Hearts of Iron IV")

    sys.path.insert(0, str(REPO))
    from tools.gen import vanilla as vanilla_mod
    from tools.gen.errors import VanillaError

    # La ruta que ya funciono una vez queda guardada: no hay que pegarla de nuevo.
    if ruta_manual is None and RUTA_GUARDADA.exists():
        ruta_manual = RUTA_GUARDADA.read_text(encoding="utf-8").strip() or None

    juego = None
    try:
        juego = vanilla_mod.locate(_limpiar_ruta(ruta_manual) if ruta_manual else None)
    except VanillaError as exc:
        mal(str(exc))

    while juego is None:
        mal("No encontre el juego solo. Necesito que me digas donde esta.")
        say()
        say("  COMO SACAR LA RUTA:")
        say("    1. Abri Steam")
        say("    2. Click derecho sobre 'Hearts of Iron IV' en tu biblioteca")
        say("    3. Administrar  ->  Explorar archivos locales")
        say("    4. Se abre una carpeta. Click en la barra de direcciones de arriba,")
        say("       Ctrl+C para copiar")
        say("    5. Volve a esta ventana, click derecho (o Ctrl+V) para pegar, y Enter")
        say()
        say("  (Enter sin escribir nada para salir)")
        say()
        try:
            respuesta = input("  Pega la ruta aca: ")
        except EOFError:
            return None
        if not respuesta.strip():
            return None
        try:
            juego = vanilla_mod.locate(_limpiar_ruta(respuesta))
        except VanillaError as exc:
            say()
            mal(str(exc))
            say()

    try:
        RUTA_GUARDADA.write_text(str(juego.root), encoding="utf-8")
    except OSError:
        pass

    bien(f"Juego encontrado en: {juego.root}")

    try:
        version = juego.version()
        bien(f"Version del juego: {version}")
    except VanillaError:
        version = None
        ojo("No pude leer la version (no es grave, sigo igual)")

    dlc_dir = juego.root / "dlc"
    if dlc_dir.is_dir():
        dlcs = sorted(p.name for p in dlc_dir.iterdir() if p.is_dir())
        bien(f"DLCs instalados: {len(dlcs)}")
        for name in dlcs:
            say(f"         - {name}")
    else:
        ojo("No encontre carpeta dlc/")

    return juego


# ---------------------------------------------------------------------------
# Paso 3 — Generar
# ---------------------------------------------------------------------------


def paso_generar(juego) -> object | None:
    titulo("PASO 3 de 5  —  Generando el mod")

    from tools.gen.cli import build
    from tools.gen.errors import GenError

    say("  Leyendo spec/ y escribiendo build/ ...")
    say()
    try:
        ctx = build(REPO / "build", vanilla_path=str(juego.root), quiet=True)
    except GenError as exc:
        mal("El generador fallo.")
        say(f"\n{exc}\n")
        say("  QUE HACER: pasame este error tal cual y lo corrijo.")
        return None

    bien(f"{len(ctx.written)} archivos generados")
    bien(f"{ctx.loc.stats()} de localisation")
    bien(f"{len(ctx.spec.countries)} paises")

    for n in ctx.notes:
        bien(n)

    if ctx.warnings:
        say()
        say(f"  AVISOS ({len(ctx.warnings)}) — son esperados, no son errores:")
        for w in ctx.warnings:
            say(f"    ! {w}")

    if ctx.skipped:
        say()
        say(f"  NO GENERADO ({len(ctx.skipped)}) — falta decidir algo:")
        for s in ctx.skipped:
            marca = f" [{s.question}]" if s.question else ""
            say(f"    - {s.what}{marca}: {s.reason}")

    return ctx


# ---------------------------------------------------------------------------
# Paso 4 — Instalar
# ---------------------------------------------------------------------------


def carpeta_de_mods() -> Path | None:
    candidatas = [
        "~/Documents/Paradox Interactive/Hearts of Iron IV/mod",
        "~/Documentos/Paradox Interactive/Hearts of Iron IV/mod",
        "~/OneDrive/Documents/Paradox Interactive/Hearts of Iron IV/mod",
        "~/OneDrive/Documentos/Paradox Interactive/Hearts of Iron IV/mod",
        "~/.local/share/Paradox Interactive/Hearts of Iron IV/mod",
    ]
    for raw in candidatas:
        path = Path(os.path.expanduser(raw))
        if path.is_dir() or path.parent.is_dir():
            return path
    return None


def paso_instalar(ctx) -> bool:
    titulo("PASO 4 de 5  —  Instalando el mod")

    destino = carpeta_de_mods()
    if destino is None:
        mal("No encontre tu carpeta de mods de HOI4.")
        say()
        say("  QUE HACER: abri el juego una vez y cerralo. Eso la crea sola.")
        say("  Deberia estar en: Documentos/Paradox Interactive/Hearts of Iron IV/mod")
        return False

    carpeta = ctx.spec.mod_folder
    origen_mod = REPO / "build" / carpeta
    origen_desc = REPO / "build" / f"{carpeta}.mod"

    try:
        destino.mkdir(parents=True, exist_ok=True)
        final = destino / carpeta
        if final.exists():
            shutil.rmtree(final)
        shutil.copytree(origen_mod, final)
        shutil.copy2(origen_desc, destino / f"{carpeta}.mod")
    except OSError as exc:
        mal(f"No pude copiar: {exc}")
        say()
        say("  QUE HACER: copia a mano estas dos cosas:")
        say(f"    {origen_mod}")
        say(f"    {origen_desc}")
        say(f"  dentro de: {destino}")
        return False

    bien(f"Instalado en: {final}")
    return True


# ---------------------------------------------------------------------------
# Paso 5 — Reporte
# ---------------------------------------------------------------------------


def paso_reporte(juego, ctx) -> None:
    titulo("PASO 5 de 5  —  Escribiendo reporte.txt")

    extra: list[str] = []
    extra.append("")
    extra.append("-" * 68)
    extra.append("DATOS DEL SISTEMA")
    extra.append("-" * 68)
    extra.append(f"Fecha:            {datetime.now():%Y-%m-%d %H:%M}")
    extra.append(f"Sistema:          {platform.system()} {platform.release()}")
    extra.append(f"Python:           {sys.version.split()[0]}")

    if juego is not None:
        extra.append(f"Ruta del juego:   {juego.root}")
        try:
            extra.append(f"Version:          {juego.version()}")
        except Exception:  # noqa: BLE001
            extra.append("Version:          (no se pudo leer)")

        # Lo mas util para mi: los nombres reales de los grupos de ideologia de
        # TU version. Si no coinciden con lo que asume el spec, el merge falla y
        # esto lo muestra sin que tengas que abrir un solo archivo.
        try:
            ideologias = juego.parse_ideologies()
            grupos = [k for k, _ in ideologias.entries if k]
            extra.append(f"Grupos ideologia: {', '.join(grupos)}")
            for grupo in grupos:
                bloque = ideologias.get(grupo)
                tipos = bloque.get("types")
                if tipos is not None:
                    extra.append(f"  {grupo}: {', '.join(tipos.keys())}")
        except Exception as exc:  # noqa: BLE001
            extra.append(f"Grupos ideologia: ERROR - {exc}")

        try:
            states = juego.states()
            extra.append(f"States vanilla:   {len(states)}")
        except Exception as exc:  # noqa: BLE001
            extra.append(f"States vanilla:   ERROR - {exc}")

    if ctx is not None:
        extra.append(f"Archivos:         {len(ctx.written)}")
        extra.append(f"Avisos:           {len(ctx.warnings)}")
        extra.append(f"Sin generar:      {len(ctx.skipped)}")

        # La tabla de balance va al final del reporte y tambien suelta, al
        # lado de este script, para poder abrirla sin buscar en build/.
        balance = ctx.data.get("balance_path")
        if balance and Path(balance).exists():
            texto_balance = Path(balance).read_text(encoding="utf-8")
            extra.append("")
            extra.append(texto_balance)
            try:
                (REPO / "balance.txt").write_text(texto_balance, encoding="utf-8")
            except OSError:
                pass

    texto = "\n".join(_log_lines + extra) + "\n"
    REPORT.write_text(texto, encoding="utf-8")
    bien(f"Escrito en: {REPORT}")


# ---------------------------------------------------------------------------


def main() -> int:
    ruta_manual = sys.argv[1] if len(sys.argv) > 1 else None

    say()
    say("  2100 MEGANATIONS  —  instalador")
    say("  Esto solo LEE tu Hearts of Iron IV. No lo modifica.")

    if not paso_python():
        paso_reporte(None, None)
        return 1

    juego = paso_buscar_juego(ruta_manual)
    if juego is None:
        paso_reporte(None, None)
        return 1

    ctx = paso_generar(juego)
    if ctx is None:
        paso_reporte(juego, None)
        return 1

    instalado = paso_instalar(ctx)
    paso_reporte(juego, ctx)

    titulo("LISTO")
    if instalado:
        say("  El mod esta instalado. Ahora:")
        say()
        say("    1. Abri el launcher de Hearts of Iron IV")
        say("    2. Anda a 'Mods' y activa '2100 Meganations'")
        say("    3. Jugar")
        say()
        say("  Es una version en desarrollo: el EFE tiene arbol, eventos y arte;")
        say("  las otras potencias todavia no. Mira balance.txt para ver con")
        say("  que arranca cada faccion.")
    say()
    say("  PASAME ESTO:")
    say(f"    1. El archivo  {REPORT}")
    say("    2. Si el juego tira error, tambien el error.log, que esta en:")
    say("       Documentos/Paradox Interactive/Hearts of Iron IV/logs/error.log")
    say()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nCancelado.")
        sys.exit(130)
    except Exception:  # noqa: BLE001
        print("\n\nERROR INESPERADO — pasame todo esto:\n")
        traceback.print_exc()
        try:
            REPORT.write_text(
                "\n".join(_log_lines) + "\n\nERROR INESPERADO:\n" + traceback.format_exc(),
                encoding="utf-8",
            )
            print(f"\n(tambien quedo guardado en {REPORT})")
        except OSError:
            pass
        sys.exit(1)
