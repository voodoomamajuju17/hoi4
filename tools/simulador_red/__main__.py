"""python3 -m tools.simulador_red [--corridas N] [--parametros ARCHIVO] [--salida ARCHIVO]

Tira los dados de La Red (la Rebelión de las Máquinas, Plan A liviano) miles
de veces y escribe un informe: cuántas veces es un trámite, cuántas se come el
mundo y cuántas sale a la medida; cuánto depende de lo que manda la IA; si
nacer en un lugar fijo o al azar castiga siempre a la misma nación; y qué pasa
si sale más fuerte o más débil. Mismos parámetros + misma semilla = mismo informe.
"""

from __future__ import annotations

import argparse
import copy
from collections import Counter, defaultdict
from pathlib import Path

from . import modelo as m


def _pct(x: float) -> str:
    return f"{round(100 * x)}%"


def _fecha(x: float | None) -> str:
    if x is None:
        return "—"
    anio = int(x)
    mes = min(12, int(round((x - anio) * 12)) + 1)
    return f"{['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'][mes - 1]} {anio}"


def _cuantil(xs: list[float], q: float):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def _con(p: dict, cambios: dict) -> dict:
    q = copy.deepcopy(p)
    for ruta, v in cambios.items():
        d = q
        partes = ruta.split(".")
        for k in partes[:-1]:
            d = d[k]
        d[partes[-1]] = v
    return q


def _nacidas(p, fin, n, **kw):
    return [r for r in m.correr(p, fin, n, **kw) if r.nace]


def _clases(p, rs) -> Counter:
    c = Counter(m.clasificar(p, r) for r in rs)
    return Counter({k: v / len(rs) for k, v in c.items()})


def _compromiso(p: dict, fr: float) -> dict:
    return _con(p, {"compromiso.frente": fr,
                    "compromiso.anarquia_frente": min(0.6, fr + 0.15)})


def informe(p: dict, fin: dict[str, float], n: int) -> str:
    out: list[str] = []
    w = out.append
    etapas = [e["nombre"] for e in p["etapas"]]
    w("# Simulador de La Red: ¿muy chica, muy grande o a la medida?\n")
    w(f"{n} partidas por fila, semilla {p['semilla']}, desde que nace (2113) hasta el 1/1/2120. "
      "Los números de diseño están en `tools/simulador_red/parametros.yaml`; lo que decide el juego "
      "(el mapa, las batallas, cuánto manda la IA) está simplificado y marcado como SUPUESTO. "
      "Es un dado cargado, no el juego: sirve para comparar diseños, no para predecir una partida.\n")
    c = p["clasificacion"]
    w(f"**Cómo se clasifica una partida.** *Trámite*: muere antes de {c['tramite_meses']} meses o nunca pasa de "
      f"{c['tramite_regiones']} regiones. *Se come el mundo*: llega a {c['gigante_regiones']} regiones o sigue en 2120 "
      f"con {c['gigante_2120']} o más. *A la medida*: todo lo demás.\n")

    # ------------------------------------------------------------ nacimiento
    pf = fin.get("fuga", 0.0)
    nac = p["nacimiento"]
    sin = (1 - pf) ** nac["potencias_ia"] * (1 - nac["asc_plan41"] * nac["asc_calor_60"])
    w("## Cuántas veces nace\n")
    w(f"Con la IA eligiendo al azar en El Despertar (spec/37), cada potencia termina en La Fuga el {_pct(pf)} de las veces. "
      f"Con las ocho, más la ASC de PLAN-41 con la red caliente ({_pct(nac['asc_plan41'] * nac['asc_calor_60'])}), "
      f"**La Red nace en el {_pct(1 - sin)} de las partidas**. En el resto llega \"La Noche que No Pasó\".\n")

    # ------------------------------------------------------------ caso base
    rs = _nacidas(p, fin, n)
    cl = _clases(p, rs)
    w("## El diseño propuesto\n")
    w(f"Con los parámetros del archivo (la IA que limita con La Red manda el {_pct(p['compromiso']['frente'])} de su ejército):\n")
    w("| | |\n|---|---|")
    w(f"| Trámite | {_pct(cl['tramite'])} |")
    w(f"| A la medida | {_pct(cl['medida'])} |")
    w(f"| Se come el mundo | {_pct(cl['gigante'])} |")
    picos = [r.pico for r in rs]
    w(f"| Regiones en su mejor momento (10% / mitad / 90%) | {_cuantil(picos, .1)} / {_cuantil(picos, .5)} / {_cuantil(picos, .9)} |")
    muertes = [r.murio for r in rs if r.murio is not None]
    w(f"| Muere (10% / mitad / 90% de las que mueren) | {_fecha(_cuantil(muertes, .1))} / {_fecha(_cuantil(muertes, .5))} / {_fecha(_cuantil(muertes, .9))} |")
    w(f"| Sigue viva el 1/1/2120 | {_pct(1 - len(muertes) / len(rs))} |")
    cod = [r.codigos[0] for r in rs if r.codigos]
    w(f"| Le terminan al menos un Código de Apagado | {_pct(len(cod) / len(rs))} (el primero, la mitad antes de {_fecha(_cuantil(cod, .5))}) |")
    w(f"| Códigos por partida (media) | {sum(len(r.codigos) for r in rs) / len(rs):.1f} |")
    w(f"| Depósito más grande (mitad de las partidas) | {round(_cuantil([r.reserva_max for r in rs], .5))} divisiones esperando suministro |")
    ok = sum(r.brotes_ok for r in rs) / len(rs)
    mal = sum(r.brotes_mal for r in rs) / len(rs)
    w(f"| Brotes por partida (prenden / los aplasta la guarnición) | {ok:.1f} / {mal:.1f} |\n")
    w("**Hasta qué etapa llega:**\n")
    w("| Etapa | llega | la mitad la abre antes de |\n|---|---|---|")
    for i, nombre in enumerate(etapas):
        llegan = [r for r in rs if r.etapa_max >= i]
        fechas = [r.etapa_fecha[i] for r in llegan if i in r.etapa_fecha]
        w(f"| {i}. {nombre} | {_pct(len(llegan) / len(rs))} | {_fecha(_cuantil(fechas, .5)) if i else 'al nacer'} |")
    w("")

    # ------------------------------------------------------------ los tres caminos
    if p.get("caminos"):
        w("## Los tres caminos\n")
        w("Cada camino forzado en todas las partidas (la IA real elige al azar, como el caso de arriba). "
          "La regla del mod: ningún camino vale más de 1,3 veces otro. Se compara por las regiones en su "
          "mejor momento y por cuánto vive.\n")
        w("| Camino | trámite / medida / se come | regiones en su mejor momento (media / mitad) "
          "| sigue viva en 2120 | Códigos (media) |")
        w("|---|---|---|---|---|")
        medias = {}
        for nombre, cam in (("Sin camino (versión 3)", None), ("La Plaga", "plaga"),
                            ("La Marea", "marea"), ("El Susurro", "susurro")):
            rr = _nacidas(p, fin, n, camino=cam)
            k = _clases(p, rr)
            media = sum(r.pico for r in rr) / len(rr)
            viva = sum(r.murio is None for r in rr) / len(rr)
            if cam:
                medias[nombre] = (media, viva)
            w(f"| {nombre} | {_pct(k['tramite'])} / {_pct(k['medida'])} / {_pct(k['gigante'])} "
              f"| {media:.0f} / {_cuantil([r.pico for r in rr], .5)} | {_pct(viva)} "
              f"| {sum(len(r.codigos) for r in rr) / len(rr):.1f} |")
        if medias:
            alto = max(medias, key=lambda x: medias[x][0])
            bajo = min(medias, key=lambda x: medias[x][0])
            razon = medias[alto][0] / medias[bajo][0]
            w(f"\n**Balance:** el más fuerte ({alto}) llega en su mejor momento a {razon:.2f} veces las regiones "
              f"del más débil ({bajo}); " + ("dentro de la regla de 1,3." if razon <= 1.3 else
                                             "**fuera de la regla de 1,3**: hay que ajustar."))
        w("")

    # ------------------------------------------------------------ cuánto manda la IA
    w("## El riesgo grande: cuánto manda la IA contra La Red\n")
    w("Es lo que el simulador no puede saber y lo que más cambia el resultado. *Rígida*: el diseño sin los dos "
      "resortes (los brotes de desesperación cuando es chica, la sobrecarga y la Emergencia cuando es grande, "
      "las etapas que se abren también con el tiempo). *Elástica*: con ellos.\n")
    w("| La IA vecina manda | Rígida: trámite / medida / se come | Elástica: trámite / medida / se come | Elástica: llega a La Singularidad |")
    w("|---|---|---|---|")
    for fr in (0.10, 0.20, 0.30, 0.40, 0.50):
        q = _compromiso(p, fr)
        a = _clases(q, _nacidas(q, fin, n, elastica=False))
        rb = _nacidas(q, fin, n)
        b = _clases(q, rb)
        sing = sum(r.etapa_max >= len(etapas) - 1 for r in rb) / len(rb)
        w(f"| {_pct(fr)} de su ejército | {_pct(a['tramite'])} / {_pct(a['medida'])} / {_pct(a['gigante'])} "
          f"| {_pct(b['tramite'])} / {_pct(b['medida'])} / {_pct(b['gigante'])} | {_pct(sing)} |")
    w("")

    # ------------------------------------------------------------ lugar fijo o al azar
    w("## Lugar fijo o al azar\n")
    w("Qué parte de todas las regiones que toma La Red le saca a una sola nación (la más castigada de cada partida), "
      "y cuántas partidas castigan a cada una. Fijo = nace siempre en el Báltico de la ASC.\n")
    filas = []
    for nombre, kw in (("Al azar entre 12 lugares", {}), ("Siempre en el mismo lugar", {"lugar_fijo": True})):
        rr = _nacidas(p, fin, n, **kw)
        share, victima = [], Counter()
        for r in rr:
            tot = sum(r.tomadas.values())
            t, v = r.tomadas.most_common(1)[0]
            share.append(v / tot)
            victima[t] += 1
        top = ", ".join(f"{t} {_pct(k / len(rr))}" for t, k in victima.most_common(4))
        filas.append((nombre, sum(share) / len(share), top))
    w("| | se lleva la más castigada | la más castigada es |\n|---|---|---|")
    for nombre, s, top in filas:
        w(f"| {nombre} | {_pct(s)} de lo que toma | {top} |")
    w("")
    w("**Dónde nace** (con el lugar al azar):\n")
    w("| Lugar | trámite / medida / se come |\n|---|---|")
    por_lugar = defaultdict(list)
    for r in rs:
        por_lugar[r.lugar].append(r)
    for lug in p["lugares"]:
        rr = por_lugar.get(lug["nombre"], [])
        if rr:
            k = _clases(p, rr)
            w(f"| {lug['nombre']} | {_pct(k['tramite'])} / {_pct(k['medida'])} / {_pct(k['gigante'])} |")
    w("")

    # ------------------------------------------------------------ la plaga
    w("## Con plaga o sin plaga\n")
    w("| | trámite / medida / se come | regiones en su mejor momento (mitad) |\n|---|---|---|")
    for nombre, cambios in (("Con brotes (una región al azar con divisiones)", {}),
                            ("Sin brotes", {"plaga.activa": False})):
        q = _con(p, cambios)
        rr = _nacidas(q, fin, n)
        k = _clases(q, rr)
        w(f"| {nombre} | {_pct(k['tramite'])} / {_pct(k['medida'])} / {_pct(k['gigante'])} | {_cuantil([r.pico for r in rr], .5)} |")
    w("")

    # ------------------------------------------------------------ más fuerte o más débil
    w("## Si sale más fuerte o más débil\n")
    w("Divisiones y calidad del arranque (la calidad es cuánto pelea una división de La Red contra una de una potencia). "
      "Cada celda: trámite / se come el mundo. Con suministro, las divisiones de más esperan en el depósito: "
      "lo que cambia el resultado es la calidad.\n")
    divs = (45, 70, 90, 120)
    cals = (2.4, 2.7, 3.0, 3.3)
    w("| divisiones \\ calidad | " + " | ".join(str(x) for x in cals) + " |")
    w("|---|" + "---|" * len(cals))
    for d in divs:
        celdas = []
        for q_ in cals:
            q = _con(p, {"arranque.divisiones": d, "arranque.calidad": q_})
            k = _clases(q, _nacidas(q, fin, max(300, n // 3)))
            celdas.append(f"{_pct(k['tramite'])} / {_pct(k['gigante'])}")
        w(f"| {d} | " + " | ".join(celdas) + " |")
    w("")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m tools.simulador_red")
    ap.add_argument("--spec", default="spec")
    ap.add_argument("--parametros", default=None)
    ap.add_argument("--corridas", type=int, default=None)
    ap.add_argument("--salida", default="SIMULADOR_RED.md")
    args = ap.parse_args(argv)
    p = m.cargar_parametros(args.parametros)
    fin = m.finales_despertar(args.spec)
    texto = informe(p, fin, args.corridas or p["corridas"])
    Path(args.salida).write_text(texto, encoding="utf-8")
    print(f"simulador de La Red: {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
