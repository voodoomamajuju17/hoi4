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
    check("10 paises", len(spec.countries) == 10, f"hay {len(spec.countries)}")
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
    check("2 states leidos", len(states) == 2, f"leyo {len(states)}")
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
        check("sin replace_path prematuro", "replace_path" not in descriptor, descriptor)

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
