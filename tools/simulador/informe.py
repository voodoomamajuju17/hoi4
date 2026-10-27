"""Pasa los conteos del simulador a un informe en Markdown."""

from __future__ import annotations

from collections import Counter

from .motor import fecha_de

AVISO = 0.9  # un lado que sale más que esto se marca: la IA casi nunca hace el otro


def _pct(x: float) -> str:
    return f"{round(100 * x)}%"


def _nombre(raw: dict, fid: str) -> str:
    for arbol in (raw["focus_trees"].get("trees") or {}).values():
        for rama in arbol.get("branches") or []:
            for f in rama.get("focuses") or []:
                if f["id"] == fid:
                    return (f.get("name") or {}).get("spanish") or fid
    return fid


def _percentiles(meses: list[int | None]) -> tuple[str, str, str, float]:
    hechos = sorted(m for m in meses if m is not None)
    nunca = 1 - len(hechos) / max(1, len(meses))
    if not hechos:
        return "-", "-", "-", nunca
    def p(q: float) -> str:
        return fecha_de(hechos[min(len(hechos) - 1, int(q * len(hechos)))])
    return p(0.1), p(0.5), p(0.9), nunca


def informe(raw: dict, sup: dict, focos: list[dict], mundo: dict, crisis: dict) -> str:
    L: list[str] = []
    w = L.append
    w("# Simulador de la IA: lo que hacen las ocho potencias si nadie las toca")
    w("")
    w(f"{mundo['corridas']} partidas por tabla, semilla {sup.get('semilla')}. Los pesos, condiciones y azares salen del spec;"
      " lo que el spec no sabe (guerras, estabilidad, cómo sube cada barra) sale de `tools/simulador/supuestos.yaml`."
      " No simula el mapa ni las batallas. Es un dado cargado con los números del mod, no el juego.")
    w("")
    escenarios = list((sup.get("escenarios_focos") or {"ia_tipica": {}}).keys())
    titulos = {"paz": "en paz", "ia_tipica": "IA típica", "guerra": "en guerra"}

    for nombre, filtro in (("Ramas políticas", lambda r: r["a"] in _politicos(raw)),
                           ("Ramas económicas", lambda r: r["a"] not in _politicos(raw))):
        w(f"## {nombre}")
        w("")
        w("Porcentaje de partidas en que la IA elige el primer foco (el resto elige el otro). "
          "⚠ marca un lado que sale más del 90%: el otro casi no existe para la IA.")
        w("")
        w("| Potencia | Foco | contra | abre (aprox.) | " + " | ".join(titulos.get(e, e) for e in escenarios) + " |")
        w("|---|---|---|---|" + "---|" * len(escenarios))
        for r in focos:
            if not filtro(r):
                continue
            celdas = []
            for e in escenarios:
                x = r["escenarios"][e].get(r["a"], 0.0)
                ninguno = r["escenarios"][e].get("ninguno", 0.0)
                marca = " ⚠" if x > AVISO or (1 - x - ninguno) > AVISO else ""
                celdas.append(_pct(x) + marca + (f" ({_pct(ninguno)} ninguno)" if ninguno >= 0.01 else ""))
            w(f"| {r['tag']} | {_nombre(raw, r['a'])} | {_nombre(raw, r['b'])} | {r['abre']} | " + " | ".join(celdas) + " |")
        w("")

    n = mundo["corridas"]
    p10, p50, p90, nunca = _percentiles(mundo["fin_disimulo"])
    w("## El Rearme Secreto")
    w("")
    w(f"Se termina el disimulo (tercer descubrimiento): el 10% de las partidas antes de {p10}, la mitad antes de {p50}, "
      f"el 90% antes de {p90}. Nunca, hasta {mundo['hasta']}: {_pct(nunca)}.")
    w("")
    w("| Potencia | veces descubierta por partida | la descubren primero | exposición máxima (media) |")
    w("|---|---|---|---|")
    for tag in mundo["exposicion_max"]:
        maxima = mundo["exposicion_max"][tag]
        w(f"| {tag} | {mundo['descubiertos'][tag] / n:.2f} | {_pct(mundo['primer_descubierto'][tag] / n)} | "
          f"{sum(maxima) / max(1, len(maxima)):.0f} |")
    w("")

    p10, p50, p90, vivo = _percentiles(mundo["muerte"])
    w("## La Sucesión del EFE")
    w("")
    w(f"Muere Aurelio IV: el 10% antes de {p10}, la mitad antes de {p50}, el 90% antes de {p90}. "
      f"Sigue vivo en {mundo['hasta']}: {_pct(vivo)}.")
    w("")
    w("| Al morir el Emperador | partidas |")
    w("|---|---|")
    nombres = {"EFE_heredero_tupa": "Tupã Benítez heredero", "EFE_heredero_pereira": "Yara Pereira, Custodia electa",
               "EFE_heredero_etchegaray": "Etchegaray regente", "sin_heredero": "sin heredero (golpe del Mariscal)"}
    for clave, cuenta in mundo["heredero_al_morir"].most_common():
        w(f"| {nombres.get(clave, clave.replace('_', ' '))} | {_pct(cuenta / n)} |")
    w("")
    anios = Counter()
    for (cual, anio), c in mundo["heredero_elegido"].items():
        anios[anio] += c
    if anios:
        w("Año en que la IA nombra heredero: " + ", ".join(f"{a}: {_pct(c / n)}" for a, c in sorted(anios.items())[:6]) + ".")
        w("")
    w("Colapsos del líder del EFE por partida (Salud en 0): " +
      ", ".join(f"{k}: {_pct(v / n)}" for k, v in sorted(mundo["colapsos"].items())) + ".")
    w("")

    c = crisis
    m = c["corridas"]
    total = sum(c["total"]) / m
    con_repeticion = sum(1 for s in c["seguidas"] if s > 0) / m
    w("## La crisis del siglo (2106-2120)")
    w("")
    w(f"{total:.0f} crisis por partida. La misma crisis dos veces seguidas: {sum(c['seguidas']) / m:.1f} veces por partida; "
      f"pasa al menos una vez en el {_pct(con_repeticion)} de las partidas.")
    w("")
    w("| Crisis | veces por partida |")
    w("|---|---|")
    for eid, cuenta in sorted(c["por_tipo"].items(), key=lambda x: -x[1]):
        w(f"| {c['titulos'].get(eid, eid)} | {cuenta / m:.1f} |")
    w("")
    w("Racha más larga de la misma crisis: " + ", ".join(f"{k} seguidas: {_pct(v / m)}" for k, v in sorted(c["racha_max"].items())) + ".")
    w("")

    w("## Supuestos que se usaron")
    w("")
    w("Condiciones del mapa que el motor no simula (probabilidad fija en supuestos.yaml): " +
      ", ".join(f"`{k}`" for k in sorted(mundo["supuestos"])) + ".")
    ignorados = [k for k, _ in mundo["ignorados"].most_common() if not k.startswith("evento:")]
    if ignorados:
        w("")
        w("Efectos que no cambian lo que se mide y no se simulan: " + ", ".join(f"`{k}`" for k in ignorados) + ".")
    w("")
    return "\n".join(L)


def _politicos(raw: dict) -> set[str]:
    """Focos de pares políticos: los que tienen ramas con peso 3 (las
    económicas pesan 1,5). Si cambia la convención, cambia acá."""
    salida = set()
    for arbol in (raw["focus_trees"].get("trees") or {}).values():
        for rama in arbol.get("branches") or []:
            if float(rama.get("ai_factor") or 1) >= 3:
                salida.update(f["id"] for f in rama.get("focuses") or [])
    return salida
