"""Emblemas de las ocho facciones de las meganaciones (2026-11-15, llegaron los 8 medallones).

assets/ui/facciones/faccion_<TAG>.dds (100 x 100, dos cuadros, como los del juego) y
faccion_<TAG>_mini.dds (32 x 32, la barra de arriba) -> sprites GFX_faction_logo_mn_<TAG> y
GFX_faction_logo_mn_<TAG>_miniature (el mismo esquema de nombres que interface/factions/factions.gfx).

Desde el 2026-11-15 (llegó common/factions del juego): el emblema lo pone la plantilla de la facción
(common/factions/templates, `icon = ...`), y una facción usa plantilla solo si se crea con
create_faction_from_template. La forma exacta de ese efecto no está en la documentación del juego,
así que se aprende al armar: se busca un uso real en los archivos del juego instalado (historia,
eventos, focos, decisiones, efectos) y se copia. Si no aparece ninguno, la facción se crea como
siempre (create_faction, con el emblema genérico) y se avisa: nunca se adivina.
"""

from __future__ import annotations

import re

from ..context import BuildContext

ARTE = "assets/ui/facciones"
TEX = "gfx/interface/factions/faction_logos/meganations"
TAGS = ("EFE", "FCU", "ASC", "HSN", "NAS", "SHD", "APF", "NRE")


# meta principal de cada facción (metas regionales del juego, sin país fijo)
MANIFIESTO = {
    "EFE": "faction_manifest_pan_americanism", "FCU": "faction_manifest_pan_americanism",
    "NAS": "faction_manifest_pan_americanism", "ASC": "faction_manifest_european_dominance",
    "NRE": "faction_manifest_european_dominance", "HSN": "faction_manifest_asian_dominance",
    "SHD": "faction_manifest_asian_dominance", "APF": "faction_manifest_african_domination",
}
_USO = re.compile(r"create_faction_from_template\s*=\s*(\{[^{}]*\}|[A-Za-z0-9_\.]+)")
_CARPETAS = ("history", "events", "common/national_focus", "common/decisions", "common/scripted_effects", "common/on_actions")


def plantilla(tag: str) -> str:
    return f"faction_template_mn_{tag}"


def forma(ctx: BuildContext) -> dict | None:
    """Cómo escribe el juego create_faction_from_template: {"bloque": bool, "clave": clave de la
    plantilla, "nombre": clave del nombre o None}. None si el juego no trae plantillas o ningún uso."""
    if "facciones_forma" in ctx.data:
        return ctx.data["facciones_forma"]
    res = None
    raiz = ctx.vanilla.root if ctx.vanilla else None
    if raiz is not None and (raiz / "common/factions/templates").is_dir():
        for carpeta in _CARPETAS:
            for f in sorted((raiz / carpeta).rglob("*.txt")) if (raiz / carpeta).is_dir() else []:
                try:
                    m = _USO.search(f.read_text(encoding="utf-8-sig", errors="replace"))
                except OSError:
                    continue
                if not m:
                    continue
                v = m.group(1)
                if not v.startswith("{"):
                    res = {"bloque": False, "clave": None, "nombre": None, "visto": f.name}
                else:
                    pares = dict(re.findall(r"(\w+)\s*=\s*\"?([^\s\"{}]+)\"?", v))
                    clave = next((k for k, x in pares.items() if x.startswith("faction_template")), None)
                    if clave is None and "template" in pares:
                        clave = "template"
                    if clave:
                        res = {"bloque": True, "clave": clave, "nombre": "name" if "name" in pares else None,
                               "visto": f.name}
                if res:
                    break
            if res:
                break
    ctx.data["facciones_forma"] = res
    return res


def crear(ctx: BuildContext, tag: str, nombre: str) -> tuple[str, object]:
    """El efecto que crea la facción de `tag` (lo usa emitters/history.py)."""
    base = ctx.spec.root.parent / ARTE
    fm = forma(ctx)
    if tag not in MANIFIESTO or fm is None or not (base / f"faccion_{tag}.dds").exists():
        return ("create_faction", nombre)
    ctx.data.setdefault("facciones_plantillas", {})[tag] = nombre
    if not fm["bloque"]:
        return ("create_faction_from_template", plantilla(tag))
    from ..pdx import Block
    b = Block([(fm["clave"], plantilla(tag))])
    if fm["nombre"]:
        b.add(fm["nombre"], nombre)
    return ("create_faction_from_template", b)


def emit(ctx: BuildContext) -> None:
    base = ctx.spec.root.parent / ARTE
    hay = [t for t in TAGS if (base / f"faccion_{t}.dds").exists() and (base / f"faccion_{t}_mini.dds").exists()]
    if not hay:
        return
    g = ["# Generado por tools/gen/emitters/facciones.py: emblemas de facción de las meganaciones\nspriteTypes = {\n"]
    for t in hay:
        for suf, nombre, cuadros in (("", f"GFX_faction_logo_mn_{t}", 2), ("_mini", f"GFX_faction_logo_mn_{t}_miniature", 1)):
            ctx.copy_asset(f"{ARTE}/faccion_{t}{suf}.dds", f"{TEX}/faccion_{t}{suf}.dds")
            g.append(f'\tspriteType = {{\n\t\tname = "{nombre}"\n\t\ttexturefile = "{TEX}/faccion_{t}{suf}.dds"\n'
                     + (f"\t\tnoOfFrames = {cuadros}\n" if cuadros > 1 else "") + "\t}\n")
    g.append("}\n")
    ctx.write_text("interface/meganations_facciones.gfx", "".join(g))
    usadas = {t: n for t, n in (ctx.data.get("facciones_plantillas") or {}).items() if t in hay}
    if not usadas:
        ctx.warn("facciones: este juego no muestra cómo usar create_faction_from_template; las facciones "
                 "se crean como siempre y el emblema queda el genérico")
        return
    p = ["# Generado por tools/gen/emitters/facciones.py: una plantilla por facción de meganación, con su\n"
         "# emblema. Solo desde el guion (visible = no): las crea la historia de cada líder.\n"]
    for t, nombre in usadas.items():
        p.append(f"{plantilla(t)} = {{\n\tname = {nombre}\n\tmanifest = {MANIFIESTO[t]}\n"
                 f"\ticon = GFX_faction_logo_mn_{t}\n\tcan_leader_join_other_factions = no\n"
                 "\tvisible = { always = no }\n"
                 "\tgoals = {\n\t\tfaction_goal_a_military_base\n\t\tfaction_goal_the_atomic_race\n\t}\n}\n\n")
    ctx.write_text("common/factions/templates/meganations_factions.txt", "".join(p))
    ctx.note(f"facciones: {len(usadas)} con su emblema ({', '.join(usadas)}), "
             f"create_faction_from_template como en {ctx.data['facciones_forma']['visto']}")
