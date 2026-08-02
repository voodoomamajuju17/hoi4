"""Contexto compartido de una corrida del generador."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import pdx
from .loc import LocRegistry
from .specload import Spec
from .vanilla import Vanilla


@dataclass
class Skipped:
    """Algo que no se generó, y por qué. Se reporta al final."""

    what: str
    reason: str
    question: str | None = None


@dataclass
class BuildContext:
    spec: Spec
    out_root: Path          # build/
    mod_root: Path          # build/<mod_folder>/
    loc: LocRegistry
    vanilla: Vanilla | None
    game_version: str | None
    written: list[Path] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # -- escritura ----------------------------------------------------------

    def write_text(self, relative: str, text: str) -> Path:
        path = self.mod_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        self.written.append(path)
        return path

    def write_script(self, relative: str, block: pdx.Block, *, source: str) -> Path:
        """Escribe un .txt de Paradox con el banner de archivo generado."""
        return self.write_text(relative, pdx.banner_for(source) + pdx.render(block))

    def track(self, path: Path) -> Path:
        self.written.append(path)
        return path

    # -- reporte ------------------------------------------------------------

    def skip(self, what: str, reason: str, question: str | None = None) -> None:
        self.skipped.append(Skipped(what, reason, question))

    def warn(self, message: str) -> None:
        self.warnings.append(message)
