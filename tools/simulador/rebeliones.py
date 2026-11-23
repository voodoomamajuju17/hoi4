"""python3 -m tools.simulador.rebeliones [--corridas N] [--salida ARCHIVO]

Qué chance tiene cada nación jugable de partirse entre 2100 y 2120: guerras civiles, divisiones (una parte se
va sin guerra civil), golpes (el líder cae) y los finales de las aventuras (pedido 2026-11-23: "calculame la
probabilidad de cada rebelión/guerra civil/división/golpe para cada nación jugable").

Qué sale del spec (se lee cada vez, así sigue al mod):
  - el Ultimátum de los Generales: la chance por mes con estabilidad bajo 50% y bajo 35%
    (MEGANATIONS_crisis_ultimatum), la mecha de la HSN y la NAS, las dos del Directorio (SHD_pulso_directorio),
    la espera de un año (MEGANATIONS_crisis_estalla) y cuánto resiste la IA (meganations_lider.21);
  - la ruta forzada del EFE, la APF y Roma (MEGANATIONS_crisis_rutas);
  - el Rumor de Golpe: cada cuánto sale un evento del líder, entre cuántos, y la chance de que termine en
    ultimátum (meganations_lider.3);
  - qué rebelión sale de cada potencia (MEGANATIONS_lider_guerra_civil): en la FCU se van las Zonas (división),
    en la Comuna arrancan los Hijos de Odín;
  - las aventuras: cada capítulo, opción y final, y dónde hay una rebelión o una crisis.
Qué sale de supuestos_rebeliones.yaml: la estabilidad (tres escenarios) y lo que depende de las barras propias.
Qué sale de SIMULADOR_IA.md: qué rama política elige la IA (columna "IA típica").
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

from ..gen import specload

REPO = Path(__file__).resolve().parents[2]
SUPUESTOS = Path(__file__).with_name("supuestos_rebeliones.yaml")
POTENCIAS = ["EFE", "ASC", "FCU", "HSN", "NAS", "SHD", "APF", "NRE"]
NOMBRES = {"EFE": "Imperio Ecofascista (EFE)", "ASC": "Comuna Algorítmica (ASC)", "FCU": "Unión Corporativa (FCU)",
           "HSN": "Liga Hanseática del Mar (HSN)", "NAS": "Imperio del Sol (NAS)", "SHD": "Directorio (SHD)",
           "APF": "Federación Panafricana (APF)", "NRE": "Nueva Roma (NRE)"}


def mes(fecha) -> int:
    """2102.6 -> meses desde enero de 2100."""
    anio, _, m = str(fecha).partition(".")
    return (int(anio) - 2100) * 12 + (int(m) - 1 if m else 0)


def _todos(nodo):
    if isinstance(nodo, dict):
        yield nodo
        for v in nodo.values():
            yield from _todos(v)
    elif isinstance(nodo, list):
        for v in nodo:
            yield from _todos(v)


def _script(raw: dict, sid: str) -> list:
    for s in raw["decisions"]["scripted_effects"]:
        if s["id"] == sid:
            return s["effects"]
    raise KeyError(sid)


def _evento(raw: dict, ns: str, eid: int) -> dict:
    evs = raw["events"]["namespaces"][ns]
    evs = evs["events"] if isinstance(evs, dict) else evs
    return next(e for e in evs if e.get("id") == eid)


def _chance_de(random_ef: dict) -> float:
    """La chance de la opción que hace algo en un `random` de dos (una vacía y otra con efectos)."""
    total = sum(float(o["weight"]) for o in random_ef["options"])
    hace = sum(float(o["weight"]) for o in random_ef["options"] if o.get("effects"))
    return hace / total


# ---------------------------------------------------------------------------- lo que dice el spec

def leer_spec(raw: dict) -> dict:
    out: dict = {}
    # el Ultimátum: bajo 35% / bajo 50%, y la mecha de la HSN y la NAS
    ult = _script(raw, "MEGANATIONS_crisis_ultimatum")[0]["then"]
    assert ult[0]["when"] == {"stability_below": 0.35}, ult[0]["when"]
    out["ult_35"] = _chance_de(ult[0]["then"][0])
    out["ult_50"] = _chance_de(ult[0]["else"][0])
    out["mecha_hsn_nas"] = _chance_de(ult[1]["then"][0])
    interna = _script(raw, "MEGANATIONS_crisis_interna")[0]["when"]["all"]
    out["umbral"] = next(c["stability_below"] for c in interna if "stability_below" in c)
    out["desde"] = mes(next(c["date_after"] for c in interna if "date_after" in c).rsplit(".", 1)[0])
    estalla = _script(raw, "MEGANATIONS_crisis_estalla")
    out["espera"] = round(next(e["days"] for e in estalla if e.get("value") == "MEGANATIONS_crisis_espera") / 30.4)
    # la ruta forzada
    rutas = _script(raw, "MEGANATIONS_crisis_rutas")
    out["ruta"] = _chance_de(next(e for e in _todos(rutas) if e.get("effect") == "random"))
    # las dos mechas del Directorio
    shd = [e for e in _todos(_script(raw, "SHD_pulso_directorio")) if e.get("effect") == "if"
           and any("stability_below" in c for c in (e.get("when") or {}).get("all") or [])]
    out["mechas_shd"] = [(next(c["stability_below"] for c in e["when"]["all"] if "stability_below" in c),
                          _chance_de(e["then"][0])) for e in shd]
    # cuánto resiste la IA
    l21 = _evento(raw, "meganations_lider", 21)
    total = sum(o["ai_chance"] for o in l21["options"])
    out["resiste"] = next(o["ai_chance"] for o in l21["options"]
                          if any(e.get("value") == "MEGANATIONS_lider_guerra_civil" for e in o["effects"])) / total
    # el Rumor de Golpe (meganations_peso.3): cada 150 días sale, con chance, una mala noticia del líder (El Peso del
    # Poder); el Rumor puede salir con estabilidad bajo 50% o con un líder de poca Astucia
    peso = next(e for e in _todos(_script(raw, "MEGANATIONS_lider_pulso")) if e.get("effect") == "random"
                and any(any(x.get("id") == "meganations_peso.3" for x in o.get("effects") or []) for o in e["options"]))
    espera = next(e for e in _todos(_script(raw, "MEGANATIONS_lider_pulso"))
                  if e.get("effect") == "flag" and e.get("value") == "MEGANATIONS_peso_espera")
    out["cada_meses"] = round(espera["days"] / 30.4)
    tregua = sum(o["weight"] for o in peso["options"] if not any(x.get("effect") == "event" for x in o["effects"]))
    noticias = [o for o in peso["options"] if any(x.get("effect") == "event" for x in o["effects"])]
    out["peso_tregua"], out["peso_noticias"] = tregua, len(noticias)
    l3 = _evento(raw, "meganations_peso", 3)
    total = sum(o["ai_chance"] for o in l3["options"])
    for o in l3["options"]:
        r = next((e for e in o["effects"] if e.get("effect") == "random"), None)
        if r:
            pw = sum(x["weight"] for x in r["options"])
            ult = sum(x["weight"] for x in r["options"] if any(y.get("id") == "meganations_lider.21" for y in x["effects"]))
            out["rumor_ultimatum"] = o["ai_chance"] / total * ult / pw
    # qué rebelión le toca a cada potencia
    out["rebelion"] = {}
    for e in _script(raw, "MEGANATIONS_lider_guerra_civil"):
        tag = e["when"]["tag"]
        eid = int(e["then"][0]["id"].rsplit(".", 1)[1])
        ev = _evento(raw, "meganations_lider", eid)
        cw = next((x for x in _todos(ev) if x.get("effect") == "civil_war"), None)
        out["rebelion"][tag] = (ev["title"]["spanish"], "guerra civil" if cw else
                                "crisis" if tag == "ASC" else "división")
    return out


def ramas_ia(md: Path) -> dict[str, float]:
    """La chance de que la IA elija la rama que termina en guerra civil (SIMULADOR_IA.md, IA típica)."""
    txt = md.read_text(encoding="utf-8")
    parte = txt.split("## Ramas políticas", 1)[1].split("##", 1)[0]
    filas = {}
    for linea in parte.splitlines():
        c = [x.strip() for x in linea.strip("|").split("|")]
        if len(c) == 7 and c[0] in POTENCIAS:
            filas[c[0]] = 1 - float(c[5].rstrip("%")) / 100   # la segunda rama ("contra")
    # EFE: Los Incendios de Gaia; APF: Los Consejos se Arman; NRE: La Legión Decide
    return {t: filas[t] for t in ("EFE", "APF", "NRE")}


# ---------------------------------------------------------------------------- una partida

def _cuando(rng, b) -> int:
    return rng.randint(mes(b["desde"]), mes(b["hasta"]))


def correr(tag: str, media: float, sp: dict, sup: dict, ramas: dict, rng: random.Random) -> dict:
    est = sup["estabilidad"]
    bar = sup["barras"]
    s = media
    pasa: dict[str, int] = {}          # lo que pasó -> mes
    espera = -1
    rebelde = False                    # la rebelión propia ya pasó (una vez por partida)
    # la rama política que lleva a la guerra civil
    elige = sup["ramas"]["abre"]
    while rng.random() >= sup["ramas"]["eleccion_mensual"]:
        elige += 1
    ruta_mala = tag in ramas and rng.random() < ramas[tag]
    ruta_hecha = None
    if ruta_mala:
        if tag == "EFE":                                    # los Incendios; después el monte, si llega
            if rng.random() < bar["EFE_monte"]["chance"]:
                ruta_hecha = max(_cuando(rng, bar["EFE_monte"]), elige + 1)
        else:                                               # el foco mismo es la guerra
            ruta_hecha = elige + sup["ramas"]["demora_foco_meses"]
    # lo que depende de las barras
    sueltos = {}
    if tag == "ASC" and rng.random() < bar["ASC_plan41"]["chance"]:
        sueltos["PLAN-41 se Desconecta (guerra civil)"] = _cuando(rng, bar["ASC_plan41"])
    if tag == "SHD" and rng.random() < bar["SHD_crecida"]["chance"]:
        sueltos["El Río se Desborda (guerra civil)"] = _cuando(rng, bar["SHD_crecida"])
    if tag == "FCU":
        sueltos["La Secesión de Meridian (guerra civil)"] = mes(2103.3) + 2   # cadena fija: 310 -> 311 -> 312
    if tag == "HSN":
        if rng.random() < bar["HSN_australia_satelite"]:
            sueltos["Nace la República Pirata (división: Australia)"] = mes(2103.6) + 2
        if rng.random() < bar["ZJP_se_separa"]["chance"]:
            sueltos["El Shogunato de los Astilleros (división: Japón)"] = _cuando(rng, bar["ZJP_se_separa"])
    if tag == "ASC" and rng.random() < bar["ZAL_renace"]["chance"]:
        sueltos["Albión renace (división, si pierde contra Roma)"] = _cuando(rng, bar["ZAL_renace"])
    for m in range(sup["meses"]):
        s += est["vuelta"] * (media - s) + rng.gauss(0, est["ruido"])
        s = min(1.0, max(0.0, s))
        for k, mm in sueltos.items():
            if mm == m and k not in pasa:
                # ya está en guerra civil (no se parte dos veces a la vez): en la FCU las Zonas y en la Comuna los
                # Hijos de Odín no son guerra civil; en la Comuna, la del Valhalla sí
                en_guerra = "ruta" in pasa or (rebelde and tag not in ("FCU", "ASC")) or any(
                    "Valhalla" in x for x in pasa)
                if "guerra civil" in k and en_guerra:
                    continue
                pasa[k] = m
        if ruta_hecha == m and "ruta" not in pasa:
            pasa["ruta"] = m
        ultimatum = False
        # el Rumor de Golpe: cada 150 días (El Peso del Poder), entre la tregua y las noticias que le tocan al líder
        if m >= 6 and m % sp["cada_meses"] == 0 and (s < 0.5 or rng.random() < sup["rumor"]["astucia_baja"]):
            otras = sum(rng.random() < sup["rumor"]["otras_noticias"] for _ in range(sp["peso_noticias"] - 1))
            if rng.random() < 1 / (sp["peso_tregua"] + 1 + otras):
                pasa.setdefault("rumor_sale", m)
                if rng.random() < sp["rumor_ultimatum"]:
                    ultimatum = True
                    pasa.setdefault("rumor", m)
        if m >= sp["desde"] and m > espera and not rebelde and "ruta" not in pasa:
            if s < sp["umbral"]:
                # la ruta forzada: con la rama elegida y el foco todavía sin hacer
                if ruta_mala and ruta_hecha is not None and m < ruta_hecha and (tag != "EFE" or m > elige) \
                        and rng.random() < sp["ruta"]:
                    pasa["ruta"] = m
                    espera = m + sp["espera"]
                    continue
                if tag in ("APF", "NRE") and not ruta_mala and m < elige and rng.random() < sp["ruta"]:
                    pasa["ruta"] = m                     # forzada antes de elegir la otra rama
                    espera = m + sp["espera"]
                    continue
                if rng.random() < (sp["ult_35"] if s < 0.35 else sp["ult_50"]):
                    ultimatum = True
                extra = bar["HSN_reputacion_50"] if tag == "HSN" else bar["NAS_sol_bajo"] if tag == "NAS" else 0
                if rng.random() < extra * sp["mecha_hsn_nas"]:
                    ultimatum = True
            if tag == "SHD":
                for umbral, p in sp["mechas_shd"]:
                    if s < umbral and rng.random() < p:
                        ultimatum = True
        if ultimatum:
            espera = m + sp["espera"]
            pasa.setdefault("ultimatum", m)
            if rng.random() < sp["resiste"]:
                rebelde = True
                pasa["rebelion"] = m
                if tag == "ASC" and rng.random() < bar["ASC_valhalla"]:
                    pasa["El Reino del Valhalla (guerra civil)"] = m + 6
            else:
                pasa.setdefault("golpe", m)
                s -= 0.10
    return pasa


def simular(raw: dict, sup: dict, corridas: int, ramas: dict) -> dict:
    sp = leer_spec(raw)
    res = {}
    for esc, media in sup["estabilidad"]["escenarios"].items():
        for tag in POTENCIAS:
            rng = random.Random(f"{sup['semilla']}:{tag}:{esc}")
            cuenta = Counter()
            alguna = 0
            for _ in range(corridas):
                pasa = correr(tag, media, sp, sup, ramas, rng)
                cuenta.update(pasa.keys())
                guerras = [k for k in pasa if k in ("rebelion", "ruta") or "guerra civil" in k]
                if tag in ("FCU",):
                    guerras = [k for k in guerras if k != "rebelion"]   # las Zonas: división, no guerra civil
                if tag == "ASC":
                    guerras = [k for k in guerras if k != "rebelion"]   # los Hijos de Odín: crisis
                alguna += bool(guerras)
            res[(esc, tag)] = {k: v / corridas for k, v in cuenta.items()} | {"_alguna": alguna / corridas}
    return {"spec": sp, "res": res}


# ---------------------------------------------------------------------------- las aventuras

def aventura(saga: dict) -> dict[str, float]:
    """Chance de cada rebelión y de la crisis si se juega eligiendo al azar (personaje y opciones)."""
    nodos = {n["id"]: n for n in saga["nodes"]}
    finales = {f["id"]: f for f in saga.get("endings") or []}
    memo: dict = {}

    def cat(c: dict | None) -> set[str]:
        c = c or {}
        out = set()
        if c.get("rebellion"):
            out.add("rebelión: " + c["rebellion"]["leader"]["spanish"])
        if c.get("crisis"):
            out.add("crisis (el Ultimátum)")
        if c.get("war_by"):
            out.add(f"guerra de {c['war_by']}")
        return out

    def dist(nid, pila=()) -> dict[frozenset, float]:
        if nid in memo:
            return memo[nid]
        if nid in finales:
            r = {frozenset(cat(finales[nid].get("catastrophe"))): 1.0}
        elif nid in nodos and nid not in pila:
            r: dict = {}
            ops = nodos[nid]["options"]
            for o in ops:
                aqui = cat(o.get("catastrophe"))
                for k, p in dist(o.get("next"), pila + (nid,)).items():
                    kk = frozenset(set(k) | aqui)
                    r[kk] = r.get(kk, 0) + p / len(ops)
        else:
            r = {frozenset(): 1.0}
        memo[nid] = r
        return r

    total: dict[str, float] = {}
    chars = saga["characters"]
    for ch in chars:
        for k, p in dist(ch["first"]).items():
            for x in k:
                total[x] = total.get(x, 0) + p / len(chars)
    return total


# ---------------------------------------------------------------------------- el informe

def _pct(x: float) -> str:
    return "—" if x < 0.005 else f"{x * 100:.0f}%"


ETIQUETAS = {"rebelion": "La rebelión propia (Ultimátum, el líder resiste)", "golpe": "Golpe (Ultimátum, el líder renuncia)",
             "ruta": "La guerra de la rama", "rumor": "El Rumor de Golpe termina en Ultimátum"}
RUTA = {"EFE": "La Guerra del Monte (los Incendios de Gaia → El Monte se Levanta)",
        "APF": "La Guerra de los Consejos (Los Consejos se Arman)",
        "NRE": "La Guerra de las Legiones (La Legión Decide)"}


def informe(raw: dict, sup: dict, out: dict, ramas: dict, corridas: int) -> str:
    sp, res = out["spec"], out["res"]
    escs = list(sup["estabilidad"]["escenarios"])
    L = ["# Rebeliones, guerras civiles, divisiones y golpes: la chance de cada nación", "",
         f"{corridas} partidas por nación y escenario, 2100-2120, la IA jugando. Los números del mod se leen "
         "del spec; la estabilidad y las barras propias son supuestos (`tools/simulador/supuestos_rebeliones.yaml`). "
         "Es un dado cargado con los números del mod, no el juego.", "",
         "## Las reglas (del spec)", "",
         f"- **El Ultimátum de los Generales**: con estabilidad bajo {sp['umbral']:.0%}, "
         f"{sp['ult_50'] * 100:.1f}% por mes ({sp['ult_35'] * 100:.0f}% bajo 35%); después, {sp['espera']} meses de espera. "
         f"La IA resiste el {sp['resiste']:.0%} (rebelión) y renuncia el resto (golpe: cae el líder, -10% de estabilidad). "
         "La rebelión propia pasa una vez por partida.",
         f"- **Por cada año entero bajo 50%**: {1 - (1 - sp['ult_50']) ** 12:.0%} de Ultimátum, "
         f"{(1 - (1 - sp['ult_50']) ** 12) * sp['resiste']:.0%} de rebelión. Bajo 35%: "
         f"{1 - (1 - sp['ult_35']) ** 12:.0%} y {(1 - (1 - sp['ult_35']) ** 12) * sp['resiste']:.0%}.",
         f"- **Mechas propias**: la HSN (infamia 50 o más) y la NAS (Sol Bajo) suman {sp['mecha_hsn_nas']:.0%} por mes "
         "bajo 50%; el Directorio, " + " y ".join(f"{p:.0%} por mes bajo {u:.0%}" for u, p in sp["mechas_shd"]) + ".",
         f"- **La rama forzada** (EFE, APF, Roma): bajo 50%, {sp['ruta']:.0%} por mes de que el foco que lleva a la "
         "guerra civil se complete solo.",
         f"- **El Rumor de Golpe** (El Peso del Poder): cada {sp['cada_meses']} meses sale una mala noticia del líder o una "
         f"tregua (peso {sp['peso_tregua']} contra 1 por noticia, de {sp['peso_noticias']}); el Rumor sale bajo 50% de "
         f"estabilidad o con poca Astucia, y termina en Ultimátum el {sp['rumor_ultimatum']:.2%} de las veces "
         "(sin mirar la estabilidad).",
         "", "## Escenarios de estabilidad", "",
         "Media de la estabilidad de cada potencia (vuelve a la media y se mueve ±10 puntos): " +
         ", ".join(f"**{e}** {m:.0%}" for e, m in sup["estabilidad"]["escenarios"].items()) + ".", "",
         "## Resumen: alguna guerra civil antes de 2120", "",
         "| Nación | " + " | ".join(escs) + " |", "|---|" + "---|" * len(escs)]
    for t in POTENCIAS:
        L.append(f"| {NOMBRES[t]} | " + " | ".join(_pct(res[(e, t)]["_alguna"]) for e in escs) + " |")
    L += ["", "## Nación por nación", ""]
    for t in POTENCIAS:
        nombre_reb, tipo = sp["rebelion"][t]
        L += [f"### {NOMBRES[t]}", "", "| Qué | Tipo | " + " | ".join(escs) + " |", "|---|---|" + "---|" * len(escs)]
        filas = [("rebelion", f"{nombre_reb} (el líder resiste el Ultimátum)", tipo),
                 ("golpe", "Golpe: el líder renuncia ante el Ultimátum", "golpe")]
        if t in RUTA:
            filas.append(("ruta", RUTA[t], "guerra civil"))
        claves = set().union(*(res[(e, t)].keys() for e in escs))
        for k in sorted(claves):
            if k not in ("rebelion", "golpe", "ruta", "rumor", "rumor_sale", "ultimatum", "_alguna"):
                tipo_k = "guerra civil" if "guerra civil" in k else "división" if "división" in k else "crisis"
                filas.append((k, k.split(" (")[0] + (f" ({k.split(' (', 1)[1]}" if "si pierde" in k else ""), tipo_k))
        for k, txt, tipo_k in filas:
            L.append(f"| {txt} | {tipo_k} | " + " | ".join(_pct(res[(e, t)].get(k, 0)) for e in escs) + " |")
        L.append(f"| *(de esos Ultimátums, los que vinieron por el Rumor de Golpe)* | | "
                 + " | ".join(_pct(res[(e, t)].get("rumor", 0)) for e in escs) + " |")
        L.append("")
    zal = sup["barras"]
    L += ["## Japón, Albión y las anarquías", "",
          "- **Japón (Shogunato de los Astilleros)**: no tiene Ultimátum propio (no está en la lista de rebeliones de las "
          "potencias); se parte solo en sus aventuras (abajo).",
          f"- **Albión**: además de sus aventuras, la Guerra de las Dos Eras (la Pompa cae dos veces bajo 10, o la Red cae "
          f"dos veces): {zal['ZAL_guerra_eras']:.0%} estimado, con Albión ya formada (renace en el "
          f"{zal['ZAL_renace']['chance']:.0%} de las partidas, si la Comuna pierde contra Roma).",
          "- **Las anarquías** (Caudillos del Amazonas, Señores de la Guerra de Eurasia, de Hindustán, Emiratos del "
          "Desierto, Tierras Sin Ley): sin Ultimátum; se parten en los finales malos de sus aventuras.", ""]
    L += ["## Las aventuras (si las jugás eligiendo al azar)", "",
          "Personaje y opciones al azar: la chance de llegar a un final o una opción con rebelión o crisis.", "",
          "| Aventura | Nación | Qué puede pasar | Chance |", "|---|---|---|---|"]
    for key, saga in raw["adventures"]["sagas"].items():
        r = aventura(saga)
        quien = saga.get("country") or ("las meganaciones" if saga.get("countries") else key)
        for k, p in sorted(r.items()):
            L.append(f"| {saga['name']['spanish']} | {quien} | {k} | {_pct(p)} |")
    L += ["", "## Supuestos", "",
          f"- Ramas que elige la IA (SIMULADOR_IA.md, IA típica): " +
          ", ".join(f"{t} {p:.0%}" for t, p in ramas.items()) + ".",
          "- Barras propias (estimadas a mano): " + ", ".join(
              f"{k} {v['chance'] if isinstance(v, dict) else v:.0%}" for k, v in sup["barras"].items()) + ".",
          "- No simula el mapa: guerras, conquistas y derrotas cambian la estabilidad más que cualquier otra cosa; "
          "por eso van los tres escenarios.",
          "- Nada de esto se probó dentro del juego."]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m tools.simulador.rebeliones")
    ap.add_argument("--corridas", type=int, default=None)
    ap.add_argument("--salida", default=str(REPO / "SIMULADOR_REBELIONES.md"))
    args = ap.parse_args(argv)
    raw = specload.load(REPO / "spec").raw
    sup = yaml.safe_load(SUPUESTOS.read_text(encoding="utf-8"))
    ramas = ramas_ia(REPO / "SIMULADOR_IA.md")
    out = simular(raw, sup, args.corridas or sup["corridas"], ramas)
    texto = informe(raw, sup, out, ramas, args.corridas or sup["corridas"])
    Path(args.salida).write_text(texto + "\n", encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
