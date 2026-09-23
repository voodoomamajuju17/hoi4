"""Contexto compartido de una corrida del generador."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from pathlib import Path

from . import pdx
from .errors import GenError
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
    notes: list[str] = field(default_factory=list)
    # Resultados que un emisor le pasa a otro (ej. territorio -> historia).
    data: dict[str, Any] = field(default_factory=dict)

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

    def note(self, message: str) -> None:
        """Dato informativo para el reporte: no es un problema."""
        self.notes.append(message)

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    # -- validación contra vanilla ------------------------------------------

    def verify_keys(self, kind: str, keys: dict[str, str]) -> None:
        """Verifica que cada clave exista en documentation/ del juego.

        `keys` va de clave a dónde se usó, para que el error diga qué tocar.
        Sin vanilla o sin documentation/ no hay contra qué validar: se avisa
        una vez por tipo y se sigue.
        """
        if not keys:
            return
        known = self.vanilla.documented_keys(kind) if self.vanilla else None
        if known is None or self.vanilla is None:
            self.warn(
                f"{kind}: no se validaron contra el juego (falta --vanilla-path o "
                f"documentation/). Si alguno no existe, lo va a decir error.log."
            )
            return
        missing = {k: where for k, where in keys.items() if not self.vanilla.is_documented(kind, k)}
        if missing:
            lines = "\n".join(f"    {k}  (en {where})" for k, where in sorted(missing.items()))
            raise GenError(
                f"{len(missing)} {kind} que no existen en esta version del juego:\n{lines}",
                hint="corregilos en spec/. Buscados en documentation/ de la instalacion.",
                where=kind,
            )
