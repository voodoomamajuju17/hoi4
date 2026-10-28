"""Carga y valida spec/.

La validación es agresiva a propósito. El spec es la única fuente editable a
mano, así que es el único lugar donde puede entrar un error humano. Todo lo que
se detecte acá es un error que no llega a error.log.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import SpecError

SPEC_FILES = {
    "project": "00_project.yaml",
    "ideologies": "01_ideologies.yaml",
    "countries": "02_countries.yaml",
    "leaders": "03_leaders.yaml",
    "diplomacy": "04_diplomacy.yaml",
    "ideas": "05_ideas.yaml",
    "mechanics": "06_mechanics.yaml",
    "focus_trees": "07_focus_trees.yaml",
    "territory": "08_territory.yaml",
    "free_countries": "09_free_countries.yaml",
    "legacy": "10_legacy_lore.yaml",
    "scenario": "11_scenario.yaml",
    "events": "12_events.yaml",
    "military": "13_military.yaml",
    "decisions": "14_decisions.yaml",
    "balance": "15_balance.yaml",
    "ai": "16_ai.yaml",
    "research_look": "17_research.yaml",
    "intelligence": "18_intelligence.yaml",
    "unit_names": "19_unit_names.yaml",
    "unique_units": "20_unique_units.yaml",
    "adventures": "21_aventuras.yaml",
    "questions": "99_open_questions.yaml",
}

# Archivos que se suman encima de los anteriores (2026-10-17, segundo análisis
# de rutas): las mecánicas nuevas viven en su propio archivo para no chocar con
# los cambios que se hacen al mismo tiempo en 12_events y 14_decisions.
OVERLAY_FILES = ["22_mecanicas_v4.yaml", "23_rumbo_2120.yaml", "24_japon.yaml"]


def merge_overlay(raw: dict[str, Any], overlay: dict[str, Any], filename: str) -> None:
    """Suma un archivo de mecánicas a lo ya cargado.

    Claves que entiende (todas opcionales):
      decisions: {categories, scripted_effects, dynamic_modifiers} -> se agregan
                 a 14_decisions; variable_names se mezcla.
      extend_scripted_effects: {id: [efectos]} -> se agregan al final de un
                 efecto que ya existe (los pulsos mensuales).
      events: {namespaces: {ns: {country, events}}} -> eventos nuevos en un
                 espacio que ya existe (mismo país) o en uno nuevo.
      leaders: {characters, leader_traits} -> se agregan a 03_leaders.
    Un id repetido es un error: el archivo nuevo nunca pisa lo viejo.
    """
    where = filename

    def add_unique(target: list, items: list, what: str) -> None:
        seen = {x.get("id") for x in target}
        for item in items or []:
            if item.get("id") in seen:
                raise SpecError(f"{what} '{item.get('id')}' ya existe", where=where)
            seen.add(item.get("id"))
            target.append(item)

    dec_new = overlay.get("decisions") or {}
    dec = raw.setdefault("decisions", {})
    all_decisions = [d for c in dec.get("categories") or [] for d in c.get("decisions") or []]
    for cat in dec_new.get("categories") or []:
        add_unique(all_decisions, cat.get("decisions") or [], "decision")
    add_unique(dec.setdefault("categories", []), dec_new.get("categories"), "categoria")
    add_unique(dec.setdefault("scripted_effects", []), dec_new.get("scripted_effects"), "scripted_effect")
    add_unique(dec.setdefault("dynamic_modifiers", []), dec_new.get("dynamic_modifiers"), "dynamic_modifier")
    names = dec.setdefault("variable_names", {})
    for key, value in (dec_new.get("variable_names") or {}).items():
        if key in names:
            raise SpecError(f"variable_names '{key}' ya existe", where=where)
        names[key] = value

    by_id = {e["id"]: e for e in dec.get("scripted_effects") or []}
    for sid, effects in (overlay.get("extend_scripted_effects") or {}).items():
        if sid not in by_id:
            raise SpecError(f"extend_scripted_effects: '{sid}' no existe en 14_decisions", where=where)
        by_id[sid]["effects"] = list(by_id[sid].get("effects") or []) + list(effects or [])

    namespaces = raw.setdefault("events", {}).setdefault("namespaces", {})
    for ns, block in ((overlay.get("events") or {}).get("namespaces") or {}).items():
        if ns in namespaces:
            if namespaces[ns].get("country") != block.get("country"):
                raise SpecError(f"{ns}: el pais no coincide con 12_events", where=where)
            add_unique(namespaces[ns].setdefault("events", []), block.get("events"), f"evento {ns}")
        else:
            namespaces[ns] = block

    # 2026-10-27 (Rumbo a 2120): los incidentes de frontera con la Anarquía
    if overlay.get("anarchy_incidents"):
        if raw.get("anarchy_incidents"):
            raise SpecError("anarchy_incidents ya existe", where=where)
        raw["anarchy_incidents"] = overlay["anarchy_incidents"]
    if overlay.get("power_wars"):
        if raw.get("power_wars"):
            raise SpecError("power_wars ya existe", where=where)
        raw["power_wars"] = overlay["power_wars"]

    # 2026-10-27 (Albión): árboles de focos, nombres cosméticos y ganchos del juego
    trees_new = (overlay.get("focus_trees") or {}).get("trees") or {}
    trees = raw.setdefault("focus_trees", {}).setdefault("trees", {})
    for key, tree in trees_new.items():
        if key in trees:
            raise SpecError(f"arbol de focos '{key}' ya existe", where=where)
        trees[key] = tree
    countries = raw.setdefault("countries", {})
    add_unique(countries.setdefault("cosmetic_tags", []), overlay.get("cosmetic_tags"), "cosmetic_tag")
    hooks = dec_new.get("on_actions") or []
    add_unique(dec.setdefault("on_actions", []), hooks, "on_action")

    leaders_new = overlay.get("leaders") or {}
    leaders = raw.setdefault("leaders", {})
    add_unique(leaders.setdefault("characters", []), leaders_new.get("characters"), "personaje")
    add_unique(leaders.setdefault("leader_traits", []), leaders_new.get("leader_traits"), "rasgo")


# Marcadores de "todavía no lo sabemos". Un emisor que se topa con esto debe
# levantar BlockedError con la Qxxx correspondiente, nunca inventar un default.
UNKNOWN = {"unknown", "not_started", None}


@dataclass
class Country:
    tag: str
    name_en: str
    name_es: str
    adj_en: str
    adj_es: str
    ideology: str
    ideology_group: str
    color: tuple[int, int, int]
    is_major: bool
    is_subject: bool
    overlord: str | None
    capital: str | None
    raw: dict[str, Any]

    @property
    def filename(self) -> str:
        """Nombre del archivo en common/countries/. Sin espacios: los espacios
        en rutas de Paradox funcionan pero complican los scripts."""
        return self.name_en.replace(" ", "_").replace("'", "")


class Spec:
    def __init__(self, root: Path):
        self.root = root
        self.raw: dict[str, Any] = {}
        for name, filename in SPEC_FILES.items():
            path = root / filename
            if not path.exists():
                raise SpecError(f"falta spec/{filename}", where="specload")
            try:
                self.raw[name] = yaml.safe_load(path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                raise SpecError(f"spec/{filename} no parsea: {exc}", where="specload") from exc
        for filename in OVERLAY_FILES:
            path = root / filename
            if path.exists():
                try:
                    overlay = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                except yaml.YAMLError as exc:
                    raise SpecError(f"spec/{filename} no parsea: {exc}", where="specload") from exc
                merge_overlay(self.raw, overlay, filename)
        self.countries: list[Country] = []
        self._build_countries()
        self.validate()

    # -- construcción -------------------------------------------------------

    def _build_countries(self) -> None:
        data = self.raw["countries"]
        for entry in data.get("major_powers", []) or []:
            self.countries.append(self._country(entry, subject=False))
        for entry in data.get("subjects", []) or []:
            self.countries.append(self._country(entry, subject=True))
        for entry in data.get("independents", []) or []:
            self.countries.append(self._country(entry, subject=False))

    def _country(self, entry: dict, *, subject: bool) -> Country:
        tag = entry["tag"]
        name = entry.get("name") or {}
        adj = entry.get("adjective") or {}
        color = entry.get("color_rgb")
        if not color or len(color) != 3:
            raise SpecError(f"{tag}: color_rgb invalido o ausente", where="02_countries.yaml")
        capital = entry.get("capital")
        return Country(
            tag=tag,
            name_en=name.get("english", ""),
            name_es=name.get("spanish", ""),
            adj_en=adj.get("english", ""),
            adj_es=adj.get("spanish", ""),
            ideology=entry.get("ideology", ""),
            ideology_group=entry.get("ideology_group", ""),
            color=tuple(color),  # type: ignore[arg-type]
            is_major=bool(entry.get("is_major")),
            is_subject=subject,
            overlord=entry.get("overlord"),
            capital=None if capital in UNKNOWN else capital,
            raw=entry,
        )

    # -- validación ---------------------------------------------------------

    def validate(self) -> None:
        problems: list[str] = []

        # TAGs
        seen: set[str] = set()
        for c in self.countries:
            if len(c.tag) != 3 or not c.tag.isalpha() or not c.tag.isupper():
                problems.append(
                    f"{c.tag}: los TAG de HOI4 son exactamente 3 letras mayusculas. "
                    f"Ver 00_project.yaml -> AD001"
                )
            if c.tag in seen:
                problems.append(f"{c.tag}: TAG duplicado")
            seen.add(c.tag)
            for field_name, value in (
                ("name.english", c.name_en),
                ("name.spanish", c.name_es),
                ("adjective.english", c.adj_en),
                ("adjective.spanish", c.adj_es),
            ):
                if not value:
                    problems.append(f"{c.tag}: falta {field_name}")
            for channel, value in zip("rgb", c.color):
                if not isinstance(value, int) or not 0 <= value <= 255:
                    problems.append(f"{c.tag}: componente {channel} de color fuera de rango: {value}")

        # Ideologías: todo país tiene que apuntar a un type que exista
        types, groups = self.ideology_index()
        for c in self.countries:
            if c.ideology not in types:
                problems.append(
                    f"{c.tag}: ideologia '{c.ideology}' no definida en 01_ideologies.yaml"
                )
            elif types[c.ideology] != c.ideology_group:
                problems.append(
                    f"{c.tag}: declara ideology_group '{c.ideology_group}' pero "
                    f"'{c.ideology}' vive en el grupo '{types[c.ideology]}'"
                )
            if c.ideology_group not in groups:
                problems.append(f"{c.tag}: grupo ideologico desconocido '{c.ideology_group}'")

        # Overlords
        tags = {c.tag for c in self.countries}
        for c in self.countries:
            if c.is_subject and c.overlord not in tags:
                problems.append(f"{c.tag}: overlord '{c.overlord}' no existe")

        # Diplomacia contra el roster
        for rel in self.raw["diplomacy"].get("subject_relations", []) or []:
            for role in ("overlord", "subject"):
                if rel.get(role) not in tags:
                    problems.append(
                        f"04_diplomacy.yaml: {role} '{rel.get(role)}' no esta en 02_countries.yaml"
                    )

        # Líderes contra el roster
        for ch in self.raw["leaders"].get("characters", []) or []:
            if ch.get("country") not in tags:
                problems.append(f"03_leaders.yaml: pais '{ch.get('country')}' no existe")

        # Coherencia interna del archivo de preguntas
        qids = {q["id"] for q in self.raw["questions"].get("questions", []) or []}
        declared = self.raw["questions"].get("summary", {}).get("total")
        if declared is not None and declared != len(qids):
            problems.append(
                f"99_open_questions.yaml: summary.total dice {declared} pero hay {len(qids)}"
            )

        if problems:
            raise SpecError(
                "el spec tiene " + str(len(problems)) + " problema(s):\n  - " + "\n  - ".join(problems),
                where="specload",
            )

    # -- accesores ----------------------------------------------------------

    def ideology_index(self) -> tuple[dict[str, str], dict[str, dict]]:
        """(type -> grupo, grupo -> definición del grupo)."""
        types: dict[str, str] = {}
        groups: dict[str, dict] = {}
        for group in self.raw["ideologies"].get("groups", []) or []:
            groups[group["key"]] = group
            for t in group.get("types", []) or []:
                if t["key"] in types:
                    raise SpecError(
                        f"01_ideologies.yaml: sub-ideologia duplicada '{t['key']}'", where="specload"
                    )
                types[t["key"]] = group["key"]
        return types, groups

    def country(self, tag: str) -> Country:
        for c in self.countries:
            if c.tag == tag:
                return c
        raise SpecError(f"TAG desconocido: {tag}", where="specload")

    @property
    def project(self) -> dict:
        return self.raw["project"]["project"]

    @property
    def mod_folder(self) -> str:
        return self.project["mod_folder_name"]

    def question(self, qid: str) -> dict | None:
        for q in self.raw["questions"].get("questions", []) or []:
            if q["id"] == qid:
                return q
        return None


def load(root: Path | str = "spec") -> Spec:
    return Spec(Path(root))
