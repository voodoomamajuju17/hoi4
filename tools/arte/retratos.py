"""Pedido de retratos en el estilo nuevo (2026-09-29): retrato fotorrealista
pintado, como los de Lin Wenzhao y Zhou Mingyuan (SHD). Escribe dos txt con
todos los retratos del mod que no estén hechos en el estilo nuevo (DONE_V2):

  arte/retratos_v2_MEGANACIONES.txt
  arte/retratos_v2_SATELITES_Y_ANARQUIA.txt

  python -m tools.arte.retratos

Los archivos que vuelven se llaman <id>.png y se importan igual que siempre
(python -m tools.arte.arte importar <zip>): reemplazan al retrato anterior.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
MEGAS = ["EFE", "FCU", "ASC", "HSN", "NAS", "SHD", "APF", "NRE"]
ROLES = {"civilian": "", "army": "military ", "navy": "naval ", "air": "air force "}

STYLE = (
    "Photorealistic painted portrait in the style of a modern Hearts of Iron IV leader portrait: "
    "head and shoulders, three-quarter or front view, looking at the viewer, realistic skin and fabric, "
    "soft studio key light, shallow depth of field, detailed but slightly softened background related to "
    "the nation, cinematic and believable, year 2100 near-future clothing (not sci-fi costume). "
    "Vertical 156x210 proportion (for example 624x840). No text, no letters, no logos with words, no watermark, "
    "no frame, no border."
)

NATION = {
    "EFE": ("Ecofascist Empire (South America, Buenos Aires)",
            "green and gold palette; living bio-steel details, laurels and leaves on uniforms; background of "
            "jungle-covered cities, bio-vats or reforested pampas; Latin American faces"),
    "FCU": ("Free Corporative Capital Union (North America, corporate state)",
            "navy blue, silver and white; tailored corporate suits or sleek private-military uniforms; "
            "background of glass towers, trading floors or boardrooms"),
    "ASC": ("Automated Socialist Commune (northern Europe, run by AI and councils)",
            "red and white constructivist accents over grey; functional work clothes or plain uniforms; "
            "background of data centres, robotic factories or server halls; European faces"),
    "HSN": ("High Seas Market Nation (Southeast Asia and Japan, maritime trade)",
            "teal and brass; naval officer coats or merchant captain jackets; background of container "
            "ports, ships and straits; East and Southeast Asian faces"),
    "NAS": ("NeoAndean Sky Kingdom (Andes, reborn Inca solar monarchy)",
            "gold and turquoise; Andean textiles and modern high-altitude uniforms, sun motifs; "
            "background of snowy Andes, stone terraces and solar temples; Andean faces"),
    "SHD": ("Sino-Harmonious Directorate (China, hydraulic technocracy)",
            "jade green and steel grey, modern mandarin-collar technical uniforms with a small water-ripple pin; "
            "background of dams, flood gates or hydraulic control rooms; Chinese faces; "
            "AVOID red, sun rays and communist symbols"),
    "APF": ("African Peoples' Federation (continental council federation)",
            "earth red, yellow and green; modern clothing with kente-like patterns or practical militia uniforms; "
            "background of savanna cities, assembly halls or new industry; African faces"),
    "NRE": ("Neo-Roman Empire (Italy and France, restored Rome)",
            "crimson, purple and gold; modern uniforms with Roman details (eagles, laurels, cloaks); "
            "background of marble forums, legions and standards; Mediterranean faces"),
}
OTHER = ("a client state or warlord faction of the ruined 2100 world",
         "muted colours, improvised or worn uniforms, local clothing of its region; background of its region "
         "(bunkers, ruins, frontier towns, deserts, jungle or steppe as fits)")


# ya hechos en el estilo nuevo (no se vuelven a pedir)
DONE_V2 = {"APF_amara_nwosu", "APF_gen_bello_1", "APF_gen_njoroge_2", "APF_kwame_diallo",
           "ASC_allocation_council", "ASC_min_brandt_1", "ASC_min_wolski_2", "ASC_plan_41",
           "EFE_anahi_quiroga", "EFE_aurelio_iv", "EFE_bruno_etchegaray", "EFE_min_arriagada_1",
           "EFE_min_vidal_2", "FCU_marcus_rourke", "FCU_min_okafor_2", "FCU_min_whitmore_1",
           "FCU_valeria_castellane", "HSN_gen_arakawa_1", "HSN_gen_lan_2", "HSN_ines_tavake",
           "HSN_kofi_aldana", "HSN_min_faleolo_2", "HSN_min_sato_lee_1", "NAS_amaru_inca", "NAS_amaru_quispe",
           "NAS_gen_choque_2", "NAS_gen_rimac_1", "NAS_min_huaman_2", "NAS_min_mamani_1",
           "NRE_gen_constantin_1", "NRE_gen_petrescu_2", "NRE_irina_vasilescu", "NRE_kerem_aydin",
           "NRE_legado_arbogast", "NRE_lucius_varro", "SHD_gen_yunfeng_1", "SHD_lin_wenzhao", "SHD_min_hao_1",
           "SHD_min_jing_2", "SHD_zhou_mingyuan"}


def _load(name: str) -> dict:
    return yaml.safe_load((REPO / "spec" / name).read_text(encoding="utf-8"))


def _one_line(text) -> str:
    return " ".join(str(text or "").split())


def requests() -> dict[str, list[str]]:
    countries = _load("02_countries.yaml")
    names = {c["tag"]: c["name"]["english"]
             for key in ("major_powers", "subjects", "independents") for c in countries.get(key) or []}
    out: dict[str, list[str]] = {"MEGANACIONES": [], "SATELITES_Y_ANARQUIA": []}
    for ch in _load("03_leaders.yaml").get("characters") or []:
        portrait = ch.get("portrait") or {}
        if not portrait.get("path"):
            continue
        tag = ch["country"]
        regnal = (ch.get("name") or {}).get("regnal") or {}
        who = regnal.get("english", ch["id"])
        roles = ch.get("roles") or {}
        if "country_leader" in roles:
            job = "head of state"
        elif "field_marshal" in roles:
            job = "field marshal"
        elif "corps_commander" in roles:
            job = "general"
        elif "navy_leader" in roles:
            job = "admiral"
        elif roles.get("advisor"):
            slot = roles["advisor"].get("slot", "")
            job = {"army_chief": "chief of the army", "navy_chief": "chief of the navy", "air_chief": "chief of the air force",
                   "high_command": "high command officer", "theorist": "government minister and theorist",
                   "political_advisor": "government minister"}.get(slot, "government minister")
        else:
            job = ROLES.get(portrait.get("role", "civilian"), "") + "official"
        nation, look = NATION.get(tag, OTHER)
        if tag not in NATION:
            nation = f"{names.get(tag, tag)}, {OTHER[0]}"
        if ch["id"] in DONE_V2:
            continue
        lore = _one_line(ch.get("lore")) or _one_line(portrait.get("description"))
        if not lore and ch.get("biography"):
            civil = (ch.get("name") or {}).get("civil")
            steps = "; ".join(str(b.get("event")) + (f" ({b['date']})" if b.get("date") not in (None, "unknown") else "")
                              for b in ch["biography"])
            lore = (f"Born {civil}. " if civil else "") + f"Life: {steps}."
        born = f", born {ch['born']}" if ch.get("born") else ""
        block = "\n".join([
            "ASSET_REQUEST",
            "type: leader_portrait",
            f"id: {ch['id']}",
            f"filename: {ch['id']}.png",
            "size: 156x210 (o más grande con la misma proporción, por ejemplo 624x840)",
            f"style: {STYLE}",
            f"nation: {nation}; {look}",
            f"description: {who}{born}, {job} of {names.get(tag, tag)}. {lore}",
            "transparent_background: false",
            "",
        ])
        out["MEGANACIONES" if tag in MEGAS else "SATELITES_Y_ANARQUIA"].append(block)
    return out


HEADER = """RETRATOS v2 - 2100 MEGANATIONS ({n} retratos)
=================================================

Estilo nuevo: retrato FOTORREALISTA PINTADO, como los de Lin Wenzhao y Zhou Mingyuan
(busto, luz suave de estudio, fondo de su nación desenfocado, ropa realista de 2100).

Para ChatGPT:
- Cada bloque ASSET_REQUEST es UNA imagen, vertical (proporción 156x210, por ejemplo 624x840).
- Guardar cada imagen con el nombre de `filename` EXACTO (el id + .png).
- Mismo estilo en todas; los colores y el fondo cambian por nación (ver `nation`).
- Sin texto, sin letras, sin marcos.

Para devolver: juntarlas en un .zip y pasárselo a Claude. Reemplazan a los retratos actuales.

"""


def main() -> None:
    for group, blocks in requests().items():
        path = REPO / "arte" / f"retratos_v2_{group}.txt"
        path.write_text(HEADER.format(n=len(blocks)) + "\n".join(blocks), encoding="utf-8")
        print(f"{path.relative_to(REPO)}: {len(blocks)}")


if __name__ == "__main__":
    main()
