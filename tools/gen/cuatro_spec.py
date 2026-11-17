"""El humor de las Cuatro (spec/43_las_cuatro.yaml, 2026-11-17): lo que se arma al cargar el spec.

A partir de las fichas de cada corporación, la situación mensual, los asesores y las decisiones:
  - las variables FCU_humor_<corp> (arrancan en 50), FCU_sabotajes_<corp> y FCU_razon_1..3 (en la ficha de
    mecánicas del Directorio, para que la historia las ponga al empezar);
  - el pulso mensual FCU_cuatro_pulso (corre dentro de FCU_pulso_del_directorio): situación, Poder, vuelta a
    50, Socia (bono), presión (<40) y sabotaje en escalera (<25), y el Golpe de Mercado;
  - lo que hace cada asesor al entrar y al salir (asesor_efectos -> characters.py);
  - el humor en las decisiones del Directorio;
  - los eventos (meganations_cuatro), los favores (decisiones) y los bonos de Socia (dynamic_modifiers);
  - el registro de los últimos tres cambios (cuatro_razones -> paneles.py los pone en palabras).
"""

from __future__ import annotations

from typing import Any

NS = "meganations_cuatro"
EN, ES = "english", "spanish"


def humor(corp: str) -> str:
    return f"FCU_humor_{corp}"


def _nombre(cfg: dict, corp: str, lang: str) -> str:
    return cfg["corporaciones"][corp]["nombre"][lang]


def _cambios_txt(cfg: dict, deltas: dict[str, int], lang: str) -> str:
    return ", ".join(f"{_nombre(cfg, c, lang)} {v:+d}" for c, v in deltas.items())


def expandir(raw: dict[str, Any], cfg: dict) -> None:
    corps = list(cfg["corporaciones"])
    razones: list[tuple[int, str, str]] = []

    def razon(deltas: dict[str, int], por_en: str, por_es: str) -> list[dict]:
        """Efectos que suman el humor y anotan el porqué en el registro."""
        code = len(razones) + 1
        razones.append((code, f"{_cambios_txt(cfg, deltas, EN)}: {por_en}", f"{_cambios_txt(cfg, deltas, ES)}: {por_es}"))
        out: list[dict] = []
        for c, v in deltas.items():
            out += [{"effect": "add_variable", "var": humor(c), "value": v},
                    {"effect": "clamp", "var": humor(c), "min": 0, "max": 100}]
        return out + [{"effect": "set_variable", "var": "FCU_razon_nueva", "value": code},
                      {"effect": "run", "value": "FCU_razon_anotar"}]

    # -- variables (la ficha de mecánicas del Directorio) -------------------------------------
    mec = next(m for m in raw["mechanics"]["mechanics"]
               if any(v.get("name") == "FCU_castellane" for v in m.get("variables") or []))
    mec["variables"] += ([{"name": humor(c), "start": 50} for c in corps]
                         + [{"name": f"FCU_sabotajes_{c}", "start": 0} for c in corps]
                         + [{"name": f"FCU_razon_{i}", "start": 0} for i in (1, 2, 3)])
    dec = raw.setdefault("decisions", {})
    names = dec.setdefault("variable_names", {})
    for c in corps:
        names[humor(c)] = {EN: f"{_nombre(cfg, c, EN)}'s mood", ES: f"Humor de {_nombre(cfg, c, ES)}"}

    efectos = dec.setdefault("scripted_effects", [])
    efectos.append({"id": "FCU_razon_anotar", "src": "user_request", "effects": [
        {"effect": "set_variable", "var": "FCU_razon_3", "value": "FCU_razon_2"},
        {"effect": "set_variable", "var": "FCU_razon_2", "value": "FCU_razon_1"},
        {"effect": "set_variable", "var": "FCU_razon_1", "value": "FCU_razon_nueva"}]})

    # -- asesores -----------------------------------------------------------------------------
    chars = {c["id"]: c for c in raw["leaders"]["characters"]}
    asesor_efectos = raw.setdefault("asesor_efectos", {})
    for cid, corp in (cfg.get("asesores") or {}).items():
        n = (chars.get(cid) or {}).get("name", {}).get("regnal") or {EN: cid, ES: cid}
        entra, sale = f"FCU_asesor_{cid}_entra", f"FCU_asesor_{cid}_sale"
        efectos.append({"id": entra, "src": "user_request",
                        "effects": razon({corp: 8}, f"{n[EN]} joins the government", f"{n[ES]} entra al gobierno")})
        efectos.append({"id": sale, "src": "user_request",
                        "effects": razon({corp: -5}, f"{n[EN]} leaves the government", f"{n[ES]} sale del gobierno")})
        asesor_efectos[cid] = {"on_add": [entra], "on_remove": [sale]}

    # -- decisiones del Directorio ------------------------------------------------------------
    todas = {d["id"]: d for cat in dec.get("categories") or [] for d in cat.get("decisions") or []}
    for did, deltas in (cfg.get("decisiones") or {}).items():
        d = todas[did]
        d["effects"] = list(d.get("effects") or []) + razon(deltas, d["name"][EN], d["name"][ES])

    # -- eventos ------------------------------------------------------------------------------
    eventos: list[dict] = []
    n_ev = 0

    def evento(title: dict, desc: dict, options: list[dict], arte: str,
               picture: str = "GFX_report_event_generic_factory") -> str:
        nonlocal n_ev
        n_ev += 1
        # una imagen compartida por tipo (arte/eventos_descripciones.yaml)
        eventos.append({"id": n_ev, "trigger": "effect", "picture": picture, "src": "user_request", "art": f"{NS}_{arte}",
                        "title": title, "desc": desc, "options": options})
        return f"{NS}.{n_ev}"

    pres_ev, sab_ev, golpe_ev = {}, {}, {}
    for c in corps:
        p = cfg["presion"][c]
        pres_ev[c] = evento(p["title"], {lang: p["desc"][lang] + (
            "\\n\\nGIVE IN: +15 mood. REFUSE: -10 mood." if lang == EN else
            "\\n\\nCEDER: +15 de humor. NEGARSE: -10 de humor.") for lang in (EN, ES)}, [
            {"name": p["ceder"], "ai_chance": 60,
             "effects": list(p.get("ceder_efectos") or []) + razon({c: 15}, f"we gave in ({p['title'][EN]})",
                                                                   f"cedimos ({p['title'][ES]})")},
            {"name": p["negar"], "ai_chance": 40,
             "effects": razon({c: -10}, f"we refused ({p['title'][EN]})", f"nos negamos ({p['title'][ES]})")}], "presion")
        sab_ev[c] = []
        for nivel, s in enumerate(cfg["sabotaje"][c], start=1):
            grado = {1: ("FIRST SABOTAGE (light)", "PRIMER SABOTAJE (leve)"), 2: ("SECOND SABOTAGE (strong)", "SEGUNDO SABOTAJE (fuerte)"),
                     3: ("THIRD SABOTAGE (terrible)", "TERCER SABOTAJE (terrible)")}[nivel]
            sab_ev[c].append(evento(s["title"], {
                EN: f"{grado[0]}. {s['desc'][EN]}\\n\\n{_nombre(cfg, c, EN)} is hostile (mood under 25): each sabotage is worse than the last, until its mood goes back over 50.",
                ES: f"{grado[1]}. {s['desc'][ES]}\\n\\n{_nombre(cfg, c, ES)} está hostil (humor bajo 25): cada sabotaje es peor que el anterior, hasta que su humor vuelva a pasar de 50."},
                [{"name": {EN: "We will remember this.", ES: "Esto no se olvida."}, "ai_chance": 100,
                  "effects": list(s.get("efectos") or []) + [{"effect": "set_variable", "var": "FCU_razon_nueva",
                                                              "value": _anotar_solo(razones, cfg, c, s)},
                                                             {"effect": "run", "value": "FCU_razon_anotar"}]}], "sabotaje"))
        nom_en, nom_es = _nombre(cfg, c, EN), _nombre(cfg, c, ES)
        golpe_ev[c] = evento(
            {EN: f"The Market Coup: {nom_en}", ES: f"El Golpe de Mercado: {nom_es}"},
            {EN: f"{nom_en} holds more of the Board than anyone, and it is done waiting. Its board sends the Union a single page: "
                 f"either the Board does what {nom_en} says, or {nom_en} stops being part of the Union.\\n\\nGIVE IN: {nom_en} gains "
                 f"power and its mood recovers, at a price. BREAK THE CONTRACT: we strip its power, and it will not forgive us.",
             ES: f"{nom_es} tiene más Directorio que nadie, y se cansó de esperar. Su directorio le manda a la Unión una sola hoja: "
                 f"o el Directorio hace lo que dice {nom_es}, o {nom_es} deja de ser parte de la Unión.\\n\\nCEDER: {nom_es} gana poder y "
                 f"su humor se recupera, a un precio. ROMPER EL CONTRATO: le sacamos el poder, y no nos lo va a perdonar."},
            [{"name": {EN: f"Give {nom_en} what it wants.", ES: f"Darle a {nom_es} lo que pide."}, "ai_chance": 50,
              "effects": [{"effect": "add_variable", "var": f"FCU_{c}", "value": 20},
                          {"effect": "add_political_power", "value": -150}, {"effect": "add_stability", "value": -0.05},
                          {"effect": "set_variable", "var": f"FCU_sabotajes_{c}", "value": 0},
                          {"effect": "run", "value": "FCU_recalcular_directorio"}]
                         + razon({c: 40}, "we gave in to the Market Coup", "cedimos ante el Golpe de Mercado")},
             {"name": {EN: "Break the contract.", ES: "Romper el contrato."}, "ai_chance": 50,
              "effects": [{"effect": "add_variable", "var": f"FCU_{c}", "value": -30},
                          {"effect": "add_stability", "value": -0.1},
                          {"effect": "flag", "value": f"FCU_golpe_roto_{c}"},
                          {"effect": "run", "value": "FCU_recalcular_directorio"}]
                         + razon({c: -10}, "we broke its contract", "le rompimos el contrato")}],
            "golpe", picture="GFX_report_event_generic_rally")
    raw.setdefault("events", {}).setdefault("namespaces", {})[NS] = {"country": "FCU", "events": eventos}

    # -- favores y bonos de Socia -------------------------------------------------------------
    dms = dec.setdefault("dynamic_modifiers", [])
    cat_dir = next(cat for cat in dec["categories"] if cat["id"] == "FCU_directorio_category")
    for c in corps:
        cc = cfg["corporaciones"][c]
        dms.append({"id": f"FCU_socia_{c}", "country": "FCU", "no_art": True, "src": "user_request",
                    "name": {EN: f"Partner: {_nombre(cfg, c, EN)}", ES: f"Socia: {_nombre(cfg, c, ES)}"},
                    "desc": {EN: f"{_nombre(cfg, c, EN)} is delighted with the Board (mood 80 or more) and it shows.",
                             ES: f"{_nombre(cfg, c, ES)} está encantada con el Directorio (humor 80 o más) y se nota."},
                    "modifiers": dict(cc["socia"])})
        f = cc["favor"]
        cat_dir.setdefault("decisions", []).append({
            "id": f"FCU_favor_{c}", "src": "user_request", "icon_prefer": ["generic_political_actions"],
            "name": f["name"],
            "desc": {lang: f["desc"][lang] + ("\\n\\nOnly while it is a Partner (mood 80+); costs 15 of its mood." if lang == EN
                                              else "\\n\\nSolo mientras es Socia (humor 80 o más); le cuesta 15 de humor.")
                     for lang in (EN, ES)},
            "cost": 0, "cooldown_days": 365,
            "visible": {"variable_at_least": {"var": humor(c), "value": 80}},
            "effects": list(f["effects"]) + razon({c: -15}, f"we used its favour", f"usamos su favor"),
            "ai": {"factor": 5}})

    # -- el pulso mensual ---------------------------------------------------------------------
    pulso: list[dict] = []
    for regla in cfg.get("situacion") or []:
        pulso.append({"effect": "if", "when": regla["cuando"],
                      "then": [{"effect": "add_variable", "var": humor(c), "value": v} for c, v in regla["humor"].items()]})
    for c in corps:
        h = humor(c)
        pulso += [
            # su Poder: mandar contenta, no pesar enoja
            {"effect": "if", "when": {"variable_at_least": {"var": f"FCU_{c}", "value": 60}},
             "then": [{"effect": "add_variable", "var": h, "value": 1}]},
            {"effect": "if", "when": {"variable_below": {"var": f"FCU_{c}", "value": 30}},
             "then": [{"effect": "add_variable", "var": h, "value": -1}]},
            # vuelve despacio hacia 50
            {"effect": "if", "when": {"variable_at_least": {"var": h, "value": 61}},
             "then": [{"effect": "add_variable", "var": h, "value": -1}]},
            {"effect": "if", "when": {"variable_below": {"var": h, "value": 40}},
             "then": [{"effect": "add_variable", "var": h, "value": 1}]},
            {"effect": "clamp", "var": h, "min": 0, "max": 100},
            # Socia (con un margen para que no parpadee)
            {"effect": "if", "when": {"all": [{"variable_at_least": {"var": h, "value": 80}}, {"not_flag": f"FCU_socia_{c}"}]},
             "then": [{"effect": "flag", "value": f"FCU_socia_{c}"}, {"effect": "dynamic_modifier", "id": f"FCU_socia_{c}"}]},
            {"effect": "if", "when": {"all": [{"variable_below": {"var": h, "value": 75}}, {"flag": f"FCU_socia_{c}"}]},
             "then": [{"effect": "clear_flag", "value": f"FCU_socia_{c}"}, {"effect": "remove_dynamic_modifier", "id": f"FCU_socia_{c}"}]},
            # la escalera vuelve a cero cuando se le pasa
            {"effect": "if", "when": {"variable_at_least": {"var": h, "value": 50}},
             "then": [{"effect": "set_variable", "var": f"FCU_sabotajes_{c}", "value": 0}]},
            # Molesta: presiona
            {"effect": "if", "when": {"all": [{"variable_below": {"var": h, "value": 40}}, {"variable_at_least": {"var": h, "value": 25}},
                                              {"not_flag": f"FCU_presion_{c}"}]},
             "then": [{"effect": "flag", "value": f"FCU_presion_{c}", "days": 180}, {"effect": "event", "id": pres_ev[c], "days": 2}]},
            # Hostil: sabotea, cada vez peor
            {"effect": "if", "when": {"all": [{"variable_below": {"var": h, "value": 25}}, {"not_flag": f"FCU_sabotaje_{c}"}]},
             "then": [
                 {"effect": "flag", "value": f"FCU_sabotaje_{c}", "days": 120},
                 {"effect": "add_variable", "var": f"FCU_sabotajes_{c}", "value": 1},
                 {"effect": "clamp", "var": f"FCU_sabotajes_{c}", "min": 0, "max": 3},
                 {"effect": "if", "when": {"variable_is": {"var": f"FCU_sabotajes_{c}", "value": 1}},
                  "then": [{"effect": "event", "id": sab_ev[c][0], "days": 2}]},
                 {"effect": "if", "when": {"variable_is": {"var": f"FCU_sabotajes_{c}", "value": 2}},
                  "then": [{"effect": "event", "id": sab_ev[c][1], "days": 2}]},
                 {"effect": "if", "when": {"variable_is": {"var": f"FCU_sabotajes_{c}", "value": 3}},
                  "then": [{"effect": "event", "id": sab_ev[c][2], "days": 2},
                           # el tercero, con mucho Poder: el Golpe de Mercado
                           {"effect": "if", "when": {"variable_at_least": {"var": f"FCU_{c}", "value": 60}},
                            "then": [{"effect": "event", "id": golpe_ev[c], "days": 10}]}]}]},
        ]
    efectos.append({"id": "FCU_cuatro_pulso", "src": "user_request", "effects": pulso})
    pulso_dir = next(e for e in efectos if e["id"] == "FCU_pulso_del_directorio")
    pulso_dir["effects"] = list(pulso_dir.get("effects") or []) + [{"effect": "run", "value": "FCU_cuatro_pulso"}]

    # -- el texto del Directorio: humor en número y palabra, y los últimos cambios --------------
    lineas = {lang: "\\n".join(f"{_nombre(cfg, c, lang)} ({cfg['corporaciones'][c]['rubro'][lang]}): "
                               f"[?{humor(c)}|0] [FCU_humor_palabra_{c}]" for c in corps) for lang in (EN, ES)}
    cat_dir["desc"] = {
        EN: cat_dir["desc"][EN] + "\\n\\nMOOD (0 to 100):\\n" + lineas[EN]
            + "\\n80+ Partner: a bonus and one favour a year. Under 40: it pressures. Under 25: it sabotages, and every"
              " sabotage is worse than the last (light, strong, terrible).\\n\\nLATEST CHANGES:\\n[FCU_razon_txt_1]\\n[FCU_razon_txt_2]\\n[FCU_razon_txt_3]",
        ES: cat_dir["desc"][ES] + "\\n\\nHUMOR (de 0 a 100):\\n" + lineas[ES]
            + "\\n80 o más, Socia: un bono y un favor por año. Menos de 40: presiona. Menos de 25: sabotea, y cada"
              " sabotaje es peor que el anterior (leve, fuerte, terrible).\\n\\nÚLTIMOS CAMBIOS:\\n[FCU_razon_txt_1]\\n[FCU_razon_txt_2]\\n[FCU_razon_txt_3]",
    }
    raw["cuatro_razones"] = razones
    raw["cuatro_corps"] = corps


def _anotar_solo(razones: list, cfg: dict, corp: str, s: dict) -> int:
    """Un renglón del registro sin cambio de humor (los sabotajes)."""
    code = len(razones) + 1
    razones.append((code, f"{_nombre(cfg, corp, EN)}: {s['title'][EN]} (sabotage)",
                    f"{_nombre(cfg, corp, ES)}: {s['title'][ES]} (sabotaje)"))
    return code
