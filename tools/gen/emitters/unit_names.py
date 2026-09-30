"""Nombres de divisiones y de barcos por facción (spec/19_unit_names.yaml).

Produce:
  common/units/names_divisions/meganations_names_divisions.txt
  common/units/names_ships/meganations_names_ships.txt

HOI4 elige la lista de una plantilla por su batallón principal
(`division_types`) y la de un barco por su casco (`ship_types`). Los ids se
validan contra el juego instalado: los que no existen se omiten con aviso, y
una lista sin ningún id válido no se escribe.
"""

from __future__ import annotations

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted, inline_list

SOURCE = "spec/19_unit_names.yaml"
LOC_FILE = "meganations_unit_names"
DIVISIONS_FILE = "common/units/names_divisions/meganations_names_divisions.txt"
SHIPS_FILE = "common/units/names_ships/meganations_names_ships.txt"


def roman(n: int) -> str:
    out = ""
    for value, sym in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
                       (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out += sym
            n -= value
    return out


def ordinal_en(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def _types(kind: str, spec: dict, section: str, all_key: str, known: set[str] | None,
           where: str, report: dict) -> list[str]:
    table = spec.get(section) or {}
    kinds = (spec.get(all_key) or list(table)) if kind == "all" else [kind]
    ids: list[str] = []
    for k in kinds:
        if k not in table:
            raise SpecError(f"{where}: tipo '{k}' no esta en unit_names.{section}", where=SOURCE)
        for i in table[k]:
            if known is not None and i not in known:
                continue
            if i not in ids:
                ids.append(i)
    if known is not None:
        report.setdefault(section, (set(), []))
        report[section][0].update(i for k in kinds for i in table[k] if i not in known)
        if not ids:
            report[section][1].append(where)
    return ids


def _check_names(names, where: str) -> list[str]:
    if not names or not all(isinstance(n, str) and n.strip() for n in names):
        raise SpecError(f"{where}: 'names' vacio o con nombres que no son texto", where=SOURCE)
    seen: set[str] = set()
    for n in names:
        if n in seen:
            raise SpecError(f"{where}: nombre repetido '{n}'", where=SOURCE)
        seen.add(n)
    return list(names)


def build_blocks(spec: dict, known_units: set[str] | None, known_ships: set[str] | None):
    """(divisiones, barcos, loc, report). `known_*` None = no validar.
    report: seccion -> (ids que el juego no tiene, listas que quedaron vacias)."""
    divisions, ships = Block(), Block()
    loc: list[tuple[str, str, str]] = []
    report: dict[str, tuple[set[str], list[str]]] = {}

    for tag, groups in (spec.get("divisions") or {}).items():
        for kind, g in groups.items():
            where = f"divisions.{tag}.{kind}"
            ids = _types(kind, spec, "division_types", "all_divisions", known_units, where, report)
            if not ids:
                continue
            names = _check_names(g.get("names"), where)
            pattern, fallback = g.get("pattern"), g.get("fallback")
            if not pattern or "{name}" not in pattern or not fallback or "%d" not in fallback:
                raise SpecError(f"{where}: falta pattern con {{name}} o fallback con %d", where=SOURCE)
            key = f"{tag}_DIVNAMES_{kind.upper()}"
            ordered = Block()
            for n, name in enumerate(names, start=1):
                text = pattern.format(n=n, roman=roman(n), nth=ordinal_en(n), name=name)
                ordered.add(str(n), inline_list(Quoted(text)))
            body = Block()
            body.add("name", key)
            body.add("for_countries", inline_list(tag))
            body.add("can_use", Block([("always", True)]))
            body.add("division_types", inline_list(*(Quoted(i) for i in ids)))
            body.add("fallback_name", Quoted(fallback))
            body.add("ordered", ordered)
            divisions.add(f"{tag}_DIV_{kind.upper()}", body)
            loc.append((key, g["group"]["en"], g["group"]["es"]))

    for tag, groups in (spec.get("ships") or {}).items():
        used: dict[str, str] = {}
        for kind, g in groups.items():
            where = f"ships.{tag}.{kind}"
            names = _check_names(g.get("names"), where)
            for n in names:
                if n in used:
                    raise SpecError(f"{where}: '{n}' ya esta en ships.{tag}.{used[n]}", where=SOURCE)
                used[n] = kind
            ids = _types(kind, spec, "ship_types", "all_ships", known_ships, where, report)
            if not ids:
                continue
            if not g.get("fallback") or "%d" not in g["fallback"]:
                raise SpecError(f"{where}: falta fallback con %d", where=SOURCE)
            key = f"{tag}_SHIPNAMES_{kind.upper()}"
            body = Block()
            body.add("name", key)
            body.add("for_countries", inline_list(tag))
            body.add("type", "ship")
            body.add("ship_types", inline_list(*ids))
            body.add("fallback_name", Quoted(g["fallback"]))
            body.add("unique", Block([(None, Quoted(n)) for n in names]))
            ships.add(f"{tag}_SHIP_{kind.upper()}", body)
            loc.append((key, g["group"]["en"], g["group"]["es"]))

    return divisions, ships, loc, report


def emit(ctx: BuildContext) -> None:
    spec = (ctx.spec.raw.get("unit_names") or {}).get("unit_names") or {}
    if not spec:
        return
    tags = {c.tag for c in ctx.spec.countries}
    for section in ("divisions", "ships"):
        unknown = sorted(set(spec.get(section) or {}) - tags)
        if unknown:
            raise SpecError(f"unit_names.{section}: paises que no existen: {', '.join(unknown)}", where=SOURCE)
    known_units = known_ships = None
    if ctx.vanilla is not None:
        known_units = ctx.vanilla.sub_units() or None
        known_ships = set(ctx.vanilla.equipment()) or None
    divisions, ships, loc, report = build_blocks(spec, known_units, known_ships)
    for section, (ids, empty) in report.items():
        if ids:
            ctx.warn(f"nombres de unidades: {section} que el juego no tiene (se omiten): {', '.join(sorted(ids))}"
                     + (f"; {len(empty)} listas quedan sin escribir" if empty else ""))
    for key, en, es in loc:
        ctx.loc.define_and_reference(key, en=en, es=es, file=LOC_FILE, origin=f"unit_names:{key}")
    if len(divisions):
        ctx.write_script(DIVISIONS_FILE, divisions, source=SOURCE)
    if len(ships):
        ctx.write_script(SHIPS_FILE, ships, source=SOURCE)
    ctx.note(f"nombres de unidades: {len(divisions)} listas de divisiones, {len(ships)} de barcos")
