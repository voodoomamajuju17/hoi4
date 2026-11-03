"""Genera arte/pedidos_agentes_inteligencia.txt (40 retratos de espías, 5 por potencia).

Uso: python3 arte/pedidos_agentes_inteligencia.py arte/pedidos_agentes_inteligencia.txt
Los datos sirven también para crear los agentes cuando lleguen las imágenes."""
import sys

NATIONS = {
    "EFE": ("Ecofascist Empire (South America, capital Buenos Aires)", "the Green Eye (Ojo Verde), the Empire's forest-born intelligence service"),
    "FCU": ("Free Corporative Capital Union (North America, a state run by four corporations)", "the Risk Office, the Union's privatised intelligence department"),
    "ASC": ("Automated Socialist Commune (Europe, an economy run by planning algorithms and robots)", "the Surveillance Commissariat, where algorithms and a few stubborn humans watch everyone"),
    "HSN": ("High Seas Market Nation (Asia-Pacific, a trading league of ports and islands)", "the Harbour of Whispers, a network of port informants, smugglers and divers"),
    "NAS": ("Neo-Andean Sun Empire (Andes, a restored Inca empire, Tawantinsuyu)", "the Chasquis, the imperial runners turned into a modern secret service"),
    "SHD": ("Socialist Hydraulic Directorate (China, a state built around dams and canals)", "the Census Bureau, which counts every person, every litre and every secret"),
    "APF": ("African Peoples' Federation (a continental federation of councils)", "the Diaspora Networks, agents spread through the African communities of the whole world"),
    "NRE": ("Neo-Roman Empire (Italy, the Balkans and the Mediterranean, a restored Rome)", "the Frumentarii, the reborn imperial secret service of Rome"),
}

STYLE = ("photorealistic painted portrait matching the existing leader portraits of this Hearts of Iron IV mod: "
         "realistic skin pores, hair and fabric weave, subtle painterly softness, rich but natural colour grading, "
         "believable near-future clothing of the year 2100 (not a sci-fi costume); the face must be fully visible and "
         "readable even when the image is shrunk to a small icon (no mask, no helmet, no sunglasses over the eyes, "
         "no hand covering the face); no text, no letters, no numbers, no logos with words, no watermark, no frame, no border")

# Cada agente: tag, slug, código, nombre real, oficio (en/es), persona, gesto, ropa, detalle, encuadre, cámara, luz, fondo.
A = []
def ag(**k): A.append(k)

# ---------------------------------------------------------------- EFE
ag(tag="EFE", slug="yaguarete", code="Yaguareté", name="Tomás Ledesma",
   role=("jungle infiltrator and scout", "infiltrador y explorador de selva"),
   person="a 41-year-old Argentine man of mixed criollo and Guaraní descent: lean weathered face, short black hair wet with sweat, a three-day beard, a thin white scar through the left eyebrow, smudges of dark green and ochre camouflage paint across the cheekbones",
   expr="still and alert, the eyes of a hunter who has been waiting for hours",
   clothes="a mottled forest-green ranger smock of the Empire with the hood of a leaf-covered ghillie cape pushed back onto the shoulders, a bark-brown leather strap across the chest",
   detail="a single jaguar claw hanging from a cord at his throat, and a few real leaves and twigs still caught in the ghillie hood",
   framing="tight head-and-shoulders: the frame cuts just below the collarbones, the face fills about 45% of the image height, the eyes slightly above the upper-third line",
   camera="low angle from about 30 cm below his eye line, as if the viewer were lying in the undergrowth too; 35mm lens at f/2 close to him, giving a slight sense of closeness; his head turned three-quarters to the left, the eyes sliding back to the lens",
   light="dappled sunlight breaking through the canopy: a hard spot of sun on one cheekbone and the eye, the rest of the face in soft green shade; tiny insects and humidity glittering in the light",
   bg="dense jungle undergrowth with giant leaves very close and out of focus in the foreground corners, a sunlit gap in the trees far behind")
ag(tag="EFE", slug="orquidea", code="Orquídea", name="Valentina Sosa Miró",
   role=("seducer and embassy botanist (cover)", "seductora, de pantalla botánica de embajada"),
   person="a 34-year-old Argentine woman: olive skin, dark brown hair in a low elegant chignon with loose strands at the temples, high cheekbones, a beauty mark above the lip, dark eyes lined with a thin green line",
   expr="a warm, inviting half-smile that does not reach the eyes; the eyes are measuring the viewer",
   clothes="an evening gown in deep emerald silk with a high asymmetric neckline and one bare shoulder, long thin gold earrings shaped like vines",
   detail="a white-and-purple orchid corsage pinned at the left shoulder; looking closely, the centre of the orchid is a tiny lens catching a glint of light",
   framing="chest-up portrait, the frame cuts above the waist; she is placed slightly right of centre with the empty space of the greenhouse on the left",
   camera="eye level, 85mm lens at f/1.8, shallow focus; she stands in profile to the right and turns only her head over the bare shoulder to look straight into the lens",
   light="night inside a glass greenhouse: warm amber lanterns hung among the plants give a soft key light from the front right, the cool blue moonlight through the glass draws a rim along her shoulder and hair",
   bg="the night-time imperial greenhouse of an embassy party: blurred orchids, ferns, glowing lanterns and blurred guests in green and gold far behind")
ag(tag="EFE", slug="hornero", code="Hornero", name="Ezequiel Barrios",
   role=("saboteur of dams, pipelines and bridges", "saboteador de represas, ductos y puentes"),
   person="a 56-year-old Argentine man from the Litoral: broad sun-cracked face, a grey moustache, thick greying hair under a sweat-stained bucket hat in olive canvas, large ears, heavy work-worn hands",
   expr="patient and a little sad, like a craftsman who does not enjoy what he builds",
   clothes="an old olive-green fisherman's waistcoat full of pockets over a faded shirt, the small gold seedling pin of the Empire hidden on the inside of the lapel and just visible as the lapel folds",
   detail="he holds at chest height, in both muddy hands, a round lump of grey river clay shaped like an ovenbird's nest, with a thin copper wire and a tiny green diode sticking out of it (a disguised charge)",
   framing="mid-chest bust with the hands and the clay nest included in the lower fifth of the frame; centred",
   camera="slightly high angle, the camera about 20 cm above his eyes looking down, 50mm lens at f/2.8; he faces the camera squarely and looks up into the lens",
   light="flat grey overcast light from the open sky, a soft white reflector from below catching the clay and his hands; muted earthy colours",
   bg="the brown wide Paraná river at dawn, a huge concrete dam and a pipeline bridge hazy in the distance")
ag(tag="EFE", slug="lapacho", code="Lapacho", name="Ana Paula Ferreira",
   role=("hacker of living bio-networks", "hackeadora de redes vivas"),
   person="a 29-year-old Brazilian woman from the south: light brown skin, short asymmetric undercut hair dyed dark green on one side, a fine silver ring in the nostril, freckles, a small leaf tattoo behind the ear",
   expr="focused, eyebrows slightly raised, a mischievous corner of the mouth",
   clothes="a green canvas technician's jacket of the Empire with the sleeves pushed up, gold laurel embroidery only on the collar, fingerless gloves",
   detail="a thin translucent tube of glowing green fungal mycelium runs from a jack behind her ear down over her shoulder, like a living cable",
   framing="head-and-shoulders, the frame cuts at the top of the chest; she sits slightly left of centre leaning forward towards the viewer",
   camera="eye level, 50mm at f/2, the camera slightly to her left; head tilted a little, eyes straight into the lens",
   light="split lighting: the only key light is the green glow of a bio-luminescent screen below and to the right of the frame, lighting half her face from underneath; the other half falls into deep shadow with a faint warm rim from a desk lamp behind",
   bg="a dark root-cellar laboratory under the capital: glass jars of glowing fungus, roots coming through the brick ceiling, out of focus")
ag(tag="EFE", slug="tero", code="El Tero", name="Ramiro Quiroga",
   role=("old counter-intelligence officer", "viejo oficial de contrainteligencia"),
   person="a 63-year-old Argentine man of the pampas: long weathered face, white hair swept back, thick white eyebrows, a deep furrow between them, a silver stubble, small very pale grey eyes",
   expr="suspicious and unhurried, one eyebrow raised as if he already knows the viewer is lying",
   clothes="a dark green three-piece suit of the Empire's officials under a grey wool gaucho poncho thrown over one shoulder, a black neckerchief",
   detail="he holds a mate gourd with a silver straw close to his chin, steam rising from it",
   framing="classic bust cutting at mid-chest, the mate at chest height inside the frame; centred with a little air above the head",
   camera="eye level, 105mm lens at f/4, a slightly compressed, calm image; body turned 40 degrees to the right, the face turned back almost to the camera",
   light="Rembrandt lighting from a single tall window on the left: a triangle of light on the shadowed cheek, warm late-afternoon sun, deep brown shadows",
   bg="the dim study of an old estancia turned into a secret service office: leather chairs, maps of the pampas on the wall, a lapwing (tero) stuffed on a shelf, all in soft focus")

# ---------------------------------------------------------------- FCU
ag(tag="FCU", slug="escrow", code="Escrow", name="Dana Prescott",
   role=("corporate infiltrator under an auditor's cover", "infiltradora con pantalla de auditora"),
   person="a 38-year-old American woman: pale skin, straight ash-blond hair in a sharp jaw-length bob, thin precise eyebrows, light grey eyes, very little make-up",
   expr="neutral, polite, unreadable; a professional half-smile",
   clothes="a perfectly cut charcoal trouser suit with a navy silk blouse, a blank white access badge on a navy lanyard (no text), a slim steel watch",
   detail="a second, different access badge is half-hidden in her breast pocket",
   framing="chest-up, she stands slightly left of centre; the frame is cut at the waist",
   camera="the feel of a long-lens surveillance photo: 200mm telephoto from across an office floor, shooting through a glass wall, faint reflections of the city and of ceiling lights over the glass; she looks straight back at the lens as if she has spotted the camera",
   light="cool clean office daylight from tall windows on her right, glossy highlights, a slight blue cast",
   bg="an open-plan corporate floor of glass and white surfaces, blurred employees and floating blue holographic charts without text")
ag(tag="FCU", slug="short_seller", code="Short Seller", name="Desmond Okoro-Reed",
   role=("market saboteur", "saboteador de mercados"),
   person="a 45-year-old American man of Nigerian and Irish descent: dark brown skin, a shaved head, a well-trimmed salt-and-pepper beard, rimless glasses",
   expr="amused and cold, a slight smirk, eyes calculating",
   clothes="a navy three-piece suit with the jacket off, sleeves of the white shirt rolled to the elbows, a silver tie loosened, navy braces",
   detail="the reflection of red falling market charts runs across the lenses of his glasses (no readable text)",
   framing="head-and-shoulders with a slight Dutch tilt of about 6 degrees; centred",
   camera="eye level, 35mm lens at f/2 quite close, wide enough to show the wall of screens around him; frontal pose, eyes to the lens",
   light="night: the only light comes from the wall of screens behind and in front of him, cold blue key light on the face, red flickering accents from the falling charts, deep black shadows",
   bg="a dark trading floor at 3 a.m., walls of monitors in blue and red, empty chairs")
ag(tag="FCU", slug="golden_parachute", code="Golden Parachute", name="Elliot Kane",
   role=("extraction commando of a private military contractor", "comando de extracción de contratista militar"),
   person="a 52-year-old American man from Montana: square jaw, sunburnt skin, short grey crew cut, crow's feet, a broken nose healed slightly crooked, pale blue eyes",
   expr="calm and tired, the face of someone counting the seconds before a helicopter lifts off",
   clothes="a navy tactical softshell jacket of a contractor with silver chevrons on the collar and an abstract silver shoulder patch (no letters), a plate carrier in navy over it, a headset around the neck",
   detail="rain drops on his face and on the shoulders of the jacket, a carabiner with a rescue rope on the chest strap",
   framing="bust cut at mid-chest; he is placed on the right third, the left two thirds show the blurred helipad",
   camera="eye level, 135mm lens at f/2.8, strong background compression; body turned 45 degrees to the left, the face toward the lens",
   light="night rain: a hard white floodlight from the upper right, red navigation lights of a helicopter blurred behind, every raindrop catching the light",
   bg="a rooftop helipad of a glass tower in the rain, a black corporate tiltrotor with spinning rotors as a blur")
ag(tag="FCU", slug="due_diligence", code="Due Diligence", name="Sofía Márquez-Lindgren",
   role=("hacker and cryptanalyst", "hackeadora y criptoanalista"),
   person="a 31-year-old Mexican-American woman: warm tan skin, black curly hair pulled into a messy high bun with a pencil through it, thick dark eyebrows, a small gap between the front teeth",
   expr="a confident grin of someone who just broke a code",
   clothes="a grey hoodie under an expensive navy blazer with silver buttons, a silver corporate pin (abstract shape, no letters) on the blazer",
   detail="her irises carry a faint ring of blue light from augmented-reality contact lenses",
   framing="close portrait from the top of the head to the collarbone, she sits slightly to the right of centre",
   camera="high angle, the camera above her as if it were her own monitor looking down at her; 50mm lens at f/2; she looks up into the lens",
   light="cold blue-white light from the screen in front of her as the key light, server LEDs drawing small green and blue points in her hair, a warm accent of a coffee cup lamp at the edge",
   bg="a cold server room with rows of racks and blinking lights, out of focus")
ag(tag="FCU", slug="non_compete", code="Non-Compete", name="Harold Vance",
   role=("recruiter of defectors", "reclutador de desertores"),
   person="a 67-year-old American man from Connecticut: tanned and well-kept, thick white hair parted on the side, bright white teeth, liver spots on the temples, kind blue eyes",
   expr="grandfatherly warmth, a broad friendly smile; the friendliest person in the room is the most dangerous",
   clothes="a cream linen blazer over a pale blue polo shirt, a navy club tie loosened, a silver abstract corporate lapel pin",
   detail="he holds an unlit cigar between two fingers near his chin and a golf glove sticks out of the blazer pocket",
   framing="bust cut at mid-chest, centred, the cigar inside the frame at chin height",
   camera="eye level, 85mm at f/2.8; he leans slightly towards the viewer, square to the camera, like someone about to make an offer",
   light="golden hour outdoors, warm sun from behind making a halo in his white hair, a white bounce filling the face softly",
   bg="the terrace of a private country club over a golf course and a glass city skyline far away")

# ---------------------------------------------------------------- ASC
ag(tag="ASC", slug="vektor", code="Vektor", name="Greta Solbakken",
   role=("cryptologist with a neural interface", "criptóloga con interfaz neural"),
   person="a 36-year-old Norwegian woman: very fair skin, white-blond hair shaved on the right side and long on the left, colourless eyelashes, ice-blue eyes, a small metal port with a red LED set into the skin behind her right ear",
   expr="detached and precise, almost no expression, the eyes slightly unfocused as if reading something invisible",
   clothes="a charcoal-grey high-collared work jacket of the Commune with the vertical red stripe down the left side and the white chest panel, the red triangle-in-hexagon pin",
   detail="thin lines of red light from a holographic node network reflect on her cheek",
   framing="head-and-shoulders, the face turned so that the right side with the port faces the viewer; centred",
   camera="eye level, 85mm at f/2; her head in strict profile to the left, then only the eyes turning towards the lens",
   light="even cool white light from above as in an operating theatre, very clean soft shadows, a small red accent from the port LED",
   bg="a white algorithmic hall with suspended screens of abstract node graphs and moving lines (no readable text), robot arms in the far distance")
ag(tag="ASC", slug="schraube", code="Schraube", name="Pavel Novák",
   role=("saboteur under a maintenance technician's cover", "saboteador con pantalla de técnico de mantenimiento"),
   person="a 48-year-old Czech man: heavy-set, round face with ruddy cheeks, a thick brown moustache, short greying hair, a smear of machine oil on the forehead",
   expr="friendly, a bit sly, the look of a worker who knows where every bolt is",
   clothes="oil-stained grey work overalls of the Commune with the red stripe, a white chest panel scratched and dirty, a red triangle badge, a headlamp on an elastic band around the neck",
   detail="a long screwdriver held like a pen at chest height; a robot arm in the background has a visible missing bolt",
   framing="chest-up, the screwdriver inside the frame; he stands on the left third, a disabled robot arm fills the right",
   camera="low angle, about 40 cm under his eyes, 28mm lens close to him so the factory feels huge behind; he looks down into the lens",
   light="the hard warm cone of a portable work lamp from the lower left, the factory behind in cold blue darkness with red warning lights",
   bg="a stopped automated assembly line at night, rows of frozen white robot arms, sparks dying on the floor")
ag(tag="ASC", slug="null", code="Null", name="Elin Virtanen",
   role=("deep-cover infiltrator in capitalist countries", "infiltrada de larga duración en países capitalistas"),
   person="a 27-year-old Finnish woman: pale skin with light freckles, auburn shoulder-length hair under a camel beret, round face, grey-green eyes",
   expr="softly anxious, a polite tourist smile held a bit too long",
   clothes="a beige trench coat with the collar turned up over a cream turtleneck, deliberately un-Communal clothes, no badges at all",
   detail="the only trace of the Commune: a tiny red thread sewn into the inside of the collar, visible where the collar folds",
   framing="the portrait is seen as a reflection in a train window: head and shoulders, centred, with faint reflections of station lights crossing the glass",
   camera="eye level, 50mm at f/2, shot through the glass of a train window; she looks at her own reflection, therefore into the lens",
   light="mixed: warm interior light of the carriage on her face, cold blue neon of the station sliding across the glass in streaks",
   bg="a night-time maglev station of a foreign capital seen through the window, blurred platforms and advertising screens without readable text")
ag(tag="ASC", slug="kuckuck", code="Genosse Kuckuck", name="Dieter Brandt",
   role=("old human case officer who distrusts the algorithms", "viejo oficial de caso humano que desconfía de los algoritmos"),
   person="a 59-year-old German man: long gaunt face, thinning grey hair combed back, heavy dark bags under the eyes, half-moon reading glasses low on the nose",
   expr="ironic and weary, looking over the top of his glasses",
   clothes="a worn charcoal-grey Commune jacket with the red stripe faded almost to pink, an old knitted grey cardigan underneath",
   detail="he holds a small paper notebook and a pencil, real paper in an automated world; cigarette smoke drifting",
   framing="bust cut at mid-chest, the notebook at chest height; placed slightly right of centre",
   camera="eye level, 50mm at f/2.8, the camera a little to his left; body leaning on a desk, face toward the lens",
   light="low-key: a single green-shaded desk lamp from below left, warm pool of light on the face and the notebook, the rest of the room black; smoke catching the light",
   bg="a dark archive room with metal shelves of old paper files, the only analog room in the Commune")
ag(tag="ASC", slug="ida7", code="Ida-7", name="Ida Kowalczyk",
   role=("commando with a robotic arm", "comando con brazo robótico"),
   person="a 32-year-old Polish woman: strong jaw, short dark brown hair cropped close, a scar across the bridge of the nose, intense brown eyes, a soot mark on the cheek",
   expr="hard and determined, jaw set",
   clothes="a charcoal-grey field uniform of the Commune with white shoulder panels and red chevrons, a light grey ballistic vest",
   detail="her left arm is a white-and-grey robotic prosthesis of the same design as the Commune's factory robots, raised so that the mechanical hand is visible near her shoulder",
   framing="chest-up with a 10 degree Dutch tilt, the robotic hand entering the frame at the right edge at shoulder height",
   camera="eye level, 35mm at f/2.8; body turned 30 degrees right, face to the lens",
   light="red emergency light from the upper left as key, a cold white strobe rim from behind, a dark smoky atmosphere",
   bg="a corridor of a captured bunker with red emergency lights and drifting smoke")

# ---------------------------------------------------------------- HSN
ag(tag="HSN", slug="manta", code="Manta", name="Viliami Lolohea",
   role=("combat diver and harbour saboteur", "buzo de combate y saboteador de puertos"),
   person="a 40-year-old Tongan man: broad shoulders, dark brown skin, wet black hair tied back, a short beard with water drops, traditional Tongan tattoo lines on the shoulder and up the neck",
   expr="calm and controlled, breathing slowly",
   clothes="a matte black and dark teal diving suit with a brass compass-rose patch on the chest, a compact rebreather mouthpiece hanging below the chin",
   detail="water streaming down his face; a magnetic mine clipped to his chest harness",
   framing="head-and-shoulders, he rises out of the water: the waterline cuts the frame at the lower fifth",
   camera="the camera at water level, 24mm lens very close, the water surface in the foreground; he faces the lens directly",
   light="night: teal-blue light from an underwater lamp below the surface lighting his face from beneath, distant yellow harbour lights behind",
   bg="a dark harbour at night with the hull of a grey warship towering above, out of focus")
ag(tag="HSN", slug="jade_ledger", code="Jade Ledger", name="Lim Su-yin",
   role=("smuggling accountant and customs infiltrator", "contadora de contrabandistas e infiltrada en aduanas"),
   person="a 44-year-old Singaporean Chinese woman: smooth face, black hair cut in a precise straight bob with a fringe, thin gold glasses, red lipstick",
   expr="politely amused, a small closed-lip smile",
   clothes="a dark teal silk qipao-inspired jacket with brass buttons and a high collar, a small brass compass-rose pin",
   detail="a jade abacus bead bracelet on the wrist and a cup of tea held near her chin with both hands",
   framing="bust cut at mid-chest; centred, the tea cup inside the frame",
   camera="slightly high angle, 85mm at f/2; she sits, body square to the camera, head slightly tilted",
   light="warm red and gold paper lanterns from both sides, a soft key from the front left, steam from the tea catching the light",
   bg="a private room above a crowded harbour tea house, red lanterns and blurred wooden screens, a container ship visible through the window")
ag(tag="HSN", slug="monzon", code="Monsoon", name="Arjun Pillai",
   role=("signals hacker aboard merchant ships", "hacker de señales a bordo de mercantes"),
   person="a 33-year-old Indian man from Kerala: dark skin with a sheen of sweat, curly black hair, a thin moustache, dark circles under the eyes",
   expr="tired but sharp, mouth slightly open as if about to speak",
   clothes="a teal short-sleeved merchant officer's shirt with brass buttons, the collar open, a headset with one ear cup pushed back",
   detail="a tangle of coloured cables and a hand-soldered radio board on the desk at the lower edge of the frame",
   framing="close head-and-shoulders, centred",
   camera="eye level, 35mm at f/2 in the tight space of a ship cabin; the frame slightly tilted to suggest the rolling sea",
   light="the warm amber glow of old radio displays from the right, a cold blue porthole light from the left, a swinging bare bulb above",
   bg="the cramped radio room of a container ship, a round porthole showing a stormy sea")
ag(tag="HSN", slug="perla", code="Pearl", name="Dewi Kartika",
   role=("seducer in the casinos of the floating cities", "seductora en los casinos de las ciudades flotantes"),
   person="a 28-year-old Indonesian woman: golden-brown skin, long black hair over one shoulder, dark almond eyes with gold eyeliner, a small pearl stud in each ear",
   expr="playful and confident, one eyebrow raised, lips just parted",
   clothes="a backless gold-and-teal evening dress with a high halter neck, a thin teal shawl",
   detail="a single large black pearl on a fine chain at her throat; it is a microphone",
   framing="chest-up, she is placed on the right third, gold blurred lights on the left",
   camera="eye level, 85mm at f/1.4, very shallow focus; she looks over her right shoulder into the lens, her back half turned",
   light="warm gold casino lights, bokeh of chandeliers, a soft key from the front, a teal neon rim from behind",
   bg="the casino of a floating city at night, mirrored walls, blurred gaming tables, the sea through tall windows")
ag(tag="HSN", slug="anzuelo", code="Old Hook", name="Nguyễn Văn Tâm",
   role=("chief of the port informant network", "jefe de la red de informantes del puerto"),
   person="a 70-year-old Vietnamese man: deeply lined dark face, a thin white beard on the chin, white stubble on a shaved head, one eye cloudy, a broad gap-toothed smile",
   expr="cheerful and cunning, laughing quietly",
   clothes="a faded teal fisherman's jacket with brass buttons, a conical straw hat pushed back and hanging on his back by a cord",
   detail="his forearms and hands are covered in old faded sailor tattoos of fish and stars; he holds a fish hook up between two fingers",
   framing="bust cut at mid-chest, the hand with the hook inside the frame at chin height; centred",
   camera="eye level, 50mm at f/4, documentary-photo feel; he faces the lens squarely",
   light="pale blue-pink light of early dawn, soft and diffused, with a warm lamp from a stall on one side",
   bg="a fish market on the docks at dawn, ice, baskets of fish, gulls and container cranes in the mist")

# ---------------------------------------------------------------- NAS
ag(tag="NAS", slug="kuntur", code="Kuntur", name="Illari Mamani",
   role=("high-altitude wingsuit infiltrator", "infiltradora con traje de alas de altura"),
   person="a 30-year-old Aymara woman: copper-brown skin reddened by cold and wind, two long black braids, high cheekbones, wind-chapped lips, dark eyes",
   expr="exhilarated and fearless, a slight smile, eyes narrowed against the wind",
   clothes="a dark blue wingsuit with woven tocapu bands on the collar and across the chest, a gold condor-wings badge",
   detail="flight goggles pushed up on the forehead, ice crystals on the braids and on the eyelashes",
   framing="head-and-shoulders, the braids flying sideways out of the frame; centred",
   camera="eye level on a mountain ridge, 24mm lens, slight upward angle so the sky fills the space above; she faces the lens",
   light="crisp high-altitude sun from the right, hard and bright, a deep blue sky, snow reflecting light from below",
   bg="the edge of a snowy Andean summit, a sea of clouds below, a condor gliding far away")
ag(tag="NAS", slug="khipu", code="Khipu", name="Waman Huarachi",
   role=("cryptologist who writes in knots", "criptólogo que escribe en nudos"),
   person="a 52-year-old Quechua man: round face, deep-set dark eyes, straight black hair with grey streaks down to the collar, a small gold ring in one ear",
   expr="serene and absorbed, a scholar's concentration",
   clothes="a modern jacket covered with woven tocapu panels in teal, cobalt and gold, a gold sun-disc pin",
   detail="he holds up a modern khipu: knotted cords in many colours, some of them thin glowing fibre-optic threads",
   framing="bust cut at mid-chest, the khipu hanging from his raised hands across the lower third",
   camera="eye level, 85mm at f/2.8; body turned 30 degrees left, face to the lens",
   light="warm candlelight from several candles in front and to the left, the glow of the optic fibres adding small cool points of light on his face",
   bg="a room of precisely cut Inca stone walls with trapezoidal niches, each niche holding a coiled khipu")
ag(tag="NAS", slug="amaru", code="Amaru", name="Killa Huanca",
   role=("night saboteur and assassin", "saboteadora y asesina nocturna"),
   person="a 37-year-old Quechua woman: lean angular face, black hair cut short at the jaw, a thin tattoo of a serpent along the left jaw line, very dark eyes",
   expr="cold and silent, the mouth a straight line",
   clothes="a dark blue field tunic with tocapu-patterned bands on the collar, a short woven mantle in black and deep red over the shoulders",
   detail="a coca leaf held between her teeth, a thin obsidian blade in its sheath on the chest strap",
   framing="tight head-and-shoulders; she is placed left of centre, darkness on the right",
   camera="eye level, 85mm at f/1.8; face turned three-quarters right, the eyes cutting back to the lens",
   light="split lighting by a cold full moon from the left: exactly half of her face lit, the other half in darkness with only the eye catching a glint",
   bg="night ruins of a stone fortress, black sky with the Milky Way, almost invisible")
ag(tag="NAS", slug="rumi", code="Rumi", name="Ernesto Apaza",
   role=("counter-intelligence chief of the mining towns", "jefe de contrainteligencia de los pueblos mineros"),
   person="a 61-year-old Aymara man: square heavy face, deep wrinkles, short grey hair, a grey moustache, cheeks bulging with coca, eyes red from the dust",
   expr="stern and still, like stone (rumi)",
   clothes="a dark blue jacket of the Empire with woven bands on the collar under an orange miner's reflective vest, a gold sun pin on the vest",
   detail="a miner's helmet with a lamp pushed back on the head, the lamp switched on and pointing up",
   framing="bust cut at mid-chest, centred",
   camera="slight low angle, 50mm at f/2.8; he faces the lens squarely",
   light="the cold white beam of the helmet lamps of other miners crossing in front of him, a warm orange light from a tunnel lamp on the right, dust floating in the beams",
   bg="the tunnel of a lithium mine, wet rock walls, rails and small carts in the darkness")
ag(tag="NAS", slug="qillqa", code="Qillqa", name="Nina Condemayta",
   role=("young hacker of the cable cities", "joven hackeadora de las ciudades del teleférico"),
   person="a 24-year-old Quechua woman: round cheerful face, cheeks pink from the cold, long black hair under a knitted chullo hat with ear flaps, small gold earrings",
   expr="cheeky and smiling openly, as if she just pulled off a prank",
   clothes="a modern blue puffer jacket with a colourful striped aguayo shawl tied over the shoulders",
   detail="a cheap cracked smartphone held at chest height, its screen glowing on her chin, a gold sun sticker on its case",
   framing="chest-up, the phone inside the frame; she sits on the right third",
   camera="eye level, 35mm at f/2.8, shot inside a cable-car cabin, with the reflections of the window glass crossing the image",
   light="bright cool afternoon light through the cabin windows from the left, the phone glow warm on her chin",
   bg="the window of a cable car over a high Andean city of red-brick houses climbing the slopes, snowy peaks behind")

# ---------------------------------------------------------------- SHD
ag(tag="SHD", slug="compuerta", code="Sluice", name="Zhou Wen",
   role=("census enumerator who knows everyone", "censista que conoce a todos"),
   person="a 46-year-old Chinese man: plain forgettable face, short neat black hair with a few grey strands, thin metal glasses, a polite face",
   expr="bland and courteous, deliberately forgettable; only the eyes are too attentive",
   clothes="a slate-grey Zhongshan-style tunic with four covered pockets, a small jade wave pin, a census armband in pale green (no text)",
   detail="a thin tablet held against his chest with both hands, its screen showing a grid of hundreds of tiny faces (no readable text)",
   framing="bust cut at mid-chest, the tablet inside the frame; perfectly centred and symmetrical",
   camera="eye level, 50mm at f/4, strictly frontal and symmetrical like an identity photo",
   light="flat even fluorescent light from above, slightly green, almost no shadows",
   bg="a hydraulic control room with walls of green screens showing river levels and population counts as graphs (no readable text)")
ag(tag="SHD", slug="limo", code="Silt", name="Han Meiling",
   role=("diver who sabotages enemy dams", "buceadora que sabotea represas enemigas"),
   person="a 33-year-old Chinese woman from Sichuan: oval face, wet black hair slicked back, strong eyebrows, no make-up, cold-reddened cheeks",
   expr="concentrated and quiet",
   clothes="a dark green wetsuit with grey shoulder panels and a small jade wave insignia on the chest, a diving hood pulled down around the neck",
   detail="diving mask hanging around the neck, a thin layer of grey river mud on the cheek and chin",
   framing="head-and-shoulders, she is placed on the left third, the misty gorge on the right",
   camera="slightly high angle from a boat, 85mm at f/2; she looks up from the water to the lens",
   light="soft grey dawn mist, diffused and cool, a faint warm glow of the sun trying to break through",
   bg="a river gorge in mist with the curved wall of an enemy dam far away")
ag(tag="SHD", slug="piedra_de_tinta", code="Ink Stone", name="Chen Bo",
   role=("calligrapher and code-maker", "calígrafo y hacedor de claves"),
   person="a 58-year-old Chinese man: long thin face, thin grey beard on the chin, grey hair tied in a small knot, long fingers stained with ink",
   expr="gentle and inward, a scholar's patience",
   clothes="a dark green Zhongshan-style tunic with a high collar, sleeves protected by grey cloth oversleeves",
   detail="he holds a calligraphy brush wet with black ink; the characters on the paper below are blurred and unreadable",
   framing="bust cut at mid-chest, the brush inside the frame at chest height; placed slightly left of centre",
   camera="eye level, 105mm at f/2.8; body turned 45 degrees left over a desk, the face turned to the lens",
   light="soft north window light from the left through a paper screen, very gentle gradient, ink-wash greys and greens",
   bg="a quiet study with paper screens, hanging scrolls and a view of a canal lock through the window, in soft focus")
ag(tag="SHD", slug="martin_pescador", code="Kingfisher", name="Liang Xiaoyu",
   role=("drone hacker of the river megacities", "hacker de drones de las megaciudades del río"),
   person="a 26-year-old Chinese woman from Chongqing: small face, black hair with a long fringe, a few strands dyed electric blue, a tiny silver stud in the eyebrow",
   expr="cool and alert, chin slightly raised",
   clothes="a grey-green oversized technical jacket with a jade wing badge, the hood down, a transparent umbrella resting on the shoulder",
   detail="a small kingfisher-blue drone hovering just above her shoulder, its single lens glinting",
   framing="head-and-shoulders, centred under the transparent umbrella",
   camera="eye level, 135mm telephoto at f/2 from across a wet street, background bokeh; she looks straight at the lens",
   light="night rain, pink and teal neon signs (no readable text) as coloured rim lights, a soft white key from a shop window",
   bg="a vertical river city at night, stacked streets, bridges and neon reflected on the wet asphalt")
ag(tag="SHD", slug="gran_canal", code="Grand Canal", name="Wang Jie",
   role=("commando of the maglev rail lines", "comando de las líneas de maglev"),
   person="a 40-year-old northern Chinese man: broad face, crew-cut black hair, a heavy jaw, a scar on the chin, narrow watchful eyes",
   expr="tense and ready, the face of someone braced against speed",
   clothes="a dark green high-collared field uniform with grey shoulder boards, a jade wave insignia, a compact black tactical harness",
   detail="a pair of night-vision goggles hanging on the harness, wind pushing his collar flat",
   framing="chest-up, placed on the right third, the speeding tunnel on the left",
   camera="eye level, 35mm at f/4 with motion blur in the background only, he is sharp; body turned 45 degrees, face to the lens",
   light="streaks of white and green tunnel lights flashing past, a cold steady light from the train interior on his face",
   bg="the open door of a maglev train racing through a tunnel, lights smearing into lines")

# ---------------------------------------------------------------- APF
ag(tag="APF", slug="griot", code="Griot", name="Amadou Diallo",
   role=("storyteller and spymaster", "narrador y jefe de red"),
   person="a 64-year-old Malian man: dark skin, a long lined face, a short white beard, a white kufi cap, gentle eyes",
   expr="warm and knowing, as if in the middle of telling a story",
   clothes="a long ochre boubou robe with fine embroidery around the neck, a woven kente-pattern stole in red, gold and green over the shoulders",
   detail="the long neck of a kora (West African harp) rests against his shoulder; among the strings there is a thin antenna wire",
   framing="bust cut at mid-chest, the kora neck entering the frame on the left; centred",
   camera="eye level, 85mm at f/2.8; he sits, face to the lens",
   light="soft shade of a courtyard at midday with warm bounced light from sunlit earth walls, gentle and golden",
   bg="the courtyard of a mud-brick house in Bamako with a large tree, children's shapes blurred in the background")
ag(tag="APF", slug="baobab", code="Baobab", name="Chiamaka Okafor",
   role=("infiltrator in the diaspora of the northern cities", "infiltrada en la diáspora de las ciudades del norte"),
   person="a 35-year-old Nigerian woman: dark skin, an oval face, short natural hair, high cheekbones, small gold earrings",
   expr="composed and guarded, a polite closed smile",
   clothes="a long grey wool winter coat with the collar up and a red, gold and green kente scarf wrapped around the neck, the only colour in the image",
   detail="snowflakes caught in her hair and on the shoulders of the coat",
   framing="head-and-shoulders, she is placed on the left third, snowy street on the right",
   camera="eye level, 85mm at f/1.8; body turned away to the right as if walking, head turned back to the lens",
   light="cold blue winter dusk, a warm shop window light from the left as key on her face",
   bg="a snowy street in a northern European city at dusk, tram lines and blurred passers-by")
ag(tag="APF", slug="mamba", code="Mamba", name="Farai Chikwanha",
   role=("commando of the savanna", "comando de la sabana"),
   person="a 39-year-old Zimbabwean man: very dark skin, shaved head, a lean hard face, a small scar under the right eye, a gold tooth",
   expr="silent menace, the eyes perfectly still",
   clothes="an olive-khaki field uniform with a woven kente band across the chest, a gold star badge on the collar, a light plate carrier",
   detail="night-vision goggles pushed up onto the forehead, a black mamba head embroidered on the shoulder patch",
   framing="tight head-and-shoulders, centred",
   camera="eye level, 50mm at f/2; face square to the lens",
   light="night: a faint green light from the goggles' screens on the forehead, cold blue moonlight from above, almost everything else in black",
   bg="dark savanna at night, the silhouette of an acacia against a starry sky")
ag(tag="APF", slug="kente", code="Kente", name="Abena Owusu",
   role=("hacker of the solar grids", "hackeadora de las redes solares"),
   person="a 29-year-old Ghanaian woman: dark skin, long box braids tied up on top of the head, round glasses with red frames, a broad face with dimples",
   expr="laughing, delighted with herself",
   clothes="a deep red tailored jacket with a kente-pattern collar, a gold star pin, a small headset",
   detail="a laptop with a handwoven kente cover open in front of her at the bottom edge of the frame, its light on her face",
   framing="chest-up, the laptop edge at the bottom; placed slightly right of centre",
   camera="slight high angle, 35mm at f/2.8 inside a small hut; she looks up to the lens",
   light="hard bright midday sun through the door on the left making a strong rectangle of light on her, cooler light from the laptop",
   bg="the control hut of a huge solar farm, rows of panels shining outside the door")
ag(tag="APF", slug="harmattan", code="Harmattan", name="Youssef Ag Ibrahim",
   role=("desert smuggler and saboteur", "contrabandista y saboteador del desierto"),
   person="a 47-year-old Tuareg man: brown skin, sharp face, kohl around the dark eyes, a short black beard",
   expr="proud and patient, eyes narrowed against the sand",
   clothes="an indigo tagelmust turban and veil, the veil pulled down below the chin so the whole face is visible, the indigo dye staining his skin faintly blue; an olive jacket of the Federation with a kente band under the robe",
   detail="a silver Tuareg cross pendant (Agadez cross) and a satellite phone tucked in the chest strap",
   framing="bust cut at mid-chest; he stands on the right third, the dust storm on the left",
   camera="eye level, 135mm at f/2.8, heavy compression; profile to the left, head turned to the lens",
   light="harsh orange light of a sandstorm, sun as a pale disc, dust everywhere softening the contrast",
   bg="dunes in a sandstorm, camels and an armoured truck as faint shapes")

# ---------------------------------------------------------------- NRE
ag(tag="NRE", slug="vulpes", code="Vulpes", name="Livia Moretti",
   role=("seducer and diplomat", "seductora y diplomática"),
   person="a 42-year-old Italian woman: olive skin, thick dark hair styled in a Roman-inspired braided updo, a strong nose, dark red lipstick, heavy-lidded brown eyes",
   expr="regal and amused, a slow, knowing smile",
   clothes="a black evening dress with a crimson toga-like sash over the left shoulder held by a gold laurel fibula",
   detail="a small gold fox-head ring on the hand held near her collarbone, a glass of red wine just out of focus",
   framing="chest-up, centred, the hand with the ring inside the frame",
   camera="eye level from a theatre box, 85mm at f/2; three-quarter turn to the right, eyes to the lens",
   light="warm candlelight and gold reflections from the opera house, deep crimson shadows",
   bg="the red velvet and gold boxes of an opera house in Rome, blurred audience and chandeliers")
ag(tag="NRE", slug="speculator", code="Speculator", name="Dragan Petrović",
   role=("legion scout and commando", "explorador y comando de las legiones"),
   person="a 50-year-old Serbian man: heavy brows, broken nose, close-cropped grey hair, a thick grey stubble, frost on the eyebrows",
   expr="grim and steady",
   clothes="a dark burgundy winter uniform with segmented ballistic plates on the chest, a white snow cape over a crimson cloak pinned with a gold eagle fibula",
   detail="his breath visible as vapour, snowflakes in the stubble",
   framing="head-and-shoulders, placed left of centre, mountains on the right",
   camera="low angle, 35mm at f/4; face to the lens",
   light="cold blue snow light, the low sun behind a ridge giving a thin gold rim light on the cape",
   bg="snow-covered Balkan mountains, pine forest, a ruined stone watchtower")
ag(tag="NRE", slug="mercurius", code="Mercurius", name="Elif Demir",
   role=("courier and hacker of the Bosphorus", "mensajera y hackeadora del Bósforo"),
   person="a 31-year-old Turkish woman: light olive skin, long dark wavy hair blowing in the wind, hazel eyes, a small mole on the cheekbone",
   expr="alert, slightly impatient, about to leave",
   clothes="a dark modern tunic with a short crimson scarf, a small gold winged-sandal pin, a messenger bag strap across the chest",
   detail="a data chip in a gold capsule hanging on a chain at her neck",
   framing="head-and-shoulders, placed on the right third, the Bosphorus on the left",
   camera="eye level on the deck of a ferry, 50mm at f/2; body turned left, head back to the lens",
   light="dusk, the sky orange and violet, warm last sun on her face from the left, gulls in silhouette",
   bg="the Bosphorus at dusk, minarets, domes and a big suspension bridge with crimson banners (no letters)")
ag(tag="NRE", slug="sicarius", code="Sicarius", name="Théo Marchand",
   role=("assassin of the ports", "asesino de los puertos"),
   person="a 38-year-old French man from Marseille: pale olive skin, sharp cheekbones, black hair slicked back with rain, a thin dark moustache, a cold grey stare",
   expr="nothing at all, a perfectly empty face",
   clothes="a black raincoat over a dark burgundy suit, a crimson tie, a gold eagle tie pin",
   detail="rain running down his face, a black leather glove pulling up the coat collar",
   framing="head-and-shoulders, a dark Dutch tilt of 8 degrees; centred",
   camera="slightly high angle, 85mm at f/1.8; face to the lens",
   light="night rain, a single sodium-orange street lamp above left, wet glints, deep black shadows",
   bg="the old port of Marseille at night, wet stones, moored boats and crimson banners")
ag(tag="NRE", slug="augur", code="Augur", name="Andreas Kallas",
   role=("cryptologist who reads patterns", "criptólogo que lee patrones"),
   person="a 67-year-old Greek man: long white curly hair and white beard, a sun-darkened face, deep wrinkles, bright black eyes",
   expr="thoughtful, looking up at something, then catching the viewer's eye",
   clothes="a dark modern tunic with a crimson sash and a gold laurel fibula, an old wool cardigan over it",
   detail="a flock of birds reflected in his eyes and a small augur's curved staff (lituus) of polished metal held against the shoulder",
   framing="bust cut at mid-chest; centred, a lot of sky above",
   camera="low angle, 50mm at f/2.8 looking up at him against the sky; face to the lens",
   light="bright morning Mediterranean light, warm sun from the right, the sky clear blue",
   bg="a rooftop in Athens with the Acropolis far away and a big flock of starlings drawing shapes in the sky")

def out():
    o = []
    w = o.append
    w("PEDIDOS DE RETRATOS - AGENTES DE INTELIGENCIA (40 retratos, 5 por potencia)")
    w("=" * 77)
    w("")
    w("Espías para la agencia de inteligencia de cada meganación: los agentes que")
    w("hoy salen con el retrato genérico del juego base cuando reclutás uno.")
    w("")
    w("Para ChatGPT:")
    w("- Cada bloque ASSET_REQUEST es UNA imagen vertical (proporción 156x210, por")
    w("  ejemplo 624x840), el mismo formato que los retratos que ya están en el juego.")
    w("- Guardar cada imagen con el nombre de `filename` EXACTO.")
    w("- Mismo estilo pintado-fotorrealista de los retratos del mod, pero cada agente")
    w("  tiene su propia cámara, encuadre, luz y escena (no repetir la pose del")
    w("  anterior). La cara tiene que verse completa y leerse aunque la imagen quede")
    w("  chica en el panel de agentes.")
    w("- Sin texto, sin letras, sin marcos.")
    w("")
    w("Para devolver: un .zip por nación (o varios juntos), se lo pasás a Claude y")
    w("los conecta como agentes propios de cada potencia.")
    w("")
    n = 0
    for tag, (nation, agency) in NATIONS.items():
        group = [a for a in A if a["tag"] == tag]
        w("")
        w(f"########## {tag} ({len(group)}) ##########")
        for a in group:
            n += 1
            ident = f"{tag}_agente_{a['slug']}"
            w("")
            w("ASSET_REQUEST")
            w("type: operative_portrait")
            w(f"id: {ident}")
            w(f"filename: {ident}.png")
            w("size: 156x210 (o más grande con la misma proporción)")
            w(f"style: {STYLE}")
            d = (f"WHO: intelligence operative \"{a['code']}\" ({a['name']}), {a['role'][0]} ({a['role'][1]}) of {agency}, "
                 f"{nation}, year 2100. PERSON: {a['person']}. Expression: {a['expr']}. CLOTHING: {a['clothes']}. "
                 f"DETAIL: {a['detail']}. FRAMING: vertical 3:4 portrait (for example 624x840); {a['framing']}. "
                 f"CAMERA: {a['camera']}. LIGHT: {a['light']}. BACKGROUND: {a['bg']}; recognisable but softer than the face.")
            w(f"description: {d}")
            w("transparent_background: false")
    assert n == 40, n
    return "\n".join(o) + "\n"

if __name__ == "__main__":
    open(sys.argv[1], "w", encoding="utf-8").write(out())
