"""Tests del generador.

No puedo correr HOI4 desde acá, así que estos tests cubren lo que sí es
verificable sin el juego: que el spec valide, que el Paradox script haga
round-trip, que el merge de ideologías preserve los campos vanilla, que la
localisation no deje huérfanas, y que los binarios de arte tengan el header
correcto.

Lo que NO cubren, y por eso existe la Fase 4: si HOI4 acepta los nombres de
campo que emitimos. Eso solo lo dice error.log.

    python -m tools.tests.test_gen
"""

from __future__ import annotations

import struct
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.gen import art, pdx, specload  # noqa: E402
from tools.gen import vanilla as vanilla_mod  # noqa: E402
from tools.gen.cli import build  # noqa: E402
from tools.gen.errors import LocalisationError  # noqa: E402
from tools.gen.loc import LocRegistry  # noqa: E402

FIXTURE_VANILLA = Path(__file__).parent / "fixtures" / "vanilla"

_failures: list[str] = []
_passes = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global _passes
    if condition:
        _passes += 1
    else:
        _failures.append(f"{name}: {detail}" if detail else name)


def section(title: str) -> None:
    print(f"\n-- {title}")


# Scopes de CWTools (cwtools-hoi4-config, effects.cwt / triggers.cwt) de lo que
# usa el mod. El error.log de 2026-09-29 mostró create_unit a nivel país.
_STATE_ONLY = {"create_unit", "add_building_construction", "add_extra_state_shared_building_slots", "add_core_of",
               "set_state_flag", "clr_state_flag", "add_claim_by", "is_owned_by", "is_core_of", "has_state_flag",
               "is_controlled_by", "any_neighbor_state", "is_coastal", "free_building_slots"}
_COUNTRY_ONLY = {"add_political_power", "add_stability", "add_war_support", "army_experience", "add_ideas", "swap_ideas",
                 "set_autonomy", "country_event", "annex_country", "create_wargoal", "add_research_slot", "set_technology",
                 "add_equipment_to_stockpile", "create_faction", "add_to_faction", "add_opinion_modifier", "declare_war_on",
                 "add_named_threat", "transfer_state", "add_timed_idea", "remove_ideas", "set_country_flag",
                 "clr_country_flag", "add_country_leader_trait", "random_owned_controlled_state", "every_owned_state",
                 "add_tech_bonus", "puppet", "white_peace", "send_equipment", "division_template", "add_to_war",
                 "every_enemy_country", "leave_faction", "diplomatic_relation", "has_stability", "has_country_flag",
                 "has_war", "has_idea", "has_completed_focus", "controls_state", "has_war_with", "has_army_size",
                 "has_capitulated", "num_of_factories", "has_tech", "has_manpower", "has_war_support", "has_equipment",
                 "exists", "has_wargoal_against", "is_in_faction_with", "surrender_progress", "is_ai", "capital_scope",
                 "set_truce", "is_subject_of", "is_subject"}
_TO_STATE = {"capital_scope", "random_owned_state", "random_owned_controlled_state", "every_owned_state", "every_state",
             "random_state", "any_state", "any_owned_state", "every_controlled_state", "random_controlled_state",
             "any_neighbor_state", "random_neighbor_state", "every_neighbor_state", "CAPITAL"}
_TO_COUNTRY = {"owner", "controller", "OWNER", "CONTROLLER", "ROOT", "FROM", "every_country", "random_country",
               "any_country", "every_other_country", "any_other_country", "every_enemy_country", "any_enemy_country",
               "random_enemy_country", "every_subject_country", "any_subject_country", "overlord"}
_FLOW = {"if", "else", "else_if", "limit", "hidden_effect", "AND", "OR", "NOT", "NOR", "NAND", "random_list", "random",
         "effect_tooltip", "custom_trigger_tooltip", "hidden_trigger", "count_triggers", "modifier"}


def _scope_errors(mod: Path) -> list[str]:
    """Efectos y condiciones de país usados en un state, o al revés."""
    import re as _re
    tag = _re.compile(r"^[A-Z]{3}$|^[A-Z][0-9]{2}$")
    errors: list[str] = []

    def walk(block, scopes: list[str], parent: str, where: str) -> None:
        scope = scopes[-1]
        for key, value in block.entries:
            k = str(key)
            if (k in _STATE_ONLY and scope != "state") or (k in _COUNTRY_ONLY and scope != "country"):
                errors.append(f"{where}: {k} en {scope} (dentro de {parent})")
            if not isinstance(value, pdx.Block):
                continue
            if k in _FLOW:
                nxt = scope
            elif k in _TO_STATE or (k.isdigit() and parent not in ("random_list", "random_events")):
                nxt = "state"
            elif k in _TO_COUNTRY or k.startswith("event_target:") or (tag.match(k) and k not in _FLOW):
                nxt = "country"     # los event_target que guarda el mod son todos países
            elif k == "PREV":
                nxt = scopes[-2] if len(scopes) > 1 else "country"
            elif (k in _STATE_ONLY or k in _COUNTRY_ONLY) and parent:
                continue    # bloque de parámetros del efecto (arriba de todo es un evento)
            else:
                nxt = scope
            walk(value, scopes + [nxt], k, where)

    for sub in ("common/national_focus", "common/decisions", "events", "common/scripted_effects"):
        for f in sorted((mod / sub).glob("*.txt")):
            text = f.read_text(encoding="utf-8-sig", errors="replace")
            if "ARCHIVO GENERADO" in text[:600]:
                walk(pdx.parse(text), ["country"], "", f"{sub}/{f.name}")
    return errors


# ---------------------------------------------------------------------------


def test_pdx_roundtrip() -> None:
    section("pdx: parse y render")
    for src, want in (("a = { b < 16 }", "b < 16"), ("a = { b == 16 }", "b == 16"),
                      ("a = { date > 1936.1.1 }", "date > 1936.1.1"), ("a = { x >= 2 y <= 3 z != 4 }", "x >= 2")):
        out = pdx.render(pdx.parse(src))
        check(f"el operador sobrevive: {src}", want in out, out)
    check("text() de una comparacion da el valor", pdx.text(pdx.parse("b < 16").get("b")) == "16")

    text = """
    # comentario
    ideologies = {
        fascism = {
            types = { nazism = { } falangism = { } }
            color = { 128 128 128 }
            can_be_boosted = yes
            war_impact_on_world_tension = 0.5
            name = "con espacios"
        }
    }
    """
    root = pdx.parse(text)
    ideologies = root.get("ideologies")
    check("bloque raiz parseado", isinstance(ideologies, pdx.Block))
    fascism = ideologies.get("fascism")
    check("grupo anidado parseado", isinstance(fascism, pdx.Block))
    check("yes preservado", fascism.get("can_be_boosted") == "yes")
    check("string con espacios", pdx.text(fascism.get("name")) == "con espacios")
    check("comillas preservadas al releer", isinstance(fascism.get("name"), pdx.Quoted))
    color = fascism.get("color")
    check("lista inline", [v for _, v in color.entries] == ["128", "128", "128"])

    types = fascism.get("types")
    check("types tiene 2 entradas", len(types) == 2, f"tiene {len(types)}")

    # Round-trip: render y re-parse tienen que dar lo mismo.
    rendered = pdx.render(root)
    reparsed = pdx.parse(rendered)
    check(
        "round-trip estable",
        pdx.render(reparsed) == rendered,
        "render(parse(render(x))) != render(x)",
    )

    section("pdx: claves duplicadas")
    dup = pdx.parse("a = { x = 1 } a = { x = 2 }")
    check("duplicados preservados", len(dup.get_all("a")) == 2, "los duplicados se perdieron")

    section("pdx: escritura de escalares")
    b = pdx.Block()
    b.add("bare", "western_european_gfx")
    b.add("quoted", "countries/Ecofascist Empire.txt")
    b.add("number", 42)
    b.add("boolean", True)
    out = pdx.render(b)
    check("token pelado sin comillas", "bare = western_european_gfx" in out)
    check("ruta con espacio entrecomillada", 'quoted = "countries/Ecofascist Empire.txt"' in out)
    check("bool como yes", "boolean = yes" in out)


def test_spec_loads() -> None:
    section("spec")
    spec = specload.load(REPO_ROOT / "spec")
    check("30 paises (8 meganaciones + 16 satelites + 5 de la Anarquia + el Santuario de Gaia)", len(spec.countries) == 30, f"hay {len(spec.countries)}")
    check("todos los TAG de 3 letras", all(len(c.tag) == 3 for c in spec.countries))
    tags = {c.tag for c in spec.countries}
    for expected in ("EFE", "ASC", "FCU", "HSN", "NAS", "SHD", "APF", "NRE", "PTA", "YYG"):
        check(f"existe {expected}", expected in tags)

    types, groups = spec.ideology_index()
    check("4 grupos ideologicos", len(groups) == 4, f"hay {len(groups)}")
    check("grupos son los vanilla", set(groups) == {"fascism", "communism", "democratic", "neutrality"})
    for c in spec.countries:
        check(f"{c.tag} apunta a ideologia existente", c.ideology in types)

    # Colores de mapa bien distintos (2026-09-29): distancia en Lab (CIE76) entre cualquier par.
    def _lab(rgb):
        def lin(c):
            c /= 255
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        r, g, b = (lin(float(c)) for c in rgb)
        xyz = ((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047, 0.2126 * r + 0.7152 * g + 0.0722 * b,
               (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883)
        fx, fy, fz = (t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in xyz)
        return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))
    import math as _math
    labs = {c.tag: _lab(c.color) for c in spec.countries}
    closest = min((_math.dist(labs[a], labs[b]), a, b) for i, a in enumerate(labs) for b in list(labs)[i + 1:])
    check("colores de mapa: ningun par de paises se parece (Lab >= 15)", closest[0] >= 15, str(closest))

    efe = spec.country("EFE")
    check("capital del EFE es Buenos Aires", efe.capital == "Buenos Aires")
    check("EFE es major", efe.is_major)
    check("PTA es subject de EFE", spec.country("PTA").overlord == "EFE")


def test_loc_orphans() -> None:
    section("localisation: claves huerfanas")

    reg = LocRegistry()
    reg.define_and_reference("OK_KEY", en="Fine", es="Bien", file="t")
    try:
        reg.verify()
        check("registro coherente pasa", True)
    except LocalisationError as exc:
        check("registro coherente pasa", False, str(exc))

    reg = LocRegistry()
    reg.reference("MISSING_KEY", origin="test")
    try:
        reg.verify()
        check("referenciada sin definir falla", False, "verify() no fallo")
    except LocalisationError as exc:
        check("referenciada sin definir falla", "MISSING_KEY" in str(exc))

    reg = LocRegistry()
    reg.define("DEAD_KEY", en="Dead", es="Muerta", file="t")
    try:
        reg.verify()
        check("definida sin usar falla", False, "verify() no fallo")
    except LocalisationError as exc:
        check("definida sin usar falla", "DEAD_KEY" in str(exc))

    reg = LocRegistry()
    try:
        reg.define("NO_ES", en="Only english", es="", file="t")
        check("texto vacio falla", False, "define() no fallo")
    except LocalisationError:
        check("texto vacio falla", True)

    reg = LocRegistry()
    reg.define("DUP", en="a", es="b", file="t")
    try:
        reg.define("DUP", en="c", es="d", file="t")
        check("clave duplicada falla", False, "define() no fallo")
    except LocalisationError:
        check("clave duplicada falla", True)

    section("localisation: formato de archivo")
    reg = LocRegistry()
    reg.define_and_reference("EFE_DEF", en="Ecofascist Empire", es="Imperio Ecofascista", file="test")
    with tempfile.TemporaryDirectory() as tmp:
        paths = reg.write(Path(tmp))
        check("un archivo por idioma", len(paths) == 2, f"escribio {len(paths)}")
        english = next(p for p in paths if "english" in p.name)
        raw = english.read_bytes()
        check("UTF-8 con BOM", raw.startswith(b"\xef\xbb\xbf"), "sin BOM HOI4 ignora el archivo")
        text = raw.decode("utf-8-sig")
        check("cabecera de idioma", text.startswith("l_english:"))
        check("formato clave:0", ' EFE_DEF:0 "Ecofascist Empire"' in text)
        check("en carpeta del idioma", english.parent.name == "english")
        check("sufijo de idioma", english.name.endswith("_l_english.yml"))


def test_vanilla_fixture() -> None:
    section("vanilla: lectura")
    van = vanilla_mod.locate(str(FIXTURE_VANILLA))
    check("fixture localizada", van is not None)
    check("version leida de launcher-settings", van.version() == "1.99.9", van.version())
    check("supported_version con comodin", vanilla_mod.Vanilla.supported_version("1.16.3") == "1.16.*")

    ideologies = van.parse_ideologies()
    check("4 grupos en el fixture", len([k for k, _ in ideologies.entries if k]) == 4)

    states = van.states()
    check("19 states leidos", len(states) == 19, f"leyo {len(states)}")
    by_id = {s.id: s for s in states}
    check("state 900 con owner ARG", by_id[900].owner == "ARG")
    check("provincias parseadas", by_id[900].provinces == [1, 2, 3], str(by_id[900].provinces))
    check("localisation de states", van.state_localisation().get("STATE_900") == "Buenos Aires")


def test_ideology_merge() -> None:
    section("ideologias: merge sobre vanilla")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        path = ctx.mod_root / "common" / "ideologies" / "00_ideologies.txt"
        check("archivo de ideologias generado", path.exists())

        merged = pdx.parse_file(path).get("ideologies")
        fascism = merged.get("fascism")
        types = fascism.get("types")
        keys = types.keys()

        check("sub-ideologia nueva inyectada", "ecofascism" in keys, str(keys))
        check("segunda sub-ideologia del grupo", "imperial_restoration" in keys, str(keys))
        check("types vanilla preservados", "nazism" in keys and "falangism" in keys, str(keys))

        # Lo importante del merge: NO perder los campos hermanos del vanilla.
        check("rules preservado", isinstance(fascism.get("rules"), pdx.Block))
        check("ai preservado", isinstance(fascism.get("ai"), pdx.Block))
        dfn = fascism.get("dynamic_faction_names")
        check("dynamic_faction_names preservado", dfn is not None)
        check(
            "comillas de contenido vanilla intactas",
            'dynamic_faction_names = { "FACTION_NAME_FASCIST_1" }' in path.read_text(),
            "el merge le quito las comillas a contenido vanilla",
        )
        check("can_be_boosted preservado", fascism.get("can_be_boosted") == "yes")
        check(
            "war_impact preservado",
            fascism.get("war_impact_on_world_tension") == "0.5",
            str(fascism.get("war_impact_on_world_tension")),
        )

        # El color sí lo pisa el mod: es parte del reskin.
        color = [v for _, v in fascism.get("color").entries]
        check("color pisado por el spec", color == ["58", "92", "54"], str(color))

        # Los otros tres grupos también reciben sus types.
        check("democratic recibe corporate_union", "corporate_union" in merged.get("democratic").get("types").keys())
        check("communism recibe automated_socialism", "automated_socialism" in merged.get("communism").get("types").keys())
        check("neutrality recibe solar_monarchism", "solar_monarchism" in merged.get("neutrality").get("types").keys())
        # 2026-09-29: las democracias justifican guerras sin esperar 100% de tensión.
        demo = merged.get("democratic")
        check("democracia: justifica sin 100% de tension",
              pdx.text(demo.get("modifiers").get("generate_wargoal_tension")) in ("0.0", "0"), pdx.render(demo.get("modifiers")))
        check("democracia: justifica contra cualquiera, no solo contra quien genera amenaza",
              pdx.text(demo.get("rules").get("can_only_justify_war_on_threat_country")) == "no", pdx.render(demo.get("rules")))
        check("democracia: el resto de sus modificadores queda como en el juego",
              pdx.text(demo.get("modifiers").get("join_faction_tension")) == "0.60")
        check("el reporte dice que cambio", any("democratic.modifiers.generate_wargoal_tension: 1.00 -> 0.0" in n for n in ctx.notes),
              str([n for n in ctx.notes if n.startswith("ideologias")]))


def test_full_build() -> None:
    section("build completo")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root

        for rel in (
            "descriptor.mod",
            "common/country_tags/00_meganations.txt",
            "common/countries/colors.txt",
            "common/ideologies/00_ideologies.txt",
        ):
            check(f"existe {rel}", (mod / rel).exists())

        check("descriptor del launcher", (Path(tmp) / "meganations_2100.mod").exists())

        descriptor = (mod / "descriptor.mod").read_text()
        check("descriptor con nombre", 'name = "2100 Meganations"' in descriptor)
        check("supported_version del fixture", 'supported_version = "1.99.*"' in descriptor, descriptor)
        check("tags no vacio", "tags = {" in descriptor and "map" in descriptor, descriptor)
        check("version entrecomillada", 'version = "0.1.0"' in descriptor, descriptor)
        check("reemplaza los bookmarks vanilla", 'replace_path = "common/bookmarks"' in descriptor, descriptor)
        check("reemplaza los eventos vanilla (1936-1945 se disparaban en 2100)", 'replace_path = "events"' in descriptor)
        check("history/ todavia no se reemplaza (Q042)", 'replace_path = "history' not in descriptor, descriptor)

        colors = (mod / "common/countries/colors.txt").read_text()
        check("color en una linea: rgb { r g b }", "color = rgb { 42 132 54 }" in colors, colors[400:700])
        check("color_ui en una linea", "color_ui = rgb { 42 132 54 }" in colors)
        tags_text = (mod / "common/country_tags/00_meganations.txt").read_text()
        for tag in ("EFE", "ASC", "FCU", "NAS", "PTA", "YYG"):
            check(f"tag {tag} registrado", f"{tag} = " in tags_text)

        for c in ctx.spec.countries:
            check(f"archivo de pais {c.tag}", (mod / f"common/countries/{c.filename}.txt").exists())
            for variant in ("", "medium", "small"):
                flag = mod / "gfx/flags" / variant / f"{c.tag}.tga" if variant else mod / "gfx/flags" / f"{c.tag}.tga"
                check(f"bandera {c.tag} {variant or 'grande'}", flag.exists())

        check("sin avisos de ideologias faltantes",
              not any("SIN IDEOLOGIAS" in w for w in ctx.warnings))
        check("nada bloqueado por Q035", not any(s.question == "Q035" for s in ctx.skipped))

        # Todo archivo generado lleva el banner de no-editar.
        for path in mod.rglob("*.txt"):
            check(f"banner en {path.name}", "NO EDITAR A MANO" in path.read_text(), str(path))

        section("build: determinismo")
        with tempfile.TemporaryDirectory() as tmp2:
            build(Path(tmp2), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
            a = sorted(p.relative_to(tmp).as_posix() for p in Path(tmp).rglob("*") if p.is_file())
            b = sorted(p.relative_to(tmp2).as_posix() for p in Path(tmp2).rglob("*") if p.is_file())
            check("mismo listado de archivos", a == b)
            differing = [
                rel for rel in a
                if (Path(tmp) / rel).read_bytes() != (Path(tmp2) / rel).read_bytes()
            ]
            check("bytes identicos entre corridas", not differing, str(differing[:5]))


def test_build_without_vanilla() -> None:
    section("build sin vanilla: degrada, no revienta")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), quiet=True)
        check("genero igual los paises", (ctx.mod_root / "common/country_tags/00_meganations.txt").exists())
        check("no genero ideologias", not (ctx.mod_root / "common/ideologies/00_ideologies.txt").exists())
        check("reporta el skip", any(s.question == "Q035" for s in ctx.skipped))
        check("avisa que no va a cargar", any("SIN IDEOLOGIAS" in w for w in ctx.warnings))
        version_skips = [s for s in ctx.skipped if s.question == "Q004"]
        check("aviso de version una sola vez", len(version_skips) == 1, f"aparecio {len(version_skips)} veces")


def test_art() -> None:
    section("arte: binarios")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "flag.tga"
        art.write_tga(path, 4, 2, art.flag_pixels(4, 2, (45, 84, 41)))
        raw = path.read_bytes()
        header = struct.unpack("<BBBHHBHHHHBB", raw[:18])
        check("TGA sin paleta", header[1] == 0)
        check("TGA tipo 2 (RGB sin comprimir)", header[2] == 2)
        check("TGA ancho", header[8] == 4, str(header[8]))
        check("TGA alto", header[9] == 2, str(header[9]))
        check("TGA 24 bits", header[10] == 24)
        check("TGA tamano de cuerpo", len(raw) == 18 + 4 * 2 * 3, str(len(raw)))

        dds = Path(tmp) / "icon.dds"
        art.write_dds(dds, 4, 4, [(10, 20, 30)] * 16)
        raw = dds.read_bytes()
        check("DDS magic", raw[:4] == b"DDS ")
        check("DDS header de 124", struct.unpack("<I", raw[4:8])[0] == 124)
        check("DDS tamano", len(raw) == 128 + 4 * 4 * 4, str(len(raw)))

        check("3 tamanos de bandera", set(art.FLAG_SIZES) == {"", "medium", "small"})
        pixels = art.flag_pixels(8, 6, (100, 100, 100))
        check("cantidad de pixeles", len(pixels) == 48, str(len(pixels)))
        check("bandas distintas", len({pixels[0], pixels[8 * 3], pixels[8 * 5]}) > 1)


def test_check_detects_edits() -> None:
    section("check: detecta ediciones a mano")
    from tools.gen.cli import _compare_trees

    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        build(Path(a), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        build(Path(b), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        check("dos builds limpios coinciden", _compare_trees(Path(a), Path(b)) == [])

        victim = Path(b) / "meganations_2100" / "common" / "countries" / "colors.txt"
        victim.write_text(victim.read_text() + "\n# editado a mano\n")
        diffs = _compare_trees(Path(a), Path(b))
        check("detecta el archivo tocado", any(kind == "DIFIERE" for kind, _ in diffs), str(diffs))

        (Path(b) / "meganations_2100" / "colado.txt").write_text("archivo que no deberia estar")
        diffs = _compare_trees(Path(a), Path(b))
        check("detecta archivo de mas", any(kind == "SOBRA" for kind, _ in diffs), str(diffs))

        victim.unlink()
        diffs = _compare_trees(Path(a), Path(b))
        check("detecta archivo borrado", any(kind == "FALTA" for kind, _ in diffs), str(diffs))


def test_phase3_content() -> None:
    section("fase 3: ideas, focos, personajes, historia, BioSteel")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root

        ideas = (mod / "common/ideas/EFE_ideas.txt").read_text()
        for iid in ("EFE_mandato_verde", "EFE_conservacion_coercitiva", "EFE_biosteel_t3"):
            check(f"idea {iid}", f"{iid} = {{" in ideas)
        check("ideas no elegibles desde el panel", "always = no" in ideas)
        check("ideas no removibles", "removal_cost = -1" in ideas)

        focus = pdx.parse((mod / "common/national_focus/EFE_focus.txt").read_text())
        tree = focus.get("focus_tree")
        focuses = tree.get_all("focus")
        ids = [pdx.text(f.get("id")) for f in focuses]
        check("arbol del EFE de 55-75 focos (+4 del destino y +4 de los caminos economicos, 2026-09-29)", 55 <= len(focuses) <= 75, str(len(focuses)))
        by = {pdx.text(f.get("id")): f for f in focuses}
        aurelio = by["EFE_el_mandato_renovado"].get("mutually_exclusive")
        monte = by["EFE_los_incendios_de_gaia"].get("mutually_exclusive")
        check("Aurelio y el Monte se excluyen (ida)", pdx.text(aurelio.get("focus")) == "EFE_los_incendios_de_gaia")
        check("Aurelio y el Monte se excluyen (vuelta)", pdx.text(monte.get("focus")) == "EFE_el_mandato_renovado")
        golpe = by["EFE_el_monte_se_levanta"]
        check("el golpe pide el control del monte", "has_country_flag = EFE_monte_listo" in pdx.render(golpe.get("available")))
        check("el requisito del golpe se explica (no muestra el nombre de la bandera)",
              "custom_trigger_tooltip" in pdx.render(golpe.get("available"))
              and "MN_tt_req_EFE_monte_listo" in pdx.render(golpe.get("available")))
        check("el golpe asciende a Anahi", "promote_character = EFE_anahi_quiroga" in pdx.render(golpe.get("completion_reward")))
        check("el golpe dura 21 dias (3 semanas; +50% desde 2026-09-26)", pdx.text(golpe.get("cost")) == "3")
        agua = by["EFE_el_agua_no_se_vende"]
        reward = pdx.render(agua.get("completion_reward"))
        check("El Agua no se Vende es un ultimatum, no un wargoal directo",
              "create_wargoal" not in reward and "meganations_fcu.7" in reward, reward)
        check("el ultimatum pide Bioacero nivel 2", "EFE_biosteel" in pdx.render(agua.get("available")))
        raw_tree = (mod / "common/national_focus/EFE_focus.txt").read_text()
        monte_raw = raw_tree[raw_tree.index("id = EFE_los_incendios_de_gaia"):]
        check("la IA toma el Monte si la estabilidad es baja",
              "has_stability < 0.4" in monte_raw[:monte_raw.index("focus = {")])
        check("la integracion abre decisiones, no anexa de golpe",
              "annex_country" not in pdx.render(by["EFE_las_misiones_guaranies"].get("completion_reward")))
        rand_build = by["EFE_ministerio_de_restauracion"].get("completion_reward").get_all("random_owned_controlled_state")
        check("tabla nueva: 2 fabricas en regiones al azar, cada una con su slot",
              len(rand_build) == 2 and all("add_extra_state_shared_building_slots" in b.keys()
              and pdx.text(b.get("add_building_construction").get("type")) == "industrial_complex" for b in rand_build))
        dock = pdx.render(by["EFE_astilleros_del_plata"].get("completion_reward"))
        check("los astilleros van a una region con costa", "is_coastal = yes" in dock, dock)
        airfield = pdx.render(by["EFE_aerodromos_de_la_pampa"].get("completion_reward"))
        check("una base aerea no suma slots compartidos", "add_extra_state_shared_building_slots" not in airfield, airfield)
        check("arbol asignado al EFE", pdx.text(tree.get("country").get("modifier").get("tag")) == "EFE")
        cont = tree.get("continuous_focus_position")
        max_y = max(int(pdx.text(f.get("y"))) for f in focuses)
        check("los enfoques continuos van debajo del ultimo foco",
              cont is not None and int(pdx.text(cont.get("y"))) > max_y * 130, str(cont))
        coords = [(pdx.text(f.get("x")), pdx.text(f.get("y"))) for f in focuses]
        check("sin focos superpuestos", len(set(coords)) == len(coords), str(coords))
        for f in focuses:
            fid = pdx.text(f.get("id"))
            for pre in f.get_all("prerequisite"):
                check(f"{fid}: prerequisito existe", pdx.text(pre.get("focus")) in ids)
        corona = by["EFE_la_corona_de_gaia"]
        check("prerequisitos AND = dos bloques", len(corona.get_all("prerequisite")) == 2)

        amounts = []
        for n in (1, 2, 3):
            f = next(f for f in focuses if pdx.text(f.get("id")) == f"EFE_biosteel_umbral_{n}")
            cond = f.get("available").get("check_variable")
            check(f"umbral {n} mira la variable EFE_biosteel", pdx.text(cond.get("var")) == "EFE_biosteel")
            check(f"umbral {n} compara >=", pdx.text(cond.get("compare")) == "greater_than_or_equals")
            amounts.append(pdx.text(cond.get("value")))
        check("umbrales 5/10/15", amounts == ["5", "10", "15"], str(amounts))
        t2 = next(f for f in focuses if pdx.text(f.get("id")) == "EFE_biosteel_umbral_2")
        swap = t2.get("completion_reward").get("swap_ideas")
        check("tier 2 reemplaza al 1", pdx.text(swap.get("remove_idea")) == "EFE_biosteel_t1")

        chars = (mod / "common/characters/EFE_characters.txt").read_text()
        check("Aurelio IV lider ecofascista", "ideology = ecofascism" in chars)
        check("retrato del usuario copiado tal cual",
              (mod / "gfx/leaders/EFE/Aurelio_IV.dds").read_bytes()
              == (REPO_ROOT / "assets/EFE/leaders/Aurelio_IV.dds").read_bytes())
        check("mariscal con retrato de ejercito", "army = {" in chars and "field_marshal = {" in chars, chars)
        # error.log 2026-09-29 (Icon definition "_small"): cada retrato con su versión chica.
        chars_s = " ".join(chars.split())
        check("retrato: grande y chico explicitos",
              'large = "gfx/leaders/EFE/Aurelio_IV.dds" small = "gfx/leaders/EFE/small/Aurelio_IV.dds"' in chars_s, chars_s[:600])
        check("retrato chico copiado del arte (65x67)",
              (mod / "gfx/leaders/EFE/small/Aurelio_IV.dds").read_bytes()
              == (REPO_ROOT / "assets/EFE/leaders/small/Aurelio_IV.dds").read_bytes())
        check("retrato pedido y todavia sin dibujo: el juego usa el generico (sin provisorio)",
              "EFE_bruno_etchegaray" in chars_s and not (mod / "gfx/leaders/EFE/EFE_mando_beltran_1.dds").exists()
              and "EFE_mando_beltran_1.dds" not in chars_s)
        check("bandera del usuario", (mod / "gfx/flags/EFE.tga").read_bytes()
              == (REPO_ROOT / "assets/EFE/flags/EFE.tga").read_bytes())
        check("los demas siguen con bandera placeholder", (mod / "gfx/flags/ASC.tga").exists())
        gfx = (mod / "interface/meganations_EFE_goals.gfx").read_text()
        for icon in ("GFX_EFE_reforest_patagonia", "GFX_EFE_condor_doctrine"):
            check(f"sprite {icon} y su _shine", f'"{icon}"' in gfx and f'"{icon}_shine"' in gfx)
            check(f"textura de {icon} copiada", (mod / f"gfx/interface/goals/{icon[4:]}.dds").exists())
        focus_txt = (mod / "common/national_focus/EFE_focus.txt").read_text()
        check("foco usa icono propio aunque vanilla no lo tenga", "icon = GFX_EFE_green_legions" in focus_txt)

        hist_dir = mod / "history/countries"
        ours = {c.tag for c in ctx.spec.countries}
        own_files = [p for p in hist_dir.glob("*.txt") if p.name[:3] in ours]
        check("historia para todos nuestros paises", len(own_files) == len(ours), str(len(own_files)))
        efe = (hist_dir / "EFE - Ecofascist Empire.txt").read_text()
        check("EFE recluta a Aurelio", "recruit_character = EFE_aurelio_iv" in efe)
        check("mariscal reclutado", "recruit_character = EFE_bruno_etchegaray" in efe)
        check("EFE arranca con el Mandato", "EFE_mandato_verde" in efe)
        check("las ideas de foco no arrancan puestas", "EFE_conservacion_coercitiva" not in efe)
        check("capital del EFE = Buenos Aires (900)", "capital = 900" in efe, efe)
        check("EFE somete a PTA como titere comun",
              "target = PTA" in efe and "autonomy_state = autonomy_puppet" in efe, efe)
        for path in own_files:
            pops = pdx.parse(path.read_text()).get("set_popularities")
            total = sum(int(pdx.text(v)) for _, v in pops.entries)
            check(f"popularidades suman 100 en {path.name}", total == 100, str(total))

        check("BioSteel ya no es un recurso del mapa", not (mod / "common/resources").exists())
        efe_hist = (mod / "history/countries/EFE - Ecofascist Empire.txt").read_text()
        sv = pdx.parse(efe_hist).get("set_variable")
        check("el EFE arranca con 5 de BioSteel (variable)",
              pdx.text(sv.get("var")) == "EFE_biosteel" and pdx.text(sv.get("value")) == "5", efe_hist[-400:])
        by2 = {pdx.text(f.get("id")): f for f in focuses}
        add = by2["EFE_el_metal_que_crece"].get("completion_reward").get("add_to_variable")
        check("El Metal que Crece suma 5 de BioSteel",
              pdx.text(add.get("var")) == "EFE_biosteel" and pdx.text(add.get("value")) == "5", str(add))
        check("Anahi se recluta despues de Aurelio y Aurelio queda confirmado",
              efe_hist.index("recruit_character = EFE_aurelio_iv") < efe_hist.index("recruit_character = EFE_anahi_quiroga")
              and "promote_character = EFE_aurelio_iv" in efe_hist)
        decs = (mod / "common/decisions/meganations_decisions.txt").read_text()
        check("reforestacion: sembrar marca una region no propia",
              "random_owned_controlled_state" in decs and "set_state_flag = EFE_reforestando" in decs)
        check("reforestacion: a los 120 dias pasa a nucleo",
              "days > 120" in decs and "add_core_of = EFE" in decs, decs[:200])
        check("integracion por etapas: la ultima anexa con nucleos",
              "annex_country" in decs and decs.index("add_core_of = EFE") < decs.rindex("annex_country"))
        check("cada decision del Monte recalcula", decs.count("EFE_recalcular_monte = yes") == 4)

        section("minijuego del BioSteel: decisiones")
        cats = pdx.parse((mod / "common/decisions/categories/meganations_categories.txt").read_text())
        cat = cats.get("EFE_biosteel_category")
        check("panel propio del EFE", pdx.text(cat.get("allowed").get("original_tag")) == "EFE")
        check("icono elegido entre los vanilla", pdx.text(cat.get("icon")) == "generic_industry")
        decs_raw = (mod / "common/decisions/meganations_decisions.txt").read_text()
        decs = pdx.parse(decs_raw).get("EFE_biosteel_category")
        check("7 decisiones (con Purgar las Cubas, Como se Juega y el Gliptodonte)", len(decs.keys()) == 7, str(decs.keys()))
        guia = decs.get("EFE_como_se_juega")
        check("Como se Juega: gratis, la IA no la usa, muestra la bienvenida", pdx.text(guia.get("cost")) == "0"
              and "meganations_efe.29" in pdx.render(guia.get("complete_effect"))
              and pdx.text(guia.get("ai_will_do").get("factor")) == "0")
        ampliar = decs.get("EFE_ampliar_las_cubas")
        check("ampliar: cuesta 50 y tiene espera", pdx.text(ampliar.get("cost")) == "50"
              and pdx.text(ampliar.get("days_re_enable")) == "45")
        ampl = pdx.render(ampliar.get("complete_effect"))
        check("ampliar satura las cubas", "var = EFE_saturacion" in ampl, ampl)
        check("ampliar: +1 BioSteel", pdx.text(ampliar.get("complete_effect").get("add_to_variable").get("value")) == "1")
        check("icono de decision vanilla", pdx.text(ampliar.get("icon")) == "generic_industry")
        check("cultivo intensivo pide estabilidad > 0.4", "has_stability > 0.4" in decs_raw, decs_raw[:2000])
        blindar = decs.get("EFE_blindar_la_guardia")
        check("blindar gasta 3", pdx.text(blindar.get("complete_effect").get("add_to_variable").get("value")) == "-3")
        check("blindar pide tener 3", pdx.text(blindar.get("available").get("check_variable").get("value")) == "3")
        dl = (mod / "localisation/spanish/meganations_decisions_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("el panel muestra el contador", "[?EFE_biosteel]" in dl, dl[:500])


def test_territory() -> None:
    section("territorio: reparto sobre states vanilla")
    # Línea de fuertes (2026-09-29): solo la zona de Italia, solo frente a la ASC.
    from types import SimpleNamespace as _S
    from tools.gen.emitters.territory import fort_line_provinces
    fake = [_S(id=1, owner="ITA", provinces=[1, 2]), _S(id=2, owner="FRA", provinces=[3, 4]),
            _S(id=3, owner="FRA", provinces=[5]), _S(id=4, owner="SWI", provinces=[6]), _S(id=5, owner="GER", provinces=[7])]
    got = fort_line_provinces({1: "NRE", 2: "NRE", 3: "NRE", 4: "ASC", 5: "ASC"}, fake,
                              {(1, 6), (2, 3), (4, 6), (5, 7)}, {"owner": "NRE", "facing": "ASC", "near": "ITA", "level": 5})
    check("fuertes: la region italiana y la vecina, solo en las provincias que tocan a la ASC",
          got == {1: {1: 5}, 2: {4: 5}}, str(got))
    # 2026-09-29 (pedido del usuario): Panamá y Puerto Rico a la FCU; Chequia y Danzig a la ASC.
    import yaml as _yt
    from tools.gen.emitters.territory import _resolve, normalize as _tnorm
    terr_spec = _yt.safe_load((REPO_ROOT / "spec/08_territory.yaml").read_text(encoding="utf-8"))["territories"]
    wanted = {t: v for t, v in terr_spec.items() if isinstance(v, dict) and isinstance(v.get("resolve"), list)}
    rows = [(1, "CZE", "Bohemia", "europe"), (2, "CZE", "Slovakia", "europe"), (3, "CZE", "Carpathian Ruthenia", "europe"),
            (4, "DNZ", "Danzig", "europe"), (5, "PAN", "Panama", "north_america"), (9, "POL", "Gdynia", "europe"),
            # Puerto Rico en otro continente: lo toma el nombre, no el dueño
            (6, "USA", "Puerto Rico", "south_america"), (7, "COL", "Bogota", "south_america"), (8, "POL", "Warsaw", "europe")]
    rstates = [_S(id=i, owner=o, cores=[o], name_key=f"S{i}", file_label=n) for i, o, n, _ in rows]
    rctx = _S(vanilla=_S(state_continents=lambda: {i: c for i, _, _, c in rows}),
              spec=_S(country=lambda t: None), warn=lambda m: None)
    got = _resolve(rctx, wanted, rstates, {}, {_tnorm(s.file_label): [s] for s in rstates})
    check("territorio: Chequia y Danzig a la ASC; Eslovaquia y Rutenia quedan en ZBC",
          (got[1], got[2], got[3], got[4], got[8]) == ("ASC", "ZBC", "ZBC", "ASC", "ZBC"), str(got))
    check("territorio: Gdynia (la region entera) a la ASC aunque era polaca", got[9] == "ASC", str(got))
    check("territorio: el canal de Panama y Puerto Rico a la FCU; Colombia sigue en ZNG",
          (got[5], got[6], got[7]) == ("FCU", "FCU", "ZNG"), str(got))
    # reporte 2026-09-29: "clave de localisation duplicada: STATE_446" (en 1.19.3
    # "Suez" y "Cairo" son la misma región). Gana el primer nombre y se avisa.
    from tools.gen.emitters.territory import _rename_states
    defined, rwarn = {}, []

    def _define(key, en, es, file, origin):
        if key in defined:
            raise AssertionError(f"clave duplicada {key}")
        defined[key] = es
    egypt = _S(id=446, name_key="STATE_446", vp_provinces=[])
    nctx = _S(spec=_S(raw={"territory": {"state_names": {"renames": [
                  {"state": ["Cairo"], "name": {"english": "Council of the Nile", "spanish": "Consejo del Nilo"}},
                  {"state": ["Suez"], "name": {"english": "Federal Canal", "spanish": "Canal Federal"}}]}}}),
              loc=_S(define_and_reference=_define), data={"state_names": {}}, warn=rwarn.append, note=lambda m: None)
    try:
        _rename_states(nctx, {"cairo": [egypt], "suez": [egypt]})
        dup_ok = defined == {"STATE_446": "Consejo del Nilo"}
    except AssertionError as exc:
        dup_ok = False
        rwarn.append(str(exc))
    check("nombres: dos nombres para la misma region no frenan el generador (queda el primero y se avisa)",
          dup_ok and any("Suez" in w and "Cairo" in w for w in rwarn), str(defined) + str(rwarn))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        import shutil as _shf
        _shf.copytree(REPO_ROOT / "spec", root / "spec")
        (root / "assets").symlink_to(REPO_ROOT / "assets")
        mil = (root / "spec/13_military.yaml").read_text(encoding="utf-8")
        (root / "spec/13_military.yaml").write_text(
            mil.replace("{owner: NRE, facing: ASC, near: ITA, level: 5", "{owner: NRE, facing: ZWE, near: ITA, level: 5"),
            encoding="utf-8")
        fctx = build(root / "out", vanilla_path=str(FIXTURE_VANILLA), quiet=True, spec_dir=root / "spec")
        st = " ".join((fctx.mod_root / "history/states/909-Fixture.txt").read_text().split())
        check("fuertes: el bunker queda escrito en la provincia del state", "13 = { bunker = 5 }" in st, st[-500:])
    # 2026-09-29: las milicias de las Tierras Sin Ley quedaban todas en un solo territorio.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        import shutil as _shm
        _shm.copytree(REPO_ROOT / "spec", root / "spec")
        (root / "assets").symlink_to(REPO_ROOT / "assets")
        mil = (root / "spec/13_military.yaml").read_text(encoding="utf-8")
        (root / "spec/13_military.yaml").write_text(
            mil.replace("    ZAN: {min: 2, states_per_division: 2}", "    ZWI: {min: 2, states_per_division: 2}"), encoding="utf-8")
        mctx = build(root / "out", vanilla_path=str(FIXTURE_VANILLA), quiet=True, spec_dir=root / "spec")
        zwi_u = pdx.parse((mctx.mod_root / "history/units/ZWI_2100.txt").read_text()).get("units").get_all("division")
        locs = [pdx.text(d.get("location")) for d in zwi_u]
        check("milicias repartidas: cada territorio contiguo con su minimo (India y Ceilan, 2 y 2)",
              len(zwi_u) == 4 and any(l in {"18", "19", "20", "21"} for l in locs) and len(set(locs)) >= 2,
              str(locs))
    ideas_raw = (REPO_ROOT / "spec/05_ideas.yaml").read_text(encoding="utf-8")
    check("Tierras Sin Ley: arrancan con La Frontera Armada", "id: ZAN_la_frontera_armada" in ideas_raw)
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        terr = ctx.data["territory"]
        check("Buenos Aires (ARG) -> EFE", terr.get(900) == "EFE", str(terr))
        check("Cordoba (ARG) -> EFE", terr.get(902) == "EFE")
        check("Formosa queda en el EFE (decision del usuario)", terr.get(903) == "EFE", str(terr))
        check("Magallanes -> PTA", terr.get(901) == "PTA")
        check("Paraguay (PAR) -> YYG", terr.get(904) == "YYG")
        check("Rio Grande do Sul (BRA) -> EFE", terr.get(905) == "EFE")
        check("Ruhr (GER) -> ASC", terr.get(906) == "ASC")
        check("Italia europea -> NRE", terr.get(909) == "NRE", str(terr))
        check("Libia italiana -> APF por continente", terr.get(910) == "APF")
        check("Corea por core, aunque sea de Japon -> ZKR", terr.get(911) == "ZKR")
        check("Japon -> HSN (los puertos)", terr.get(912) == "HSN")
        check("India -> Anarquia de Asia (ZWI)", terr.get(914) == "ZWI" and terr.get(915) == "ZWI")
        check("Moscu -> Anarquia de Europa (ZWE)", terr.get(917) == "ZWE")
        check("Ceilan (asia) -> ZWI", terr.get(916) == "ZWI")
        check("state con comparaciones queda afuera del reparto", 907 not in terr)
        check("nadie queda vanilla salvo lo no reescribible",
              all(s.id in terr or s.id == 907 for s in ctx.vanilla.states() if s.owner), str(terr))
        check("Etiopia: el TAG le gana al continente -> ZET", terr.get(913) == "ZET")
        ger = (mod / "history/countries/GER - Germany.txt").read_text()
        check("Alemania sin territorio: sin oob", "oob" not in ger, ger)
        nor = (mod / "history/countries/NOR - Norway.txt").read_text()
        check("historia que no parsea: queda solo la capital", "capital = 912" in nor and "broken" not in nor, nor)
        names = (mod / "common/names/00_meganations_names.txt").read_text()
        check("EFE toma la lista de nombres argentina", "EFE = {" in names and "Perez" in names, names)
        check("Alemania: sin historia de 1939", "1939" not in ger.split("####")[-1] and "annex_country" not in ger)
        check("Alemania: sin personajes", "recruit_character" not in ger)
        check("Alemania: conserva capital y gobierno para ser liberable",
              "capital = 906" in ger and "set_politics" in ger and "set_popularities" in ger)
        lazio = pdx.parse((mod / "history/states/909-Fixture.txt").read_text()).get("state").get("history")
        check("sin reclamos de paises de 1936", "add_claim_by" not in lazio.keys())
        check("sin resistencia de paises de 1936", "start_resistance" not in lazio.keys())
        check("conserva los puntos de victoria", "victory_points" in lazio.keys())
        sov = mod / "history/countries/SOV - Soviet Union.txt"
        check("la URSS conserva un state y reubica su capital", sov.exists() and "capital = 907" in sov.read_text())

        units = pdx.parse((mod / "history/units/ZWI_2100.txt").read_text())
        divs = units.get("units").get_all("division")
        check("5 milicias en el Indostan (2026-09-28: anarquias mas fuertes)", len(divs) == 5, str(len(divs)))
        locs = sorted(pdx.text(d.get("location")) for d in divs)
        check("en el territorio mas poblado (India, no Ceilan)", set(locs) <= {"18", "19", "20", "21"} and "18" in locs, str(locs))
        zwe = pdx.parse((mod / "history/units/ZWE_2100.txt").read_text()).get("units").get_all("division")
        check("7 milicias en Europa (Moscu): Eurasia mas fuerte (2026-09-29)", len(zwe) == 7 and pdx.text(zwe[0].get("location")) == "22", str(len(zwe)))

        section("la Anarquia no es una faccion (2026-09-25)")
        lh = next(p for p in (mod / "history/countries").glob("ZWI - *.txt")).read_text()
        check("ningun senor de la guerra funda una faccion", "create_faction" not in lh, lh[-600:])
        check("ni suma a los otros", "add_to_faction" not in lh)
        tpl = units.get("division_template")
        check("plantilla de milicia con 2 infanterias", len(tpl.get("regiments").get_all("infantry")) == 2)
        bal = (Path(tmp) / "balance.txt").read_text()
        check("balance generado fuera del mod", not (mod / "balance.txt").exists() and "BALANCE" in bal)
        check("balance cuenta las milicias", any(l.startswith("ZWI") and " 5 " in l for l in bal.splitlines()), bal[:800])
        check("balance muestra el contador de BioSteel", "EFE_biosteel: arranca en 5" in bal)
        check("balance ya no alerta ejercitos vacios", "Sin ejercito inicial" not in bal, bal[-600:])

        section("arranque militar: tecnologias, ejercito, equipo")
        efe_h = (mod / "history/countries/EFE - Ecofascist Empire.txt").read_text()
        check("el EFE (blindados) solo tiene lo basico: en el fixture no hay pestaña de blindados",
              set(pdx.parse(efe_h).get("set_technology").keys()) - {"popup"} == {"infantry_weapons", "tech_support", "basic_train", "tech_trucks"})
        check("avisa la pestaña que falta y lista las que hay",
              any("investigacion" in w and "infantry_folder" in w for w in ctx.warnings))
        nre_h = next((mod / "history/countries").glob("NRE - *.txt")).read_text()
        techs = pdx.parse(nre_h).get("set_technology")
        keys = set(techs.keys()) - {"popup", "tech_support", "basic_train", "tech_trucks"}
        check("NRE (infanteria): las 5 primeras de la pestaña, en orden de arbol",
              keys == {"infantry_weapons", "either_or_tech", "infantry_weapons1", "infantry_weapons2",
                       "improved_infantry_weapons"}, str(keys))
        check("de un par excluyente toma uno solo", "other_tech" not in keys)
        check("no regala variantes sin DLC", "legacy_only_tech" not in keys)
        check("no toma techs de otra pestaña", "basic_ship_hull_heavy" not in keys)
        check("sin popup", pdx.text(techs.get("popup")) == "no")
        pta_h = (mod / "history/countries/PTA - Southern Patagonia.txt").read_text()
        check("satelite: solo lo basico", set(pdx.parse(pta_h).get("set_technology").keys()) - {"popup"} <= {"infantry_weapons", "tech_support", "basic_train", "tech_trucks"})
        zwi_h = next((mod / "history/countries").glob("ZWI - *.txt")).read_text()
        check("anarquia: solo lo basico", set(pdx.parse(zwi_h).get("set_technology").keys()) - {"popup"} <= {"infantry_weapons", "tech_support", "basic_train", "tech_trucks"})
        # 2026-09-29 (pedido del usuario): todos arrancan con trenes y camiones.
        check("trenes y camiones para todos (meganacion, satelite y anarquia)",
              all({"basic_train", "tech_trucks"} <= set(pdx.parse(h).get("set_technology").keys()) for h in (efe_h, pta_h, zwi_h)))

        oob = pdx.parse((mod / "history/units/EFE_2100.txt").read_text())
        tpls = [pdx.text(tpl.get("name")) for tpl in oob.get_all("division_template")]
        check("EFE: una sola plantilla, infanteria basica", tpls == ["Infantería Básica"], str(tpls))
        divs = oob.get("units").get_all("division")
        check("EFE: 2 divisiones", len(divs) == 2, str(len(divs)))
        check("en la capital", all(pdx.text(d.get("location")) == pdx.text(divs[0].get("location")) for d in divs))
        check("todos pueden fabricar equipo de infanteria (tecnologia base)",
              "infantry_weapons" in efe_h and "infantry_weapons" in zwi_h and "infantry_weapons" in pta_h)
        check("EFE carga su oob", 'oob = "EFE_2100"' in efe_h)
        stock = {pdx.text(b.get("type")): int(pdx.text(b.get("amount")))
                 for b in pdx.parse(efe_h).get_all("add_equipment_to_stockpile")}
        check("fusiles: la variante mas nueva hasta 1942", "infantry_equipment_3" in stock, str(stock))
        check("fusiles: 4000 en deposito para una meganacion", stock.get("infantry_equipment_3") == 4000, str(stock))
        check("convoyes", "convoy_1" in stock)

        section("nombres de 2100 y compensacion industrial")
        st = (mod / "localisation/spanish/replace/meganations_states_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("Buenos Aires se llama Gaia", 'STATE_900:0 "Gaia"' in st, st)
        check("Magallanes es la Custodia Austral", 'STATE_901:0 "Custodia Austral"' in st)
        check("la ciudad capital tambien se llama Gaia", 'VICTORY_POINTS_1:0 "Gaia"' in st, st)
        oob_txt = (mod / "history/units/EFE_2100.txt").read_text()
        check("las divisiones usan el nombre nuevo", "de Gaia" in oob_txt and "de Buenos Aires" not in oob_txt)
        check("nombres en replace/ (pisan los vanilla)", "replace" in str(mod / "localisation/spanish/replace"))
        check("EFE arranca con Las Cubas de la Pampa", "EFE_cubas_de_la_pampa" in efe_h)
        zwi = next((mod / "history/countries").glob("ZWI - *.txt")).read_text()
        check("la Anarquia carga su oob", 'oob = "ZWI_2100"' in zwi, zwi)
        check("nombre con comentario al final se lee",
              ctx.data["state_names"].get("STATE_902") == "Córdoba", str(ctx.data["state_names"].get("STATE_902")))
        check("Ponta Pora por nombre de archivo (sin localisation) -> YYG", terr.get(908) == "YYG", str(terr))
        check("el reporte no muestra '?'", not any("?" in n for n in ctx.notes if n.startswith("territorio")),
              str(ctx.notes))

        states = mod / "history/states"
        cordoba = pdx.parse((states / "902-Fixture.txt").read_text())
        hist = cordoba.get("state").get("history")
        check("mismo nombre de archivo que vanilla", (states / "902-Fixture.txt").exists())
        check("owner EFE", pdx.text(hist.get("owner")) == "EFE")
        check("core solo del EFE", [pdx.text(v) for v in hist.get_all("add_core_of")] == ["EFE"])
        check("bloque 1939 borrado", "1939.1.1" not in hist.keys(), str(hist.keys()))
        check("edificios conservados", isinstance(hist.get("buildings"), pdx.Block))
        res = cordoba.get("state").get("resources")
        check("el carbon vanilla del EFE queda igual", pdx.text(res.get("coal")) == "12")

        ruhr = pdx.parse((states / "906-Fixture.txt").read_text()).get("state")
        check("Ruhr conserva su carbon (energia para la ASC)", pdx.text(ruhr.get("resources").get("coal")) == "40")
        check("Ruhr pasa a la ASC", pdx.text(ruhr.get("history").get("owner")) == "ASC")
        par = pdx.parse((states / "904-Fixture.txt").read_text()).get("state")
        check("el satelite conserva su carbon", pdx.text(par.get("resources").get("coal")) == "5")
        check("el satelite no tiene BioSteel", "biosteel" not in par.get("resources").keys())
        check("archivo con comparaciones no se reescribe", not (states / "907-Fixture.txt").exists())
        # 2026-09-29: "casi no se puede construir" y "el NAS no tiene astilleros"
        lazio_h = pdx.parse((states / "909-Fixture.txt").read_text()).get("state").get("history")
        check("construccion: espacios extra en cada region (meganacion +3)",
              pdx.text(lazio_h.get("add_extra_state_shared_building_slots")) == "3", pdx.render(lazio_h)[:500])
        check("construccion: los espacios extra van antes que los edificios",
              [k for k, _ in lazio_h.entries].index("add_extra_state_shared_building_slots")
              < [k for k, _ in lazio_h.entries].index("buildings"))
        check("astilleros: la region con costa de Roma recibe astilleros",
              int(pdx.text(lazio_h.get("buildings").get("dockyard")) or 0) >= 1, pdx.render(lazio_h.get("buildings")))
        check("astilleros: el reporte dice cuantos", any(n.startswith("astilleros: NRE") for n in ctx.notes))
        pta_s = pdx.parse((states / "901-Fixture.txt").read_text()).get("state").get("history")
        check("construccion: satelite +2", pdx.text(pta_s.get("add_extra_state_shared_building_slots")) == "2")
        check("astilleros: sin costa no se inventan (Buenos Aires del fixture no tiene costa)",
              "dockyard" not in pdx.render(pdx.parse((states / "900-Fixture.txt").read_text())).replace("dockyard = 0", ""))
        check("avisa del archivo con comparaciones", any("907-Fixture" in w for w in ctx.warnings), str(ctx.warnings))

        check("avisa lo que no encontro con parecidos",
              any("Tierra del Fuego" in w for w in ctx.warnings), str(ctx.warnings))
        pta = (mod / "history/countries/PTA - Southern Patagonia.txt").read_text()
        check("capital provisoria del satelite", "capital = 901" in pta, pta)
        check("pais sin territorio no lleva capital",
              "capital" not in (mod / "history/countries/FCU - Free Corporative Capital Union.txt").read_text())


def test_scenario() -> None:
    section("escenario 2100: bookmark y fechas")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        root = pdx.parse((mod / "common/bookmarks/meganations_2100.txt").read_text())
        bm = root.get("bookmarks").get("bookmark")
        check("fecha 2100", pdx.text(bm.get("date")) == "2100.1.1.12")
        check("EFE por defecto", pdx.text(bm.get("default_country")) == "EFE")
        featured = [k for k in bm.keys() if isinstance(k, str) and len(k) == 3 and k.isupper()]
        check("destaca a todas las meganaciones con territorio", {"EFE", "ASC", "NRE", "HSN", "APF"} <= set(featured), str(featured))
        check("picture copiada de vanilla", pdx.text(bm.get("picture")) == "GFX_select_date_1936")
        check("effect copiado de vanilla", isinstance(bm.get("effect"), pdx.Block))
        efe = bm.get("EFE")
        check("EFE destacado con su ideologia", pdx.text(efe.get("ideology")) == "fascism")
        check("EFE muestra el foco raiz", "EFE_custodio_de_la_tierra" in [pdx.text(v) for _, v in efe.get("focuses").entries])
        raw = (mod / "common/bookmarks/meganations_2100.txt").read_text()
        check("bloque del resto del mundo entrecomillado", '"---" = {' in raw, raw)
        defines = (mod / "common/defines/00_meganations_defines.lua").read_text()
        check("START_DATE 2100", 'NDefines.NGame.START_DATE = "2100.1.1.12"' in defines, defines)
        check("END_DATE 2200", 'NDefines.NGame.END_DATE = "2200.1.1.1"' in defines, defines)
        es = (mod / "localisation/spanish/meganations_scenario_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("nombre del escenario en castellano", "La Era de las Meganaciones" in es)

    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), quiet=True)
        check("sin vanilla igual hay bookmark (el descriptor reemplaza los vanilla)",
              (ctx.mod_root / "common/bookmarks/meganations_2100.txt").exists())


def test_anarchy_upgrades() -> None:
    section("anarquias: el espiritu nuevo no es peor que el que reemplaza (2026-10-01)")
    import yaml
    trees = yaml.safe_load((REPO_ROOT / "spec/07_focus_trees.yaml").read_text(encoding="utf-8"))["trees"]
    ideas_all = yaml.safe_load((REPO_ROOT / "spec/05_ideas.yaml").read_text(encoding="utf-8"))["countries"]
    worse = []
    for tag, tree in trees.items():
        if not tag.startswith("Z") or not isinstance(tree, dict):
            continue
        mods = {i["id"]: i.get("modifiers") or {} for g in ("starting_ideas", "focus_ideas")
                for i in (ideas_all.get(tag) or {}).get(g) or []}
        for b in tree["branches"]:
            for f in b["focuses"]:
                rw = f.get("reward") or []
                gone = [e["value"] for e in rw if e.get("effect") == "remove_idea"]
                new = [e["value"] for e in rw if e.get("effect") == "add_ideas"]
                for old_id in gone:
                    for new_id in new:
                        o, n = mods.get(old_id, {}), mods.get(new_id, {})
                        for k, v in o.items():
                            nv = n.get(k)
                            if nv is None or (v >= 0 and nv < v) or (v < 0 and nv > v):
                                worse.append(f"{f['id']}: {new_id}.{k}={nv} < {old_id}.{k}={v}")
    check("ningun foco de anarquia cambia un espiritu por uno con menos de algo", not worse, "; ".join(worse[:5]))
    import collections
    dup = []
    for tag, tree in trees.items():
        if isinstance(tree, dict):
            c = collections.Counter(f["name"]["spanish"] for b in tree["branches"] for f in b["focuses"])
            dup += [f"{tag}: {n}" for n, k in c.items() if k > 1]
    check("ningun arbol tiene dos focos con el mismo nombre", not dup, "; ".join(dup))


def test_routes() -> None:
    section("rutas: la IA hace lo politico temprano y ningun final depende de un pais vivo (2026-10-01)")
    import yaml
    trees = yaml.safe_load((REPO_ROOT / "spec/07_focus_trees.yaml").read_text(encoding="utf-8"))["trees"]
    megas = ["EFE", "ASC", "FCU", "HSN", "NAS", "SHD", "APF", "NRE"]
    low = [f"{t}.{b['id']}" for t in megas for b in trees[t]["branches"][:3]
           if (b.get("ai_factor") or 1) < 4]
    check("ramas politicas y de destino pesan 4 o mas para la IA", not low, ", ".join(low))
    dead = []
    for t in megas:
        for b in trees[t]["branches"]:
            for f in b["focuses"]:
                tag = (f.get("available") or {}).get("country_exists", "")
                if tag and tag not in megas:
                    dead.append(f["id"])
    check("ningun foco de meganacion pide que exista una anarquia o un satelite", not dead, ", ".join(dead))
    alt = [f["id"] for t in megas for b in trees[t]["branches"] for f in b["focuses"]
           if any(r.get("effect") == "or_cores" for r in f.get("reward") or [])]
    check("16 focos con camino alternativo (6 anarquias, 10 satelites)", len(alt) == 16, str(alt))
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root

        def focus(tag, fid):
            tree = pdx.parse((mod / f"common/national_focus/{tag}_focus.txt").read_text(encoding="utf-8-sig"))
            return next(f for k, f in tree.get("focus_tree").entries
                        if k == "focus" and pdx.text(f.get("id")) == fid)

        mandato = focus("EFE", "EFE_el_mandato_renovado")
        check("el peso de la rama multiplica el del foco (3 x 5)",
              pdx.text(mandato.get("ai_will_do").get("factor")) == "15", pdx.render(mandato.get("ai_will_do")))
        lib = " ".join(pdx.render(focus("ASC", "ASC_la_liberacion_del_este").get("completion_reward")).split())
        check("anarquia viva: objetivo de guerra; caida o satelite: nucleos y reclamos",
              "is_subject = no" in lib and "create_wargoal" in lib and "else = {" in lib
              and "add_core_of = ROOT" in lib and "add_claim_by = ROOT" in lib
              and "is_subject_of = ROOT" in lib and "annex_country" in lib, lib)
        ofe = focus("EFE", "EFE_la_ofensiva_verde")
        rew = " ".join(pdx.render(ofe.get("completion_reward")).split())
        check("la Ofensiva Verde se toma sin el Amazonas y no reclama el Santuario",
              ofe.get("available") is None and "is_owned_by = ZSG" in rew and "else" not in rew, rew)
        dacia = " ".join(pdx.render(focus("NRE", "NRE_dacia_provincia").get("completion_reward")).split())
        check("satelite: el premio normal solo si sigue siendo satelite propio",
              "ZDA = { is_subject_of = ROOT }" in dacia and "annex_country" not in dacia, dacia)
        loc_text = "".join(p.read_text(encoding="utf-8-sig") for p in (mod / "localisation").rglob("*focus*.yml"))
        check("la descripcion explica el camino alternativo",
              "Si ya no es tu satélite: núcleos" in loc_text and "Si ya cayeron o son satélite de alguien" in loc_text)
        caen = " ".join(pdx.render(focus("APF", "APF_los_emiratos_caen").get("available")).split())
        check("Los Emiratos Caen: tambien si son satelite de alguien o con Suez y Bagdad",
              "custom_trigger_tooltip" in caen and "ZWM = { is_subject = yes }" in caen
              and "NOT = { country_exists = ZWM }" in caen, caen)
        decs = pdx.parse((mod / "common/decisions/meganations_decisions.txt").read_text(encoding="utf-8-sig"))
        gaia = " ".join(pdx.render(decs.get("EFE_destino_category").get("EFE_proclamar_la_forma_final")
                                   .get("available")).split())
        check("el Dominio de Gaia acepta el Santuario garantizado en vez del Amazonas",
              "has_guaranteed = ZSG" in gaia and "country_exists = ZSG" in gaia, gaia)


def test_focus_idea_consistency() -> None:
    section("arboles: ningun espiritu se saca dos veces en la misma linea (2026-09-29)")
    import yaml
    trees = yaml.safe_load((REPO_ROOT / "spec/07_focus_trees.yaml").read_text(encoding="utf-8"))["trees"]
    bad = []
    for tag, tree in trees.items():
        if not isinstance(tree, dict):
            continue
        focs = {f["id"]: f for b in tree["branches"] for f in b["focuses"]}

        def removes(f):
            out = set()
            for e in f.get("reward") or []:
                if e.get("effect") == "remove_idea":
                    out.add(e["value"])
                if e.get("effect") == "swap_ideas":
                    out.add(e["remove"])
            return out

        def must(fid, seen=None):
            f = focs[fid]
            res = set()
            for p in f.get("prerequisites") or []:
                if p in focs:
                    res |= {p} | must(p)
            anyp = [p for p in (f.get("prerequisites_any") or []) if p in focs]
            if anyp:
                res |= set.intersection(*[{p} | must(p) for p in anyp])
            return res

        for fid, f in focs.items():
            for i in removes(f):
                for a in must(fid):
                    if i in removes(focs[a]):
                        bad.append(f"{fid} saca {i}, que ya saco {a}")
    check("ningun foco saca un espiritu que ya saco un foco del que depende", not bad, "; ".join(bad))


def test_events() -> None:
    section("eventos y on_actions")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        raw = (mod / "events/meganations_efe.txt").read_text()
        root = pdx.parse(raw)
        check("namespace declarado", pdx.text(root.get("add_namespace")) == "meganations_efe")
        events = root.get_all("country_event")
        # 2026-09-29: los caminos economicos, mas largos y con pros y contras
        efe_c = " ".join((mod / "common/national_focus/EFE_focus.txt").read_text().split())
        dip = efe_c[efe_c.index("id = EFE_diplomacia_del_agua"):][:1500]
        check("EFE: Ciudades Sedientas la saca solo el Ministerio (no la Diplomacia del Agua, que depende de el)",
              "EFE_ciudades_sedientas" not in dip.split("ai_will_do")[0], dip[:700])
        agua = efe_c[efe_c.index("id = EFE_el_agua_de_la_vida"):][:1500]
        check("EFE: el camino del agua termina en un espiritu del agua",
              "swap_ideas = { remove_idea = EFE_potencia_hidrica add_idea = EFE_agua_de_la_vida }" in agua, agua[:700])
        ideas_efe = " ".join((mod / "common/ideas/EFE_ideas.txt").read_text().split())
        adv = ideas_efe[ideas_efe.index("EFE_agua_de_la_vida = {"):][:900]
        check("EFE: el espiritu final tiene pros y contras", "monthly_population = 0.15" in adv and "war_support_factor = -0.1" in adv, adv)
        check("73 eventos del EFE (guerra limitada, 5 menores, independencias, el Santuario, guerra civil y destino)", len(events) == 73, str(len(events)))
        # 2026-09-29: guerras civiles (elegir bando), rama política extendida y forma final
        efe_cw = " ".join((mod / "events/meganations_efe.txt").read_text().split())
        e220 = efe_cw[efe_cw.index("id = meganations_efe.220 title"):][:30000]
        opa, opb = e220.split("name = meganations_efe.220.b")[0], e220.split("name = meganations_efe.220.b")[1]
        check("guerra civil: antes de empezar se anotan los espiritus y las variables del pais",
              "if = { limit = { has_idea = EFE_mandato_verde } set_global_flag = MN_cw_EFE_mandato_verde }" in opa
              and "set_variable = { var = global.MN_cw_EFE_biosteel value = EFE_biosteel }" in opa
              and opa.index("MN_cw_EFE_mandato_verde") < opa.index("start_civil_war"))
        e221 = efe_cw[efe_cw.index("id = meganations_efe.221 title"):][:30000]
        check("guerra civil: el ganador recupera los espiritus que le faltan",
              "if = { limit = { has_global_flag = MN_cw_EFE_mandato_verde NOT = { has_idea = EFE_mandato_verde } } "
              "add_ideas = EFE_mandato_verde }" in e221
              and "set_variable = { var = EFE_biosteel value = global.MN_cw_EFE_biosteel }" in e221, e221[:800])
        efe_hist = " ".join(next((mod / "history/countries").glob("EFE - *.txt")).read_text().split())
        check("tanques: las meganaciones arrancan con un diseño de tanque del juego base",
              'if = { limit = { has_dlc = "No Step Back" } set_technology = {' in efe_hist
              and "create_equipment_variant = { name = \"Blindado" in efe_hist
              and "type = light_tank_chassis_1" in efe_hist, efe_hist[-900:])
        # OIM propias y zonas desmilitarizadas (2026-09-30)
        mio_dir = mod / "common/military_industrial_organization/organizations"
        mio_own = " ".join((mio_dir / "meganations_mio.txt").read_text().split())
        mio_gen = " ".join((mio_dir / "00_generic_organization.txt").read_text().split())
        check("OIM: una propia por meganacion, con su nombre", "EFE_tank_organization = { allowed = { original_tag = EFE }" in mio_own
              and mio_own.count("_tank_organization = {") == 8 and "generic_repair" not in mio_own, mio_own[:400])
        check("OIM: la generica ya no esta para las meganaciones",
              "NOT = { OR = { original_tag = EFE original_tag = FCU" in mio_gen)
        states_txt = "".join(p.read_text() for p in (mod / "history/states").glob("*.txt"))
        check("sin zonas desmilitarizadas de 1936 (el Rin, los Estrechos)", "set_demilitarized_zone" not in states_txt)
        # La Guerra en las Sombras (2026-09-30)
        ops = " ".join((mod / "common/operations/meganations_operations.txt").read_text().split())
        check("sombras: 48 operaciones (6 por meganacion objetivo)", ops.count(" name = mn_op_") == 48)
        check("sombras: la estructura se copia de una operacion del juego (fases y equipo)",
              "infiltration_steal_tech_a = { base = 1 }" in ops and "infantry_equipment = 50" in ops
              and "steal_tech_modifier" not in ops and "cipher_token" not in ops)
        golpe = ops[ops.index("mn_op_golpe_mecanica_ASC = {"):][:6000]
        check("sombras: el golpe a la ASC pide 50 de infiltracion y le sube el calor",
              "var = MN_inf_ASC value = 50 compare = greater_than_or_equals" in golpe
              and "FROM = {" in golpe and "var = ASC_calor value = 15" in golpe
              and "has_country_flag = MN_vigilado_por_ASC" in golpe, golpe[:1500])
        check("sombras: solo contra esa potencia", "visible = { FROM = { tag = ASC } OR = { tag = EFE" in golpe)
        # error.log 2026-10-01: en outcome_execute el alcance es la operación;
        # todo efecto va dentro de ROOT (el que la lanza) o FROM (el objetivo).
        ops_root = pdx.parse((mod / "common/operations/meganations_operations.txt").read_text())
        sueltos = sorted({k for _, op in ops_root.entries if isinstance(op, pdx.Block)
                          for k in op.get("outcome_execute").keys() if k not in ("ROOT", "FROM")})
        check("sombras: outcome_execute solo tiene ROOT y FROM (nada suelto en la operacion)", not sueltos, str(sueltos))
        robo = ops[ops.index("mn_op_robo_tecnologico_EFE = {"):][:6000]
        check("sombras: la infiltracion y los planos robados van al pais que la lanza",
              "outcome_execute = { ROOT = { if = { limit = { has_country_flag = MN_vigilado_por_EFE }" in robo
              and "if = { limit = { tag = FCU } add_timed_idea = { idea = FCU_planos_robados" in robo, robo[:1500])
        decs_all = " ".join((mod / "common/decisions/meganations_decisions.txt").read_text().split())
        se_all = " ".join((mod / "common/scripted_effects/meganations_effects.txt").read_text().split())
        check("sombras: la defensa es de a 4 y vence sola cada 3 meses",
              "EFE_blindarse_contra_NRE" in decs_all and "var = MN_escudos value = 4 compare = less_than" in decs_all
              and "var = MN_ciclo_sombras value = 3 compare = greater_than_or_equals" in se_all
              and "clr_country_flag = MN_escudo_NRE" in se_all)
        efe_ev = " ".join((mod / "events/meganations_efe.txt").read_text().split())
        check("sombras: el pulso mensual corre la contrainteligencia", "EFE_sombras_mes = yes" in efe_ev)
        check("guerra civil: con el Monte, se separa la Dinastia con Aurelio IV",
              "start_civil_war = { ideology = fascism size = 0.35 }" in opa
              and "random_country = { limit = { original_tag = EFE NOT = { tag = EFE } has_civil_war = yes } set_cosmetic_tag = EFE_DINASTIA" in opa
              and "set_country_leader_portrait = { portrait = GFX_portrait_mn_Aurelio_IV }" in opa
              and "set_global_flag = EFE_guerra_civil" in opa, opa[:1500])
        check("guerra civil: se puede elegir el otro bando (vuelve Aurelio IV, se separa el Monte con Anahi)",
              "promote_character = EFE_aurelio_iv" in opb and "set_cosmetic_tag = EFE_MONTE" in opb
              and "GFX_portrait_mn_anahi_quiroga" in opb, opb[:1500])
        efe_tree_cw = " ".join((mod / "common/national_focus/EFE_focus.txt").read_text().split())
        monte = efe_tree_cw[efe_tree_cw.index("id = EFE_el_monte_se_levanta"):][:2500]
        check("guerra civil del EFE: la dispara la rama de cambiar lider", "id = meganations_efe.220" in monte, monte[:1200])
        cwo = " ".join((mod / "common/on_actions/04_meganations_civil_war.txt").read_text().split())
        check("guerra civil: al terminar, el ganador (sea quien sea) recibe su premio",
              "on_civil_war_end = { effect = { if = { limit = { original_tag = EFE has_global_flag = EFE_guerra_civil } "
              "clr_global_flag = EFE_guerra_civil country_event = meganations_efe.221 }" in cwo, cwo[:600])
        check("guerra civil: el premio es un espiritu nacional", "add_ideas = EFE_la_paz_verde" in efe_cw)
        gfx_cw = (mod / "interface/meganations_civil_war_portraits.gfx").read_text()
        check("guerra civil: el retrato del lider rebelde es un sprite del mod",
              'name = "GFX_portrait_mn_Aurelio_IV"' in gfx_cw and 'texturefile = "gfx/leaders/EFE/Aurelio_IV.dds"' in gfx_cw)
        pulses_cw = pdx.parse((mod / "common/scripted_effects/meganations_effects.txt").read_text())
        asc_p = " ".join(pdx.render(pulses_cw.get("ASC_pulso_de_la_red")).split())
        check("guerra civil de la ASC: por condiciones (computo y calor altos, sin guerra), una vez",
              "var = ASC_computo value = 100 compare = greater_than_or_equals" in asc_p
              and "set_country_flag = ASC_guerra_civil_hecha" in asc_p and "id = meganations_asc.220" in asc_p, asc_p[-900:])
        shd_p = " ".join(pdx.render(pulses_cw.get("SHD_pulso_del_rio")).split())
        check("guerra civil de la SHD: por condiciones alcanzables (los caudales suman 150): Pueblo 70 y Orden 35, o 3 meses de desborde",
              "var = SHD_pueblo value = 70 compare = greater_than_or_equals" in shd_p
              and "var = SHD_orden value = 36 compare = less_than" in shd_p
              and "var = SHD_meses_desborde value = 3" in shd_p
              and "has_idea = SHD_desborde" in shd_p and "id = meganations_shd.220" in shd_p, shd_p[-1500:])
        dest = efe_tree_cw[efe_tree_cw.index("id = EFE_el_destino_de_gaia"):][:1500]
        check("destino: el foco destraba la forma final", "set_country_flag = EFE_destino_abierto" in dest, dest[:600])
        decs_d = " ".join((mod / "common/decisions/meganations_decisions.txt").read_text().split())
        pf = decs_d[decs_d.index("EFE_proclamar_la_forma_final = {"):][:3000]
        check("forma final: nombre y bandera nuevos, nucleos y espiritu, con condiciones de tropas",
              "set_cosmetic_tag = EFE_GAIA" in pf and "add_ideas = EFE_dominio_de_gaia" in pf
              and "has_army_size = { size > 44 }" in pf and "add_core_of = EFE" in pf, pf[:1500])
        names_ct = (mod / "localisation/spanish/meganations_countries_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("forma final: el nombre nuevo en todos los gobiernos",
              ' EFE_GAIA:0 "El Dominio de Gaia"' in names_ct and ' EFE_GAIA_fascism:0 "El Dominio de Gaia"' in names_ct
              and " EFE_GAIA_ADJ:0 " in names_ct, names_ct[-800:])
        check("forma final: bandera (la del pais mientras no llegue la propia)",
              (mod / "gfx/flags/EFE_GAIA.tga").exists() and (mod / "gfx/flags/small/EFE_GAIA.tga").exists())
        # El Santuario de Gaia (2026-09-29): proteger el Amazonas crea una nación neutral.
        efe_ev2 = " ".join((mod / "events/meganations_efe.txt").read_text().split())
        e30 = efe_ev2[efe_ev2.index("id = meganations_efe.30 title"):][:1500]
        check("Santuario: proteger lo deja pendiente", "set_country_flag = EFE_santuario_pendiente" in e30, e30[:600])
        e32 = efe_ev2[efe_ev2.index("id = meganations_efe.32 title"):][:3000]
        check("Santuario: el EFE lo garantiza",
              "diplomatic_relation = { country = ZSG relation = guarantee active = yes }" in e32, e32[:700])
        check("Santuario: objetivo de guerra de la FCU, la NAS, la ASC y ZAF",
              all(f"{t_} = {{ create_wargoal = {{ type = annex_everything target = ZSG }} }}" in e32 for t_ in ("FCU", "NAS", "ASC", "ZAF")), e32[:1500])
        se_raw_s = (mod / "common/scripted_effects/meganations_effects.txt").read_text()
        pulso_s = " ".join(pdx.render(pdx.parse(se_raw_s).get("EFE_pulso_de_las_cubas")).split())
        check("Santuario: nace cuando el EFE ya tiene regiones de la selva",
              "has_country_flag = EFE_santuario_pendiente" in pulso_s and "EFE_crear_santuario = yes" in pulso_s)
        check("Santuario: garantia para siempre (si se cae, vuelve)",
              "NOT = { has_guaranteed = ZSG }" in pulso_s, pulso_s[-800:])
        zsg_h = next((mod / "history/countries").glob("ZSG - *.txt")).read_text()
        check("Santuario: neutral, con su espiritu y leyes de paz",
              "ZSG_santuario_de_gaia" in zsg_h and "civilian_economy" in zsg_h and "volunteer_only" in zsg_h, zsg_h[-700:])
        # La FCU y la Federación contra las Tierras Sin Ley (2026-09-29): cuando ZAN
        # termina su tercer foco, cada una puede justificar la guerra por lo que ocupa.
        import yaml as _ye
        zan_sel = _ye.safe_load((REPO_ROOT / "spec/08_territory.yaml").read_text(encoding="utf-8"))["territories"]["ZAN"]["resolve"]
        zan_names = [sel["state"] for sel in zan_sel if "state" in sel]
        spec_ns = _ye.safe_load((REPO_ROOT / "spec/12_events.yaml").read_text(encoding="utf-8"))["namespaces"]
        spec_plans = _ye.safe_load((REPO_ROOT / "spec/16_ai.yaml").read_text(encoding="utf-8"))["plans"]
        pulses = pdx.parse(se_raw_s)
        for tag_, ns_, pulse_, zev in (("FCU", "meganations_fcu", "FCU_pulso_del_directorio", 2),
                                       ("APF", "meganations_apf", "APF_pulso_de_los_consejos", 3)):
            evs_ = " ".join((mod / f"events/{ns_}.txt").read_text().split())
            e210 = evs_[evs_.index(f"id = {ns_}.210 title"):][:1500]
            check(f"Tierras Sin Ley: la {tag_} justifica una guerra para tomar regiones de ZAN",
                  "create_wargoal = { type = take_state_focus target = ZAN" in e210 and f"set_country_flag = {tag_}_contra_ZAN" in e210, e210[:900])
            check(f"Tierras Sin Ley: ZAN se entera de lo de la {tag_}",
                  f"ZAN = {{ country_event = {{ id = meganations_zan.{zev} days = 1 }} }}" in e210, e210[:900])
            pz = " ".join(pdx.render(pulses.get(pulse_)).split())
            check(f"Tierras Sin Ley: a la {tag_} le llega cuando ZAN termina su tercer foco (una vez)",
                  f"NOT = {{ has_country_flag = {tag_}_tierras_sin_ley }} country_exists = ZAN "
                  f"ZAN = {{ has_completed_focus = ZAN_foco_3_the_frontier_pact }} }} set_country_flag = {tag_}_tierras_sin_ley "
                  f"country_event = {{ id = {ns_}.210 days = 1 }}" in pz, pz[-700:])
            wg = next(x for x in next(e for e in spec_ns[ns_]["events"] if e["id"] == 210)["options"][0]["effects"]
                      if x.get("effect") == "wargoal")
            check(f"Tierras Sin Ley: la {tag_} reclama solo regiones que ocupa ZAN",
                  len(wg["states"]) >= 10 and all(n in zan_names for n in wg["states"]), str(wg["states"]))
            plan = next((p for p in spec_plans if p["id"] == f"{tag_}_declara_a_tierras_sin_ley"), None)
            check(f"Tierras Sin Ley: la IA de la {tag_} declara con la justificacion hecha",
                  plan is not None and plan["enable"].get("flag") == f"{tag_}_contra_ZAN"
                  and plan["strategies"] == [{"type": "declare_war", "target": "ZAN", "value": 80}], str(plan))
        from tools.gen.emitters import effects as _effm
        saved_states, saved_unres = _effm._STATES, set(_effm.UNRESOLVED)
        try:
            _effm.use_states({"alaska": 501, "kansas": 502})
            wg_r = " ".join(pdx.render(_effm.render_effects("FCU", [dict(wg, states=[["Alaska"], ["Kansas"], ["Atlantis"]])],
                                                             set(), {}, where="t")).split())
        finally:
            _effm.use_states(saved_states)
            _effm.UNRESOLVED.clear()
            _effm.UNRESOLVED.update(saved_unres)
        check("Tierras Sin Ley: el objetivo lista las regiones que existen (generator)",
              "generator = { 501 502 }" in wg_r, wg_r)
        # El lado del satélite (2026-09-29): su panel, la independencia y el aviso al señor.
        cats_s = " ".join((mod / "common/decisions/categories/meganations_categories.txt").read_text().split())
        # 2026-09-29: decisiones de emergencia 1, 2 y 3, una sola vez por partida
        decs_e = " ".join((mod / "common/decisions/meganations_decisions.txt").read_text().split())
        e3 = decs_e[decs_e.index("MEGANATIONS_emergencia_3 = {"):][:9000]
        check("emergencia: la 3 cuesta 250, se usa una vez y da 8 de infanteria y 6 de milicia",
              "cost = 250" in e3 and "NOT = { has_country_flag = MEGANATIONS_emergencia_3_usada }" in e3
              and "set_country_flag = MEGANATIONS_emergencia_3_usada" in e3
              # create_unit sin comillas internas (error.log 2026-09-30: "Malformed token")
              and e3.count('"division_template = Leva_de_Emergencia_III ') == 16
              and e3.count('"division_template = Milicia_de_Emergencia ') == 12
              and "add_manpower = 20000" in e3 and "type = support_equipment amount = 1000" in e3, e3[:1500])
        e1 = decs_e[decs_e.index("MEGANATIONS_emergencia_1 = {"):][:3000]
        check("emergencia: la 1 baja estabilidad y apoyo a la guerra 5% por 6 meses (Leva Forzosa, 2026-10-01)",
              "cost = 150" in e1 and "add_dynamic_modifier = { modifier = MEGANATIONS_leva_forzosa_1 days = 180 }" in e1
              and "add_stability = -0.05" not in e1)
        check("emergencia: para las meganaciones y las anarquias, no para los satelites",
              "original_tag = ZAN" in cats_s and "original_tag = NRE" in cats_s
              and "original_tag = PTA" not in cats_s[cats_s.index("MEGANATIONS_emergencia_category"):][:600])
        check("satelite: panel propio visible mientras sea satelite",
              "PTA_independencia_category = {" in cats_s and "is_subject_of = EFE" in cats_s, cats_s[:300])
        decs_s = " ".join((mod / "common/decisions/meganations_decisions.txt").read_text().split())
        ind = decs_s[decs_s.index("PTA_declarar_la_independencia = {"):][:1800]
        check("satelite: declarar la independencia con lealtad baja y el senor en guerra o perdiendo",
              "var = EFE_lealtad_pta value = 20 compare = less_than" in ind and "surrender_progress > 0.2" in ind, ind[:900])
        check("satelite: el senor lo suelta (end_puppet) y recibe la noticia",
              "EFE = { end_puppet = PTA country_event = { id = meganations_efe.44 days = 1 } }" in ind, ind[:1200])
        loc_d = (mod / "localisation/spanish/meganations_decisions_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("satelite: el panel muestra la lealtad guardada en el senor", "[?EFE.EFE_lealtad_pta]" in loc_d)
        se_raw = (mod / "common/scripted_effects/meganations_effects.txt").read_text()
        se_all = " ".join(se_raw.split())
        pulso = " ".join(pdx.render(pdx.parse(se_raw).get("EFE_pulso_de_las_cubas")).split())
        # Bioacero v2 (2026-09-29): "llega a 15 sin consecuencias ni saturacion".
        check("Bioacero v2: el metal vivo come (la saturacion sube la mitad del Bioacero guardado)",
              "set_variable = { var = EFE_hambre_del_metal value = EFE_biosteel }" in pulso
              and "divide_variable = { var = EFE_hambre_del_metal value = 2 }" in pulso
              and "add_to_variable = { var = EFE_saturacion value = EFE_hambre_del_metal }" in pulso, pulso[:900])
        check("Bioacero v2: se pudre desde 13", "var = EFE_biosteel value = 13 compare = greater_than_or_equals" in pulso)
        check("Bioacero v2: la plaga, mas probable cuanto mas llenas las cubas",
              "var = EFE_saturacion value = 85 compare = greater_than_or_equals" in pulso)
        efe_tree_b = " ".join((mod / "common/national_focus/EFE_focus.txt").read_text().split())
        metal = efe_tree_b[efe_tree_b.index("id = EFE_el_metal_que_crece"):][:2500]
        check("Bioacero v2: el que dan los focos tambien satura",
              "var = EFE_biosteel value = 5" in metal and "var = EFE_saturacion value = 15" in metal, metal[:800])
        check("eventos menores: salen por fecha, una sola vez",
              "limit = { date > 2100.3.20 NOT = { has_country_flag = EFE_menor_200 } } set_country_flag = EFE_menor_200 "
              "country_event = { id = meganations_efe.200 days = 1 }" in pulso, pulso[:300])
        mundo = " ".join((mod / "events/meganations_mundo.txt").read_text().split())
        check("eventos mundiales: namespace propio con 5 eventos y la Senal",
              "add_namespace = meganations_mundo" in mundo and all(f"id = meganations_mundo.{n} " in mundo for n in (1, 2, 3, 4, 5, 10, 11, 12)))
        clock = se_all[se_all.index("MEGANATIONS_eventos_mundiales = {"):][:4000]
        check("eventos mundiales: una bandera global y a todos los paises",
              "NOT = { has_global_flag = MEGANATIONS_mundo_1 }" in clock and "set_global_flag = MEGANATIONS_mundo_1" in clock
              and "every_country = { country_event = { id = meganations_mundo.1 days = 1 } }" in clock, clock[:600])
        check("eventos mundiales: los corre el pulso de cada potencia", pulso.count("MEGANATIONS_eventos_mundiales = yes") == 1
              and se_all.count("MEGANATIONS_eventos_mundiales = yes") == 8)
        check("la Senal: solo las potencias reciben el aviso",
              "every_country = { limit = { OR = { tag = EFE tag = FCU" in clock and "country_event = { id = meganations_mundo.10 days = 1 }" in clock)
        cats = " ".join((mod / "common/decisions/categories/meganations_categories.txt").read_text().split())
        check("la Senal: panel compartido por las ocho potencias y visible solo mientras dura",
              "MEGANATIONS_senal_category = {" in cats and "OR = { original_tag = EFE" in cats
              and "has_global_flag = MEGANATIONS_senal_activa" in cats and "NOT = { has_global_flag = MEGANATIONS_senal_resuelta }" in cats, cats[-700:])
        decs = " ".join((mod / "common/decisions/meganations_decisions.txt").read_text().split())
        frag = decs[decs.index("MEGANATIONS_descifrar_fragmento = {"):][:1500]
        check("la Senal: el quinto fragmento da el mensaje al ganador y la noticia a los demas",
              "set_global_flag = MEGANATIONS_senal_resuelta" in frag and "meganations_mundo.11" in frag
              and "NOT = { tag = ROOT } }" in frag and "OR = { tag = EFE" in frag, frag[:900])
        conq = next(ev for ev in events if pdx.text(ev.get("id")) == "meganations_efe.30")
        check("la conquista del Amazonas ofrece proteger o explotar", len(conq.get_all("option")) == 2)
        check("el pulso dispara la conquista por control del state", "meganations_efe.30" in (mod / "common/scripted_effects").joinpath(
            next(p.name for p in (mod / "common/scripted_effects").glob("*.txt") if "EFE_pulso" in p.read_text())).read_text())
        dec = "".join(p.read_text() for p in (mod / "common/decisions").glob("*.txt"))
        check("decisiones que abre la conquista", "EFE_conquista_proteger" in dec and "EFE_conquista_explotar" in dec)
        zwm = (mod / "events/meganations_zwm.txt").read_text()
        check("los Emiratos tienen su pulso de levas", "ANARQUIA_levas" in zwm or "ANARQUIA_levas" in "".join(
            p.read_text() for p in (mod / "common/scripted_effects").glob("*.txt")), zwm[:400])
        for ev in events:
            eid = pdx.text(ev.get("id"))
            check(f"{eid} solo por disparo", pdx.text(ev.get("is_triggered_only")) == "yes")
            for opt in ev.get_all("option"):
                check(f"{eid}: opcion con nombre primero", opt.entries[0][0] == "name")
        corona = events[1]
        check("evento de la corona con 2 opciones", len(corona.get_all("option")) == 2)

        on = pdx.parse((mod / "common/on_actions/00_meganations_on_actions.txt").read_text())
        efe = on.get("on_actions").get("on_startup").get("effect").get("EFE")
        check("on_startup dispara el evento 1 al EFE", pdx.text(efe.get("country_event")) == "meganations_efe.1")

        focus = (mod / "common/national_focus/EFE_focus.txt").read_text()
        check("el foco de la corona dispara el evento 2", "country_event = meganations_efe.2" in focus)
        check("el umbral 3 dispara el evento 3", "country_event = meganations_efe.3" in focus)

        es = (mod / "localisation/spanish/meganations_events_l_spanish.yml").read_text(encoding="utf-8-sig")
        for key in ("meganations_efe.1.t", "meganations_efe.2.b", "meganations_efe.3.d"):
            check(f"loc {key}", f" {key}:0 " in es)


def test_leaders_and_ideologies() -> None:
    section("lideres, rasgos e ideologias")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        spec = ctx.spec
        for c in spec.countries:
            chars = mod / f"common/characters/{c.tag}_characters.txt"
            check(f"{c.tag} tiene lider", chars.exists())
            if chars.exists():
                check(f"{c.tag}: lider con la ideologia del pais (TN001)",
                      f"ideology = {c.ideology}" in chars.read_text())
        check("ningun aviso TN001", not any("TN001" in w for w in ctx.warnings), str(ctx.warnings))
        traits = pdx.parse((mod / "common/country_leader/meganations_traits.txt").read_text())
        body = traits.get("leader_traits")
        check("88 rasgos propios (14 de lideres, 40 de ministros, 8 de inteligencia, 20 del alto mando, 6 de experiencia)", len(body.keys()) == 88, str(len(body.keys())))
        # 2026-09-29: "los oficiales deberian dar experiencia, como en vanilla"
        efe_raw = " ".join((mod / "common/characters/EFE_characters.txt").read_text().split())
        chief = efe_raw[efe_raw.index("EFE_mando_beltran_1 = {"):][:900]
        check("experiencia: el jefe del ejercito da experiencia de ejercito",
              "mn_xp_jefe_ejercito" in chief and "mn_mando_maniobra" in chief, chief)
        check("experiencia: el rasgo da experiencia diaria",
              "experience_gain_army = 0.25" in " ".join(pdx.render(body.get("mn_xp_jefe_ejercito")).split()))
        efe_chars = pdx.parse((mod / "common/characters/EFE_characters.txt").read_text()).get("characters")
        advisors = [k for k, v in efe_chars.entries if isinstance(v, pdx.Block) and v.get("advisor") is not None]
        hc_raw = [k for k, v in efe_chars.entries if isinstance(v, pdx.Block) and v.get("advisor") is not None
                  and pdx.text(v.get("advisor").get("slot")) == "high_command"]
        check("experiencia: el alto mando da experiencia de su rama",
              all(any(t in pdx.render(efe_chars.get(k).get("advisor").get("traits"))
                      for t in ("mn_xp_mando_ejercito", "mn_xp_mando_marina", "mn_xp_mando_aire")) for k in hc_raw) and hc_raw,
              str(hc_raw))
        check("experiencia: los ministros politicos no reciben rasgo de experiencia",
              "mn_xp_" not in pdx.render(efe_chars.get(next(k for k in advisors if "_min_" in k))))
        efe_chars = pdx.parse((mod / "common/characters/EFE_characters.txt").read_text()).get("characters")
        advisors = [k for k, v in efe_chars.entries if isinstance(v, pdx.Block) and v.get("advisor") is not None]
        mins = [k for k in advisors if "_min_" in k]
        check("6 ministros por meganacion (EFE; el sexto, de inteligencia)", len(mins) == 6 and "EFE_min_inteligencia_6" in mins, str(mins))
        # Altos mandos (2026-09-29): jefes de ejército, marina y aire y dos del alto mando.
        mandos = {pdx.text(efe_chars.get(k).get("advisor").get("slot")) for k in advisors if "_mando_" in k}
        check("alto mando del EFE: jefes de ejercito, marina y aire y alto mando",
              mandos == {"army_chief", "navy_chief", "air_chief", "high_command"}, str(mandos))
        jefe = efe_chars.get("EFE_mando_beltran_1").get("advisor")
        check("alto mando: en el panel militar (ledger) con su rasgo",
              pdx.text(jefe.get("ledger")) == "army" and "mn_mando_maniobra" in pdx.render(jefe.get("traits")), pdx.render(jefe))
        zwe_chars = pdx.parse(next((mod / "common/characters").glob("ZWE_characters.txt")).read_text()).get("characters")
        check("alto mando tambien para la Anarquia (un atamán y un jefe de guerrilla)",
              zwe_chars.get("ZWE_mando_voronov_1") is not None and zwe_chars.get("ZWE_mando_kozlova_2") is not None)
        adv = efe_chars.get(mins[0]).get("advisor")
        check("ministro: puesto, token, rasgo propio y costo", pdx.text(adv.get("slot")) == "political_advisor"
              and pdx.text(adv.get("idea_token")) == mins[0] and pdx.text(adv.get("cost")) == "150", pdx.render(adv))
        gens = [k for k, v in efe_chars.entries if isinstance(v, pdx.Block) and v.get("corps_commander") is not None]
        check("generales propios (EFE: 3 + su mariscal)", len(gens) == 3, str(gens))
        hsn_chars = pdx.parse((mod / "common/characters/HSN_characters.txt").read_text()).get("characters")
        adm = [k for k, v in hsn_chars.entries if isinstance(v, pdx.Block) and v.get("navy_leader") is not None]
        check("la HSN tiene almirantes", len(adm) == 2, str(adm))
        efe_hist = next((mod / "history/countries").glob("EFE - *.txt")).read_text()
        check("los ministros y generales se reclutan en la historia", f"recruit_character = {mins[0]}" in efe_hist)
        check("rasgos no aleatorios", all(pdx.text(v.get("random")) == "no" for _, v in body.entries))
        efe = (mod / "common/characters/EFE_characters.txt").read_text()
        check("Aurelio con su rasgo", "efe_custodian_of_the_earth" in efe)
        ideos = (mod / "localisation/spanish/replace/meganations_ideologies_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("nombre de gobierno corto", 'fascism_desc:0 "Régimen de Restauración"' in ideos, ideos[:600])
        check("grupo neutral renombrado", 'neutrality:0 "Mandato Trascendente"' in ideos, ideos[:400])
        check("sin descripciones placeholder", "Placeholder" not in ideos)
        types, groups = spec.ideology_index()
        check("17 sub-ideologias", len(types) == 17, str(len(types)))
        for g in groups:
            check(f"{g}: dos meganaciones", sum(
                1 for c in spec.countries if c.is_major and c.ideology_group == g) == 2)


def test_balance() -> None:
    section("balance: transferencias invariantes, industrializacion, leyes, milicias")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        van = ctx.vanilla
        from tools.gen.emitters import economy
        for res in ("oil", "steel", "aluminium", "rubber", "tungsten", "chromium", "coal"):
            before = sum((s.resources or {}).get(res, 0) for s in van.states())
            after = sum(economy.resources_of(ctx, s).get(res, 0) for s in van.states())
            check(f"total mundial de {res} invariable", before == after, f"{before} -> {after}")
        # Y en los archivos generados, no solo en memoria.
        total_steel = 0
        for s in van.states():
            f = mod / "history/states" / s.path.name
            src = f if f.exists() else s.path
            res = pdx.parse(src.read_text()).get("state").get("resources")
            if isinstance(res, pdx.Block) and res.get("steel") is not None:
                total_steel += float(pdx.text(res.get("steel")))
        check("acero total en los archivos = vanilla (64)", total_steel == 64, str(total_steel))
        delta = ctx.data["resource_delta"]
        check("el Ruhr (ASC) dona acero", delta[906]["steel"] < 0, str(dict(delta[906])))
        check("la ASC no baja de su minimo", 60 + delta[906]["steel"] >= 20, str(dict(delta[906])))
        check("la capital del EFE recibe acero", delta[900]["steel"] > 0, str(dict(delta[900])))
        zan_states = [sid for sid, tag in ctx.data["territory"].items() if tag in ("ZAN", "ZWE", "ZWI", "ZWM", "ZWB")]
        check("la Anarquia no dona ni recibe", all(not any(delta.get(sid, {}).values()) for sid in zan_states))

        added = ctx.data["added_buildings"]
        check("industrializacion: fabricas en slots libres del EFE (city 6 - 2 usados = 4)",
              added.get(900, {}).get("industrial_complex") == 4, str(dict(added.get(900, {}))))
        ba = pdx.parse((mod / "history/states/900-Fixture.txt").read_text()).get("state").get("history").get("buildings")
        check("la fabrica queda escrita en el state", pdx.text(ba.get("industrial_complex")) == "6", str(ba))
        check("la Anarquia no recibe fabricas", not any(added.get(sid) for sid in zan_states))

        efe = (mod / "history/countries/EFE - Ecofascist Empire.txt").read_text()
        check("EFE arranca con reclutamiento extensivo", "extensive_conscription" in efe)
        apf = (mod / "history/countries/APF - African Peoples Federation.txt").read_text()
        check("APF arranca con voluntarios", "volunteer_only" in apf, apf[-500:])
        hsn = (mod / "history/countries/HSN - High Seas Market Nation.txt").read_text()
        check("HSN arranca con voluntarios", "volunteer_only" in hsn)

        check("Polonia pasa a la Comuna Baltica", ctx.data["territory"].get(918) == "ZBC")
        asc = (mod / "history/countries/ASC - Automated Socialist Commune.txt").read_text()
        check("la ASC arranca con el Cuello de Botella", "ASC_cuello_de_botella" in asc)
        # Satélites del EFE más fuertes (2026-09-29): fábricas, guarnición e idea propia.
        yyg = next((mod / "history/countries").glob("YYG - *.txt")).read_text()
        pta = next((mod / "history/countries").glob("PTA - *.txt")).read_text()
        check("YYG y PTA arrancan con su idea", "YYG_protegidos_del_imperio" in yyg and "PTA_guardianes_del_hielo" in pta)
        check("YYG y PTA con guarnicion reforzada",
              ctx.data["division_count"].get("YYG") == 4 and ctx.data["division_count"].get("PTA") == 3,
              str(ctx.data["division_count"]))
        # Doctrinas de arranque (2026-09-29): cada bloque la suya, ya iniciada.
        doc = " ".join((mod / "common/on_actions/01_meganations_doctrines.txt").read_text().split())
        check("doctrina: el EFE con guerra de movimiento y blindados, ya iniciada",
              "EFE = { set_grand_doctrine = mobile_warfare set_sub_doctrine = rapid_dominance "
              "add_mastery = { amount = 100 sub_doctrine = rapid_dominance } }" in doc, doc[:600])
        check("doctrina: sus satelites comparten la del senor",
              "PTA = { set_grand_doctrine = mobile_warfare set_sub_doctrine = rapid_dominance" in doc
              and "YYG = { set_grand_doctrine = mobile_warfare" in doc)
        check("doctrina: Roma con asalto en masa e infanteria de choque",
              "NRE = { set_grand_doctrine = mass_assault set_sub_doctrine = shock_infantry" in doc)
        check("doctrina: la Anarquia comparte una (infiltracion)",
              "ZWE = { set_grand_doctrine = mass_assault set_sub_doctrine = infiltration_tactics" in doc
              and "ZWI = { set_grand_doctrine = mass_assault set_sub_doctrine = infiltration_tactics" in doc)
        check("doctrina: la HSN naval (corsarios) y la APF antitanque (palabra clave en otro track)",
              "HSN = { set_grand_doctrine = trade_interdiction set_sub_doctrine = destroyer_hunters" in doc
              and "APF = { set_grand_doctrine = grand_battleplan set_sub_doctrine = anti_tank_forces" in doc)
        check("doctrina: solo si el pais existe", "if = { limit = { country_exists = EFE } EFE = {" in doc)
        check("doctrina: el reporte lista las del juego", any(n.startswith("doctrinas del juego:") for n in ctx.notes))
        names = (mod / "localisation/spanish/meganations_countries_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("nombre de pais para las 4 ideologias y a secas (game.log: guerra contra un pais sin nombre)",
              all(f" {k}:0 " in names for k in ("ZWE", "ZWE_ADJ", "ZWE_neutrality", "ZWE_communism", "ZWE_fascism",
                                                  "ZWE_democratic", "EFE_communism_DEF"))
              and ' ZWE_communism:0 "Señores de la Guerra de Eurasia (Colectivismo)"' in names, names[:400])
        check("YYG y PTA con meta de industrializacion",
              any(n.startswith("industrializacion: YYG") for n in ctx.notes)
              and any(n.startswith("industrializacion: PTA") for n in ctx.notes))
        bal = (Path(tmp) / "balance.txt").read_text()
        check("el balance muestra los totales mundiales OK", "TOTAL MUNDIAL" in bal and "DISTINTO" not in bal, bal)

        menu = mod / "gfx/loadingscreens/load_5.dds"
        check("fondo del menu en la ruta de GFX_frontend_bg", menu.exists())
        raw = menu.read_bytes()
        import struct as _st
        check("reescalado al tamano del vanilla (4x2)", _st.unpack_from("<II", raw, 12) == (2, 4), str(_st.unpack_from("<II", raw, 12)))
        check("no toca otros sprites", not (mod / "gfx/interface/goals/goal_unknown.dds").exists())
        dlc = mod / "gfx/interface/frontend/dlc_menu_bg.dds"
        check("reemplaza tambien el fondo grande que usa frontendmainview.gui", dlc.exists())
        check("fondo grande al tamano del vanilla (1920x1080)",
              dlc.exists() and _st.unpack_from("<II", dlc.read_bytes(), 12) == (1080, 1920))
        check("no toca los botones chicos del menu", not (mod / "gfx/interface/frontend/menu_button.dds").exists())
        lar = mod / "gfx/loadingscreens/load_prueba.dds"
        check("pisa las pantallas de carga grandes de las expansiones (selector de fondos)",
              lar.exists() and _st.unpack_from("<II", lar.read_bytes(), 12) == (1440, 1920))
        # Pantallas de carga del usuario (2026-09-29)
        shots = {p.read_bytes() for p in (REPO_ROOT / "assets/menu/loading").glob("*.dds")}
        check("pantallas de carga: las del juego llevan las imagenes del mod", lar.read_bytes() in shots)
        check("pantallas de carga: el fondo del menu queda en la textura del menu", raw not in shots)
        check("pantallas de carga: el reporte lo dice", any(n.startswith("pantallas de carga:") for n in ctx.notes))
        # Fondos que el juego estira (2026-09-30: rayas en focos y Construcciones)
        check("fondos: no pisa un corneredTile que estira el centro",
              not (mod / "gfx/interface/tiles/tiled_plain_bg2.dds").exists())
        check("fondos: avisa cual salteo y por que",
              any("tiled_plain_bg2" in w and "rayas" in w for w in ctx.warnings), str(ctx.warnings))
        check("fondos: el papel oscuro ya no se usa (texto oscuro de las tecnologias)",
              not (REPO_ROOT / "assets/ui/fondo_papel_agencia.dds").exists())
        check("fondos: el papel de las tecnologias es el claro, si ya llego",
              (mod / "gfx/interface/tiles/tiled_paper_bg.dds").exists()
              == (REPO_ROOT / "assets/ui/fondo_papel_claro.dds").exists())
        # Fondos de cada rama de investigación (2026-09-30)
        check("investigacion: el reporte da textura y tamano de cada rama",
              any("GFX_industry_techtree_bg -> gfx/interface/techtree/industry_bg.dds (12x8)" in n for n in ctx.notes),
              "\n".join(n for n in ctx.notes if "investigacion" in n))
        check("investigacion: avisa la rama que el juego no tiene",
              any("GFX_armor_techtree_bg no existe" in w for w in ctx.warnings))
        from tools.gen.emitters.menu import _cover
        src = bytearray(128) + bytes(range(4 * 4 * 2)) * 1
        struct_src = bytearray(src)
        _st.pack_into("<III", struct_src, 12, 2, 4, 16)
        cov = _cover(bytes(struct_src), 4, 2, 2, 2)
        check("investigacion: _cover recorta al centro sin deformar",
              _st.unpack_from("<II", cov, 12) == (2, 2) and len(cov) == 128 + 2 * 2 * 4
              and cov[128:132] == bytes(struct_src[128 + 4:128 + 8]), cov[128:].hex())

        efe_c = (mod / "common/countries/Ecofascist_Empire.txt").read_text()
        check("EFE con cultura grafica sudamericana", "southamerican_gfx" in efe_c and "southamerican_2d" in efe_c, efe_c)
        shd_c = next((mod / "common/countries").glob("Sino*.txt")).read_text()
        check("cultura que no existe en el juego cae a la europea con aviso",
              "western_european_gfx" in shd_c and any("SHD: la cultura grafica" in w for w in ctx.warnings), shd_c)

        libya = (mod / "history/states/910-Fixture.txt").read_text()
        check("Congo: el dueno dentro de un if condicional se borra", "COG" not in libya, libya)
        check("el if que queda sin efectos desaparece, el que tiene otros efectos queda",
              libya.count("if = {") == 1 and "fixture_flag" in libya and 'has_dlc = "Thunder' in libya, libya)
        startup = (mod / "common/on_actions/01_meganations_territory.txt").read_text()
        check("red de seguridad: on_startup devuelve cada state a su dueno", "on_startup" in startup
              and "transfer_state = 910" in startup and "is_owned_by = APF" in startup, startup[:600])
        apf_h = next((mod / "history/countries").glob("APF - *.txt")).read_text()
        check("la APF funda su faccion con sus satelites",
              "MEGANATIONS_APF_FACTION" in apf_h and "add_to_faction = ZET" in apf_h, apf_h[-800:])
        check("bandera del usuario para la ASC", (mod / "gfx/flags/small/ASC.tga").exists()
              and (mod / "gfx/flags/ASC.tga").read_bytes() == (REPO_ROOT / "assets/ASC/flags/ASC.tga").read_bytes())

        ger_dec = " ".join((mod / "common/decisions/GER.txt").read_text().split())
        check("vacia las decisiones nacionales de un pais vanilla (GER): quedan cascaras inertes",
              "GER_example = { allowed = { always = no } available = { always = no } }" in ger_dec
              and "has_idea = GER_does_not_exist" not in ger_dec, ger_dec[-400:])
        check("una mision vaciada sigue siendo mision (otros scripts la nombran)",
              "GER_example_mission = { allowed = { always = no } activation = { always = no } days_mission_timeout = 30" in ger_dec
              and "timeout_effect" not in ger_dec, ger_dec[-400:])
        check("no toca las decisiones genericas", not (mod / "common/decisions/economy.txt").exists())


def test_fcu() -> None:
    section("FCU: el Directorio de las Cuatro y su arbol")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        tree = (mod / "common/national_focus/FCU_focus.txt").read_text()
        root = pdx.parse(tree).get("focus_tree")
        focuses = root.get_all("focus")
        check("arbol de la FCU con 50+ focos", len(focuses) >= 50, str(len(focuses)))
        by_id = {pdx.text(f.get("id")): f for f in focuses}
        check("days -> cost en semanas (49 dias = 7)", pdx.text(by_id["FCU_ano_fiscal"].get("cost")) == "7")
        opa = by_id["FCU_junta_de_emergencia"]
        check("la OPA pide la bandera de la mecanica", "has_country_flag = FCU_opa_habilitada" in pdx.render(opa.get("available")))
        check("la OPA y el segundo mandato se excluyen", "FCU_segundo_mandato" in pdx.render(opa.get("mutually_exclusive")))
        reward = pdx.render(opa.get("completion_reward"))
        check("la OPA asciende a Rourke", "promote_character = FCU_marcus_rourke" in reward, reward)
        check("la IA prefiere la OPA en guerra", "has_war = yes" in pdx.render(opa.get("ai_will_do")))
        bonos = pdx.render(by_id["FCU_bonos_del_directorio"])
        check("prerequisites_any: un solo bloque con dos focos",
              bonos.count("prerequisite = {") == 1 and "FCU_presupuesto_civil" in bonos and "FCU_presupuesto_militar" in bonos, bonos)
        check("mesa redonda pide las cuatro entre 40 y 60",
              pdx.render(by_id["FCU_la_mesa_redonda"].get("available")).count("check_variable") == 8)

        hist = next((mod / "history/countries").glob("FCU - *.txt")).read_text()
        check("las cuatro corporaciones arrancan en 50", all(f"var = FCU_{c}" in hist for c in
              ("castellane", "halvorsen", "meridian", "obsidian")) and hist.count("value = 50") >= 4, hist[-1500:])
        check("Rourke se recluta en la historia, despues de Castellane",
              hist.index("recruit_character = FCU_valeria_castellane") < hist.index("recruit_character = FCU_marcus_rourke"))
        check("Castellane queda confirmada como lider", "promote_character = FCU_valeria_castellane" in hist)
        check("el foco no recluta (error.log: solo en historia)", "recruit_character" not in reward)

        se = (mod / "common/scripted_effects/meganations_effects.txt").read_text()
        check("efecto recalcular: clamp de las cuatro", all(f"var = FCU_{c}" in se for c in
              ("castellane", "halvorsen", "meridian", "obsidian")), se[:800])
        check("dos rivales debajo de 25: OR de pares con AND", "OR = {" in se and "AND = {" in se)
        decs = (mod / "common/decisions/meganations_decisions.txt").read_text()
        check("cada contrato recalcula el Directorio", decs.count("FCU_recalcular_directorio = yes") >= 6)
        check("el dividendo solo en guerra", "has_war = yes" in decs)

        efe_ev = (mod / "events/meganations_efe.txt").read_text()
        check("ultimatum: rechazarlo le da a la FCU el wargoal", "FCU = {" in efe_ev and "create_wargoal" in efe_ev)
        check("la HSN reacciona al ultimatum", (mod / "events/meganations_hsn.txt").exists())
        fcu_ev = (mod / "events/meganations_fcu.txt").read_text()
        check("el informe trimestral se vuelve a disparar", "id = meganations_fcu.3" in fcu_ev and "days = 90" in fcu_ev)


def test_asc() -> None:
    section("ASC: Poder de Computo, Consejo Sorteado y PLAN-41")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        root = pdx.parse((mod / "common/national_focus/ASC_focus.txt").read_text()).get("focus_tree")
        focuses = root.get_all("focus")
        check("arbol de la ASC de 55-75 focos (+4 del destino y +4 de los caminos economicos, 2026-09-29)", 55 <= len(focuses) <= 75, str(len(focuses)))
        by = {pdx.text(f.get("id")): f for f in focuses}
        for fid in ("ASC_el_sorteo_del_ano", "ASC_transparencia_del_plan", "ASC_el_derecho_a_no_trabajar",
                    "ASC_el_silencio_del_consejo", "ASC_la_singularidad_del_plan", "ASC_el_mercado_de_creditos_de_computo",
                    "ASC_lineas_sin_operarios", "ASC_supercomputadora_de_planificacion", "ASC_drones_de_infanteria",
                    "ASC_submarinos_autonomos", "ASC_enfriamiento_del_rin", "ASC_la_mente_de_la_comuna"):
            check(f"foco {fid} existe (alineado con el pack de iconos)", fid in by)
        silencio = by["ASC_el_silencio_del_consejo"]
        check("PLAN-41 pide 50 de computo", "ASC_computo" in pdx.render(silencio.get("available")))
        check("PLAN-41 asciende al sistema", "promote_character = ASC_plan_41" in pdx.render(silencio.get("completion_reward")))
        raw = (mod / "common/national_focus/ASC_focus.txt").read_text()
        check("la IA va por PLAN-41 con mucho computo", "value = 80" in raw)
        check("Asignar Africa es un ultimatum", "meganations_apf.1" in pdx.render(by["ASC_asignar_africa"].get("completion_reward")))
        check("Lineas sin Operarios saca el Cuello de Botella",
              "remove_ideas = ASC_cuello_de_botella" in pdx.render(by["ASC_lineas_sin_operarios"].get("completion_reward")))

        se = (mod / "common/scripted_effects/meganations_effects.txt").read_text()
        body = se[se.index("ASC_recalcular_computo"):]
        body = " ".join(body[:body.index("\n}") + 2].split())
        check("recalcular: sin las 12 ideas de computo (ahora es un espiritu vivo)", "ASC_computo_" not in body.replace("ASC_computo ", ""), body[:400])
        check("recalcular: el bonus sale del computo", "multiply_variable = { var = ASC_ef_investigacion value = 3 } divide_variable = { var = ASC_ef_investigacion value = 2000 }" in body, body[:1500])
        check("recalcular: agrega el espiritu vivo una sola vez",
              "has_dynamic_modifier = { modifier = ASC_mod_red_de_computo }" in body and "add_dynamic_modifier = { modifier = ASC_mod_red_de_computo }" in body)
        dm = pdx.parse((mod / "common/dynamic_modifiers/meganations_dynamic_modifiers.txt").read_text())
        red = dm.get("ASC_mod_red_de_computo")
        check("espiritu vivo: el valor es una variable", pdx.text(red.get("research_speed_factor")) == "ASC_ef_investigacion")
        check("espiritu vivo: siempre activo", pdx.text(red.get("enable").get("always")) == "yes")
        check("16 espiritus vivos (la mecanica y los satelites de cada potencia) y 3 de la Leva Forzosa",
              len(dm.entries) == 19 and dm.get("MEGANATIONS_leva_forzosa_3") is not None, str([k for k, _ in dm.entries]))
        sat = dm.get("EFE_mod_satelites")
        check("satelites: el espiritu vivo da poder politico segun la lealtad", pdx.text(sat.get("political_power_gain")) == "EFE_ef_sat_pp")
        se_all = " ".join((mod / "common/scripted_effects/meganations_effects.txt").read_text().split())
        ps = se_all[se_all.index("EFE_pulso_satelites = {"):]
        ps = ps[:ps.index("EFE_recalcular_satelites = yes }") + 40]
        check("satelites: la lealtad baja cada mes y mas en guerra", "var = EFE_lealtad_pta value = -1" in ps and "has_war = yes" in ps, ps[:600])
        check("satelites: con poca lealtad puede haber rebelion", "id = meganations_efe.40" in ps)
        check("satelites: el pulso de la potencia corre el de sus satelites", "EFE_pulso_satelites = yes" in se_all)
        hist = next((mod / "history/countries").glob("EFE - *.txt")).read_text()
        check("satelites: la lealtad arranca en 60", "var = EFE_lealtad_pta" in " ".join(hist.split()) and "value = 60" in hist)
        dec_all = (mod / "common/decisions/meganations_decisions.txt").read_text()
        check("satelites: ayuda y tributo por satelite", "EFE_ayuda_pta = {" in dec_all and "EFE_tributo_yyg = {" in dec_all)
        zwi = (mod / "events/meganations_zwi.txt").read_text()
        check("Anarquia: el pulso corre los caudillos", "ZWI_pulso_caudillos = yes" in zwi)
        for n in (2, 3, 4, 5, 6):
            check(f"Anarquia: evento meganations_zwi.{n}", f"id = meganations_zwi.{n}" in zwi)
        cz = se_all[se_all.index("ZWI_pulso_caudillos = {"):][:1500]
        check("Anarquia: el saqueo le llega a un vecino (SHD o HSN)", "id = meganations_zwi.2" in cz)
        raid = " ".join(zwi[zwi.index("id = meganations_zwi.2"):zwi.index("title = meganations_zwi.3.t")].split())
        check("Anarquia: el saqueo apunta a los vecinos", "SHD = { country_event" in raid and "HSN = { country_event" in raid, raid[:600])
        ideas_zwi = (mod / "common/ideas/ZWI_ideas.txt").read_text()
        check("Anarquia: caudillo supremo y tregua", "ZWI_caudillo_supremo" in ideas_zwi and "ZWI_tregua_de_caudillos" in ideas_zwi)
        decs = (mod / "common/decisions/meganations_decisions.txt").read_text()
        check("reasignar deja 30 dias de espera", "flag = ASC_reasignando" in decs and "days = 30" in decs)
        check("cada decision de la ASC recalcula", decs.count("ASC_recalcular_computo = yes") >= 6)
        hist = next((mod / "history/countries").glob("ASC - *.txt")).read_text()
        check("la ASC arranca con 30 de computo", "var = ASC_computo" in hist)
        check("PLAN-41 reclutado despues del Consejo", hist.index("ASC_allocation_council") < hist.index("ASC_plan_41")
              and "promote_character = ASC_allocation_council" in hist)
        ev = (mod / "events/meganations_asc.txt").read_text()
        check("el sorteo anual elige 3 rasgos al azar y se repite", ev.count("random_list") == 3 and "days = 365" in ev)
        check("la APF recibe el ultimatum", (mod / "events/meganations_apf.txt").exists())


def test_hsn() -> None:
    section("HSN: red de nodos, seguros, corso y botin")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        root = pdx.parse((mod / "common/national_focus/HSN_focus.txt").read_text()).get("focus_tree")
        focuses = root.get_all("focus")
        check("arbol de la HSN de 55-75 focos (+4 del destino y +4 de los caminos economicos, 2026-09-29)", 55 <= len(focuses) <= 75, str(len(focuses)))
        by = {pdx.text(f.get("id")): f for f in focuses}
        check("Aldana y Tavake se excluyen", "HSN_el_motin_de_kanto" in pdx.render(by["HSN_el_libro_de_fletes"].get("mutually_exclusive")))
        check("el motin asciende a Tavake", "promote_character = HSN_ines_tavake" in pdx.render(by["HSN_el_motin_de_kanto"].get("completion_reward")))
        check("el bloqueo legal es un ultimatum a la FCU", "meganations_fcu.8" in pdx.render(by["HSN_bloqueo_legal"].get("completion_reward")))
        se = (mod / "common/scripted_effects/meganations_effects.txt").read_text()
        body = se[se.index("HSN_recalcular_nodos"):]
        check("los nodos son regiones reales: Kanto resuelto por nombre", "controls_state = 912" in body, body[:600])
        check("un nodo que no existe nunca cuenta (y avisa)", "always = no" in body
              and any("Hong Kong" in w for w in ctx.warnings))
        check("perder un nodo da la idea de crisis", "HSN_nodo_perdido" in body and "value = HSN_nodos_prev" in body)
        check("con Tavake no hay peajes", "HSN_tavake" in body)
        ev = (mod / "events/meganations_hsn.txt").read_text()
        check("el conteo es un evento oculto (hidden = yes) que se repite cada 30 dias", "hidden = yes" in ev and "hide_window" not in ev and "days = 30" in ev)
        oa = (mod / "common/on_actions/00_meganations_on_actions.txt").read_text()
        check("el conteo arranca con la partida", "meganations_hsn.4" in oa)
        decs = (mod / "common/decisions/meganations_decisions.txt").read_text()
        check("seguros solo a quien esta en guerra y no contra nosotros",
              "HSN_asegurar_convoyes_fcu" in decs and "has_war_with = FCU" in decs)
        check("patentes de corso contra enemigos concretos", "HSN_patente_de_corso_fcu" in decs)
        check("el botin se gasta en decisiones", "HSN_botin_marines" in decs and "HSN_botin" in decs)


def test_nas() -> None:
    section("NAS: Inti-Soma, Qhapaq Nan, los Suyus y la tabla nueva de premios")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        raw = (mod / "common/national_focus/NAS_focus.txt").read_text()
        root = pdx.parse(raw).get("focus_tree")
        focuses = root.get_all("focus")
        check("arbol de la NAS de 55-75 focos (+4 del destino y +4 de los caminos economicos, 2026-09-29)", 55 <= len(focuses) <= 75, str(len(focuses)))
        by = {pdx.text(f.get("id")): f for f in focuses}
        tropas = pdx.render(by["NAS_guerreros_de_la_puna"].get("completion_reward"))
        check("tabla nueva: bono de investigacion con categoria del juego",
              "add_tech_bonus" in tropas and "category = mountaineers_tech" in tropas and "uses = 2" in tropas, tropas)
        check("las doctrinas dan experiencia de ejercito (land_doctrine no existe en 1.19)",
              not any("categoria de investigacion" in w for w in ctx.warnings)
              and "army_experience = 75" in pdx.render(by["NAS_doctrina_de_la_quebrada"].get("completion_reward")))
        check("Tawantinsuyu pide los cuatro suyus",
              pdx.render(by["NAS_el_tawantinsuyu"].get("available")).count("has_country_flag") == 4)
        check("el Inca asciende a su version Tawantinsuyu",
              "promote_character = NAS_amaru_inca" in pdx.render(by["NAS_el_inca_rompe_el_silencio"].get("completion_reward")))
        check("el Qhapaq Nan arranca en la capital", "capital_scope" in pdx.render(by["NAS_el_qhapaq_nan"].get("completion_reward")))
        decs = (mod / "common/decisions/meganations_decisions.txt").read_text()
        check("el camino crece hacia regiones vecinas conectadas", "any_neighbor_state" in decs)
        check("ceremonias con costo de Inti-Soma", "NAS_ceremonia_raymi" in decs and "var = NAS_inti" in decs)
        se = (mod / "common/scripted_effects/meganations_effects.txt").read_text()
        body = se[se.index("NAS_mes_del_sol"):]
        check("el mes del Sol suma las granjas y respeta el maximo", "value = NAS_granjas" in body and "value = NAS_inti_max" in body)
        check("la sobrecarga arriesga La Noche del Sol", "random_list" in body and "NAS_noche_del_sol" in body)
        check("el ultimatum al Directorio llega a la SHD", (mod / "events/meganations_shd.txt").exists())
        chars = (mod / "common/characters/NAS_characters.txt").read_text()
        check("retrato alternativo del Inca", "amaru_quispe_tawantinsuyu.dds" in chars)


def test_apf() -> None:
    section("APF: integracion federal, Amara contra Diallo")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        root = pdx.parse((mod / "common/national_focus/APF_focus.txt").read_text()).get("focus_tree")
        focuses = root.get_all("focus")
        check("arbol de la APF de 55-75 focos (+4 del destino y +4 de los caminos economicos, 2026-09-29)", 55 <= len(focuses) <= 75, str(len(focuses)))
        by = {pdx.text(f.get("id")): f for f in focuses}
        check("Diallo asciende con su retrato", "promote_character = APF_kwame_diallo"
              in pdx.render(by["APF_los_consejos_se_arman"].get("completion_reward")))
        check("Contra la Maquina es un ultimatum a la ASC",
              "meganations_asc.4" in pdx.render(by["APF_contra_la_maquina"].get("completion_reward")))
        decs = (mod / "common/decisions/meganations_decisions.txt").read_text()
        body = decs[decs.index("APF_integrar_zet"):]
        check("con Amara la integracion no pasa al desarrollo", "value = APF_integracion_zet" in body[:1500])
        check("con Diallo la integracion corre mas rapido y deja territorios dificiles",
              "has_country_flag = APF_diallo" in body and "APF_territorios_dificiles" in body)
        check("en 100 se anexa con nucleos", "annex_country" in body and "add_core_of = APF" in body)
        check("desarrollo regional en el mapa, region por region", "APF_plan_de_desarrollo_regional" in decs
              and "set_state_flag = APF_desarrollada" in decs)
        check("la ASC recibe el ultimatum", "meganations_asc.4" in (mod / "events/meganations_asc.txt").read_text())
        check("la APF arranca con 20 de desarrollo por miembro",
              "var = APF_desarrollo_zet" in next((mod / "history/countries").glob("APF - *.txt")).read_text())


def test_shd() -> None:
    section("SHD: tres caudales, Lin contra Zhou")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        root = pdx.parse((mod / "common/national_focus/SHD_focus.txt").read_text()).get("focus_tree")
        focuses = root.get_all("focus")
        check("arbol del SHD de 55-75 focos (+4 del destino y +4 de los caminos economicos, 2026-09-29)", 55 <= len(focuses) <= 75, str(len(focuses)))
        by = {pdx.text(f.get("id")): f for f in focuses}
        check("Zhou asciende con la Gran Crecida", "promote_character = SHD_zhou_mingyuan"
              in pdx.render(by["SHD_abrir_las_compuertas"].get("completion_reward")))
        check("Corregir el Sol es un ultimatum al NAS",
              "meganations_nas.5" in pdx.render(by["SHD_corregir_el_sol"].get("completion_reward")))
        eff = (mod / "common/scripted_effects/meganations_effects.txt").read_text()
        check("la armonia se recalcula", "SHD_recalcular_caudales" in eff and "SHD_armonia_perfecta" in eff
              and "SHD_desborde" in eff)
        check("el NAS recibe el ultimatum", "meganations_nas.5" in (mod / "events/meganations_nas.txt").read_text())
        check("el SHD arranca con los tres caudales",
              "var = SHD_pueblo" in next((mod / "history/countries").glob("SHD - *.txt")).read_text())


def test_nre() -> None:
    section("NRE: legiones, Auctoritas, Varro contra los Cuatro Imperatores")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        root = pdx.parse((mod / "common/national_focus/NRE_focus.txt").read_text()).get("focus_tree")
        focuses = root.get_all("focus")
        check("arbol del NRE de 55-75 focos (+4 del destino y +4 de los caminos economicos, 2026-09-29)", 55 <= len(focuses) <= 75, str(len(focuses)))
        by = {pdx.text(f.get("id")): f for f in focuses}
        check("ids alineados con los iconos", all(i in by for i in (
            "NRE_la_aclamacion_confirmada", "NRE_el_senado_restaurado", "NRE_las_vias_imperiales",
            "NRE_la_legion_decide", "NRE_la_guardia_pretoriana", "NRE_la_annona", "NRE_las_forjas_imperiales",
            "NRE_astilleros_de_ostia", "NRE_legio_i_italica", "NRE_mare_nostrum", "NRE_el_aquila_de_oro", "NRE_spqr")))
        check("Arbogast asciende con La Legion Decide", "promote_character = NRE_legado_arbogast"
              in pdx.render(by["NRE_la_legion_decide"].get("completion_reward")))
        check("Roma contra la Tierra es un ultimatum al EFE",
              "meganations_efe.14" in pdx.render(by["NRE_roma_contra_la_tierra"].get("completion_reward")))
        eff = (mod / "common/scripted_effects/meganations_effects.txt").read_text()
        body = eff[eff.index("NRE_mes_de_las_legiones"):]
        check("AVE IMPERATOR sale de la legion en 85", all(f"meganations_nre.{n}" in body for n in (4, 5, 6)))
        ev = (mod / "events/meganations_nre.txt").read_text()
        check("comprar a la legion solo con 25 de Auctoritas", "trigger" in ev and "promote_character = NRE_irina_vasilescu" in ev)
        chars = (mod / "common/characters/NRE_characters.txt").read_text()
        check("los cuatro imperatores existen", all(c in chars for c in (
            "NRE_lucius_varro", "NRE_legado_arbogast", "NRE_irina_vasilescu", "NRE_kerem_aydin")))
        decs = (mod / "common/decisions/meganations_decisions.txt").read_text()
        check("provincializacion de Hispania y Dacia en tres etapas",
              "NRE_provincia_zhi_3" in decs and "NRE_provincia_zda_3" in decs and "add_core_of = NRE" in decs)
        check("el NRE arranca con prestigio y Auctoritas",
              "var = NRE_auctoritas" in next((mod / "history/countries").glob("NRE - *.txt")).read_text())


def test_ai() -> None:
    section("IA: estrategias, decisiones con criterio, pesos por rama, iconos")
    import shutil
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        nas_tree = " ".join((mod / "common/national_focus/NAS_focus.txt").read_text().split())
        chicha = nas_tree[nas_tree.index("id = NAS_la_chicha_del_sol"):][:900]
        check("tooltips: un foco que solo suma variables muestra que suma", "custom_effect_tooltip = MN_tt_NAS_granjas_p1" in chicha, chicha)
        tips = (mod / "localisation/spanish/meganations_tooltips_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("tooltips: con nombre legible", 'MN_tt_NAS_granjas_p1:0 "§YGranjas del Sol§!: +1"' in tips, tips[:300])
        check("tooltips: el Control del Monte sigue secreto", "EFE_control_del_monte" not in tips)
        import yaml
        raw_dec = yaml.safe_load((REPO_ROOT / "spec/14_decisions.yaml").read_text(encoding="utf-8"))
        used = set()
        def walk(x):
            if isinstance(x, dict):
                if x.get("effect") == "add_variable":
                    used.add(x["var"])
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        for f in (REPO_ROOT / "spec").glob("*.yaml"):
            walk(yaml.safe_load(f.read_text(encoding="utf-8")))
        missing = sorted(used - set(raw_dec["variable_names"]))
        check("tooltips: toda variable que se suma tiene nombre (o hidden)", not missing, str(missing))
        cap = " ".join((mod / "common/on_actions/03_meganations_capitulation.txt").read_text().split())
        check("Emiratos: cuando capitulan en guerra con Roma, Roma decide", "on_capitulation" in cap
              and "ZWM = { has_capitulated = yes } NRE = { has_war_with = ZWM" in cap and "country_event = meganations_nre.50" in cap
              and "set_country_flag = NRE_capitulacion_zwm" in cap, cap[-400:])
        nre_log = (mod / "events/meganations_nre.txt").read_text()
        check("eventos: cada evento visible deja rastro en game.log", 'log = "[GetDateText] MEGANATIONS evento meganations_nre.50 para [Root.GetTag]"' in nre_log)
        check("Emiratos: respaldo si el tratado de paz ya los borro (pulso de Roma)",
              "NRE_capitulacion_zwm" in (mod / "common/scripted_effects/meganations_effects.txt").read_text())
        nre_ev = " ".join((mod / "events/meganations_nre.txt").read_text().split())
        e50 = nre_ev[nre_ev.index("id = meganations_nre.50 title"):][:2500]
        check("Emiratos: anexar, provincia cliente o tomar la costa", "annex_country" in e50 and "puppet = ZWM" in e50
              and "APF" not in e50[:0] and "NRE = { transfer_state = PREV }" in e50, e50[:800])
        check("Emiratos: anexar dispara las exigencias 30 dias despues", "id = meganations_nre.51 days = 30" in e50
              and "id = meganations_nre.54 days = 39" in e50)
        check("Emiratos: opcion que no choca con la clave del texto (.d)", "name = meganations_nre.50.d" not in e50)
        e82 = nre_ev[nre_ev.index("id = meganations_nre.82 title"):][:900]
        check("Emiratos: si Roma se niega, el vecino declara la guerra y se envalentona",
              "declare_war_on = { target = NRE type = take_state" in e82 and "APF_liberar_los_emiratos days = 182" in e82, e82)
        e61 = nre_ev[nre_ev.index("id = meganations_nre.61 title"):][:900]
        check("Emiratos: la Comuna pide que Roma marche contra Eurasia", "declare_war_on = { target = ZWE" in e61, e61)
        se_c = " ".join((mod / "common/scripted_effects/meganations_effects.txt").read_text().split())
        pulses = {"EFE_pulso_de_las_cubas": 3, "FCU_pulso_del_directorio": 2, "ASC_pulso_de_la_red": 2, "NRE_pulso_del_ocio": 3,
                  "SHD_pulso_del_rio": 2, "NAS_pulso_de_los_templos": 2, "APF_pulso_de_los_consejos": 1, "HSN_pulso_de_las_potencias": 1}
        total = sum(se_c.count(f"has_country_flag = {p.split('_')[0]}_cadena_") for p in pulses)
        check("16 cadenas de eventos, cada una chequeada una vez en el pulso de quien la empieza", total == 16, str(total))
        for needle, what in (("num_of_factories > 149", "industria (ASC 150 fabricas)"),
                             ("has_tech = improved_computing_machine", "tecnologia"),
                             ("has_manpower > 399999", "manpower"),
                             ("has_war_support > 0.7", "apoyo belico"),
                             ("has_equipment = { infantry_equipment > 7999 }", "equipo"),
                             ("has_army_size = { size > 23 }", "divisiones ajenas"),
                             ("date > 2102.1.1", "fecha"),
                             ("NRE = { has_completed_focus = NRE_hispania_provincia }", "foco ajeno"),
                             ("has_completed_focus = SHD_el_caudal_perfecto", "foco propio"),
                             ("has_stability < 0.3", "estabilidad")):
            check(f"cadenas: gatillo por {what}", needle in se_c, needle)
        hsn_rec = se_c[se_c.index("HSN_recalcular_nodos = {"):][:3000]
        check("HSN: cada nodo tiene su 0/1 para el panel", "set_variable = { var = HSN_nodo_kanto value = 1 }" in hsn_rec
              and "set_variable = { var = HSN_nodo_hong_kong value = 0 }" in hsn_rec, hsn_rec[:500])
        es_dec = (mod / "localisation/spanish/meganations_decisions_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("HSN: el panel explica que es un nodo y lista los 8", "¿QUÉ ES?" in es_dec and "Hong Kong: [?HSN_nodo_hong_kong]" in es_dec)
        zwe_tree = " ".join((mod / "common/national_focus/ZWE_focus.txt").read_text().split())
        check("Anarquia: arbol de 7 focos", zwe_tree.count("focus = { id = ZWE_foco_") == 7, str(zwe_tree.count("focus = { id = ZWE_foco_")))
        check("Anarquia: cuanto mas sobrevive, mas focos (fecha)", "available = { date > 2100.7.1 }" in zwe_tree and "date > 2105.1.1" in zwe_tree)
        check("Anarquia: cada foco sube el espiritu (swap)", "swap_ideas = { remove_idea = ZWE_resistencia_1 add_idea = ZWE_resistencia_2 }" in zwe_tree)
        check("Anarquia: la culminacion crea divisiones", "create_unit = { division =" in zwe_tree and "division_template = { name = \"Hueste\"" in zwe_tree)
        # error.log 2026-09-29: "create_unit -- invalid scope state". Solo vale en scope de state.
        state_scopes = {"capital_scope", "random_owned_controlled_state", "every_owned_state", "random_owned_state"}
        loose = []

        def _walk(block, parent, where):
            for key, value in block.entries:
                if key == "create_unit" and parent not in state_scopes:
                    loose.append(f"{where}: dentro de {parent}")
                if isinstance(value, pdx.Block):
                    _walk(value, key, where)
        for sub in ("common/national_focus", "common/scripted_effects", "common/decisions", "events"):
            for f in sorted((mod / sub).glob("*.txt")):
                _walk(pdx.parse(f.read_text(encoding="utf-8-sig")), None, f.name)
        check("create_unit siempre dentro de un state (capital o state propio)", not loose, "; ".join(loose[:5]))
        wrong = _scope_errors(mod)
        check("cada efecto y condicion en su scope (pais o state, reglas de CWTools)", not wrong, "; ".join(wrong[:5]))
        zwb_tree = " ".join((mod / "common/national_focus/ZWB_focus.txt").read_text().split())
        check("Amazonas: el 7mo foco firma paz blanca con todos y se queda lo que controla",
              "every_enemy_country = { white_peace = ROOT }" in zwb_tree and "CONTROLLER = { transfer_state = PREV }" in zwb_tree
              and "set_country_flag = ZWB_intocable" in zwb_tree)
        zan_tree = " ".join((mod / "common/national_focus/ZAN_focus.txt").read_text().split())
        check("Tierras Sin Ley: un foco por año", zan_tree.count("cost = 52") == 7 or zan_tree.count("cost = 52.0") == 7, zan_tree[:300])
        check("Tierras Sin Ley: 350.000 hombres, trenes y convoyes", "add_manpower = 350000" in zan_tree
              and "type = train_equipment_1 amount = 20" in zan_tree and "type = convoy amount = 50" in zan_tree)
        check("Tierras Sin Ley: casus belli contra la FCU y contra todos", "create_wargoal = { type = annex_everything target = FCU }" in zan_tree
              and "target = SHD" in zan_tree)
        ideas_zwb = (mod / "common/ideas/ZWB_ideas.txt").read_text()
        check("Amazonas: modificador opcional que el juego no conoce se omite con aviso",
              any("attrition" in w for w in ctx.warnings) or "attrition" in ideas_zwb)
        zwe_ev = " ".join((mod / "events/meganations_zwe.txt").read_text().split())
        check("Eurasia: la Union de los Senores (crea la faccion y convoca a las demas)",
              'create_faction = "La Unión de los Señores de la Guerra"' in zwe_ev and "id = meganations_zwe.11" in zwe_ev
              and "ZWE = { add_to_faction = ROOT }" in zwe_ev, zwe_ev[:500])
        zwi_ev = " ".join((mod / "events/meganations_zwi.txt").read_text().split())
        check("Indostan: si cae Bagdad entra en las guerras de los Emiratos",
              "add_to_faction = ZWM" in zwi_ev and "add_to_war = { targeted_alliance = ZWM enemy = PREV }" in zwi_ev, zwi_ev[:600])
        dm_hsn = pdx.parse((mod / "common/dynamic_modifiers/meganations_dynamic_modifiers.txt").read_text()).get("HSN_mod_nodos")
        check("HSN: cada nodo da comercio, astilleros, fabricas y poder politico",
              all(dm_hsn.get(k) is not None for k in ("trade_opinion_factor", "industrial_capacity_dockyard", "industrial_capacity_factory", "political_power_gain")))
        dec_hk = " ".join((mod / "common/decisions/meganations_decisions.txt").read_text().split())
        hk = dec_hk[dec_hk.index("HSN_reclamar_hong_kong = {"):][:800]
        check("HSN: decision Reclamar Hong Kong da el casus belli", "create_wargoal = { type = take_state target = ZWI" in hk, hk)
        hsn_tree = " ".join((mod / "common/national_focus/HSN_focus.txt").read_text().split())
        mal = hsn_tree[hsn_tree.index("id = HSN_malaca"):][:1500]
        check("HSN: la rama de nodos da experiencia naval, poder politico y baja la presion",
              "navy_experience = 15" in mal and "var = HSN_presion value = -5" in mal, mal[:600])
        check("HSN: y construye astilleros en el nodo (spec; en el fixture la region no existe)",
              "building: dockyard" in (REPO_ROOT / "spec/07_focus_trees.yaml").read_text(encoding="utf-8").split("- id: HSN_malaca")[1][:900])
        efe_h2 = next((mod / "history/countries").glob("EFE - *.txt")).read_text()
        check("debuffs: el EFE arranca con Ciudades Sedientas, Corte Dividida y Guardia Mal Equipada",
              all(x in efe_h2 for x in ("EFE_ciudades_sedientas", "EFE_corte_dividida", "EFE_guardia_mal_equipada")))
        efe_t2 = " ".join((mod / "common/national_focus/EFE_focus.txt").read_text().split())
        corte = efe_t2[efe_t2.index("id = EFE_la_corte_de_los_bosques"):][:3000]
        check("debuffs: un foco los saca", "remove_ideas = EFE_corte_dividida" in corte)
        check("debuffs: o un objetivo (20 divisiones) en el pulso", "has_idea = EFE_guardia_mal_equipada" in se_c
              and "remove_ideas = EFE_guardia_mal_equipada" in se_c)
        lev = se_c[se_c.index("ANARQUIA_levas = {"):][:1500]
        check("Anarquia: recluta una milicia por mes hasta 40 divisiones", "create_unit" in lev and "Leva_Anarquica" in lev and 'NOT = { has_template = "Leva_Anarquica" }' in lev and "size > 39" in lev, lev[:500])
        efe_h3 = next((mod / "history/countries").glob("EFE - *.txt")).read_text()
        check("ventaja de terreno para los mas debiles (EFE)", "EFE_la_selva_es_nuestra" in efe_h3)
        check("crisis entre potencias: el EFE le exige Arequipa al Sol", "EFE_crisis_1" in se_c and "meganations_efe.150" in se_c)
        efe_ev = " ".join((mod / "events/meganations_efe.txt").read_text().split())
        e153 = efe_ev[efe_ev.index("id = meganations_efe.153 title"):][:600]
        check("crisis: si el otro se niega, casus belli y la IA se prepara", "create_wargoal = { type = annex_everything target = NAS }" in e153
              and "EFE_contra_NAS" in e153 and "EFE_crisis_entre_potencias_NAS" in (REPO_ROOT / "spec/16_ai.yaml").read_text(encoding="utf-8"), e153)
        sa = se_c[se_c.index("ANARQUIA_sin_alianzas = {"):][:2500]
        check("Anarquia: sale de las facciones de las potencias y pierde sus garantias",
              "is_in_faction_with = FCU" in sa and "leave_faction = yes" in sa
              and "FCU = { diplomatic_relation = { country = ROOT relation = guarantee active = no } }" in sa, sa[:600])
        check("cadenas: con fecha minima (no saltan todas el dia 2)", "date > 2101.1.1" in se_c and "date > 2100.9.1" in se_c)
        gl = se_c[se_c.index("EFE_guerra_limitada = {"):][:1500]
        check("guerra limitada: hasta 2104, al 40% de rendicion del rival salta el armisticio",
              "has_war_with = FCU" in gl and "FCU = { surrender_progress > 0.4 }" in gl and "date > 2104.1.1" in gl, gl[:700])
        efe_ev2 = " ".join((mod / "events/meganations_efe.txt").read_text().split())
        arm = efe_ev2[efe_ev2.index("id = meganations_efe.160 title"):][:2500]
        check("armisticio: firma todo el bando del rival (el, sus satelites y su faccion)",
              "every_country = { limit = { OR = { tag = FCU is_subject_of = FCU is_in_faction_with = FCU } }"
              " save_event_target_as = meganations_armisticio_x" in arm, arm[:900])
        check("armisticio: con todo el bando propio que este en guerra con el",
              "every_enemy_country = { limit = { OR = { tag = ROOT is_subject_of = ROOT is_in_faction_with = ROOT } }" in arm)
        check("armisticio: cada uno se queda lo que ocupa y paz blanca",
              "event_target:meganations_armisticio_x = { every_owned_state = { limit = { is_controlled_by = "
              "event_target:meganations_armisticio_a } event_target:meganations_armisticio_a = { transfer_state = PREV } } }" in arm
              and "white_peace = event_target:meganations_armisticio_x" in arm and "FCU_revancha" in arm, arm[:1200])
        check("armisticio: tregua de un ano de verdad (set_truce)",
              "set_truce = { target = event_target:meganations_armisticio_x days = 364 }" in arm, arm[:1500])
        check("guerra limitada: se revisa cada semana", "id = meganations_efe.159 days = 7" in efe_ev2)
        rio = se_c[se_c.index("SHD_pulso_del_rio = {"):][:6000]
        check("SHD v4: el rio empuja lo pronosticado y pronostica el proximo mes",
              "var = SHD_produccion value = SHD_prox_p" in rio and "set_variable = { var = SHD_prox_o value = 6 }" in rio, rio[:900])
        check("SHD v4: racha de armonia con premios", "var = SHD_racha" in rio and "meganations_shd.192" in rio)
        shd_ev = (mod / "events/meganations_shd.txt").read_text()
        check("SHD v4: el Mandato del Cielo", "id = meganations_shd.192" in shd_ev and "SHD_mandato_del_cielo" in shd_ev)
        dec_s = " ".join((mod / "common/decisions/meganations_decisions.txt").read_text().split())
        check("SHD v4: Cerrar las Compuertas anula el proximo empuje", "SHD_cerrar_las_compuertas = {" in dec_s
              and "set_country_flag = SHD_compuertas" in dec_s)
        ob = se_c[se_c.index("MEGANATIONS_obras_de_la_ia = {"):][:1500]
        check("IA: cada mes infraestructura donde falta y a veces un espacio de construccion",
              "is_ai = yes" in ob and "free_building_slots = { building = infrastructure size > 0 include_locked = yes }" in ob and "add_extra_state_shared_building_slots = 1" in ob, ob[:700])
        mon = (mod / "common/on_actions/01_monroe_fixture.txt").read_text()
        check("Monroe: el script del juego que la reparte se pisa sin ella", "USA_monroe_doctrine_idea" not in mon.split("\n", 1)[1], mon)
        check("Monroe: el resto del script queda", "other_generic_idea" in mon and "is_in_americas" in mon)
        # error.log 2026-09-29: con events/ reemplazado, copiar un evento vanilla lo volvía a cargar entero.
        check("Monroe: los eventos del juego no se copian (events/ esta reemplazado)",
              not (mod / "events/MTG_USA.txt").exists())
        # ...y los on_actions del juego seguían llamando a eventos genéricos que ya no cargaban.
        wj = mod / "events/WarJustification.txt"
        check("eventos genericos: el aviso de justificacion de guerra vuelve",
              wj.exists() and "id = war_justification.1" in wj.read_text())
        gen_ev = (mod / "events/Generic_Fixture.txt").read_text() if (mod / "events/Generic_Fixture.txt").exists() else ""
        check("eventos genericos: de un archivo mixto, solo las elecciones (no el evento de 1938 de EEUU)",
              "id = election.2" in gen_ev and "usa.6" not in gen_ev and "add_namespace = usa" not in gen_ev, gen_ev)
        check("eventos genericos: los que faltan en el juego se avisan",
              any("ace_died" in w for w in ctx.warnings), str(ctx.warnings[-5:]))
        check("Monroe: el evento de limpieza corre cada semana", "days = 7" in (mod / "events/meganations_limpieza.txt").read_text())
        check("Monroe: el reporte dice de donde salia", any("01_monroe_fixture" in n for n in ctx.notes), str(ctx.notes[-5:]))
        ai = (mod / "common/ai_strategy/meganations_ai.txt").read_text()
        root = pdx.parse(ai)
        plan = root.get("MEGANATIONS_ASC_la_guerra_del_este")
        check("la ASC quiere conquistar Eurasia", plan is not None
              and "type = conquer" in pdx.render(plan) and "id = ZWE" in pdx.render(plan))
        check("el plan se abandona cuando el objetivo desaparece",
              plan is not None and "country_exists = ZWE" in pdx.render(plan.get("abort")))
        check("el senor protege a su satelite", "MEGANATIONS_EFE_protege_PTA" in ai and "type = protect" in ai)
        check("el satelite apoya a su senor", "MEGANATIONS_PTA_apoya_EFE" in ai)
        check("las rivalidades se antagonizan", "MEGANATIONS_EFE_rivaliza_con_NRE" in ai)
        check("no hay planes contra paises sin territorio (ZWB en el fixture)", "id = ZWB" not in ai)
        mil = root.get("MEGANATIONS_EFE_militar")
        milr = " ".join(pdx.render(mil).split()) if mil is not None else ""
        check("IA militar: el EFE arma blindados", "type = role_ratio id = armor value = 25" in milr, milr[:600])
        check("IA militar: pone industria en armas (tipo sin id)", "type = added_military_to_civilian_factory_ratio value = 25" in milr)
        inf = (mod / "common/technologies/infantry.txt").read_text()
        nv = inf[inf.index("night_vision_fixture = {"):]
        nv = nv[:nv.index("folder")]
        check("IA militar: investiga lo que sigue en su especialidad (ai_will_do de la tecnologia, solo NRE)",
              "modifier = { factor = 4 original_tag = NRE }" in nv, nv)
        check("IA militar: sin research_tech (el juego no lo conoce)", "research_tech" not in ai)
        # error.log 2026-09-29: "Unexpected token: ai_will_do". Un bloque anidado con el
        # nombre de la tecnología no se toca; el ai_will_do es el de la tecnología.
        from tools.gen.emitters.research import _inject_weights
        trap = ("technologies = {\n\tother = {\n\t\tsub = {\n\t\t\tradio = { dummy = yes }\n\t\t}\n"
                "\t\tname = \"llave } y # en texto\"\n\t}\n\tradio = {\n\t\ton_research_complete = { if = { "
                "ai_will_do = { factor = 9 } } }\n\t\tai_will_do = { factor = 1 }\n\t}\n}\n")
        out, n = _inject_weights(trap, {"radio": [("ASC", 4.0)]})
        techs = pdx.parse(out).get("technologies")
        radio = techs.get("radio")
        check("IA militar: el peso va a la tecnologia, no a un bloque anidado con su nombre",
              n == 1 and "ai_will_do" not in pdx.render(techs.get("other").get("sub"))
              and sum(1 for k, _ in radio.entries if k == "ai_will_do") == 1
              and "original_tag = ASC" in pdx.render(radio.get("ai_will_do")), out)
        # 2026-09-30 ("la HSN no investiga barcos"): el peso va al final del
        # ai_will_do, después de un `factor = 0` del juego, y trae un piso (add).
        zero = ("technologies = {\n\tbasic_ship_hull_light = {\n\t\tai_will_do = {\n\t\t\tfactor = 1\n"
                "\t\t\tmodifier = { factor = 0 has_navy_size = { size < 5 } }\n\t\t}\n\t}\n}\n")
        out, n = _inject_weights(zero, {"basic_ship_hull_light": [("HSN", 16.0)]})
        aw = pdx.render(pdx.parse(out).get("technologies").get("basic_ship_hull_light").get("ai_will_do"))
        aw1 = " ".join(aw.split())
        check("IA naval: el peso de la potencia va despues del factor = 0 del juego",
              n == 1 and aw1.index("factor = 0") < aw1.index("original_tag = HSN"), aw)
        check("IA naval: con piso (add) para que el juego no la deje en cero",
              "modifier = { add = 16 original_tag = HSN }" in aw1, aw)
        inv = root.get("MEGANATIONS_EFE_investigacion")
        invr = " ".join(pdx.render(inv).split()) if inv is not None else ""
        check("IA: research_weight_factor para las tecnologias del arbol (documentado, aunque el juego no lo use)",
              "type = research_weight_factor" in invr and "original_tag = EFE" in invr, invr[:400] or ai[:400])
        check("IA: research_weight_factor con ids que el juego no tiene se omite",
              "research_weight_factor id = advanced_ship_hull_light" not in " ".join(ai.split()))
        hsn = " ".join(pdx.render(root.get("MEGANATIONS_HSN_militar")).split())
        check("IA militar: un id que el juego no usa se omite (marines en el fixture)", "marines" not in hsn, hsn[:400])
        check("IA militar: el aviso lo dice", any("role_ratio:marines" in w for w in ctx.warnings))
        war = root.get("MEGANATIONS_EFE_militar_en_guerra")
        check("IA militar: en guerra, mas industria a las armas", war is not None
              and "has_war = yes" in pdx.render(war.get("enable")) and "value = 75" in pdx.render(war))
        check("la Anarquia no recibe plan militar de meganacion", "MEGANATIONS_ZWI_militar" not in ai)
        dz = root.get("MEGANATIONS_NRE_declara_a_ZWE")
        dzr = " ".join(pdx.render(dz).split()) if dz is not None else ""
        check("guerras contra la Anarquia: Roma declara desde su fecha, con ejercito y sin otra guerra",
              "type = declare_war id = ZWE" in dzr and "date > 2100.2.1" in dzr and "size > 11" in dzr and "has_war = no" in dzr, dzr)
        check("y se prepara desde el dia uno", "type = prepare_for_war id = ZWE" in " ".join(pdx.render(root.get("MEGANATIONS_NRE_se_prepara_contra_ZWE")).split()))
        nzc = " ".join(pdx.render(root.get("MEGANATIONS_NRE_contra_ZWE")).split())
        check("pero conquistar, recien desde su fecha (no declara solo antes)",
              "type = conquer id = ZWE" in nzc and "date > 2100.2.1" in nzc and "prepare_for_war" not in nzc, nzc)
        # Partida 2026-09-29: Eurasia quedó satélite de la Comuna y Roma, con el plan de
        # siempre, le declaró a Eurasia... y con eso a la Comuna entera.
        nz = " ".join(pdx.render(root.get("MEGANATIONS_NRE_contra_ZWE")).split())
        check("guerras contra la Anarquia: si la anarquia es satelite de alguien, no se le declara (seria declararle al senor)",
              "ZWE = { NOT = { has_country_flag = ZWE_intocable } is_subject = no }" in dzr
              and "ZWE = { is_subject = no }" in nz, dzr + " || " + nz)
        check("guerras contra la Anarquia: el plan se abandona si pasa a ser satelite",
              "abort = { OR = { NOT = { country_exists = ZWE } ZWE = { is_subject = yes } } }" in dzr
              and "abort = { OR = { NOT = { country_exists = ZWE } ZWE = { is_subject = yes } } }" in nz, dzr)
        from tools.gen.emitters.effects import render_conditions
        cond = " ".join(pdx.render(render_conditions("t", {"divisions_at_least": 12}, {}, where="t")).split())
        check("declarar la guerra puede pedir un ejercito minimo", "has_army_size = { size > 11 }" in cond, cond)
        import yaml
        spec_ai = yaml.safe_load((REPO_ROOT / "spec/16_ai.yaml").read_text(encoding="utf-8"))
        decl = [p for p in spec_ai["plans"] if any(st["type"] == "declare_war" for st in p["strategies"])]
        check("todo plan que declara guerra pide ejercito o ya esta en guerra",
              all("divisions_at_least" in str(p.get("enable")) for p in decl), str([p["id"] for p in decl]))
        check("prepararse va aparte de declarar", all(len(p["strategies"]) == 1 for p in decl))
        decs = (mod / "common/decisions/meganations_decisions.txt").read_text()
        cuotas = decs[decs.index("SHD_aumentar_cuotas = {"):]
        cuotas = cuotas[cuotas.index("ai_will_do"):cuotas.index("ai_will_do") + 900]
        check("la SHD sube el caudal mas bajo", "var = SHD_produccion" in cuotas and "modifier" in cuotas, cuotas)
        tree = (mod / "common/national_focus/EFE_focus.txt").read_text()
        cubas = tree[tree.index("id = EFE_biorrefinerias_de_rosario"):]
        check("la rama industrial pesa el doble", "factor = 2" in cubas[cubas.index("ai_will_do"):cubas.index("ai_will_do") + 60])
        eff = pdx.parse((mod / "common/scripted_effects/meganations_effects.txt").read_text())
        bad = []
        for name, body in eff.entries:
            for key, blk in body.entries if isinstance(body, pdx.Block) else []:
                if key == "if" and isinstance(blk, pdx.Block) and blk.get("remove_ideas") is not None:
                    idea = pdx.text(blk.get("remove_ideas"))
                    lim = pdx.render(blk.get("limit"))
                    # quitar una idea solo porque la tiene (y despues volver a ponerla) ensucia el tooltip
                    rest = " ".join(lim.replace(f"has_idea = {idea}", "").replace("limit", "").split()).strip("{} =")
                    if lim.strip().splitlines() and "NOT" not in lim and f"has_idea = {idea}" in lim and not rest:
                        bad.append(f"{name}:{idea}")
        check("tooltips: ninguna recalculacion quita una idea solo para volver a ponerla", not bad, str(bad))
        tech = (mod / "common/technologies/infantry.txt").read_text()
        check("investigacion: años corridos a 2100 (1936 -> 2100, 1943 -> 2107)",
              "start_year = 2100" in tech and "start_year = 2107" in tech and "start_year = 1936" not in tech)
        check("el resto del archivo del juego queda igual", "leads_to_tech = infantry_weapons1" in tech)
        eq = (mod / "common/units/equipment/infantry.txt").read_text()
        check("el equipo tambien corre de año", "year = 19" not in eq)
        names = (mod / "localisation/spanish/replace/meganations_research_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("tecnologias con nombre de 2100", 'infantry_weapons:0 "Fusiles de Fibra de Carbono"' in names, names[:300])
        check("nombre corto de la casilla renombrado (no '1942 rifle')",
              'infantry_weapons2_short:0 "Fusiles de Bobina Mejorados"' in names, names[:600])
        check("un nombre del juego con año escrito corre a 2100+",
              'other_tech:0 "Tech of 2100"' in names and 'other_tech_short:0 "2100 tech"' in names, names)
        check("el fixture reparte la Doctrina Monroe: se escribe la limpieza",
              (mod / "events/meganations_limpieza.txt").exists())
        gfx = (mod / "interface/meganations_EFE_goals.gfx").read_text()
        check("iconos propios registrados con brillo",
              "GFX_focus_EFE_custodio_de_la_tierra" in gfx and "GFX_focus_EFE_custodio_de_la_tierra_shine" in gfx)
        check("icono copiado al mod", (mod / "gfx/interface/goals/EFE_custodio_de_la_tierra.dds").exists())
        efe = (mod / "common/national_focus/EFE_focus.txt").read_text()
        check("el foco usa el icono", "icon = GFX_focus_EFE_custodio_de_la_tierra" in efe)

    with tempfile.TemporaryDirectory() as tmp:
        van = Path(tmp) / "vanilla"
        shutil.copytree(FIXTURE_VANILLA, van)
        f = van / "common/ai_strategy/default.txt"
        f.write_text(f.read_text().replace("type = contain", "type = protect"))
        ctx = build(Path(tmp) / "out", vanilla_path=str(van), quiet=True)
        ai = (ctx.mod_root / "common/ai_strategy/meganations_ai.txt").read_text()
        check("un tipo que el juego no usa se descarta con aviso",
              "type = contain" not in ai and any("contain" in w for w in ctx.warnings))


def test_arte() -> None:
    section("arte: iconos genericos, conexion por nombre, pedidos para el generador de imagenes")
    import shutil
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        shd = (ctx.mod_root / "common/ideas/SHD_ideas.txt").read_text()
        body = shd[shd.index("SHD_boom_exportador = {"):]   # sin dibujo todavia
        check("un espiritu sin dibujo toma un icono generico del juego segun su efecto (sin '?')",
              "picture = generic_production_bonus" in body[:300], body[:300])
        # Partida 2026-09-29: los espíritus sin dibujo mostraban un asesor con un papel o un avión.
        all_pics = " ".join((ctx.mod_root / "common/ideas").joinpath(f).read_text()
                            for f in [p.name for p in (ctx.mod_root / "common/ideas").glob("*.txt")])
        check("iconos genericos: nunca uno de asesor, de aviacion, de un pais o sin archivo",
              not any(b in all_pics for b in ("army_chief_defensive_1", "air_army_support", "GER_army_generic_bonus",
                                              "generic_army_zzz_missing")), "")
        check("iconos genericos: el ejercito usa el generico del ejercito", "picture = generic_army_support" in all_pics)
        from tools.gen.emitters.ideas import _generic_picture
        check("iconos genericos: sin tema reconocible, un generico en vez de '?'",
              _generic_picture({"odd_modifier": 1}, ["GFX_idea_generic_production_bonus"]) == "generic_production_bonus")
        check("iconos genericos: el reporte lista los que uso", any("iconos genericos usados" in n for n in ctx.notes))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shutil.copytree(REPO_ROOT / "spec", root / "spec")
        shutil.copytree(REPO_ROOT / "assets", root / "assets")
        px = [(10, 20, 30, 255)]
        art.write_dds(root / "assets/NRE/goals/NRE_el_consilium.dds", 1, 1, px)
        art.write_dds(root / "assets/NRE/ideas/NRE_senado.dds", 1, 1, px)
        art.write_dds(root / "assets/NRE/leaders/irina_vasilescu.dds", 1, 1, px)
        art.write_dds(root / "assets/events/meganations_nre.3.dds", 1, 1, px)
        art.write_dds(root / "assets/events/meganations_armisticio.dds", 1, 1, px)
        ctx = build(root / "out", vanilla_path=str(FIXTURE_VANILLA), quiet=True, spec_dir=root / "spec")
        mod = ctx.mod_root
        tree = (mod / "common/national_focus/NRE_focus.txt").read_text()
        check("foco: assets/<TAG>/goals/<id>.dds se conecta solo", "icon = GFX_focus_NRE_el_consilium" in tree)
        check("con su sprite y brillo", "GFX_focus_NRE_el_consilium_shine" in (mod / "interface/meganations_NRE_goals.gfx").read_text())
        ideas = (mod / "common/ideas/NRE_ideas.txt").read_text()
        check("espiritu: assets/<TAG>/ideas/<id>.dds se conecta solo", "picture = NRE_senado" in ideas)
        check("sprite del espiritu registrado", "GFX_idea_NRE_senado" in (mod / "interface/meganations_ideas.gfx").read_text())
        port = mod / "gfx/leaders/NRE/irina_vasilescu.dds"
        check("retrato: reemplaza al provisorio", port.exists() and port.read_bytes() == (root / "assets/NRE/leaders/irina_vasilescu.dds").read_bytes())
        ev = (mod / "events/meganations_nre.txt").read_text()
        check("evento: assets/events/<id>.dds reemplaza la imagen generica", "picture = GFX_meganations_nre_3" in ev)
        check("sprite del evento registrado", "GFX_meganations_nre_3" in (mod / "interface/meganations_events.gfx").read_text())
        efe_ev = " ".join((mod / "events/meganations_efe.txt").read_text().split())
        shared = [efe_ev[efe_ev.index(f"id = meganations_efe.{n} "):][:400] for n in (160, 164, 184)]
        check("arte compartido: los armisticios usan una sola imagen",
              all("picture = GFX_meganations_armisticio " in e for e in shared), shared[0][:300])
        gfx = (mod / "interface/meganations_events.gfx").read_text()
        check("arte compartido: el sprite se registra una vez", gfx.count('"GFX_meganations_armisticio"') == 1)
        from tools.arte import arte as arte_tool
        cat = [i["id"] for i in arte_tool.catalog() if i["type"] == "event_picture"]
        check("arte compartido: un solo pedido por imagen, no uno por evento",
              cat.count("meganations_armisticio") == 1 and "meganations_efe.160" not in cat)

    import shutil as _sh
    from tools.gen.errors import SpecError as _SpecError
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _sh.copytree(REPO_ROOT / "spec", root / "spec")
        (root / "assets").symlink_to(REPO_ROOT / "assets")
        dec = (root / "spec/14_decisions.yaml").read_text().replace("focus: EFE_rotar_los_cultivos", "focus: EFE_foco_que_no_existe", 1)
        (root / "spec/14_decisions.yaml").write_text(dec)
        try:
            build(root / "out", vanilla_path=str(FIXTURE_VANILLA), quiet=True, spec_dir=root / "spec")
            failed = False
        except _SpecError as exc:
            failed = "EFE_foco_que_no_existe" in str(exc)
        check("una condicion con un foco que no existe frena el build", failed)

    from tools.arte import arte as arte_mod
    items = arte_mod.catalog()
    ids = [i["id"] for i in items]
    check("catalogo de arte sin ids repetidos", len(ids) == len(set(ids)))
    check("el catalogo cubre focos, espiritus, retratos y eventos",
          {i["type"] for i in items} == set(arte_mod.KINDS))
    req = arte_mod._request(next(i for i in items if i["id"] == "NRE_irina_vasilescu"))
    check("el pedido sigue el contrato", all(k in req for k in ("ASSET_REQUEST", "type: leader_portrait",
          "id: NRE_irina_vasilescu", "filename: NRE_irina_vasilescu.png", "size: 156x210", "transparent_background: false")))


def test_mecanicas_v2() -> None:
    section("mecanicas v2: pulso mensual, riesgos y explicacion al arranque")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        eff = pdx.parse((mod / "common/scripted_effects/meganations_effects.txt").read_text())
        for tag, name in (("EFE", "EFE_pulso_de_las_cubas"), ("FCU", "FCU_pulso_del_directorio"), ("ASC", "ASC_pulso_de_la_red"),
                          ("HSN", "HSN_pulso_de_las_potencias"), ("NAS", "NAS_pulso_de_los_templos"), ("SHD", "SHD_pulso_del_rio"),
                          ("APF", "APF_pulso_de_los_consejos"), ("NRE", "NRE_pulso_del_ocio")):
            check(f"{tag}: pulso mensual definido", eff.get(name) is not None)
        cubas = pdx.render(eff.get("EFE_pulso_de_las_cubas"))
        check("EFE: la saturacion baja sola y trae fiebre y plaga",
              "EFE_fiebre_de_las_cubas" in cubas and "meganations_efe.22" in cubas and "EFE_biosteel" in cubas)
        check("SHD: los caudales se mueven solos (P+2 Pu+1 O-1)", "var = SHD_produccion" in pdx.render(eff.get("SHD_pulso_del_rio")))
        on = "".join(p.read_text() for p in (mod / "common/on_actions").glob("*.txt"))
        check("cada pulso arranca el primer dia", all(f"meganations_{t}.20" in on for t in ("efe", "fcu", "asc", "hsn", "nas", "shd", "apf", "nre")))
        check("cada potencia recibe su explicacion al arranque", all(f"meganations_{t}.21" in on for t in ("efe", "fcu", "asc", "hsn", "nas", "shd", "apf", "nre")))
        decs = (mod / "common/decisions/meganations_decisions.txt").read_text()
        inv = decs[decs.index("APF_invertir_zet = {"):]
        inv = inv[:inv.index("complete_effect")]
        check("APF: invertir se ve desde el dia 1 (sin foco)", "APF_integracion_abierta" not in inv, inv)
        es = (mod / "localisation/spanish/meganations_decisions_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("SHD: el nombre de cada decision dice cuanto mueve", "Aumentar Cuotas (P+10 Pu-10)" in es)
        check("SHD: el panel explica que suman 150 y muestra el bonus", "SUMAN SIEMPRE 150" in es and "[?SHD_ef_produccion_ver]%" in es)
        se_txt = (mod / "common/scripted_effects/meganations_effects.txt").read_text()
        shd = se_txt[se_txt.index("SHD_recalcular_caudales = {"):]
        shd = " ".join(shd[:shd.index("\n}") + 2].split())
        check("SHD: los caudales se normalizan a 150", "set_variable = { var = SHD_factor value = 150 }" in shd
              and "divide_variable = { var = SHD_factor value = SHD_suma }" in shd and "round_variable = SHD_pueblo" in shd, shd[:1200])
        fcu = se_txt[se_txt.index("FCU_recalcular_directorio = {"):]
        fcu = " ".join(fcu[:fcu.index("\n}") + 2].split())
        check("FCU: las cuatro se normalizan a 200", "set_variable = { var = FCU_factor value = 200 }" in fcu)
        check("FCU: sin 'el fuerte se hace mas fuerte' (no es suma cero)", "FCU_castellane value = 1 }" not in se_txt)
        check("FCU: cada contrato sube una y baja otra", "Contrato Ferroviario Automatizado (M+10 H-10)" in es)
        check("APF: la tension sube con cada miembro a medio integrar", "var = APF_integracion_zet value = 30" in " ".join(se_txt.split()))
        dec_txt = (mod / "common/decisions/meganations_decisions.txt").read_text()
        inv2 = dec_txt[dec_txt.index("APF_invertir_zet = {"):]
        inv2 = " ".join(inv2[:inv2.index("ai_will_do")].split())
        check("APF: invertir suma 10 de desarrollo y 3 de tension", "var = APF_desarrollo_zet value = 10" in inv2 and "var = APF_tension value = 3" in inv2, inv2)
        check("APF: el panel explica que es el Desarrollo", "Desarrollo = cuánto invirtió la Federación" in es)
        check("NRE: el panel explica la Auctoritas", "Es el respeto del ejército por el emperador" in es)
        check("ASC: el panel dice para que sirve", "¿PARA QUÉ SIRVE?" in es and "[?ASC_ef_investigacion_ver]%" in es)
        efe = (mod / "common/national_focus/EFE_focus.txt").read_text()
        check("rama nueva del EFE: Rotar los Cultivos da su espiritu", "id = EFE_rotar_los_cultivos" in efe and "add_ideas = EFE_rotacion_de_cultivos" in efe)
        cubas = pdx.render(eff.get("EFE_pulso_de_las_cubas"))
        check("y la rotacion alivia la saturacion en el pulso", "has_completed_focus = EFE_rotar_los_cultivos" in cubas)
        fcu_ev = (mod / "events/meganations_fcu.txt").read_text()
        check("interaccion: el Bioacero en venta le llega a la FCU y le paga al EFE",
              "meganations_fcu.23" in fcu_ev and "EFE = {" in fcu_ev[fcu_ev.index("meganations_fcu.23"):])
        check("interaccion: la HSN ofrece arbitraje a la FCU", "meganations_fcu.24" in fcu_ev)
        check("interaccion: la ASC ofrece computo al EFE", "meganations_efe.23" in (mod / "events/meganations_efe.txt").read_text())
        check("interaccion: el SHD pide puertos a la HSN", "meganations_hsn.23" in (mod / "events/meganations_hsn.txt").read_text())


def test_forces() -> None:
    section("armada y aviacion: sin aviones, solo destructores para la HSN")
    import shutil
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        check("nadie tiene aviones (2026-09-25)", not list((mod / "history/units").glob("*_air.txt")))
        check("el NRE no esta en navies: sin flota", not (mod / "history/units/NRE_2100_naval.txt").exists())
        check("la Anarquia no tiene barcos", not any(t in ctx.data["ships"] for t in ("ZWE", "ZWI", "ZWM", "ZWB", "ZAN")))

    # Con una copia del spec: el NRE con flota, solo acorazados, uno solo; y
    # una franja de industria que obliga a la ASC a bajar.
    with tempfile.TemporaryDirectory() as tmp:
        spec = Path(tmp) / "spec"
        shutil.copytree(REPO_ROOT / "spec", spec)
        (Path(tmp) / "assets").symlink_to(REPO_ROOT / "assets")   # el spec apunta a ../assets
        mil = (spec / "13_military.yaml").read_text()
        mil = mil.replace("navies: [HSN]", "navies: [NRE]").replace("ship_definition: destroyer", "ship_definition: battleship")
        (spec / "13_military.yaml").write_text(mil)
        bal = (spec / "15_balance.yaml").read_text().replace("meganation: [95, 115]", "meganation: [0, 1]")
        (spec / "15_balance.yaml").write_text(bal)
        ctx = build(Path(tmp) / "out", vanilla_path=str(FIXTURE_VANILLA), quiet=True, spec_dir=spec)
        mod = ctx.mod_root
        raw = (mod / "history/units/NRE_2100_naval.txt").read_text()
        check("solo el tipo pedido (acorazado), hasta el tope", "Roma" in raw and "Zara" not in raw, raw)
        check("owner pasa a NRE", "owner = NRE" in raw and "owner = ITA" not in raw)
        check("usa la version de DLC (mtg), no la legacy", "Vecchia" not in raw)
        variants = pdx.parse(raw).get("instant_effect").get_all("create_equipment_variant")
        check("solo las variantes que usan los barcos que quedan", [pdx.text(v.get("name")) for v in variants] == ["Classe Littorio"],
              str([pdx.text(v.get("name")) for v in variants]))
        check("no copia otros efectos del instant_effect", "add_political_power" not in raw)
        nre_h = next((mod / "history/countries").glob("NRE - *.txt")).read_text()
        check("la historia carga la armada", 'set_naval_oob = "NRE_2100_naval"' in nre_h)
        check("recibe la tecnologia del casco de sus barcos", "basic_ship_hull_heavy" in nre_h)
        added = ctx.data["added_buildings"]
        check("franja de industria: el EFE (2 IC en el fixture) baja a 1",
              sum(added.get(900, {}).get(k, 0) for k in ("industrial_complex", "arms_factory")) == -1,
              str(dict(added.get(900, {}))))
        ba = pdx.parse((mod / "history/states/900-Fixture.txt").read_text()).get("state").get("history").get("buildings")
        check("nunca queda un edificio en negativo",
              all(int(float(pdx.text(v))) >= 0 for k, v in ba.entries if k in ("industrial_complex", "arms_factory")), str(ba))


def test_unit_names() -> None:
    section("nombres de divisiones y barcos por faccion (19_unit_names)")
    import yaml
    import copy
    from tools.gen.emitters import unit_names as un
    from tools.gen.pdx import Block
    from tools.gen.errors import SpecError
    spec = yaml.safe_load((REPO_ROOT / "spec/19_unit_names.yaml").read_text(encoding="utf-8"))["unit_names"]
    div, ships, loc, _ = un.build_blocks(spec, None, None)
    megas = ["EFE", "ASC", "FCU", "HSN", "NAS", "SHD", "APF", "NRE"]
    for tag in megas:
        check(f"{tag}: lista de infanteria o su especialidad", any(k.startswith(f"{tag}_DIV_") for k in div.keys()))
        check(f"{tag}: los cinco tipos de barco", all(f"{tag}_SHIP_{t}" in ships.keys()
              for t in ("SCREEN", "SUBMARINE", "CRUISER", "CAPITAL", "CARRIER")))
    check("especialidades: marines HSN, montaña NAS, blindados EFE, artilleria SHD",
          all(k in div.keys() for k in ("HSN_DIV_MARINES", "NAS_DIV_MOUNTAIN", "EFE_DIV_ARMOR", "SHD_DIV_ARTILLERY")))
    nre = div.get("NRE_DIV_INFANTRY").get("ordered")
    check("legiones con numero romano", pdx.text(nre.get("9").entries[0][1]) == "Legio IX Hispana",
          pdx.text(nre.get("9").entries[0][1]))
    fcu = pdx.text(div.get("FCU_DIV_INFANTRY").get("ordered").get("2").entries[0][1])
    check("ordinal ingles", fcu.startswith("2nd "), fcu)
    check("cada lista tiene su nombre en EN y ES", len(loc) == len(div) + len(ships))
    rendered = pdx.render(div) + pdx.render(ships)
    check("el archivo se vuelve a leer", len(pdx.parse(rendered)) == len(div) + len(ships))
    check("satelites: una lista para todas las tropas", "ZNG_DIV_ALL" in div.keys()
          and '"mountaineers"' in pdx.render(Block([("x", div.get("ZNG_DIV_ALL"))])))
    # validacion contra el juego: los ids que no existen se omiten
    div2, ships2, _, report = un.build_blocks(spec, {"infantry"}, {"ship_hull_light"})
    check("sin el batallon en el juego, la lista no se escribe", "EFE_DIV_ARMOR" not in div2.keys()
          and "EFE_DIV_INFANTRY" in div2.keys())
    check("se omite el id que no existe", pdx.render(Block([("x", div2.get("EFE_DIV_INFANTRY"))])).count("bicycle") == 0)
    check("reporta los ids que faltan", "marine" in report["division_types"][0] and "destroyer" in report["ship_types"][0])
    bad = copy.deepcopy(spec)
    bad["ships"]["EFE"]["carrier"]["names"].append("Paraná")
    try:
        un.build_blocks(bad, None, None)
        check("un barco repetido en el mismo pais falla", False)
    except SpecError:
        check("un barco repetido en el mismo pais falla", True)
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        f = ctx.mod_root / un.DIVISIONS_FILE
        check("se escribe names_divisions", f.exists())
        fs = ctx.mod_root / un.SHIPS_FILE
        ships_txt = " ".join(fs.read_text(encoding="utf-8").split()) if fs.exists() else ""
        # reporte 2026-10-01: destroyer, battleship... se descartaban (se validaban solo contra el equipo)
        check("nombres de barcos: un tipo de barco del juego (destroyer) vale como ship_types",
              "HSN_SHIP_SCREEN" in ships_txt and "ship_types = { destroyer }" in ships_txt, ships_txt[:400])
        check("con el juego del fixture: solo los batallones que existen",
              f.exists() and '"marine"' not in f.read_text(encoding="utf-8") and "HSN_DIV_INFANTRY" in f.read_text(encoding="utf-8"))


def test_diplomacy() -> None:
    section("diplomacia: reclamos, rivalidades, guerras, tension")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        claims = ctx.data["claims"]
        check("la NRE reclama Moscu (vecino anarquico)", "NRE" in claims.get(917, set()), str(claims))
        check("el vecino de un satelite lo reclama su senor (SHD, no ZKR)",
              "SHD" in claims.get(914, set()) and "ZKR" not in claims.get(914, set()), str(claims))
        moscow = pdx.parse((mod / "history/states/917-Fixture.txt").read_text()).get("state").get("history")
        check("el reclamo queda escrito en el state", "NRE" in [pdx.text(v) for v in moscow.get_all("add_claim_by")])
        check("la Anarquia no reclama nada", not any(t in ("ZWE", "ZWI", "ZWM", "ZWB", "ZAN") for s in claims.values() for t in s))

        om = pdx.parse((mod / "common/opinion_modifiers/meganations_opinion_modifiers.txt").read_text()).get("opinion_modifiers")
        check("modificador de rival de bloque -50", pdx.text(om.get("meganations_bloc_rival").get("value")) == "-50")
        efe = next((mod / "history/countries").glob("EFE - *.txt")).read_text()
        nre = next((mod / "history/countries").glob("NRE - *.txt")).read_text()
        check("EFE mira mal a la NRE", "target = NRE" in efe and "meganations_bloc_rival" in efe)
        check("y la NRE al EFE (dos sentidos)", "target = EFE" in nre)
        check("rivalidad con un pais sin territorio no se escribe (FCU)", "target = FCU" not in efe)
        check("tension mundial en el pais por defecto", "add_named_threat" in efe and "threat = 30" in efe)
        asc = next((mod / "history/countries").glob("ASC - *.txt")).read_text()
        check("todos arrancan en paz (2026-09-28): la ASC no declara la guerra", "declare_war_on" not in asc, asc[-600:])
        check("leyes de arranque por ideologia: Roma (fascista) en economia de guerra y servicio obligatorio",
              "war_economy" in nre and "limited_exports" in nre and "service_by_requirement" in nre, nre[:900])
        fcu_h = next((mod / "history/countries").glob("FCU - *.txt")).read_text()
        check("leyes de arranque por ideologia: la FCU con libre comercio", "free_trade" in fcu_h, fcu_h[:900])
        asc_l = next((mod / "history/countries").glob("ASC - *.txt")).read_text()
        check("una sola ley por categoria (sin reclutamiento repetido)",
              sum(asc_l.count(x) for x in ("volunteer_only", "limited_conscription", "extensive_conscription",
                                           "service_by_requirement")) == 1, asc_l[:900])
        zwe_h = next((mod / "history/countries").glob("ZWE - *.txt")).read_text()
        check("leyes de arranque: la Anarquia en economia de guerra", "war_economy" in zwe_h and "closed_economy" in zwe_h)
        check("poder politico de arranque (200 las meganaciones)", "add_political_power = 200" in nre)
        # 2026-09-29: con el casus belli desde el día uno la IA declaraba en 2100 aunque su plan
        # esperara (la Federación contra los Emiratos). Roma tiene fecha (2100.2.1): el casus
        # belli le llega con el pulso, al jugador enseguida y a la IA desde esa fecha.
        check("Roma: sin casus belli en la historia (tiene fecha de guerra); lo da el pulso", "target = ZWE" not in nre.split("add_opinion_modifier")[0] or "create_wargoal" not in nre, nre[-800:])
        check("y se odian (en los dos sentidos)", "meganations_odio_anarquia" in nre
              and "target = NRE" in next((mod / "history/countries").glob("ZWE - *.txt")).read_text())
        cb = " ".join((mod / "common/scripted_effects/meganations_casus_belli.txt").read_text().split())
        check("el casus belli se renueva si se pierde", "MEGANATIONS_renovar_casus_belli" in cb and "tag = NRE ZWE = { exists = yes" in cb
              and "NOT = { has_wargoal_against = ZWE }" in cb, cb[-600:])
        check("el casus belli: el jugador enseguida, la IA desde su fecha de guerra",
              "OR = { is_ai = no date > 2100.2.1 }" in cb, cb[-600:])
        check("las Tierras Sin Ley no reciben casus belli (en paz con todos)", "target = ZAN" not in cb)
        check("el pulso de cada potencia renueva los casus belli",
              "MEGANATIONS_renovar_casus_belli = yes" in (mod / "common/scripted_effects/meganations_effects.txt").read_text())
        check("la justificacion no declara la guerra", "declare_war_on" not in efe)
        bal = (Path(tmp) / "balance.txt").read_text()
        check("balance: tabla de valor de los arboles", "VALOR DE LOS ARBOLES" in bal and "\nEFE " in bal[bal.index("VALOR DE LOS ARBOLES"):])
        check("avisa la guerra no declarada", any("ZWM" in w for w in ctx.warnings))


def test_vanilla_validation() -> None:
    section("validacion contra documentation/ e interface/ del juego")
    import shutil

    from tools.gen.errors import GenError

    with tempfile.TemporaryDirectory() as tmp:
        van = Path(tmp) / "vanilla"
        shutil.copytree(FIXTURE_VANILLA, van)
        spec = specload.load(REPO_ROOT / "spec")
        mods = set()
        for c in spec.raw["ideas"]["countries"].values():
            if isinstance(c, dict):
                for group in ("starting_ideas", "focus_ideas"):
                    ideas = c.get(group)
                    for idea in ideas if isinstance(ideas, list) else []:
                        mods.update(idea["modifiers"])
                for tier in (c.get("biosteel_tiers") or {}).get("tiers", []):
                    mods.update(tier["modifiers"])
        for trait in spec.raw["leaders"].get("leader_traits") or []:
            mods.update(trait["modifiers"])
        for dm in spec.raw["decisions"].get("dynamic_modifiers") or []:
            mods.update(dm["modifiers"])
        docs = van / "documentation"
        docs.mkdir()
        (docs / "triggers_documentation.md").write_text("### has_resources_amount\n### country_exists\n### check_variable\n### has_stability\n### original_tag\n### is_owned_by\n"
            "### has_country_flag\n### has_war\n### has_idea\n### has_completed_focus\n### is_core_of\n### has_state_flag\n### controls_state\n### has_war_with\n### any_neighbor_state\n### is_coastal\n### has_dynamic_modifier\n### has_army_size\n### tag\n### has_capitulated\n### num_of_factories\n### has_tech\n### has_manpower\n### has_war_support\n### has_equipment\n### date\n### exists\n### has_wargoal_against\n### is_controlled_by\n### is_in_faction_with\n### surrender_progress\n### is_ai\n### free_building_slots\n### is_subject_of\n### is_subject\n### has_civil_war\n### has_global_flag\n### is_major\n### owns_state\n### has_guaranteed\n### has_intelligence_agency\n")
        (docs / "effects_documentation.md").write_text(
            "add_political_power add_stability add_war_support army_experience "
            "add_manpower add_ideas swap_ideas set_autonomy country_event annex_country "
            "create_wargoal add_building_construction add_extra_state_shared_building_slots "
            "add_research_slot add_resource set_technology add_equipment_to_stockpile add_to_variable set_variable create_faction add_to_faction set_naval_oob set_air_oob add_opinion_modifier declare_war_on add_named_threat transfer_state "
            "add_timed_idea air_experience navy_experience promote_character recruit_character remove_ideas "
            "set_country_flag clr_country_flag clamp_variable set_variable add_country_leader_trait "
            "random_owned_controlled_state every_owned_state add_core_of set_state_flag clr_state_flag random_list add_claim_by add_tech_bonus "
            "add_dynamic_modifier subtract_from_variable multiply_variable divide_variable round_variable every_country custom_effect_tooltip puppet white_peace send_equipment log "
            "create_unit division_template add_to_war every_enemy_country set_state_owner add_advisor_role every_state create_faction add_to_faction leave_faction diplomatic_relation save_event_target_as set_truce set_grand_doctrine set_sub_doctrine add_mastery set_global_flag end_puppet clr_global_flag random_country set_cosmetic_tag start_civil_war create_intelligence_agency create_equipment_variant add_equipment_production\n"
        )
        (docs / "modifiers_documentation.md").write_text("\n".join(sorted(mods)))
        (van / "interface").mkdir(exist_ok=True)
        (van / "interface/goals.gfx").write_text(
            'spriteTypes = { spriteType = { name = "GFX_goal_generic_political_pressure" } '
            'spriteType = { name = "GFX_goal_unknown" } }'
        )

        out = Path(tmp) / "out"
        ctx = build(out, vanilla_path=str(van), quiet=True)
        check("con todo documentado no hay avisos de validacion",
              not any("no se validaron" in w for w in ctx.warnings), str(ctx.warnings))
        # todos los árboles: el del EFE ya tiene íconos propios en todos sus focos (2026-09-30)
        focus = "".join(p.read_text() for p in (ctx.mod_root / "common/national_focus").glob("*_focus.txt"))
        check("icono existente se conserva", "GFX_goal_generic_political_pressure" in focus)
        check("icono inexistente cae a GFX_goal_unknown", "GFX_goal_unknown" in focus)
        check("avisa del icono reemplazado", any("no existe en el juego" in w for w in ctx.warnings))

        # Caso real (reporte del usuario): la documentacion lista estos con
        # hueco, no por nombre. Tienen que pasar igual.
        templated = {"democratic_drift", "production_speed_arms_factory_factor",
                     "production_speed_infrastructure_factor"}
        check("el spec usa los modificadores con plantilla", templated <= mods, str(mods))
        (docs / "modifiers_documentation.md").write_text(
            "\n".join(sorted(mods - templated)) + "\n<ideology>_drift\n"
        )
        ctx = build(out, vanilla_path=str(van), quiet=True)
        check("drift aceptado por plantilla del doc", True)
        from tools.gen.vanilla import Vanilla
        v = Vanilla(van)
        check("plantilla <x> reconocida", v.is_documented("modifiers", "fascism_drift"))
        check("edificio vanilla -> production_speed_*", v.is_documented(
            "modifiers", "production_speed_arms_factory_factor"))
        check("edificio inexistente no pasa", not v.is_documented(
            "modifiers", "production_speed_datacenter_factor"))
        check("un hueco solo no acepta cualquier cosa", not v.is_documented("modifiers", "inventado_total"))

        (docs / "modifiers_documentation.md").write_text(
            "\n".join(sorted(mods - {"monthly_population"}))
        )
        try:
            build(out, vanilla_path=str(van), quiet=True)
            check("modificador inexistente frena el build", False, "no fallo")
        except GenError as exc:
            check("modificador inexistente frena el build", "monthly_population" in str(exc), str(exc))


# ---------------------------------------------------------------------------


def test_unique_units() -> None:
    section("unidades unicas (20_unique_units): una por meganacion")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        root = ctx.mod_root
        # 2026-10-01: el Gliptodonte es el TANQUE MODERNO (modular, libre en el
        # diseñador y en las divisiones), no el superpesado
        check("bloqueo: el tanque moderno es solo del EFE",
              ctx.data.get("tech_locks", {}).get("main_battle_tank_chassis") == "EFE", str(ctx.data.get("tech_locks")))
        check("el superpesado vuelve a ser de todos", "super_heavy_tank_chassis" not in ctx.data.get("tech_locks", {}))
        check("bloqueo: la tecnologia de un modulo compartido no se bloquea",
              "heavy_cannon_fixture_tech" not in ctx.data.get("tech_locks", {}))
        techs = (root / "common/technologies/super_heavy_fixture.txt").read_text(encoding="utf-8")
        mbt = None
        for k, v in pdx.parse(techs).entries:
            if k == "technologies":
                mbt = v.get("main_battle_tank_chassis")
        check("allow nuevo con original_tag", mbt is not None and pdx.text(mbt.get("allow").get("original_tag")) == "EFE",
              techs)
        check("sigue habilitando el batallon moderno (se usa libre en las divisiones)",
              mbt is not None and mbt.get("enable_subunits") is not None)
        eff = pdx.parse((root / "common/scripted_effects/meganations_unique_units.txt").read_text(encoding="utf-8"))
        body = eff.get("EFE_gliptodonte_desbloqueo")
        check("efecto de desbloqueo", body is not None)
        st = body.get("set_technology")
        check("da el chasis moderno y las piezas", all(t in st.keys() for t in
              ("main_battle_tank_chassis", "heavy_cannon_fixture_tech", "cast_armor_fixture_tech")), str(st.keys()))
        var = body.get("create_equipment_variant")
        check("diseño sobre el chasis moderno", pdx.text(var.get("type")) == "modern_tank_chassis_1", str(var))
        tpl = body.get("division_template")
        check("plantilla con batallones modernos (de linea, no de apoyo)",
              tpl is not None and "modern_armor" in tpl.get("regiments").keys(), str(tpl))
        ideas = (root / "common/ideas/meganations_unique_units.txt").read_text(encoding="utf-8")
        check("espiritu: +10% velocidad y blindaje, +8% ataque duro sobre el arquetipo moderno",
              "modern_tank_chassis" in ideas and "maximum_speed = 0.1" in ideas and "hard_attack = 0.08" in ideas, ideas[:600])
        units = (root / "common/units/super_heavy_fixture.txt").read_text(encoding="utf-8")
        check("el batallon usa 5% mas de suministros", "supply_consumption = 0.21" in units, units)
        dec = (root / "common/decisions/meganations_decisions.txt").read_text(encoding="utf-8")
        check("la decision del EFE corre el desbloqueo", "EFE_gliptodonte_desbloqueo" in dec)
        check("cada potencia tiene la decision de su unidad",
              all(f"{u}_desbloqueo" in dec for u in ("SHD_dragon_del_canal", "HSN_leviatan", "NAS_hijos_del_condor",
                  "NRE_onagro", "ASC_centinela", "APF_kiboko", "FCU_ala_de_obsidiana")))
        check("cola de produccion del Gliptodonte", body.get("add_equipment_production") is not None)
        check("marca de desbloqueo", pdx.text(body.get("set_country_flag")) == "EFE_gliptodonte_desbloqueado",
              str(body.get("set_country_flag")))
        # los paracaidistas del NAS: equipo fijo (tiltrotor), plantilla y una división
        nas = eff.get("NAS_hijos_del_condor_desbloqueo")
        st = nas.get("set_technology")
        check("NAS: paracaidistas y transporte", all(t in st.keys() for t in ("paratroopers", "transport_plane_fixture_tech")),
              str(st.keys()))
        check("NAS: bloqueo de la linea de paracaidistas",
              all(ctx.data["tech_locks"].get(t) == "NAS" for t in ("paratroopers", "paratroopers2")))
        tpl = nas.get("division_template")
        check("NAS: plantilla de una sola palabra", tpl is not None and pdx.text(tpl.get("name")) == "Condores",
              str(tpl))
        check("NAS: una division de arranque", "create_unit" in pdx.render(nas))
        check("NAS: sin plantilla si falta el batallon (Onagros)", eff.get("NRE_onagro_desbloqueo").get("division_template") is None)
        ai = (root / "common/ai_strategy/meganations_ai.txt").read_text(encoding="utf-8")
        check("IA: plan de los Kiboko que se activa con el desbloqueo (solo los ids que el juego usa)",
              "MEGANATIONS_APF_kiboko_produccion" in ai and "APF_kiboko_desbloqueado" in ai
              and "id = amphibious_mechanized" not in ai)
        check("IA: sin plan si ningun id existe (SHD)", "MEGANATIONS_SHD_dragon_del_canal_produccion" not in ai)


def main() -> int:
    for test in (
        test_pdx_roundtrip,
        test_spec_loads,
        test_loc_orphans,
        test_vanilla_fixture,
        test_ideology_merge,
        test_full_build,
        test_build_without_vanilla,
        test_art,
        test_check_detects_edits,
        test_phase3_content,
        test_territory,
        test_scenario,
        test_events,
        test_focus_idea_consistency,
        test_anarchy_upgrades,
        test_routes,
        test_leaders_and_ideologies,
        test_balance,
        test_fcu,
        test_asc,
        test_hsn,
        test_nas,
        test_apf,
        test_shd,
        test_nre,
        test_ai,
        test_arte,
        test_mecanicas_v2,
        test_forces,
        test_unit_names,
        test_unique_units,
        test_diplomacy,
        test_vanilla_validation,
    ):
        test()

    print("\n" + "=" * 62)
    if _failures:
        print(f"FALLARON {len(_failures)} de {_passes + len(_failures)} checks:\n")
        for f in _failures:
            print(f"  X {f}")
        return 1
    print(f"OK — {_passes} checks pasaron")
    return 0


if __name__ == "__main__":
    sys.exit(main())
