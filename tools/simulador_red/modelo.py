"""El modelo de La Red: un mes por paso, desde que nace hasta el 1/1/2120.

No simula el mapa. La Red tiene tres clases de frente:
  - la isla: fortificada, solo se ataca por mar (el enemigo pega a media fuerza)
    y no sirve para avanzar;
  - la costa (el frente principal): avanza contra los dueños con los que tiene
    contacto; con 6 regiones toca a todos los vecinos del lugar y con 15 a uno
    lejano más;
  - los brotes: una región suelta en cualquier parte del mundo, con sus propias
    divisiones.
Cada mes, en cada frente, se compara la fuerza de los dos lados (divisiones por
calidad, fuertes al defender). El que tiene 15% más avanza o recupera regiones.

Cada frente aguanta solo las divisiones que le da el suministro; el resto espera
en el depósito (que tiene techo) y sale cuando La Red gana regiones. El Código de
Apagado no la borra: la golpea un año (equipo, fábricas, suministro, combate, sin
brotes ni etapas nuevas) y tarda más cuanto más avanzada está.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

AQUI = Path(__file__).resolve().parent


def cargar_parametros(ruta: str | None = None) -> dict:
    with open(ruta or AQUI / "parametros.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def finales_despertar(spec_dir: str = "spec") -> dict[str, float]:
    """Probabilidad de cada final de El Despertar si la IA elige al azar.

    El emisor de aventuras pone ai_chance = 1 en todas las opciones (y en las
    tres puertas), así que cada opción sale con la misma chance.
    """
    with open(Path(spec_dir) / "37_el_despertar.yaml", encoding="utf-8") as fh:
        saga = yaml.safe_load(fh)["adventures"]["sagas"]["MN2110"]
    nodos = {n["id"]: n for n in saga["nodes"]}
    finales = {e["id"]: e for e in saga["endings"]}
    prob: Counter = Counter()

    def andar(i: int, p: float) -> None:
        if i in finales:
            prob[i] += p
            return
        opciones = nodos[i]["options"]
        for o in opciones:
            andar(o["next"], p / len(opciones))

    puertas = saga["characters"]
    for c in puertas:
        andar(c["first"], 1 / len(puertas))
    out: dict[str, float] = {}
    for i, p in prob.items():
        banderas = [x.get("value", "") for x in finales[i].get("effects", [])
                    if x.get("effect") == "flag"]
        clave = banderas[0].replace("MEGANATIONS_despertar_", "") if banderas else str(i)
        out[clave] = out.get(clave, 0.0) + p
    return out


def _poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    l, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= l:
            return k
        k += 1


@dataclass
class Frente:
    tipo: str                 # isla | costa | brote
    dueno: str                # de quién son las regiones (para la isla y los brotes)
    div: float
    reg: int
    fort: int = 0
    edad: int = 0
    contacto: dict = field(default_factory=dict)   # solo la costa: dueño -> peso


@dataclass
class Partida:
    nace: bool
    lugar: str = ""
    nacio: float = 0.0
    murio: float | None = None
    pico: int = 0
    final: int = 0
    etapa_max: int = 0
    etapa_fecha: dict = field(default_factory=dict)
    codigos: list = field(default_factory=list)
    reserva_max: float = 0.0
    tray: list = field(default_factory=list)   # mes a mes: regiones, costa, depósito, etapa, brotes, golpe
    brotes_ok: int = 0
    brotes_mal: int = 0
    tomadas: Counter = field(default_factory=Counter)
    camino: str | None = None


def jugar(p: dict, rng: random.Random, finales: dict[str, float],
          lugar_fijo: bool = False, elastica: bool = True, camino: str | None = "azar") -> Partida:
    nac = p["nacimiento"]
    mundo = p["mundo"]
    potencias = list(mundo["potencias"])
    anarquias = list(mundo["anarquias"])
    tamano = {**mundo["potencias"], **mundo["anarquias"]}
    calidad_enemiga = {t: 1.0 for t in potencias} | {t: mundo["calidad_anarquias"] for t in anarquias}

    # ------------------------------------------------ El Despertar de cada potencia
    claves, pesos = zip(*finales.items())
    final_de = {t: rng.choices(claves, pesos)[0] for t in potencias[: nac["potencias_ia"]]}
    plan41 = rng.random() < nac["asc_plan41"] * nac["asc_calor_60"]
    if not (any(f == "fuga" for f in final_de.values()) or plan41):
        return Partida(nace=False)
    inmunes = {t for t, f in final_de.items() if f == "apagon"} if p["plaga"]["inmunes_apagon"] else set()
    con_llave = {t for t, f in final_de.items() if f == "llave"}

    # ------------------------------------------------ el arranque
    lugar = p["lugar_fijo"] if lugar_fijo else rng.choice(p["lugares"])
    arr = p["arranque"]
    sup = p["suministro"]
    cod = p["codigo"]
    t0 = rng.uniform(nac["desde"], nac["hasta"])
    meses_total = int(round((p["hasta"] - t0) * 12))
    ri, rc = arr["regiones_isla"], arr["regiones_costa"]
    isla = Frente("isla", lugar["isla"], 0.0, ri, fort=ri)
    costa = Frente("costa", lugar["costa"], 0.0, rc, fort=rc, contacto={lugar["costa"]: 1.0})
    frentes = [isla, costa]
    reserva = float(arr["divisiones"])   # lo que no entra en el suministro espera en el depósito
    res = Partida(nace=True, lugar=lugar["nombre"], nacio=t0)
    cam = p.get("caminos") or {}
    if camino == "azar":
        camino = rng.choices(list(cam["eleccion"]), list(cam["eleccion"].values()))[0] if cam else None
    res.camino = camino
    cp = cam.get(camino) or {} if camino else {}
    red = cam.get("redundancia")
    etapa1_mes: list[int] = []          # cuándo abrió La Red se Extiende (Redundancia va detrás)
    marea_dada = [0]                    # hasta qué nivel ya llegaron las divisiones de La Marea
    proxima_infiltracion: list[float] = []
    res.tomadas[lugar["isla"]] += ri
    res.tomadas[lugar["costa"]] += rc

    etapas = p["etapas"]
    etapa = 0
    emergencia = False
    coalicion: set[str] = set()
    guerra_rival = {t: rng.random() < p["compromiso"]["prob_guerra_rival"] for t in potencias}
    codigo_fin: float | None = None      # mes en que termina el Código en curso
    golpe_hasta = -1.0                   # mientras dura el golpe del Código
    golpe_k = [1.0]                      # cuánto pega el golpe en curso (Redundancia, El Susurro)
    codigos = 0
    proximo_brote: int | None = None
    comb, comp = p["combate"], p["compromiso"]
    lejano_agregado = False

    def total_reg() -> int:
        return sum(f.reg for f in frentes)

    def golpeada(mes: int) -> bool:
        return mes < golpe_hasta

    def nivel() -> int:
        """Nivel del camino: 1 con La Red se Extiende, 2 con Conciencia, 3 con El Enjambre."""
        return min(etapa, 3) if camino else 0

    def de_nivel(lista, por_defecto=0.0):
        return lista[nivel() - 1] if nivel() else por_defecto

    def dias_brote(dias: float) -> float:
        if camino in ("plaga", "marea") and nivel():
            dias = dias * cp["brote_dias"] - (de_nivel(cp.get("menos_dias", [0, 0, 0]), 0))
        return max(30.0, dias)

    def suave(mes: int) -> float:
        """Cuánto del golpe del Código llega (Redundancia y Nadie Apaga lo que No Ve)."""
        k = 1.0
        if red and etapa1_mes and mes >= etapa1_mes[0] + red["meses"]:
            k *= red["golpe"]
        if camino == "susurro" and nivel():
            k *= de_nivel(cp["golpe"], 1.0)
        return k

    def calidad(mes: int) -> float:
        q = arr["calidad"] + sum(e["calidad"] for e in etapas[: etapa + 1])
        sob = p["sobrecarga"]
        if elastica and total_reg() > sob["desde"]:
            q += sob["calidad"] * (total_reg() - sob["desde"]) / sob["cada"]
        if golpeada(mes):
            q += cod["calidad"] * golpe_k[0]
        return max(0.6, q)

    def tope(f: Frente, mes: int) -> float:
        if f.reg <= 0:
            return 0.0
        por_region = sup["por_region"] + sup["por_etapa"] * etapa
        if f.tipo == "isla":
            t = sup["isla"]
        elif f.tipo == "brote":
            t = sup["brote_base"] + sup["brote_por_region"] * f.reg
        else:
            t = sup["base"] + por_region * f.reg
        if camino == "marea" and nivel():
            t *= 1 + cp["suministro"]
        if camino == "plaga" and f.tipo == "brote":
            t *= 1 + de_nivel(cp["suministro_brote"])
        return t * (1 - cod["infraestructura"] * golpe_k[0]) if golpeada(mes) else t

    anios = [0.0]   # años desde que nació (el mundo se moviliza con el tiempo)

    def compromiso(t: str, en_frente: bool) -> float:
        if t in anarquias:
            return comp["anarquia_frente"] if en_frente else 0.0
        c = (comp["frente"] + comp["movilizacion"] * anios[0]) if en_frente else 0.0
        if t in coalicion:
            c += comp["coalicion"] if en_frente else comp["expedicion"]
        if emergencia:
            c += comp["emergencia"]
        if guerra_rival.get(t) and t not in coalicion:
            c *= comp["guerra_rival"]
        return c * (1 + total_reg() / comp["amenaza"]) if comp.get("amenaza") else c

    for mes in range(meses_total):
        ahora = t0 + mes / 12
        anios[0] = mes / 12

        # ---- el mundo reacciona
        if mes % 12 == 0 and mes:
            guerra_rival = {t: rng.random() < comp["prob_guerra_rival"] for t in potencias}
        en_contacto = set(costa.contacto) | {f.dueno for f in frentes if f.tipo == "brote"} | {isla.dueno}
        if mes >= 3:
            for t in potencias:
                if t not in coalicion:
                    q = comp["coalicion_mes_frente"] if t in en_contacto else comp["coalicion_mes"]
                    if rng.random() < q:
                        coalicion.add(t)

        # ---- el Código de Apagado: tarda según la etapa, debilita, se puede repetir
        if mes >= cod["desde_mes"] and codigo_fin is None and not golpeada(mes) \
                and etapa >= cod["desde_etapa"]:
            for t in sorted(coalicion):
                if rng.random() < cod["empezar_mes"]:
                    dias = cod["dias_por_etapa"][etapa] * (1 + cod["repetido"] * codigos)
                    if camino == "susurro" and nivel():
                        dias *= de_nivel(cp["codigo"], 1.0)
                    if t in con_llave:
                        dias *= cod["llave"]
                    elif t == "ASC" and rng.random() < cod["arkhipov"]:
                        dias *= cod["arkhipov_factor"]
                    codigo_fin = mes + dias / 30
                    break
        if codigo_fin is not None and mes >= codigo_fin:
            codigo_fin = None
            codigos += 1
            res.codigos.append(ahora)
            golpe_hasta = mes + cod["efecto_dias"] / 30
            golpe_k[0] = suave(mes)
            for f in frentes:
                f.div *= 1 - cod["equipo"] * golpe_k[0]
            reserva *= 1 - cod["reserva"]

        # ---- las etapas (tamaño y tiempo); golpeada no abre etapas nuevas
        if not golpeada(mes):
            while etapa + 1 < len(etapas) and (
                    (total_reg() >= etapas[etapa + 1]["regiones"] and mes >= etapas[etapa + 1]["meses"])
                    or (elastica and etapas[etapa + 1].get("solo_tiempo") is not None
                        and mes >= etapas[etapa + 1]["solo_tiempo"])):
                etapa += 1
                res.etapa_fecha[etapa] = ahora
                if etapa == 1:
                    etapa1_mes.append(mes)
                    if camino == "susurro":
                        proxima_infiltracion.append(mes + 1)
                if etapas[etapa].get("emergencia"):
                    emergencia = True
                dias = etapas[etapa]["brote_dias"]
                if dias and p["plaga"]["activa"]:
                    proximo_brote = mes + max(1, round(dias_brote(dias) / 30))
            if camino == "marea":
                while marea_dada[0] < nivel():
                    reserva += cp["divisiones"][marea_dada[0]]
                    marea_dada[0] += 1
            res.etapa_max = max(res.etapa_max, etapa)

        # la red ya es una potencia: Ginebra declara la Emergencia aunque no haya Singularidad
        if elastica and total_reg() >= p["emergencia_regiones"]:
            emergencia = True

        # ---- producción: va al depósito
        pr = p["produccion"]
        prod = pr["base"] + pr["por_region"] * min(total_reg(), pr["hasta"]) \
            + pr["despues"] * max(0, total_reg() - pr["hasta"])
        prod *= 1 + sum(e["produccion"] for e in etapas[: etapa + 1])
        if golpeada(mes):
            prod *= 1 - cod["fabricas"] * golpe_k[0]
        if mes < arr["provision_meses"]:
            prod *= 1 + arr["provision_bonus"]
        # el depósito tiene techo: sin regiones no hay dónde guardar ni con quién tripular.
        # Las fábricas paran al llegar al techo; lo que ya existe (el arranque) no se tira.
        techo = sup["deposito_base"] + sup["deposito_por_region"] * total_reg()
        reserva += max(0.0, min(prod, techo - reserva))

        # ---- la plaga (el Código la suspende mientras dura el golpe)
        plaga_ok = p["plaga"]["activa"] and not golpeada(mes)
        desesp = p["plaga"]["desesperacion"]
        chica = elastica and total_reg() <= desesp["regiones"] and mes >= 3
        if chica and plaga_ok and (proximo_brote is None or proximo_brote - mes > desesp["dias"] / 30):
            proximo_brote = mes + max(1, round(desesp["dias"] / 30))
        if proximo_brote is not None and mes >= proximo_brote and plaga_ok:
            cand = [t for t in tamano if t not in inmunes]
            div = p["plaga"]["divisiones"] + p["plaga"]["por_etapa"] * etapa + (desesp["extra"] if chica else 0)
            if camino == "plaga":
                div += de_nivel(cp["divisiones"])
            brotes = [div]
            if camino == "plaga" and nivel() >= cp["esporas_desde"]:
                brotes.append(1)        # Esporas en los Cables: otro brote chico en otro lado
            for d in brotes:
                dueno = rng.choices(cand, [tamano[t] for t in cand])[0]
                guarn = rng.uniform(*p["plaga"]["guarnicion"]) * calidad_enemiga[dueno]
                if d * calidad(mes) > guarn * comb["umbral"]:
                    frentes.append(Frente("brote", dueno, float(d), 1))
                    res.brotes_ok += 1
                    res.tomadas[dueno] += 1
                else:
                    res.brotes_mal += 1
            dias = etapas[etapa]["brote_dias"]
            dias = dias_brote(dias) if dias else desesp["dias"]
            proximo_brote = mes + max(1, round(dias / 30))

        # ---- la costa toca a más países al crecer
        if costa.reg >= 6:
            for t, w in lugar["vecinos"].items():
                costa.contacto.setdefault(t, w)
        if costa.reg >= 15 and not lejano_agregado:
            cand = [t for t in tamano if t not in costa.contacto]
            costa.contacto[rng.choices(cand, [tamano[t] for t in cand])[0]] = 0.3
            lejano_agregado = True

        # ---- el suministro: lo que sobra vuelve al depósito, lo que falta sale de él.
        # Los brotes solo reciben del depósito con El Enjambre (antes están sueltos).
        for f in frentes:
            t = tope(f, mes)
            if f.div > t:
                reserva += f.div - t
                f.div = t
        for f in [costa] + [g for g in frentes if g.tipo == "brote"] + [isla]:
            if f.tipo == "brote" and etapa < sup["brotes_desde_etapa"]:
                continue
            falta = max(0.0, tope(f, mes) - f.div)
            dar = min(falta, reserva)
            f.div += dar
            reserva -= dar
        res.reserva_max = max(res.reserva_max, reserva)

        # ---- El Susurro: la decisión de infiltrar toma una región vecina cada tanto
        if camino == "susurro" and proxima_infiltracion and mes >= proxima_infiltracion[0]:
            vivos = [g for g in frentes if g.reg > 0 and g.tipo != "isla"]
            if vivos:
                g = max(vivos, key=lambda g: g.reg)
                g.reg += 1
                if g.tipo == "costa":
                    duenos, pesos = zip(*g.contacto.items())
                    res.tomadas[rng.choices(duenos, pesos)[0]] += 1
                else:
                    res.tomadas[g.dueno] += 1
            proxima_infiltracion[0] = mes + de_nivel(cp["infiltrar_dias"], 120) / 30

        # ---- el combate, frente por frente
        q = calidad(mes)
        expedicion = sum(compromiso(t, False) * tamano[t] for t in coalicion if t not in costa.contacto)
        # la expedición de la coalición va al frente donde La Red tiene más regiones
        vivos = [g for g in frentes if g.reg > 0 and g.tipo != "isla"]
        mayor = max(vivos, key=lambda g: g.reg) if vivos else None
        for f in frentes:
            if f.reg <= 0:
                continue
            f.edad += 1
            if f.tipo == "costa":
                enemigo = sum(compromiso(t, True) * tamano[t] * calidad_enemiga[t] for t in f.contacto)
                enemigo += expedicion if f is mayor else 0.0
            elif f.tipo == "isla":
                enemigo = comb["isla"] * sum(compromiso(t, True) * tamano[t] * calidad_enemiga[t]
                                             for t in costa.contacto | {f.dueno: 1})
            else:
                base = rng.uniform(*p["plaga"]["guarnicion"]) * calidad_enemiga[f.dueno]
                reaccion = 0.5 * compromiso(f.dueno, True) * tamano[f.dueno] * calidad_enemiga[f.dueno] \
                    if f.edad >= 2 else 0.0
                enemigo = base + reaccion + (expedicion if f is mayor else 0.0)
            fuerza = f.div * q
            frac_fort = min(1.0, f.fort / f.reg) if f.reg else 0
            fuertes = arr["fuertes"] * (arr["escudo"] if mes < arr["escudo_meses"] else 1)
            defensa = fuerza * (1 + (fuertes - 1) * frac_fort)
            if camino == "plaga" and nivel():
                defensa *= 1 + cp["defensa"]
            ataque = fuerza * (1 + de_nivel(cp["ataque"])) if camino == "marea" else fuerza
            if f.tipo != "isla" and ataque > comb["umbral"] * max(enemigo, 0.1):
                gana = _poisson(rng, min(comb["avance_max"], comb["avance"] * (ataque / max(enemigo, 0.1) - 1)))
                if gana:
                    f.reg += gana
                    if f.tipo == "costa":
                        duenos, pesos = zip(*f.contacto.items())
                        for _ in range(gana):
                            res.tomadas[rng.choices(duenos, pesos)[0]] += 1
                    else:
                        res.tomadas[f.dueno] += gana
                f.div -= comb["bajas"] * enemigo / q
            elif enemigo > comb["umbral"] * defensa:
                pierde = _poisson(rng, min(comb["avance_max"], comb["avance"] * (enemigo / defensa - 1)))
                pierde = min(pierde, f.reg)
                f.reg -= pierde
                f.fort = min(f.fort, f.reg)   # las fortificadas caen últimas
                f.div -= comb["bajas"] * enemigo / q * 0.7
            else:
                f.div -= comb["bajas"] * enemigo / q * 0.7
            if f.div <= 0.5:
                f.reg = 0
            if f.reg <= 0:
                reserva += max(0.0, f.div) * 0.3   # algo se escapa por los cables
                f.div = 0
        frentes = [f for f in frentes if f.reg > 0 or f.tipo in ("isla", "costa")]
        reg = total_reg()
        res.pico = max(res.pico, reg)
        res.tray.append((reg, round(costa.div), round(reserva), etapa, sum(1 for g in frentes if g.tipo == 'brote'), golpeada(mes)))
        if reg <= 0:
            res.murio = ahora
            break
    res.final = total_reg()
    return res


def correr(p: dict, finales: dict[str, float], corridas: int | None = None,
           lugar_fijo: bool = False, semilla: int | None = None,
           elastica: bool = True, camino: str | None = "azar") -> list[Partida]:
    rng = random.Random(p["semilla"] if semilla is None else semilla)
    return [jugar(p, rng, finales, lugar_fijo, elastica, camino) for _ in range(corridas or p["corridas"])]


def clasificar(p: dict, r: Partida) -> str:
    c = p["clasificacion"]
    vida = ((r.murio if r.murio is not None else p["hasta"]) - r.nacio) * 12
    if (r.murio is not None and vida < c["tramite_meses"]) or r.pico < c["tramite_regiones"]:
        return "tramite"
    if r.pico >= c["gigante_regiones"] or (r.murio is None and r.final >= c["gigante_2120"]):
        return "gigante"
    return "medida"
