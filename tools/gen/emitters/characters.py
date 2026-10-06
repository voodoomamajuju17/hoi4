"""Personajes (common/characters/, sintaxis moderna — TN003).

Produce:
  common/characters/<TAG>_characters.txt
  gfx/leaders/<TAG>/<archivo>.dds    retrato placeholder
  localisation del nombre visible

Solo se emiten los personajes con `id` en 03_leaders.yaml. Las entradas sin id
son huecos declarados (Q016): no se inventa un líder para taparlos, el juego
genera uno genérico.

Traits: propios del mod (03_leaders.yaml -> leader_traits), escritos en
  common/country_leader/meganations_traits.txt
Un trait vanilla escrito de memoria rompe la carga si no existe (TN004); uno
propio lo definimos nosotros. Un personaje que pide un trait que no está en
leader_traits frena el build.
"""

from __future__ import annotations

from ..art import write_dds
from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, Quoted

SOURCE = "spec/03_leaders.yaml"
LOC_FILE = "meganations_characters"

LAND_SKILLS = ("skill", "attack_skill", "defense_skill", "planning_skill", "logistics_skill")
NAVY_SKILLS = ("skill", "attack_skill", "defense_skill", "maneuvering_skill", "coordination_skill")

# Tamaño estándar de retrato de líder en HOI4.
PORTRAIT_SIZE = (156, 210)
SMALL_PORTRAIT_SIZE = (65, 67)   # casilla de asesor y alto mando (como un ícono de idea)


def defined_characters(ctx: BuildContext) -> list[dict]:
    return [ch for ch in ctx.spec.raw["leaders"].get("characters", []) or [] if ch.get("id")]


def characters_of(ctx: BuildContext, tag: str) -> list[dict]:
    return [ch for ch in defined_characters(ctx) if ch["country"] == tag]


def leaders_of(ctx: BuildContext, tag: str) -> list[dict]:
    return [
        ch for ch in defined_characters(ctx)
        if ch["country"] == tag and isinstance((ch.get("roles") or {}).get("country_leader"), dict)
    ]


TRAITS_SOURCE = "spec/03_leaders.yaml -> leader_traits"


def _emit_traits(ctx: BuildContext) -> set[str]:
    traits = ctx.spec.raw["leaders"].get("leader_traits") or []
    if not traits:
        return set()
    if ctx.vanilla is not None:
        found = any(
            "leader_traits" in p.read_text(encoding="utf-8-sig", errors="replace")
            for p in (ctx.vanilla.root / "common" / "country_leader").glob("*.txt")
        )
        if not found:
            raise SpecError("common/country_leader/ del juego no usa 'leader_traits': cambio el formato",
                            where="03_leaders.yaml")
    body = Block()
    modifiers_used: dict[str, str] = {}
    for trait in traits:
        tid = trait["id"]
        tb = Block()
        tb.add("random", False)
        for key, value in (trait.get("modifiers") or {}).items():
            if key.startswith("?"):
                # modificador opcional (los de inteligencia son de La Résistance):
                # si el juego no lo documenta, se saltea con aviso
                key = key[1:]
                if ctx.vanilla is not None and ctx.vanilla.documented_keys("modifiers") is not None \
                        and not ctx.vanilla.is_documented("modifiers", key):
                    ctx.warn(f"{tid}: el modificador '{key}' no existe en este juego; se omite.")
                    continue
                tb.add(key, float(value))
                continue
            tb.add(key, float(value))
            modifiers_used.setdefault(key, tid)
        body.add(ctx.loc.reference(tid, f"traits:{tid}"), tb)
        ctx.loc.define(tid, en=trait["name"]["english"], es=trait["name"]["spanish"],
                       file=LOC_FILE, origin=f"traits:{tid}")
    root = Block()
    root.add("leader_traits", body)
    ctx.write_script("common/country_leader/meganations_traits.txt", root, source=TRAITS_SOURCE)
    ctx.verify_keys("modifiers", modifiers_used)
    return {t["id"] for t in traits}


def emit(ctx: BuildContext) -> None:
    known_traits = _emit_traits(ctx)
    xp_rules = {k: v for k, v in (ctx.spec.raw["leaders"].get("advisor_experience") or {}).items() if k != "src"}
    unit_traits = ctx.vanilla.unit_leader_traits() if ctx.vanilla else None
    types, _ = ctx.spec.ideology_index()
    by_country: dict[str, list[dict]] = {}
    for ch in defined_characters(ctx):
        by_country.setdefault(ch["country"], []).append(ch)

    for tag in sorted(by_country):
        country = ctx.spec.country(tag)
        characters = Block()
        for ch in by_country[tag]:
            cid = ch["id"]
            body = Block()
            body.add("name", ctx.loc.reference(cid, f"characters:{cid}"))

            portrait = ch.get("portrait") or {}
            portrait_path = portrait.get("path")
            if not portrait_path and (ctx.spec.root.parent / f"assets/{country.tag}/leaders/{cid}.dds").exists():
                # 2026-10-06: el retrato pedido por tools/arte llega con el id del
                # personaje y se conecta solo, aunque el spec no tenga `portrait`
                portrait_path = f"gfx/leaders/{country.tag}/{cid}.dds"
                roles = {k for k, v in (ch.get("roles") or {}).items() if v}
                portrait = {"path": portrait_path,
                            "role": "navy" if "navy_leader" in roles
                            else "army" if roles & {"corps_commander", "field_marshal"} else "civilian"}
            if portrait_path:
                repo = ctx.spec.root.parent
                name = portrait_path.rsplit('/', 1)[-1]
                own = f"assets/{country.tag}/leaders/{name}"
                small_rel = f"{portrait_path.rsplit('/', 1)[0]}/small/{name}"
                src = portrait.get("asset") or (own if (repo / own).exists() else None)
                if src is None and portrait.get("placeholder", True) is False:
                    # pedido al generador de imágenes (2026-09-29): hasta que llegue,
                    # el juego usa su retrato genérico, no un provisorio del mod
                    src = "skip"
                if src != "skip":
                    if src:
                        # convención de arte (tools/arte): el retrato llegó después
                        ctx.copy_asset(src, portrait_path)
                        small_src = f"{src.rsplit('/', 1)[0]}/small/{name}"
                        if (repo / small_src).exists():
                            ctx.copy_asset(small_src, small_rel)
                        else:
                            _write_portrait(ctx, small_rel, country.color, SMALL_PORTRAIT_SIZE)
                    else:
                        _write_portrait(ctx, portrait_path, country.color)
                        _write_portrait(ctx, small_rel, country.color, SMALL_PORTRAIT_SIZE)
                    sizes = Block()
                    sizes.add("large", Quoted(portrait_path))
                    # el chico explícito: sin él el juego arma "<grande>_small" y, con un
                    # archivo, queda vacío (error.log: Icon definition "_small")
                    sizes.add("small", Quoted(small_rel))
                    portraits = Block()
                    # civilian para lideres de pais, army para militares
                    portraits.add(portrait.get("role", "civilian"), sizes)
                    body.add("portraits", portraits)

            # 2026-10-06 (captura: un ministro con "?" en la casilla de asesores;
            # error.log: Icon definition "_small"): los asesores sin retrato
            # propio no reciben uno genérico del juego. Llevan una silueta en el
            # color de su país hasta que llegue el arte.
            if body.get("portraits") is None and "advisor" in (ch.get("roles") or {}):
                large = f"gfx/leaders/{country.tag}/mn_silueta.dds"
                small = f"gfx/leaders/{country.tag}/small/mn_silueta.dds"
                if not (ctx.mod_root / large).exists():
                    _write_silhouette(ctx, large, country.color, PORTRAIT_SIZE)
                    _write_silhouette(ctx, small, country.color, SMALL_PORTRAIT_SIZE)
                body.add("portraits", Block([("civilian", Block([("large", Quoted(large)), ("small", Quoted(small))]))]))

            leader = (ch.get("roles") or {}).get("country_leader")
            if isinstance(leader, dict):
                ideology = leader.get("ideology")
                if ideology not in types:
                    raise SpecError(
                        f"{cid}: ideologia de lider '{ideology}' no existe en 01_ideologies.yaml",
                        where="03_leaders.yaml",
                    )
                if ideology != country.ideology:
                    ctx.warn(
                        f"{cid} lidera con '{ideology}' pero {tag} arranca en "
                        f"'{country.ideology}'. Ver TN001."
                    )
                role = Block()
                role.add("ideology", ideology)
                traits = Block()
                wanted = leader.get("traits")
                for trait in wanted if isinstance(wanted, list) else []:
                    if trait not in known_traits:
                        raise SpecError(f"{cid}: el trait '{trait}' no esta en leader_traits",
                                        where="03_leaders.yaml")
                    traits.add(None, trait)
                role.add("traits", traits)
                body.add("country_leader", role)

            roles = ch.get("roles") or {}
            for role, keys in (("field_marshal", LAND_SKILLS), ("corps_commander", LAND_SKILLS),
                               ("navy_leader", NAVY_SKILLS)):
                spec_role = roles.get(role)
                if not isinstance(spec_role, dict):
                    continue
                rb = Block()
                traits = Block()
                for trait in spec_role.get("traits") or []:
                    if unit_traits is not None and trait not in unit_traits:
                        ctx.warn(f"{cid}: el rasgo '{trait}' no existe en common/unit_leader/; se omite.")
                        continue
                    traits.add(None, trait)
                rb.add("traits", traits)
                for key in keys:
                    if key not in spec_role:
                        raise SpecError(f"{cid}: {role} sin {key}", where="03_leaders.yaml")
                    rb.add(key, int(spec_role[key]))
                body.add(role, rb)

            advisor = roles.get("advisor")
            if isinstance(advisor, dict):
                ab = Block()
                ab.add("slot", advisor.get("slot", "political_advisor"))
                ab.add("idea_token", cid)
                if advisor.get("ledger"):
                    # alto mando (2026-09-29): ejército, marina o aire en el panel militar
                    ab.add("ledger", advisor["ledger"])
                ab.add("allowed", Block([("original_tag", tag)]))
                traits = Block()
                wanted_traits = list(advisor.get("traits") or [])
                # experiencia por cargo (03_leaders.yaml -> advisor_experience)
                xp = xp_rules.get(advisor.get("slot", "political_advisor"))
                if isinstance(xp, dict):
                    xp = xp.get(advisor.get("ledger") or "army")
                if isinstance(xp, str) and xp not in wanted_traits:
                    wanted_traits.append(xp)
                for trait in wanted_traits:
                    if trait not in known_traits:
                        raise SpecError(f"{cid}: el rasgo de ministro '{trait}' no esta en leader_traits",
                                        where="03_leaders.yaml")
                    traits.add(None, trait)
                ab.add("traits", traits)
                ab.add("cost", int(advisor.get("cost", 150)))
                ab.add("ai_will_do", Block([("factor", float(advisor.get("ai_factor", 1)))]))
                body.add("advisor", ab)

            characters.add(cid, body)

            regnal = (ch.get("name") or {}).get("regnal")
            if not isinstance(regnal, dict):
                raise SpecError(f"{cid}: falta name.regnal en EN y ES", where="03_leaders.yaml")
            ctx.loc.define(cid, en=regnal["english"], es=regnal["spanish"],
                           file=LOC_FILE, origin=f"characters:{cid}")

        root = Block()
        root.add("characters", characters)
        ctx.write_script(f"common/characters/{tag}_characters.txt", root, source=SOURCE)


def _write_silhouette(ctx: BuildContext, relative: str, color: tuple[int, int, int],
                      size: tuple[int, int]) -> None:
    """Silueta de cabeza y hombros sobre un fondo oscuro del color del país."""
    w, h = size
    dark = tuple(int(c * 0.35) for c in color)
    light = tuple(min(255, int(c * 0.6) + 70) for c in color)
    cx, head_y, head_r = w / 2, h * 0.38, min(w, h) * 0.2
    sh_y, sh_rx, sh_ry = h * 0.95, w * 0.42, h * 0.32
    pixels = []
    for y in range(h):
        for x in range(w):
            in_head = (x - cx) ** 2 + (y - head_y) ** 2 <= head_r ** 2
            in_body = y >= h * 0.62 and ((x - cx) / sh_rx) ** 2 + ((y - sh_y) / sh_ry) ** 2 <= 1
            shade = 1 - 0.35 * y / h
            base = tuple(int(c * shade) for c in dark)
            pixels.append(light if in_head or in_body else base)
    path = ctx.mod_root / relative
    write_dds(path, w, h, pixels)
    ctx.track(path)


def _write_portrait(ctx: BuildContext, relative: str, color: tuple[int, int, int],
                    size: tuple[int, int] | None = None) -> None:
    """Retrato placeholder: fondo liso del color del país, con un marco claro.

    Se lee como placeholder a propósito (regla de arte del proyecto).
    """
    w, h = size or PORTRAIT_SIZE
    frame = tuple(min(255, int(c * 1.5) + 40) for c in color)
    pixels = [
        frame if x < 4 or y < 4 or x >= w - 4 or y >= h - 4 else color
        for y in range(h)
        for x in range(w)
    ]
    path = ctx.mod_root / relative
    write_dds(path, w, h, pixels)
    ctx.track(path)
