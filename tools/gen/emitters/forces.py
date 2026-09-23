"""Armada y aviación de arranque: herencia de las flotas y alas de 1936.

Produce:
  history/units/<TAG>_2100_naval.txt   flotas + variantes de barcos
  history/units/<TAG>_2100_air.txt     alas aéreas + variantes de aviones
y deja en ctx.data["naval_oob"] / ["air_oob"] los nombres para la historia.

No se inventa ningún barco: los barcos del juego necesitan variantes con
módulos, y un campo mal escrito ahí rompe la carga. Se leen los OOB navales y
aéreos vanilla (los que cada país vanilla carga con set_naval_oob /
set_air_oob; si hay versión de DLC "mtg" y "legacy", se usa la de DLC) y cada
flota o ala pasa al país del mod que ahora tiene su base:

  flota -> dueño del state de su naval_base (o de su primer task_force)
  ala   -> dueño del state donde está basada

Lo que queda en territorio de la Anarquía se descarta. Las variantes que usa
cada archivo (create_equipment_variant en su instant_effect) se copian a cada
país que hereda algo de ese archivo. owner y creator pasan al país nuevo.
"""

from __future__ import annotations

from collections import defaultdict

from ..context import BuildContext
from ..pdx import Block, Quoted, banner_for, parse_file, render
from .military import faction_kind

SOURCE = "flotas y alas vanilla de 1936, reasignadas por 08_territory.yaml"


def emit(ctx: BuildContext) -> None:
    assignment = ctx.data.get("territory")
    if ctx.vanilla is None or assignment is None:
        return
    kinds = {c.tag: faction_kind(c) for c in ctx.spec.countries}
    receivers = {t for t, k in kinds.items() if k in ("meganation", "satellite")}
    prov_state = {p: s.id for s in ctx.vanilla.states() for p in s.provinces}

    def owner_of_province(prov) -> str | None:
        sid = prov_state.get(_int(prov))
        tag = assignment.get(sid) if sid is not None else None
        return tag if tag in receivers else None

    def owner_of_state(sid) -> str | None:
        tag = assignment.get(_int(sid))
        return tag if tag in receivers else None

    naval_files, air_files = _vanilla_oob_files(ctx)
    fleets: dict[str, Block] = defaultdict(Block)
    wings: dict[str, Block] = defaultdict(Block)
    variants: dict[str, dict[str, list]] = {"naval": defaultdict(list), "air": defaultdict(list)}
    ships = defaultdict(int)
    planes = defaultdict(int)
    dropped = 0

    for path in naval_files:
        root = _safe_parse(ctx, path)
        if root is None:
            continue
        units = root.get("units")
        if not isinstance(units, Block):
            continue
        used_by: set[str] = set()
        for key, fleet in units.entries:
            if key != "fleet" or not isinstance(fleet, Block):
                continue
            base = fleet.get("naval_base")
            if base is None:
                tf = fleet.get("task_force")
                base = tf.get("location") if isinstance(tf, Block) else None
            tag = owner_of_province(_text(base)) if base is not None else None
            if tag is None:
                dropped += 1
                continue
            _retag(fleet, tag)
            fleets[tag].add("fleet", fleet)
            ships[tag] += _count(fleet, "ship")
            used_by.add(tag)
        for tag in used_by:
            variants["naval"][tag].extend(_variants(root))

    for path in air_files:
        root = _safe_parse(ctx, path)
        if root is None:
            continue
        air = root.get("air_wings")
        if not isinstance(air, Block):
            continue
        used_by = set()
        for sid, wing in air.entries:
            if not isinstance(wing, Block):
                continue
            tag = owner_of_state(sid)
            if tag is None:
                dropped += 1
                continue
            _retag(wing, tag)
            wings[tag].add(sid, wing)
            planes[tag] += _sum_amounts(wing)
            used_by.add(tag)
        for tag in used_by:
            variants["air"][tag].extend(_variants(root))

    ctx.data["naval_oob"] = {}
    ctx.data["air_oob"] = {}
    for tag, block in fleets.items():
        root = Block()
        root.add("units", block)
        _add_variants(root, variants["naval"][tag])
        name = f"{tag}_2100_naval"
        ctx.write_text(f"history/units/{name}.txt", banner_for(SOURCE) + render(root))
        ctx.data["naval_oob"][tag] = name
    for tag, block in wings.items():
        root = Block()
        root.add("air_wings", block)
        _add_variants(root, variants["air"][tag])
        name = f"{tag}_2100_air"
        ctx.write_text(f"history/units/{name}.txt", banner_for(SOURCE) + render(root))
        ctx.data["air_oob"][tag] = name
    ctx.data["ships"] = dict(ships)
    ctx.data["planes"] = dict(planes)
    if fleets or wings:
        ctx.note(f"armada y aviacion: {sum(ships.values())} barcos y {sum(planes.values())} aviones heredados "
                 f"de 1936; {dropped} flotas/alas en territorio de la Anarquia descartadas")
    elif naval_files or air_files:
        ctx.warn("armada y aviacion: habia OOB vanilla pero ninguna base quedo en manos de un pais del mod.")


# ---------------------------------------------------------------------------


def _vanilla_oob_files(ctx: BuildContext):
    """Archivos de history/units que los países vanilla cargan como naval/aéreo."""
    naval: set[str] = set()
    air: set[str] = set()
    for _, path in ctx.vanilla.country_history_files().items():
        try:
            root = parse_file(path)
        except ValueError:
            continue
        found_n: list[str] = []
        found_a: list[str] = []
        _collect(root, "set_naval_oob", found_n)
        _collect(root, "set_air_oob", found_a)
        mtg = [n for n in found_n if "mtg" in n.lower()]
        naval.update(mtg or [n for n in found_n if "legacy" not in n.lower()])
        air.update(found_a)
    units_dir = ctx.vanilla.root / "history" / "units"
    to_paths = lambda names: [units_dir / f"{n}.txt" for n in sorted(names) if (units_dir / f"{n}.txt").exists()]
    return to_paths(naval), to_paths(air)


def _collect(block: Block, key: str, out: list[str]) -> None:
    for k, v in block.entries:
        if k == key and not isinstance(v, Block):
            out.append(_text(v))
        elif isinstance(v, Block):
            _collect(v, key, out)


def _safe_parse(ctx: BuildContext, path):
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    import re
    if re.search(r'^[^#"\n]*[<>]', raw, re.MULTILINE):
        ctx.warn(f"{path.name}: usa comparaciones; no lo reasigno.")
        return None
    try:
        return parse_file(path)
    except ValueError:
        ctx.warn(f"{path.name}: no parsea; sus unidades no se heredan.")
        return None


def _retag(block: Block, tag: str) -> None:
    for i, (k, v) in enumerate(block.entries):
        if k in ("owner", "creator") and not isinstance(v, Block):
            block.entries[i] = (k, Quoted(tag) if isinstance(v, Quoted) else tag)
        elif isinstance(v, Block):
            _retag(v, tag)


def _variants(root: Block) -> list[tuple[str, Block]]:
    """Entradas de instant_effect que definen variantes (o bloques if con variantes)."""
    effect = root.get("instant_effect")
    if not isinstance(effect, Block):
        return []
    out = []
    for k, v in effect.entries:
        if k == "create_equipment_variant" or (isinstance(v, Block) and _has(v, "create_equipment_variant")):
            out.append((k, v))
    return out


def _has(block: Block, key: str) -> bool:
    return any(k == key or (isinstance(v, Block) and _has(v, key)) for k, v in block.entries)


def _add_variants(root: Block, entries: list[tuple[str, Block]]) -> None:
    if not entries:
        return
    seen: set[str] = set()
    effect = Block()
    for k, v in entries:
        sig = render(Block([(k, v)]))
        if sig in seen:
            continue
        seen.add(sig)
        effect.add(k, v)
    root.add("instant_effect", effect)


def _count(block: Block, key: str) -> int:
    return sum(1 if k == key else _count(v, key) if isinstance(v, Block) else 0 for k, v in block.entries)


def _sum_amounts(block: Block) -> int:
    total = 0
    for k, v in block.entries:
        if isinstance(v, Block):
            amount = v.get("amount")
            if amount is not None:
                total += _int(amount) or 0
    return total


def _text(v) -> str:
    return str(getattr(v, "text", v))


def _int(v) -> int | None:
    try:
        return int(_text(v))
    except (TypeError, ValueError):
        return None
