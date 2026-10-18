"""El motor del simulador: corre los scripts del spec mes a mes, sin el juego.

Lee las condiciones y los efectos tal como están en spec/*.yaml (los mismos
que el generador convierte a script de Paradox) y los ejecuta sobre un estado
de juguete: variables, flags, estabilidad y guerra por país. Lo que el motor no
sabe calcular (cuántas divisiones hay, si un satélite sigue siéndolo) sale de
supuestos.yaml; lo que no está ni acá ni allá corta la corrida con un error,
así nadie lee una tabla que inventó un valor en silencio.

Escala: un paso = un mes. Los `days:` de flags y eventos se redondean a meses.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

MES_DIAS = 30.4
POTENCIAS = ["EFE", "FCU", "ASC", "HSN", "NAS", "SHD", "APF", "NRE"]

# Efectos que no cambian nada de lo que el simulador mide (fábricas,
# experiencia, modificadores...). Se cuentan, no se ejecutan.
EFECTOS_IGNORADOS = {
    "add_political_power", "add_war_support", "dynamic_modifier", "build", "air_experience",
    "navy_experience", "army_experience", "add_manpower", "add_ideas", "remove_idea", "retire_leader",
    "equipment", "milestone_snapshot", "add_command_power", "country_event",
}


class SupuestoFaltante(Exception):
    """Una condición que el motor no sabe evaluar y supuestos.yaml no cubre."""


def mes_de(fecha: str | int | float) -> int:
    """'2104.1.1' -> meses desde enero de 2100 (el día 1 no suma, otro día sí)."""
    partes = [int(p) for p in str(fecha).split(".")]
    anio, mes = partes[0], partes[1] if len(partes) > 1 else 1
    dia = partes[2] if len(partes) > 2 else 1
    return (anio - 2100) * 12 + (mes - 1) + (1 if dia > 1 else 0)


def fecha_de(mes: int) -> str:
    return f"{2100 + mes // 12}.{mes % 12 + 1}"


def meses(dias: int | float) -> int:
    return max(1, math.ceil(float(dias) / MES_DIAS))


@dataclass
class Pais:
    tag: str
    variables: dict[str, float] = field(default_factory=dict)
    flags: dict[str, int | None] = field(default_factory=dict)  # nombre -> mes en que vence (None = nunca)
    flags_desde: dict[str, int] = field(default_factory=dict)
    estabilidad: float = 0.6
    en_guerra: bool = False
    focos: set[str] = field(default_factory=set)
    enfriamiento: dict[str, int] = field(default_factory=dict)  # decisión -> mes en que se puede repetir
    registro: list[tuple[int, str]] = field(default_factory=list)

    def tiene_flag(self, nombre: str, mes: int) -> bool:
        if nombre not in self.flags:
            return False
        vence = self.flags[nombre]
        if vence is not None and mes >= vence:
            del self.flags[nombre]
            return False
        return True


class Mundo:
    """Todos los países, lo global y el azar de una corrida."""

    def __init__(self, spec_raw: dict, supuestos: dict, rng: random.Random, paises: list[str] | None = None):
        self.raw = spec_raw
        self.sup = supuestos
        self.rng = rng
        self.mes = 0
        self.globales: dict[str, float] = {}
        self.flags_globales: set[str] = set()
        self.paises = {t: Pais(t) for t in (paises or POTENCIAS)}
        self.ignorados: dict[str, int] = {}
        self.supuestos_usados: dict[str, int] = {}
        self.contadores: dict[str, int] = {}
        self._efectos = {e["id"]: e for e in spec_raw["decisions"].get("scripted_effects") or []}
        self._eventos: dict[str, dict] = {}
        for ns, bloque in (spec_raw["events"].get("namespaces") or {}).items():
            for ev in bloque.get("events") or []:
                self._eventos[f"{ns}.{ev['id']}"] = ev

    # -- variables ----------------------------------------------------------

    def _store(self, pais: Pais, var: str) -> tuple[dict, str]:
        if var.startswith("global."):
            return self.globales, var[len("global."):]
        return pais.variables, var

    def var(self, pais: Pais, var: str) -> float:
        store, k = self._store(pais, var)
        return store.get(k, 0.0)

    def _valor(self, pais: Pais, v: Any) -> float:
        if isinstance(v, str):
            return self.var(pais, v)
        return float(v)

    def contar(self, clave: str, n: int = 1) -> None:
        self.contadores[clave] = self.contadores.get(clave, 0) + n

    # -- condiciones --------------------------------------------------------

    def cumple(self, pais: Pais, cond: Any, root: Pais | None = None) -> bool:
        """Un dict es AND de sus claves; listas en any/all."""
        if cond is None:
            return True
        if isinstance(cond, list):
            return all(self.cumple(pais, c, root) for c in cond)
        root = root or pais
        for clave, valor in cond.items():
            if not self._una(pais, clave, valor, root):
                return False
        return True

    def _una(self, p: Pais, k: str, v: Any, root: Pais) -> bool:
        m = self.mes
        if k == "all":
            return all(self.cumple(p, c, root) for c in v)
        if k == "any":
            return any(self.cumple(p, c, root) for c in v)
        if k == "not":
            return not self.cumple(p, v, root)
        if k == "date_after":
            return m >= mes_de(v)
        if k == "flag":
            return p.tiene_flag(v, m)
        if k == "not_flag":
            return not p.tiene_flag(v, m)
        if k == "flags":
            return all(p.tiene_flag(f, m) for f in v)
        if k == "flag_older":
            return p.tiene_flag(v["flag"], m) and (m - p.flags_desde[v["flag"]]) * MES_DIAS >= v["days"]
        if k == "global_flag":
            return v in self.flags_globales
        if k == "not_global_flag":
            return v not in self.flags_globales
        if k == "variable_at_least":
            return self.var(p, v["var"]) >= self._valor(p, v["value"])
        if k == "variable_below":
            return self.var(p, v["var"]) < self._valor(p, v["value"])
        if k == "variables_below":
            return all(self.var(p, x["var"]) < self._valor(p, x["value"]) for x in v)
        if k == "stability_below":
            return p.estabilidad < float(v)
        if k == "stability_at_least":
            return p.estabilidad >= float(v)
        if k == "at_war":
            return p.en_guerra == bool(v)
        if k == "tag":
            return p.tag == (root.tag if v == "ROOT" else v)
        if k == "focus":
            return v in p.focos
        if k == "country":
            otro = self.paises.get(v["tag"])
            if otro is None:
                return self._supuesto(p, f"country:{v['tag']}", v.get("when"))
            return self.cumple(otro, v.get("when"), root)
        return self._supuesto(p, k, v)

    def _supuesto(self, p: Pais, clave: str, valor: Any) -> bool:
        """Condiciones del mapa (divisiones, facciones, súbditos) que el motor
        no simula: probabilidad fija por país en supuestos.yaml."""
        tabla = self.sup.get("condiciones") or {}
        literal = f"{clave}: {str(valor).lower() if isinstance(valor, bool) else valor}"
        entrada = tabla.get(literal, tabla.get(clave))
        clave = literal if literal in tabla else clave
        if entrada is None:
            raise SupuestoFaltante(f"no sé evaluar '{clave}: {valor}' ({p.tag}); agregalo a condiciones en supuestos.yaml")
        prob = entrada.get(p.tag, entrada.get("resto")) if isinstance(entrada, dict) else entrada
        if prob is None:
            raise SupuestoFaltante(f"supuestos.yaml: condiciones.{clave} no tiene valor para {p.tag} ni 'resto'")
        self.supuestos_usados[clave] = self.supuestos_usados.get(clave, 0) + 1
        return self.rng.random() < float(prob)

    # -- efectos ------------------------------------------------------------

    def correr(self, pais: Pais, efectos: list | None) -> None:
        for ef in efectos or []:
            self._efecto(pais, ef)

    def correr_script(self, pais: Pais, sid: str) -> None:
        if sid not in self._efectos:
            raise KeyError(f"scripted effect '{sid}' no existe en el spec")
        self.correr(pais, self._efectos[sid].get("effects"))

    def _efecto(self, p: Pais, ef: dict) -> None:
        tipo = ef.get("effect")
        m = self.mes
        if tipo == "if":
            self.correr(p, ef.get("then") if self.cumple(p, ef.get("when")) else ef.get("else"))
        elif tipo == "random":
            opciones = [o for o in ef.get("options") or [] if not (o.get("skip_if") and self.cumple(p, o["skip_if"]))]
            if opciones:
                elegida = self.rng.choices(opciones, weights=[float(o.get("weight", 1)) for o in opciones])[0]
                self.correr(p, elegida.get("effects"))
        elif tipo == "run":
            self.correr_script(p, ef["value"])
        elif tipo == "add_variable":
            store, k = self._store(p, ef["var"])
            store[k] = store.get(k, 0.0) + self._valor(p, ef["value"])
        elif tipo == "set_variable":
            store, k = self._store(p, ef["var"])
            store[k] = self._valor(p, ef["value"])
        elif tipo == "clamp":
            store, k = self._store(p, ef["var"])
            store[k] = min(max(store.get(k, 0.0), float(ef.get("min", -1e18))), float(ef.get("max", 1e18)))
        elif tipo == "math":
            self._math(p, ef.get("ops") or [])
        elif tipo == "flag":
            p.flags[ef["value"]] = m + meses(ef["days"]) if ef.get("days") else None
            p.flags_desde[ef["value"]] = m
        elif tipo == "clear_flag":
            p.flags.pop(ef["value"], None)
        elif tipo == "global_flag":
            self.flags_globales.add(ef["value"])
        elif tipo == "add_stability":
            p.estabilidad = min(1.0, max(0.0, p.estabilidad + float(ef["value"])))
        elif tipo == "event":
            objetivo = ef.get("target")
            destino = self.paises.get(objetivo) if objetivo else p
            if destino is not None:
                self.evento(destino, ef["id"])
        elif tipo == "every_country":
            for otro in list(self.paises.values()):
                if self.cumple(otro, ef.get("when"), root=p):
                    self.correr(otro, ef.get("effects"))
        elif tipo == "wargoal":
            self.contar(f"objetivo_de_guerra_contra:{p.tag if ef.get('target') in (None, 'ROOT') else ef['target']}")
        else:
            self.ignorados[tipo] = self.ignorados.get(tipo, 0) + 1

    def _math(self, p: Pais, ops: list) -> None:
        for op, var, *resto in ops:
            store, k = self._store(p, var)
            x = store.get(k, 0.0)
            v = self._valor(p, resto[0]) if resto else 0.0
            if op == "set":
                x = v
            elif op == "add":
                x += v
            elif op == "sub":
                x -= v
            elif op == "mul":
                x *= v
            elif op == "div":
                x = x / v if v else x
            elif op == "round":
                x = float(round(x))
            elif op in ("min", "max"):
                x = min(x, v) if op == "min" else max(x, v)
            store[k] = x

    # -- eventos ------------------------------------------------------------

    def evento(self, pais: Pais, eid: str) -> None:
        pais.registro.append((self.mes, eid))
        ev = self._eventos.get(eid)
        if ev is None:
            self.ignorados[f"evento:{eid}"] = self.ignorados.get(f"evento:{eid}", 0) + 1
            return
        self.correr(pais, ev.get("immediate"))
        opciones = ev.get("options") or []
        if opciones:
            pesos = [float(o.get("ai_chance", 1) or 0) for o in opciones]
            if sum(pesos) <= 0:
                pesos = [1.0] * len(opciones)
            self.correr(pais, self.rng.choices(opciones, weights=pesos)[0].get("effects"))

    # -- decisiones de la IA ------------------------------------------------

    def peso_ia(self, pais: Pais, ai: dict | None) -> float:
        """Factor de la IA con sus modificadores (decisiones y focos)."""
        if not ai:
            return 1.0
        peso = float(ai.get("factor", 1))
        for mod in ai.get("modifiers") or []:
            if self.cumple(pais, mod.get("when")):
                peso *= float(mod["factor"])
        return peso

    def decisiones_ia(self, pais: Pais, categorias: list[dict], prob_base: float, max_por_mes: int = 1) -> None:
        """Cada mes la IA mira las decisiones que puede tomar. Una decisión con
        factor f se toma con probabilidad 1-(1-prob_base)^f (prob_base cubre que
        el poder político alcance y compita con leyes y asesores)."""
        tomadas = 0
        candidatas = []
        for cat in categorias:
            paises = cat.get("country")
            if paises and pais.tag not in (paises if isinstance(paises, list) else [paises]):
                continue
            if not self.cumple(pais, cat.get("visible")):
                continue
            for d in cat.get("decisions") or []:
                if pais.enfriamiento.get(d["id"], -1) > self.mes:
                    continue
                if not self.cumple(pais, d.get("visible")) or not self.cumple(pais, d.get("available")):
                    continue
                peso = self.peso_ia(pais, d.get("ai"))
                if peso > 0:
                    candidatas.append((peso, d))
        self.rng.shuffle(candidatas)
        candidatas.sort(key=lambda x: -x[0])
        for peso, d in candidatas:
            if tomadas >= max_por_mes:
                break
            if self.rng.random() < 1 - (1 - prob_base) ** peso:
                tomadas += 1
                if d.get("fire_only_once"):
                    pais.enfriamiento[d["id"]] = 10 ** 6
                elif d.get("cooldown_days"):
                    pais.enfriamiento[d["id"]] = self.mes + meses(d["cooldown_days"])
                pais.registro.append((self.mes, f"decision:{d['id']}"))
                self.correr(pais, d.get("effects"))
