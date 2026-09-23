"""Territorio: reasigna states vanilla a nuestros países (Q007, reskin del mapa).

Produce:
  history/states/<mismo nombre de archivo que vanilla>.txt

Para pisar un state vanilla el archivo del mod tiene que llamarse IGUAL que el
vanilla; con otro nombre el juego carga los dos y el state queda duplicado.
Por eso no se escribe de cero: se lee el archivo vanilla, se cambian dueño y
cores, y se reescribe entero conservando provincias, edificios y demás.

Qué se toca en cada state reasignado:
  - owner      -> el país nuevo
  - controller -> se borra (lo controla el dueño)
  - add_core_of -> solo el país nuevo
  - bloques con fecha (1939.1.1 = {...}) -> se borran. El juego aplica toda
    entrada con fecha anterior al inicio, y arrancamos en 2100: un cambio de
    dueño de 1939 pisaría el nuestro.

BioSteel exclusivo (Q043): en todo state del mundo que NO quede en manos del
EFE, el recurso reskineado se pone en 0 (se borra la entrada).

Seguridad: el parser trata `<` y `>` como `=`. Un archivo que los use no se
reescribe: se avisa y queda vanilla.
"""

from __future__ import annotations

import difflib
import re
import unicodedata

from ..context import BuildContext
from ..errors import SpecError
from ..pdx import Block, banner_for, parse_file
from ..vanilla import StateInfo

SOURCE = "spec/08_territory.yaml (sobre history/states/ vanilla)"

_DATE_KEY = re.compile(r"^\d{1,4}\.\d{1,2}\.\d{1,2}(\.\d{1,2})?$")
_COMPARISON = re.compile(r'"[^"]*"|#[^\n]*|([<>])')


def normalize(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.lower().split())


def display_name(s: StateInfo, names: dict[str, str]) -> str:
    """Nombre en inglés del juego; si falta, el del archivo (278-Buenos Aires.txt)."""
    return names.get(s.name_key) or s.file_label or "?"


def emit(ctx: BuildContext) -> None:
    spec = ctx.spec.raw["territory"]
    territories = spec.get("territories") or {}
    wanted = {tag: t for tag, t in territories.items() if isinstance(t, dict) and isinstance(t.get("resolve"), list)}

    if ctx.vanilla is None:
        if wanted:
            ctx.skip("history/states/", "el reparto se resuelve leyendo los states vanilla y no hay --vanilla-path", "Q035")
        return

    states = ctx.vanilla.states()
    names = ctx.vanilla.state_localisation()
    by_name: dict[str, list[StateInfo]] = {}
    for s in states:
        # Dos fuentes: la localisation y el nombre del archivo. Un state puede
        # buscarse por cualquiera de las dos.
        for shown in {names.get(s.name_key), s.file_label} - {None, ""}:
            bucket = by_name.setdefault(normalize(shown), [])
            if s not in bucket:
                bucket.append(s)

    _check_tags(ctx)
    assignment = _resolve(ctx, wanted, states, names, by_name)
    _fix_vanilla_capitals(ctx, assignment, names)
    ctx.data["territory"] = assignment
    ctx.data["state_names"] = names

    by_id = {s.id: s for s in states}
    for tag in wanted:
        owned = sorted(sid for sid, t in assignment.items() if t == tag)
        listed = ", ".join(f"{display_name(by_id[sid], names)} ({sid})" for sid in owned)
        ctx.note(f"territorio {tag}: {len(owned)} states: {listed or 'ninguno'}")

    exclusive = spec.get("biosteel_exclusive_to")
    resource = _biosteel_resource(ctx) if exclusive else None

    stripped = 0
    for s in states:
        new_owner = assignment.get(s.id)
        strip = bool(resource) and new_owner != exclusive
        if new_owner is None and not strip:
            continue
        _, removed = _rewrite(ctx, s, new_owner, resource if strip else None)
        stripped += removed
    if resource:
        ctx.note(f"BioSteel exclusivo de {exclusive}: '{resource}' quitado de {stripped} states de otros paises")


# ---------------------------------------------------------------------------


# Prioridad de los selectores: un nombre explícito le gana a un TAG o core, y
# un TAG o core le gana a un continente entero. Dentro del mismo nivel, dos
# países pidiendo el mismo state es un error del spec.
_TIER_STATE, _TIER_OWNER, _TIER_CONTINENT = 3, 2, 1


def _resolve(ctx, wanted, states, names, by_name) -> dict[int, str]:
    """state id -> TAG nuevo.

    Selectores (se pueden combinar owner/core con continent, que filtra):
      { owner: ITA }                    states que ITA tiene en vanilla
      { owner: ITA, continent: europe } solo los europeos
      { core: KOR }                     states que son core de KOR
      { continent: africa }             todo un continente
      { state: [nombres] }              un state por nombre
    """
    continents = ctx.vanilla.state_continents()
    claims: dict[int, tuple[int, str]] = {}   # state -> (nivel, TAG)

    def claim(s: StateInfo, tag: str, tier: int) -> None:
        prev = claims.get(s.id)
        if prev is None or prev[0] < tier:
            claims[s.id] = (tier, tag)
        elif prev[0] == tier and prev[1] != tag:
            raise SpecError(
                f"state {s.id} ({display_name(s, names)}) lo piden {prev[1]} y {tag} con la misma prioridad",
                where="08_territory.yaml",
            )

    for tag, terr in wanted.items():
        ctx.spec.country(tag)
        for sel in terr["resolve"]:
            if "state" in sel:
                options = sel["state"] if isinstance(sel["state"], list) else [sel["state"]]
                found = next((by_name[normalize(o)] for o in options if normalize(o) in by_name), None)
                if not found:
                    close = difflib.get_close_matches(normalize(options[0]), list(by_name), n=4, cutoff=0.6)
                    hint = f" Parecidos en el juego: {', '.join(close)}." if close else ""
                    ctx.warn(f"territorio {tag}: no hay ningun state llamado {' / '.join(options)}.{hint}")
                    continue
                for s in found:
                    claim(s, tag, _TIER_STATE)
                continue

            if not any(k in sel for k in ("owner", "core", "continent")):
                raise SpecError(f"territorio {tag}: selector desconocido {sel}", where="08_territory.yaml")
            continent = sel.get("continent")
            matched = []
            for s in states:
                if "owner" in sel and s.owner != sel["owner"]:
                    continue
                if "core" in sel and sel["core"] not in s.cores:
                    continue
                if continent and continents.get(s.id) != continent:
                    continue
                matched.append(s)
            if not matched:
                ctx.warn(f"territorio {tag}: el selector {sel} no encontro ningun state en esta version.")
            tier = _TIER_OWNER if ("owner" in sel or "core" in sel) else _TIER_CONTINENT
            for s in matched:
                claim(s, tag, tier)

    return {sid: tag for sid, (_, tag) in claims.items()}


def _check_tags(ctx: BuildContext) -> None:
    """Nuestros TAG no pueden pisar uno vanilla: el país vanilla desaparece."""
    vanilla_tags = ctx.vanilla.country_tags()
    clash = sorted(c.tag for c in ctx.spec.countries if c.tag in vanilla_tags)
    if clash:
        raise SpecError(
            f"estos TAG ya existen en el juego: {', '.join(clash)}",
            hint="cambialos en 02_countries.yaml (los satelites usan prefijo Z para evitarlo)",
            where="02_countries.yaml",
        )


def _fix_vanilla_capitals(ctx: BuildContext, assignment: dict[int, str], names) -> None:
    """Un país vanilla que pierde su capital pero conserva states necesita otra.

    Se reescribe su history/countries vanilla (mismo nombre de archivo) con la
    capital en el state que le quede con más manpower. El resto del archivo
    queda igual.
    """
    by_id = {s.id: s for s in ctx.vanilla.states()}
    remaining: dict[str, list[StateInfo]] = {}
    for s in ctx.vanilla.states():
        if s.id not in assignment and s.owner:
            remaining.setdefault(s.owner, []).append(s)
    ours = {c.tag for c in ctx.spec.countries}
    for tag, path in ctx.vanilla.country_history_files().items():
        if tag in ours or tag not in remaining:
            continue
        raw = path.read_text(encoding="utf-8-sig", errors="replace")
        m = re.search(r"^\s*capital\s*=\s*(\d+)", raw, re.MULTILINE)
        if not m or int(m.group(1)) not in assignment:
            continue
        best = max(remaining[tag], key=lambda s: (s.manpower, -s.id))
        fixed = raw[: m.start(1)] + str(best.id) + raw[m.end(1):]
        banner = banner_for(f"history/countries/{path.name} vanilla, capital reubicada por 08_territory.yaml")
        ctx.write_text(f"history/countries/{path.name}", banner + fixed)
        ctx.note(f"{tag} perdio su capital: nueva capital {display_name(best, names)} ({best.id})")


def _biosteel_resource(ctx: BuildContext) -> str | None:
    for mech in ctx.spec.raw["mechanics"].get("mechanics", []) or []:
        if mech.get("id") == "biosteel":
            return (mech.get("resource") or {}).get("vanilla_key")
    return None


def _rewrite(ctx: BuildContext, info: StateInfo, owner: str | None, strip_resource: str | None) -> tuple[bool, int]:
    raw = info.path.read_text(encoding="utf-8-sig", errors="replace")
    root = parse_file(info.path)
    state = root.get("state")
    if not isinstance(state, Block):
        return False, 0

    removed = 0
    if strip_resource:
        resources = state.get("resources")
        if isinstance(resources, Block) and strip_resource in resources.keys():
            resources.entries = [(k, v) for k, v in resources.entries if k != strip_resource]
            removed = 1
            if not resources.entries:
                state.entries = [(k, v) for k, v in state.entries if k != "resources"]
    if owner is None and not removed:
        return False, 0

    if any(m.group(1) for m in _COMPARISON.finditer(raw)):
        ctx.warn(
            f"{info.path.name}: usa comparaciones (< o >) y no lo reescribo para no "
            f"cambiarle el sentido. Queda vanilla."
        )
        return False, 0

    if owner is not None:
        history = state.get("history")
        if not isinstance(history, Block):
            history = Block()
            state.add("history", history)
        kept = []
        for k, v in history.entries:
            if k in ("owner", "controller", "add_core_of"):
                continue
            if k and _DATE_KEY.match(k):
                continue
            kept.append((k, v))
        history.entries = [("owner", owner)] + kept + [("add_core_of", owner)]

    ctx.write_script(f"history/states/{info.path.name}", root, source=SOURCE)
    return True, removed
