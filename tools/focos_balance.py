"""Planilla de beneficios por árbol de focos (pedido del usuario, 2026-10-13:
"hacé el cálculo, la suma total de los beneficios que da cada árbol de foco,
quiero compararlos y equilibrar a mano"; y después: "me faltan un montón de
datos, ¿no afectan la producción? ¿la org o el ataque de las divisiones?").

    python3 -m tools.focos_balance            -> balance/focos_comparacion.xlsx

Lee el spec y recorre cada árbol foco por foco, en orden, con un simulador
chico del estado del país (variables de la mecánica, banderas, espíritus,
espíritus vivos). Así cada foco muestra:

  - lo que da en el acto (poder político, fábricas, equipo, divisiones...)
  - cuánto cambia los modificadores permanentes (producción, organización,
    ataque, defensa, investigación...) sumando sus espíritus (agregados menos
    quitados) Y lo que mueve en la mecánica de su potencia: si sube el
    Cómputo de la ASC, la planilla corre la fórmula del espíritu vivo y anota
    cuánto sube la producción o el ataque.
  - los eventos propios que dispara (promedio de sus opciones).

Hojas: Resumen, Por rama, Por foco, Mecánicas, Pesos, Notas.
"""

from __future__ import annotations

import copy
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "spec"
OUT = REPO / "balance" / "focos_comparacion.xlsx"
MAJORS = ["EFE", "ASC", "FCU", "HSN", "NAS", "SHD", "APF", "NRE"]

# ---------------------------------------------------------------- columnas
# lo que se da en el acto (clave interna, título)
COLS = [
    ("dias", "Días"),
    ("pp", "Poder político"),
    ("estab", "Estabilidad en el acto (%)"),
    ("guerra", "Apoyo a la guerra en el acto (%)"),
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
]
BUILD = {"industrial_complex": "civ", "arms_factory": "mil", "dockyard": "dock", "infrastructure": "infra"}

# pesos por defecto de lo que se da en el acto (editables en la hoja Pesos)
WEIGHTS = {
    "pp": 1, "estab": 10, "guerra": 8, "manpower": 0.002, "exp_ej": 1, "exp_nav": 1, "exp_aire": 1,
    "slots": 300, "tech": 25, "civ": 100, "mil": 80, "dock": 60, "infra": 15, "otros_edif": 10,
    "equipo": 0.02, "divisiones": 40, "cazas": 0.5, "territorio": 20, "dias": 0,
}

# modificadores que no son porcentaje (se muestran tal cual)
RAW = {"political_power_gain", "weekly_manpower", "operative_slot", "monthly_population",
       "command_power_gain", "max_command_power", "local_supplies", "democratic_drift",
       "communism_drift", "fascism_drift", "neutrality_drift", "army_experience_gain",
       "naval_experience_gain", "air_experience_gain"}

# nombre en castellano y grupo de cada modificador (los que faltan salen con su clave)
LABELS = {
    # política
    "political_power_gain": ("Poder político por día", "Política"),
    "political_power_factor": ("Poder político (%)", "Política"),
    "stability_factor": ("Estabilidad (%)", "Política"),
    "war_support_factor": ("Apoyo a la guerra (%)", "Política"),
    "democratic_drift": ("Deriva democrática por día", "Política"),
    "trade_opinion_factor": ("Opinión comercial (%)", "Política"),
    "operative_slot": ("Agentes", "Política"),
    "command_power_gain": ("Poder de mando por día", "Política"),
    "enemy_justify_war_goal_time": ("Tiempo del enemigo para justificar guerra (%)", "Política"),
    # economía
    "industrial_capacity_factory": ("Producción de fábricas (%)", "Producción"),
    "industrial_capacity_dockyard": ("Producción de astilleros (%)", "Producción"),
    "production_factory_efficiency_gain_factor": ("Ganancia de eficiencia (%)", "Producción"),
    "production_factory_max_efficiency_factor": ("Eficiencia máxima (%)", "Producción"),
    "production_factory_start_efficiency_factor": ("Eficiencia inicial (%)", "Producción"),
    "production_speed_buildings_factor": ("Velocidad de construcción (%)", "Producción"),
    "production_speed_arms_factory_factor": ("Construcción de fábricas militares (%)", "Producción"),
    "production_speed_industrial_complex_factor": ("Construcción de fábricas civiles (%)", "Producción"),
    "production_speed_infrastructure_factor": ("Construcción de infraestructura (%)", "Producción"),
    "production_speed_dockyard_factor": ("Construcción de astilleros (%)", "Producción"),
    "consumer_goods_factor": ("Bienes de consumo (%) (negativo es bueno)", "Producción"),
    "local_resources_factor": ("Recursos (%)", "Producción"),
    "research_speed_factor": ("Velocidad de investigación (%)", "Producción"),
    "monthly_population": ("Crecimiento de población por mes", "Producción"),
    "production_lack_of_resource_penalty_factor": ("Castigo por falta de recursos (%)", "Producción"),
    # mano de obra
    "recruitable_population_factor": ("Población reclutable (%)", "Mano de obra"),
    "conscription_factor": ("Reclutamiento (%)", "Mano de obra"),
    "weekly_manpower": ("Mano de obra por semana", "Mano de obra"),
    "casualty_trickleback": ("Heridos que vuelven (%)", "Mano de obra"),
    # ejército
    "army_attack_factor": ("Ataque del ejército (%)", "Ejército"),
    "army_defence_factor": ("Defensa del ejército (%)", "Ejército"),
    "army_org_factor": ("Organización del ejército (%)", "Ejército"),
    "army_morale_factor": ("Recuperación de organización (%)", "Ejército"),
    "army_core_attack_factor": ("Ataque en núcleos (%)", "Ejército"),
    "army_core_defence_factor": ("Defensa en núcleos (%)", "Ejército"),
    "army_armor_attack_factor": ("Ataque de blindados (%)", "Ejército"),
    "army_armor_defence_factor": ("Defensa de blindados (%)", "Ejército"),
    "army_infantry_attack_factor": ("Ataque de infantería (%)", "Ejército"),
    "army_infantry_defence_factor": ("Defensa de infantería (%)", "Ejército"),
    "army_artillery_attack_factor": ("Ataque de artillería (%)", "Ejército"),
    "army_speed_factor": ("Velocidad del ejército (%)", "Ejército"),
    "breakthrough_factor": ("Ruptura (%)", "Ejército"),
    "experience_gain_army": ("Experiencia del ejército (%)", "Ejército"),
    "land_reinforce_rate": ("Refuerzos (%)", "Ejército"),
    "max_dig_in": ("Atrincheramiento máximo", "Ejército"),
    "attrition": ("Desgaste (%) (negativo es bueno)", "Ejército"),
    "supply_consumption_factor": ("Consumo de suministros (%) (negativo es bueno)", "Ejército"),
    "out_of_supply_factor": ("Castigo sin suministros (%) (negativo es bueno)", "Ejército"),
    "winter_attrition_factor": ("Desgaste por frío (%)", "Ejército"),
    "heat_attrition_factor": ("Desgaste por calor (%)", "Ejército"),
    # aire
    "air_attack_factor": ("Ataque aéreo (%)", "Aire"),
    "air_defence_factor": ("Defensa aérea (%)", "Aire"),
    "air_agility_factor": ("Agilidad aérea (%)", "Aire"),
    "air_superiority_efficiency": ("Superioridad aérea (%)", "Aire"),
    "air_interception_detect_factor": ("Detección de intercepción (%)", "Aire"),
    "air_ace_generation_chance_factor": ("Aparición de ases (%)", "Aire"),
    "air_ace_bonuses_factor": ("Bonos de los ases (%)", "Aire"),
    "experience_gain_air": ("Experiencia aérea (%)", "Aire"),
    "air_training_xp_gain_factor": ("Experiencia por entrenamiento aéreo (%)", "Aire"),
    "air_accidents_factor": ("Accidentes aéreos (%)", "Aire"),
    # mar
    "navy_org_factor": ("Organización naval (%)", "Mar"),
    "naval_damage_factor": ("Daño naval (%)", "Mar"),
    "naval_defense_factor": ("Defensa naval (%)", "Mar"),
    "naval_speed_factor": ("Velocidad naval (%)", "Mar"),
    "experience_gain_navy": ("Experiencia naval (%)", "Mar"),
    "navy_casualty_on_hit": ("Bajas navales por impacto (%)", "Mar"),
    "navy_casualty_on_sink": ("Bajas navales por hundimiento (%)", "Mar"),
    "amphibious_invasion": ("Desembarcos (%)", "Mar"),
    "amphibious_invasion_defence": ("Defensa contra desembarcos (%)", "Mar"),
}
GROUP_ORDER = ["Política", "Producción", "Mano de obra", "Ejército", "Aire", "Mar", "Otros"]

# pesos por defecto de los modificadores: puntos por cada 1% (o por cada
# unidad en los que no son porcentaje). Inventados para comparar con la misma
# vara que lo que se da en el acto: p. ej. +0,1 PP diario durante ~2 años son
# ~73 PP (730 por 1 PP diario); +1% de producción de fábricas en ~50 fábricas
# es media fábrica (30 puntos).
MOD_WEIGHTS = {
    "political_power_gain": 730, "political_power_factor": 4, "stability_factor": 10, "war_support_factor": 8,
    "trade_opinion_factor": 1, "operative_slot": 100, "democratic_drift": 0, "command_power_gain": 300,
    "enemy_justify_war_goal_time": 1,
    "industrial_capacity_factory": 30, "industrial_capacity_dockyard": 15,
    "production_factory_efficiency_gain_factor": 8, "production_factory_max_efficiency_factor": 20,
    "production_factory_start_efficiency_factor": 8,
    "production_speed_buildings_factor": 15, "production_speed_arms_factory_factor": 5,
    "production_speed_industrial_complex_factor": 6, "production_speed_infrastructure_factor": 3,
    "production_speed_dockyard_factor": 3, "consumer_goods_factor": -30, "local_resources_factor": 10,
    "research_speed_factor": 15, "monthly_population": 3, "production_lack_of_resource_penalty_factor": -3,
    "recruitable_population_factor": 30, "conscription_factor": 10, "weekly_manpower": 0.2,
    "casualty_trickleback": 5,
    "army_attack_factor": 15, "army_defence_factor": 12, "army_org_factor": 10, "army_morale_factor": 6,
    "army_core_attack_factor": 6, "army_core_defence_factor": 5, "army_armor_attack_factor": 5,
    "army_armor_defence_factor": 5, "army_infantry_attack_factor": 6, "army_infantry_defence_factor": 6,
    "army_artillery_attack_factor": 4, "army_speed_factor": 5, "breakthrough_factor": 6,
    "experience_gain_army": 3, "land_reinforce_rate": 4, "max_dig_in": 10, "attrition": -5,
    "supply_consumption_factor": -6, "out_of_supply_factor": -3, "winter_attrition_factor": -1,
    "heat_attrition_factor": -1,
    "air_attack_factor": 4, "air_defence_factor": 4, "air_agility_factor": 4, "air_superiority_efficiency": 4,
    "air_interception_detect_factor": 2, "air_ace_generation_chance_factor": 1, "air_ace_bonuses_factor": 1,
    "experience_gain_air": 2, "air_training_xp_gain_factor": 1, "air_accidents_factor": -1,
    "navy_org_factor": 5, "naval_damage_factor": 5, "naval_defense_factor": 5, "naval_speed_factor": 3,
    "experience_gain_navy": 2, "navy_casualty_on_hit": -1, "navy_casualty_on_sink": -1,
    "amphibious_invasion": 2, "amphibious_invasion_defence": 2,
}

# lo que corre cada potencia para refrescar sus espíritus vivos después de un
# foco (en el juego lo hace el pulso mensual); de los pulsos ("@") se toman
# solo los topes (clamp) y los niveles de espíritus (idea_tiers), no el
# crecimiento ni el desgaste.
REFRESH = {
    "EFE": ["EFE_espiritu_vivo", "@EFE_pulso_de_las_cubas"],
    "ASC": ["ASC_recalcular_computo", "@ASC_pulso_de_la_red"],
    "FCU": ["FCU_recalcular_directorio", "@FCU_pulso_del_directorio"],
    "HSN": ["HSN_espiritu_vivo", "@HSN_pulso_de_las_potencias"],
    "NAS": ["NAS_espiritu_vivo", "@NAS_pulso_de_los_templos"],
    "SHD": ["SHD_recalcular_caudales"],
    "APF": ["APF_espiritu_vivo", "@APF_pulso_de_los_consejos"],
    "NRE": ["NRE_recalcular_legiones", "@NRE_pulso_del_ocio"],
}
# dependen del mapa (quién controla cada región): no se simulan
OPAQUE = {"HSN_recalcular_nodos"}


def _load(name: str) -> dict:
    return yaml.safe_load((SPEC / name).read_text(encoding="utf-8"))


def _clean(mods: dict) -> dict:
    return {str(k).lstrip("?"): v for k, v in (mods or {}).items()
            if not isinstance(v, bool) and isinstance(v, (int, float, str))}


class Data:
    """Todo lo que la simulación necesita leer del spec."""

    def __init__(self) -> None:
        self.ideas: dict[str, dict] = {}
        self.idea_names: dict[str, str] = {}
        self.starting: dict[str, list[str]] = {}

        def walk(o):
            if isinstance(o, dict):
                if "id" in o and isinstance(o.get("modifiers"), dict):
                    self.ideas[o["id"]] = _clean(o["modifiers"])
                    self.idea_names[o["id"]] = (o.get("name") or {}).get("spanish", o["id"])
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        ideas = _load("05_ideas.yaml")
        walk(ideas)
        for tag, c in (ideas.get("countries") or {}).items():
            self.starting[tag] = [i["id"] for i in (c or {}).get("starting_ideas") or [] if isinstance(i, dict)] \
                if isinstance(c, dict) else []
        dec = _load("14_decisions.yaml")
        self.dms: dict[str, dict] = {}
        for m in dec.get("dynamic_modifiers") or []:
            self.dms[m["id"]] = _clean(m.get("modifiers"))
            self.idea_names[m["id"]] = (m.get("name") or {}).get("spanish", m["id"])
        self.scripted = {s["id"]: s.get("effects") or [] for s in dec.get("scripted_effects") or []}
        self.events: dict[str, dict] = {}
        for ns, block in (_load("12_events.yaml").get("namespaces") or {}).items():
            for e in block.get("events") or []:
                self.events[f"{ns}.{e['id']}"] = e
        self.start_vars: dict[str, dict[str, float]] = defaultdict(dict)
        for m in _load("06_mechanics.yaml").get("mechanics") or []:
            v = m.get("variable")
            if isinstance(v, dict) and v.get("name"):
                self.start_vars[v.get("country") or m.get("country")][v["name"]] = float(v.get("start", 0))
            for var in m.get("variables") or []:
                self.start_vars[var.get("country") or m.get("country")][var["name"]] = float(var.get("start", 0))
        self.fighters = (_load("13_military.yaml").get("free_fighters") or {}).get("focuses") or {}
        self.trees = _load("07_focus_trees.yaml")["trees"]


class Sim:
    """El estado de un país mientras se recorren sus focos."""

    def __init__(self, data: Data, tag: str) -> None:
        self.d = data
        self.tag = tag
        self.vars: dict[str, float] = dict(data.start_vars.get(tag, {}))
        self.flags: set[str] = set()
        self.ideas: set[str] = set(data.starting.get(tag, []))
        self.dms: set[str] = set()
        self.done: set[str] = set()
        self.unknown: set[str] = set()
        self.refresh()

    def __deepcopy__(self, memo):
        new = copy.copy(self)
        new.vars, new.flags, new.ideas = dict(self.vars), set(self.flags), set(self.ideas)
        new.dms, new.done, new.unknown = set(self.dms), set(self.done), set(self.unknown)
        return new

    # ---- valores y condiciones
    def val(self, x) -> float:
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            return float(x)
        if isinstance(x, str):
            try:
                return float(x)
            except ValueError:
                return self.vars.get(x, 0.0)
        return 0.0

    def cond(self, c, optimistic: bool) -> bool:
        if c is None:
            return True
        if isinstance(c, list):
            return all(self.cond(x, optimistic) for x in c)
        if not isinstance(c, dict):
            return bool(c)
        for k, v in c.items():
            r = self._one(k, v, optimistic)
            if r is None:
                self.unknown.add(k)
                r = optimistic
            if not r:
                return False
        return True

    def _one(self, k, v, optimistic):
        V = self.vars
        if k == "variable_at_least":
            return V.get(v["var"], 0.0) >= self.val(v["value"])
        if k == "variable_below":
            return V.get(v["var"], 0.0) < self.val(v["value"])
        if k == "variable_between":
            return self.val(v["min"]) <= V.get(v["var"], 0.0) <= self.val(v["max"])
        if k == "variables_below":
            return all(V.get(x["var"], 0.0) < self.val(x["value"]) for x in v)
        if k == "all_between":
            return all(self.val(v["min"]) <= V.get(x, 0.0) <= self.val(v["max"]) for x in v["vars"])
        if k == "flag":
            return all(f in self.flags for f in (v if isinstance(v, list) else [v]))
        if k == "flags":
            return all(f in self.flags for f in v)
        if k == "not_flag":
            return not any(f in self.flags for f in (v if isinstance(v, list) else [v]))
        if k == "idea":
            return v in self.ideas
        if k == "not_idea":
            return v not in self.ideas
        if k == "focus":
            return v in self.done
        if k == "at_war":
            return bool(v) is False      # se supone paz
        if k in ("tag", "original_tag"):
            return v == self.tag
        if k == "country_exists":
            return True
        if k == "always":
            return bool(v)
        if k == "any":
            items = v if isinstance(v, list) else [{kk: vv} for kk, vv in v.items()]
            return any(self.cond(x, optimistic) for x in items)
        if k == "all":
            return self.cond(v, optimistic)
        if k == "not":
            items = v if isinstance(v, list) else [v]
            return not all(self.cond(x, not optimistic) for x in items)
        if k == "explained":
            return self.cond(v.get("when"), optimistic)
        return None

    # ---- efectos sobre el estado (y lo que se da en el acto, en `row`)
    def apply(self, items, row: dict | None, texts: dict | None, weight: float = 1.0,
              optimistic: bool = True, depth: int = 0) -> None:
        if depth > 12:
            return
        for it in items or []:
            if not isinstance(it, dict):
                continue
            e = it.get("effect")
            v = it.get("value")
            if row is not None:
                _instant(it, row, weight)
            if weight < 1.0 and e not in ("if", "random", "states", "in_state", "capital"):
                continue          # dentro de un `random`: solo cuenta lo del momento
            if e == "add_variable":
                self.vars[it["var"]] = self.vars.get(it["var"], 0.0) + self.val(v)
                if texts is not None and depth == 0:
                    texts["mecanica"].append(f"{it['var']} {self.val(v):+g}")
            elif e == "set_variable":
                self.vars[it["var"]] = self.val(v)
            elif e == "clamp":
                x = self.vars.get(it["var"], 0.0)
                if it.get("min") is not None:
                    x = max(x, self.val(it["min"]))
                if it.get("max") is not None:
                    x = min(x, self.val(it["max"]))
                self.vars[it["var"]] = x
            elif e == "math":
                for op in it.get("ops") or []:
                    self._op(op)
            elif e == "flag":
                self.flags.add(v)
            elif e == "clear_flag":
                self.flags.discard(v)
            elif e == "add_ideas":
                ids = v if isinstance(v, list) else [v]
                if it.get("days"):
                    if texts is not None:
                        texts["temporales"] += [f"{self.d.idea_names.get(i, i)} ({it['days']} días)" for i in ids]
                else:
                    self.ideas.update(ids)
                    if texts is not None and depth == 0:
                        texts["ideas"] += [self.d.idea_names.get(i, i) for i in ids]
            elif e == "timed_idea":
                if texts is not None:
                    i = it.get("idea") or v
                    texts["temporales"].append(f"{self.d.idea_names.get(i, i)} ({it.get('days')} días)")
            elif e == "remove_idea":
                self.ideas.discard(v)
                if texts is not None and depth == 0:
                    texts["ideas"].append(f"quita {self.d.idea_names.get(v, v)}")
            elif e == "swap_ideas":
                self.ideas.discard(it.get("remove"))
                self.ideas.add(it.get("add"))
                if texts is not None and depth == 0:
                    texts["ideas"].append(f"{self.d.idea_names.get(it.get('remove'), it.get('remove'))} -> "
                                          f"{self.d.idea_names.get(it.get('add'), it.get('add'))}")
            elif e == "dynamic_modifier":
                i = it.get("id") or v
                if it.get("days"):
                    if texts is not None:
                        texts["temporales"].append(f"{self.d.idea_names.get(i, i)} ({it['days']} días)")
                else:
                    self.dms.add(i)
                    if texts is not None and depth == 0:
                        texts["ideas"].append(self.d.idea_names.get(i, i))
            elif e == "idea_tiers":
                chosen = None
                for t in it.get("tiers") or []:
                    if chosen is None and self.cond(t.get("when"), False):
                        chosen = t["idea"]
                for t in it.get("tiers") or []:
                    self.ideas.discard(t["idea"])
                if chosen:
                    self.ideas.add(chosen)
            elif e == "run":
                if v not in OPAQUE and v in self.d.scripted:
                    self.apply(self.d.scripted[v], row, None, weight, False, depth + 1)
                elif texts is not None and v in OPAQUE:
                    texts["mecanica"].append(f"{v} (depende del mapa)")
            elif e == "if":
                if self.cond(it.get("when"), optimistic):
                    self.apply(it.get("then"), row, texts, weight, optimistic, depth)
                else:
                    self.apply(it.get("else"), row, texts, weight, optimistic, depth)
            elif e in ("states", "in_state", "capital"):
                self.apply(it.get("effects"), row, None, weight, optimistic, depth)
            elif e == "random":
                opts = it.get("options") or []
                total = sum(float(o.get("weight", 1)) for o in opts) or 1
                for o in opts:
                    self.apply(o.get("effects"), row, None, weight * float(o.get("weight", 1)) / total,
                               optimistic, depth)
            elif e == "event" and depth == 0 and texts is not None:
                eid = it.get("id") or v
                if it.get("target") and it.get("target") != self.tag:
                    texts["eventos"].append(f"{eid} (le llega a {it['target']}, no cuenta)")
                else:
                    texts["eventos_propios"].append(eid)

    def _op(self, op) -> None:
        name, var = op[0], op[1]
        arg = op[2] if len(op) > 2 else None
        x = self.vars.get(var, 0.0)
        a = self.val(arg) if arg is not None else None
        if name == "set":
            x = a
        elif name == "add":
            x += a
        elif name == "sub":
            x -= a
        elif name == "mul":
            x *= a
        elif name == "div":
            x = x / a if a else x
        elif name == "round":
            x = float(round(x))
        elif name == "min":
            x = min(x, a)
        elif name == "max":
            x = max(x, a)
        self.vars[var] = x

    def refresh(self) -> None:
        for name in REFRESH.get(self.tag, []):
            if name.startswith("@"):
                tiers = [x for x in self.d.scripted.get(name[1:], []) if x.get("effect") in ("clamp", "idea_tiers")]
                self.apply(tiers, None, None, 1.0, False, 1)
            else:
                self.apply(self.d.scripted.get(name, []), None, None, 1.0, False, 1)

    def modifiers(self) -> dict[str, float]:
        out: dict[str, float] = defaultdict(float)
        for i in self.ideas:
            for k, x in self.d.ideas.get(i, {}).items():
                if isinstance(x, (int, float)):
                    out[k] += x
        for m in self.dms:
            for k, x in self.d.dms.get(m, {}).items():
                out[k] += self.val(x)
        return out


def _instant(it: dict, row: dict, weight: float) -> None:
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
        row[BUILD.get(it.get("building"), "otros_edif")] += weight * float(it.get("level", 1))
    elif e == "equipment" and float(it.get("amount", 0)) > 0:
        row["equipo"] += weight * float(it["amount"])
    elif e == "create_units":
        row["divisiones"] += weight * float(it.get("count", 1))
    elif e in ("claim", "or_cores", "wargoal", "wargoal_holders", "core"):
        row["territorio"] += weight


def _diff(after: dict, before: dict) -> dict[str, float]:
    keys = set(after) | set(before)
    return {k: after.get(k, 0.0) - before.get(k, 0.0) for k in keys
            if abs(after.get(k, 0.0) - before.get(k, 0.0)) > 1e-9}


def _event_effect(sim: Sim, eid: str) -> tuple[dict, dict, int]:
    """Promedio de las opciones de un evento propio: (en el acto, modificadores, opciones)."""
    ev = sim.d.events.get(eid)
    if not ev:
        return {}, {}, 0
    opts = ev.get("options") or []
    inst: dict[str, float] = defaultdict(float)
    mods: dict[str, float] = defaultdict(float)
    base = sim.modifiers()
    for o in opts:
        s = copy.deepcopy(sim)
        r = {k: 0.0 for k, _ in COLS}
        s.apply(o.get("effects"), r, None, 1.0, True, 1)
        s.refresh()
        for k, x in r.items():
            inst[k] += x / len(opts)
        for k, x in _diff(s.modifiers(), base).items():
            mods[k] += x / len(opts)
    return dict(inst), dict(mods), len(opts)


def collect() -> tuple[list[dict], dict, list[str], list[dict]]:
    """Filas por foco, modificadores netos por árbol, orden de árboles, mecánicas."""
    data = Data()
    rows: list[dict] = []
    tree_mods: dict[str, dict] = {}
    mech: list[dict] = []
    for tag, tree in data.trees.items():
        if not isinstance(tree, dict) or "branches" not in tree:
            continue
        sim = Sim(data, tag)
        start_vars = dict(data.start_vars.get(tag, {}))
        start_mods = sim.modifiers()
        for branch in tree["branches"]:
            for f in branch.get("focuses") or []:
                row = {k: 0.0 for k, _ in COLS}
                row["dias"] = float(f.get("days", 0))
                texts = {"ideas": [], "temporales": [], "mecanica": [], "eventos": [], "eventos_propios": []}
                before = sim.modifiers()
                sim.unknown = set()
                sim.apply(f.get("reward"), row, texts)
                sim.done.add(f["id"])
                sim.refresh()
                mods = _diff(sim.modifiers(), before)
                for eid in texts["eventos_propios"]:
                    inst, emods, n = _event_effect(sim, eid)
                    for k, x in inst.items():
                        row[k] += x
                    for k, x in emods.items():
                        mods[k] = mods.get(k, 0.0) + x
                    texts["eventos"].append(f"{eid}" + (f" (promedio de {n} opciones)" if n > 1 else ""))
                row["cazas"] += float(data.fighters.get(f["id"], 0))
                excl = f.get("mutually_exclusive") or []
                rows.append({"arbol": tag, "rama": branch.get("id", ""), "foco": f["id"],
                             "nombre": (f.get("name") or {}).get("spanish", ""), **row, "mods": mods,
                             "ideas": ", ".join(texts["ideas"]), "temporales": ", ".join(texts["temporales"]),
                             "mecanica": ", ".join(texts["mecanica"]), "eventos": ", ".join(texts["eventos"]),
                             "sin_evaluar": ", ".join(sorted(sim.unknown)),
                             "excluye": ", ".join(excl) if isinstance(excl, list) else str(excl)})
        tree_mods[tag] = _diff(sim.modifiers(), start_mods)
        for var, x0 in start_vars.items():
            if abs(sim.vars.get(var, 0.0) - x0) > 1e-9 or (tag in MAJORS and "_lealtad_" not in var):
                mech.append({"arbol": tag, "var": var, "inicio": x0, "fin": sim.vars.get(var, 0.0)})
    order = list(dict.fromkeys(r["arbol"] for r in rows))
    return rows, tree_mods, order, mech


def _mod_keys(rows: list[dict]) -> list[str]:
    keys = {k for r in rows for k, v in r["mods"].items() if abs(v) > 1e-9}

    def sort_key(k):
        group = LABELS.get(k, (k, "Otros"))[1]
        return (GROUP_ORDER.index(group), list(LABELS).index(k) if k in LABELS else 999, k)
    return sorted(keys, key=sort_key)


def _label(k: str) -> str:
    if k in LABELS:
        return LABELS[k][0]
    return k + ("" if k in RAW else " (%)")


def _scale(k: str) -> float:
    return 1.0 if k in RAW else 100.0


def write(path: Path = OUT) -> Path:
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    rows, tree_mods, order, mech = collect()
    mkeys = _mod_keys(rows)
    font = Font(name="Arial", size=10)
    bold = Font(name="Arial", size=10, bold=True)
    blue = Font(name="Arial", size=10, color="0000FF")
    head_fill = PatternFill("solid", fgColor="DDE3EA")
    mod_fill = PatternFill("solid", fgColor="D9EAD3")
    yellow = PatternFill("solid", fgColor="FFFF00")
    wb = Workbook()

    # todas las columnas numéricas: (clave, título, es_modificador)
    num = [(k, t, False) for k, t in COLS] + [(k, _label(k), True) for k in mkeys]

    # ---- Por foco
    ws = wb.active
    ws.title = "Por foco"
    texts = ["Espíritus (detalle)", "Temporales (no suman)", "Mecánica que mueve", "Eventos (los propios suman)",
             "Condiciones que no se pudieron evaluar", "Excluye a"]
    ws.append(["Árbol", "Rama", "Foco", "Nombre"] + [t for _, t, _ in num] + texts)
    for r in rows:
        vals = [round(r[k], 3) for k, _ in COLS] + [round(r["mods"].get(k, 0.0) * _scale(k), 3) for k in mkeys]
        ws.append([r["arbol"], r["rama"], r["foco"], r["nombre"]] + [v if abs(v) > 1e-9 else None for v in vals]
                  + [r["ideas"], r["temporales"], r["mecanica"], r["eventos"], r["sin_evaluar"], r["excluye"]])
    n = len(rows) + 1
    col_of = {k: get_column_letter(5 + i) for i, (k, _, _) in enumerate(num)}
    excl_L = get_column_letter(5 + len(num) + len(texts) - 1)

    # ---- Pesos
    wp = wb.create_sheet("Pesos")
    wp.append(["Beneficio", "Peso (puntos por unidad)", "Grupo"])
    for k, t, is_mod in num:
        w = MOD_WEIGHTS.get(k, 0) if is_mod else WEIGHTS[k]
        wp.append([t, w, LABELS.get(k, (k, "Otros"))[1] if is_mod else "En el acto"])
    for row in wp.iter_rows(min_row=2, max_row=len(num) + 1, min_col=2, max_col=2):
        for c in row:
            c.fill = yellow
            c.font = blue
    wp["B1"].comment = Comment("Pesos inventados para comparar, no salen del juego. Los modificadores valen "
                               "por cada 1% (o por unidad si no son porcentaje). Cambialos y el puntaje se "
                               "recalcula.", "2100 Meganations")
    weight_row = {k: i + 2 for i, (k, _, _) in enumerate(num)}

    # ---- Resumen
    wr = wb.create_sheet("Resumen", 0)
    wr.append(["Árbol", "Focos"] + [t for _, t, _ in num]
              + ["Puntaje en el acto", "Puntaje de modificadores", "Puntaje total", "Total vs promedio de potencias",
                 "Focos excluyentes (se cuentan igual)"])
    first_score = 3 + len(num)
    sL, mL, tL = (get_column_letter(first_score + i) for i in range(3))
    for i, tag in enumerate(order, start=2):
        wr.cell(i, 1, tag)
        wr.cell(i, 2, f"=COUNTIF('Por foco'!$A$2:$A${n},$A{i})")
        inst_terms, mod_terms = [], []
        for j, (k, _, is_mod) in enumerate(num):
            col = col_of[k]
            L = get_column_letter(3 + j)
            wr.cell(i, 3 + j, f"=SUMIFS('Por foco'!${col}$2:${col}${n},'Por foco'!$A$2:$A${n},$A{i})")
            (mod_terms if is_mod else inst_terms).append(f"{L}{i}*Pesos!$B${weight_row[k]}")
        wr.cell(i, first_score, "=" + "+".join(inst_terms))
        wr.cell(i, first_score + 1, "=" + ("+".join(mod_terms) if mod_terms else "0"))
        wr.cell(i, first_score + 2, f"={sL}{i}+{mL}{i}")
        wr.cell(i, first_score + 4,
                f"=COUNTIFS('Por foco'!$A$2:$A${n},$A{i},'Por foco'!${excl_L}$2:${excl_L}${n},\"?*\")")
    m = len(order) + 1
    avg_row = m + 1
    wr.cell(avg_row, 1, "Promedio de las 8 potencias")
    for j in range(2, first_score + 3):
        L = get_column_letter(j)
        wr.cell(avg_row, j, f"=AVERAGE({L}2:{L}9)")
    for i in range(2, m + 1):
        wr.cell(i, first_score + 3, f"=IF(${tL}${avg_row}=0,0,{tL}{i}/${tL}${avg_row}-1)")
        wr.cell(i, first_score + 3).number_format = "0%;-0%;-"
    for i in range(2, avg_row + 1):
        for L in (sL, mL, tL):
            wr[f"{L}{i}"].number_format = "#,##0"
        for j, (k, _, is_mod) in enumerate(num):
            if is_mod:
                wr.cell(i, 3 + j).number_format = "0.0;-0.0;-" if k not in RAW else "0.00;-0.00;-"

    # ---- Por rama
    wb2 = wb.create_sheet("Por rama", 1)
    wb2.append(["Árbol", "Rama", "Focos"] + [t for _, t, _ in num])
    branches = list(dict.fromkeys((r["arbol"], r["rama"]) for r in rows))
    for i, (tag, br) in enumerate(branches, start=2):
        wb2.cell(i, 1, tag)
        wb2.cell(i, 2, br)
        wb2.cell(i, 3, f"=COUNTIFS('Por foco'!$A$2:$A${n},$A{i},'Por foco'!$B$2:$B${n},$B{i})")
        for j, (k, _, _) in enumerate(num):
            col = col_of[k]
            wb2.cell(i, 4 + j, f"=SUMIFS('Por foco'!${col}$2:${col}${n},'Por foco'!$A$2:$A${n},$A{i},"
                               f"'Por foco'!$B$2:$B${n},$B{i})")

    # ---- Mecánicas: cómo quedan las variables de cada potencia después de todos sus focos
    wm = wb.create_sheet("Mecánicas", 3)
    wm.append(["Árbol", "Variable", "Al arrancar", "Después de todos los focos", "Cambio"])
    for i, x in enumerate(mech, start=2):
        wm.append([x["arbol"], x["var"], round(x["inicio"], 2), round(x["fin"], 2)])
        wm.cell(i, 5, f"=D{i}-C{i}")

    # ---- Notas
    wn = wb.create_sheet("Notas")
    for line in [
        "Cómo se cuenta (generado por tools/focos_balance.py desde el spec; se vuelve a generar con cada cambio):",
        "- Cada árbol se recorre foco por foco, rama por rama, en el orden del spec, con un simulador del país:",
        "  variables de la mecánica (con su valor de arranque), banderas, espíritus y espíritus vivos.",
        "- Columnas grises: lo que el foco da una sola vez (poder político, fábricas, equipo...).",
        "- Columnas verdes: cuánto cambia cada modificador permanente al terminar el foco. Suma sus",
        "  espíritus (agregados menos quitados; un reemplazo cuenta la diferencia) y lo que mueve en la",
        "  mecánica: la planilla corre la fórmula del espíritu vivo (p. ej. Cómputo de la ASC -> producción;",
        "  Auctoritas de Roma -> organización; Bioacero del EFE -> blindados).",
        "- Los modificadores van en % (10 = +10%), salvo los que dicen 'por día', 'por semana' o 'por mes'.",
        "- 'Bienes de consumo', 'Desgaste' y los castigos: negativo es bueno (su peso es negativo).",
        "- Las mecánicas se simulan sin el paso del tiempo: no cuenta el crecimiento o el desgaste mensual ni",
        "  las decisiones; solo lo que suman los focos, con sus topes. La ASC se toma en su prioridad por",
        "  defecto (economía); la HSN no suma nodos (dependen de las regiones que controle).",
        "- Eventos propios que dispara un foco: suman el promedio de sus opciones. Los que le llegan a otro",
        "  país no cuentan. Los espíritus temporales no suman (están en su columna con los días).",
        "- Se suman TODOS los focos de cada árbol, aunque algunos sean excluyentes (columna 'Excluye a').",
        "- Un 'states' al azar es 1 región. Una condición que no se puede evaluar (p. ej. controlar una",
        "  región) se da por cumplida dentro de un foco; queda anotada en su columna.",
        "- No incluye la repoblación (depende del mapa instalado).",
        "- Puntaje = cada columna por su peso de la hoja Pesos (celdas amarillas, editables). Los pesos son",
        "  inventados para comparar con la misma vara; no salen del juego.",
        "- 'Total vs promedio' compara con el promedio de las 8 potencias (filas 2 a 9). Las anarquías, las",
        "  Tierras Sin Ley (ZAN) y la Junta tienen árboles cortos: no se comparan con las potencias.",
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
            sheet.column_dimensions[get_column_letter(j)].width = 13
    # cabeceras de modificadores en verde
    for sheet, offset in ((ws, 5), (wr, 3), (wb2, 4)):
        for j, (_, _, is_mod) in enumerate(num):
            if is_mod:
                sheet.cell(1, offset + j).fill = mod_fill
        sheet.row_dimensions[1].height = 75
    ws.column_dimensions["C"].width = 34
    ws.column_dimensions["D"].width = 34
    ws.freeze_panes = "E2"
    for j in range(5 + len(num), 5 + len(num) + len(texts)):
        ws.column_dimensions[get_column_letter(j)].width = 50
    wn.column_dimensions["A"].width = 120
    wp.column_dimensions["A"].width = 45
    wm.column_dimensions["B"].width = 30
    wr.cell(avg_row, 1).font = bold
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


if __name__ == "__main__":
    print(write())
