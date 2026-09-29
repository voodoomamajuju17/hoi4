"""Organizaciones industriales militares propias (spec/13_military.yaml -> mio).

Cada OIM genérica del juego (common/military_industrial_organization/
organizations, ids que empiezan con generic_) se copia una vez por meganación
con el nombre de esa potencia (mismos rasgos, mismo ícono) y la genérica deja
de estar disponible para las 8 meganaciones, así no aparecen repetidas.

Además, para el reporte: de dónde salen los puntos con los que arrancan las
OIM (usos de *mio_size* en el juego y lo que dice documentation/).
"""

from __future__ import annotations

import copy
import re

from ..context import BuildContext
from ..pdx import Block, parse_file

SOURCE = "spec/13_military.yaml -> mio"
LOC_FILE = "meganations_mio"
MEGAS = ["EFE", "FCU", "ASC", "HSN", "NAS", "SHD", "APF", "NRE"]


def emit(ctx: BuildContext) -> None:
    spec = (ctx.spec.raw.get("military") or {}).get("mio")
    if not spec or ctx.vanilla is None:
        return
    folder = ctx.vanilla.root / "common" / "military_industrial_organization" / "organizations"
    if not folder.is_dir():
        ctx.warn("OIM: el juego no tiene common/military_industrial_organization/organizations; no se personalizan.")
        return
    _diagnose(ctx, folder)
    _personalize(ctx, spec, folder)


def _category(mio_id: str, categories: dict) -> str | None:
    # por partes del id ("repair" no es "air"): generic_light_aircraft -> light, aircraft
    low = f"_{mio_id.lower()}_"
    for cat, words in categories.items():
        if any(f"_{w}_" in low for w in words):
            return cat
    return None


def _personalize(ctx: BuildContext, spec: dict, folder) -> None:
    names = spec.get("names") or {}
    categories = spec.get("categories") or {}
    megas = [t for t in MEGAS if t in names]
    ours = Block()
    touched = 0
    used: dict[str, str] = {}
    for path in sorted(folder.glob("*.txt")):
        try:
            root = parse_file(path)
        except ValueError:
            continue
        changed = False
        for key, body in root.entries:
            if not key or not key.startswith("generic_") or not isinstance(body, Block):
                continue
            cat = _category(key, categories)
            if cat is None or cat in used:
                continue
            used[cat] = key
            # la genérica deja de estar para las meganaciones
            allowed = body.get("allowed")
            if not isinstance(allowed, Block):
                allowed = Block()
                body.add("allowed", allowed)
            allowed.add("NOT", Block([("OR", Block([("original_tag", t) for t in megas]))]))
            changed = True
            # una copia por meganación, con su nombre
            for tag in megas:
                name = names[tag].get(cat)
                if not name:
                    continue
                new_id = f"{tag}_{key[len('generic_'):]}"
                copy_body = copy.deepcopy(body)
                copy_body.entries = [(k, v) for k, v in copy_body.entries if k != "allowed"]
                copy_body.entries.insert(0, ("allowed", Block([("original_tag", tag)])))
                if copy_body.get("name") is not None:
                    copy_body.entries = [(k, new_id if k == "name" else v) for k, v in copy_body.entries]
                ours.add(new_id, copy_body)
                ctx.loc.define_and_reference(new_id, en=name, es=name, file=LOC_FILE, origin=f"mio:{new_id}")
        if changed:
            touched += 1
            ctx.write_script(f"common/military_industrial_organization/organizations/{path.name}", root,
                             source=f"{path.name} del juego: las OIM genericas ya no aparecen para las meganaciones")
    if ours.entries:
        ctx.write_script("common/military_industrial_organization/organizations/meganations_mio.txt", ours,
                         source=SOURCE)
    ctx.note(f"OIM: {len(ours)} propias ({', '.join(f'{c}={k}' for c, k in sorted(used.items()))}) "
             f"en {touched} archivos del juego")


def _diagnose(ctx: BuildContext, folder) -> None:
    """¿De dónde salen los puntos de arranque? Usos de mio_size en el juego y
    su sintaxis según documentation/."""
    root = ctx.vanilla.root
    hits: list[str] = []
    pattern = re.compile(r"\b\w*mio\w*size\w*\s*=\s*(\{[^{}]{0,80}\}|\S+)")
    for base in ("history", "common/on_actions", "common/scripted_effects", "events", "common/national_focus"):
        for path in sorted((root / base).rglob("*.txt")):
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            for m in pattern.finditer(text):
                hits.append(f"{path.relative_to(root).as_posix()}: {' '.join(m.group(0).split())}")
                if len(hits) >= 12:
                    break
            if len(hits) >= 12:
                break
    for h in hits:
        ctx.note(f"OIM (uso en el juego): {h}")
    first = None
    for path in sorted(folder.glob("*.txt")):
        try:
            r = parse_file(path)
        except ValueError:
            continue
        for key, body in r.entries:
            if key and key.startswith("generic_") and isinstance(body, Block):
                first = (key, body.keys())
                break
        if first:
            break
    if first:
        ctx.note(f"OIM (claves de {first[0]}): {', '.join(first[1])}")
    doc = root / "documentation"
    for path in sorted(doc.glob("*effects*")) + sorted(doc.glob("*triggers*")):
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines):
            if re.match(r"^#+\s*\w*mio\w*size\w*", line, re.I):
                snippet = " | ".join(x.strip() for x in lines[i:i + 6] if x.strip())
                ctx.note(f"OIM (documentacion {path.name}): {snippet[:300]}")
