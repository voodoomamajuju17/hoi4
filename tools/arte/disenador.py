"""Íconos del diseñador de equipo, de nuevo y sin referencia (2026-11-06).

Pedido: "no me gustan las imágenes de las partes/equipo del diseñador. Están
DEMASIADO iguales a las referencias y pareciera además que las referencias
confunden bastante al generador. Haceme otro txt con nuevos pedidos ...
Priorizar originalidad / rigurosidad del lore, época, lo que ya sabés sobre el
equipo y sus diseños."

Cada módulo del juego (arte/iconos_juego.yaml, familia disenador) se
reinterpreta como la pieza de 2100 que lo reemplaza en el mundo del mod: después
del Gran Desarme, con fábricas reconstruidas, drones en todas partes, railguns,
láseres de defensa, motores de hidrógeno y cerámica compuesta. Va SIN imagen de
referencia (el ícono viejo confundía al generador) y con una descripción propia.
Los íconos son genéricos (no de una facción): diseño neutro de 2100.
"""

from __future__ import annotations

from pathlib import Path

import re

# (patrón sobre el "que" del ícono, lo que muestra en 2100). El primero que coincide gana.
REGLAS: list[tuple[str, str]] = [
    # --- huecos y estados
    (r"^unknown$", "a sealed equipment crate with a single question-shaped glowing seam of light on its lid (no letters)"),
    (r"^empty$", "an empty modular mounting socket: a square hardpoint frame with four locking claws open and nothing inside"),
    (r"^locked$", "a mounting hardpoint closed by a heavy circular blast shutter with a padlock-shaped magnetic clamp"),
    (r"custom slot", "an open universal hardpoint rail with standard quick-release clamps, ready for any module"),
    (r"plane role module", "a swappable mission pod: a sleek streamlined underwing canister with an access hatch"),
    (r"plane special module electronics", "a compact avionics brick with heat-sink fins and a bundle of fibre-optic cables"),
    (r"tank special module", "a boxy add-on equipment module with mounting lugs and a small sensor dome"),
    (r"tank radio module", "a vehicle mesh-network communications box with a short flexible antenna"),
    # --- barcos (huecos fijos)
    (r"ship anti air", "a naval point-defence turret: a compact laser emitter dome beside a short rotary cannon"),
    (r"ship armor", "a thick curved section of layered ceramic-composite hull armour, seen edge-on to show its layers"),
    (r"ship battery", "a naval railgun turret: a flat angular turret with two long parallel rail barrels"),
    (r"ship deck space", "an empty flight-deck square with landing markings and a recessed elevator outline"),
    (r"ship engine", "a marine gas-turbine and electric drive block with a large pump-jet intake ring"),
    (r"ship fire control", "a ship's fire-control mast: a stacked tower of flat phased-array panels"),
    (r"ship radar", "a tall naval radar mast with four flat phased-array faces"),
    (r"ship secondaries", "a small secondary turret with a single fast-firing gun and a sensor ball"),
    (r"ship torpedo", "a triple launcher of sleek supercavitating torpedoes"),
    # --- aviones: motores
    (r"rocket engine", "a compact rocket booster pack with {n} bell nozzles and fuel lines"),
    (r"jet engine axial", "{n} slim axial-flow hydrogen turbofan nacelle(s) with visible fan blades in the intake"),
    (r"jet engine", "{n} short ducted turbojet nacelle(s) with a glowing ring exhaust"),
    (r"quad large plane jet engine type", "four large wing-mounted hydrogen turbofans on a heavy wing section"),
    (r"large plane jet engine type", "a large high-bypass hydrogen turbofan pod under a wing section"),
    (r"medium plane jet engine type", "a mid-size turbofan nacelle blended into a wing root"),
    (r"twin plane jet engine type", "two side-by-side turbofan nacelles on a short wing"),
    (r"plane jet engine type", "a single sleek jet nacelle with a variable exhaust nozzle"),
    (r"quad large plane engine type", "four large open-rotor propfans with curved scimitar blades on a heavy wing"),
    (r"large plane engine type", "a large contra-rotating propfan engine with curved blades"),
    (r"medium plane engine type", "a mid-size electric ducted-fan engine with a cooling grille"),
    (r"twin plane engine type", "two electric ducted-fan engines on a short wing section"),
    (r"plane engine type", "a single electric ducted-fan engine with a five-bladed fan"),
    (r"^engine (\d)", "{n} {tier} hydrogen-electric ducted fan(s) in streamlined pods"),
    # --- aviones: armas y equipo
    (r"large aircraft cannon", "{n} heavy aircraft railgun barrel(s) under a fuselage section, with capacitor housings"),
    (r"aircraft cannon", "{n} {tier} aircraft autocannon(s): short electromagnetic coilgun barrels with ammunition belts"),
    (r"heavy mg", "{n} heavy rotary guns in a streamlined gun pack"),
    (r"light mg", "{n} light rotary guns in a slim wing pod"),
    (r"cannon defense turret", "{n} remote-controlled defensive cannon turret(s) with a sensor eye, no gunner"),
    (r"hmg defense turret", "{n} remote-controlled heavy gun turret(s) on a fuselage ring, no gunner"),
    (r"lmg defense turret", "{n} small remote gun turret(s) with a camera ball, no gunner"),
    (r"air air radar", "an {tier} air-to-air radar: a nose cone opened to show a flat round phased-array disc"),
    (r"air ground radar", "an {tier} ground-mapping radar: a long belly pod with a side-looking array strip"),
    (r"radio navigation", "an {tier} satellite-navigation unit: a small dome antenna on a circuit block"),
    (r"recon camera", "a reconnaissance sensor pod with a multi-lens camera turret"),
    (r"guided anti ship missile", "a sea-skimming anti-ship missile with small cruciform fins and a seeker nose"),
    (r"armor piercing bomb locks", "a pylon holding a pointed penetrator bomb with a hardened nose"),
    (r"heavy bomb locks", "a heavy pylon holding one large glide bomb with folding wings"),
    (r"bomb locks", "a wing pylon with two small precision glide bombs"),
    (r"earthshaker bomb release", "a massive streamlined deep-penetration bomb with a spiral tail, hanging in release clamps"),
    (r"improved rocket propelled bombs", "a cluster of guided rocket-boosted bombs with folding fins"),
    (r"rocket propelled bombs", "two rocket-boosted bombs with exhaust bells at the tail"),
    (r"rocket rails", "a launcher rail with four small guided rockets"),
    (r"bomb sights", "an {tier} targeting pod: a pod with a rotating optical-laser ball"),
    (r"large bomb bay", "an open large internal weapons bay seen from below, with a rotary launcher of bombs"),
    (r"medium bomb bay", "an open internal weapons bay with a row of guided bombs"),
    (r"small bomb bay", "a small internal weapons bay with two compact guided bombs"),
    (r"tank buster", "an {tier} anti-armour gun pod: a long single-barrel railgun pod with a muzzle brake"),
    (r"torpedo mounting", "an {tier} air-launched torpedo with a parachute pack and seeker nose, on a pylon"),
    (r"airdropped mines", "a pylon with smart sea mines that deploy their own little parachutes"),
    (r"drop tanks", "two conformal external hydrogen tanks shaped to hug a wing"),
    (r"self sealing fuel tanks", "a fuel cell wrapped in a self-healing gel bladder, cut away to show its layers"),
    (r"expanded fuel tank|fuel tanks small", "an extra fuel cell: a rounded hydrogen tank with insulated piping"),
    (r"armor plate", "{size} ceramic-composite armour panel(s) with a honeycomb core visible on the cut edge"),
    (r"dive brakes", "perforated split airbrake panels deployed open on a wing trailing edge"),
    (r"floats", "a pair of streamlined pontoon floats with folding struts"),
    (r"flying boat", "a boat-hull fuselage underside with a stepped keel and wing floats"),
    (r"non strategic materials", "an airframe section built of printed carbon composite, with a visible lattice pattern"),
    (r"plane", "an aircraft equipment module"),
    # --- tanques: torretas y armas
    (r"super heavy (three|four) man tank turret", "a colossal fortress turret with layered armour and a huge gun mantlet"),
    (r"(one|two|three) man tank turret", "a {weight} crewless robotic tank turret with a sensor mast (the crew rides in the hull capsule)"),
    (r"fixed superstructure turret", "a {weight} casemate: a low sloped fixed fighting compartment with a hull-mounted gun"),
    (r"modern (tank )?turret", "a low, angular, crewless modern turret with an autoloader bustle and sensor heads"),
    (r"turret type", "a {weight} tank turret silhouette, clean and angular"),
    (r"super heavy (cannon|main armament)", "a monstrous long-barrel tank railgun with a capacitor bank"),
    (r"heavy (cannon|main armament)", "an {tier} heavy tank gun: a long smoothbore barrel with an electrothermal breech"),
    (r"medium (cannon|main armament)", "an {tier} medium tank gun with a thermal sleeve and fume extractor"),
    (r"small (cannon|main armament)", "an {tier} light tank gun: a short fast-firing barrel"),
    (r"high velocity cannon", "an {tier} hypervelocity tank railgun: a long thin barrel with rail housings"),
    (r"heavy howitzer", "an {tier} heavy tank howitzer with a fat short barrel and an ammunition carousel"),
    (r"medium howitzer", "an {tier} medium howitzer barrel with a recoil sleeve"),
    (r"close support gun", "a short-barrel support gun for bunker busting"),
    (r"auto cannon", "an {tier} tank autocannon with a twin ammunition feed"),
    (r"anti air cannon", "an {tier} anti-drone turret: a quad rotary cannon beside a small laser emitter"),
    (r"tank flamethrower|^flamethrower|advanced flamethrower", "a thermobaric projector: a thick nozzle fed by armoured fuel hoses"),
    (r"rocket launcher", "an {tier} vehicle rocket launcher box with a grid of tube openings"),
    (r"heavy machine gun|additional machine guns|secondary turret hmg", "a remote weapon station with a heavy rotary gun and a camera ball"),
    (r"secondary turret small cannon", "a small secondary remote turret with a compact cannon"),
    (r"secondary turret close support gun", "a small secondary turret with a stubby support gun"),
    (r"squeezebore", "a tapered squeeze-bore muzzle adaptor on the end of a gun barrel"),
    (r"auto loader", "an autoloader cassette: a carousel of shells moving on a chain into a breech"),
    (r"stabilizer", "a gyroscopic gun stabiliser: a spinning gyro drum on a gun cradle"),
    (r"troop carrier", "an armoured troop compartment with a rear ramp open"),
    # --- tanques: chasis, motor, blindaje
    (r"gas turbine engine", "a compact gas-turbine powerpack with a recuperator drum"),
    (r"petrol electric engine", "a hybrid generator and electric hub-motor drivetrain"),
    (r"diesel engine", "a compact high-power hydrogen combustion engine block with turbochargers"),
    (r"gasoline engine", "a small rugged combustion engine with an exposed air filter, an old-style powerpack"),
    (r"wheeled suspension", "a set of three large all-terrain wheels with independent hydro-pneumatic arms"),
    (r"half track suspension", "a wheel-and-rubber-track hybrid running gear"),
    (r"(christie|torsion bar|interleaved|bogie) suspension", "a {susp} tracked running gear: road wheels and a segmented band track"),
    (r"riveted armor", "a riveted plate of improvised scrap armour, old-fashioned"),
    (r"welded armor", "a welded composite armour plate with clean seams"),
    (r"cast armor", "a curved cast armour shell with a smooth rounded surface"),
    (r"sloped armor", "a steeply sloped armour glacis with a reactive tile pattern"),
    (r"armor skirts|lc armored skirts", "side skirts of slatted cage armour hanging over road wheels"),
    (r"amphibious drive", "a pair of shrouded water-jet propulsors with a folding trim vane"),
    (r"dozer blade", "a front-mounted bulldozer blade with hydraulic arms"),
    (r"demining coil|obstacle clearance", "a mine-clearing roller rig with a magnetic signature coil"),
    (r"smoke launchers|smoke generators", "a cluster of smoke and decoy grenade launchers"),
    (r"extra ammo storage|internal ammunition", "an armoured ammunition locker with blow-out panels on top"),
    (r"wet ammo storage|wet ammunition", "an ammunition rack surrounded by coolant jackets"),
    (r"easy maintenance", "a powerpack sliding out of an open engine deck on rails"),
    (r"fixed explosive charge", "a demolition charge rack bolted to a hull front"),
    (r"tank radio", "an {tier} vehicle communications mast with a mesh-network antenna"),
    # --- vehículos de tierra enormes (land cruisers, lc)
    (r"lc aerial deployment", "a land-cruiser drone hangar: a deck hatch opening with launch rails"),
    (r"lc aircraft catapult", "a deck catapult track with a small drone on it"),
    (r"lc assault gun", "a huge hull-mounted assault gun in a sloped casemate"),
    (r"lc bunker emplacement", "a fortified bunker block with firing slits, mounted on a giant vehicle deck"),
    (r"lc command center", "a command bridge tower with antennas and a glass observation band"),
    (r"lc flamethrower turret", "a heavy thermobaric projector turret"),
    (r"lc heavy anti air platform", "a large anti-air platform with radar and quad missile racks"),
    (r"lc heavy anti air battery|lc light anti air battery", "an anti-air battery of rotary cannons and a laser dome"),
    (r"lc heavy high velocity cannons|lc high velocity cannon turret", "a twin railgun turret on a giant land vehicle"),
    (r"lc heavy naval guns|lc medium naval guns", "a battleship-style triple gun turret mounted on tracks"),
    (r"lc helipad", "a deck landing pad with a circle marking and a small tiltrotor"),
    (r"lc high impact obliterator cannon", "an enormous single siege railgun with a ribbed barrel and capacitor towers"),
    (r"lc medium cannon turret", "a medium cannon turret on a giant vehicle deck"),
    (r"lc hull mounted railway gun|lc super heavy railway gun", "a gigantic hull-mounted siege gun with a long barrel"),
    (r"lc internal fuel tanks", "a bank of large internal fuel cells"),
    (r"lc radar", "a rotating radar array on a tall mast"),
    (r"lc radio", "an {tier} long-range communications array with a dish"),
    (r"lc rocket launcher", "a large vertical-launch rocket cell block"),
    (r"lc stabilizers", "hydraulic outrigger stabiliser legs deployed to the ground"),
    (r"lc super heavy howitzer", "a super-heavy siege howitzer with a gigantic short barrel"),
    (r"lc obstacle clearance", "a giant mine-clearing roller and plough rig for a land cruiser"),
    (r"lc smoke generators", "a row of smoke and decoy launchers on a giant vehicle hull"),
    (r"lc internal ammunition", "an armoured magazine compartment with shell racks and blow-out roof panels"),
    (r"lc wet ammunition", "a magazine of shell racks wrapped in coolant jackets"),
    (r"lc ", "a module for a giant land cruiser vehicle"),
]

TIERS = {"1": "early-model", "2": "improved", "3": "advanced", "4": "state-of-the-art 2100"}


def describir(que: str) -> str:
    q = que.lower().strip()
    m = re.search(r"(\d)x\b", q)
    n = {"1": "one", "2": "two", "3": "three", "4": "four", "6": "six"}.get(m.group(1) if m else "1", "one")
    tier_m = re.search(r"(?:^engine |cannon |radar |navigation |radio |buster |mounting |sights |\s)(\d)(?:\s|$)", q)
    tier = TIERS.get(tier_m.group(1) if tier_m else "", "standard")
    size = "large" if "large" in q else "medium" if "medium" in q else "small" if "small" in q else "an"
    weight = ("super-heavy" if "super heavy" in q else "heavy" if "heavy" in q else
              "medium" if "medium" in q else "light" if "light" in q else "standard")
    susp = next((s for s in ("christie", "torsion bar", "interleaved", "bogie") if s in q), "")
    susp = {"christie": "high-speed large-wheel", "torsion bar": "torsion-bar", "interleaved": "interleaved-wheel",
            "bogie": "bogie-spring"}.get(susp, "")
    for patron, texto in REGLAS:
        # los módulos de los vehículos gigantes (lc) solo con sus propias reglas
        if q.startswith("lc ") and "lc" not in patron:
            continue
        if re.search(patron, q):
            return texto.format(n=n, tier=tier, size=size, weight=weight, susp=susp)
    return f"a 2100 equipment module: {que}"


ESTILO = (
    "game user-interface icon of an equipment module for a grand strategy game set in the year 2100. ORIGINAL "
    "design, do NOT imitate any existing game's icon: a believable piece of 2100 military hardware (post-collapse "
    "rebuilt industry: drones, railguns, defensive lasers, hydrogen engines, ceramic-composite armour; practical, "
    "industrial, no sci-fi fantasy). Rendered as ONE object in clean three-quarter view on its own, like a museum "
    "catalogue cutout: aged bronze and warm copper metal (#c27a45, highlights #f0b585, shadows #6b3a1c) with dark "
    "graphite parts and at most one small teal accent (#4fd6c8, a light or a glowing part). Solid dark outline "
    "about 3% of the canvas wide, light from the top left, no cast shadow. Bold readable silhouette, at most three "
    "inner details: it must read at 40 pixels. Transparent background, nothing around the object: no plate, no "
    "circle, no frame, no hand, no vehicle around it unless the description says so. No text, no letters, no numbers.")


LLEGADOS = Path(__file__).resolve().parents[2] / "arte" / "disenador_llegados.txt"


def _llegados() -> set[str]:
    if not LLEGADOS.exists():
        return set()
    return {l.strip() for l in LLEGADOS.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def anotar_llegados(carpeta: str) -> list[str]:
    """Anota en arte/disenador_llegados.txt los módulos de una carpeta recién importada
    (2026-11-07): las imágenes viejas ya existían, así que el archivo es lo que dice
    cuáles ya se rehicieron en el estilo nuevo."""
    from tools.fabrica import control
    todos = {i["id"] for i in items(todos=True)}
    previos = _llegados()
    buenos = control.mejores_por_nombre(p for p in Path(carpeta).rglob("*.png") if "revisar" not in p.parts)
    nuevos = {s for s in buenos if s in todos} - previos
    cabeza = "# Módulos del diseñador que ya llegaron en el estilo 2100 (tools/arte/disenador.py no los vuelve a pedir)."
    LLEGADOS.write_text(cabeza + "\n" + "\n".join(sorted(previos | nuevos)) + "\n", encoding="utf-8")
    return [f"diseñador: {len(nuevos)} módulos nuevos anotados ({len(previos | nuevos)} de {len(todos)})"]


def items(todos: bool = False) -> list[dict]:
    """Un pedido por módulo del diseñador que todavía no llegó en el estilo nuevo."""
    from tools.arte import auditoria
    datos = auditoria.cargar() or {}
    hechos = set() if todos else _llegados()
    out = []
    for i in datos.get("iconos") or []:
        if i.get("familia") != "disenador" or i["id"] in hechos:
            continue
        out.append({"id": i["id"], "que": i.get("que", ""), "descripcion": describir(i.get("que", ""))})
    return out


def pedido(i: dict) -> str:
    return "\n".join([
        "ASSET_REQUEST",
        "type: game_icon",
        f"id: {i['id']}",
        f"filename: {i['id']}.png",
        "size: 512x512 (o más grande con la misma proporción)",
        f"style: {ESTILO}",
        f"description: WHAT: module '{i['que']}' of the equipment designer (tanks, planes, ships). "
        f"EXACT SUBJECT: {i['descripcion']}.",
        "transparent_background: true",
        "",
    ])
