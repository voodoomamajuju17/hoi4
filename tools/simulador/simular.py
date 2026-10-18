"""Las tres simulaciones: ramas políticas, el mundo (rearme, sucesión, líder) y
la crisis del siglo. Cada una tira los dados de la IA muchas veces con los
números del spec y devuelve conteos; informe.py los pasa a tablas."""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from .motor import Mundo, Pais, POTENCIAS, fecha_de, mes_de

SUPUESTOS = Path(__file__).with_name("supuestos.yaml")


def cargar_supuestos(path: Path | str | None = None) -> dict:
    return yaml.safe_load(Path(path or SUPUESTOS).read_text(encoding="utf-8"))


def _estado(sup: dict, tag: str) -> dict:
    base = dict((sup.get("estado") or {}).get("resto") or {})
    base.update((sup.get("estado") or {}).get(tag) or {})
    return base


def valores_iniciales(raw: dict) -> dict[str, float]:
    """Los `start` de las variables de 06_mechanics (ASC_computo arranca en 30...)."""
    salida = {}
    for mec in raw["mechanics"].get("mechanics") or []:
        for v in mec.get("variables") or []:
            if isinstance(v, dict) and v.get("name") and v.get("start") is not None:
                salida[v["name"]] = float(v["start"])
        v = mec.get("variable")
        if isinstance(v, dict) and v.get("name") and v.get("start") is not None:
            salida[v["name"]] = float(v["start"])
    return salida


def iniciar(mundo: Mundo, pais: Pais, sup: dict) -> None:
    est = _estado(sup, pais.tag)
    pais.estabilidad = float((est.get("estabilidad") or {}).get("inicio", 0.6))
    for var, valor in valores_iniciales(mundo.raw).items():
        if var.startswith(pais.tag + "_"):
            pais.variables[var] = valor
    for var, cfg in (est.get("variables") or {}).items():
        if "inicio" in cfg:
            pais.variables[var] = float(cfg["inicio"])


def evolucionar(mundo: Mundo, pais: Pais, sup: dict, guerra_fija: str | None = None) -> None:
    """Un mes del estado de juguete: estabilidad, guerra, variables, flags."""
    rng, m = mundo.rng, mundo.mes
    est = _estado(sup, pais.tag)
    e = est.get("estabilidad") or {}
    pais.estabilidad += 0.05 * (float(e.get("media", 0.55)) - pais.estabilidad) + rng.gauss(0, float(e.get("sd", 0.03)))
    pais.estabilidad = min(1.0, max(0.0, pais.estabilidad))
    if guerra_fija == "always":
        pais.en_guerra = True
    elif guerra_fija == "never":
        pais.en_guerra = False
    else:
        g = est.get("guerra") or {}
        if pais.en_guerra:
            pais.en_guerra = rng.random() >= float(g.get("paz", 0.05))
        elif m >= mes_de(g.get("desde", "2100.1.1")):
            pais.en_guerra = rng.random() < float(g.get("riesgo", 0.0))
    for var, cfg in (est.get("variables") or {}).items():
        x = pais.variables.get(var, 0.0) + float(cfg.get("por_mes", 0)) + rng.gauss(0, float(cfg.get("sd", 0)))
        pais.variables[var] = min(float(cfg.get("max", 1e9)), max(float(cfg.get("min", -1e9)), x))
    for flag, cfg in (est.get("flags") or {}).items():
        if flag not in pais.flags and m >= mes_de(cfg.get("desde", "2100.1.1")) and rng.random() < float(cfg["riesgo"]):
            pais.flags[flag] = None
            pais.flags_desde[flag] = m


# ---------------------------------------------------------------------------
# Ramas políticas (y económicas): los pares de focos excluyentes
# ---------------------------------------------------------------------------

def pares_excluyentes(raw: dict) -> list[dict]:
    """Cada par de focos excluyentes con su rama, peso de rama y apertura."""
    pares, vistos = [], set()
    for tag, arbol in (raw["focus_trees"].get("trees") or {}).items():
        focos, rama_de, peso_rama = {}, {}, {}
        for rama in arbol.get("branches") or []:
            for f in rama.get("focuses") or []:
                focos[f["id"]] = f
                rama_de[f["id"]] = rama.get("id")
                peso_rama[f["id"]] = rama.get("ai_factor")
        fin: dict[str, float] = {}

        def termina(fid: str, pila: tuple = ()) -> float:
            if fid in fin:
                return fin[fid]
            f = focos.get(fid)
            if f is None or fid in pila:
                return 0.0
            antes = max([termina(p, pila + (fid,)) for p in f.get("prerequisites") or []] or [0.0])
            if f.get("prerequisites_any"):
                antes = max(antes, min(termina(p, pila + (fid,)) for p in f["prerequisites_any"]))
            fin[fid] = antes + float(f.get("days", 70))
            return fin[fid]

        for fid, f in focos.items():
            for otro in f.get("mutually_exclusive") or []:
                clave = frozenset((fid, otro))
                if clave in vistos or otro not in focos:
                    continue
                vistos.add(clave)
                a, b = focos[fid], focos[otro]
                abre = max(termina(p) for p in (a.get("prerequisites") or []) + (b.get("prerequisites") or []) or [""])
                pares.append({
                    "tag": tag,
                    "focos": [a, b],
                    "ramas": [rama_de[fid], rama_de[otro]],
                    "peso_rama": [peso_rama[fid], peso_rama[otro]],
                    "abre_dias": abre,
                })
    return pares


def _peso_foco(mundo: Mundo, pais: Pais, foco: dict, peso_rama: float | None) -> float:
    if foco.get("available") and not mundo.cumple(pais, foco["available"]):
        return 0.0
    return mundo.peso_ia(pais, foco.get("ai")) * float(peso_rama if peso_rama is not None else 1)


def simular_focos(raw: dict, sup: dict, corridas: int | None = None) -> list[dict]:
    corridas = corridas or int(sup["corridas"])
    ritmo = float(sup.get("focos_ritmo", 1.6))
    q = float(sup.get("focos_eleccion_mensual", 0.35))
    filas = []
    for i, par in enumerate(pares_excluyentes(raw)):
        tag = par["tag"]
        abre = int(par["abre_dias"] * ritmo / 30.4)
        fila = {"tag": tag, "a": par["focos"][0]["id"], "b": par["focos"][1]["id"], "abre": fecha_de(abre),
                "ramas": par["ramas"], "escenarios": {}}
        for nombre, esc in (sup.get("escenarios_focos") or {"ia_tipica": {}}).items():
            rng = random.Random(f"{sup.get('semilla', 0)}:{tag}:{i}:{nombre}")
            cuenta = Counter()
            for _ in range(corridas):
                mundo = Mundo(raw, sup, rng, paises=[tag])
                pais = mundo.paises[tag]
                iniciar(mundo, pais, sup)
                elegido = "ninguno"
                for m in range(0, 12 * 100):
                    mundo.mes = m
                    evolucionar(mundo, pais, sup, (esc or {}).get("guerra"))
                    if m < abre or rng.random() >= q:
                        continue
                    pesos = [_peso_foco(mundo, pais, f, w) for f, w in zip(par["focos"], par["peso_rama"])]
                    if sum(pesos) <= 0:
                        continue
                    elegido = rng.choices([fila["a"], fila["b"]], weights=pesos)[0]
                    break
                cuenta[elegido] += 1
            fila["escenarios"][nombre] = {k: v / corridas for k, v in cuenta.items()}
        filas.append(fila)
    return filas


# ---------------------------------------------------------------------------
# El mundo: Rearme Secreto (las ocho), Sucesión del EFE y salud del líder
# ---------------------------------------------------------------------------

def _categorias(raw: dict, ids: list[str]) -> list[dict]:
    por_id = {c["id"]: c for c in raw["decisions"].get("categories") or []}
    return [por_id[i] for i in ids if i in por_id]


def simular_mundo(raw: dict, sup: dict, corridas: int | None = None) -> dict:
    corridas = corridas or int(sup["corridas"])
    hasta = mes_de(sup.get("hasta", "2140.1.1"))
    p_base = float(sup.get("decisiones_prob_base", 0.15))
    rearme = _categorias(raw, ["MEGANATIONS_rearme_category"])
    efe_cats = _categorias(raw, ["EFE_sucesion_category", "MEGANATIONS_lider_category"])
    rng = random.Random(f"{sup.get('semilla', 0)}:mundo")

    fin_disimulo = []                     # mes del tercer descubrimiento (None si no pasa)
    descubiertos = Counter()              # país -> veces descubierto (total de corridas)
    primer_descubierto = Counter()
    muerte, heredero_al_morir, heredero_elegido = [], Counter(), Counter()
    colapsos, ignorados, supuestos = Counter(), Counter(), Counter()
    exposicion_max = {t: [] for t in POTENCIAS}

    for _ in range(corridas):
        mundo = Mundo(raw, sup, rng)
        for p in mundo.paises.values():
            iniciar(mundo, p, sup)
        fin, murio, eligio = None, None, None
        maxima = Counter()
        for m in range(hasta):
            mundo.mes = m
            for tag in POTENCIAS:
                p = mundo.paises[tag]
                evolucionar(mundo, p, sup)
                mundo.correr_script(p, "MEGANATIONS_rearme_pulso")
                if tag == "EFE":
                    mundo.correr_script(p, "EFE_pulso_v4")
                    mundo.correr_script(p, "MEGANATIONS_lider_pulso")
                    if murio is None and p.tiene_flag("EFE_sucesion_hecha", m):
                        murio = m
                        cual = next((h for h in ("EFE_heredero_tupa", "EFE_heredero_pereira", "EFE_heredero_etchegaray")
                                     if p.tiene_flag(h, m)), "sin_heredero")
                        heredero_al_morir[cual] += 1
                    mundo.decisiones_ia(p, efe_cats, p_base)
                    if eligio is None:
                        eligio = next((h for h in ("EFE_heredero_tupa", "EFE_heredero_pereira", "EFE_heredero_etchegaray")
                                       if p.tiene_flag(h, m)), None)
                        if eligio:
                            heredero_elegido[(eligio, m // 12 + 2100)] += 1
                mundo.decisiones_ia(p, rearme, p_base)
                maxima[tag] = max(maxima[tag], mundo.var(p, "MN_rearme"))
            if fin is None and "MN_disimulo_terminado" in mundo.flags_globales:
                fin = m
        fin_disimulo.append(fin)
        primero = None
        for tag, p in mundo.paises.items():
            veces = [mm for mm, e in p.registro if e == "meganations_v4.1"]
            descubiertos[tag] += len(veces)
            if veces and (primero is None or veces[0] < primero[0]):
                primero = (veces[0], tag)
            exposicion_max[tag].append(maxima[tag])
        if primero:
            primer_descubierto[primero[1]] += 1
        efe = mundo.paises["EFE"]
        colapsos[sum(1 for _, e in efe.registro if e == "meganations_lider.22")] += 1
        if murio is None:
            heredero_al_morir["vivo_en_" + str(2100 + hasta // 12)] += 1
        muerte.append(murio)
        ignorados.update(mundo.ignorados)
        supuestos.update(mundo.supuestos_usados)

    return {
        "corridas": corridas, "hasta": fecha_de(hasta),
        "fin_disimulo": fin_disimulo, "descubiertos": descubiertos, "primer_descubierto": primer_descubierto,
        "exposicion_max": exposicion_max, "muerte": muerte, "heredero_al_morir": heredero_al_morir,
        "heredero_elegido": heredero_elegido, "colapsos": colapsos,
        "ignorados": ignorados, "supuestos": supuestos,
    }


# ---------------------------------------------------------------------------
# La crisis del siglo (2106-2200)
# ---------------------------------------------------------------------------

def _bloque_crisis(raw: dict) -> dict:
    efectos = {e["id"]: e for e in raw["decisions"].get("scripted_effects") or []}
    for ef in efectos["MEGANATIONS_eventos_mundiales"].get("effects") or []:
        if "MEGANATIONS_crisis_tardia" in json.dumps(ef.get("when"), ensure_ascii=False):
            return ef
    raise KeyError("no encontré el bloque de la crisis del siglo en MEGANATIONS_eventos_mundiales")


def simular_crisis(raw: dict, sup: dict, corridas: int | None = None) -> dict:
    corridas = corridas or int(sup["corridas"])
    bloque = _bloque_crisis(raw)
    rng = random.Random(f"{sup.get('semilla', 0)}:crisis")
    desde, hasta = mes_de("2106.1.1"), mes_de("2200.1.1")
    por_tipo, seguidas, racha_max, total = Counter(), [], Counter(), []
    for _ in range(corridas):
        mundo = Mundo(raw, sup, rng)
        for m in range(desde - 1, hasta):
            mundo.mes = m
            for tag in POTENCIAS:   # el bloque corre en el pulso de cada potencia
                mundo._efecto(mundo.paises[tag], bloque)
        serie = [e for _, e in mundo.paises["EFE"].registro if e.startswith("meganations_mundo.")]
        total.append(len(serie))
        por_tipo.update(serie)
        repetidas = sum(1 for x, y in zip(serie, serie[1:]) if x == y)
        seguidas.append(repetidas)
        mejor, actual = 1 if serie else 0, 1
        for x, y in zip(serie, serie[1:]):
            actual = actual + 1 if x == y else 1
            mejor = max(mejor, actual)
        racha_max[mejor] += 1
    return {"corridas": corridas, "total": total, "por_tipo": por_tipo, "seguidas": seguidas, "racha_max": racha_max,
            "titulos": _titulos(raw, por_tipo)}


def _titulos(raw: dict, ids: Any) -> dict[str, str]:
    salida = {}
    ns = (raw["events"].get("namespaces") or {})
    for eid in ids:
        nombre, _, num = eid.rpartition(".")
        for ev in (ns.get(nombre) or {}).get("events") or []:
            if str(ev["id"]) == num:
                salida[eid] = ((ev.get("title") or {}).get("spanish")) or eid
    return salida
