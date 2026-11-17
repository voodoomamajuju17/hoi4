"""Puntos de fricción (spec/41_friccion.yaml, 2026-11-14): lo que se arma solo a partir de los pares.

Cada par trae a mano su lugar, su causa y dos incidentes. Lo que es igual para todos los pares sale
de acá, al cargar el spec (así lo ven también los pedidos de arte y la localización):

  - cuatro eventos por par en meganations_friccion: la crisis (base+3), la propuesta de tratado
    (base+4) y sus respuestas, aceptado (base+5) y rechazado (base+6). `base` es la decena del primer
    incidente (los salares: incidentes 11 y 12, crisis 13...). Comparten tres imágenes.
  - el panel de decisiones "Puntos de fricción": tratado, concesión y presión para cada lado de cada
    par, y la propuesta de la Línea para la Alta Mar y el Directorio.

La mecánica (tensión, pulso mensual, objetivos de guerra, IA) la escribe tools/gen/emitters/friccion.py.
"""

from __future__ import annotations

from typing import Any

NS = "meganations_friccion"
ARTE = {"crisis": "meganations_friccion_crisis", "tratado": "meganations_friccion_tratado",
        "rechazo": "meganations_friccion_rechazo"}


def var(pid: str) -> str:
    return f"MN_friccion_{pid}"


def activa(pid: str) -> str:
    return f"MN_friccion_{pid}_activa"


def base(par: dict) -> int:
    return int(str(par["incidentes"][0]).split(".")[-1]) // 10 * 10


def _t(par: dict, campo: str, idioma: str) -> str:
    return par[campo][idioma]


def eventos(par: dict) -> list[dict]:
    pid, b = par["id"], base(par)
    lugar_en, lugar_es = _t(par, "lugar", "english"), _t(par, "lugar", "spanish")
    causa_en, causa_es = _t(par, "causa", "english"), _t(par, "causa", "spanish")
    cap = lambda s: s[:1].upper() + s[1:]
    return [
        {"id": b + 3, "trigger": "effect", "picture": "GFX_report_event_generic_rally", "art": ARTE["crisis"],
         "title": {"english": f"Crisis over {lugar_en}", "spanish": f"Crisis por {lugar_es}"},
         "desc": {"english": f"{causa_en}\\n\\nThe tension can no longer be contained. Both governments now have a war goal over {lugar_en}: if war comes, it will not be for everything, it will be for that.",
                  "spanish": f"{causa_es}\\n\\nLa tensión ya no se puede contener. Los dos gobiernos tienen ahora un objetivo de guerra por {lugar_es}: si viene la guerra, no va a ser por todo, va a ser por eso."},
         "options": [
             {"name": {"english": "Let the guns speak.", "spanish": "Que hablen las armas."}, "ai_chance": 60,
              "effects": [{"effect": "add_war_support", "value": 0.03}]},
             {"name": {"english": "There is still time to talk.", "spanish": "Todavía hay tiempo para hablar."},
              "ai_chance": 40, "effects": [{"effect": "run", "value": f"MN_friccion_{pid}_baja"}]}],
         "src": "user_request"},
        {"id": b + 4, "trigger": "effect", "picture": "GFX_report_event_generic_sign_treaty1", "art": ARTE["tratado"],
         "title": {"english": f"A Treaty for {cap(lugar_en)}", "spanish": f"Un Tratado por {cap(lugar_es)}"},
         "desc": {"english": f"[From.GetName] proposes a treaty over {lugar_en}. {causa_en}\\n\\nIF WE SIGN: the tension falls sharply and keeps falling for two years.\\nIF WE REFUSE: it rises.",
                  "spanish": f"[From.GetName] propone un tratado por {lugar_es}. {causa_es}\\n\\nSI FIRMAMOS: la tensión baja mucho y sigue bajando por dos años.\\nSI NOS NEGAMOS: sube."},
         "options": [
             {"name": {"english": "Sign.", "spanish": "Firmar."}, "ai_chance": 60,
              "effects": [{"effect": "run", "value": f"MN_friccion_{pid}_tratado"},
                          {"effect": "event", "id": f"{NS}.{b + 5}", "target": "FROM"}]},
             {"name": {"english": "Refuse.", "spanish": "Negarse."}, "ai_chance": 40,
              "effects": [{"effect": "run", "value": f"MN_friccion_{pid}_sube"},
                          {"effect": "event", "id": f"{NS}.{b + 6}", "target": "FROM"}]}],
         "src": "user_request"},
        {"id": b + 5, "trigger": "effect", "picture": "GFX_report_event_generic_sign_treaty1", "art": ARTE["tratado"],
         "title": {"english": f"Treaty Signed: {cap(lugar_en)}", "spanish": f"Tratado Firmado: {cap(lugar_es)}"},
         "desc": {"english": f"[From.GetName] signed the treaty over {lugar_en}. For two years the tension will keep falling.",
                  "spanish": f"[From.GetName] firmó el tratado por {lugar_es}. Por dos años la tensión va a seguir bajando."},
         "options": [{"name": {"english": "Ink, not blood.", "spanish": "Tinta, no sangre."},
                      "effects": [{"effect": "add_political_power", "value": 25}]}],
         "src": "user_request"},
        {"id": b + 6, "trigger": "effect", "picture": "GFX_report_event_generic_rally", "art": ARTE["rechazo"],
         "title": {"english": f"Treaty Refused: {cap(lugar_en)}", "spanish": f"Tratado Rechazado: {cap(lugar_es)}"},
         "desc": {"english": f"[From.GetName] refused our treaty over {lugar_en}. The tension rises.",
                  "spanish": f"[From.GetName] rechazó nuestro tratado por {lugar_es}. La tensión sube."},
         "options": [{"name": {"english": "We tried.", "spanish": "Lo intentamos."}, "effects": []}],
         "src": "user_request"},
    ]


def _otro(par: dict, efecto_a: list[dict], efecto_b: list[dict]) -> dict:
    """`efecto_a` si el que decide es `a`, si no `efecto_b`."""
    return {"effect": "if", "when": {"tag": par["a"]}, "then": efecto_a, "else": efecto_b}


def decisiones(par: dict) -> list[dict]:
    pid, a, b = par["id"], par["a"], par["b"]
    en, es = par["lugar"]["english"], par["lugar"]["spanish"]
    def tension(op: str, v: int) -> dict:
        # con texto propio (el juego mostraba "Comuna Socialista Automatizada: Comuna Socialista Automatizada")
        menos = op == "variable_below"
        return {"explained": {
            "id": f"friccion_{pid}_{'menos' if menos else 'mas'}_{v}",
            "english": f"Tension over {par['lugar']['english']} {'below' if menos else 'at least'} {v}",
            "spanish": f"Tensión por {par['lugar']['spanish']} {'por debajo de' if menos else 'de al menos'} {v}",
            "when": {"country": {"tag": a, "when": {op: {"var": var(pid), "value": v}}}}}}
    en_paz = {"all": [{"not": {"war_with": a}}, {"not": {"war_with": b}}]}
    # 2026-11-17 ("si ya estoy en guerra con, por ejemplo el NRE con el ASC, no deberia seguir viendo el
    # panel de tension"): en guerra con el rival, las decisiones de ese punto no se ven
    de_lado = {"all": [{"any": [{"tag": a}, {"tag": b}]}, {"global_flag": activa(pid)}, en_paz]}
    # (el requisito se mostraba crudo: "No:MN_friccion_rin_tratado")
    sin_tratado = {"explained": {"id": f"friccion_{pid}_sin_tratado",
                                 "english": f"No treaty over {en} in force",
                                 "spanish": f"Sin un tratado vigente por {es}",
                                 "when": {"country": {"tag": a, "when": {"not": {"flag": f"{var(pid)}_tratado"}}}}}}
    ev = f"{NS}.{base(par) + 4}"
    # la tensión de ahora (la variable está en los dos países del par)
    ten_en, ten_es = f"\\n\\nTENSION NOW: [?{var(pid)}]/100.", f"\\n\\nTENSIÓN AHORA: [?{var(pid)}]/100."
    out = [
        {"id": f"MN_friccion_{pid}_proponer", "icon_prefer": ["generic_political_actions"],
         "name": {"english": f"Propose a Treaty: {en}", "spanish": f"Proponer un Tratado: {es}"},
         "desc": {"english": f"An embassy and a draft treaty over {en}. If the other side signs, the tension falls sharply and keeps falling for two years.",
                  "spanish": f"Una embajada y un borrador de tratado por {es}. Si el otro lado firma, la tensión baja mucho y sigue bajando por dos años."},
         "cost": 75, "cooldown_days": 365, "visible": de_lado,
         "available": {"all": [tension("variable_at_least", 20), sin_tratado, en_paz]},
         "effects": [_otro(par, [{"effect": "event", "id": ev, "target": b}], [{"effect": "event", "id": ev, "target": a}])],
         "ai": {"factor": 1, "modifiers": [{"factor": 3, "when": {"stability_below": 0.4}}]},
         "src": "user_request"},
        {"id": f"MN_friccion_{pid}_conceder", "icon_prefer": ["generic_political_actions"],
         "name": {"english": f"Make a Concession: {en}", "spanish": f"Hacer una Concesión: {es}"},
         "desc": {"english": f"Give way on {en} without asking for anything back. The tension falls a lot; at home, not everyone will like it.",
                  "spanish": f"Ceder en {es} sin pedir nada a cambio. La tensión baja mucho; adentro, no a todos les va a gustar."},
         "cost": 100, "cooldown_days": 365, "visible": de_lado,
         "available": {"all": [tension("variable_at_least", 15), en_paz]},
         "effects": [{"effect": "run", "value": f"MN_friccion_{pid}_baja_mucho"},
                     {"effect": "add_stability", "value": -0.03}],
         "ai": {"factor": 1, "modifiers": [{"factor": 3, "when": {"at_war": True}}]},
         "src": "user_request"},
        {"id": f"MN_friccion_{pid}_presionar", "icon_prefer": ["generic_army_support"],
         "name": {"english": f"Press the Claim: {en}", "spanish": f"Presionar: {es}"},
         "desc": {"english": f"Speeches, manoeuvres near the border and a firm note over {en}. The tension rises; with 80 a war goal opens for both sides.",
                  "spanish": f"Discursos, maniobras cerca de la frontera y una nota firme por {es}. La tensión sube; con 80 se abre un objetivo de guerra para los dos lados."},
         "cost": 25, "cooldown_days": 180, "visible": de_lado,
         "available": {"all": [tension("variable_below", 95), sin_tratado]},
         "effects": [{"effect": "run", "value": f"MN_friccion_{pid}_sube"},
                     {"effect": "add_war_support", "value": 0.03}],
         "ai": {"factor": 1, "modifiers": [{"factor": 0, "when": {"at_war": True}}]},
         "src": "user_request"},
    ]
    for d in out:
        d["desc"] = {"english": d["desc"]["english"] + ten_en, "spanish": d["desc"]["spanish"] + ten_es}
    return out


def condiciones_linea(cfg: dict, pares: dict) -> dict:
    lin = cfg.get("linea") or {}
    par = pares[lin["par"]]
    a, b = par["a"], par["b"]
    peaje = pares.get("peaje")
    amenaza: list[dict] = []
    if peaje:
        amenaza.append({"country": {"tag": peaje["a"], "when": {"variable_at_least": {"var": var("peaje"), "value": lin["amenaza_peaje"]}}}})
    amenaza.append({"all": [{"country_exists": "ZJP"}, {"country": {"tag": "ZJP", "when": {"war_with": a}}}]})
    return {"all": [
        {"date_after": str(lin["desde"])},
        {"country_exists": a}, {"country_exists": b},
        {"global_flag": activa(lin["par"])},
        {"country": {"tag": a, "when": {"variable_at_least": {"var": var(lin["par"]), "value": lin["tension_minima"]}}}},
        {"country": {"tag": a, "when": {"not": {"war_with": b}}}},
        {"country": {"tag": a, "when": {"variable_at_least": {"var": "MEGANATIONS_lider_astucia", "value": lin["astucia_minima"]}}}},
        {"country": {"tag": b, "when": {"variable_at_least": {"var": "MEGANATIONS_lider_astucia", "value": lin["astucia_minima"]}}}},
        {"any": amenaza},
        {"not": {"global_flag": "MN_linea"}}, {"not": {"global_flag": "MN_linea_propuesta"}},
    ]}


def expandir(raw: dict[str, Any], cfg: dict) -> None:
    pares = {p["id"]: p for p in cfg.get("pares") or []}
    ns = raw.setdefault("events", {}).setdefault("namespaces", {}).setdefault(NS, {"country": None, "events": []})
    decs: list[dict] = []
    for par in pares.values():
        ns["events"].extend(eventos(par))
        decs.extend(decisiones(par))
    if cfg.get("linea"):
        lin = cfg["linea"]
        a, b = pares[lin["par"]]["a"], pares[lin["par"]]["b"]
        decs.append({
            "id": "MN_linea_proponer", "icon_prefer": ["generic_political_actions"], "fire_only_once": True,
            "name": {"english": "Propose the Line", "spanish": "Proponer la Línea"},
            "desc": {"english": "A single stroke on the map of the world, from pole to pole: one half of the world's trade for us, the other for them, and Hong Kong a free port. The Sun Kingdom arbitrates. Only once: if they refuse, there is no second Line.",
                     "spanish": "Una sola raya en el mapa del mundo, de polo a polo: la mitad del comercio del mundo para nosotros, la otra para ellos, y Hong Kong puerto libre. Arbitra el Reino del Sol. Una sola vez: si se niegan, no hay segunda Línea."},
            "cost": 150,
            "visible": {"all": [{"any": [{"tag": a}, {"tag": b}]}, {"not": {"global_flag": "MN_linea"}},
                                {"not": {"global_flag": "MN_linea_propuesta"}}]},
            "available": condiciones_linea(cfg, pares),
            "effects": [{"effect": "global_flag", "value": "MN_linea_propuesta"},
                        {"effect": "if", "when": {"tag": a},
                         "then": [{"effect": "event", "id": f"{NS}.200", "target": b}],
                         "else": [{"effect": "event", "id": f"{NS}.200", "target": a}]}],
            "ai": {"factor": 0},
            "src": "user_request"})
    tags = sorted({t for p in pares.values() for t in (p["a"], p["b"])})
    raw.setdefault("decisions", {}).setdefault("categories", []).append({
        "id": "MN_friccion_category", "country": tags, "icon_prefer": ["generic_political_actions"],
        "name": {"english": "Points of Friction", "spanish": "Puntos de Fricción"},
        "desc": {"english": "What we and our rivals both want and cannot both have. Each point has a tension from 0 to 100: incidents and pressure raise it, treaties and concessions lower it. With 80 a war goal opens for both sides, only over the disputed regions.",
                 "spanish": "Lo que nosotros y nuestros rivales queremos y no podemos tener los dos. Cada punto tiene una tensión de 0 a 100: los incidentes y la presión la suben, los tratados y las concesiones la bajan. Con 80 se abre un objetivo de guerra para los dos lados, solo por las regiones en disputa."},
        "visible": {"any": [{"all": [{"any": [{"tag": p["a"]}, {"tag": p["b"]}]}, {"global_flag": activa(p["id"])},
                                     {"not": {"war_with": p["a"]}}, {"not": {"war_with": p["b"]}}]}
                            for p in pares.values()]},
        "src": "user_request", "decisions": decs})
