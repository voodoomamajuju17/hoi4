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
    resources: dict | None = None      # recurso -> cantidad
    buildings: dict | None = None      # edificio de state -> nivel (sin los de provincia)
    victory_points: int = 0
    category: str | None = None
    vp_provinces: tuple[int, ...] = ()   # de mayor a menor valor

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
            resources: dict[str, float] = {}
            res_block = state.get("resources")
            if isinstance(res_block, pdx.Block):
                for k, v in res_block.entries:
                    try:
                        resources[k] = float(pdx.text(v))
                    except (TypeError, ValueError):
                        pass
            buildings: dict[str, int] = {}
            vp = 0
            vps: list[tuple[int, int]] = []
            if isinstance(history, pdx.Block):
                b_block = history.get("buildings")
                if isinstance(b_block, pdx.Block):
                    for k, v in b_block.entries:
                        if k and not k.isdigit() and not isinstance(v, pdx.Block):
                            try:
                                buildings[k] = int(float(pdx.text(v)))
                            except (TypeError, ValueError):
                                pass
                for vblock in history.get_all("victory_points"):
                    if isinstance(vblock, pdx.Block) and len(vblock) >= 2:
                        try:
                            value = int(float(pdx.text(vblock.entries[1][1])))
                            vp += value
                            vps.append((value, int(pdx.text(vblock.entries[0][1]))))
                        except (TypeError, ValueError):
                            pass
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
                    resources=resources,
                    buildings=buildings,
                    victory_points=vp,
                    category=pdx.text(state.get("state_category")) if state.get("state_category") is not None else None,
                    vp_provinces=tuple(p for _, p in sorted(vps, key=lambda x: -x[0])),
                )
            )
        self._states = out
        return out

    def _definition(self) -> dict[int, tuple[int, str, int]]:
        """map/definition.csv: provincia -> (color RGB como int, tipo, continente)."""
        if getattr(self, "_definition_cache", None) is not None:
            return self._definition_cache
        out: dict[int, tuple[int, str, int]] = {}
        definition = self.root / "map" / "definition.csv"
        if definition.exists():
            for line in definition.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                parts = line.split(";")
                if len(parts) < 8 or not parts[0].isdigit():
                    continue
                try:
                    r, g, b = int(parts[1]), int(parts[2]), int(parts[3])
                    cont = int(parts[7]) if parts[7].strip().isdigit() else 0
                except ValueError:
                    continue
                out[int(parts[0])] = ((r << 16) | (g << 8) | b, parts[4].strip(), cont)
        self._definition_cache = out
        return out

    def land_provinces(self) -> set[int]:
        return {p for p, (_, kind, _) in self._definition().items() if kind == "land"}

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
        by_province = {
            p: names[idx - 1]
            for p, (_, _, idx) in self._definition().items()
            if 1 <= idx <= len(names)
        }
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

    def province_adjacency(self, cache_dir: Path | None = None) -> set[tuple[int, int]]:
        """Pares de provincias vecinas (a < b), leídos de map/provinces.bmp.

        El juego no trae la lista de vecinos escrita: está implícita en el
        bitmap, donde cada provincia es un color (definition.csv). Dos
        provincias son vecinas si hay un pixel de una pegado a uno de la otra.
        Recorrer el bitmap entero tarda unos segundos, así que el resultado se
        guarda en cache_dir, invalidado por tamaño y fecha del .bmp.
        """
        if getattr(self, "_adjacency", None) is not None:
            return self._adjacency
        bmp = self.root / "map" / "provinces.bmp"
        if not bmp.exists():
            return set()
        stamp = f"{bmp.stat().st_size}-{int(bmp.stat().st_mtime)}"
        cache = cache_dir / f"adjacency-{stamp}.json" if cache_dir else None
        if cache and cache.exists():
            try:
                self._adjacency = {tuple(p) for p in json.loads(cache.read_text())}
                return self._adjacency
            except (ValueError, OSError):
                pass
        pairs = _bmp_adjacency(bmp.read_bytes(), {c: p for p, (c, _, _) in self._definition().items()})
        if cache:
            try:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(sorted(pairs)))
            except OSError:
                pass
        self._adjacency = pairs
        return pairs

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

    def graphical_cultures(self) -> tuple[set[str], set[str]]:
        """Valores de graphical_culture y graphical_culture_2d que usa algún
        país vanilla (common/countries/). Son los únicos que seguro cargan."""
        gfx: set[str] = set()
        gfx2d: set[str] = set()
        for path in (self.root / "common" / "countries").glob("*.txt"):
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            gfx.update(re.findall(r"^\s*graphical_culture\s*=\s*\"?([a-z0-9_]+)", text, re.MULTILINE))
            gfx2d.update(re.findall(r"^\s*graphical_culture_2d\s*=\s*\"?([a-z0-9_]+)", text, re.MULTILINE))
        return gfx, gfx2d

    def ai_strategy_types(self) -> set[str] | None:
        """Tipos de ai_strategy que usa el juego (common/ai_strategy/**).

        No hay documentación de estos tipos: lo que el juego usa en sus propios
        planes es lo único que se sabe que existe. None si no hay carpeta."""
        folder = self.root / "common" / "ai_strategy"
        if not folder.is_dir():
            return None
        words: set[str] = set()
        for path in folder.rglob("*.txt"):
            try:
                words.update(re.findall(r"\btype\s*=\s*([a-z_]+)",
                                        path.read_text(encoding="utf-8-sig", errors="replace")))
            except OSError:
                continue
        return words

    def unit_leader_traits(self) -> set[str] | None:
        """Rasgos de generales y almirantes (common/unit_leader/*.txt -> leader_traits).
        None si la carpeta no existe."""
        folder = self.root / "common" / "unit_leader"
        if not folder.is_dir():
            return None
        out: set[str] = set()
        for path in sorted(folder.glob("*.txt")):
            try:
                root = pdx.parse_file(path)
            except ValueError:
                continue
            block = root.get("leader_traits")
            if isinstance(block, pdx.Block):
                out.update(k for k, v in block.entries if k and isinstance(v, pdx.Block))
        return out

    def ai_strategy_ids(self) -> dict[str, set[str]] | None:
        """Por tipo de ai_strategy, los `id` que el juego usa con ese tipo
        (role_ratio -> infantry, armor...). Sirve para no inventar ids."""
        folder = self.root / "common" / "ai_strategy"
        if not folder.is_dir():
            return None
        out: dict[str, set[str]] = {}
        pat = re.compile(r"\btype\s*=\s*([a-z_]+)\s+id\s*=\s*\"?([A-Za-z0-9_]+)")
        for path in folder.rglob("*.txt"):
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            for kind, ident in pat.findall(text):
                out.setdefault(kind, set()).add(ident)
        return out

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


    def localisation(self, lang: str, keys: set[str]) -> dict[str, str]:
        """Texto vanilla de las claves pedidas, en 'english' o 'spanish'
        (incluye las carpetas de las expansiones)."""
        out: dict[str, str] = {}
        roots = [self.root / "localisation"] + sorted((self.root / "dlc").glob("*/localisation"))
        for base in roots:
            if not base.is_dir():
                continue
            for path in base.glob(f"**/*_l_{lang}.yml"):
                try:
                    text = path.read_text(encoding="utf-8-sig", errors="replace")
                except OSError:
                    continue
                for line in text.splitlines():
                    m = _LOC_LINE.match(line)
                    if m and m.group(1) in keys and m.group(1) not in out:
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

    def technologies(self) -> list[tuple[str, int, bool]]:
        """(tech, start_year, elegible) de common/technologies/.

        No elegible = no se regala al arranque: doctrinas (archivos o
        carpetas con "doctrine"), techs con `xor` (excluyentes) y las que
        solo existen SIN un DLC (bloques NOT = { has_dlc = ... }).
        """
        out: list[tuple[str, int, bool]] = []
        for path in sorted((self.root / "common" / "technologies").glob("*.txt")):
            try:
                root = pdx.parse_file(path)
            except ValueError:
                continue
            block = root.get("technologies")
            if not isinstance(block, pdx.Block):
                continue
            doctrine_file = "doctrine" in path.name.lower()
            for name, tech in block.entries:
                if not name or not isinstance(tech, pdx.Block) or name.startswith("@"):
                    continue
                year_text = pdx.text(tech.get("start_year")) if tech.get("start_year") is not None else None
                year = int(year_text) if year_text and year_text.isdigit() else 1936
                folder = tech.get("folder")
                folder_name = pdx.text(folder.get("name")) if isinstance(folder, pdx.Block) and folder.get("name") else ""
                eligible = not (
                    doctrine_file
                    or "doctrine" in (folder_name or "").lower()
                    or "xor" in tech.keys()
                    or _has_not_dlc(tech)
                )
                out.append((name, year, eligible))
        return out

    def tech_tree(self) -> dict[str, dict]:
        """El árbol de investigación: tech -> {year, folder, x, y, leads_to,
        xor, eligible}.

        folder es la pestaña de la pantalla de investigación (infantry_folder,
        naval_folder...); leads_to sale de los bloques `path`; x/y de
        `folder.position` (con las variables @ del archivo resueltas).
        eligible sigue la regla de technologies(): ni doctrinas ni variantes
        que solo existen sin un DLC.
        """
        out: dict[str, dict] = {}
        for path in sorted((self.root / "common" / "technologies").glob("*.txt")):
            try:
                root = pdx.parse_file(path)
            except ValueError:
                continue
            consts: dict[str, float] = {}
            for key, value in root.entries:
                if key and key.startswith("@"):
                    try:
                        consts[key] = float(_scalar(value))
                    except (TypeError, ValueError):
                        pass
            block = root.get("technologies")
            if not isinstance(block, pdx.Block):
                continue
            for key, value in block.entries:
                if key and key.startswith("@"):
                    try:
                        consts[key] = float(_scalar(value))
                    except (TypeError, ValueError):
                        pass
            doctrine_file = "doctrine" in path.name.lower()

            def num(v) -> float:
                t = _scalar(v) if v is not None else None
                if t is None:
                    return 0.0
                if t in consts:
                    return consts[t]
                try:
                    return float(t)
                except ValueError:
                    return 0.0

            for name, tech in block.entries:
                if not name or not isinstance(tech, pdx.Block) or name.startswith("@"):
                    continue
                year_text = _scalar(tech.get("start_year")) if tech.get("start_year") is not None else None
                folder = tech.get("folder")
                folder_name, x, y = "", 0.0, 0.0
                if isinstance(folder, pdx.Block):
                    folder_name = _scalar(folder.get("name")) or ""
                    pos = folder.get("position")
                    if isinstance(pos, pdx.Block):
                        x, y = num(pos.get("x")), num(pos.get("y"))
                leads = []
                for pth in tech.get_all("path"):
                    if isinstance(pth, pdx.Block) and pth.get("leads_to_tech") is not None:
                        lead = _scalar(pth.get("leads_to_tech"))
                        if lead:
                            leads.append(lead)
                xor = tech.get("xor")
                xor_list = [x for x in (_scalar(v) for _, v in xor.entries) if x] if isinstance(xor, pdx.Block) else []
                enables = set()
                for field in ("enable_equipments", "enable_equipment_modules"):
                    blk = tech.get(field)
                    if isinstance(blk, pdx.Block):
                        enables.update(x for x in (_scalar(v) for _, v in blk.entries) if x)
                out[name] = {
                    "enables": enables,
                    "year": int(year_text) if year_text and year_text.isdigit() else 1936,
                    "folder": folder_name, "x": x, "y": y, "leads_to": leads, "xor": xor_list,
                    "eligible": not (doctrine_file or "doctrine" in folder_name.lower() or _has_not_dlc(tech)),
                }
        return out

    def tech_categories(self) -> set[str]:
        """Categorías de investigación (bloques `categories` de cada tech):
        lo que acepta add_tech_bonus."""
        out: set[str] = set()
        for path in sorted((self.root / "common" / "technologies").glob("*.txt")):
            try:
                root = pdx.parse_file(path)
            except ValueError:
                continue
            block = root.get("technologies")
            if not isinstance(block, pdx.Block):
                continue
            for _, tech in block.entries:
                if isinstance(tech, pdx.Block):
                    cats = tech.get("categories")
                    if isinstance(cats, pdx.Block):
                        out.update(pdx.text(v) for _, v in cats.entries if not isinstance(v, pdx.Block))
        return out

    def equipment(self) -> dict[str, tuple[str | None, int]]:
        """equipo -> (arquetipo, año) de common/units/equipment/. Los
        arquetipos mismos quedan con arquetipo None."""
        out: dict[str, tuple[str | None, int]] = {}
        for path in sorted((self.root / "common" / "units" / "equipment").glob("*.txt")):
            try:
                root = pdx.parse_file(path)
            except ValueError:
                continue
            block = root.get("equipments")
            if not isinstance(block, pdx.Block):
                continue
            for name, eq in block.entries:
                if not name or not isinstance(eq, pdx.Block):
                    continue
                if pdx.text(eq.get("is_archetype")) == "yes":
                    out[name] = (None, 0)
                    continue
                archetype = pdx.text(eq.get("archetype")) if eq.get("archetype") is not None else None
                year_text = pdx.text(eq.get("year")) if eq.get("year") is not None else "1936"
                out[name] = (archetype, int(year_text) if year_text.isdigit() else 1936)
        return out

    def sub_units(self) -> set[str]:
        out: set[str] = set()
        for path in (self.root / "common" / "units").glob("*.txt"):
            try:
                root = pdx.parse_file(path)
            except ValueError:
                continue
            block = root.get("sub_units")
            if isinstance(block, pdx.Block):
                out.update(k for k, v in block.entries if k and isinstance(v, pdx.Block))
        return out

    def state_category_slots(self) -> dict[str, int]:
        """categoría de state -> local_building_slots (common/state_category/)."""
        out: dict[str, int] = {}
        for path in sorted((self.root / "common" / "state_category").glob("*.txt")):
            try:
                root = pdx.parse_file(path)
            except ValueError:
                continue
            block = root.get("state_categories")
            if not isinstance(block, pdx.Block):
                continue
            for name, cat in block.entries:
                if name and isinstance(cat, pdx.Block):
                    slots = pdx.text(cat.get("local_building_slots")) if cat.get("local_building_slots") is not None else None
                    if slots and slots.isdigit():
                        out[name] = int(slots)
        return out

    def shared_slot_buildings(self) -> set[str]:
        """Edificios que ocupan slots compartidos del state (shares_slots = yes)."""
        out: set[str] = set()
        for path in sorted((self.root / "common" / "buildings").glob("*.txt")):
            try:
                root = pdx.parse_file(path)
            except ValueError:
                continue
            block = root.get("buildings")
            if isinstance(block, pdx.Block):
                for name, b in block.entries:
                    if name and isinstance(b, pdx.Block) and pdx.text(b.get("shares_slots")) == "yes":
                        out.add(name)
        return out

    def idea_names(self) -> set[str]:
        """Todas las ideas vanilla (incluye leyes) de common/ideas/."""
        out: set[str] = set()
        for path in sorted((self.root / "common" / "ideas").glob("*.txt")):
            try:
                root = pdx.parse_file(path)
            except ValueError:
                continue
            ideas = root.get("ideas")
            if not isinstance(ideas, pdx.Block):
                continue
            for _, cat in ideas.entries:
                if isinstance(cat, pdx.Block):
                    out.update(k for k, v in cat.entries if k and isinstance(v, pdx.Block))
        return out

    def country_spirits(self) -> set[str]:
        """Espíritus nacionales vanilla (categoría `country` de common/ideas/,
        sin leyes ni asesores)."""
        out: set[str] = set()
        for path in sorted((self.root / "common" / "ideas").glob("*.txt")):
            try:
                root = pdx.parse_file(path)
            except ValueError:
                continue
            ideas = root.get("ideas")
            if not isinstance(ideas, pdx.Block):
                continue
            for key, cat in ideas.entries:
                if key == "country" and isinstance(cat, pdx.Block):
                    out.update(k for k, v in cat.entries if k and isinstance(v, pdx.Block))
        return out

    def ideas_given_by_scripts(self) -> set[str]:
        """Ideas que los scripts genéricos del juego (on_actions, efectos,
        eventos) pueden dar a cualquier país con add_ideas / add_timed_idea."""
        found: set[str] = set()
        one = re.compile(r"add_ideas\s*=\s*([A-Za-z0-9_.]+)")
        many = re.compile(r"add_ideas\s*=\s*\{([^}]*)\}")
        timed = re.compile(r"add_timed_idea\s*=\s*\{[^}]*?idea\s*=\s*([A-Za-z0-9_.]+)")
        for folder in ("common/on_actions", "common/scripted_effects", "events"):
            for path in sorted((self.root / folder).glob("**/*.txt")):
                try:
                    text = path.read_text(encoding="utf-8-sig", errors="replace")
                except OSError:
                    continue
                found.update(one.findall(text))
                found.update(timed.findall(text))
                for group in many.findall(text):
                    found.update(re.findall(r"[A-Za-z0-9_.]+", group))
        return found

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


def _scalar(value) -> str | None:
    """Como pdx.text, pero un bloque (sintaxis rara de alguna versión) da None
    en vez de romper la lectura de todo el árbol."""
    if isinstance(value, pdx.Block):
        return None
    return pdx.text(value)


def _has_not_dlc(block: pdx.Block) -> bool:
    """¿Hay algún NOT = { ... has_dlc ... } adentro? (variante sin DLC)."""
    for key, value in block.entries:
        if isinstance(value, pdx.Block):
            if key == "NOT" and any(k == "has_dlc" for k, _ in value.entries):
                return True
            if _has_not_dlc(value):
                return True
    return False


def _bmp_adjacency(raw: bytes, color_to_prov: dict[int, int]) -> set[tuple[int, int]]:
    """Vecindad de provincias a partir de un BMP de 24 bits sin comprimir."""
    import struct

    if raw[:2] != b"BM":
        raise VanillaError("provinces.bmp no es un BMP")
    offset = struct.unpack_from("<I", raw, 10)[0]
    width, height = struct.unpack_from("<ii", raw, 18)
    bpp = struct.unpack_from("<H", raw, 28)[0]
    if bpp != 24:
        raise VanillaError(f"provinces.bmp de {bpp} bits; esperaba 24")
    height = abs(height)
    stride = (width * 3 + 3) & ~3
    pairs: set[tuple[int, int]] = set()
    prev: list[int] | None = None
    for y in range(height):
        start = offset + y * stride
        row = raw[start:start + width * 3]
        # BGR -> un int por pixel
        cols = [row[i + 2] << 16 | row[i + 1] << 8 | row[i] for i in range(0, width * 3, 3)]
        for a, b in zip(cols, cols[1:]):
            if a != b:
                pairs.add((a, b) if a < b else (b, a))
        if prev is not None:
            for a, b in zip(prev, cols):
                if a != b:
                    pairs.add((a, b) if a < b else (b, a))
        prev = cols
    out: set[tuple[int, int]] = set()
    for a, b in pairs:
        pa, pb = color_to_prov.get(a), color_to_prov.get(b)
        if pa is not None and pb is not None and pa != pb:
            out.add((pa, pb) if pa < pb else (pb, pa))
    return out


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
