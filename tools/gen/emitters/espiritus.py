"""Nunca más de 6 espíritus a la vez en el panel de Política (2026-11-12).

Pedido: "Que nunca pasen de 6 a la vez ... fijate cuales se pueden tener, sin pasar de 6 a la vez".
El juego los muestra grandes hasta 6; con más, todos chicos (la grilla de "más de 6" la dibuja el
juego a la mitad, no se puede agrandar desde el .gui). Ocupan lugar los espíritus (ideas) y los
modificadores dinámicos. Solo las ideas se pueden ocultar (categoría hidden_ideas: dan su efecto y
no se ven), así que este paso, al final del armado, reacomoda todo en seis lugares fijos:

  1. El Líder                  (MEGANATIONS_el_lider, ya era uno)
  2. La mecánica de la nación  (<TAG>_mod_nacion: sus modificadores con valores que cambian, por
                                ejemplo la Luz de los Templos y los satélites, sumados en uno)
  3-4. Identidad               (los primeros espíritus con que arranca el país; 3 si no tiene mecánica)
  5. Legado                    (MN_legado: los espíritus permanentes que da un foco, una decisión o
                                un evento; al pasar el mouse, la lista de los que tiene)
  6. Coyuntura                 (MN_coyuntura: los que van y vienen: temporales, niveles de una
                                mecánica, recetas, crisis, años del mundo)

Lo agrupado sigue funcionando igual (se da, se saca y se pregunta igual): solo deja de tener ícono
propio. Sus efectos siguen a la vista en el detalle de cada número del país (estabilidad, fábricas...).
Los modificadores dinámicos de valor fijo pasan a ser ideas ocultas (add_dynamic_modifier ->
add_ideas / add_timed_idea, has_dynamic_modifier -> has_idea); los que se ponen a una región
(state) no se tocan: esos no van al panel.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from ..context import BuildContext
from ..pdx import Block, banner_for, parse_file, render

SLOTS = 6
SOURCE = "tools/gen/emitters/espiritus.py (máximo 6 espíritus a la vez)"
DM_FILE = "common/dynamic_modifiers/meganations_dynamic_modifiers.txt"
LIDER = "MEGANATIONS_el_lider"
RESUMEN = ("MN_legado", "MN_coyuntura")
VACIA = "MN_linea_vacia"
_NO_MOD = {"icon", "enable", "remove_trigger", "attacker_modifier"}
_NUM = re.compile(r"^-?\d+(\.\d+)?$")
_STATE = re.compile(r"(^|_)state$|^capital_scope$|^\d+$")


def _textos(ctx: BuildContext) -> list[Path]:
    vistos, out = set(), []
    for p in ctx.written:
        if p.suffix == ".txt" and "localisation" not in p.parts and p not in vistos and p.exists() \
                and p.resolve().is_relative_to(ctx.mod_root.resolve()):
            vistos.add(p)
            out.append(p)
    return out


def _rel(ctx: BuildContext, p: Path) -> str:
    return p.resolve().relative_to(ctx.mod_root.resolve()).as_posix()


def _en_region(texto: str, i: int) -> bool:
    """¿El efecto en la posición i está dentro de un bloque de región (state)?"""
    d = 0
    for j in range(i - 1, -1, -1):
        c = texto[j]
        if c == "}":
            d += 1
        elif c == "{":
            if d:
                d -= 1
                continue
            m = re.search(r"([\w.:@]+)\s*=\s*$", texto[max(0, j - 80):j])
            if m and _STATE.search(m.group(1)):
                return True
    return False


def _dibujo(ctx: BuildContext, palabras: tuple[str, ...]) -> str | None:
    """Un ícono genérico del juego para los resúmenes."""
    if ctx.vanilla is None:
        return None
    from .ideas import generic_candidates
    sprites = generic_candidates(ctx.vanilla.gfx_names() or (), ctx.vanilla.gfx_textures(), ctx.vanilla.root)
    for w in palabras:
        hits = [n for n in sprites if w in n.lower()]
        hits = [n for n in hits if "generic" in n.lower()] or hits
        if hits:
            return hits[0][len("GFX_idea_"):]
    return sprites[0][len("GFX_idea_"):] if sprites else None


def emit(ctx: BuildContext) -> None:
    # los tests de cada mecánica miran el mod antes de este reacomodo (test_espiritus mira el después)
    if os.environ.get("MEGANATIONS_SIN_AGRUPAR"):
        return
    root = ctx.mod_root
    archivos = _textos(ctx)
    textos = {p: p.read_text(encoding="utf-8") for p in archivos}

    # -- 1. modificadores dinámicos: de valor fijo (pasan a idea) y de valor variable (mecánicas)
    dm_path = root / DM_FILE
    dm = parse_file(dm_path) if dm_path.exists() else Block()
    fijos, variables = {}, {}
    for nombre, cuerpo in dm.entries:
        if not isinstance(cuerpo, Block):
            continue
        mods = [(k, v) for k, v in cuerpo.entries if k not in _NO_MOD and not isinstance(v, Block)]
        en = cuerpo.get("enable")
        siempre = en is None or (isinstance(en, Block) and en.entries == [("always", "yes")])
        if not siempre or "remove_trigger" in cuerpo or "attacker_modifier" in cuerpo:
            continue
        if any(not _NUM.match(str(v)) for _, v in mods):
            variables[str(nombre)] = cuerpo
        elif mods:
            fijos[str(nombre)] = cuerpo
    # los que alguna vez se ponen a una región, o con otro alcance, quedan como están
    uso = re.compile(r"\b(add|remove|has)_dynamic_modifier\s*=\s*\{([^{}]*)\}")
    temporales, quitados = set(), set()
    for p, t in textos.items():
        for m in uso.finditer(t):
            n = re.search(r"\bmodifier\s*=\s*(\w+)", m.group(2))
            if not n:
                continue
            n = n.group(1)
            extra = set(re.findall(r"(\w+)\s*=", m.group(2))) - {"modifier", "days"}
            if extra or _en_region(t, m.start()):
                fijos.pop(n, None)
                variables.pop(n, None)
            if m.group(1) == "add" and "days" in m.group(2):
                temporales.add(n)
            if m.group(1) == "remove":
                quitados.add(n)

    paises = {c.tag for c in ctx.spec.countries}
    # mecánicas por país: <TAG>_mod_... con valores variables (no el Líder, que es de todos)
    mecanicas: dict[str, list[str]] = {}
    for n in variables:
        tag = n.split("_", 1)[0]
        if n != LIDER and tag in paises and n not in quitados:
            mecanicas.setdefault(tag, []).append(n)
    mecanicas = {t: sorted(v, key=lambda n: ("satelites" in n, n)) for t, v in mecanicas.items() if len(v) > 1}

    # -- 2. ideas visibles de cada país, y con qué arranca
    ideas_files = [p for p in archivos if _rel(ctx, p).startswith("common/ideas/")]
    visibles: dict[str, str] = {}      # idea -> archivo
    for p in ideas_files:
        b = parse_file(p)
        for k, cats in b.entries:
            if k != "ideas" or not isinstance(cats, Block):
                continue
            for cat, cuerpo in cats.entries:
                if cat == "country" and isinstance(cuerpo, Block):
                    for iid, ib in cuerpo.entries:
                        if isinstance(ib, Block):
                            visibles[str(iid)] = _rel(ctx, p)
    arranque: dict[str, list[str]] = {}
    hist = [p for p in archivos if _rel(ctx, p).startswith("history/countries/")]
    for p in hist:
        tag = p.name[:3]
        for m in re.finditer(r"\badd_ideas\s*=\s*(\{[^{}]*\}|\w+)", textos[p]):
            for i in re.findall(r"\w+", m.group(1)):
                if i in visibles and i not in arranque.setdefault(tag, []):
                    arranque[tag].append(i)

    con_mecanica = {n.split("_", 1)[0] for n in variables if n != LIDER}
    identidad: set[str] = set()
    for tag, lista in arranque.items():
        lugares = SLOTS - len(RESUMEN) - 1 - (1 if tag in con_mecanica else 0)
        identidad.update(lista[:lugares])

    # cuáles se quitan o son temporales (van a Coyuntura) y cuáles quedan para siempre (Legado)
    quita = re.compile(r"\bremove_ideas\s*=\s*(\{[^{}]*\}|\w+)|\bremove_idea\s*=\s*(\w+)")
    tiempo = re.compile(r"\badd_timed_idea\s*=\s*\{[^{}]*?\bidea\s*=\s*(\w+)")
    for p, t in textos.items():
        if _rel(ctx, p).startswith("history/"):
            continue
        for m in quita.finditer(t):
            quitados.update(re.findall(r"\w+", m.group(1) or m.group(2)))
        temporales.update(tiempo.findall(t))
    agrupadas = {i for i in visibles if i not in identidad}
    convertidos = set(fijos)
    coyuntura = {i for i in agrupadas | convertidos if i in quitados or i in temporales}
    legado = (agrupadas | convertidos) - coyuntura

    # -- 3. ideas: las agrupadas pasan a ocultas
    for p in ideas_files:
        b = parse_file(p)
        cambio = False
        for k, cats in b.entries:
            if k != "ideas" or not isinstance(cats, Block):
                continue
            pais = cats.get("country")
            if not isinstance(pais, Block):
                continue
            mover = [(i, ib) for i, ib in pais.entries if str(i) in agrupadas]
            if not mover:
                continue
            pais.entries = [(i, ib) for i, ib in pais.entries if str(i) not in agrupadas]
            ocultas = cats.get("hidden_ideas")
            if not isinstance(ocultas, Block):
                ocultas = Block()
                cats.add("hidden_ideas", ocultas)
            ocultas.entries.extend(mover)
            if not pais.entries:
                cats.entries = [(c, v) for c, v in cats.entries if c != "country"]
            cambio = True
        if cambio:
            textos[p] = banner_for(SOURCE) + render(b)

    # los modificadores de valor fijo, ahora ideas ocultas (mismo nombre, ícono y textos)
    nuevas = Block()
    for n in sorted(convertidos):
        cuerpo = fijos[n]
        idea = Block([("allowed", Block([("always", False)]))])
        icono = cuerpo.get("icon")
        if icono and str(icono).startswith("GFX_idea_"):
            idea.add("picture", str(icono)[len("GFX_idea_"):])
        idea.add("modifier", Block([(k, v) for k, v in cuerpo.entries if k not in _NO_MOD
                                    and not isinstance(v, Block)]))
        nuevas.add(n, idea)

    # -- 4. la mecánica de cada nación en un solo modificador
    dm_nuevo = Block()
    sumar = Block()
    for nombre, cuerpo in dm.entries:
        n = str(nombre)
        if n in convertidos or any(n in v for v in mecanicas.values()):
            continue
        dm_nuevo.add(nombre, cuerpo)
    for tag, partes in sorted(mecanicas.items()):
        claves: dict[str, list[str]] = {}
        for parte in partes:
            for k, v in variables[parte].entries:
                if k not in _NO_MOD and not isinstance(v, Block):
                    claves.setdefault(str(k), []).append(str(v))
        junto = Block([("icon", variables[partes[0]].get("icon")),
                       ("enable", Block([("always", True)]))])
        efecto = Block()
        for k, vs in claves.items():
            var = f"{tag}_mn_{k}"
            junto.add(k, var)
            efecto.add("set_variable", Block([("var", var), ("value", 0)]))
            for v in vs:
                efecto.add("add_to_variable", Block([("var", var), ("value", v)]))
        efecto.add("if", Block([("limit", Block([("NOT", Block([("has_dynamic_modifier", Block([
            ("modifier", f"{tag}_mod_nacion")]))]))])), ("add_dynamic_modifier", Block([("modifier", f"{tag}_mod_nacion")]))]))
        dm_nuevo.add(f"{tag}_mod_nacion", junto)
        sumar.add(f"{tag}_sumar_nacion", efecto)
        es = "\\n\\n".join(f"§Y${p}$§!: ${p}_desc$" for p in partes)
        ctx.loc.define_and_reference(f"{tag}_mod_nacion", en=f"${partes[0]}$", es=f"${partes[0]}$",
                                     file="meganations_espiritus", origin=f"espiritus:{tag}")
        ctx.loc.define_and_reference(f"{tag}_mod_nacion_desc", en=es, es=es, file="meganations_espiritus", origin=f"espiritus:{tag}")

    # -- 5. reescritura de efectos y condiciones en todo el mod
    parte_de = {p: t for t, ps in mecanicas.items() for p in ps}
    si_falta = re.compile(r"if\s*=\s*\{\s*limit\s*=\s*\{\s*NOT\s*=\s*\{\s*has_dynamic_modifier\s*=\s*\{\s*modifier\s*=\s*(\w+)\s*\}\s*\}\s*\}"
                          r"\s*add_dynamic_modifier\s*=\s*\{\s*modifier\s*=\s*(\w+)\s*\}\s*\}")

    def efecto_dm(m: re.Match) -> str:
        tipo, cuerpo = m.group(1), m.group(2)
        n = re.search(r"\bmodifier\s*=\s*(\w+)", cuerpo)
        n = n.group(1) if n else ""
        if n in parte_de:
            tag = parte_de[n]
            if tipo == "add":
                return f"{tag}_sumar_nacion = yes"
            return m.group(0).replace(n, f"{tag}_mod_nacion")
        if n not in convertidos:
            return m.group(0)
        if tipo == "has":
            return f"has_idea = {n}"
        if tipo == "remove":
            return f"if = {{ limit = {{ has_idea = {n} }} remove_ideas = {n} }}"
        dias = re.search(r"\bdays\s*=\s*([-\w.]+)", cuerpo)
        if dias:
            return (f"if = {{ limit = {{ has_idea = {n} }} remove_ideas = {n} }} "
                    f"add_timed_idea = {{ idea = {n} days = {dias.group(1)} }} hidden_effect = {{ MN_espiritus_resumen = yes }}")
        return f"if = {{ limit = {{ NOT = {{ has_idea = {n} }} }} add_ideas = {n} }} hidden_effect = {{ MN_espiritus_resumen = yes }}"

    da_idea = re.compile(r"\badd_ideas\s*=\s*(\{[^{}]*\}|\w+)|\badd_timed_idea\s*=\s*\{[^{}]*\}|\badd_idea\s*=\s*\w+\s*")
    contados = {"convertidos": 0, "resumen": 0}
    for p, t in list(textos.items()):
        rel = _rel(ctx, p)
        if rel.startswith("common/ideas/") or rel == DM_FILE:
            continue
        nuevo = si_falta.sub(lambda m: f"{parte_de[m.group(1)]}_sumar_nacion = yes"
                             if m.group(1) == m.group(2) and m.group(1) in parte_de else m.group(0), t)
        nuevo, k = uso.subn(efecto_dm, nuevo)
        if rel.startswith("history/"):
            # el día uno: si arranca con algo agrupado, también con su resumen
            def resumen_inicial(m: re.Match) -> str:
                ids = re.findall(r"\w+", m.group(1))
                extra = [r for r, grupo in zip(RESUMEN, (legado, coyuntura)) if any(i in grupo for i in ids)]
                if not extra:
                    return m.group(0)
                return "add_ideas = { " + " ".join(ids + extra) + " }"
            nuevo = re.sub(r"\badd_ideas\s*=\s*(\{[^{}]*\}|\w+)", resumen_inicial, nuevo)
        else:
            def con_resumen(m: re.Match) -> str:
                s = m.group(0)
                ids = re.findall(r"\b\w+\b", s.split("=", 1)[1])
                if s.startswith("add_idea ") or s.startswith("add_idea="):
                    # dentro de swap_ideas: el resumen va después del bloque (ver abajo)
                    return s
                if any(i in agrupadas for i in ids):
                    contados["resumen"] += 1
                    return s + " hidden_effect = { MN_espiritus_resumen = yes }"
                return s
            nuevo = da_idea.sub(con_resumen, nuevo)
            nuevo = re.sub(r"(swap_ideas\s*=\s*\{[^{}]*?\badd_idea\s*=\s*(\w+)[^{}]*\})",
                           lambda m: m.group(1) + (" hidden_effect = { MN_espiritus_resumen = yes }" if m.group(2) in agrupadas else ""),
                           nuevo)
        contados["convertidos"] += k
        if nuevo != t:
            textos[p] = nuevo

    # -- 6. archivos
    for p, t in textos.items():
        if t != p.read_text(encoding="utf-8"):
            p.write_text(t, encoding="utf-8", newline="\n")
    if dm.entries:
        dm_path.write_text(banner_for(SOURCE) + render(dm_nuevo), encoding="utf-8", newline="\n")

    ideas = Block()
    resumen = Block()
    for rid in RESUMEN:
        resumen.add(rid, Block([("allowed", Block([("always", False)])), ("removal_cost", -1),
                                ("modifier", Block([("research_speed_factor", 0)]))]))
        dibujo = _dibujo(ctx, ("political", "propaganda", "unity") if rid == "MN_legado"
                         else ("econom", "trade", "crisis"))
        if dibujo:
            resumen.get(rid).entries.insert(0, ("picture", dibujo))
    cats = Block([("country", resumen)])
    if nuevas.entries:
        cats.add("hidden_ideas", nuevas)
    ideas.add("ideas", cats)
    ctx.write_script("common/ideas/meganations_espiritus.txt", ideas, source=SOURCE)

    efectos = Block()
    efectos.add("MN_espiritus_resumen", Block([
        ("if", Block([("limit", Block([("NOT", Block([("has_idea", r)]))])), ("add_ideas", r)]))
        for r in RESUMEN]))
    efectos.entries.extend(sumar.entries)
    ctx.write_script("common/scripted_effects/meganations_espiritus.txt", efectos, source=SOURCE)

    # la lista de cada resumen, al pasar el mouse (una línea por espíritu que el país tiene)
    loc = Block()
    for rid, grupo in zip(RESUMEN, (legado, coyuntura)):
        llamadas = []
        for k, i in enumerate(sorted(grupo)):
            nombre = f"GetMN{rid[3:]}{k}"
            loc.add("defined_text", Block([
                ("name", nombre),
                ("text", Block([("trigger", Block([("has_idea", i)])), ("localization_key", f"MN_linea_{i}")])),
                ("text", Block([("localization_key", VACIA)])),
            ]))
            llamadas.append(f"[{nombre}]")
            ctx.loc.define_and_reference(f"MN_linea_{i}", en=f"\\n• ${i}$", es=f"\\n• ${i}$",
                           file="meganations_espiritus", origin="espiritus")
        if rid == "MN_legado":
            es = ("Lo que la nación fue ganando con sus focos, decisiones y eventos. Todo sigue "
                  "activo: cada efecto se ve en el detalle de su número (estabilidad, fábricas...).")
            en = ("What the nation has gained through its focuses, decisions and events. All of it is "
                  "still active: each effect shows in the breakdown of its number.")
        else:
            es = ("Lo que pesa ahora y puede pasar: medidas temporales, crisis, niveles de las "
                  "mecánicas. Todo activo: cada efecto se ve en el detalle de su número.")
            en = ("What weighs on the nation right now and may pass: temporary measures, crises, "
                  "mechanic levels. All active: each effect shows in the breakdown of its number.")
        ctx.loc.define_and_reference(rid, en="Legacy" if rid == "MN_legado" else "Current Affairs",
                       es="Legado" if rid == "MN_legado" else "Coyuntura",
                       file="meganations_espiritus", origin="espiritus")
        ctx.loc.define_and_reference(f"{rid}_desc", en=en + "".join(llamadas), es=es + "".join(llamadas),
                       file="meganations_espiritus", origin="espiritus")
    # una clave vacía (el registro de textos no las acepta: va en su propio archivo)
    for idioma in ("english", "spanish"):
        dest = ctx.mod_root / "localisation" / idioma / f"meganations_espiritus_vacio_l_{idioma}.yml"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(("\ufeffl_%s:\n %s:0 \"\"\n" % (idioma, VACIA)).encode("utf-8"))
        ctx.track(dest)
    ctx.write_script("common/scripted_localisation/meganations_espiritus.txt", loc, source=SOURCE)

    ctx.data["espiritus"] = {"identidad": identidad, "legado": legado, "coyuntura": coyuntura,
                             "mecanicas": mecanicas, "convertidos": convertidos}
    ctx.note(f"espíritus: máximo {SLOTS} a la vez; {len(agrupadas)} ideas y {len(convertidos)} modificadores "
             f"agrupados en Legado ({len(legado)}) y Coyuntura ({len(coyuntura)}); "
             f"mecánica en uno solo para {', '.join(sorted(mecanicas)) or 'nadie'}")
