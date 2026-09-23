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
    check("25 paises (8 meganaciones + 16 satelites + la Anarquia)", len(spec.countries) == 25, f"hay {len(spec.countries)}")
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
    check("18 states leidos", len(states) == 18, f"leyo {len(states)}")
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
        check("31 focos", len(focuses) == 31, str(len(focuses)))
        by = {pdx.text(f.get("id")): f for f in focuses}
        dyn = by["EFE_dinastia_verde"].get("mutually_exclusive")
        grd = by["EFE_la_guardia_manda"].get("mutually_exclusive")
        check("rutas politicas excluyentes (ida)", pdx.text(dyn.get("focus")) == "EFE_la_guardia_manda")
        check("rutas politicas excluyentes (vuelta)", pdx.text(grd.get("focus")) == "EFE_dinastia_verde")
        war = by["EFE_la_guerra_del_agua"]
        wg = war.get("completion_reward").get("create_wargoal")
        check("la guerra del agua apunta a la FCU", pdx.text(wg.get("target")) == "FCU")
        check("solo si la FCU existe", pdx.text(war.get("available").get("country_exists")) == "FCU")
        check("antes hay que romper el cerco andino",
              pdx.text(war.get("prerequisite").get("focus")) == "EFE_romper_el_cerco_andino")
        heir = by["EFE_el_heredero_del_norte"].get("completion_reward").get("annex_country")
        check("el heredero anexa YYG", pdx.text(heir.get("target")) == "YYG")
        capital_build = by["EFE_ministerio_de_restauracion"].get("completion_reward").get("capital_scope")
        check("fabricas con slots en la capital",
              "add_extra_state_shared_building_slots" in capital_build.keys()
              and pdx.text(capital_build.get("add_building_construction").get("type")) == "industrial_complex")
        check("arbol asignado al EFE", pdx.text(tree.get("country").get("modifier").get("tag")) == "EFE")
        coords = [(pdx.text(f.get("x")), pdx.text(f.get("y"))) for f in focuses]
        check("sin focos superpuestos", len(set(coords)) == len(coords), str(coords))
        for f in focuses:
            fid = pdx.text(f.get("id"))
            for pre in f.get_all("prerequisite"):
                check(f"{fid}: prerequisito existe", pdx.text(pre.get("focus")) in ids)
        corona = next(f for f in focuses if pdx.text(f.get("id")) == "EFE_corona_de_2081")
        check("prerequisitos AND = dos bloques", len(corona.get_all("prerequisite")) == 2)

        amounts = []
        for n in (1, 2, 3):
            f = next(f for f in focuses if pdx.text(f.get("id")) == f"EFE_biosteel_umbral_{n}")
            cond = f.get("available").get("900").get("has_resources_amount")
            check(f"umbral {n} pide biosteel", pdx.text(cond.get("resource")) == "biosteel")
            amounts.append(pdx.text(cond.get("amount")))
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

        resources = pdx.parse((mod / "common/resources/00_resources.txt").read_text()).get("resources")
        check("biosteel es un recurso nuevo", isinstance(resources.get("biosteel"), pdx.Block))
        check("copia los campos del acero", pdx.text(resources.get("biosteel").get("icon_frame")) == "5")
        check("el carbon sigue existiendo", isinstance(resources.get("coal"), pdx.Block))
        text = (mod / "localisation/english/meganations_resources_l_english.yml").read_text(encoding="utf-8-sig")
        check("nombre del recurso", 'biosteel:0 "BioSteel"' in text, text)
        check("clave derivada en mayusculas", 'PRODUCTION_MATERIALS_BIOSTEEL:0 "BioSteel"' in text, text)
        check("no toca el carbon", "coal" not in text, text)
        check("no toca claves que no son del recurso", "TECH_" not in text, text)
        es = (mod / "localisation/spanish/meganations_resources_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("BioSteel en castellano", 'biosteel:0 "Bioacero"' in es, es)
        capital = pdx.parse((mod / "history/states/900-Fixture.txt").read_text()).get("state")
        check("5 de BioSteel en la capital del EFE",
              pdx.text(capital.get("resources").get("biosteel")) == "5", str(capital.get("resources")))
        by2 = {pdx.text(f.get("id")): f for f in focuses}
        add = by2["EFE_biosteel_umbral_1"].get("completion_reward").get("add_resource")
        check("el umbral 1 suma BioSteel en la capital",
              pdx.text(add.get("type")) == "biosteel" and pdx.text(add.get("state")) == "900", str(add))


def test_territory() -> None:
    section("territorio: reparto sobre states vanilla")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build(Path(tmp), vanilla_path=str(FIXTURE_VANILLA), quiet=True)
        mod = ctx.mod_root
        terr = ctx.data["territory"]
        check("Buenos Aires (ARG) -> EFE", terr.get(900) == "EFE", str(terr))
        check("Cordoba (ARG) -> EFE", terr.get(902) == "EFE")
        check("Formosa: el nombre explicito le gana al owner ARG", terr.get(903) == "YYG", str(terr))
        check("Magallanes -> PTA", terr.get(901) == "PTA")
        check("Paraguay (PAR) -> YYG", terr.get(904) == "YYG")
        check("Rio Grande do Sul (BRA) -> EFE", terr.get(905) == "EFE")
        check("Ruhr (GER) -> ASC", terr.get(906) == "ASC")
        check("Italia europea -> NRE", terr.get(909) == "NRE", str(terr))
        check("Libia italiana -> APF por continente", terr.get(910) == "APF")
        check("Corea por core, aunque sea de Japon -> ZKR", terr.get(911) == "ZKR")
        check("Japon -> HSN (los puertos)", terr.get(912) == "HSN")
        check("India -> Anarquia (resto)", terr.get(914) == "ZAN" and terr.get(915) == "ZAN")
        check("Moscu -> Anarquia", terr.get(917) == "ZAN")
        check("state con comparaciones queda afuera del reparto", 907 not in terr)
        check("nadie queda vanilla salvo lo no reescribible",
              all(s.id in terr or s.id == 907 for s in ctx.vanilla.states() if s.owner), str(terr))
        check("Etiopia: el TAG le gana al continente -> ZET", terr.get(913) == "ZET")
        ger = (mod / "history/countries/GER - Germany.txt").read_text()
        check("Alemania sin territorio: sin oob", "oob" not in ger, ger)
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

        units = pdx.parse((mod / "history/units/ZAN_2100.txt").read_text())
        divs = units.get("units").get_all("division")
        check("3 milicias: India contigua, Ceilan y Moscu separadas", len(divs) == 3, str(len(divs)))
        locs = sorted(pdx.text(d.get("location")) for d in divs)
        check("una milicia por territorio, en el state con mas manpower", locs == ["18", "20", "22"], str(locs))
        tpl = units.get("division_template")
        check("plantilla de milicia con 2 infanterias", len(tpl.get("regiments").get_all("infantry")) == 2)
        bal = (Path(tmp) / "balance.txt").read_text()
        check("balance generado fuera del mod", not (mod / "balance.txt").exists() and "BALANCE" in bal)
        check("balance cuenta las milicias", any(l.startswith("ZAN") and l.rstrip().endswith(" 3") for l in bal.splitlines()), bal[:800])
        check("balance incluye el BioSteel inicial", "BioS" in bal)
        check("balance ya no alerta ejercitos vacios", "Sin ejercito inicial" not in bal, bal[-600:])

        section("arranque militar: tecnologias, ejercito, equipo")
        efe_h = (mod / "history/countries/EFE - Ecofascist Empire.txt").read_text()
        techs = pdx.parse(efe_h).get("set_technology")
        keys = set(techs.keys())
        check("meganacion: techs hasta 1942", {"infantry_weapons", "infantry_weapons1", "infantry_weapons2"} <= keys, str(keys))
        check("no recibe techs posteriores", "improved_infantry_weapons" not in keys)
        check("tech sin start_year cuenta como 1936", "tech_support" in keys)
        check("no regala doctrinas", "mobile_warfare" not in keys)
        check("no regala techs excluyentes (xor)", "either_or_tech" not in keys)
        check("no regala variantes sin DLC", "legacy_only_tech" not in keys)
        check("sin popup", pdx.text(techs.get("popup")) == "no")
        pta_h = (mod / "history/countries/PTA - Southern Patagonia.txt").read_text()
        pta_t = set(pdx.parse(pta_h).get("set_technology").keys())
        check("satelite: techs hasta 1940", "infantry_weapons1" in pta_t and "infantry_weapons2" not in pta_t)
        zan_t = set(pdx.parse((mod / "history/countries/ZAN - The Lawless Lands.txt").read_text()).get("set_technology").keys())
        check("anarquia: techs de 1936", "infantry_weapons" in zan_t and "infantry_weapons1" not in zan_t)

        oob = pdx.parse((mod / "history/units/EFE_2100.txt").read_text())
        tpls = [pdx.text(tpl.get("name")) for tpl in oob.get_all("division_template")]
        check("EFE: tres plantillas", tpls == ["Infantería de Línea", "División Motorizada", "División Blindada"], str(tpls))
        divs = oob.get("units").get_all("division")
        check("EFE: divisiones = 6 + IC/4", len(divs) == 6, str(len(divs)))
        check("EFE carga su oob", 'oob = "EFE_2100"' in efe_h)
        stock = {pdx.text(b.get("type")): int(pdx.text(b.get("amount")))
                 for b in pdx.parse(efe_h).get_all("add_equipment_to_stockpile")}
        check("fusiles: la variante mas nueva hasta 1942", "infantry_equipment_3" in stock, str(stock))
        check("fusiles: 400 por division", stock.get("infantry_equipment_3") == 2400, str(stock))
        check("convoyes", "convoy_1" in stock)
        check("avisa arquetipos de equipo que no existen", any("artillery_equipment" in w for w in ctx.warnings))

        section("nombres de 2100 y compensacion industrial")
        st = (mod / "localisation/spanish/replace/meganations_states_l_spanish.yml").read_text(encoding="utf-8-sig")
        check("Buenos Aires se llama Gaia", 'STATE_900:0 "Gaia"' in st, st)
        check("Magallanes es la Custodia Austral", 'STATE_901:0 "Custodia Austral"' in st)
        check("nombres en replace/ (pisan los vanilla)", "replace" in str(mod / "localisation/spanish/replace"))
        check("EFE arranca con Las Cubas de la Pampa", "EFE_cubas_de_la_pampa" in efe_h)
        zan = (mod / "history/countries/ZAN - The Lawless Lands.txt").read_text()
        check("la Anarquia carga su oob", 'oob = "ZAN_2100"' in zan, zan)
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
        check("4 eventos", len(events) == 4, str(len(events)))
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
        check("10 rasgos propios", len(body.keys()) == 10, str(body.keys()))
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
        (docs / "triggers_documentation.md").write_text("### has_resources_amount\n### country_exists\n")
        (docs / "effects_documentation.md").write_text(
            "add_political_power add_stability add_war_support army_experience "
            "add_manpower add_ideas swap_ideas set_autonomy country_event annex_country "
            "create_wargoal add_building_construction add_extra_state_shared_building_slots "
            "add_research_slot add_resource set_technology add_equipment_to_stockpile\n"
        )
        (docs / "modifiers_documentation.md").write_text("\n".join(sorted(mods)))
        (van / "interface").mkdir()
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
