"""Planilla de beneficios por árbol de focos (pedido del usuario, 2026-10-13:
"hacé el cálculo, la suma total de los beneficios que da cada árbol de foco,
quiero compararlos y equilibrar a mano").

    python3 -m tools.focos_balance            -> balance/focos_comparacion.xlsx

Lee spec/07_focus_trees.yaml (y las ideas, los espíritus vivos y los cazas
gratis) y suma, foco por foco, lo que da cada recompensa. Hojas:

  Por foco        una fila por foco con cada beneficio
  Resumen         una fila por árbol: totales con fórmulas sobre "Por foco"
                  y un puntaje con los pesos de "Pesos" (editables)
  Por rama        lo mismo por rama
  Espíritus       suma neta de los modificadores de los espíritus que dejan
                  los focos (agregados - quitados), por árbol
  Pesos           cuánto vale cada beneficio para el puntaje (celdas amarillas)

Supuestos (también en la hoja Notas): se cuentan TODOS los focos, aunque
algunos sean excluyentes; un `states` al azar es 1 región; dentro de un `if`
cuenta lo de `then`; un `random` cuenta el promedio pesado de sus opciones.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "spec"
OUT = REPO / "balance" / "focos_comparacion.xlsx"

# columnas numéricas de "Por foco" (clave interna, título)
COLS = [
    ("dias", "Días"),
    ("pp", "Poder político"),
    ("estab", "Estabilidad (%)"),
    ("guerra", "Apoyo a la guerra (%)"),
    ("manpower", "Mano de obra"),
    ("exp_ej", "Exp. ejército"),
    ("exp_nav", "Exp. naval"),
    ("exp_aire", "Exp. aérea"),
    ("slots", "Casillas de investigación"),
    ("tech", "Bonos de tecnología (usos)"),
    ("civ", "Fábricas civiles"),
    ("mil", "Fábricas militares"),
    ("dock", "Astilleros"),
    ("infra", "Infraestructura"),
    ("otros_edif", "Otros edificios (niveles)"),
    ("equipo", "Equipo (unidades)"),
    ("divisiones", "Divisiones"),
    ("cazas", "Cazas gratis"),
    ("territorio", "Reclamos, núcleos y objetivos"),
    ("espiritus", "Espíritus (agregados)"),
]
BUILD = {"industrial_complex": "civ", "arms_factory": "mil", "dockyard": "dock", "infrastructure": "infra"}

# pesos por defecto del puntaje (editables en la hoja Pesos)
WEIGHTS = {
    "pp": 1, "estab": 10, "guerra": 8, "manpower": 0.002, "exp_ej": 1, "exp_nav": 1, "exp_aire": 1,
    "slots": 300, "tech": 25, "civ": 100, "mil": 80, "dock": 60, "infra": 15, "otros_edif": 10,
    "equipo": 0.02, "divisiones": 40, "cazas": 0.5, "territorio": 20, "espiritus": 0, "dias": 0,
}

# pesos por defecto de los modificadores de los espíritus (puntos por 1,0 del
# modificador, o sea por +100%); editables en la hoja Espíritus. Inventados
# para comparar con la misma vara que la hoja Pesos: p. ej. +0,1 PP diario
# durante ~2 años son ~73 PP, de ahí 730 por cada 1,0.
MOD_WEIGHTS = {
    "political_power_gain": 730, "stability_factor": 1000, "war_support_factor": 800,
    "industrial_capacity_factory": 3000, "industrial_capacity_dockyard": 1500,
    "production_speed_buildings_factor": 1500, "production_speed_arms_factory_factor": 500,
    "production_speed_infrastructure_factor": 300, "research_speed_factor": 1500,
    "consumer_goods_factor": -3000, "local_resources_factor": 1000, "monthly_population": 300,
    "recruitable_population_factor": 3000, "trade_opinion_factor": 100, "democratic_drift": 0,
    "army_attack_factor": 1500, "army_defence_factor": 1200, "army_org_factor": 1000,
    "army_armor_attack_factor": 500, "army_armor_defence_factor": 500, "experience_gain_army": 300,
    "navy_org_factor": 500, "experience_gain_air": 200, "air_attack_factor": 400, "air_defence_factor": 400,
    "air_agility_factor": 400, "air_superiority_efficiency": 400, "air_interception_detect_factor": 200,
    "air_ace_bonuses_factor": 100, "air_ace_generation_chance_factor": 100,
}


def _load(name: str) -> dict:
    return yaml.safe_load((SPEC / name).read_text(encoding="utf-8"))


def _ideas() -> dict[str, dict]:
    out: dict[str, dict] = {}

    def walk(o):
        if isinstance(o, dict):
            if "id" in o and isinstance(o.get("modifiers"), dict):
                out[o["id"]] = {str(k).lstrip("?"): v for k, v in o["modifiers"].items()}
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(_load("05_ideas.yaml"))
    for m in (_load("14_decisions.yaml").get("dynamic_modifiers") or []):
        out[m["id"]] = {str(k).lstrip("?"): v for k, v in (m.get("modifiers") or {}).items()
                        if isinstance(v, (int, float)) and not isinstance(v, bool)}
    return out


def _tally(items, row: dict, mods: dict, ideas: dict, texts: dict, weight: float = 1.0) -> None:
    for it in items or []:
        if not isinstance(it, dict):
            continue
        e = it.get("effect")
        v = it.get("value")
        if e == "add_political_power":
            row["pp"] += weight * float(v)
        elif e == "add_stability":
            row["estab"] += weight * float(v) * 100
        elif e == "add_war_support":
            row["guerra"] += weight * float(v) * 100
        elif e == "add_manpower":
            row["manpower"] += weight * float(v)
        elif e == "army_experience":
            row["exp_ej"] += weight * float(v)
        elif e == "navy_experience":
            row["exp_nav"] += weight * float(v)
        elif e == "air_experience":
            row["exp_aire"] += weight * float(v)
        elif e == "add_research_slot":
            row["slots"] += weight * float(v or 1)
        elif e == "tech_bonus":
            row["tech"] += weight * float(it.get("uses", 1))
        elif e in ("build", "build_here"):
            key = BUILD.get(it.get("building"), "otros_edif")
            row[key] += weight * float(it.get("level", 1))
        elif e == "equipment" and float(it.get("amount", 0)) > 0:
            row["equipo"] += weight * float(it["amount"])
        elif e == "create_units":
            row["divisiones"] += weight * float(it.get("count", 1))
        elif e in ("claim", "or_cores", "wargoal", "wargoal_holders", "core"):
            row["territorio"] += weight
        elif e in ("add_ideas", "timed_idea", "dynamic_modifier"):
            iid = it.get("value") or it.get("idea") or it.get("id")
            temporal = e == "timed_idea" or bool(it.get("days"))
            row["espiritus"] += weight
            texts["ideas"].append(f"{iid}{' (temporal)' if temporal else ''}")
            if not temporal:
                for k, x in (ideas.get(iid) or {}).items():
                    if isinstance(x, (int, float)):
                        mods[k] += weight * x
        elif e == "swap_ideas":
            row["espiritus"] += weight
            texts["ideas"].append(f"{it.get('remove')} -> {it.get('add')}")
            for k, x in (ideas.get(it.get("add")) or {}).items():
                if isinstance(x, (int, float)):
                    mods[k] += weight * x
            for k, x in (ideas.get(it.get("remove")) or {}).items():
                if isinstance(x, (int, float)):
                    mods[k] -= weight * x
        elif e == "remove_idea":
            texts["ideas"].append(f"- {v}")
            for k, x in (ideas.get(v) or {}).items():
                if isinstance(x, (int, float)):
                    mods[k] -= weight * x
        elif e in ("add_variable",) and it.get("var"):
            texts["mecanica"].append(f"{it['var']} {float(v):+g}")
        if e in ("states", "in_state", "capital", "every_country", "country"):
            _tally(it.get("effects"), row, mods, ideas, texts, weight)
        elif e == "if":
            _tally(it.get("then"), row, mods, ideas, texts, weight)
        elif e == "random":
            opts = it.get("options") or []
            total = sum(float(o.get("weight", 1)) for o in opts) or 1
            for o in opts:
                _tally(o.get("effects"), row, mods, ideas, texts, weight * float(o.get("weight", 1)) / total)


def collect() -> tuple[list[dict], dict, list[str]]:
    trees = _load("07_focus_trees.yaml")["trees"]
    ideas = _ideas()
    fighters = (_load("13_military.yaml").get("free_fighters") or {}).get("focuses") or {}
    rows: list[dict] = []
    tree_mods: dict[str, dict] = {}
    for tag, tree in trees.items():
        if not isinstance(tree, dict) or "branches" not in tree:
            continue
        mods_tree: dict = defaultdict(float)
        for branch in tree["branches"]:
            for f in branch.get("focuses") or []:
                row = {k: 0.0 for k, _ in COLS}
                row["dias"] = float(f.get("days", 0))
                texts = {"ideas": [], "mecanica": []}
                _tally(f.get("reward"), row, mods_tree, ideas, texts)
                row["cazas"] += float(fighters.get(f["id"], 0))
                excl = f.get("mutually_exclusive") or []
                rows.append({"arbol": tag, "rama": branch.get("id", ""), "foco": f["id"],
                             "nombre": (f.get("name") or {}).get("spanish", ""), **row,
                             "ideas": ", ".join(texts["ideas"]), "mecanica": ", ".join(texts["mecanica"]),
                             "excluye": ", ".join(excl) if isinstance(excl, list) else str(excl)})
        tree_mods[tag] = dict(mods_tree)
    order = list(dict.fromkeys(r["arbol"] for r in rows))
    return rows, tree_mods, order


def write(path: Path = OUT) -> Path:
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    rows, tree_mods, order = collect()
    font = Font(name="Arial", size=10)
    bold = Font(name="Arial", size=10, bold=True)
    blue = Font(name="Arial", size=10, color="0000FF")
    head_fill = PatternFill("solid", fgColor="DDE3EA")
    yellow = PatternFill("solid", fgColor="FFFF00")
    wb = Workbook()

    # ---- Por foco
    ws = wb.active
    ws.title = "Por foco"
    heads = ["Árbol", "Rama", "Foco", "Nombre"] + [t for _, t in COLS] + ["Espíritus (detalle)", "Mecánica", "Excluye a"]
    ws.append(heads)
    for r in rows:
        ws.append([r["arbol"], r["rama"], r["foco"], r["nombre"]] + [round(r[k], 3) for k, _ in COLS]
                  + [r["ideas"], r["mecanica"], r["excluye"]])
    n = len(rows) + 1
    col_of = {k: get_column_letter(5 + i) for i, (k, _) in enumerate(COLS)}

    # ---- Pesos
    wp = wb.create_sheet("Pesos")
    wp.append(["Beneficio", "Peso (puntos por unidad)", "Qué significa"])
    meaning = {
        "pp": "1 punto por cada poder político", "estab": "por cada 1% de estabilidad",
        "guerra": "por cada 1% de apoyo a la guerra", "manpower": "por cada hombre (500 hombres = 1 punto)",
        "slots": "por cada casilla de investigación", "tech": "por cada uso de bono de tecnología",
        "civ": "por cada fábrica civil", "mil": "por cada fábrica militar", "dock": "por cada astillero",
        "equipo": "por cada unidad de equipo (50 = 1 punto)", "divisiones": "por cada división",
        "cazas": "por cada caza", "espiritus": "0: los espíritus se valoran por sus efectos, con los pesos de la hoja Espíritus",
        "dias": "0: los días no suman puntos",
    }
    for k, t in COLS:
        wp.append([t, WEIGHTS[k], meaning.get(k, "")])
    for row in wp.iter_rows(min_row=2, max_row=len(COLS) + 1, min_col=2, max_col=2):
        for c in row:
            c.fill = yellow
            c.font = blue
    wp["B1"].comment = Comment("Pesos inventados para comparar, no salen del juego: cambialos y el puntaje "
                               "del Resumen se recalcula.", "2100 Meganations")
    weight_row = {k: i + 2 for i, (k, _) in enumerate(COLS)}

    # ---- Resumen (fórmulas)
    wr = wb.create_sheet("Resumen", 0)
    wr.append(["Árbol", "Focos"] + [t for _, t in COLS]
              + ["Puntaje en el acto (Pesos)", "Puntaje de espíritus (Espíritus)", "Puntaje total"])
    for i, tag in enumerate(order, start=2):
        wr.cell(i, 1, tag)
        wr.cell(i, 2, f"=COUNTIF('Por foco'!$A$2:$A${n},$A{i})")
        for j, (k, _) in enumerate(COLS):
            col = col_of[k]
            wr.cell(i, 3 + j, f"=SUMIFS('Por foco'!${col}$2:${col}${n},'Por foco'!$A$2:$A${n},$A{i})")
        terms = [f"{get_column_letter(3 + j)}{i}*Pesos!$B${weight_row[k]}" for j, (k, _) in enumerate(COLS)]
        wr.cell(i, 3 + len(COLS), "=" + "+".join(terms))
    m = len(order) + 1
    score_L = get_column_letter(3 + len(COLS))
    spirit_L = get_column_letter(4 + len(COLS))
    total_L = get_column_letter(5 + len(COLS))
    # ---- Espíritus (suma neta de modificadores por árbol, con pesos editables)
    we = wb.create_sheet("Espíritus", 2)
    keys = sorted({k for mods in tree_mods.values() for k, v in mods.items() if abs(v) > 1e-9})
    we.append(["Modificador", "Peso (por +100%)"] + order)
    for k in keys:
        we.append([k, MOD_WEIGHTS.get(k, 0)] + [round(tree_mods.get(t, {}).get(k, 0.0), 4) for t in order])
    for row in we.iter_rows(min_row=2, max_row=len(keys) + 1, min_col=2, max_col=2):
        for c in row:
            c.fill = yellow
            c.font = blue
    we["B1"].comment = Comment("Pesos inventados para comparar, no salen del juego: puntos por cada +1,0 "
                               "(+100%) del modificador. Cambialos y el puntaje se recalcula.", "2100 Meganations")
    k_last = len(keys) + 1
    spirit_total_row = k_last + 1
    we.cell(spirit_total_row, 1, "Puntaje de espíritus")
    for j, _ in enumerate(order):
        L = get_column_letter(3 + j)
        we.cell(spirit_total_row, 3 + j, f"=SUMPRODUCT($B$2:$B${k_last},{L}2:{L}{k_last})")
    for i, _ in enumerate(order, start=2):
        L = get_column_letter(3 + i - 2)
        wr.cell(i, 4 + len(COLS), f"='Espíritus'!{L}{spirit_total_row}")
        wr.cell(i, 5 + len(COLS), f"={score_L}{i}+{spirit_L}{i}")
    avg_row = m + 1
    wr.cell(avg_row, 1, "Promedio de las 8 potencias")
    for j in range(2, 6 + len(COLS)):
        L = get_column_letter(j)
        wr.cell(avg_row, j, f"=AVERAGE({L}2:{L}9)")
    # cuánto se aparta el total de cada árbol del promedio de las potencias
    rel_col = 6 + len(COLS)
    wr.cell(1, rel_col, "Total vs promedio de potencias")
    for i in range(2, m + 1):
        wr.cell(i, rel_col, f"=IF(${total_L}${avg_row}=0,0,{total_L}{i}/${total_L}${avg_row}-1)")
        wr.cell(i, rel_col).number_format = "0%;-0%;-"
    excl_L = get_column_letter(4 + len(COLS) + 3)
    wr.cell(1, rel_col + 1, "Focos excluyentes (se cuentan igual)")
    for i in range(2, m + 1):
        wr.cell(i, rel_col + 1, f"=COUNTIFS('Por foco'!$A$2:$A${n},$A{i},'Por foco'!${excl_L}$2:${excl_L}${n},\"?*\")")
    for i in range(2, avg_row + 1):
        for L in (score_L, spirit_L, total_L):
            wr[f"{L}{i}"].number_format = "#,##0"

    # ---- Por rama
    wb2 = wb.create_sheet("Por rama", 1)
    wb2.append(["Árbol", "Rama", "Focos"] + [t for _, t in COLS])
    branches = list(dict.fromkeys((r["arbol"], r["rama"]) for r in rows))
    for i, (tag, br) in enumerate(branches, start=2):
        wb2.cell(i, 1, tag)
        wb2.cell(i, 2, br)
        wb2.cell(i, 3, f"=COUNTIFS('Por foco'!$A$2:$A${n},$A{i},'Por foco'!$B$2:$B${n},$B{i})")
        for j, (k, _) in enumerate(COLS):
            col = col_of[k]
            wb2.cell(i, 4 + j, f"=SUMIFS('Por foco'!${col}$2:${col}${n},'Por foco'!$A$2:$A${n},$A{i},"
                               f"'Por foco'!$B$2:$B${n},$B{i})")

    # ---- Notas
    wn = wb.create_sheet("Notas")
    for line in [
        "Cómo se cuenta (generado por tools/focos_balance.py desde spec/07_focus_trees.yaml):",
        "- Se suman TODOS los focos de cada árbol, aunque algunos sean excluyentes (columna 'Excluye a').",
        "- 'Estabilidad' y 'Apoyo a la guerra' son los puntos que se suman en el acto (no los de los espíritus).",
        "- Un 'states' al azar cuenta como 1 región; dentro de un 'if' cuenta solo lo de 'then'.",
        "- Un 'random' cuenta el promedio pesado de sus opciones.",
        "- 'Espíritus' (hoja) es la suma neta de modificadores de los espíritus permanentes que dejan los focos:",
        "  agregados menos quitados (los reemplazos por nivel cuentan solo el último). Los temporales no suman.",
        "- Los espíritus vivos que dependen de una variable de la mecánica no tienen valor fijo: no suman.",
        "- No incluye la repoblación (depende del mapa instalado) ni lo que dan los eventos que disparan los focos.",
        "- 'Puntaje en el acto' = suma de cada beneficio por su peso de la hoja Pesos (celdas amarillas, editables).",
        "- 'Puntaje de espíritus' = cada modificador neto por su peso de la hoja Espíritus (columna B, amarilla).",
        "- Los pesos son inventados para comparar con una misma vara; no salen del juego. Cambialos a gusto.",
        "- 'Total vs promedio' compara el total con el promedio de las 8 potencias (filas 2 a 9).",
        "- Las anarquías, las Tierras Sin Ley (ZAN) y la Junta tienen árboles cortos: no se comparan con las potencias.",
    ]:
        wn.append([line])

    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for c in row:
                if c.font != blue:
                    c.font = font
        for c in sheet[1]:
            c.font = bold
            c.fill = head_fill
            c.alignment = Alignment(wrap_text=True, vertical="top")
        sheet.freeze_panes = "B2" if sheet.title != "Notas" else None
        for j in range(1, sheet.max_column + 1):
            sheet.column_dimensions[get_column_letter(j)].width = 14
    ws.column_dimensions["C"].width = 34
    ws.column_dimensions["D"].width = 34
    for j in range(5 + len(COLS), 8 + len(COLS)):
        ws.column_dimensions[get_column_letter(j)].width = 50
    wn.column_dimensions["A"].width = 120
    we.column_dimensions["A"].width = 40
    wr.cell(avg_row, 1).font = bold
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


if __name__ == "__main__":
    print(write())
