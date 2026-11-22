"""python3 -m tools.simulador.estabilidad_shd [--antes REV] [--salida ARCHIVO]

La estabilidad del Directorio (SHD) mes a mes, 2100-2119, y cuántas veces termina en
guerra civil (pedido 2026-11-22: "habría que triggerear más esas guerras civiles,
dificultar más la estabilidad para SHD... corré una simulación, tendría que dificultarse
mucho mantener la estabilidad, sin que sea un suplicio").

Qué sale del spec (se lee cada vez, así la simulación sigue al mod):
  - los espíritus del Directorio y su stability_factor (05_ideas), los focos que los dan
    y los add_stability de los focos (07_focus_trees, con sus días, prerrequisitos y
    exclusiones);
  - El Peso de la Armonía, El Peso de la Conquista y el Sobreestiramiento (con sus umbrales
    de regiones) y las medallas con estabilidad;
  - las chances de que estalle el Ultimátum de los Generales (crisis interna de todos y la
    mecha propia del Directorio), la chance de que el líder resista (meganations_lider.21)
    y el umbral de Siberia se Levanta.
Qué sale de supuestos_estabilidad_shd.yaml: cuántas regiones tiene en cada escenario,
cuándo proclama su forma final, cuándo le declara a Eurasia, el ritmo de los focos y lo
que pone el motor del juego (popularidad del partido, leyes), que se calibra con la
partida real del 2026-11-22.

--antes REV corre lo mismo con el spec de un commit de git (por ejemplo HEAD) y pone las
dos tablas lado a lado.
"""

from __future__ import annotations

import argparse
import random
import subprocess
import sys
import tarfile
import tempfile
from io import BytesIO
from pathlib import Path
from statistics import median

import yaml

from ..gen import specload

REPO = Path(__file__).resolve().parents[2]
SUPUESTOS = Path(__file__).with_name("supuestos_estabilidad_shd.yaml")


def mes(fecha) -> int:
    """2102.6 -> meses desde enero de 2100 (2102.6 = junio de 2102)."""
    s = str(fecha)
    anio, _, m = s.partition(".")
    return (int(anio) - 2100) * 12 + (int(m) - 1 if m else 0)


# ---------------------------------------------------------------------------- lo que dice el spec

def _todos(nodo):
    if isinstance(nodo, dict):
        yield nodo
        for v in nodo.values():
            yield from _todos(v)
    elif isinstance(nodo, list):
        for v in nodo:
            yield from _todos(v)


def _por_id(raw: dict, ident: str) -> dict:
    for d in _todos(raw):
        if d.get("id") == ident:
            return d
    raise KeyError(ident)


def _tabla_estab(raw: dict) -> dict[str, float]:
    """stability_factor de cada idea y modificador dinámico del spec (una pasada)."""
    out = {}
    for d in _todos(raw):
        mods = d.get("modifiers")
        if isinstance(d.get("id"), str) and isinstance(mods, dict):
            try:
                out.setdefault(d["id"], float(mods.get("stability_factor", 0) or 0))
            except (ValueError, TypeError):
                out.setdefault(d["id"], 0.0)  # sale de una variable
    return out


def _estab(raw: dict, ident: str, _cache: dict = {}) -> float:
    key = id(raw)
    if key not in _cache:
        _cache[key] = _tabla_estab(raw)
    return _cache[key].get(ident, 0.0)


def _es_del_directorio(when) -> bool:
    """Un `if` que pide otro país (la mecha de la HSN, la de la NAS...) no corre en el Directorio."""
    if not isinstance(when, dict):
        return True
    directos = [when] + [x for x in when.get("all") or [] if isinstance(x, dict)]
    tags = [d["tag"] for d in directos if "tag" in d]
    if tags and any(t != "SHD" for t in tags):
        return False
    for d in directos:
        ramas = [x for x in d.get("any") or [] if isinstance(x, dict)]
        if not ramas:
            continue
        # any: [{tag: HSN}, {all: [{tag: NAS}, ...]}]: alguna rama tiene que servirle al Directorio
        if not any(_es_del_directorio(x if "all" in x or "tag" in x else {"all": [x]}) for x in ramas):
            return False
    return True


def _reglas_crisis(raw: dict) -> list[tuple[float, float, float, str]]:
    """(desde, hasta, chance por mes, de dónde) de cada tirada que dispara el ultimátum."""
    se = {s["id"]: s for s in raw["decisions"]["scripted_effects"]}
    reglas = []

    def cond(when, lo, hi):
        for d in _todos(when or {}):
            if "stability_below" in d:
                hi = min(hi, float(d["stability_below"]))
            if "stability_at_least" in d:
                lo = max(lo, float(d["stability_at_least"]))
        return lo, hi

    def corre(efectos, lo, hi, donde, pila=()):
        for ef in efectos or []:
            tipo = ef.get("effect")
            if tipo == "run" and ef.get("value") in se and ef["value"] not in pila:
                if ef["value"] == "MEGANATIONS_crisis_estalla":
                    continue
                corre(se[ef["value"]]["effects"], lo, hi, ef["value"], pila + (ef["value"],))
            elif tipo == "if":
                if not _es_del_directorio(ef.get("when")):
                    continue
                l2, h2 = cond(ef.get("when"), lo, hi)
                corre(ef.get("then"), l2, h2, donde, pila)
                if ef.get("else"):
                    # el else de "estabilidad bajo X" es "X o más"
                    _, hthen = cond(ef.get("when"), 0.0, 9.0)
                    corre(ef["else"], max(lo, hthen) if hthen < 9 else lo, hi, donde, pila)
            elif tipo == "random":
                total = sum(float(o["weight"]) for o in ef["options"])
                for o in ef["options"]:
                    if any(x.get("effect") == "run" and x.get("value") == "MEGANATIONS_crisis_estalla"
                           for x in o.get("effects") or []):
                        reglas.append((lo, hi, float(o["weight"]) / total, donde))

    corre(se["MEGANATIONS_crisis_interna"]["effects"], 0.0, 9.0, "crisis interna (todos)")
    corre(se["SHD_pulso_directorio"]["effects"], 0.0, 9.0, "mecha del Directorio")
    return [r for r in reglas if r[1] < 9]


def leer_spec(raw: dict) -> dict:
    arbol = raw["focus_trees"]["trees"]["SHD"]
    focos = {f["id"]: f for rama in arbol["branches"] for f in rama.get("focuses") or []}
    gig = _por_id(raw, "MEGANATIONS_gigante_pulso")
    umbrales = [int(d["states_at_least"]) for d in _todos(gig) if "states_at_least" in d]
    e21 = [e for e in raw["events"]["namespaces"]["meganations_lider"]["events"] if e["id"] == 21][0]
    resiste = sum(float(o.get("ai_chance", 1)) for o in e21["options"]
                  if any(x.get("value") == "MEGANATIONS_lider_guerra_civil" for x in o["effects"]))
    total = sum(float(o.get("ai_chance", 1)) for o in e21["options"])
    sib = _por_id(raw, "SIB_al_declarar")
    sib_umbral = min(float(d["stability_below"]) for d in _todos(sib) if "stability_below" in d)
    medallas = 0.0
    for d in _todos(raw["medallas"]):
        b = d.get("bonus") or {}
        if "stability_factor" in b and ("SHD" in str(d.get("tile", "")) or "SHD" in str(d.get("unlock", ""))):
            medallas += float(b["stability_factor"])
    conquista = None
    try:
        conquista = _por_id(raw, "SHD_peso_conquista_calculo")["effects"]
    except KeyError:
        pass
    return {
        "focos": focos,
        "ideas": _tabla_estab(raw),
        "peso_armonia": _estab(raw, "MEGANATIONS_peso_de_la_armonia"),
        "sobre": (_estab(raw, "MEGANATIONS_sobreestiramiento"), _estab(raw, "MEGANATIONS_sobreestiramiento_grave")),
        "gigante_umbrales": (umbrales[0], umbrales[1], umbrales[-1]),
        "gigante_en_forma_final": not any("SHD_forma_final" in str(d) for d in _todos(gig.get("effects", [])[:1])),
        "conquista": conquista,
        "crisis": _reglas_crisis(raw),
        "resiste": resiste / total,
        "siberia": sib_umbral,
        "medallas": medallas,
    }


def peso_conquista(efectos, regiones: float) -> float:
    """Corre las cuentas de SHD_peso_conquista_calculo con num_owned_states = regiones."""
    if not efectos:
        return 0.0
    v: dict[str, float] = {}
    val = lambda x: regiones if x == "num_owned_states" else (v.get(x, 0.0) if isinstance(x, str) else float(x))
    for ef in efectos:
        if ef.get("effect") == "math":
            for op, var, x in ef["ops"]:
                if op == "set": v[var] = val(x)
                elif op == "add": v[var] = v.get(var, 0) + val(x)
                elif op == "sub": v[var] = v.get(var, 0) - val(x)
                elif op == "mul": v[var] = v.get(var, 0) * val(x)
                elif op == "div": v[var] = v.get(var, 0) / val(x)
        elif ef.get("effect") == "clamp":
            v[ef["var"]] = min(float(ef.get("max", 1e9)), max(float(ef.get("min", -1e9)), v.get(ef["var"], 0)))
    return v.get("SHD_peso_conquista", 0.0)


# ---------------------------------------------------------------------------- una partida

def _interp(tabla: dict, m: int, _cache: dict = {}) -> float:
    key = id(tabla)
    if key not in _cache:
        _cache[key] = sorted((mes(k), float(x)) for k, x in tabla.items())
    pts = _cache[key]
    if m <= pts[0][0]:
        return pts[0][1]
    for (m0, a), (m1, b) in zip(pts, pts[1:]):
        if m0 <= m <= m1:
            return a + (b - a) * (m - m0) / max(1, m1 - m0)
    return pts[-1][1]


def _focos_hechos(focos: dict, sup: dict, rng: random.Random) -> dict[str, int]:
    """Mes en que termina cada foco en esta corrida (los de la rama excluida no se hacen)."""
    excluidos = set()
    for fid, f in focos.items():
        for otro in f.get("mutually_exclusive") or []:
            if fid in excluidos or otro in excluidos or otro not in focos:
                continue
            excluidos.add(rng.choice([fid, otro]))
    fin: dict[str, float | None] = {}

    def termina(fid, pila=()):
        if fid in fin:
            return fin[fid]
        f = focos.get(fid)
        if f is None or fid in excluidos or fid in pila:
            fin[fid] = None
            return None
        antes = 0.0
        for p in f.get("prerequisites") or []:
            t = termina(p, pila + (fid,))
            if t is None:
                fin[fid] = None
                return None
            antes = max(antes, t)
        if f.get("prerequisites_any"):
            ts = [t for t in (termina(p, pila + (fid,)) for p in f["prerequisites_any"]) if t is not None]
            if not ts:
                fin[fid] = None
                return None
            antes = max(antes, min(ts))
        lo, hi = sup["focos_desvio"]
        fin[fid] = antes + float(f.get("days", 70)) * float(sup["focos_ritmo"]) * rng.uniform(lo, hi)
        return fin[fid]

    return {fid: int(t / 30.4) for fid in focos if (t := termina(fid)) is not None}


def correr(spec: dict, sup: dict, esc: dict, rng: random.Random, motor: float) -> dict:
    meses_t = int(sup["meses"])
    hechos = _focos_hechos(spec["focos"], sup, rng)
    # base (add_stability) e ideas (stability_factor) por mes
    base_suma = [0.0] * (meses_t + 1)
    ideas_on: dict[str, int] = {}
    ideas_off: dict[str, int] = {}
    for fid, m in hechos.items():
        for r in spec["focos"][fid].get("reward") or []:
            if r.get("effect") == "add_stability" and m <= meses_t:
                base_suma[m] += float(r["value"])
            elif r.get("effect") == "add_ideas":
                ideas_on[r["value"]] = min(m, ideas_on.get(r["value"], 10**6))
            elif r.get("effect") == "swap_ideas":
                ideas_off[r["remove"]] = m
                ideas_on[r["add"]] = min(m, ideas_on.get(r["add"], 10**6))
    forma = mes(esc["forma_final"]) if esc.get("forma_final") else 10**6
    for idea, s in (sup.get("espiritus_externos") or {}).items():
        if s.get("en_forma_final"):
            ideas_on[idea] = forma
        elif rng.random() < float(s["chance"]):
            ideas_on[idea] = mes(s["desde"]) + rng.randint(0, 11)
    if "SHD_armonia_perfecta" in ideas_on and "SHD_armonia_parcial" in ideas_on:
        ideas_off["SHD_armonia_parcial"] = ideas_on["SHD_armonia_perfecta"]
    medalla_m = hechos.get("SHD_el_caudal_perfecto", 10**6)
    # eventos sueltos: un monto por año, repartido en el año
    ev = sup["eventos_por_anio"]
    for anio in range(meses_t // 12 + 1):
        monto = rng.gauss(float(ev["media"]), float(ev["desvio"]))
        m = min(meses_t, anio * 12 + rng.randint(0, 11))
        base_suma[m] += monto

    curva, guerra_civil, siberia = [], None, False
    base = 0.0
    espera = -1
    cayo_lider = False
    declara = mes(esc["declara_a_eurasia"]) if esc.get("declara_a_eurasia") else None
    gig_on, gig_grave, gig_off = spec["gigante_umbrales"]
    gigante = grave = False
    regiones = [_interp(esc["regiones"], m) for m in range(meses_t + 1)]
    conq = [peso_conquista(spec["conquista"], r) for r in regiones]
    for m in range(meses_t + 1):
        base = min(1.0, max(-1.0, base + base_suma[m]))
        reg = regiones[m]
        mods = spec["peso_armonia"] + conq[m]
        for idea, desde in ideas_on.items():
            if desde <= m < ideas_off.get(idea, 10**6):
                mods += spec["ideas"].get(idea, 0.0)
        if m >= medalla_m:
            mods += spec["medallas"]
        en_forma = m >= forma
        if reg >= gig_on and not en_forma:
            gigante = True
        if gigante and (reg < gig_off or en_forma):
            gigante = grave = False
        if gigante and reg >= gig_grave:
            grave = True
        mods += (spec["sobre"][0] if gigante else 0) + (spec["sobre"][1] if grave else 0)
        rampa = min(1.0, m / 12)
        estab = min(1.0, max(0.0, motor * rampa + spec["arranque"] + base + mods))
        curva.append(estab)
        if declara is not None and m == declara and estab < spec["siberia"]:
            siberia = True
        if guerra_civil is None and m >= 5 and m > espera:
            for lo, hi, p, _ in spec["crisis"]:
                if lo <= estab < hi and rng.random() < p:
                    espera = m + 12
                    if rng.random() < spec["resiste"]:
                        guerra_civil = m
                    else:
                        base -= 0.10
                        cayo_lider = True
                    break
    return {"curva": curva, "guerra_civil": guerra_civil, "siberia": siberia, "cayo_lider": cayo_lider}


# ---------------------------------------------------------------------------- calibración e informe

def _arranque(spec: dict, sup: dict) -> float:
    # en enero de 2100 el juego mostró 67%: lo que no es del mod en ese momento (el único
    # modificador del mod al arrancar es El Peso de la Armonía)
    return float(sup["partida_estabilidad"][2100]) - spec["peso_armonia"]


def calibrar(spec: dict, sup: dict) -> float:
    """Lo que el juego suma en el primer año (partido, leyes), para que el spec de la partida
    dé lo que mostró la partida en enero de 2101."""
    objetivo = float(sup["partida_estabilidad"][2101])
    esc = sup["escenarios"]["como_la_partida"]
    lo, hi = -0.5, 0.8
    for _ in range(24):
        mid = (lo + hi) / 2
        rng = random.Random(f"{sup['semilla']}:calibrar")
        vals = [correr(spec, sup, esc, rng, mid)["curva"][12] for _ in range(300)]
        if median(vals) < objetivo:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def simular(spec: dict, sup: dict, motor: float) -> dict:
    out = {}
    for nombre, esc in sup["escenarios"].items():
        rng = random.Random(f"{sup['semilla']}:{nombre}")
        corridas = [correr(spec, sup, esc, rng, motor) for _ in range(int(sup["corridas"]))]
        out[nombre] = corridas
    return out


def _fila(corridas: list[dict], anio: int) -> tuple[float, float, float, float]:
    m = min(anio * 12, len(corridas[0]["curva"]) - 1)
    vals = sorted(c["curva"][m] for c in corridas)
    n = len(vals)
    gc = sum(1 for c in corridas if c["guerra_civil"] is not None and c["guerra_civil"] <= m) / n
    return vals[n // 2], vals[n // 10], vals[(9 * n) // 10], gc


def informe(res_d: dict, res_a: dict | None, spec_d: dict, spec_a: dict | None, motor: float, sup: dict) -> str:
    L = ["# Estabilidad del Directorio: simulación 2100-2119", "",
         f"{sup['corridas']} partidas por escenario. Lo que pone el juego en el primer año (partido, leyes) "
         f"calibrado con la partida del 2026-11-22: +{motor * 100:.0f} puntos.", ""]
    L.append("Chances de que estalle el Ultimátum de los Generales (por mes):")
    for lo, hi, p, d in spec_d["crisis"]:
        L.append(f"  - estabilidad {lo * 100:.0f}-{hi * 100:.0f}%: {p * 100:.1f}% ({d})")
    L.append(f"  - si estalla, el líder resiste (guerra civil) el {spec_d['resiste'] * 100:.0f}% de las veces; si no, cae (-10%).")
    L.append(f"  - Siberia se levanta si le declara a Eurasia con menos de {spec_d['siberia'] * 100:.0f}%.")
    L.append("")
    for nombre in res_d:
        L.append(f"## {nombre.replace('_', ' ')}")
        reg = sup["escenarios"][nombre]["regiones"]
        L.append("")
        cab = "| año | regiones | " + ("antes: estab. (10-90%) | antes: guerra civil | " if res_a else "") + \
              "después: estab. (10-90%) | después: guerra civil |"
        L.append(cab)
        L.append("|" + "|".join(["---"] * (cab.count("|") - 1)) + "|")
        for anio in (0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 19):
            r = _interp(reg, anio * 12)
            fila = f"| {2100 + anio} | {r:.0f} | "
            if res_a:
                md, p10, p90, gc = _fila(res_a[nombre], anio)
                fila += f"{md * 100:.0f}% ({p10 * 100:.0f}-{p90 * 100:.0f}) | {gc * 100:.0f}% | "
            md, p10, p90, gc = _fila(res_d[nombre], anio)
            fila += f"{md * 100:.0f}% ({p10 * 100:.0f}-{p90 * 100:.0f}) | {gc * 100:.0f}% |"
            L.append(fila)
        for etiqueta, res in (("antes", res_a), ("después", res_d)):
            if not res:
                continue
            cs = res[nombre]
            n = len(cs)
            bajo60 = sum(sum(1 for x in c["curva"] if x < 0.6) for c in cs) / n / 12
            sib = sum(1 for c in cs if c["siberia"]) / n
            cae = sum(1 for c in cs if c["cayo_lider"]) / n
            L.append(f"- {etiqueta}: {bajo60:.1f} años bajo 60% en promedio; Siberia se levanta en el "
                     f"{sib * 100:.0f}%; el líder cae por un ultimátum en el {cae * 100:.0f}%.")
        L.append("")
    return "\n".join(L)


def _spec_de(rev: str) -> dict:
    datos = subprocess.run(["git", "-C", str(REPO), "archive", rev, "spec"], check=True,
                           capture_output=True).stdout
    tmp = tempfile.mkdtemp(prefix="spec_antes_")
    with tarfile.open(fileobj=BytesIO(datos)) as tar:
        tar.extractall(tmp, filter="data")
    return specload.load(Path(tmp) / "spec").raw


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m tools.simulador.estabilidad_shd")
    ap.add_argument("--antes", default=None, help="commit de git con el spec de antes (ej. HEAD)")
    ap.add_argument("--salida", default=None)
    args = ap.parse_args(argv)
    sup = yaml.safe_load(SUPUESTOS.read_text(encoding="utf-8"))
    spec_d = leer_spec(specload.load(REPO / "spec").raw)
    spec_a = leer_spec(_spec_de(args.antes)) if args.antes else None
    # lo que no es del mod en enero de 2100 sale del spec que jugó la partida; los cambios del
    # mod (por ejemplo un Peso de la Armonía más pesado) se suman encima
    otros = _arranque(spec_a or spec_d, sup)
    for s in (spec_d, spec_a):
        if s:
            s["arranque"] = otros
    # el motor se calibra con el spec que jugó la partida (el de antes, si está)
    motor = calibrar(spec_a or spec_d, sup)
    res_d = simular(spec_d, sup, motor)
    res_a = simular(spec_a, sup, motor) if spec_a else None
    texto = informe(res_d, res_a, spec_d, spec_a, motor, sup)
    if args.salida:
        Path(args.salida).write_text(texto + "\n", encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
