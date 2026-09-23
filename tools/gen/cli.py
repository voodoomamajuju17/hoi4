"""CLI del generador.

    python -m tools.gen build     [--vanilla-path P] [--game-version V] [--out DIR]
    python -m tools.gen validate  # valida spec/ sin escribir nada
    python -m tools.gen check     # regenera en temp y compara con build/
    python -m tools.gen install   # copia build/ a la carpeta de mods de HOI4

`check` es lo que hace cumplir la regla dura del proyecto: los .txt del mod son
salida del generador y nunca se editan a mano. Si alguien toca build/, check
falla y muestra el diff.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys
import tempfile
from pathlib import Path

from . import specload, vanilla as vanilla_mod
from .context import BuildContext
from .emitters import balance as em_balance
from .emitters import cleanup as em_cleanup
from .emitters import characters as em_characters
from .emitters import countries as em_countries
from .emitters import decisions as em_decisions
from .emitters import descriptor as em_descriptor
from .emitters import diplomacy as em_diplomacy
from .emitters import events as em_events
from .emitters import focus_trees as em_focus_trees
from .emitters import forces as em_forces
from .emitters import history as em_history
from .emitters import ideas as em_ideas
from .emitters import ideologies as em_ideologies
from .emitters import military as em_military
from .emitters import menu as em_menu
from .emitters import militia as em_militia
from .emitters import names as em_names
from .emitters import resources as em_resources
from .emitters import scenario as em_scenario
from .emitters import territory as em_territory
from .errors import GenError
from .loc import LocRegistry

REPO_ROOT = Path(__file__).resolve().parents[2]

# Orden intencional: el descriptor primero para que un error de version salte
# antes de escribir cien archivos.
EMITTERS = [
    ("descriptor", em_descriptor.emit),
    ("ideologies", em_ideologies.emit),
    ("countries", em_countries.emit),
    ("resources", em_resources.emit),
    ("territory", em_territory.emit),   # antes que focos e historia: define capitales
    ("militia", em_militia.emit),       # antes que history: define el oob
    ("military", em_military.emit),     # despues de militia: tecnologias, ejercito, equipo
    ("forces", em_forces.emit),         # armada y aviacion heredadas de 1936
    ("ideas", em_ideas.emit),
    ("characters", em_characters.emit),
    ("names", em_names.emit),
    ("focus_trees", em_focus_trees.emit),
    ("events", em_events.emit),
    ("decisions", em_decisions.emit),
    ("cleanup", em_cleanup.emit),       # vacia decisiones de paises vanilla que no existen
    ("diplomacy", em_diplomacy.emit),   # antes que history: opiniones, guerras, tension
    ("history", em_history.emit),
    ("scenario", em_scenario.emit),     # despues de territory: destaca solo paises con states
    ("menu", em_menu.emit),
    ("balance", em_balance.emit),       # ultimo: resume lo que quedo
]


# ---------------------------------------------------------------------------


def build(
    out_dir: Path,
    *,
    vanilla_path: str | None = None,
    game_version: str | None = None,
    spec_dir: Path | None = None,
    quiet: bool = False,
) -> BuildContext:
    spec = specload.load(spec_dir or REPO_ROOT / "spec")

    van = vanilla_mod.locate(vanilla_path)
    mod_root = out_dir / spec.mod_folder

    if mod_root.exists():
        shutil.rmtree(mod_root)
    for stale in out_dir.glob("*.mod"):
        stale.unlink()

    ctx = BuildContext(
        spec=spec,
        out_root=out_dir,
        mod_root=mod_root,
        loc=LocRegistry(),
        vanilla=van,
        game_version=game_version,
    )

    for name, fn in EMITTERS:
        try:
            fn(ctx)
        except GenError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise GenError(f"el emisor '{name}' exploto: {exc}", where=name) from exc

    # Cero claves huerfanas, verificado antes de escribir los .yml.
    ctx.loc.verify()
    for path in ctx.loc.write(mod_root):
        ctx.track(path)

    if not quiet:
        _report(ctx, van)
    return ctx


def _report(ctx: BuildContext, van) -> None:
    print(f"\n  mod:     {ctx.spec.project['name']} v{ctx.spec.project['version']}")
    print(f"  salida:  {ctx.mod_root}")
    print(f"  vanilla: {van.root if van else 'NO ENCONTRADA'}")
    print(f"  paises:  {len(ctx.spec.countries)}")
    print(f"  loc:     {ctx.spec and ctx.loc.stats()}")
    print(f"  archivos:{len(ctx.written)}")

    for n in ctx.notes:
        print(f"  {n}")

    if ctx.warnings:
        print(f"\n  AVISOS ({len(ctx.warnings)}):")
        for w in ctx.warnings:
            print(f"    ! {w}")

    if ctx.skipped:
        print(f"\n  NO GENERADO ({len(ctx.skipped)}):")
        for s in ctx.skipped:
            q = f" [{s.question}]" if s.question else ""
            print(f"    - {s.what}{q}\n        {s.reason}")


# ---------------------------------------------------------------------------


def cmd_validate(args) -> int:
    spec = specload.load(args.spec or REPO_ROOT / "spec")
    types, groups = spec.ideology_index()
    questions = spec.raw["questions"]["questions"]
    blocking = [q for q in questions if q.get("blocking_phase") in (2, 3) and q.get("status") != "ANSWERED"]
    print("spec valido")
    print(f"  paises:           {len(spec.countries)}")
    print(f"  grupos ideologia: {len(groups)}")
    print(f"  sub-ideologias:   {len(types)}")
    answered = sum(1 for q in questions if q.get("status") == "ANSWERED")
    print(f"  preguntas:        {len(questions)} ({answered} respondidas, {len(blocking)} abiertas bloquean fase 2 o 3)")
    return 0


def cmd_build(args) -> int:
    out = Path(args.out) if args.out else REPO_ROOT / "build"
    ctx = build(
        out,
        vanilla_path=args.vanilla_path,
        game_version=args.game_version,
        spec_dir=Path(args.spec) if args.spec else None,
    )
    return 1 if (args.strict and (ctx.skipped or ctx.warnings)) else 0


def cmd_check(args) -> int:
    """Regenera en un temporal y compara con build/. Detecta ediciones a mano."""
    committed = Path(args.out) if args.out else REPO_ROOT / "build"
    if not committed.exists():
        print("no existe build/. Corre 'build' primero.", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        build(
            Path(tmp),
            vanilla_path=args.vanilla_path,
            game_version=args.game_version,
            spec_dir=Path(args.spec) if args.spec else None,
            quiet=True,
        )
        differences = _compare_trees(Path(tmp), committed)

    if not differences:
        print("build/ coincide con lo que produce el spec")
        return 0

    print(f"build/ NO coincide con el spec ({len(differences)} diferencia(s)):\n", file=sys.stderr)
    for kind, rel in differences[:40]:
        print(f"  {kind:9} {rel}", file=sys.stderr)
    if len(differences) > 40:
        print(f"  ... y {len(differences) - 40} mas", file=sys.stderr)
    print(
        "\nLos .txt del mod son SALIDA del generador y no se editan a mano.\n"
        "Si el cambio es intencional, va en spec/ y despues 'build'.",
        file=sys.stderr,
    )
    return 1


def _compare_trees(expected: Path, actual: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    exp_files = {p.relative_to(expected).as_posix() for p in expected.rglob("*") if p.is_file()}
    act_files = {p.relative_to(actual).as_posix() for p in actual.rglob("*") if p.is_file()}
    for rel in sorted(exp_files - act_files):
        out.append(("FALTA", rel))
    for rel in sorted(act_files - exp_files):
        out.append(("SOBRA", rel))
    for rel in sorted(exp_files & act_files):
        if not filecmp.cmp(expected / rel, actual / rel, shallow=False):
            out.append(("DIFIERE", rel))
    return out


def cmd_install(args) -> int:
    spec = specload.load(args.spec or REPO_ROOT / "spec")
    source_root = Path(args.out) if args.out else REPO_ROOT / "build"
    mod_dir = Path(os.path.expanduser(args.mod_dir)) if args.mod_dir else _default_mod_dir()
    if mod_dir is None:
        print(
            "no encontre la carpeta de mods de HOI4. Pasala con --mod-dir\n"
            "  (suele ser ~/Documents/Paradox Interactive/Hearts of Iron IV/mod)",
            file=sys.stderr,
        )
        return 1

    src_mod = source_root / spec.mod_folder
    src_descriptor = source_root / f"{spec.mod_folder}.mod"
    if not src_mod.is_dir() or not src_descriptor.exists():
        print(f"no hay build en {source_root}. Corre 'build' primero.", file=sys.stderr)
        return 1

    dest_mod = mod_dir / spec.mod_folder
    if dest_mod.exists():
        shutil.rmtree(dest_mod)
    mod_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_mod, dest_mod)
    shutil.copy2(src_descriptor, mod_dir / f"{spec.mod_folder}.mod")
    print(f"instalado en {dest_mod}")
    return 0


def _default_mod_dir() -> Path | None:
    for candidate in (
        "~/Documents/Paradox Interactive/Hearts of Iron IV/mod",
        "~/.local/share/Paradox Interactive/Hearts of Iron IV/mod",
    ):
        path = Path(os.path.expanduser(candidate))
        if path.parent.is_dir():
            return path
    return None


# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.gen",
        description="Genera el mod 2100 Meganations a partir de spec/.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--spec", help="carpeta del spec (default: spec/)")
        p.add_argument("--out", help="carpeta de salida (default: build/)")
        p.add_argument(
            "--vanilla-path",
            help="raiz de la instalacion de HOI4. Tambien se lee de $HOI4_PATH.",
        )
        p.add_argument("--game-version", help="version del juego, ej 1.16.3")
        return p

    p = sub.add_parser("build", help="genera el mod")
    common(p).add_argument(
        "--strict", action="store_true", help="salir con error si hay avisos o cosas sin generar"
    )
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("validate", help="valida spec/ sin escribir nada")
    p.add_argument("--spec")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("check", help="verifica que build/ sea lo que produce el spec")
    common(p).set_defaults(func=cmd_check)

    p = sub.add_parser("install", help="copia build/ a la carpeta de mods de HOI4")
    common(p).add_argument("--mod-dir", help="carpeta mod/ de HOI4")
    p.set_defaults(func=cmd_install)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except GenError as exc:
        print(f"\nERROR: {exc}\n", file=sys.stderr)
        return 1
