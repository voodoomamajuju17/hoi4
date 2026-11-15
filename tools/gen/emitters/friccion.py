"""Puntos de fricción entre potencias (spec/41_friccion.yaml, 2026-11-14).

Lo que es mecánica y no texto: la tensión de cada par, el pulso mensual, las crisis con objetivos de
guerra limitados a las regiones en disputa, la opinión por la causa, la IA y el Tratado de la Línea.
Los eventos y las decisiones salen del spec (incidentes a mano; crisis, tratados y decisiones,
tools/gen/friccion_spec.py).

La tensión vive en el país `a` de cada par (MN_friccion_<id>) y se copia al `b` después de cada cambio,
así los dos la ven en sus decisiones.
"""

from __future__ import annotations

from .. import friccion_spec as fs
from ..context import BuildContext
from ..pdx import Block, banner_for, render
from . import effects as effects_mod
from .effects import render_conditions, resolve_state

SOURCE = "spec/41_friccion.yaml"
LOC_FILE = "meganations_friccion"


def _cond(owner: str, cond: dict | None, triggers: dict) -> str:
    """Condición del spec en script (sin las llaves de afuera)."""
    if not cond:
        return ""
    body = render(Block([("x", render_conditions(owner, cond, triggers, where=SOURCE))]))
    return body[body.index("{") + 1:body.rindex("}")].strip()


def _regiones(ctx: BuildContext, nombres: list, faltan: list[str]) -> list[int]:
    ids = []
    for n in nombres or []:
        sid = resolve_state(n)
        if sid is None:
            faltan.append(" / ".join(n) if isinstance(n, list) else str(n))
        else:
            ids.append(sid)
    return ids


def _objetivos(quien: str, contra: list[str], ids: list[int]) -> str:
    """`quien` recibe un objetivo de guerra por cada región de `ids` que esté en manos de alguno de
    `contra` (el rival o sus satélites de arranque) al estallar la crisis."""
    out = []
    for sid in ids:
        for dueno in contra:
            out.append(f"\t\tif = {{ limit = {{ {sid} = {{ is_owned_by = {dueno} }} NOT = {{ has_wargoal_against = {dueno} }} }} "
                       f"create_wargoal = {{ type = take_state target = {dueno} generator = {{ {sid} }} }} }}")
    return f"\t{quien} = {{\n" + "\n".join(out) + "\n\t}\n" if out else ""


def emit(ctx: BuildContext) -> None:
    cfg = ctx.spec.raw.get("friccion")
    if not cfg:
        return
    effects_mod.use_states(ctx.data.get("state_ids_by_name"))
    alive = set((ctx.data.get("territory") or {}).values()) or {c.tag for c in ctx.spec.countries}
    subditos: dict[str, list[str]] = {}
    for c in ctx.spec.countries:
        if c.is_subject and c.overlord:
            subditos.setdefault(c.overlord, []).append(c.tag)
    triggers: dict[str, str] = {}
    faltan: list[str] = []
    pares = cfg.get("pares") or []
    lin = cfg.get("linea") or {}
    umbral_inc = int(cfg.get("inicio_incidentes", 25))
    chance = int(cfg.get("chance_incidente", 12))
    umbral_ia = int(cfg.get("umbral_ia", 50))
    umbral_crisis = int(cfg.get("umbral_crisis", 80))
    despues = int(cfg.get("despues_de_guerra", 35))
    dias_tratado = int(cfg.get("tratado_dias", 730))

    efectos: list[str] = []
    pulso: list[str] = []
    opiniones: list[str] = []
    planes: list[dict] = ctx.data.setdefault("unique_ai_plans", [])
    for par in pares:
        pid, a, b = par["id"], par["a"], par["b"]
        v, act = fs.var(pid), fs.activa(pid)
        lugar = par["lugar"]
        base = fs.base(par)
        crisis_ev, inc = f"{fs.NS}.{base + 3}", par["incidentes"]
        reg_a = _regiones(ctx, par.get("regiones_a"), faltan)   # de `a`, las quiere `b`
        reg_b = _regiones(ctx, par.get("regiones_b"), faltan)   # de `b`, las quiere `a`
        sync = f"\t{b} = {{ set_variable = {{ var = {v} value = {a}.{v} }} }}\n"
        # subir y bajar (con su aviso para el que elige)
        for nombre, delta, en, es in (("sube", 10, "rises by 10", "sube 10"), ("baja", -10, "falls by 10", "baja 10"),
                                      ("sube_mucho", 20, "rises by 20", "sube 20"),
                                      ("baja_mucho", -20, "falls by 20", "baja 20")):
            tt = f"MN_friccion_{pid}_tt_{nombre}"
            ctx.loc.define_and_reference(tt, en=f"The tension over {lugar['english']} {en}.",
                           es=f"La tensión por {lugar['spanish']} {es}.", file=LOC_FILE, origin=SOURCE)
            efectos.append(
                f"MN_friccion_{pid}_{nombre} = {{\n\tcustom_effect_tooltip = {tt}\n\thidden_effect = {{\n"
                f"\t\t{a} = {{ add_to_variable = {{ var = {v} value = {delta} }} clamp_variable = {{ var = {v} min = 0 max = 100 }} }}\n"
                f"\t{sync}\t}}\n}}\n")
        tt = f"MN_friccion_{pid}_tt_tratado"
        ctx.loc.define_and_reference(tt, en=f"The tension over {lugar['english']} falls by 30 and keeps falling for two years.",
                       es=f"La tensión por {lugar['spanish']} baja 30 y sigue bajando por dos años.",
                       file=LOC_FILE, origin=SOURCE)
        efectos.append(
            f"MN_friccion_{pid}_tratado = {{\n\tcustom_effect_tooltip = {tt}\n\thidden_effect = {{\n"
            f"\t\t{a} = {{ set_country_flag = {{ flag = {v}_tratado days = {dias_tratado} }} "
            f"add_to_variable = {{ var = {v} value = -30 }} clamp_variable = {{ var = {v} min = 0 max = 100 }} }}\n"
            f"\t{sync}\t}}\n}}\n")
        # la crisis: objetivos de guerra por las regiones en disputa, para los dos lados
        efectos.append(
            f"MN_friccion_{pid}_crisis = {{\n"
            + _objetivos(a, [b] + subditos.get(b, []), reg_b)
            + _objetivos(b, [a] + subditos.get(a, []), reg_a)
            + "}\n")
        # la opinión por la causa
        mod = f"MN_friccion_{pid}_opinion"
        opiniones.append(f"\t{mod} = {{ value = -30 }}\n")
        ctx.loc.define_and_reference(mod, en=par["opinion"]["english"], es=par["opinion"]["spanish"], file=LOC_FILE, origin=SOURCE)
        # el pulso de este par (corre en `a`, una vez por mes)
        activa = _cond(f"friccion {pid}", par.get("activa"), triggers) or f"country_exists = {b}"
        congelado = "has_global_flag = MN_linea" if lin and lin.get("par") == pid else "always = no"
        pulso.append(f"""\tif = {{
\t\tlimit = {{ tag = {a} }}
\t\tif = {{
\t\t\tlimit = {{ {activa} }}
\t\t\tif = {{
\t\t\t\tlimit = {{ NOT = {{ has_global_flag = {act} }} }}
\t\t\t\tset_global_flag = {act}
\t\t\t\tif = {{
\t\t\t\t\tlimit = {{ NOT = {{ has_country_flag = {v}_iniciada }} }}
\t\t\t\t\tset_country_flag = {v}_iniciada
\t\t\t\t\tset_variable = {{ var = {v} value = {int(par.get('inicio', 30))} }}
\t\t\t\t\tadd_opinion_modifier = {{ target = {b} modifier = {mod} }}
\t\t\t\t\t{b} = {{ add_opinion_modifier = {{ target = {a} modifier = {mod} }} }}
\t\t\t\t}}
\t\t\t}}
\t\t\tif = {{
\t\t\t\tlimit = {{ {congelado} }}
\t\t\t\tset_variable = {{ var = {v} value = 0 }}
\t\t\t}}
\t\t\telse_if = {{
\t\t\t\tlimit = {{ has_war_with = {b} }}
\t\t\t\tset_country_flag = {v}_guerra
\t\t\t}}
\t\t\telse = {{
\t\t\t\tif = {{
\t\t\t\t\tlimit = {{ has_country_flag = {v}_guerra }}
\t\t\t\t\tclr_country_flag = {v}_guerra
\t\t\t\t\tclr_country_flag = {v}_crisis
\t\t\t\t\tset_variable = {{ var = {v} value = {despues} }}
\t\t\t\t}}
\t\t\t\tif = {{
\t\t\t\t\tlimit = {{ has_country_flag = {v}_tratado }}
\t\t\t\t\tadd_to_variable = {{ var = {v} value = -2 }}
\t\t\t\t}}
\t\t\t\telse = {{ add_to_variable = {{ var = {v} value = 1 }} }}
\t\t\t\tclamp_variable = {{ var = {v} min = 0 max = 100 }}
\t\t\t\tif = {{
\t\t\t\t\tlimit = {{ check_variable = {{ var = {v} value = {umbral_inc} compare = greater_than_or_equals }} NOT = {{ has_country_flag = {v}_incidente }} }}
\t\t\t\t\trandom_list = {{
\t\t\t\t\t\t{chance} = {{
\t\t\t\t\t\t\tset_country_flag = {{ flag = {v}_incidente days = 180 }}
\t\t\t\t\t\t\trandom_list = {{
\t\t\t\t\t\t\t\t50 = {{ country_event = {{ id = {inc[0]} days = 1 }} }}
\t\t\t\t\t\t\t\t50 = {{ {b} = {{ country_event = {{ id = {inc[1]} days = 1 }} }} }}
\t\t\t\t\t\t\t}}
\t\t\t\t\t\t}}
\t\t\t\t\t\t{100 - chance} = {{ }}
\t\t\t\t\t}}
\t\t\t\t}}
\t\t\t\tif = {{
\t\t\t\t\tlimit = {{ check_variable = {{ var = {v} value = {umbral_crisis} compare = greater_than_or_equals }} NOT = {{ has_country_flag = {v}_crisis }} }}
\t\t\t\t\tset_country_flag = {v}_crisis
\t\t\t\t\tMN_friccion_{pid}_crisis = yes
\t\t\t\t\tcountry_event = {{ id = {crisis_ev} days = 1 }}
\t\t\t\t\t{b} = {{ country_event = {{ id = {crisis_ev} days = 1 }} }}
\t\t\t\t}}
\t\t\t\tif = {{
\t\t\t\t\tlimit = {{ has_country_flag = {v}_crisis check_variable = {{ var = {v} value = 60 compare = less_than }} }}
\t\t\t\t\tclr_country_flag = {v}_crisis
\t\t\t\t}}
\t\t\t}}
\t\t\tif = {{ limit = {{ country_exists = {b} }} {b} = {{ set_variable = {{ var = {v} value = {a}.{v} }} }} }}
\t\t}}
\t\telse = {{ clr_global_flag = {act} }}
\t}}
""")
        # la IA: con 50 se prepara contra el otro; con 80 (ya con objetivo de guerra) declara si puede
        if a in alive or b in alive:
            for x, y in ((a, b), (b, a)):
                tension = lambda n: {"country": {"tag": a, "when": {"variable_at_least": {"var": v, "value": n}}}}
                planes.append({"id": f"MN_friccion_{pid}_{x}_se_prepara", "country": x,
                               "enable": {"all": [{"global_flag": act}, tension(umbral_ia)]},
                               "strategies": [{"type": "prepare_for_war", "target": y, "value": 60},
                                              {"type": "antagonize", "target": y, "value": 40}]})
                planes.append({"id": f"MN_friccion_{pid}_{x}_declara", "country": x,
                               "enable": {"all": [{"global_flag": act}, tension(umbral_crisis),
                                                  {"at_war": False}, {"divisions_at_least": 20}]},
                               "strategies": [{"type": "declare_war", "target": y, "value": 60}]})

    # -- el Tratado de la Línea ----------------------------------------------------------
    if lin:
        par = next(p for p in pares if p["id"] == lin["par"])
        a, b, v = par["a"], par["b"], fs.var(lin["par"])
        condiciones = _cond("linea", fs.condiciones_linea(cfg, {p["id"]: p for p in pares}), triggers)
        hk = resolve_state("Hong Kong")
        peaje = next((p for p in pares if p["id"] == "peaje"), None)
        for k, en, es in (
                ("MN_linea_tt_reaccion",
                 "The Union is left out of both halves (the tension over the Malacca toll rises by 20); Japan, if it exists, sees its waters cut in two.",
                 "La Unión queda afuera de las dos mitades (la tensión por el peaje de Malaca sube 20); Japón, si existe, ve sus aguas cortadas por la raya."),
                ("MN_linea_tt_hong_kong",
                 "They get a claim on Hong Kong.", "Reciben un reclamo sobre Hong Kong.")):
            ctx.loc.define_and_reference(k, en=en, es=es, file=LOC_FILE, origin=SOURCE)
        opiniones.append("\tMN_linea_socios = { value = 50 }\n")
        ctx.loc.define_and_reference("MN_linea_socios", en="Partners of the Line", es="Socios de la Línea", file=LOC_FILE, origin=SOURCE)
        efectos.append(f"""MN_linea_firmar = {{
\tset_global_flag = MN_linea
\t{a} = {{
\t\tset_variable = {{ var = {v} value = 0 }}
\t\tclr_country_flag = {v}_crisis
\t\tdiplomatic_relation = {{ country = {b} relation = non_aggression_pact active = yes }}
\t\tadd_dynamic_modifier = {{ modifier = HSN_linea_oeste }}
\t\tadd_opinion_modifier = {{ target = {b} modifier = MN_linea_socios }}
\t\tcountry_event = {{ id = {fs.NS}.202 days = 1 }}
\t}}
\t{b} = {{
\t\tset_variable = {{ var = {v} value = 0 }}
\t\tadd_dynamic_modifier = {{ modifier = SHD_linea_este }}
\t\tadd_opinion_modifier = {{ target = {a} modifier = MN_linea_socios }}
\t\tcountry_event = {{ id = {fs.NS}.202 days = 1 }}
\t}}
\tMN_linea_reaccion_mundo = yes
\tevery_country = {{
\t\tlimit = {{ NOT = {{ tag = {a} tag = {b} }} is_ai = no }}
\t\tcountry_event = {{ id = {fs.NS}.203 days = 2 }}
\t}}
}}
MN_linea_reaccion_mundo = {{
{('	if = { limit = { country_exists = ' + peaje['a'] + ' } MN_friccion_peaje_sube_mucho = yes }') if peaje else ''}
\tif = {{
\t\tlimit = {{ country_exists = ZJP }}
\t\tZJP = {{
\t\t\tadd_war_support = 0.05
\t\t\tadd_opinion_modifier = {{ target = {a} modifier = meganations_afrenta }}
\t\t\tadd_opinion_modifier = {{ target = {b} modifier = meganations_afrenta }}
\t\t}}
\t}}
}}
MN_linea_reaccion = {{
\tcustom_effect_tooltip = MN_linea_tt_reaccion
}}
MN_linea_hong_kong_FROM = {{
\tcustom_effect_tooltip = MN_linea_tt_hong_kong
\t{('hidden_effect = { FROM = { add_state_claim = ' + str(hk) + ' } }') if hk else ''}
}}
MN_linea_romper = {{
\tclr_global_flag = MN_linea
\tset_global_flag = MN_linea_rota
\t{a} = {{
\t\tremove_dynamic_modifier = {{ modifier = HSN_linea_oeste }}
\t\tremove_opinion_modifier = {{ target = {b} modifier = MN_linea_socios }}
\t\tset_variable = {{ var = {v} value = {int(lin.get('tension_al_romperse', 70))} }}
\t\tset_country_flag = {v}_crisis
\t\tcountry_event = {{ id = {fs.NS}.204 days = 1 }}
\t}}
\t{b} = {{
\t\tremove_dynamic_modifier = {{ modifier = SHD_linea_este }}
\t\tremove_opinion_modifier = {{ target = {a} modifier = MN_linea_socios }}
\t\tset_variable = {{ var = {v} value = {a}.{v} }}
\t\tcountry_event = {{ id = {fs.NS}.204 days = 1 }}
\t}}
\tMN_friccion_{lin['par']}_crisis = yes
}}
""")
        pulso.append(f"""\t# el Tratado de la Línea: se rompe con una guerra entre los dos; la IA de {a} lo propone, rara vez
\tif = {{
\t\tlimit = {{ tag = {a} has_global_flag = MN_linea has_war_with = {b} }}
\t\tMN_linea_romper = yes
\t}}
\tif = {{
\t\tlimit = {{ tag = {a} is_ai = yes {condiciones} }}
\t\trandom_list = {{
\t\t\t{int(lin.get('chance', 3))} = {{ set_global_flag = MN_linea_propuesta {b} = {{ country_event = {{ id = {fs.NS}.200 days = 1 }} }} }}
\t\t\t{100 - int(lin.get('chance', 3))} = {{ }}
\t\t}}
\t}}
\t# si la Alta Mar la juega una persona, la propone la IA del Directorio
\tif = {{
\t\tlimit = {{ tag = {b} is_ai = yes {a} = {{ is_ai = no }} {condiciones} }}
\t\trandom_list = {{
\t\t\t{int(lin.get('chance', 3))} = {{ set_global_flag = MN_linea_propuesta {a} = {{ country_event = {{ id = {fs.NS}.200 days = 1 }} }} }}
\t\t\t{100 - int(lin.get('chance', 3))} = {{ }}
\t\t}}
\t}}
""")

    ctx.write_text("common/scripted_effects/meganations_friccion.txt",
                   banner_for(SOURCE) + "".join(efectos) + "MN_friccion_pulso = {\n" + "".join(pulso) + "}\n")
    ctx.write_text("common/opinion_modifiers/meganations_friccion.txt",
                   banner_for(SOURCE) + "opinion_modifiers = {\n" + "".join(opiniones) + "}\n")
    for k in ("custom_effect_tooltip", "hidden_effect", "add_to_variable", "clamp_variable", "set_variable",
              "set_country_flag", "clr_country_flag", "set_global_flag", "clr_global_flag", "add_opinion_modifier",
              "remove_opinion_modifier", "random_list", "country_event", "create_wargoal", "diplomatic_relation",
              "add_dynamic_modifier", "remove_dynamic_modifier", "every_country", "add_state_claim", "add_war_support"):
        ctx.verify_keys("effects", {k: SOURCE})
    triggers.update({k: SOURCE for k in ("tag", "has_global_flag", "has_country_flag", "has_war_with", "check_variable",
                                         "country_exists", "is_owned_by", "has_wargoal_against", "is_ai")})
    ctx.verify_keys("triggers", triggers)
    if faltan:
        ctx.warn(f"puntos de fricción: regiones que no están en el mapa de este juego (quedan afuera): {', '.join(sorted(set(faltan)))}")
    ctx.note(f"puntos de fricción: {len(pares)} pares ({', '.join(p['id'] for p in pares)})"
             + ("; Tratado de la Línea entre " + " y ".join((next(p for p in pares if p['id'] == lin['par'])['a'],
                                                            next(p for p in pares if p['id'] == lin['par'])['b'])) if lin else ""))
