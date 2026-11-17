"""Las Leyendas (spec/42_leyendas.yaml, 2026-11-16): seis personajes legendarios por nación jugable.

Pedido: "prepara 6 portraits mas por nacion, un mariscal, un almirante, dos generales, un ministro y
un teorico/personal militar. Cada uno completamente original (en cuanto a stats-bonus y el portrait)
... Cada uno de estos se destraba con una decision, un foco, un evento, una aventura ... son de lo
mejorcito del juego y con lore."

Cada leyenda viene en el spec en forma compacta (quién es, su historia, sus números, su rasgo y su
llave). Acá, al cargar el spec, se arma todo lo demás, así lo ven también los pedidos de arte:

  - el personaje (recruit_in_history: false: no existe hasta que llega) con su retrato pedido;
  - su rasgo propio: de general/almirante (unit_leader_traits, con puntos y `modifier`) o de
    ministro (leader_traits); un ministro también suma stats al líder (lider_ck.ministros);
  - un evento de llegada en meganations_leyendas con su historia; la opción lo recluta;
  - la llave, que dispara ese evento una sola vez (bandera MN_leyenda_<id>):
      decision  una decisión en "Las Leyendas" de su nación, que se habilita con `cuando`;
      foco      al completar `foco` (se suma a la recompensa del foco);
      aventura  cuando la nación termina bien una aventura (`cuando`, lo mira el pulso mensual);
      evento    cuando pasa algo en el mundo (`cuando`, lo mira el pulso mensual).
    El pulso es MN_leyendas_pulso, que corre dentro de MEGANATIONS_lider_pulso (cada país, cada mes).
"""

from __future__ import annotations

from typing import Any

NS = "meganations_leyendas"
CARGOS = {"mariscal": "field_marshal", "general": "corps_commander", "almirante": "navy_leader"}
ASESORES = {"ministro", "teorico", "estado_mayor"}
PULSO = "MN_leyendas_pulso"
FOTO = {"mariscal": "GFX_report_event_generic_rally", "general": "GFX_report_event_generic_rally",
        "almirante": "GFX_report_event_generic_navy", "ministro": "GFX_report_event_generic_sign_treaty1",
        "teorico": "GFX_report_event_generic_research_lab", "estado_mayor": "GFX_report_event_generic_factory"}
LLAVE_TXT = {
    "decision": ("decision", "decisión"), "foco": ("focus", "foco"),
    "aventura": ("adventure", "aventura"), "evento": ("event", "evento"),
}


def bandera(cid: str) -> str:
    return f"MN_leyenda_{cid}"


def personajes(ley: dict) -> list[tuple[str, dict]]:
    return [(tag, p) for tag, nacion in ley.items() for p in nacion.get("personajes") or []]


def _llegada(p: dict) -> dict[str, str]:
    """La línea de lo que trae, al pie del evento."""
    r = p["rasgo"]
    if p["rol"] in CARGOS:
        return {"english": f"Joins our command with the trait {r['name']['english']}: {r['desc']['english']}",
                "spanish": f"Se suma a nuestro mando con el rasgo {r['name']['spanish']}: {r['desc']['spanish']}"}
    return {"english": f"Can be appointed to the government as {r['name']['english']}.",
            "spanish": f"Se lo puede nombrar en el gobierno como {r['name']['spanish']}."}


def expandir(ley: dict[str, Any]) -> dict[str, Any]:
    """Devuelve un overlay común (leaders, events, decisions, extend_focuses...) para merge_overlay."""
    chars, ut, lt, eventos, cats, pulso = [], [], [], [], [], []
    focos: dict[str, list] = {}
    ministros: dict[str, dict] = {}
    n = 0
    for tag, nacion in ley.items():
        decs = []
        for p in nacion.get("personajes") or []:
            n += 1
            cid = p["id"]
            rol = p["rol"]
            r = dict(p["rasgo"], src="user_request")
            ch = {"id": cid, "country": tag, "src": "user_request", "leyenda": True,
                  "recruit_in_history": False, "name": {"regnal": p["nombre"]}, "born": p["born"],
                  "lore": p["lore"]["spanish"], "look": p["look"],
                  "portrait": {"path": f"gfx/leaders/{tag}/{cid}.dds",
                               "role": "navy" if rol == "almirante" else "civilian" if rol in ASESORES else "army",
                               "placeholder": False}}
            if rol in CARGOS:
                r.setdefault("country", tag)
                if rol == "almirante":
                    r.setdefault("type", "navy")
                ut.append(r)
                ch["roles"] = {CARGOS[rol]: dict(p["habilidades"], traits=list(p.get("rasgos") or []) + [r["id"]])}
            elif rol in ASESORES:
                lt.append(r)
                cargo = dict(p.get("cargo") or {})
                cargo.setdefault("slot", "political_advisor" if rol == "ministro" else "theorist")
                cargo.setdefault("cost", 150 if rol == "ministro" else 100)
                cargo["traits"] = [r["id"]]
                ch["roles"] = {"advisor": cargo}
                if p.get("stats"):
                    ministros[cid] = dict(p["stats"])
            else:
                raise ValueError(f"leyenda {cid}: rol '{rol}' (mariscal, general, almirante, ministro, teorico, estado_mayor)")
            chars.append(ch)

            eid = f"{NS}.{n}"
            p["_evento"] = eid
            llegada = _llegada(p)
            eventos.append({
                "id": n, "trigger": "effect", "picture": FOTO[rol], "src": "user_request",
                # una imagen por nación para sus seis llegadas (arte/eventos_descripciones.yaml)
                "art": f"{NS}_{tag.lower()}",
                "title": {"english": f"Legend: {p['nombre']['english']}", "spanish": f"Leyenda: {p['nombre']['spanish']}"},
                "desc": {lang: f"{p['lore'][lang]}\\n\\n{llegada[lang]}" for lang in ("english", "spanish")},
                "options": [{"name": p.get("frase") or {"english": "Welcome. We have waited for you.",
                                                       "spanish": "Bienvenido. Te estábamos esperando."},
                             "ai_chance": 100,
                             "effects": [{"effect": "recruit", "character": cid}, {"effect": "add_political_power", "value": 25}]}],
            })
            llave = p["llave"]
            disparo = [{"effect": "flag", "value": bandera(cid)}, {"effect": "event", "id": eid, "days": 1}]
            tipo = llave["tipo"]
            if tipo == "decision":
                decs.append({
                    "id": f"{cid}_convocar", "src": "user_request", "fire_only_once": True,
                    "name": {"english": f"Summon {p['nombre']['english']}", "spanish": f"Convocar a {p['nombre']['spanish']}"},
                    "desc": {lang: f"{llave['texto'][lang]}\\n\\n{llegada[lang]}" for lang in ("english", "spanish")},
                    "icon_prefer": ["generic_political_actions"], "cost": int(llave.get("costo", 100)),
                    "visible": {"not_flag": bandera(cid)}, "available": llave["cuando"],
                    "effects": disparo, "ai": {"factor": 20}})
            elif tipo == "foco":
                # una lista: el que se complete primero (Japón y Albión tienen ramas excluyentes)
                for foco in llave["foco"] if isinstance(llave["foco"], list) else [llave["foco"]]:
                    focos.setdefault(foco, []).append(
                        {"effect": "if", "when": {"all": [{"tag": tag}, {"not_flag": bandera(cid)}]}, "then": disparo})
            elif tipo in ("aventura", "evento"):
                pulso.append({"effect": "if", "when": {"all": [{"tag": tag}, {"not_flag": bandera(cid)}, llave["cuando"]]},
                              "then": disparo})
            else:
                raise ValueError(f"leyenda {cid}: llave '{tipo}' (decision, foco, aventura, evento)")

        lista = {lang: "\\n".join(f"- {p['nombre'][lang]} ({LLAVE_TXT[p['llave']['tipo']][0 if lang == 'english' else 1]}): "
                                  f"{p['llave']['texto'][lang]}" for p in nacion.get("personajes") or [])
                 for lang in ("english", "spanish")}
        cats.append({
            "id": f"{tag}_leyendas_category", "country": tag, "src": "user_request",
            "icon_prefer": ["generic_formable_nations", "generic_political_actions"],
            "name": {"english": "The Legends", "spanish": "Las Leyendas"},
            "desc": {lang: f"{nacion['intro'][lang]}\\n\\n{lista[lang]}" for lang in ("english", "spanish")},
            "decisions": decs})

    return {
        "leaders": {"characters": chars, "leader_traits": lt, "unit_leader_traits": ut},
        "lider_ck": {"ministros": ministros},
        "events": {"namespaces": {NS: {"country": None, "events": eventos}}},
        "decisions": {"categories": cats, "scripted_effects": [{"id": PULSO, "src": "user_request", "effects": pulso}]},
        "extend_scripted_effects": {"MEGANATIONS_lider_pulso": [{"effect": "run", "value": PULSO}]},
        "extend_focuses": {f: {"reward_append": e} for f, e in focos.items()},
    }
