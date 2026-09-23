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
  - add_claim_by, start_resistance, add_resistance -> se borran (apuntan a
    países de 1936)
  - bloques con fecha (1939.1.1 = {...}) -> se borran. El juego aplica toda
    entrada con fecha anterior al inicio, y arrancamos en 2100: un cambio de
    dueño de 1939 pisaría el nuestro.

Yacimientos iniciales de recursos propios (06_mechanics.yaml ->
starting_deposits): se agregan al bloque `resources` del state (hoy: 5 de
BioSteel en la capital del EFE). El carbón vanilla no se toca.

Capitales: se resuelven acá (capital_of) porque las necesitan la historia de
países y los efectos de foco que agregan recursos en la capital.

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

# Del bloque history de un state reasignado se sacan el dueño, el
# controlador y los cores vanilla (se ponen los nuestros), y lo que apunta a
# países que en 2100 no existen: resistencia y reclamos. En 1.19.3
# Dalmatia tiraba "start_resistance ... is not a core".
_DROP_FROM_HISTORY = {
    "owner", "controller", "add_core_of", "add_claim_by",
    "start_resistance", "add_resistance", "add_resistance_target",
}

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
    # Un state cuyo archivo no se puede reescribir sin riesgo queda con su
    # dueño vanilla: se lo saca del reparto ANTES de calcular capitales, para
    # que ese dueño conserve una capital válida.
    by_path = {s.id: s for s in states}
    for sid in sorted(assignment):
        if _unsafe(by_path[sid]):
            ctx.warn(
                f"{by_path[sid].path.name}: usa comparaciones (< o >) y no lo reescribo para no "
                f"cambiarle el sentido. Queda de {by_path[sid].owner}, no de {assignment[sid]}."
            )
            del assignment[sid]
    _fix_vanilla_capitals(ctx, assignment, names)
    _stub_landless_vanilla(ctx, assignment)
    ctx.data["territory"] = assignment
    ctx.data["state_names"] = names

    by_id = {s.id: s for s in states}
    for tag in wanted:
        owned = sorted(sid for sid, t in assignment.items() if t == tag)
        shown = [f"{display_name(by_id[sid], names)} ({sid})" for sid in owned[:12]]
        more = f" y {len(owned) - 12} mas" if len(owned) > 12 else ""
        ctx.note(f"territorio {tag}: {len(owned)} states: {', '.join(shown) or 'ninguno'}{more}")
    remainder = next((tag for tag, terr in wanted.items()
                      if any(sel.get("remainder") for sel in terr["resolve"])), None)
    if remainder:
        rest = sum(1 for t in assignment.values() if t == remainder)
        total = len(assignment)
        ctx.note(f"reparto: {total - rest} states en meganaciones y satelites, "
                 f"{rest} en {remainder} ({100 * rest // max(total, 1)}% del mundo)")

    by_state = {s.id: s for s in states}
    capitals = {}
    for c in ctx.spec.countries:
        cap = capital_of(ctx, c.tag, assignment, names, by_state)
        if cap is not None:
            capitals[c.tag] = cap
    ctx.data["capitals"] = capitals

    _rename_states(ctx, by_name)
    deposits = _starting_deposits(ctx, capitals)
    ctx.data["deposits"] = deposits
    for s in states:
        new_owner = assignment.get(s.id)
        if new_owner is None and s.id not in deposits:
            continue
        _rewrite(ctx, s, new_owner, deposits.get(s.id, {}))


def _rename_states(ctx: BuildContext, by_name) -> None:
    """Nombres de 2100: pisan STATE_<id> desde localisation/<idioma>/replace/."""
    renames = (ctx.spec.raw["territory"].get("state_names") or {}).get("renames") or []
    done = 0
    for entry in renames:
        options = entry["state"]
        found = next((by_name[normalize(o)] for o in options if normalize(o) in by_name), None)
        if not found:
            ctx.warn(f"nombres: no hay ningun state llamado {' / '.join(options)}; no se renombra.")
            continue
        for s in found:
            if not s.name_key:
                continue
            ctx.loc.define_and_reference(
                s.name_key, en=entry["name"]["english"], es=entry["name"]["spanish"],
                file="replace/meganations_states", origin=f"state_names:{options[0]}",
            )
            done += 1
    if done:
        ctx.note(f"nombres de 2100: {done} states renombrados")


def capital_of(ctx, tag, assignment, names, by_state) -> int | None:
    """Capital: la del spec (capital_state) si es propia; si no, la de más manpower."""
    owned = [sid for sid, t in assignment.items() if t == tag]
    if not owned:
        return None
    terr = (ctx.spec.raw["territory"].get("territories") or {}).get(tag) or {}
    wanted = terr.get("capital_state")
    if wanted:
        options = {normalize(w) for w in wanted}
        for sid in sorted(owned):
            s = by_state.get(sid)
            if s and options & {normalize(n) for n in (names.get(s.name_key), s.file_label) if n}:
                return sid
        ctx.warn(f"{tag}: la capital {' / '.join(wanted)} no esta entre sus states; uso la de mas manpower.")
    best = max(owned, key=lambda sid: (by_state[sid].manpower if sid in by_state else 0, -sid))
    if not wanted:
        shown = display_name(by_state[best], names) if best in by_state else "?"
        ctx.note(f"{tag}: capital provisoria {shown} ({best}), la de mas manpower.")
    return best


def _starting_deposits(ctx, capitals) -> dict[int, dict[str, int]]:
    out: dict[int, dict[str, int]] = {}
    for mech in ctx.spec.raw["mechanics"].get("mechanics", []) or []:
        res = mech.get("resource")
        if not isinstance(res, dict) or res.get("strategy") != "new_resource":
            continue
        for dep in res.get("starting_deposits", []) or []:
            if dep.get("state") != "capital":
                raise SpecError("starting_deposits: por ahora solo state: capital", where="06_mechanics.yaml")
            sid = capitals.get(dep["country"])
            if sid is None:
                ctx.warn(f"{dep['country']} no tiene capital: no recibe su yacimiento de {res['key']}.")
                continue
            out.setdefault(sid, {})[res["key"]] = int(dep["amount"])
            ctx.note(f"{res['key']}: {dep['amount']} en la capital de {dep['country']} (state {sid})")
    return out


# ---------------------------------------------------------------------------


# Prioridad de los selectores, de mayor a menor: nombre explícito, core, TAG
# dueño, continente, resto. El core le gana al dueño porque es más específico
# (Corea es core de KOR aunque en 1936 la tenga Japón). Dentro del mismo nivel,
# dos países pidiendo el mismo state es un error del spec.
_TIER_STATE, _TIER_CORE, _TIER_OWNER, _TIER_CONTINENT = 4, 3, 2, 1


def _resolve(ctx, wanted, states, names, by_name) -> dict[int, str]:
    """state id -> TAG nuevo.

    Selectores (se pueden combinar owner/core con continent, que filtra):
      { owner: ITA }                    states que ITA tiene en vanilla
      { owner: ITA, continent: europe } solo los europeos
      { core: KOR }                     states que son core de KOR
      { continent: africa }             todo un continente
      { state: [nombres] }              un state por nombre
      { remainder: true }               todo lo que no pidió nadie (uno solo)
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

    remainder_tag = None
    for tag, terr in wanted.items():
        ctx.spec.country(tag)
        for sel in terr["resolve"]:
            if sel.get("remainder"):
                if remainder_tag and remainder_tag != tag:
                    raise SpecError(f"remainder pedido por {remainder_tag} y {tag}", where="08_territory.yaml")
                remainder_tag = tag
                continue
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
            tier = _TIER_CORE if "core" in sel else _TIER_OWNER if "owner" in sel else _TIER_CONTINENT
            for s in matched:
                claim(s, tag, tier)

    if remainder_tag:
        # Solo states con dueño en vanilla: los que no tienen dueño son
        # tierra de nadie a propósito (algunos islotes del juego).
        for s in states:
            if s.id not in claims and s.owner:
                claims[s.id] = (0, remainder_tag)

    return {sid: tag for sid, (_, tag) in claims.items()}


def _unsafe(info: StateInfo) -> bool:
    """El parser trata < y > como =: reescribir un archivo con comparaciones
    le cambiaría el sentido."""
    raw = info.path.read_text(encoding="utf-8-sig", errors="replace")
    return any(m.group(1) for m in _COMPARISON.finditer(raw))


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


# Lo único que se conserva de la historia de un país vanilla que quedó sin
# territorio: lo que necesita un país liberable (capital, gobierno).
_STUB_KEYS = ("capital", "set_politics", "set_popularities")


def _stub_landless_vanilla(ctx: BuildContext, assignment: dict[int, str]) -> None:
    """Deja en su mínimo la historia de los países vanilla sin territorio.

    Arrancando en 2100 el juego ejecuta TODA la historia vanilla: ejércitos
    (oob), flotas, aviones, personajes y cada bloque con fecha (1939.1.1...).
    Para un país que ya no tiene ni un state eso coloca unidades y ejecuta
    anexiones sobre territorio ajeno; en 1.19.3 terminó en un crash
    (EXCEPTION_ACCESS_VIOLATION durante "Executing History ... to 2100").
    Se reescribe su archivo con el mismo nombre, como el de un país liberable.
    """
    owners_left = {s.owner for s in ctx.vanilla.states() if s.id not in assignment and s.owner}
    ours = {c.tag for c in ctx.spec.countries}
    stubbed = 0
    for tag, path in ctx.vanilla.country_history_files().items():
        if tag in ours or tag in owners_left:
            continue
        stub = Block()
        try:
            vanilla = parse_file(path)
            for key in _STUB_KEYS:
                value = vanilla.get(key)
                if value is not None:
                    stub.add(key, value)
        except ValueError:
            # No parsea (en 1.19.3: NOR - Norway.txt). Quedarse con la
            # historia entera es peor: ejecuta focos y crea unidades de 1936.
            # Se rescata solo la capital con una búsqueda de texto.
            raw = path.read_text(encoding="utf-8-sig", errors="replace")
            m = re.search(r"^\s*capital\s*=\s*(\d+)", raw, re.MULTILINE)
            if m:
                stub.add("capital", int(m.group(1)))
            ctx.warn(f"{path.name}: no parsea; se reduce a la capital sola.")
        ctx.write_script(
            f"history/countries/{path.name}", stub,
            source=f"history/countries/{path.name} vanilla, reducido: el pais no tiene territorio en 2100",
        )
        stubbed += 1
    if stubbed:
        ctx.note(f"{stubbed} paises vanilla sin territorio: historia reducida a capital y gobierno")


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


def _rewrite(ctx: BuildContext, info: StateInfo, owner: str | None, add_resources: dict[str, int]) -> bool:
    if _unsafe(info):
        return False
    root = parse_file(info.path)
    state = root.get("state")
    if not isinstance(state, Block):
        return False

    if add_resources:
        resources = state.get("resources")
        if not isinstance(resources, Block):
            resources = Block()
            state.add("resources", resources)
        for key, amount in add_resources.items():
            resources.entries = [(k, v) for k, v in resources.entries if k != key]
            resources.add(key, amount)

    if owner is not None:
        history = state.get("history")
        if not isinstance(history, Block):
            history = Block()
            state.add("history", history)
        kept = []
        for k, v in history.entries:
            if k in _DROP_FROM_HISTORY:
                continue
            if k and _DATE_KEY.match(k):
                continue
            kept.append((k, v))
        history.entries = [("owner", owner)] + kept + [("add_core_of", owner)]

    ctx.write_script(f"history/states/{info.path.name}", root, source=SOURCE)
    return True
