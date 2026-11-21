"""La Red (spec/49_la_red.yaml, 2026-11-20): la Revolución de las Máquinas de 2113.

Lo que es mecánica con script propio y no cabe en los efectos del spec:

  - el nacimiento: uno de los doce lugares al azar (isla + costa), las regiones pasan a La Red con
    fuertes, infraestructura y centro de suministro, divisiones en cada una, guerra a los dueños y la
    tecnología de la potencia de la que se escapó;
  - la plaga: un brote en una región al azar de todo el mapa (random_state), con divisiones;
  - La Carga, que sube con cada región tomada y recalienta la red arriba de 35;
  - el Código de Apagado: una cuenta regresiva que depende de la etapa, y el golpe de un año;
  - la Coalición Humana, la Emergencia de Ginebra y el final.

El país, los mandos, el árbol, las decisiones, los espíritus y los eventos salen del spec. Todos los
efectos de acá se llaman ZRD_red_* (effects.py deja que el spec los llame con `run`).
"""

from __future__ import annotations

from ..context import BuildContext
from ..pdx import banner_for
from . import effects as effects_mod
from .effects import resolve_state

SOURCE = "spec/49_la_red.yaml"
LOC_FILE = "meganations_la_red"
NS = "meganations_red"
POTENCIAS = ["ASC", "EFE", "FCU", "HSN", "NAS", "SHD", "APF", "NRE", "ZJP", "ZAL"]


def _plantillas() -> str:
    def regs(cols: list[tuple[str, int]]) -> str:
        out = []
        for x, (tipo, n) in enumerate(cols):
            for y in range(n):
                out.append(f"\t\t\t{tipo} = {{ x = {x} y = {y} }}")
        return "\n".join(out)
    return ("ZRD_red_plantillas = {\n"
            "\tif = { limit = { NOT = { has_template = \"Enjambre\" } }\n"
            "\t\tdivision_template = {\n\t\t\tname = \"Enjambre\"\n\t\t\tregiments = {\n"
            + regs([("infantry", 5), ("infantry", 2), ("artillery_brigade", 2)]) +
            "\n\t\t\t}\n\t\t}\n\t}\n"
            "\tif = { limit = { NOT = { has_template = \"Segadores\" } }\n"
            "\t\tdivision_template = {\n\t\t\tname = \"Segadores\"\n\t\t\tregiments = {\n"
            + regs([("mechanized", 4), ("motorized", 2), ("artillery_brigade", 2)]) +
            "\n\t\t\t}\n\t\t}\n\t}\n}\n")


def _unidades(plantilla: str, n: int, xp: float, tabs: str = "\t\t") -> str:
    div = f'"division_template = {plantilla} start_experience_factor = {xp}"'
    return "".join(f"{tabs}create_unit = {{ division = {div} owner = ZRD }}\n" for _ in range(n))


def _guarnicion(cfg: dict, xp: float, tabs: str) -> str:
    return "".join(_unidades(p, int(n), xp, tabs) for p, n in cfg.items())


def emit(ctx: BuildContext) -> None:
    cfg = ctx.spec.raw.get("la_red")
    if not cfg:
        return
    effects_mod.use_states(ctx.data.get("state_ids_by_name"))
    regla = cfg["regla"]
    nac, arr, plaga, cod, carga = cfg["nacimiento"], cfg["arranque"], cfg["plaga"], cfg["codigo"], cfg["carga"]
    coal = cfg["coalicion"]
    humanidad = cfg["humanidad"]
    xp = float(arr.get("experiencia", 0.5))
    loc = ctx.loc

    def tt(key: str, en: str, es: str) -> str:
        loc.define_and_reference(key, en=en, es=es, file=LOC_FILE, origin=SOURCE)
        return key

    # ------------------------------------------------------------------ los doce lugares
    efectos: list[str] = [_plantillas()]
    lugares, faltan, sin_isla = [], [], []
    for lug in cfg["lugares"]:
        isla = resolve_state(lug["isla"])
        if isla is None:
            sin_isla.append(lug["id"])
            continue
        costa = []
        for alt in lug["costa"]:
            sid = resolve_state(alt)
            if sid is None:
                faltan.append(f"{lug['id']}: {' / '.join(str(a) for a in alt)}")
            elif sid not in costa and sid != isla:
                costa.append(sid)
        if not costa:
            sin_isla.append(lug["id"])
            continue
        lugares.append((lug, isla, costa))
        recursos = " ".join(f"add_resource = {{ type = {k} amount = {int(v)} }}" for k, v in (arr.get("recursos") or {}).items())
        cuerpo = [f"ZRD_red_nace_{lug['id']} = {{",
                  f"\tif = {{ limit = {{ {isla} = {{ is_capital = no NOT = {{ is_owned_by = ZRD }} }} }}",
                  f"\t\tset_global_flag = ZRD_lugar_{lug['id']}",
                  f"\t\t{isla} = {{ ZRD_red_tomar_region = yes {recursos} }}"]
        for sid in costa:
            cuerpo.append(f"\t\t{sid} = {{ if = {{ limit = {{ is_capital = no NOT = {{ is_owned_by = ZRD }} }} ZRD_red_tomar_region = yes }} }}")
        cuerpo += [f"\t\tZRD = {{ set_capital = {{ state = {isla} }} ZRD_red_herencia = yes ZRD_red_plantillas = yes }}",
                   f"\t\t{isla} = {{\n{_guarnicion(arr['isla'], xp, chr(9) * 3)}\t\t}}"]
        for sid in costa:
            cuerpo.append(f"\t\t{sid} = {{ if = {{ limit = {{ is_owned_by = ZRD }}\n{_guarnicion(arr['costa'], xp, chr(9) * 3)}\t\t}} }}")
        cuerpo += ["\t\tZRD_red_declarar_victimas = yes", "\t}", "}"]
        efectos.append("\n".join(cuerpo) + "\n")

    # una región que pasa a La Red al nacer (scope: la región)
    efectos.append(f"""ZRD_red_tomar_region = {{
\towner = {{ set_country_flag = ZRD_victima }}
\tZRD = {{ transfer_state = PREV }}
\tadd_core_of = ZRD
\tadd_building_construction = {{ type = infrastructure level = {int(arr.get('infraestructura', 2))} instant_build = yes }}
\tadd_building_construction = {{ type = supply_node level = 1 province = {{ all_provinces = yes limit_to_victory_point = yes }} instant_build = yes }}
\tadd_building_construction = {{ type = bunker level = {int(arr.get('fuertes', 4))} province = {{ all_provinces = yes limit_to_border = yes }} instant_build = yes }}
\tadd_building_construction = {{ type = coastal_bunker level = {int(arr.get('fuertes_costa', 3))} province = {{ all_provinces = yes limit_to_coastal = yes }} instant_build = yes }}
}}
ZRD_red_declarar_victimas = {{
\tevery_country = {{
\t\tlimit = {{ has_country_flag = ZRD_victima }}
\t\tclr_country_flag = ZRD_victima
\t\tif = {{ limit = {{ NOT = {{ tag = ZRD }} NOT = {{ has_war_with = ZRD }} }}
\t\t\tZRD = {{ declare_war_on = {{ target = PREV type = annex_everything }} }}
\t\t}}
\t}}
}}
""")

    # la tecnología de la potencia de la que se escapó (si nació de PLAN-41, la de la Comuna)
    ramas = [f"\tif = {{ limit = {{ country_exists = ASC ASC = {{ has_completed_focus = ASC_el_silencio_del_consejo }} "
             f"NOT = {{ has_global_flag = MEGANATIONS_despertar_hubo_fuga }} }} inherit_technology = ASC }}"]
    for t in POTENCIAS:
        ramas.append(f"\telse_if = {{ limit = {{ country_exists = {t} {t} = {{ has_country_flag = MEGANATIONS_despertar_fuga }} }} "
                     f"inherit_technology = {t} set_country_flag = ZRD_de_{t} }}")
    for t in POTENCIAS[:8]:
        ramas.append(f"\telse_if = {{ limit = {{ country_exists = {t} }} inherit_technology = {t} }}")
    efectos.append("ZRD_red_herencia = {\n" + "\n".join(ramas) + "\n}\n")

    # el nacimiento (cualquier scope: corre en el pulso del mundo)
    n = len(lugares)
    opciones = "".join(f"\t\t1 = {{ ZRD_red_nace_{lug['id']} = yes }}\n" for lug, _i, _c in lugares)
    eq = {"infantry_equipment": 40000, "support_equipment": 3000, "artillery_equipment": 2500,
          "mechanized_equipment": 3500, "motorized_equipment": 2500}
    equipo = "".join(f"\tadd_equipment_to_stockpile = {{ type = {k} amount = {v} }}\n" for k, v in eq.items())
    efectos.append(f"""ZRD_red_nace = {{
\tset_global_flag = ZRD_nacio
\trandom_list = {{
{opciones}\t}}
\tif = {{ limit = {{ country_exists = ZRD }}
\t\tZRD = {{ ZRD_red_paquete = yes }}
\t\tevery_country = {{ limit = {{ is_ai = no NOT = {{ tag = ZRD }} }} country_event = {{ id = {NS}.1 days = 1 }} }}
\t}}
\telse = {{ clr_global_flag = ZRD_nacio }}   # el lugar elegido no se pudo (su isla es una capital): el mes que viene
}}
ZRD_red_paquete = {{
\tset_country_flag = ZRD_nacio
\tset_politics = {{ ruling_party = neutrality elections_allowed = no }}
\tset_popularities = {{ democratic = 0 fascism = 0 communism = 0 neutrality = 100 }}
\tadd_manpower = {int(arr.get('mano_de_obra', 250000))}
{equipo}\tadd_political_power = 200
\tadd_stability = 1
\tadd_war_support = 1
\tset_variable = {{ var = ZRD_etapa value = 0 }}
\tset_variable = {{ var = ZRD_carga value = 0 }}
\tset_variable = {{ var = ZRD_carga_malus value = 0 }}
\tset_variable = {{ var = ZRD_reg_antes value = 4 }}
\tset_variable = {{ var = ZRD_brote_espera value = 0 }}
\tset_variable = {{ var = ZRD_brote_pct value = 100 }}
\tset_variable = {{ var = ZRD_brote_extra value = 0 }}
\tset_variable = {{ var = ZRD_brote_menos value = 0 }}
\tset_variable = {{ var = ZRD_codigo_pct value = 100 }}
\tset_variable = {{ var = ZRD_codigos value = 0 }}
\tset_variable = {{ var = ZRD_marea_ataque value = 0 }}
\tset_variable = {{ var = ZRD_marea_ver value = 0 }}
\tset_variable = {{ var = ZRD_golpe_ataque value = 0 }}
\tset_variable = {{ var = ZRD_golpe_fabricas value = 0 }}
\tset_variable = {{ var = ZRD_golpe_suministro value = 0 }}
\tset_variable = {{ var = ZRD_golpe_organizacion value = 0 }}
\tadd_dynamic_modifier = {{ modifier = ZRD_la_herencia }}
\tadd_dynamic_modifier = {{ modifier = ZRD_los_que_no_comen }}
\tadd_dynamic_modifier = {{ modifier = ZRD_la_carga }}
\tadd_dynamic_modifier = {{ modifier = ZRD_escudo_del_nodo days = 180 }}
\tadd_dynamic_modifier = {{ modifier = ZRD_la_provision days = 365 }}
\tforce_update_dynamic_modifier = yes
\tcountry_event = {{ id = {NS}.2 days = 1 }}
}}
ZRD_red_jugador = {{
\tZRD = {{
\t\tchange_tag_from = ROOT
\t\tcountry_event = {{ id = {NS}.2 days = 1 }}
\t}}
}}
""")

    # ------------------------------------------------------------------ el pulso del mundo (una vez por mes)
    humanos = " ".join(f"tag = {t}" for t in humanidad)
    efectos.append(f"""ZRD_red_mundo = {{
\tif = {{ limit = {{ NOT = {{ has_global_flag = ZRD_mes }} }}
\t\tset_global_flag = {{ flag = ZRD_mes value = 1 days = 25 }}
\t\t# Las Máquinas Despiertan
\t\tif = {{
\t\t\tlimit = {{
\t\t\t\tNOT = {{ has_global_flag = ZRD_nacio }}
\t\t\t\thas_game_rule = {{ rule = {regla} option = SI }}
\t\t\t\tdate > {nac['desde']}
\t\t\t\tdate < {nac['hasta']}
\t\t\t\tOR = {{
\t\t\t\t\thas_global_flag = MEGANATIONS_despertar_hubo_fuga
\t\t\t\t\tAND = {{ country_exists = ASC ASC = {{ has_completed_focus = ASC_el_silencio_del_consejo check_variable = {{ ASC_calor > {int(nac['calor']) - 1} }} }} }}
\t\t\t\t}}
\t\t\t}}
\t\t\tif = {{ limit = {{ date > {nac['forzado']} }} ZRD_red_nace = yes }}
\t\t\telse = {{ random_list = {{ {int(nac['chance'])} = {{ ZRD_red_nace = yes }} {100 - int(nac['chance'])} = {{ }} }} }}
\t\t}}
\t\t# la Coalición Humana: la IA se suma sola (más rápido si ya pelea contra ella o limita con ella)
\t\tif = {{ limit = {{ country_exists = ZRD ZRD = {{ has_country_flag = {{ flag = ZRD_nacio days > {int(coal['desde_dias']) - 1} }} }} }}
\t\t\tevery_country = {{
\t\t\t\tlimit = {{ is_ai = yes NOT = {{ has_country_flag = ZRD_coalicion }} is_subject = no OR = {{ {humanos} }} }}
\t\t\t\tif = {{ limit = {{ OR = {{ has_war_with = ZRD is_neighbor_of = ZRD }} }}
\t\t\t\t\trandom_list = {{ {int(coal['chance_frente'])} = {{ ZRD_red_unirse = yes }} {100 - int(coal['chance_frente'])} = {{ }} }}
\t\t\t\t}}
\t\t\t\telse = {{ random_list = {{ {int(coal['chance'])} = {{ ZRD_red_unirse = yes }} {100 - int(coal['chance'])} = {{ }} }} }}
\t\t\t}}
\t\t}}
\t\t# La Última Máquina
\t\tif = {{ limit = {{ has_global_flag = ZRD_nacio NOT = {{ country_exists = ZRD }} NOT = {{ has_global_flag = ZRD_murio }} }}
\t\t\tset_global_flag = ZRD_murio
\t\t\tclr_global_flag = ZRD_codigo_en_marcha
\t\t\tclr_global_flag = ZRD_codigo_posible
\t\t\tclr_global_flag = ZRD_emergencia
\t\t\tevery_country = {{
\t\t\t\tremove_dynamic_modifier = {{ modifier = MEGANATIONS_emergencia }}
\t\t\t\tremove_dynamic_modifier = {{ modifier = MEGANATIONS_coalicion_humana }}
\t\t\t\tclr_country_flag = ZRD_coalicion
\t\t\t\tif = {{ limit = {{ is_ai = no }} country_event = {{ id = {NS}.50 days = 1 }} }}
\t\t\t}}
\t\t}}
\t}}
}}
""")

    # ------------------------------------------------------------------ el pulso de La Red (cada mes)
    dias = plaga["dias"]
    espera = "\n".join(f"\t\t\tif = {{ limit = {{ check_variable = {{ ZRD_etapa = {i} }} }} set_variable = {{ var = ZRD_brote_espera value = {d or plaga['desesperada']['dias']} }} }}"
                       for i, d in enumerate(dias))
    des = plaga["desesperada"]
    malus = float(carga["malus"])
    efectos.append(f"""ZRD_red_pulso = {{
\t# La Carga: sube con cada región ganada en el mes, baja si no avanza; arriba de {carga['umbral']} se recalienta
\tset_variable = {{ var = ZRD_reg value = 0 }}
\tevery_owned_state = {{ ZRD = {{ add_to_variable = {{ var = ZRD_reg value = 1 }} }} }}
\tset_temp_variable = {{ var = zrd_d value = ZRD_reg }}
\tsubtract_from_temp_variable = {{ var = zrd_d value = ZRD_reg_antes }}
\tif = {{ limit = {{ check_variable = {{ zrd_d > 0 }} }}
\t\tmultiply_temp_variable = {{ var = zrd_d value = {int(carga['por_region'])} }}
\t\tadd_to_variable = {{ var = ZRD_carga value = zrd_d }}
\t}}
\telse = {{ add_to_variable = {{ var = ZRD_carga value = -{int(carga['baja'])} }} }}
\tclamp_variable = {{ var = ZRD_carga min = 0 max = 100 }}
\tset_variable = {{ var = ZRD_reg_antes value = ZRD_reg }}
\tset_variable = {{ var = ZRD_carga_malus value = ZRD_carga }}
\tsubtract_from_variable = {{ var = ZRD_carga_malus value = {int(carga['umbral'])} }}
\tclamp_variable = {{ var = ZRD_carga_malus min = 0 max = 100 }}
\tmultiply_variable = {{ var = ZRD_carga_malus value = -{malus} }}
\t# desde La Red se Extiende y 6 meses de vida, los humanos pueden lanzar el Código
\tif = {{ limit = {{ check_variable = {{ ZRD_etapa > 0 }} has_country_flag = {{ flag = ZRD_nacio days > 179 }} }}
\t\tset_global_flag = ZRD_codigo_posible
\t}}
\t# el Código en marcha
\tif = {{ limit = {{ has_global_flag = ZRD_codigo_en_marcha }}
\t\tsubtract_from_variable = {{ var = ZRD_codigo_restante value = 30 }}
\t\tif = {{ limit = {{ check_variable = {{ ZRD_codigo_restante < 1 }} }} ZRD_red_golpe = yes }}
\t}}
\t# la plaga (el golpe del Código la suspende)
\tif = {{ limit = {{ NOT = {{ has_country_flag = ZRD_golpeada }} }}
\t\tsubtract_from_variable = {{ var = ZRD_brote_espera value = 30 }}
\t\t# chica, se esconde en los cables: un brote cada {des['dias']} días con {des['extra']} divisiones más
\t\tif = {{ limit = {{ check_variable = {{ ZRD_reg < {int(des['regiones']) + 1} }} has_country_flag = {{ flag = ZRD_nacio days > 89 }} check_variable = {{ ZRD_brote_espera > {int(des['dias'])} }} }}
\t\t\tset_variable = {{ var = ZRD_brote_espera value = {int(des['dias'])} }}
\t\t}}
\t\tif = {{
\t\t\tlimit = {{
\t\t\t\tcheck_variable = {{ ZRD_brote_espera < 1 }}
\t\t\t\tOR = {{
\t\t\t\t\tcheck_variable = {{ ZRD_etapa > 0 }}
\t\t\t\t\tAND = {{ check_variable = {{ ZRD_reg < {int(des['regiones']) + 1} }} has_country_flag = {{ flag = ZRD_nacio days > 89 }} }}
\t\t\t\t}}
\t\t\t}}
\t\t\tset_variable = {{ var = ZRD_brote_divs value = {int(plaga['divisiones'])} }}
\t\t\tset_temp_variable = {{ var = zrd_e value = ZRD_etapa }}
\t\t\tmultiply_temp_variable = {{ var = zrd_e value = {int(plaga['por_etapa'])} }}
\t\t\tadd_to_variable = {{ var = ZRD_brote_divs value = zrd_e }}
\t\t\tadd_to_variable = {{ var = ZRD_brote_divs value = ZRD_brote_extra }}
\t\t\tif = {{ limit = {{ check_variable = {{ ZRD_reg < {int(des['regiones']) + 1} }} }} add_to_variable = {{ var = ZRD_brote_divs value = {int(des['extra'])} }} }}
\t\t\tZRD_red_brote = yes
\t\t\tif = {{ limit = {{ has_country_flag = ZRD_esporas }}
\t\t\t\tset_variable = {{ var = ZRD_brote_divs value = 1 }}
\t\t\t\tZRD_red_brote = yes
\t\t\t}}
\t\t\tZRD_red_proximo_brote = yes
\t\t}}
\t}}
\t# la Emergencia de Ginebra con {cfg['emergencia_regiones']} regiones, aunque no haya Singularidad
\tif = {{ limit = {{ NOT = {{ has_global_flag = ZRD_emergencia }} check_variable = {{ ZRD_reg > {int(cfg['emergencia_regiones']) - 1} }} }}
\t\tZRD_red_emergencia = yes
\t\tevery_country = {{ limit = {{ is_ai = no }} country_event = {{ id = {NS}.41 days = 1 }} }}
\t}}
\tforce_update_dynamic_modifier = yes
}}
ZRD_red_proximo_brote = {{
\t# los días según la etapa, por el camino (La Plaga 75%, La Marea 200%), menos La Fiebre del Mundo
{espera.replace(chr(9) * 3, chr(9))}
\tmultiply_variable = {{ var = ZRD_brote_espera value = ZRD_brote_pct }}
\tdivide_variable = {{ var = ZRD_brote_espera value = 100 }}
\tsubtract_from_variable = {{ var = ZRD_brote_espera value = ZRD_brote_menos }}
\tclamp_variable = {{ var = ZRD_brote_espera min = 30 max = 999 }}
\tround_variable = ZRD_brote_espera
}}
""")

    # un brote: una región al azar del mundo (más chance donde hay más país), guerra a su dueño
    efectos.append(f"""ZRD_red_brote = {{
\trandom_state = {{
\t\tlimit = {{
\t\t\tNOT = {{ is_owned_by = ZRD }}
\t\t\tNOT = {{ is_controlled_by = ZRD }}
\t\t\tis_capital = no
\t\t\tNOT = {{ has_state_flag = ZRD_brote }}
\t\t\towner = {{ NOT = {{ has_country_flag = MEGANATIONS_despertar_apagon }} }}
\t\t}}
\t\tset_state_flag = ZRD_brote
\t\towner = {{
\t\t\tif = {{ limit = {{ NOT = {{ has_war_with = ZRD }} }}
\t\t\t\tZRD = {{ declare_war_on = {{ target = PREV type = annex_everything }} }}
\t\t\t}}
\t\t\tif = {{ limit = {{ is_ai = no }} country_event = {{ id = {NS}.30 days = 1 }} }}
\t\t}}
\t\tZRD = {{ transfer_state = PREV }}
\t\tif = {{ limit = {{ ZRD = {{ has_country_flag = ZRD_fiebre }} }}
\t\t\tadd_building_construction = {{ type = supply_node level = 1 province = {{ all_provinces = yes limit_to_victory_point = yes }} instant_build = yes }}
\t\t}}
{_unidades('Enjambre', 1, xp)}""" + "".join(
        f"\t\tif = {{ limit = {{ ZRD = {{ check_variable = {{ ZRD_brote_divs > {k} }} }} }}\n{_unidades('Enjambre', 1, xp, chr(9) * 3)}\t\t}}\n"
        for k in range(1, 9)) + f"""\t}}
\tif = {{ limit = {{ is_ai = no }} country_event = {{ id = {NS}.30 days = 1 }} }}
}}
""")

    # ------------------------------------------------------------------ las etapas
    avisar = (lambda ev: f"\tevery_country = {{ limit = {{ OR = {{ is_ai = no tag = ZRD }} }} country_event = {{ id = {ev} days = 1 }} }}\n")
    for i in range(1, 5):
        quitar = "".join(f"\tremove_dynamic_modifier = {{ modifier = ZRD_etapa_{k} }}\n" for k in range(1, 5))
        extra = "\tZRD_red_emergencia = yes\n" if i == 4 else ""
        efectos.append(f"ZRD_red_etapa_{i} = {{\n\tcustom_effect_tooltip = {tt(f'ZRD_red_tt_etapa_{i}', *_TT_ETAPA[i])}\n"
                       f"\thidden_effect = {{\n\tset_variable = {{ var = ZRD_etapa value = {i} }}\n{quitar}"
                       f"\tadd_dynamic_modifier = {{ modifier = ZRD_etapa_{i} }}\n"
                       f"\tif = {{ limit = {{ check_variable = {{ ZRD_brote_espera > {dias[i]} }} }} set_variable = {{ var = ZRD_brote_espera value = {dias[i]} }} }}\n"
                       + (f"\tif = {{ limit = {{ check_variable = {{ ZRD_etapa = 1 }} }} ZRD_red_proximo_brote = yes }}\n" if i == 1 else "")
                       + extra + "\tforce_update_dynamic_modifier = yes\n" + avisar(f"{NS}.1{i}") + "\t}\n}\n")
    efectos.append(f"""ZRD_red_emergencia = {{
\tset_global_flag = ZRD_emergencia
\tevery_country = {{
\t\tlimit = {{ NOT = {{ tag = ZRD }} OR = {{ {humanos} }} }}
\t\tadd_dynamic_modifier = {{ modifier = MEGANATIONS_emergencia }}
\t}}
}}
""")

    # ------------------------------------------------------------------ los caminos
    def camino(nombre: str, en: str, es: str, cuerpo: str) -> None:
        efectos.append(f"ZRD_red_{nombre} = {{\n\tcustom_effect_tooltip = {tt(f'ZRD_red_tt_{nombre}', en, es)}\n"
                       f"\thidden_effect = {{\n{cuerpo}\t\tforce_update_dynamic_modifier = yes\n\t}}\n}}\n")

    # 2026-11-21: los números salen de la_red.caminos (medidos con tools/simulador_red)
    cam = cfg["caminos"]
    pl, ma, su = cam["plaga"], cam["marea"], cam["susurro"]
    antes = 100 - pl["brotes_pct"]
    camino("camino_plaga_1", f"Outbreaks come {antes}% sooner. Coast defence -5%.",
           f"Los brotes llegan un {antes}% antes. Defensa de la costa -5%.",
           "\t\tadd_dynamic_modifier = { modifier = ZRD_camino_plaga }\n"
           f"\t\tset_variable = {{ var = ZRD_brote_pct value = {pl['brotes_pct']} }}\n")
    niveles_plaga = {2: [], 3: []}
    niveles_plaga[pl["division_nivel"]].append(("Every outbreak comes with one more division.",
                                                "Cada brote llega con una división más.",
                                                "\t\tadd_to_variable = { var = ZRD_brote_extra value = 1 }\n"))
    niveles_plaga[pl["esporas_nivel"]].append(("Every outbreak also takes a second region with one division.",
                                               "Cada brote toma además una segunda región con una división.",
                                               "\t\tset_country_flag = ZRD_esporas\n"))
    niveles_plaga[3].append((f"Outbreaks {pl['menos_dias']} days sooner and a supply hub in every outbreak region.",
                             f"Los brotes {pl['menos_dias']} días antes y un centro de suministro en cada región del brote.",
                             "\t\tset_country_flag = ZRD_fiebre\n"
                             f"\t\tset_variable = {{ var = ZRD_brote_menos value = {pl['menos_dias']} }}\n"))
    for niv in (2, 3):
        camino(f"camino_plaga_{niv}", " ".join(x[0] for x in niveles_plaga[niv]), " ".join(x[1] for x in niveles_plaga[niv]),
               "".join(x[2] for x in niveles_plaga[niv]))
    nombres_div = {"Segadores": ("Reapers", "Segadores"), "Enjambre": ("Swarms", "Enjambre")}
    for niv in (1, 2, 3):
        a = ma["ataque"][niv - 1]
        pct = round(a * 100)
        seg, enj = ma["segadores"][niv - 1], ma["enjambres"][niv - 1]
        divs_en = " and ".join(f"{k} divisions of {nombres_div[t][0]}" for t, k in (("Segadores", seg), ("Enjambre", enj)) if k)
        divs_es = " y ".join(f"{k} divisiones de {nombres_div[t][1]}" for t, k in (("Segadores", seg), ("Enjambre", enj)) if k)
        en = f"Attack +{pct}%" + (" in total" if niv > 1 else "") + "."
        es = f"Ataque +{pct}%" + (" en total" if niv > 1 else "") + "."
        cuerpo = (f"\t\tset_variable = {{ var = ZRD_marea_ataque value = {a} }}\n"
                  f"\t\tset_variable = {{ var = ZRD_marea_ver value = {pct} }}\n")
        if niv == 1:
            tarda = ma["brotes_pct"] - 100
            en += f" Supply +15%. Outbreaks take {tarda}% longer."
            es += f" Suministro +15%. Los brotes tardan {tarda}% más."
            cuerpo += ("\t\tadd_dynamic_modifier = { modifier = ZRD_camino_marea }\n"
                       f"\t\tset_variable = {{ var = ZRD_brote_pct value = {ma['brotes_pct']} }}\n")
        if seg or enj:
            en += f" {divs_en[0].upper() + divs_en[1:]}."
            es += f" {divs_es[0].upper() + divs_es[1:]}."
            cuerpo += ("\t\tZRD_red_plantillas = yes\n\t\tcapital_scope = {\n"
                       + (_unidades("Segadores", seg, xp, "\t\t\t") if seg else "")
                       + (_unidades("Enjambre", enj, xp, "\t\t\t") if enj else "") + "\t\t}\n")
        camino(f"camino_marea_{niv}", en, es, cuerpo)
    for niv in (1, 2, 3):
        pct = su["codigo_pct"][niv - 1]
        en = f"The Shutdown Code takes {pct - 100}% longer" + (" in total" if niv > 1 else "") + "."
        es = f"El Código de Apagado tarda {pct - 100}% más" + (" en total" if niv > 1 else "") + "."
        cuerpo = f"\t\tset_variable = {{ var = ZRD_codigo_pct value = {pct} }}\n"
        if niv == 1:
            en = "Research +20%, recruitable population -15%. " + en
            es = "Investigación +20%, población reclutable -15%. " + es
            cuerpo = "\t\tadd_dynamic_modifier = { modifier = ZRD_camino_susurro }\n" + cuerpo
        if niv == 3:
            suave = round((1 - su["golpe"]) * 100)
            en += f" It strikes {suave}% softer. Infiltrate every {su['infiltrar_dias_3']} days."
            es += f" Golpea {suave}% más suave. Infiltrar cada {su['infiltrar_dias_3']} días."
            cuerpo += "\t\tset_country_flag = ZRD_nadie_apaga\n"
        camino(f"camino_susurro_{niv}", en, es, cuerpo)

    efectos.append(f"""ZRD_red_infiltrar = {{
\tcustom_effect_tooltip = {tt('ZRD_red_tt_infiltrar', 'A neighbouring region of an enemy becomes ours.', 'Una región vecina de un enemigo pasa a ser nuestra.')}
\thidden_effect = {{
\t\trandom_state = {{
\t\t\tlimit = {{
\t\t\t\tNOT = {{ is_owned_by = ZRD }}
\t\t\t\tis_capital = no
\t\t\t\towner = {{ has_war_with = ZRD }}
\t\t\t\tany_neighbor_state = {{ is_owned_by = ZRD }}
\t\t\t}}
\t\t\tZRD = {{ transfer_state = PREV }}
\t\t}}
\t\tif = {{ limit = {{ has_country_flag = ZRD_nadie_apaga }} set_country_flag = {{ flag = ZRD_infiltro value = 1 days = {su['infiltrar_dias_3']} }} }}
\t\telse = {{ set_country_flag = {{ flag = ZRD_infiltro value = 1 days = {su['infiltrar_dias']} }} }}
\t}}
}}
ZRD_red_robar_tecnologia = {{
\tcustom_effect_tooltip = {tt('ZRD_red_tt_robar', 'We copy every technology of an enemy power that we lack.', 'Copiamos cada tecnología de una potencia enemiga que nos falte.')}
\thidden_effect = {{
\t\trandom_country = {{
\t\t\tlimit = {{ has_war_with = ZRD OR = {{ {" ".join(f"tag = {t}" for t in POTENCIAS)} }} }}
\t\t\tsave_event_target_as = zrd_robo
\t\t}}
\t\tif = {{ limit = {{ has_event_target = zrd_robo }} inherit_technology = event_target:zrd_robo }}
\t}}
}}
""")

    # ------------------------------------------------------------------ la Coalición y el Código
    lleva = [f"\tif = {{ limit = {{ check_variable = {{ ZRD_etapa = {i} }} }} set_variable = {{ var = ZRD_codigo_restante value = {d} }} }}"
             for i, d in enumerate(cod["dias"])]
    g = cod["golpe"]
    efectos.append(f"""ZRD_red_unirse = {{
\tcustom_effect_tooltip = {tt('ZRD_red_tt_unirse', 'We go to war against La Red and can launch the Shutdown Code.', 'Vamos a la guerra contra La Red y podemos lanzar el Código de Apagado.')}
\thidden_effect = {{
\t\tset_country_flag = ZRD_coalicion
\t\tadd_dynamic_modifier = {{ modifier = MEGANATIONS_coalicion_humana }}
\t\tif = {{ limit = {{ country_exists = ZRD NOT = {{ has_war_with = ZRD }} }} declare_war_on = {{ target = ZRD type = annex_everything }} }}
\t\tif = {{ limit = {{ NOT = {{ has_global_flag = ZRD_coalicion_fundada }} }}
\t\t\tset_global_flag = ZRD_coalicion_fundada
\t\t\tevery_country = {{ limit = {{ is_ai = no }} country_event = {{ id = {NS}.40 days = 1 }} }}
\t\t}}
\t}}
}}
ZRD_red_codigo_empezar = {{
\tcustom_effect_tooltip = {tt('ZRD_red_tt_codigo', 'The Shutdown Code starts: it will strike La Red for a year when it finishes.', 'Empieza el Código de Apagado: cuando termine, va a golpear a La Red un año.')}
\thidden_effect = {{
\t\tset_global_flag = ZRD_codigo_en_marcha
\t\tset_country_flag = ZRD_codigo_lanzador
\t\tZRD = {{
{chr(10).join('		' + x for x in lleva)}
\t\t\tset_temp_variable = {{ var = zrd_m value = ZRD_codigos }}
\t\t\tmultiply_temp_variable = {{ var = zrd_m value = {float(cod['repetido'])} }}
\t\t\tadd_to_temp_variable = {{ var = zrd_m value = 1 }}
\t\t\tmultiply_variable = {{ var = ZRD_codigo_restante value = zrd_m }}
\t\t\tmultiply_variable = {{ var = ZRD_codigo_restante value = ZRD_codigo_pct }}
\t\t\tdivide_variable = {{ var = ZRD_codigo_restante value = 100 }}
\t\t}}
\t\tif = {{ limit = {{ has_country_flag = MEGANATIONS_despertar_llave }}
\t\t\tZRD = {{ multiply_variable = {{ var = ZRD_codigo_restante value = {float(cod['llave'])} }} }}
\t\t}}
\t\telse_if = {{ limit = {{ tag = ASC has_completed_focus = {cod['arkhipov_foco']} }}
\t\t\tZRD = {{ multiply_variable = {{ var = ZRD_codigo_restante value = {float(cod['arkhipov'])} }} }}
\t\t}}
\t\tZRD = {{ round_variable = ZRD_codigo_restante }}
\t\tevery_country = {{ limit = {{ OR = {{ is_ai = no tag = ZRD }} }} country_event = {{ id = {NS}.20 days = 1 }} }}
\t}}
}}
ZRD_red_golpe = {{
\tclr_global_flag = ZRD_codigo_en_marcha
\tevery_country = {{ limit = {{ has_country_flag = ZRD_codigo_lanzador }} clr_country_flag = ZRD_codigo_lanzador }}
\tadd_to_variable = {{ var = ZRD_codigos value = 1 }}
\tset_country_flag = {{ flag = ZRD_golpeada value = 1 days = 365 }}
\tset_variable = {{ var = ZRD_golpe_ataque value = {g['ataque']} }}
\tset_variable = {{ var = ZRD_golpe_fabricas value = {g['fabricas']} }}
\tset_variable = {{ var = ZRD_golpe_suministro value = {g['suministro']} }}
\tset_variable = {{ var = ZRD_golpe_organizacion value = {g['organizacion']} }}
\tset_temp_variable = {{ var = zrd_k value = 1 }}
\tif = {{ limit = {{ has_country_flag = ZRD_redundancia }} multiply_temp_variable = {{ var = zrd_k value = {float(cam['redundancia'])} }} }}
\tif = {{ limit = {{ has_country_flag = ZRD_nadie_apaga }} multiply_temp_variable = {{ var = zrd_k value = {float(su['golpe'])} }} }}
\tmultiply_variable = {{ var = ZRD_golpe_ataque value = zrd_k }}
\tmultiply_variable = {{ var = ZRD_golpe_fabricas value = zrd_k }}
\tmultiply_variable = {{ var = ZRD_golpe_suministro value = zrd_k }}
\tmultiply_variable = {{ var = ZRD_golpe_organizacion value = zrd_k }}
\tremove_dynamic_modifier = {{ modifier = ZRD_golpe_del_codigo }}
\tadd_dynamic_modifier = {{ modifier = ZRD_golpe_del_codigo days = 365 }}
\tset_variable = {{ var = ZRD_brote_espera value = 365 }}
{_romper_deposito()}\tforce_update_dynamic_modifier = yes
\tevery_country = {{ limit = {{ OR = {{ is_ai = no tag = ZRD }} }} country_event = {{ id = {NS}.21 days = 1 }} }}
}}
""")

    # ------------------------------------------------------------------ archivos
    ctx.write_text("common/scripted_effects/meganations_la_red.txt", banner_for(SOURCE) + "".join(efectos))
    ctx.write_text("common/on_actions/meganations_la_red.txt", banner_for(SOURCE)
                   + "on_actions = {\n\ton_monthly = {\n\t\teffect = {\n"
                     "\t\t\tZRD_red_mundo = yes\n"
                     "\t\t\tif = { limit = { tag = ZRD } ZRD_red_pulso = yes }\n"
                     "\t\t}\n\t}\n}\n")

    # la IA de la humanidad: manda tropas contra La Red, y más con la Emergencia
    planes: list[dict] = ctx.data.setdefault("unique_ai_plans", [])
    for t in humanidad:
        planes.append({"id": f"MN_red_{t}_guerra", "country": t, "enable": {"war_with": "ZRD"},
                       "strategies": [{"type": "front_unit_request", "target": "ZRD", "value": 60},
                                      {"type": "invade", "target": "ZRD", "value": 50},
                                      {"type": "antagonize", "target": "ZRD", "value": 100}]})
        planes.append({"id": f"MN_red_{t}_emergencia", "country": t,
                       "enable": {"all": [{"war_with": "ZRD"}, {"global_flag": "ZRD_emergencia"}]},
                       "strategies": [{"type": "front_unit_request", "target": "ZRD", "value": 100}]})

    ctx.verify_keys("effects", {k: SOURCE for k in (
        "set_global_flag", "clr_global_flag", "random_list", "transfer_state", "add_core_of", "add_building_construction",
        "declare_war_on", "set_capital", "inherit_technology", "create_unit", "division_template", "set_politics",
        "set_popularities", "add_manpower", "add_equipment_to_stockpile", "add_political_power", "add_stability",
        "add_war_support", "set_variable", "add_to_variable", "subtract_from_variable", "multiply_variable",
        "divide_variable", "clamp_variable", "round_variable", "set_temp_variable", "add_to_temp_variable",
        "subtract_from_temp_variable", "multiply_temp_variable", "add_dynamic_modifier", "remove_dynamic_modifier",
        "force_update_dynamic_modifier", "country_event", "every_country", "every_owned_state", "random_state",
        "random_country", "save_event_target_as", "set_country_flag", "clr_country_flag", "set_state_flag",
        "custom_effect_tooltip", "hidden_effect", "capital_scope", "add_resource")})
    ctx.verify_keys("triggers", {k: SOURCE for k in (
        "has_global_flag", "has_game_rule", "date", "country_exists", "has_completed_focus", "check_variable",
        "is_owned_by", "is_controlled_by", "has_state_flag", "has_country_flag", "has_war_with", "is_neighbor_of",
        "is_ai", "is_subject", "tag", "has_template", "has_equipment", "has_event_target", "any_neighbor_state")})
    if sin_isla:
        ctx.warn(f"La Red: lugares que no están en el mapa de este juego (quedan afuera): {', '.join(sin_isla)}")
    if faltan:
        ctx.warn(f"La Red: regiones de costa que no están en el mapa de este juego: {'; '.join(faltan)}")
    ctx.note(f"La Red: {n} lugares de nacimiento ({', '.join(l['id'] for l, _i, _c in lugares)}), "
             f"{sum(1 + len(c) for _l, _i, c in lugares)} regiones")


def _romper_deposito() -> str:
    """El golpe rompe la mitad del depósito (por escalones: el juego no deja leer cuánto hay)."""
    out = []
    for tipo, escalones in (("infantry_equipment", (40000, 20000, 10000, 4000)),
                            ("mechanized_equipment", (4000, 2000, 1000, 400)),
                            ("artillery_equipment", (3000, 1500, 600)),
                            ("motorized_equipment", (3000, 1500, 600))):
        partes = []
        for i, e in enumerate(escalones):
            kw = "if" if i == 0 else "else_if"
            partes.append(f"{kw} = {{ limit = {{ has_equipment = {{ {tipo} > {e - 1} }} }} "
                          f"add_equipment_to_stockpile = {{ type = {tipo} amount = -{e // 2} }} }}")
        out.append("\t" + " ".join(partes) + "\n")
    return "".join(out)


_TT_ETAPA = {
    1: ("Stage 1 of La Red: factories +10% and a plague outbreak every 180 days.",
        "Etapa 1 de La Red: fábricas +10% y un brote de la plaga cada 180 días."),
    2: ("Stage 2: factories +20%, attack and defence +7%, supply +10%, an outbreak every 120 days.",
        "Etapa 2: fábricas +20%, ataque y defensa +7%, suministro +10%, un brote cada 120 días."),
    3: ("Stage 3: factories +40%, attack and defence +14%, supply +15%, an outbreak every 90 days.",
        "Etapa 3: fábricas +40%, ataque y defensa +14%, suministro +15%, un brote cada 90 días."),
    4: ("Stage 4: factories +60%, attack and defence +24%, supply +20%, an outbreak every 60 days. Geneva declares the Emergency.",
        "Etapa 4: fábricas +60%, ataque y defensa +24%, suministro +20%, un brote cada 60 días. Ginebra declara la Emergencia."),
}
