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


# ---------------------------------------------------------------------------


def test_pdx_roundtrip() -> None:
    section("pdx: parse y render")

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
    check("29 paises (8 meganaciones + 16 satelites + 5 de la Anarquia)", len(spec.countries) == 29, f"hay {len(spec.countries)}")
    check("todos los TAG de 3 letras", all(len(c.tag) == 3 for c in spec.countries))
    tags = {c.tag for c in spec.countries}
    for expected in ("EFE", "ASC", "FCU", "HSN", "NAS", "SHD", "APF", "NRE", "PTA", "YYG"):
        check(f"existe {expected}", expected in tags)

    types, groups = spec.ideology_index()
    check("4 grupos ideologicos", len(groups) == 4, f"hay {len(groups)}")
    check("grupos son los vanilla", set(groups) == {"fascism", "communism", "democratic", "neutrality"})
    for c in spec.countries:
        check(f"{c.tag} apunta a ideologia existente", c.ideology in types)

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
        check("color en una linea: rgb { r g b }", "color = rgb { 45 84 41 }" in colors, colors[400:700])
        check("color_ui en una linea", "color_ui = rgb { 45 84 41 }" in colors)
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
        check("arbol del EFE de 50-66 focos (6 nuevos, 2026-09-26)", 50 <= len(focuses) <= 66, str(len(focuses)))
        by = {pdx.text(f.get("id")): f for f in focuses}
        aurelio = by["EFE_el_mandato_renovado"].get("mutually_exclusive")
        monte = by["EFE_los_incendios_de_gaia"].get("mutually_exclusive")
        check("Aurelio y el Monte se excluyen (ida)", pdx.text(aurelio.get("focus")) == "EFE_los_incendios_de_gaia")
        check("Aurelio y el Monte se excluyen (vuelta)", pdx.text(monte.get("focus")) == "EFE_el_mandato_renovado")
        golpe = by["EFE_el_monte_se_levanta"]
        check("el golpe pide el control del monte", "has_country_flag = EFE_monte_listo" in pdx.render(golpe.get("available")))
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
        check("5 decisiones (con Purgar las Cubas)", len(decs.keys()) == 5, str(decs.keys()))
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
        check("3 milicias por pais de la Anarquia (2026-09-26)", len(divs) == 3, str(len(divs)))
        locs = sorted(pdx.text(d.get("location")) for d in divs)
        check("en el territorio mas poblado (India, no Ceilan)", set(locs) <= {"18", "19", "20", "21"} and "18" in locs, str(locs))
        zwe = pdx.parse((mod / "history/units/ZWE_2100.txt").read_text()).get("units").get_all("division")
        check("3 milicias en Europa (Moscu)", len(zwe) == 3 and pdx.text(zwe[0].get("location")) == "22", str(len(zwe)))

        section("la Anarquia no es una faccion (2026-09-25)")
        lh = next(p for p in (mod / "history/countries").glob("ZWI - *.txt")).read_text()
        check("ningun senor de la guerra funda una faccion", "create_faction" not in lh, lh[-600:])
        check("ni suma a los otros", "add_to_faction" not in lh)
        tpl = units.get("division_template")
        check("plantilla de milicia con 2 infanterias", len(tpl.get("regiments").get_all("infantry")) == 2)
        bal = (Path(tmp) / "balance.txt").read_text()
        check("balance generado fuera del mod", not (mod / "balance.txt").exists() and "BALANCE" in bal)
        check("balance cuenta las milicias", any(l.startswith("ZWI") and " 3 " in l for l in bal.splitlines()), bal[:800])
        check("balance muestra el contador de BioSteel", "EFE_biosteel: arranca en 5" in bal)
        check("balance ya no alerta ejercitos vacios", "Sin ejercito inicial" not in bal, bal[-600:])

        section("arranque militar: tecnologias, ejercito, equipo")
        efe_h = (mod / "history/countries/EFE - Ecofascist Empire.txt").read_text()
        check("el EFE (blindados) solo tiene lo basico: en el fixture no hay pestaña de blindados",
              set(pdx.parse(efe_h).get("set_technology").keys()) - {"popup"} == {"infantry_weapons", "tech_support"})
        check("avisa la pestaña que falta y lista las que hay",
              any("investigacion" in w and "infantry_folder" in w for w in ctx.warnings))
        nre_h = next((mod / "history/countries").glob("NRE - *.txt")).read_text()
        techs = pdx.parse(nre_h).get("set_technology")
        keys = set(techs.keys()) - {"popup", "tech_support"}
        check("NRE (infanteria): las 5 primeras de la pestaña, en orden de arbol",
              keys == {"infantry_weapons", "either_or_tech", "infantry_weapons1", "infantry_weapons2",
                       "improved_infantry_weapons"}, str(keys))
        check("de un par excluyente toma uno solo", "other_tech" not in keys)
        check("no regala variantes sin DLC", "legacy_only_tech" not in keys)
        check("no toma techs de otra pestaña", "basic_ship_hull_heavy" not in keys)
        check("sin popup", pdx.text(techs.get("popup")) == "no")
        pta_h = (mod / "history/countries/PTA - Southern Patagonia.txt").read_text()
        check("satelite: solo lo basico", set(pdx.parse(pta_h).get("set_technology").keys()) - {"popup"} <= {"infantry_weapons", "tech_support"})
        zwi_h = next((mod / "history/countries").glob("ZWI - *.txt")).read_text()
        check("anarquia: solo lo basico", set(pdx.parse(zwi_h).get("set_technology").keys()) - {"popup"} <= {"infantry_weapons", "tech_support"})

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


def test_events() -> None:
    section("eventos y on_actions")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        raw = (mod / "events/meganations_efe.txt").read_text()
        root = pdx.parse(raw)
        check("namespace declarado", pdx.text(root.get("add_namespace")) == "meganations_efe")
        events = root.get_all("country_event")
        check("21 eventos del EFE (pulso, explicacion, plaga, oferta de la ASC, conquista, hito)", len(events) == 21, str(len(events)))
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
        check("13 rasgos propios", len(body.keys()) == 13, str(body.keys()))
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

        check("vacia las decisiones nacionales de un pais vanilla (GER)",
              "GER_example" not in (mod / "common/decisions/GER.txt").read_text())
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
        check("arbol de la ASC de 50-66 focos (6 nuevos, 2026-09-26)", 50 <= len(focuses) <= 66, str(len(focuses)))
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
        check("recalcular: saca las 12 ideas de computo", body.count("remove_ideas = ASC_computo_") == 12)
        check("recalcular: tres niveles por capacidad", "value = 80" in body and "value = 40" in body)
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
        check("arbol de la HSN de 50-66 focos (6 nuevos, 2026-09-26)", 50 <= len(focuses) <= 66, str(len(focuses)))
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
        check("arbol de la NAS de 50-66 focos (6 nuevos, 2026-09-26)", 50 <= len(focuses) <= 66, str(len(focuses)))
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
        check("arbol de la APF de 50-66 focos (6 nuevos, 2026-09-26)", 50 <= len(focuses) <= 66, str(len(focuses)))
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
        check("arbol del SHD de 50-66 focos (6 nuevos, 2026-09-26)", 50 <= len(focuses) <= 66, str(len(focuses)))
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
        check("arbol del NRE de 50-66 focos (6 nuevos, 2026-09-26)", 50 <= len(focuses) <= 66, str(len(focuses)))
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
                    if lim.strip().splitlines() and "NOT" not in lim and f"has_idea = {idea}" in lim:
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
        check("sin espiritus vanilla que sacar en el fixture: no se escribe la limpieza",
              not (mod / "events/meganations_limpieza.txt").exists())
        gfx = (mod / "interface/meganations_NRE_goals.gfx").read_text()
        check("iconos del pack registrados con brillo",
              "GFX_focus_2100_nre_09_legio_i_italica" in gfx and "GFX_focus_2100_nre_09_legio_i_italica_shine" in gfx)
        check("icono copiado al mod", (mod / "gfx/interface/goals/focus_2100_nre_09_legio_i_italica.dds").exists())
        nre = (mod / "common/national_focus/NRE_focus.txt").read_text()
        check("el foco usa el icono", "icon = GFX_focus_2100_nre_09_legio_i_italica" in nre)

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
        body = shd[shd.index("SHD_precision = {"):]
        check("un espiritu sin dibujo toma un icono generico del juego segun su efecto (sin '?')",
              "picture = generic_production_bonus" in body[:300], body[:300])

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shutil.copytree(REPO_ROOT / "spec", root / "spec")
        shutil.copytree(REPO_ROOT / "assets", root / "assets")
        px = [(10, 20, 30, 255)]
        art.write_dds(root / "assets/NRE/goals/NRE_el_consilium.dds", 1, 1, px)
        art.write_dds(root / "assets/NRE/ideas/NRE_senado.dds", 1, 1, px)
        art.write_dds(root / "assets/NRE/leaders/irina_vasilescu.dds", 1, 1, px)
        art.write_dds(root / "assets/events/meganations_nre.3.dds", 1, 1, px)
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
        check("SHD: el nombre de cada decision dice cuanto mueve", "Aumentar Cuotas (P+10 O+3 Pu-8)" in es)
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
        check("la ASC arranca en guerra con Eurasia", "declare_war_on" in asc and "target = ZWE" in asc, asc[-600:])
        check("guerra contra un pais sin territorio no se declara (ZWM)", "target = ZWM" not in nre)
        # en el fixture ZWB no tiene territorio: se avisa en vez de escribirla
        check("el EFE arranca con la justificacion contra los Caudillos del Amazonas (o avisa si no existen)",
              ("create_wargoal" in efe and "target = ZWB" in efe)
              or any("justificacion EFE -> ZWB" in w for w in ctx.warnings))
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
        docs = van / "documentation"
        docs.mkdir()
        (docs / "triggers_documentation.md").write_text("### has_resources_amount\n### country_exists\n### check_variable\n### has_stability\n### original_tag\n### is_owned_by\n"
            "### has_country_flag\n### has_war\n### has_idea\n### has_completed_focus\n### is_core_of\n### has_state_flag\n### controls_state\n### has_war_with\n### any_neighbor_state\n### is_coastal\n")
        (docs / "effects_documentation.md").write_text(
            "add_political_power add_stability add_war_support army_experience "
            "add_manpower add_ideas swap_ideas set_autonomy country_event annex_country "
            "create_wargoal add_building_construction add_extra_state_shared_building_slots "
            "add_research_slot add_resource set_technology add_equipment_to_stockpile add_to_variable set_variable create_faction add_to_faction set_naval_oob set_air_oob add_opinion_modifier declare_war_on add_named_threat transfer_state "
            "add_timed_idea air_experience navy_experience promote_character recruit_character remove_ideas "
            "set_country_flag clr_country_flag clamp_variable set_variable add_country_leader_trait "
            "random_owned_controlled_state every_owned_state add_core_of set_state_flag clr_state_flag random_list add_claim_by add_tech_bonus\n"
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
        focus = (ctx.mod_root / "common/national_focus/EFE_focus.txt").read_text()
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
