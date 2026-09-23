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
    "questions": "99_open_questions.yaml",
}

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
