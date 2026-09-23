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

  4. VALIDACIÓN. Los modificadores, triggers y efectos que emitimos se buscan
     en documentation/ de la instalación, y los íconos en interface/*.gfx. Un
     nombre que no existe falla acá, no en error.log.

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

GAME_DIR = "Hearts of Iron IV"

# Rutas donde suele estar HOI4 según el sistema operativo.
CANDIDATE_PATHS = [
    f"~/.steam/steam/steamapps/common/{GAME_DIR}",
    f"~/.local/share/Steam/steamapps/common/{GAME_DIR}",
    f"~/Library/Application Support/Steam/steamapps/common/{GAME_DIR}",
    f"C:/Program Files (x86)/Steam/steamapps/common/{GAME_DIR}",
    f"C:/Program Files/Steam/steamapps/common/{GAME_DIR}",
    f"D:/Steam/steamapps/common/{GAME_DIR}",
    f"D:/SteamLibrary/steamapps/common/{GAME_DIR}",
    f"E:/SteamLibrary/steamapps/common/{GAME_DIR}",
]

# Donde Steam guarda el listado de sus bibliotecas. Sirve para encontrar el
# juego cuando está en un disco secundario, que es el caso más común de
# "no me lo detecta".
STEAM_ROOTS = [
    "~/.steam/steam",
    "~/.local/share/Steam",
    "~/.var/app/com.valvesoftware.Steam/data/Steam",
    "~/Library/Application Support/Steam",
    "C:/Program Files (x86)/Steam",
    "C:/Program Files/Steam",
]


def steam_library_paths() -> list[Path]:
    """Lee libraryfolders.vdf de Steam y devuelve las carpetas de biblioteca.

    El .vdf es un formato propio de Valve, pero solo necesitamos los valores de
    "path", así que alcanza con una regex en vez de un parser entero.
    """
    found: list[Path] = []
    for raw_root in STEAM_ROOTS:
        root = Path(os.path.expanduser(raw_root))
        for relative in ("steamapps/libraryfolders.vdf", "config/libraryfolders.vdf"):
            vdf = root / relative
            if not vdf.exists():
                continue
            try:
                text = vdf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for match in re.finditer(r'"path"\s+"([^"]+)"', text):
                library = Path(match.group(1).replace("\\\\", "/").replace("\\", "/"))
                if library.is_dir():
                    found.append(library)
        if (root / "steamapps").is_dir():
            found.append(root)
    return found


@dataclass
class StateInfo:
    id: int
    name_key: str
    owner: str | None
    provinces: list[int]
    path: Path
    manpower: int = 0
    cores: tuple[str, ...] = ()

    @property
    def file_label(self) -> str:
        """'278-Buenos Aires.txt' -> 'Buenos Aires'. Segunda fuente de nombre."""
        stem = self.path.stem
        return stem.split("-", 1)[1].strip() if "-" in stem else ""


class Vanilla:
    def __init__(self, root: Path):
        self.root = root
        if not (root / "common").is_dir():
            raise VanillaError(
                f"'{root}' no parece una instalacion de HOI4 (no tiene common/)",
                hint="pasa la carpeta raiz del juego, la que contiene common/, history/ y map/",
            )
        self._states: list[StateInfo] | None = None
        self._documented: dict[str, set[str] | None] = {}
        self._templates: dict[str, list[re.Pattern]] = {}
        self._gfx: set[str] | None = None

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
            mp = pdx.text(state.get("manpower")) or "0"
            cores = tuple(
                c for c in (pdx.text(v) for v in history.get_all("add_core_of"))
                if c
            ) if isinstance(history, pdx.Block) else ()
            out.append(
                StateInfo(
                    id=int(sid),
                    name_key=name or "",
                    owner=owner or None,
                    provinces=provinces,
                    path=path,
                    manpower=int(mp) if mp.isdigit() else 0,
                    cores=cores,
                )
            )
        self._states = out
        return out

    def state_continents(self) -> dict[int, str]:
        """state id -> continente mayoritario de sus provincias.

        Sale de map/definition.csv (columna 8 = índice de continente) y
        map/continent.txt (la lista de nombres, en orden, desde 1). Sin esos
        archivos devuelve {} y los selectores por continente no matchean nada.
        """
        if getattr(self, "_continents", None) is not None:
            return self._continents
        names: list[str] = []
        cont_file = self.root / "map" / "continent.txt"
        if cont_file.exists():
            block = pdx.parse_file(cont_file).get("continents")
            if isinstance(block, pdx.Block):
                names = [pdx.text(v) for _, v in block.entries]
        by_province: dict[int, str] = {}
        definition = self.root / "map" / "definition.csv"
        if names and definition.exists():
            for line in definition.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                parts = line.split(";")
                if len(parts) >= 8 and parts[0].isdigit() and parts[7].strip().isdigit():
                    idx = int(parts[7])
                    if 1 <= idx <= len(names):
                        by_province[int(parts[0])] = names[idx - 1]
        out: dict[int, str] = {}
        for s in self.states():
            counts: dict[str, int] = {}
            for prov in s.provinces:
                cont = by_province.get(prov)
                if cont:
                    counts[cont] = counts.get(cont, 0) + 1
            if counts:
                out[s.id] = max(sorted(counts), key=lambda c: counts[c])
        self._continents = out
        return out

    def country_tags(self) -> set[str]:
        """TAGs que ya usa el juego (common/country_tags/)."""
        tags: set[str] = set()
        for path in (self.root / "common" / "country_tags").glob("*.txt"):
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            tags.update(re.findall(r"^\s*([A-Z][A-Z0-9]{2})\s*=", text, re.MULTILINE))
        return tags

    def wargoal_types(self) -> set[str]:
        words: set[str] = set()
        for path in (self.root / "common" / "wargoals").glob("*.txt"):
            try:
                words.update(re.findall(r"^\t?([a-z_]+)\s*=\s*\{",
                                        path.read_text(encoding="utf-8-sig", errors="replace"), re.MULTILINE))
            except OSError:
                continue
        return words

    def country_history_files(self) -> dict[str, Path]:
        """TAG -> history/countries/<TAG - Nombre>.txt vanilla."""
        out: dict[str, Path] = {}
        for path in sorted((self.root / "history" / "countries").glob("*.txt")):
            tag = path.name[:3]
            if re.fullmatch(r"[A-Z][A-Z0-9]{2}", tag):
                out.setdefault(tag, path)
        return out

    def states_owned_by(self, tag: str) -> list[StateInfo]:
        return [s for s in self.states() if s.owner == tag]

    def state_localisation(self) -> dict[str, str]:
        """STATE_123 -> 'Buenos Aires', leyendo la localisation inglesa vanilla."""
        out: dict[str, str] = {}
        loc_dir = self.root / "localisation" / "english"
        if not loc_dir.is_dir():
            loc_dir = self.root / "localisation"
        pattern = _LOC_LINE
        for path in loc_dir.glob("**/*_l_english.yml"):
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                m = pattern.match(line)
                if m and m.group(1).startswith("STATE_"):
                    out[m.group(1)] = m.group(2)
        return out


    # -- validación contra el juego -----------------------------------------

    def documented_keys(self, kind: str) -> set[str] | None:
        """Identificadores que aparecen en documentation/*<kind>*.

        kind es 'modifiers', 'triggers' o 'effects'. HOI4 trae esos archivos
        generados por el motor desde hace varios parches. Devuelve None si la
        instalación no los tiene: sin fuente no se valida, se avisa.

        Es un conjunto de TODAS las palabras del archivo, no un parser del
        formato: puede dejar pasar un nombre que aparece solo en un texto
        explicativo, pero nunca rechaza uno bueno. Rechazar uno bueno bloquea
        el build; dejar pasar uno malo lo termina diciendo error.log.
        """
        if kind in self._documented:
            return self._documented[kind]
        doc_dir = self.root / "documentation"
        files = sorted(doc_dir.glob(f"*{kind}*")) if doc_dir.is_dir() else []
        if not files:
            self._documented[kind] = None
            return None
        words: set[str] = set()
        templates: list[re.Pattern] = []
        for path in files:
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            words.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
            templates.extend(_templates_in(text))
        self._documented[kind] = words
        self._templates[kind] = templates
        return words

    def is_documented(self, kind: str, key: str) -> bool | None:
        """¿Existe `key`? None si no hay documentation/ contra qué validar.

        Además del nombre literal acepta dos cosas que el juego arma solo y la
        documentación lista con un hueco en vez de nombre por nombre:
          - plantillas del propio archivo: `production_speed_<building>_factor`
          - familias derivadas de datos vanilla: `<ideologia>_drift`,
            `production_speed_<edificio>_factor`, etc.
        """
        known = self.documented_keys(kind)
        if known is None:
            return None
        if key in known or key in self.dynamic_keys(kind):
            return True
        return any(t.fullmatch(key) for t in self._templates.get(kind, []))

    def dynamic_keys(self, kind: str) -> set[str]:
        """Nombres que HOI4 genera por cada ideología o edificio del juego."""
        if kind != "modifiers":
            return set()
        out: set[str] = set()
        ideologies: set[str] = set()
        try:
            for group, body in self.parse_ideologies().entries:
                if not isinstance(body, pdx.Block) or group is None:
                    continue
                ideologies.add(group)
                types = body.get("types")
                if isinstance(types, pdx.Block):
                    ideologies.update(k for k in types.keys())
        except VanillaError:
            pass
        for ideology in ideologies:
            out.update({f"{ideology}_drift", f"{ideology}_acceptance"})
        for building in self.building_keys():
            out.update({
                f"production_speed_{building}_factor",
                f"{building}_max_level",
            })
        return out

    def autonomy_ids(self) -> set[str]:
        """ids de common/autonomous_states/ (autonomy_puppet, etc.)."""
        out: set[str] = set()
        for path in sorted((self.root / "common" / "autonomous_states").glob("*.txt")):
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            out.update(re.findall(r"\bid\s*=\s*\"?([A-Za-z0-9_]+)", text))
        return out

    def building_keys(self) -> set[str]:
        out: set[str] = set()
        for path in sorted((self.root / "common" / "buildings").glob("*.txt")):
            try:
                root = pdx.parse_file(path)
            except ValueError:
                continue
            block = root.get("buildings")
            if isinstance(block, pdx.Block):
                out.update(k for k, v in block.entries if k and isinstance(v, pdx.Block))
        return out

    def gfx_names(self) -> set[str]:
        """Todos los sprites declarados en interface/**/*.gfx."""
        if self._gfx is not None:
            return self._gfx
        names: set[str] = set()
        pattern = re.compile(r'name\s*=\s*"?(GFX_[A-Za-z0-9_]+)')
        for path in (self.root / "interface").glob("**/*.gfx"):
            try:
                names.update(pattern.findall(path.read_text(encoding="utf-8-sig", errors="replace")))
            except OSError:
                continue
        self._gfx = names
        return names

    def loc_keys_with_text(self, wanted: str) -> list[str]:
        """Claves de la localisation inglesa cuyo texto es exactamente `wanted`.

        Sirve para reskinear algo por nombre visible (ej. el recurso "Coal")
        sin escribir de memoria qué clave usa el juego para mostrarlo.
        """
        out: set[str] = set()
        loc_dir = self.root / "localisation" / "english"
        if not loc_dir.is_dir():
            loc_dir = self.root / "localisation"
        pattern = _LOC_LINE
        for path in loc_dir.glob("**/*_l_english.yml"):
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                m = pattern.match(line)
                if m and m.group(2).strip().lower() == wanted.strip().lower():
                    out.add(m.group(1))
        return sorted(out)


# `CLAVE:0 "texto"`, tolerando comillas escapadas y comentarios al final de
# la línea (# ...). La versión anterior exigía que la línea terminara en la
# comilla y perdía los nombres con comentario: salían como "?" en el reporte.
_LOC_LINE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\d*\s*"((?:[^"\\]|\\.)*)"')


def _templates_in(text: str) -> list[re.Pattern]:
    """Nombres con hueco (`a_<x>_b`, `a_{x}_b`, `a_[x]_b`) pasados a regex."""
    hole = r"(?:<[^<>\s]+>|\{[^{}\s]+\}|\[[^\[\]\s]+\])"
    token = re.compile(rf"[A-Za-z0-9_]*{hole}(?:[A-Za-z0-9_]|{hole})*")
    out = []
    for raw in set(token.findall(text)):
        parts = re.split(f"({hole})", raw)
        pattern = "".join(
            "[A-Za-z0-9_]+" if re.fullmatch(hole, part) else re.escape(part)
            for part in parts if part
        )
        if pattern.replace("[A-Za-z0-9_]+", ""):  # un hueco solo no es plantilla
            out.append(re.compile(pattern))
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
        # Error util: si apuntaron al .exe o a la carpeta de mods, decirlo.
        given = Path(os.path.expanduser(explicit))
        hint = "deberia ser la carpeta que contiene common/, history/ y map/"
        if given.is_file():
            hint = (
                f"'{given.name}' es un archivo. Pasa la CARPETA que lo contiene, "
                f"no el ejecutable: {given.parent}"
            )
        elif (given / "mod").is_dir() or given.name == "mod":
            hint = (
                "esa parece la carpeta de MODS (Documentos/Paradox Interactive/...). "
                "Necesito la de instalacion del juego, la de steamapps/common/."
            )
        raise VanillaError(f"no encontre una instalacion de HOI4 en '{explicit}'", hint=hint)

    # Ultimo intento: recorrer las bibliotecas que Steam tenga declaradas,
    # incluidas las de discos secundarios.
    for library in steam_library_paths():
        path = library / "steamapps" / "common" / GAME_DIR
        if (path / "common").is_dir():
            return Vanilla(path)
    return None
