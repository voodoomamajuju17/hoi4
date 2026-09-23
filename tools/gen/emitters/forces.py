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

Solo cuentan los OOB de arranque (1936): los set_naval_oob / set_air_oob
dentro de bloques con fecha (1939...) son de otros bookmarks y duplicarían
todo. Un ala en un state sin base aérea (el juego lo rechaza) se muda a la
base aérea más grande del mismo país; si no tiene ninguna, se descarta.

Lo que queda en territorio de la Anarquía se descarta.

Recorte (13_military.yaml -> forces): sobrevive la fracción `keep`. Barcos:
se recorren en orden y se queda uno de cada 1/keep (así se mantiene la mezcla
de tipos); los task_force y flotas vacíos desaparecen. Solo los países de
`navies` tienen flota. Aviones: cada cantidad se multiplica por keep; si un
país queda con menos de `min_planes`, su entrada más grande se sube hasta
ese piso (sin pasar lo que tenía en 1936). Las variantes que usa
cada archivo (create_equipment_variant en su instant_effect) se copian a cada
país que hereda algo de ese archivo. owner y creator pasan al país nuevo.
"""

from __future__ import annotations

import re
from collections import defaultdict

from ..context import BuildContext
from ..pdx import Block, Quoted, banner_for, parse_file, render
from .military import faction_kind

SOURCE = "flotas y alas vanilla de 1936, reasignadas por 08_territory.yaml"

_DATE_KEY = re.compile(r"^\d{1,4}\.\d{1,2}\.\d{1,2}(\.\d{1,2})?$")


def emit(ctx: BuildContext) -> None:
    assignment = ctx.data.get("territory")
    if ctx.vanilla is None or assignment is None:
        return
    kinds = {c.tag: faction_kind(c) for c in ctx.spec.countries}
    receivers = {t for t, k in kinds.items() if k in ("meganation", "satellite")}
    cut = (ctx.spec.raw.get("military") or {}).get("forces") or {}
    keep = float(cut.get("keep", 1.0))
    navies = set(cut["navies"]) if "navies" in cut else receivers
    min_planes = int(cut.get("min_planes", 0))
    unknown = navies - receivers
    if unknown:
        ctx.warn(f"armada: {', '.join(sorted(unknown))} en forces.navies no es meganacion ni satelite; se ignora.")
    prov_state = {p: s.id for s in ctx.vanilla.states() for p in s.provinces}
    air_base = {s.id: (s.buildings or {}).get("air_base", 0) for s in ctx.vanilla.states()}
    best_base: dict[str, int] = {}
    for sid, tag in sorted(assignment.items()):
        if air_base.get(sid, 0) > air_base.get(best_base.get(tag), 0):
            best_base[tag] = sid

    def owner_of_province(prov) -> str | None:
        sid = prov_state.get(_int(prov))
        tag = assignment.get(sid) if sid is not None else None
        return tag if tag in receivers else None

    def owner_of_state(sid) -> str | None:
        tag = assignment.get(_int(sid))
        return tag if tag in receivers else None

    naval_files, air_files = _vanilla_oob_files(ctx)
    fleets: dict[str, Block] = defaultdict(Block)
    wings: dict[str, dict[int, Block]] = defaultdict(dict)
    variants: dict[str, dict[str, list]] = {"naval": defaultdict(list), "air": defaultdict(list)}
    ships = defaultdict(int)
    planes = defaultdict(int)
    dropped = 0
    moved = 0

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
            if tag is None or tag not in navies:
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
            sid = _int(sid)
            if air_base.get(sid, 0) <= 0:
                if tag not in best_base:
                    dropped += 1
                    continue
                sid = best_base[tag]
                moved += 1
            _retag(wing, tag)
            merged = wings[tag].setdefault(sid, Block())
            merged.entries.extend(wing.entries)
            planes[tag] += _sum_amounts(wing)
            used_by.add(tag)
        for tag in used_by:
            variants["air"][tag].extend(_variants(root))

    before = (sum(ships.values()), sum(planes.values()))
    if keep < 1.0:
        for tag in list(fleets):
            fleets[tag] = _thin_fleets(fleets[tag], keep)
            ships[tag] = _count(fleets[tag], "ship")
            if not ships[tag]:
                del fleets[tag], ships[tag]
        for tag in list(wings):
            planes[tag] = _thin_wings(wings[tag], keep, min_planes)
            wings[tag] = {sid: w for sid, w in wings[tag].items() if w.entries}
            if not wings[tag]:
                del wings[tag], planes[tag]

    ctx.data["naval_oob"] = {}
    ctx.data["air_oob"] = {}
    for tag, block in fleets.items():
        root = Block()
        root.add("units", block)
        _add_variants(root, variants["naval"][tag])
        name = f"{tag}_2100_naval"
        ctx.write_text(f"history/units/{name}.txt", banner_for(SOURCE) + render(root))
        ctx.data["naval_oob"][tag] = name
    for tag, by_state in wings.items():
        block = Block()
        for sid in sorted(by_state):
            block.add(str(sid), by_state[sid])
        root = Block()
        root.add("air_wings", block)
        _add_variants(root, variants["air"][tag])
        name = f"{tag}_2100_air"
        ctx.write_text(f"history/units/{name}.txt", banner_for(SOURCE) + render(root))
        ctx.data["air_oob"][tag] = name
    ctx.data["ships"] = dict(ships)
    ctx.data["planes"] = dict(planes)
    if fleets or wings:
        ctx.note(f"armada y aviacion: {sum(ships.values())} barcos y {sum(planes.values())} aviones "
                 f"(de {before[0]} y {before[1]} heredados de 1936, se queda el {keep:.0%}); "
                 f"flota solo para {', '.join(sorted(navies))}; {dropped} flotas/alas descartadas "
                 f"(Anarquia o sin armada); {moved} alas mudadas a una base aerea propia")
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
        elif isinstance(v, Block) and not _DATE_KEY.match(str(k)):
            _collect(v, key, out)


def _safe_parse(ctx: BuildContext, path):
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
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


def _thin_fleets(fleets: Block, keep: float) -> Block:
    """Se queda uno de cada 1/keep barcos, en orden; borra task_force y flotas vacías."""
    seen = [0]

    def kept() -> bool:
        i = seen[0]
        seen[0] += 1
        return i == 0 or int(i * keep) != int((i + 1) * keep)

    def thin(block: Block) -> Block:
        out = Block()
        for k, v in block.entries:
            if k == "ship":
                if kept():
                    out.add(k, v)
            elif k in ("task_force", "fleet") and isinstance(v, Block):
                sub = thin(v)
                if _count(sub, "ship"):
                    out.add(k, sub)
            else:
                out.add(k, v)
        return out

    return thin(fleets)


def _thin_wings(wings: dict[int, Block], keep: float, min_planes: int) -> int:
    """Multiplica cada cantidad por keep (in place). Devuelve el total que queda."""
    total = 0
    biggest = None  # (original, bloque de equipo)
    for wing in wings.values():
        entries = []
        for k, v in wing.entries:
            amount = v.get("amount") if isinstance(v, Block) else None
            if amount is None:
                entries.append((k, v))
                continue
            original = _int(amount) or 0
            new = int(original * keep)
            if biggest is None or original > biggest[0]:
                biggest = (original, v, wing, k)
            _set(v, "amount", new)
            if new > 0:
                entries.append((k, v))
                total += new
        wing.entries = entries
    if total < min_planes and biggest is not None:
        original, equip, wing, key = biggest
        current = _int(equip.get("amount")) or 0
        target = min(original, current + min_planes - total)
        _set(equip, "amount", target)
        if current == 0:
            wing.entries.append((key, equip))
        total += target - current
    # Un ala que solo conserva el nombre no es un ala.
    for wing in wings.values():
        if not any(isinstance(v, Block) and v.get("amount") is not None for _, v in wing.entries):
            wing.entries = []
    return total


def _set(block: Block, key: str, value: int) -> None:
    for i, (k, _) in enumerate(block.entries):
        if k == key:
            block.entries[i] = (k, str(value))
            return


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
