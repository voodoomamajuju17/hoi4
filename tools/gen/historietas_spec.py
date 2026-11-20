"""La Historieta (spec/46_historietas.yaml, 2026-11-18): la introducción de cada nación en viñetas.

Para cada nación con historieta (y con su página ya armada en assets/historietas/paginas/<TAG>.dds):
  - la introducción ("<Nación> en 2100", el evento on_startup cuyo texto empieza con THE WORLD IN 2100)
    queda oculta: al jugador le pone la bandera MN_historieta_abierta (se abre la ventana); a la IA le
    manda directo lo que sigue;
  - los otros avisos visibles del arranque de esa nación (la mecánica propia) dejan de salir solos:
    los manda el botón de la historieta (MN_historieta_cerrar_<TAG>) o, en la IA, la introducción.
Devuelve las historietas con lo que el armado necesita (titulo, sigue).
"""

from __future__ import annotations

from pathlib import Path

from .errors import SpecError

REPO = Path(__file__).resolve().parents[2]
FLAG = "MN_historieta_abierta"


def pagina(tag: str) -> Path:
    return REPO / "assets" / "historietas" / "paginas" / f"{tag}.dds"


def expandir(raw: dict, historietas: dict) -> dict:
    from . import historietas_geo
    spaces = (raw.get("events") or {}).get("namespaces") or {}
    out = {}
    for tag, cfg in historietas.items():
        if len(cfg.get("vinetas") or []) > 8:
            raise SpecError(f"historieta {tag}: más de 8 viñetas", where="46_historietas.yaml")
        historietas_geo.pagina(cfg)   # que la geometría cierre
        cfg = dict(cfg)
        intro, sigue = None, []
        for ns, n in spaces.items():
            if n.get("country") != tag:
                continue
            for ev in n.get("events") or []:
                if ev.get("trigger") != "on_startup" or ev.get("hidden"):
                    continue
                if "THE WORLD IN 2100" in str((ev.get("desc") or {}).get("english", "")):
                    intro = (ns, ev)
                else:
                    sigue.append((ns, ev))
        if cfg.get("sin_intro"):
            # Japón y Albión (2026-11-20): sin introducción; la abre el arranque descolonizado
            # (28_descolonizado: MN_historieta_abierta al jugador)
            cfg["intro"], cfg["sigue"] = None, []
            cfg["activa"] = pagina(tag).exists()
            out[tag] = cfg
            continue
        if intro is None:
            raise SpecError(f"historieta {tag}: no encuentro su introducción (on_startup, THE WORLD IN 2100)",
                            where="46_historietas.yaml")
        ns, ev = intro
        cfg["titulo"] = ev["title"]
        cfg["intro"] = f"{ns}.{ev['id']}"
        cfg["sigue"] = [f"{s_ns}.{s_ev['id']}" for s_ns, s_ev in sigue]
        cfg["activa"] = pagina(tag).exists()
        out[tag] = cfg
        if not cfg["activa"]:
            continue   # sin página no hay ventana: la introducción queda como estaba
        ev["hidden"] = True
        opts = ev.get("options") or [{"name": {"english": "OK", "spanish": "Entendido."}, "effects": []}]
        mandar = [{"effect": "event", "id": e, "days": 0} for e in cfg["sigue"]]
        opts[0] = dict(opts[0], effects=list(opts[0].get("effects") or []) + [
            {"effect": "if", "when": {"is_ai": True}, "then": mandar or [{"effect": "add_political_power", "value": 0}],
             "else": [{"effect": "flag", "value": FLAG}]}])
        ev["options"] = opts[:1]
        for _s_ns, s_ev in sigue:
            s_ev["trigger"] = "effect"
    return out
