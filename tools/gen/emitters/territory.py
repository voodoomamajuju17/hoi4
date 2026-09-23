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
from ..pdx import Block, parse_file
from ..vanilla import StateInfo

SOURCE = "spec/08_territory.yaml (sobre history/states/ vanilla)"

_DATE_KEY = re.compile(r"^\d{1,4}\.\d{1,2}\.\d{1,2}(\.\d{1,2})?$")
_COMPARISON = re.compile(r'"[^"]*"|#[^\n]*|([<>])')


def normalize(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.lower().split())


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
        shown = names.get(s.name_key)
        if shown:
            by_name.setdefault(normalize(shown), []).append(s)

    assignment = _resolve(ctx, wanted, states, names, by_name)
    ctx.data["territory"] = assignment
    ctx.data["state_names"] = names

    by_id = {s.id: s for s in states}
    for tag in wanted:
        owned = sorted(sid for sid, t in assignment.items() if t == tag)
        listed = ", ".join(f"{names.get(by_id[sid].name_key, '?')} ({sid})" for sid in owned)
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


def _resolve(ctx, wanted, states, names, by_name) -> dict[int, str]:
    """state id -> TAG nuevo. Los `state` explícitos le ganan a los `owner`."""
    by_owner: dict[str, list[StateInfo]] = {}
    for s in states:
        if s.owner:
            by_owner.setdefault(s.owner, []).append(s)

    explicit: dict[int, str] = {}
    broad: dict[int, str] = {}
    for tag, terr in wanted.items():
        ctx.spec.country(tag)
        for sel in terr["resolve"]:
            if "owner" in sel:
                owned = by_owner.get(sel["owner"], [])
                if not owned:
                    ctx.warn(f"territorio {tag}: el TAG vanilla '{sel['owner']}' no tiene states en esta version.")
                for s in owned:
                    prev = broad.get(s.id)
                    if prev and prev != tag:
                        raise SpecError(
                            f"state {s.id} lo piden por dueño {prev} y {tag}", where="08_territory.yaml"
                        )
                    broad[s.id] = tag
            elif "state" in sel:
                options = sel["state"] if isinstance(sel["state"], list) else [sel["state"]]
                found = next((by_name[normalize(o)] for o in options if normalize(o) in by_name), None)
                if not found:
                    close = difflib.get_close_matches(normalize(options[0]), list(by_name), n=4, cutoff=0.6)
                    hint = f" Parecidos en el juego: {', '.join(close)}." if close else ""
                    ctx.warn(f"territorio {tag}: no hay ningun state llamado {' / '.join(options)}.{hint}")
                    continue
                for s in found:
                    prev = explicit.get(s.id)
                    if prev and prev != tag:
                        raise SpecError(
                            f"state {s.id} ({names.get(s.name_key)}) lo piden por nombre {prev} y {tag}",
                            where="08_territory.yaml",
                        )
                    explicit[s.id] = tag
            else:
                raise SpecError(f"territorio {tag}: selector desconocido {sel}", where="08_territory.yaml")
    return {**broad, **explicit}


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
