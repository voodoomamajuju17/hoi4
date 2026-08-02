"""Puente con la instalación de HOI4 vanilla.

Existe por tres razones, todas defensivas:

  1. IDEOLOGÍAS. La estrategia elegida (reskin_groups, Q006) no escribe
     common/ideologies/00_ideologies.txt de cero: parte del archivo vanilla y
     le inyecta nuestras sub-ideologías. Escribirlo de cero significaría
     reproducir de memoria los bloques `rules`, `ai` y
     `dynamic_faction_names` de los cuatro grupos, y cualquier campo que me
     olvide o invente rompe la carga.

  2. STATE IDs. El reparto territorial del spec está por nombre de región. Los
     IDs numéricos salen de leer history/states/ de verdad. Un ID inventado
     reasigna territorio ajeno EN SILENCIO, sin error de carga.

  3. VERSIÓN. supported_version del descriptor sale de launcher-settings.json
     en vez de un número hardcodeado que envejece.

Sin --vanilla-path el generador sigue funcionando, pero salta lo que dependa
de esto y lo dice fuerte. No inventa.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from . import pdx
from .errors import VanillaError

# Rutas donde suele estar HOI4 según el sistema operativo.
CANDIDATE_PATHS = [
    "~/.steam/steam/steamapps/common/Hearts of Iron IV",
    "~/.local/share/Steam/steamapps/common/Hearts of Iron IV",
    "~/Library/Application Support/Steam/steamapps/common/Hearts of Iron IV",
    "C:/Program Files (x86)/Steam/steamapps/common/Hearts of Iron IV",
    "D:/Steam/steamapps/common/Hearts of Iron IV",
]


@dataclass
class StateInfo:
    id: int
    name_key: str
    owner: str | None
    provinces: list[int]
    path: Path


class Vanilla:
    def __init__(self, root: Path):
        self.root = root
        if not (root / "common").is_dir():
            raise VanillaError(
                f"'{root}' no parece una instalacion de HOI4 (no tiene common/)",
                hint="pasa la carpeta raiz del juego, la que contiene common/, history/ y map/",
            )
        self._states: list[StateInfo] | None = None

    # -- versión ------------------------------------------------------------

    def version(self) -> str:
        settings = self.root / "launcher-settings.json"
        if settings.exists():
            try:
                data = json.loads(settings.read_text(encoding="utf-8-sig"))
                raw = data.get("rawVersion") or data.get("version")
                if raw:
                    return str(raw)
            except (json.JSONDecodeError, OSError):
                pass
        raise VanillaError(
            "no pude leer la version del juego de launcher-settings.json",
            hint="pasala a mano con --game-version 1.x.y",
        )

    @staticmethod
    def supported_version(version: str) -> str:
        """'1.16.3' -> '1.16.*'. El descriptor usa comodines en el patch."""
        parts = version.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}.*"
        return version

    # -- ideologías ---------------------------------------------------------

    def ideologies_file(self) -> Path:
        path = self.root / "common" / "ideologies" / "00_ideologies.txt"
        if not path.exists():
            matches = sorted((self.root / "common" / "ideologies").glob("*.txt"))
            if not matches:
                raise VanillaError(
                    "no encontre common/ideologies/ en la instalacion vanilla",
                    hint=f"buscado en {self.root}",
                )
            return matches[0]
        return path

    def parse_ideologies(self) -> pdx.Block:
        path = self.ideologies_file()
        try:
            root = pdx.parse_file(path)
        except ValueError as exc:
            raise VanillaError(f"no pude parsear {path}: {exc}") from exc
        ideologies = root.get("ideologies")
        if not isinstance(ideologies, pdx.Block):
            raise VanillaError(
                f"{path} no tiene un bloque 'ideologies' en la raiz",
                hint="puede que la estructura del archivo haya cambiado en esta version",
            )
        return ideologies

    # -- states -------------------------------------------------------------

    def states(self) -> list[StateInfo]:
        if self._states is not None:
            return self._states
        state_dir = self.root / "history" / "states"
        if not state_dir.is_dir():
            raise VanillaError(f"no existe {state_dir}")
        out: list[StateInfo] = []
        for path in sorted(state_dir.glob("*.txt")):
            try:
                root = pdx.parse_file(path)
            except ValueError:
                continue
            state = root.get("state")
            if not isinstance(state, pdx.Block):
                continue
            sid = pdx.text(state.get("id"))
            name = pdx.text(state.get("name"))
            history = state.get("history")
            owner = pdx.text(history.get("owner")) if isinstance(history, pdx.Block) else None
            provinces_block = state.get("provinces")
            provinces = []
            if isinstance(provinces_block, pdx.Block):
                provinces = [
                    int(t) for _, v in provinces_block.entries
                    if (t := pdx.text(v)) and t.isdigit()
                ]
            if sid is None:
                continue
            out.append(
                StateInfo(
                    id=int(sid),
                    name_key=name or "",
                    owner=owner or None,
                    provinces=provinces,
                    path=path,
                )
            )
        self._states = out
        return out

    def states_owned_by(self, tag: str) -> list[StateInfo]:
        return [s for s in self.states() if s.owner == tag]

    def state_localisation(self) -> dict[str, str]:
        """STATE_123 -> 'Buenos Aires', leyendo la localisation inglesa vanilla."""
        out: dict[str, str] = {}
        loc_dir = self.root / "localisation" / "english"
        if not loc_dir.is_dir():
            loc_dir = self.root / "localisation"
        pattern = re.compile(r'^\s*(STATE_\d+):\d*\s+"(.*)"\s*$')
        for path in loc_dir.glob("**/*_l_english.yml"):
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                m = pattern.match(line)
                if m:
                    out[m.group(1)] = m.group(2)
        return out


def locate(explicit: str | None = None) -> Vanilla | None:
    """Encuentra la instalación vanilla. Devuelve None si no hay."""
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    elif os.environ.get("HOI4_PATH"):
        candidates.append(os.environ["HOI4_PATH"])
    else:
        candidates.extend(CANDIDATE_PATHS)

    for raw in candidates:
        path = Path(os.path.expanduser(raw))
        if (path / "common").is_dir():
            return Vanilla(path)

    if explicit:
        raise VanillaError(
            f"no encontre una instalacion de HOI4 en '{explicit}'",
            hint="deberia ser la carpeta que contiene common/, history/ y map/",
        )
    return None
