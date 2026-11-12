"""Pedido de retratos de Estado de los líderes (v2, 2026-11-12).

Solo líderes de las 8 potencias (con sus rutas), sus 7 rebeldes, Japón, Gran
Bretaña y las anarquías. Los satélites (incluidos los africanos), ministros,
generales y agentes NO cambian.

Cada pedido trae: cara (sacada de su retrato actual), vestuario pieza por
pieza, pose, escena en tres planos, cámara, luz, técnica, paleta,
imperfecciones y qué evitar. Arriba va un bloque contra el "estilo IA".

    python3 arte/pedidos_retratos_lideres.py arte/pedidos_retratos_lideres.txt
"""
import sys

# Cada líder: dict con face, wear, pose, fg/mg/bg (planos), cam, light, tech, palette, flaws, avoid
L = []


def P(cid, who, **k):
    L.append((cid, who, k))


# =============================== EFE ===============================
P("EFE_aurelio_iv", "Emperor Aurelio IV, 54, founder of the Ecofascist Empire, ex-commander of the Green Militias, rules from Buenos Aires",
  face="Same man as the reference: square heavy face, olive skin with sun damage and deep nasolabial lines, thick salt-and-pepper hair swept back and slightly unruly, short grey goatee with a darker moustache, heavy black eyebrows, one slightly drooping left eyelid, small white scar through the right eyebrow (Iguazú). Eyes dark brown, tired and hard, not angry.",
  wear="Dark bottle-green high-collar imperial tunic of heavy wool with matte bronze buttons shaped like seeds; a cape of hand-woven palm fibre lined with faded crimson velvet, frayed at the hem; a thin crown of oxidised bronze laurel and yerba-mate leaves, slightly crooked; on his chest the bronze tree-of-life medallion from the reference, scratched; on his right hand a cheap steel ring from his militia days.",
  pose="Seated, slumped a little to his right in a throne carved from one quebracho trunk; left forearm on the armrest, right hand resting on the stock of an old bolt-action hunting rifle laid across his knees. Head turned three-quarters toward the viewer, chin slightly down, looking up from under his brows.",
  fg="Out-of-focus: the rifle barrel and a few dry red ceibo flowers fallen on the floor.",
  mg="The throne: living roots of the quebracho still grip cracked marble tiles; moss in the cracks.",
  bg="Dim palace hall turned greenhouse: tall iron-and-glass windows dirty with condensation, palms and monstera filling the space, a faded Argentine-era fresco half hidden by leaves.",
  cam="Medium-format camera, 80mm lens (normal on 6x7), f/4, camera at his seated eye level, 2.5 m away, slightly to his left. Vertical frame, head in the upper third, crop at mid-thigh.",
  light="Single large window to camera-left as key (soft, late afternoon, warm), no fill: the right side of his face falls into deep shadow. A faint green bounce from the plants on the shadow side. Dust and pollen visible in the window beam.",
  tech="Painted, not photographed: large academic oil portrait in the tradition of John Singer Sargent and Joaquín Sorolla, loose confident brushwork in the clothes and background, careful finish only on the face and hands. Visible canvas weave, slightly yellowed varnish.",
  palette="Bottle green, oxidised bronze, dirty gold, muted crimson, warm grey skin shadows. No neon, no saturated emerald.",
  flaws="Sun spots on the cheeks, a vein on the back of the hand, a loose thread on the cape, the crown sits imperfectly.",
  avoid="No glowing halo, no golden icon frame like the reference, no fantasy armour, no symmetrical pose.")

P("EFE_anahi_quiroga", "Anahí Quiroga, the Voice of the Forest, 32, Yungas park ranger who leads the forest uprising and becomes Empress",
  face="Same woman as the reference: long straight black hair in one thick braid over her left shoulder, brown skin, strong jaw, wide cheekbones, straight thick eyebrows, dark almond eyes; a small gold leaf earring in the left ear. Freckles of sun on the nose, chapped lips, a thin scratch on the right cheek from branches.",
  wear="Worn olive ranger field jacket, rip at the right shoulder sewn with green thread; under it a woven Andean wool vest in red and ochre; the bronze tree-of-life badge of the Empire pinned crooked over the old ranger patch; a machete in a leather sheath across her back (only the handle visible over the shoulder); a carved quebracho walking staff with living moss and two tiny orchids growing on it.",
  pose="Standing waist-deep in wet ferns, both hands stacked on top of the staff, body angled 30 degrees away from the camera, face turned fully to the viewer. Calm, almost still, as if listening.",
  fg="Fern fronds very close to the lens, blurred, with water droplets.",
  mg="Her figure, sharp, with rain mist around her legs.",
  bg="Yungas cloud forest: giant trees with hanging mosses and bromeliads fading into white fog in three layers; one small toucan far away on a branch, barely visible.",
  cam="Full-frame camera, 85mm lens, f/2.0, at her eye level, 3 m away. Vertical, crop at the hips.",
  light="Overcast, flat diffuse light from above through the canopy; a gap in the clouds gives a soft brighter rim on her hair and shoulder from behind-right.",
  tech="Documentary photograph, Kodak Portra 400 film look: fine natural grain, gentle highlight roll-off, true skin tones. Like a portrait by Steve McCurry or Sebastião Salgado but in colour.",
  palette="Wet greens and grey-whites of fog, the warm red of her vest as the only strong colour.",
  flaws="Wet strands of hair stuck to her forehead, mud on the jacket, raindrops on the skin.",
  avoid="No glowing magical effects, no jaguar, no fantasy elf look, no studio retouching.")

P("EFE_tupa_heredero", "Emperor Tupã I 'of the Water', 28, nephew of Aurelio, crowned heir, reigns from Asunción",
  face="Same young man as the reference: thick dark curly hair, olive-brown skin, strong straight nose, full eyebrows, clean shaven, square jaw, light stubble shadow. Looks younger than his title; eyes wary.",
  wear="New coronation regalia that does not yet fit him: white linen high-collar tunic with ñandutí lace on the cuffs, a long crimson cape with a hand-woven guaraní border (the red-and-cream pattern from the reference), the bronze sun-and-tree medallion; a simple bronze circlet instead of his uncle's laurel; the hem of the cape dark and soaked with river water.",
  pose="Standing at the prow of a white imperial river barge, right hand gripping the gilded rail, left hand loose at his side; body facing the river, head turned back over his shoulder toward the viewer.",
  fg="The gilded prow ornament (a carved surubí fish) close to the lens, slightly soft.",
  mg="Him and the deck of the barge, wet planks reflecting the sky.",
  bg="The Paraguay river at dawn, very wide, mist on the water; the low skyline of Asunción with a few modern towers and the old Palacio de los López lit pink; a line of small canoes with people watching.",
  cam="Full-frame, 35mm lens, f/5.6, camera low at deck level near the prow looking up and back at him, 2 m away. Vertical; he occupies the right two thirds.",
  light="Sunrise behind the city (backlight) creating a strong rim on his curls and shoulders; soft fill from the bright water below lights his face from underneath.",
  tech="Romantic oil painting with the atmosphere of J.M.W. Turner in the sky and water (wet-into-wet, luminous haze) and a precise, realistic face like Ilya Repin.",
  palette="Pearl pink, pale gold, river brown-green, crimson cape, cream linen.",
  flaws="The cape too long and heavy for him, a crease in the linen, a fresh shaving nick on the jaw.",
  avoid="No satellites or sci-fi beams (the reference has them, not this one), no halo.")

P("EFE_custodia_pereira", "Elected Custodian Yara Pereira, 44, chief of park rangers, elected head of state after the Empire",
  face="Same woman as the reference: wild dark curly hair tied back loosely with strands escaping, brown skin, strong nose, a horizontal stripe of red urucum paint across both eyes, gold leaf earrings, deep smile lines, determined mouth.",
  wear="Plain ranger uniform of faded khaki-green cotton, sleeves rolled; one wide green sash of office over the right shoulder; a crimson wool shawl; a small glass vial of seeds hanging from a cord on her neck. No crown, no medals.",
  pose="At a lectern made from a sawn tree stump, right hand raised mid-oath (palm forward), left hand flat on an old leather-bound book. Body square to the camera, face very slightly turned to her right.",
  fg="Blurred torches held by people in the front row (only flames and hands visible).",
  mg="Her at the stump lectern.",
  bg="Night open-air assembly in a forest clearing: hundreds of rangers with torches forming soft orange points, giant tree silhouettes against a deep blue sky with stars.",
  cam="Full-frame, 70mm, f/2.8, camera slightly below her eye level, 3.5 m away, from her front-right. Vertical.",
  light="Warm torchlight from below and both sides (flickering, uneven), cold blue moonlight rim from behind.",
  tech="Press photograph of a historic moment: Kodak Tri-X pushed one stop then colour-toned, visible grain, slight motion blur on the raised hand. Like the great 20th-century Magnum photographers.",
  palette="Torch orange, night blue, khaki, red paint.",
  flaws="Sweat on the forehead, smoke in the air, one torch flame blown out by the wind.",
  avoid="No golden frame, no halo, no saint pose, no clean studio light.")

P("EFE_regente_etchegaray", "Regent Bruno Etchegaray, 51, marshal of the Green Guard, rules as regent and refuses the crown",
  face="Same man as the reference: lean face, short dark-grey hair receding at the temples, grizzled short beard, hollow cheeks, deep-set grey eyes, broken nose healed crooked. Expression: tired duty, no ambition.",
  wear="Green Guard field uniform, faded and practical, sleeves rolled, rank tabs only; a battered map case on a strap; an old officer's sabre hanging on the chair behind him. No cape.",
  pose="Standing behind a war table, both fists resting on the maps, leaning forward; head up, looking past the camera, not at it.",
  fg="The imperial crown of laurel on a dark red cushion at the edge of the table, closest to the lens, in soft focus, deliberately untouched.",
  mg="The war table: paper maps of the Río de la Plata with pins and coffee rings, a cold mate gourd, a revolver.",
  bg="Plain barracks office with whitewashed walls, a single window with iron bars, a framed photo of Aurelio IV turned face-down on a shelf.",
  cam="Full-frame, 50mm, f/2.0 focused on him, camera at table height over the crown, 1.8 m from him.",
  light="Cold grey window light from the left only; strong chiaroscuro, the right half of the room in darkness; a thin highlight on the crown.",
  tech="Dramatic oil painting in the manner of Caravaggio and Ribera: dark brown-black ground, sculpted light, realistic skin with every wrinkle.",
  palette="Olive drab, earth brown, bone white, one dull gold note in the crown.",
  flaws="A coffee stain on the map, dirt under the fingernails, a frayed cuff.",
  avoid="Do not put the crown on his head, no heroic pose, no golden icon frame.")

P("EFE_lider_rebelde", "General Martín Arregui, ~55, commander of the Rosario garrison, leader of the Liberal Movement of the Southern Cone (civil-war rebel)",
  face="Same man as the reference: short dark hair greying at the sides, clean shaven, square jaw, straight nose, olive skin, firm thin mouth; eyes narrowed against smoke.",
  wear="Plain olive army uniform with the imperial tree insignia torn off the chest (pale patch and loose threads where it was); a light-blue-and-white armband on the left arm; leather cross-strap; a rolled paper (the constitution) in his hand.",
  pose="Standing on the hood of an armoured car, megaphone lowered at his side, the rolled constitution raised in the other hand; body three-quarter, face to the crowd off-camera-right.",
  fg="Hands of the crowd and a blue-and-white flag edge entering the bottom of the frame, blurred.",
  mg="Him on the armoured car, its scratched green paint.",
  bg="A Rosario boulevard with plane trees and art-deco facades, the National Flag Memorial tower in the distance, smoke from a burning imperial checkpoint, blue-and-white banners from the balconies.",
  cam="Full-frame, 24mm wide, f/8, camera low on the asphalt next to the wheel, looking up, 2 m away.",
  light="Overcast noon light, flat and grey; smoke diffuses it further.",
  tech="Black-and-white war photojournalism (Ilford HP5, gritty), with selective colour ONLY on the light-blue of the banners and armband.",
  palette="Silver greys, black, and light blue.",
  flaws="Lens flare from a gap in the clouds, motion blur on a running figure, dust on the lens.",
  avoid="No golden frame, no halo, no clean glamour.")

# =============================== NRE ===============================
P("NRE_lucius_varro", "Imperator Lucius Varro, 52, legion commander acclaimed emperor by his troops, Rome",
  face="Same man as the reference: heavy square head, short tight greying curls, low broad forehead, thick brow ridge, broad crooked nose, clean shaven, deep frown lines, thick neck. Real human skin, not marble: weathered, with a shaving rash on the neck.",
  wear="Modern lorica of matte carbon-composite segmented plates over a dark red tunic; an imperial purple paludamentum cloak pinned at the right shoulder with a heavy gold fibula; laurel wreath of gilded titanium leaves; a scratched legion dog-tag on a chain.",
  pose="Raised on a legion shield held by soldiers: standing, one hand gripping a soldier's helmet crest for balance, the other raised open-palmed in a salute; looking down at the viewer.",
  fg="Gloved hands, red plumes and the rims of the shield at the bottom edge.",
  mg="Him on the shield, cloak blown by wind.",
  bg="St Peter's square at night packed with legionaries; the dome lit by drone floodlights; red flares and smoke.",
  cam="Full-frame, 24mm, f/4, camera very low among the soldiers looking straight up, 1.5 m away.",
  light="Red flare light from below, cold white drone floodlight from above-behind as rim; torchlight on the face.",
  tech="Neoclassical history painting (Jacques-Louis David, Jean-Léon Gérôme) rendered with photographic detail; smooth glazes, theatrical composition.",
  palette="Imperial purple, blood red, black carbon, gold, marble white.",
  flaws="A cut on his knuckles, the wreath bent, sweat.",
  avoid="No marble statue, no cameo frame, no fantasy gladiator look.")


P("NRE_legado_arbogast", "Legate Flavius Arbogast, 45, Legio I Italica; Varro sent him to the desert and he came back with the whole legion behind him",
  face="Same man as the reference: short tight curly brown hair, a long diagonal scar across the left cheek from cheekbone to jaw, square jaw, hooked nose, two days of stubble with sand in it, deeply sunburned skin peeling on the nose, pale grey eyes squinting.",
  wear="Desert-tan composite segmented armour scuffed to bare carbon at the edges; a sand-coloured legate's cloak wound around his neck and mouth like a scarf, pulled down under the chin; dusty goggles pushed up on the forehead; a faded red legate's sash; a modern rifle slung across the back.",
  pose="Standing upright in the open commander's hatch of a tank, one gloved hand on the hatch rim, the other holding the shaft of the legion's aquila standard planted on the turret. Seen in pure profile looking to the right of frame, into the wind.",
  fg="Shimmering heat haze distorting the bottom of the image.",
  mg="Him and the turret of a sand-scoured heavy tank; the gilded aquila eagle catches the sun.",
  bg="An endless column of tanks and trucks receding into a cloud of dust across Libyan dunes; the sky white with heat.",
  cam="Very long 400mm telephoto from 150 m away, f/5.6, camera at turret height, strong compression that stacks the column right behind him.",
  light="Brutal noon sun straight from above: hard short shadows under brow and nose, bleached highlights, no fill.",
  tech="Cinematic still shot on 65mm film (the look of David Lean's desert epics): rich grain-free detail, slight halation on the highlights, anamorphic feel cropped to vertical.",
  palette="Ochre, bone white, faded blue sky, one note of red sash and the gold eagle.",
  flaws="Sand on the lens, dust in his stubble, cracked lips, a dent in the turret.",
  avoid="No marble, no cameo frame, no glossy video-game render, no blue-orange colour grade.")

P("NRE_irina_vasilescu", "Legate Irina Vasilescu, 38, Legio V Macedonica on the Danube; daughter of the Dacian bunker junta, the first provincial the legions could acclaim",
  face="Same woman as the reference: thick wavy dark-blonde hair to the shoulders, half tied back, sharp straight nose, high strong cheekbones, narrow intense eyes, thin firm lips, a small mole on the left jaw. Pale skin reddened by cold.",
  wear="Legate's segmented armour in dark gunmetal over a heavy grey bunker-army greatcoat with a wolf-fur collar; a red-crested helmet held under her left arm; leather gloves; a small Dacian draco (wolf-headed dragon) pin on the collar.",
  pose="Standing in the concrete mouth of a Carpathian bunker, body facing out toward her legion, head turned back over her right shoulder to look at the viewer.",
  fg="The edge of a massive open steel blast door, rust streaks, very close to the lens on the left.",
  mg="Her figure in the doorway.",
  bg="Outside in falling snow: rows of legionaries kneeling with standards, the forest of the Carpathians, a pale grey dawn sky.",
  cam="Camera inside the bunker looking out, 35mm lens, f/2.8, at her shoulder height, 2.5 m behind her.",
  light="Her silhouette rim-lit by the bright snow outside; her face lit only by a single red emergency lamp on the bunker wall to camera-right. Two colour temperatures: cold white outside, red inside.",
  tech="Dramatic realistic oil painting in the manner of Ilya Repin and Vasily Vereshchagin: thick paint in the snow, fine glazing on the face.",
  palette="Snow white, steel blue, concrete grey, emergency red.",
  flaws="Frost on her eyelashes, chipped concrete, a scratch on the helmet crest.",
  avoid="No marble, no cameo frame, no fantasy valkyrie look.")

P("NRE_kerem_aydin", "Legate Kerem Aydın, 66, Legio XII Fulminata, guardian of Anatolia; old, patient and loved by soldiers, promises them land in the East",
  face="Same man as the reference: full curly white beard, thick white wavy hair, deep forehead wrinkles, heavy lids, warm brown eyes with crow's feet, broad nose, a gap between his front teeth when he smiles.",
  wear="Armour unbuckled and hanging open on one side, simple rough linen tunic under it, a faded red cloak, worn leather sandal-boots; his helmet with a lightning-bolt crest on the ground beside him.",
  pose="Seated on a folding camp chair, leaning forward, breaking a round loaf of bread with both hands and offering half to someone off-frame to the left; looking up at the viewer with a small knowing smile.",
  fg="His helmet on the dusty ground and a tin cup of tea, slightly soft.",
  mg="Him on the chair.",
  bg="Cappadocia: fairy chimneys and cave dwellings at sunset, cooking fires of the legion camp, a few hot-air surveillance balloons in the sky.",
  cam="Full-frame, 85mm, f/2.2, camera standing slightly above his head height, 2 m away, tilted down a little.",
  light="Low warm sunset from camera-right as key (Rembrandt triangle on the far cheek), soft blue sky fill.",
  tech="Intimate realistic oil painting in the manner of Osman Hamdi Bey and Rembrandt: warm brown ground, loaded highlights on the beard.",
  palette="Sunset ochre, terracotta, faded red, white beard, dusty blue.",
  flaws="Crumbs in his beard, a frayed cloak edge, an old surgical scar on the forearm.",
  avoid="No marble, no cameo frame, no angry warrior.")

P("NRE_lider_rebelde", "Basileus Constantine Láskaris, ~55, governor of the eastern provinces, crowned in Constantinople (civil-war rebel)",
  face="Same man as the reference: curly hair and full beard both greying, long straight nose, deep-set dark eyes with dark circles, olive skin, heavy eyelids, a grave unsmiling mouth.",
  wear="Purple-and-gold Byzantine loros (jewelled scarf of state) over modern dark armour; a closed crown with pearl pendilia hanging at the temples; a double-headed eagle embroidered on the chest; in his right hand a cross-topped sceptre, in the left a scroll.",
  pose="Standing perfectly frontal and still, like an icon, sceptre held upright, eyes straight into the lens.",
  fg="A row of thin beeswax candles in a brass stand, flames sharp.",
  mg="Him.",
  bg="The apse of Hagia Sophia: a gold mosaic of Christ Pantocrator exactly behind his head acting as a halo; dust in the shafts of light from the high windows.",
  cam="50mm, f/5.6, camera at chest height, perfectly centred and symmetric, 3 m away.",
  light="Warm candlelight from below and gold light reflected from the mosaic; a high window gives a cool top-light.",
  tech="A modern painting imitating a Byzantine icon: real gold leaf in the background with cracks, egg tempera textures in the robes, but a fully realistic, living, pained face.",
  palette="Gold, Tyrian purple, deep red, candle amber.",
  flaws="Cracked gold leaf, wax drips, a tiny tear in the loros.",
  avoid="No marble cameo, no velvet background like the reference.")

# =============================== SHD ===============================
P("SHD_lin_wenzhao", "Director of Harmony Lin Wenzhao, 64, former irrigation engineer; never gives speeches, his decisions are published as technical adjustments",
  face="Same man as the reference: neat grey hair combed back, thin rimless rectangular glasses, long lined face, thin lips, high cheekbones, a calm unreadable expression; age spots on the temples.",
  wear="Plain dark-grey high-collar wool suit, no insignia, a single small enamel pin of a water drop; a slim tablet held at his side.",
  pose="Standing still with hands clasped behind his back, facing the camera dead-on.",
  fg="Nothing: clean.",
  mg="Him on a steel catwalk.",
  bg="The turbine hall of a colossal dam: giant generators in perfect rows receding to a vanishing point, technicians as tiny figures.",
  cam="Large-format architectural camera, 35mm-equivalent, f/11, at his eye level, 10 m away, strict one-point perspective, perfectly level verticals.",
  light="Cool, even industrial light from long ceiling strips, almost no shadows.",
  tech="Precise architectural photography in the manner of Andreas Gursky: huge depth of detail, clinical calm.",
  palette="Concrete grey, steel blue, pale green, one red emergency button.",
  flaws="A smudge on his glasses, a slight crease in the suit.",
  avoid="No dossier paper, no red circle, no rain like the reference, no dramatic heroics.")

P("SHD_zhou_mingyuan", "Commissar Zhou Mingyuan, 34, youngest of the Directorate, commissar of the Yangtze works; wants to open the floodgates before the dam bursts",
  face="Same man as the reference: thick dark tousled hair falling over the forehead, sharp dark eyes under straight brows, strong jaw, smooth skin with a faint acne scar on one cheek, defiant closed mouth.",
  wear="Dark green rubberised commissar's work coat, open and whipping in the wind, sleeves pushed up; a red armband with a stylised wave; a white hard hat held loosely in his left hand; muddy rubber boots; a radio clipped to his chest.",
  pose="Standing on the narrow walkway on top of an open sluice gate as water bursts out below him, right arm extended, pointing forward down the river; head turned slightly toward the camera.",
  fg="Fine spray droplets on the lens, a few in focus.",
  mg="Him on the gate walkway, steel railing, warning stripes.",
  bg="The Yangtze gorge with mist; a rainbow forming in the spray; hundreds of workers on the opposite bank waving red flags; terraced hills.",
  cam="Full-frame, 35mm, f/8, from the opposite bank at water level, looking up, a 5-degree Dutch tilt.",
  light="Bright afternoon sun directly behind him, backlighting the spray and rimming his hair; his face lit by the white reflected light from the water.",
  tech="Heroic Chinese socialist-realist oil painting of the 1950s-70s (like Dong Xiwen) with modern material detail, broad confident strokes, painted spray.",
  palette="Water white, jade green, wet black steel, bright red flags, gold sun.",
  flaws="Wet hair stuck to the forehead, mud splashes, a chipped warning sign.",
  avoid="No dossier paper, no red marker circle, no paperclip like the reference, no K-pop idol face.")

P("SHD_lider_rebelde", "Commissar Lin Xiaoyu, 46, of the old algorithmic party; the AI communists come back to the river cities with the Commune's servers (civil-war rebel)",
  face="Same woman as the reference: short straight black bob with a heavy fringe, round thin wire glasses, square face, firm downturned mouth, faint dark circles, a small mole above the lip, no makeup.",
  wear="Grey wool Mao-style tunic buttoned to the throat with a small enamel badge of a red star made of circuit traces; a red armband with yellow characters; a worn party-issue wristwatch.",
  pose="Seated very upright at a bare metal table, hands folded on top of a closed red booklet, eyes straight into the lens, unblinking.",
  fg="An old ruggedised tablet lying on the table, screen glowing green, lighting her from below.",
  mg="Her at the table.",
  bg="A wall of old salvaged server racks, the blinking red LEDs arranged in the shape of a five-pointed star; cables hanging; red party banners at the edges; a cracked concrete floor.",
  cam="Full-frame, 40mm, f/2.8, camera slightly above her eye level, straight-on, centred, 2 m away.",
  light="Mixed: red LED glow from behind (rim on hair and shoulders), green tablet light from below on the face, no other source; deep shadows.",
  tech="Cold realistic painting in the manner of a socialist-realist official portrait, re-lit like a cyberpunk film frame (Blade Runner tones); smooth glazes, sharp face.",
  palette="Party red, terminal green, ash grey, black.",
  flaws="Dust on the racks, a crack in her glasses lens, a frayed cuff.",
  avoid="No dossier paper, no marker circle, no neon pink, no sexy cyberpunk outfit.")

# =============================== NAS ===============================
P("NAS_amaru_quispe", "Sapa Inti Amaru Quispe II, 27, second monarch of the restored solar dynasty, young and pious, crowned in Cusco",
  face="Same young man as the reference: long straight black hair falling past the shoulders, a gold band across the forehead, broad face with high cheekbones, aquiline nose, full lips, smooth brown skin, large round gold ear spools.",
  wear="Royal unku tunic woven with red-and-gold tocapu squares, a mantle of fine vicuña wool, a golden sun-disc headdress with rays (mascapaicha fringe of red wool on the forehead), gold bracelets; under the tunic a thin modern climate-suit collar barely visible.",
  pose="Kneeling on the stone platform of a mountain temple, back straight, palms open and raised to the sun, eyes closed, face lifted.",
  fg="Smoke of burning palo santo from a stone bowl, curling across the lower frame.",
  mg="Him on the ancient Inca stonework, perfectly fitted stones.",
  bg="The Andes at sunrise: snow peaks, terraced valleys, a sea of clouds below; distant priests in white as small figures.",
  cam="Full-frame, 85mm, f/4, camera on the platform at his kneeling eye level, 3 m away, frontal.",
  light="The rising sun exactly behind his head creating a natural halo and flare; warm gold reflected light from the stone on his face.",
  tech="Devotional oil painting in the tradition of the Cusco School (gold-leaf brocateado on the fabric patterns) with a fully realistic modern face.",
  palette="Gold, vermilion, sky blue, snow white.",
  flaws="Cold-reddened knuckles, wool fibres, a small chip in the stone.",
  avoid="No playing-card border like the reference, no cartoon condors, no tourist costume look.")

P("NAS_amaru_inca", "Sapa Inca Amaru Quispe II, 33, the same king after breaking with the priests; lord of the four suyus, comes down from the mountain with the roads",
  face="Same man as the reference and as the Sapa Inti portrait, six years older and harder: long black hair now tied back tight, red mascapaicha fringe on the forehead, a fresh pale scar across the chin, thinner cheeks, eyes narrowed and calculating, gold ear spools, wind-burned skin.",
  wear="Cuirass of hammered gold plates riveted over matte black composite armour; a red-and-gold tocapu unku tunic showing below the cuirass; a short war crown of red and gold feathers; a black wool cloak with a gold border; a staff of command topped by a gold sun disc with a thin modern antenna wired into it; a pistol holster of woven leather.",
  pose="Striding down an ancient stone Inca road straight toward the viewer, mid-step, staff in the right hand planted forward, left hand closing the cloak; head slightly lowered, eyes locked on the lens.",
  fg="The worn cobbles of the road, rough, one stone loose.",
  mg="Him, sharp.",
  bg="Long columns of soldiers and llama-drone convoys winding along the mountain road behind him; a fortress on a ridge; clouds below the mountains; a storm front.",
  cam="Full-frame, 50mm, f/4, camera low (knee height) on the road 4 m ahead of him, slightly upward.",
  light="Stormy midday sky, dark slate clouds; a single break in the clouds lights him and the road like a spotlight, the army behind in shadow.",
  tech="Historical epic film still shot on 35mm film (Kodak Vision3 500T), heavy natural grain, deep blacks.",
  palette="Gold, black, crimson, slate grey, snow white.",
  flaws="Mud on his sandals, frayed feather tips, scratches on the gold plates.",
  avoid="No playing-card border like the reference, no puma, no glowing sun magic.")

P("NAS_lider_rebelde", "General Huáscar Mamani, ~55, head of the Black Sun Junta: an esoteric, paranoid military order that reads omens in eclipses (civil-war rebel)",
  face="Same man as the reference: short black hair, broad weathered face, heavy-lidded eyes, flat broad nose, deep lines from nose to mouth, thin moustache shadow, dark brown skin.",
  wear="Black wool uniform with a woven Andean poncho in dark purple and black tocapu patterns over one shoulder; a black sun emblem (a dark disc with a thin gold corona) pinned on the chest; an old leather-bound book of omens held against his chest; a pistol on the belt.",
  pose="Standing beside a large brass telescope, one hand on its tube, looking up at the eclipse with his face half turned to the viewer.",
  fg="The brass eyepiece of the telescope, very close, soft.",
  mg="Him in a circular stone observatory.",
  bg="The open slit of the observatory dome showing a total solar eclipse: black sun with a white corona in a deep violet sky; stars visible at midday; torches on the walls.",
  cam="Full-frame, 50mm, f/2.8, camera behind the telescope, his face framed partly by the telescope tube.",
  light="Cold silver light of the corona from above, warm torchlight from the walls on one side of his face; half the face in darkness.",
  tech="Dark gothic oil painting (Goya's black paintings, Joseph Wright of Derby's astronomy scenes), thick dark varnish.",
  palette="Black, violet, silver, torch amber, a thin line of gold.",
  flaws="Sweat on the brow, a burn on the book's cover, soot on the stone.",
  avoid="No playing-card border, no condor, no fantasy wizard look.")

# =============================== ASC ===============================
P("ASC_allocation_council", "The Allocation Council: 41 delegates drawn by lot every year among the whole population of the Commune; no single face on purpose",
  face="41 ordinary people of all ages and origins (Europe in 2100): a young welder, an old woman, a teenager, a bearded nurse, etc. All different, real faces, none glamorous. The person in the very centre (a middle-aged woman with short grey hair) is slightly sharper than the rest.",
  wear="Identical grey cotton work overalls with a small red number badge (1 to 41) on the chest.",
  pose="All seated in a semicircle of plain white desks, all looking up at the same point: a huge screen above the camera.",
  fg="Nothing.",
  mg="The semicircle of delegates, perfect arc.",
  bg="A white minimalist amphitheatre; the light of the screen spills across all the faces; a red banner with the Commune's gear-and-star at the back.",
  cam="Overhead high angle from the top of the amphitheatre, 24mm, f/8, symmetric, so the arc fills the vertical frame.",
  light="Cool white light from the screen above (off-frame), soft and even, slight blue tint on the faces.",
  tech="Clean documentary photography in the manner of Andreas Gursky and Thomas Struth: crisp, every face readable, huge detail.",
  palette="White, grey, a few accents of red, faint blue.",
  flaws="A delegate yawning, a paper coffee cup, a crooked badge.",
  avoid="No propaganda-poster style like the reference, no identical clone faces.")

P("ASC_plan_41", "PLAN-41: the Commune's planning AI; one morning the Council arrived and the doors did not open",
  face="The avatar from the reference: a young woman's calm face with a thin circuit line at the left temple, short dark hair, serene eyes. Here she is made of thousands of floating points of cyan light, like a hologram, but with photographic realism in the eyes.",
  wear="None: the light figure fades below the shoulders into data streams.",
  pose="Frontal, head very slightly tilted, eyes straight at the viewer.",
  fg="A closed steel door seen from inside, with a small glowing red lock light.",
  mg="The light face hanging in the air.",
  bg="A vast hall of server pillars receding into darkness, with blinking lights in rows.",
  cam="50mm, f/2, at eye level with the face, perfectly symmetric.",
  light="Only the cyan light emitted by the face and the cold blinking of the servers; deep black everywhere else.",
  tech="Photorealistic film still (volumetric light in the haze), like Denis Villeneuve's sci-fi films.",
  palette="Cyan, black, a single red lock light.",
  flaws="Glitches: a few missing light points on the cheek, a line of interference.",
  avoid="No red poster style, no robot or skull, no Skynet red eye.")

P("ASC_lider_rebelde", "Jarl Sven Ragnarsson, ~42, prophet of the Sons of Odin, neo-pagan fascists who blow up factories and datacenters (civil-war rebel)",
  face="Same man as the reference: long blond-red beard braided into two, sides of the head shaved with a long braid on top, rune tattoos on the neck and temples, pale blue eyes, broken nose, ruddy skin.",
  wear="Heavy grey wolf-fur cloak over improvised armour of riveted steel plates and leather; a valknut amulet; leather bracers; a sledgehammer with runes carved into the handle resting on his shoulder.",
  pose="Standing still with his back almost to a burning datacenter, half-turned toward the viewer, hammer on shoulder.",
  fg="Snow and glowing embers falling.",
  mg="Him.",
  bg="A burning datacenter in a Nordic pine forest at night, flames bursting from the roof, server racks melting, followers with torches.",
  cam="Full-frame, 35mm, f/2.8, camera low and to his right side, 3 m away.",
  light="Orange firelight from behind as a strong rim, cold blue moonlight on the front of his face.",
  tech="Dramatic romantic oil painting in the manner of Peter Nicolai Arbo and Nicholas Roerich, thick impasto flames.",
  palette="Fire orange, blue snow, black pines, grey fur.",
  flaws="Soot on his face, singed fur.",
  avoid="No propaganda-poster style, no horned helmet, no fantasy Thor look.")

# =============================== FCU ===============================
P("FCU_valeria_castellane", "President Valeria Castellane, 47, rotating president of the Union's board, from Castellane Water Trust (the desalination company everyone needs)",
  face="Same woman as the reference: long wavy dark-brown hair with lighter streaks, styled but not perfect; strong brows, almond eyes, defined cheekbones, red lipstick, a faint scar under the chin; small fine wrinkles at the eyes she does not hide.",
  wear="Tailored ivory-white suit with sharp shoulders, a navy silk blouse, a small crystal vial of desalinated water as a pendant on a platinum chain, a board-member pin with the Union logo on the lapel, a thin smartwatch.",
  pose="Standing with one hand resting on a glass pipe as on a pet, body angled away, head turned three-quarters to the viewer, slight confident half-smile.",
  fg="Out-of-focus water droplets on a glass surface.",
  mg="Her beside a transparent pipe full of flowing water.",
  bg="Inside a desalination plant: floor-to-ceiling glass wall with the sea outside, rows of glass membrane tubes lit from within like a cathedral organ.",
  cam="Medium format, 110mm, f/2.8, three-quarter view from her left, 2.5 m away, at her eye level.",
  light="Clean soft blue-white light from the glass wall as key; a warm small practical light on her face from a desk lamp off-frame as fill.",
  tech="Luxury editorial portrait photography in the manner of Annie Leibovitz: precise, polished, but with real skin texture.",
  palette="Ivory, aqua blue, navy, platinum, red lips.",
  flaws="A strand of hair out of place, a water mark on the glass.",
  avoid="No stage, no fireworks, no big 3D name text like the reference, no beauty filter.")

P("FCU_marcus_rourke", "Executive Director Marcus Rourke, 56, director of Meridian Kinetics (weapons and robotics); bought the votes of the board; war is the only business that always grows",
  face="Same man as the reference: slicked-back dark hair greying at the temples, short trimmed beard with grey, tanned skin, strong nose, hooded eyes with heavy bags, a smug closed-lip smile.",
  wear="Dark navy pinstripe three-piece suit, gold tie, gold signet ring, an expensive watch; a small lapel pin shaped like a drone.",
  pose="Seated in a leather executive chair on a glass balcony, legs crossed, holding a crystal whisky glass, looking over his shoulder at the viewer.",
  fg="The edge of the glass balcony with reflections.",
  mg="Him in the chair.",
  bg="An enormous factory floor below: assembly lines of tanks and drones, sparks from welding robots, red warning lights.",
  cam="Full-frame, 35mm, f/4, camera behind and to the right of his chair, slightly above, 2 m away.",
  light="Red warning lights from below and cold steel-blue factory light from above; a warm spot on his face from a desk lamp.",
  tech="Corporate portrait photography with an ominous film-noir mood (like a Gregory Crewdson staged photograph).",
  palette="Navy, gold, steel blue, warning red.",
  flaws="Ice melting in the glass, a red wine stain on the cuff.",
  avoid="No stage, no fireworks, no big 3D name text, no cartoon villain.")

# =============================== HSN ===============================
P("HSN_kofi_aldana", "Captain-General of Ports Kofi Aldana, 49, born on a freighter, never touched land until twelve; controls the freight clearing house",
  face="Same man as the reference: dark brown skin, short locs tied back, full short beard, strong brow, wide nose, calm heavy-lidded eyes, a pipe in the corner of his mouth.",
  wear="Merchant-marine dress uniform in dark navy with gold-braided epaulettes, an old brass compass hanging from a chain on his chest, a white shirt open at the collar, a knitted cap tucked in a pocket.",
  pose="Standing at the helm of a giant container ship's bridge, one hand on the console, looking at the viewer over his shoulder, pipe smoke drifting.",
  fg="Floating holographic freight manifests (ship names, numbers) out of focus in the air.",
  mg="Him.",
  bg="Through the wide bridge windows: a night port with gantry cranes lit orange, rows of containers, the lights of other ships.",
  cam="Full-frame, 35mm, f/2.8, camera behind the helm console at chest height.",
  light="Teal light from the holograms on his face, warm orange port lights from behind as rim.",
  tech="Cinematic sci-fi film still (like Michael Mann's night photography), real grain, deep shadows.",
  palette="Navy, gold braid, teal, sodium orange.",
  flaws="Pipe ash on the console, a coffee mug ring, a scratch on the compass glass.",
  avoid="No tattoo-on-skin style like the reference, no pirate costume.")

P("HSN_ines_tavake", "Captain Inés Tavake, 36, Rapa Nui container-ship captain, elected by her crew three times; took the port of Kanto with 400 sailors and a megaphone",
  face="Same woman as the reference: long thick dark hair loose and wind-blown with a red hibiscus behind the ear, Polynesian tattoo lines on the chin, strong brows, fierce dark eyes, brown skin, open shouting mouth.",
  wear="Yellow rain jacket open over a black tank top, tattooed arms (Polynesian patterns), cargo trousers, captain's whistle on a cord, a battered megaphone.",
  pose="Standing on top of a stack of containers, shouting into the megaphone, other arm raised in a fist.",
  fg="Hands of sailors climbing up the containers.",
  mg="Her on the containers.",
  bg="A captured port in storm: cranes, sailors with flags cheering, a sunbreak in dark clouds.",
  cam="Full-frame, 24mm, f/5.6, camera from below the containers, looking up.",
  light="Stormy dark sky with a sudden sun break lighting her from the side.",
  tech="Heroic colour photojournalism (like Sebastião Salgado's workers series but in colour), real grain.",
  palette="Storm grey, safety yellow, rust red container, red hibiscus.",
  flaws="Rain on her face, rust on the containers.",
  avoid="No tattoo-on-skin style like the reference, no glamour model look.")

P("HSN_lider_rebelde", "Admiral Teodoro Salas, ~58, commander of the Malacca squadron, leader of the Sea Cross, a religious-military order that wants the fleet to serve God, not the freight market (civil-war rebel)",
  face="Same man as the reference: short slicked black hair greying, thin moustache, Filipino-Latino features, deep-set eyes, lined cheeks, stern mouth.",
  wear="White naval dress uniform with gold buttons and epaulettes, a long white cape with a large red cross, a rosary wrapped around the right hand, a naval sabre.",
  pose="Standing on the deck of a warship, rosary held over his heart, looking at the viewer, sailors kneeling in prayer around him.",
  fg="Kneeling sailors' backs.",
  mg="Him.",
  bg="The Malacca strait at sunset, a fleet of grey warships with crosses painted on their bows.",
  cam="Full-frame, 35mm, f/4, from the mast above, looking down at him.",
  light="Warm low sunset light from the side, long shadows.",
  tech="Baroque religious oil painting in the manner of Zurbarán and Murillo.",
  palette="White, red cross, gold, sunset orange, steel grey.",
  flaws="Sea salt on the uniform, a frayed cape.",
  avoid="No tattoo-on-skin style, no neon colours like the reference.")

# =============================== APF ===============================
P("APF_amara_nwosu", "Spokesperson Amara Nwosu-Keïta, 56, elected by 1,200 local councils, former rural teacher; she does not command, she coordinates, and a continent moves",
  face="Same woman as the reference: round warm face, deep brown skin, thin round gold-rimmed glasses, gentle smile with deep laugh lines, a small gap between front teeth, small gold earrings; grey hairs visible at the temple under the headwrap.",
  wear="Wax-print dress in orange, cobalt blue and yellow geometric patterns; a large matching gele headwrap tied high; a necklace of wooden beads and one bronze council token; a stick of white chalk between her fingers; reading notes folded in her other hand.",
  pose="Standing slightly raised on a wooden crate under a baobab, right hand lifted with the chalk as if making a point, head tilted, smiling at someone in the crowd just right of the camera.",
  fg="Heads, shoulders and raised hands of the crowd, out of focus, warm skin tones and colourful cloth.",
  mg="Her under the baobab, a school blackboard propped against the trunk with tallies of votes in chalk.",
  bg="The huge baobab with its bare twisted branches; beyond it a village with solar panels on round huts, a water tower, a dusty road with a line of people still arriving.",
  cam="Full-frame, 50mm, f/2.8, camera among the crowd at head height, 4 m away, slightly below her.",
  light="Warm late-afternoon sun from camera-left filtered through the baobab, dappled light on her face and dress; dust glowing in the air.",
  tech="Contemporary realistic oil portrait in the manner of Amoako Boafo (expressive finger-painted skin) combined with the patterned richness of Kehinde Wiley, but set in a real scene, not a flat background.",
  palette="Orange, cobalt blue, yellow, ochre earth, chalk white.",
  flaws="Chalk dust on her fingers and dress, sweat on the forehead, a crooked blackboard.",
  avoid="No street-mural style like the reference, no tourist postcard, no queen pose.")

P("APF_kwame_diallo", "Commander Kwame Diallo, 44, commander of the Sahel militias, organised the defence of the councils in the water wars; draws the map first, discovers people live inside later",
  face="Same man as the reference: short afro, full black beard, very dark skin, strong cheekbones, intense eyes under a furrowed brow, a nick in the left ear.",
  wear="A long orange tagelmust scarf wrapped around the neck and one shoulder; faded desert fatigues; a canvas chest rig with magazines and a radio; a rifle slung across the back; a worn leather map case.",
  pose="Standing on the crest of a dune, holding a paper map open with both hands against the wind, looking up from it straight at the viewer.",
  fg="Sand blowing across the frame, streaked by the wind.",
  mg="Him on the dune crest, the map flapping.",
  bg="Below the dune: a line of pickup trucks with mounted guns and militia fighters, a green flag on an antenna, a dry riverbed, a flat Sahel horizon with acacias.",
  cam="Full-frame, 24mm, f/8, camera low on the dune slope, 2 m away, looking up.",
  light="Harsh noon sun, very short hard shadows, the sky almost white.",
  tech="Cinematic war film still with a bleach-bypass look (high contrast, desaturated), real grain.",
  palette="Sand, orange, olive, white sky.",
  flaws="Sand in his beard, a torn map edge, a frayed scarf.",
  avoid="No mural style, no posing like a model.")

P("APF_lider_rebelde", "General Kwame Adeyemi-Sow, ~63, veteran of the Sinai campaign, voice of the nationalist movements: each people its own state, not a thousand councils in Lagos (civil-war rebel)",
  face="Same man as the reference: short grey hair, grey beard trimmed short, deep brown skin with heavy forehead lines, a heavy brow, hard old eyes, a scar on the right temple.",
  wear="Olive general's uniform with rows of campaign medals (one from Sinai, cracked enamel), a red-gold-green sash across the chest, a peaked cap under the left arm, white gloves.",
  pose="Standing perfectly frontal, jaw set, eyes into the lens, right hand on a ceremonial cane.",
  fg="Nothing: clean.",
  mg="Him.",
  bg="A tall wall where dozens of different national flags of old African states hang side by side, faded and patched, one freshly sewn.",
  cam="Full-frame, 50mm, f/4, frontal, symmetric, at his chest height, 3 m away.",
  light="Dramatic single key light from his left, deep shadow on the right; flags lit softly.",
  tech="Official state oil portrait of the 1960s-70s African independence era (like the portraits of Nkrumah or Sankara), painted realistically.",
  palette="Olive, red, gold, green, black.",
  flaws="A loose medal ribbon, scuffed glove.",
  avoid="No mural style, no cartoon dictator.")

# =============================== Japón ===============================
P("ZJP_kaede_mori", "Shōgun-Admiral Kaede Mori, 41, Yokosuka admiral who switched off the radio when Singapore demanded the Kanto fleet, raised an old flag and told the shipyards they answered to her",
  face="Same woman as the reference: black chin-length bob with straight bangs, sharp narrow eyes, straight brows, pale skin, thin red lips, a small scar on the left eyebrow, calm cold expression.",
  wear="Dark navy admiral's coat with gold buttons and high collar, a white hachimaki headband with a red sun, a katana in a black lacquered scabbard at the hip, admiral's insignia, a pair of old binoculars.",
  pose="Standing at the bow of her flagship, one hand on the katana hilt, turning her head toward the viewer.",
  fg="The bow railing and the anchor chain, wet.",
  mg="Her.",
  bg="Tokyo Bay at dawn in mist, the shipyards of Yokosuka with cranes, other warships, an old Japanese flag snapping in the wind.",
  cam="Full-frame, 35mm, f/4, from the deck below her, looking up.",
  light="Pale pink dawn light, mist diffusing everything, rim light on her hair.",
  tech="Realistic oil painting with ukiyo-e influences in the waves and mist (Hokusai) but a modern photographic face.",
  palette="Navy, pale pink, sea grey, red sun.",
  flaws="Sea spray on her coat, a nick in the scabbard lacquer.",
  avoid="No woodblock-card frame like the reference, no anime style.")

P("ZJP_daisuke_kanemura", "CyberShōgun Daisuke Kanemura, 52, heir of the oldest zaibatsu of Kanto; speaks in quarters and tons; at the end his mind goes into the biggest Mecha in the world",
  face="Same man as the reference: slicked-back black hair with grey streaks, thin face, rectangular green-tinted glasses, thin lips, sharp cheekbones, cold expression.",
  wear="Black tailored suit, red tie, the zaibatsu logo pin on the lapel, a thin silver neural-link port behind the ear.",
  pose="Seated at the head of a long glass boardroom table, fingers steepled, looking straight at the viewer.",
  fg="Reflections in the glass table.",
  mg="Him.",
  bg="Through the window: a giant Mecha standing among skyscrapers at night, with the zaibatsu logo on its chest.",
  cam="Full-frame, 50mm, f/2.8, from the other end of the table.",
  light="Neon green and white city light from the windows, his face half lit.",
  tech="Cyberpunk realism (like Blade Runner 2049's photography).",
  palette="Black, neon green, red tie, night blue.",
  flaws="A smudge on the glass table.",
  avoid="No woodblock-card frame, no anime style.")

P("ZJP_ryuji_sakaguchi", "CyberShōgun Ryūji Sakaguchi, 63, oyabun of the clan that has run the Osaka docks for three generations; two missing finger joints, friends in every port",
  face="Same man as the reference: grey hair swept back, short grey goatee, deep lines, narrow eyes with a relaxed dangerous half-smile, tanned skin; the tips of the left little and ring fingers missing.",
  wear="White suit jacket over a black silk shirt open to the chest, showing irezumi dragon tattoos from neck to wrists; a red folding fan; a katana in a white sheath leaning against his chair.",
  pose="Seated low and wide on a leather sofa, one arm on the backrest, fan half open in the mutilated hand, looking at the viewer from under his brows.",
  fg="A low table with a sake set and an ashtray with a smouldering cigarette, smoke rising.",
  mg="Him on the sofa.",
  bg="A dim office above the docks: wooden lattice screens, a calligraphy scroll, a window with red neon (a kanji sign) and container cranes outside in the rain.",
  cam="Full-frame, 35mm, f/2, camera low at the table height, 2 m away.",
  light="Red neon from the window as rim light on the right, warm small table lamp on his face, everything else dark.",
  tech="Neo-noir film still in the manner of Takeshi Kitano's yakuza films, shot on Fuji Eterna film, rich blacks and grain.",
  palette="Red neon, black, white suit, tattoo indigo and gold.",
  flaws="Cigarette ash on the table, a scratch on the sake bottle, rain on the window.",
  avoid="No woodblock-card frame like the reference, no anime style, no cartoon gangster.")

P("ZJP_kenzo_akabane", "CyberShōgun Kenzō Akabane, 67, president of SRS, the most respected pharmaceutical of Sendai; clones grow in the basements; the first to upload his own mind",
  face="Same man as the reference: thick white hair combed neatly, round thin glasses, wide propaganda smile showing perfect teeth, soft wrinkled cheeks, eyes that do not smile.",
  wear="Immaculate white lab coat over a dark purple suit and tie, the SRS crane-logo pin, a pen in the breast pocket, surgical gloves tucked in a pocket.",
  pose="Standing in the middle of a corridor of clone tanks, arms slightly open in a welcoming gesture, smiling at the viewer.",
  fg="The glass of a tank very close to the lens, with condensation.",
  mg="Him.",
  bg="Rows of tall glass tanks with pale green fluid and the blurred silhouettes of sleeping human clones, all with his young face; white tiles; a red biohazard light.",
  cam="Full-frame, 50mm, f/4, perfectly symmetric corridor, camera at his chest height, 4 m away.",
  light="Cold clinical white light from the ceiling, green glow from the tanks on both sides of his face.",
  tech="Unsettling clean realism in the manner of a Stanley Kubrick frame (symmetry, sterile light).",
  palette="Clinical white, pale green, purple, one red light.",
  flaws="A smear on the tank glass, a coffee cup left on a cart.",
  avoid="No woodblock-card frame, no anime style, no blood.")

# =============================== Gran Bretaña ===============================
P("ZAL_tom_ashworth", "President Tom Ashworth, 54, grandson of Yorkshire miners, led the Night of the Broken Servers in Manchester",
  face="Same man as the reference: ruddy weathered face, ginger beard turning grey, small sharp blue eyes, a broken nose, missing tooth, flat cap.",
  wear="Brown tweed flat cap, worn brown leather work jacket over a wool waistcoat, a red neckerchief, heavy boots; a sledgehammer.",
  pose="Standing on a pile of smashed servers, sledgehammer resting head-down by his boot, the other hand raised in a fist, mouth open in a shout.",
  fg="Broken circuit boards and glass.",
  mg="Him on the heap.",
  bg="Inside an old Manchester mill: iron beams, broken windows, workers' banners, a crowd of workers with tools.",
  cam="Full-frame, 28mm, f/5.6, camera low, looking up, 3 m away.",
  light="Grey industrial daylight through broken windows, dust in the beams.",
  tech="Social-realist oil painting in the manner of L.S. Lowry's palette but with the realism of Ford Madox Brown's 'Work'.",
  palette="Brick red, soot black, tweed brown, grey sky.",
  flaws="Grime on the face, a bleeding knuckle.",
  avoid="No newspaper clipping frame like the reference.")

P("ZAL_siobhan_cray", "First Ascended Siobhan Cray, 35, neuro-engineer from Edinburgh, the first person to live a whole year connected to the London network; speaks for everyone at once",
  face="Same woman as the reference: dark curly hair, shaved on one side, strong nose, intense dark eyes, pale freckled skin; thin silver neural ports at the temples.",
  wear="A simple white high-neck garment; thin glowing filaments run from her temples into the walls.",
  pose="Floating slightly above the floor, arms loose at her sides, eyes open with faint light in the irises, calm smile.",
  fg="Floating dust motes lit by the filaments.",
  mg="Her, sharp.",
  bg="A white circular room; multiple translucent copies of her face overlap at the edges of the frame like after-images.",
  cam="Full-frame, 85mm, f/2, frontal close-up at eye level.",
  light="Bright white diffused light from everywhere, no shadows; the filaments emit a faint blue.",
  tech="Photorealistic sci-fi film still (like 'Ex Machina'), very clean, real skin texture.",
  palette="White, pale blue, her dark hair as the only strong tone.",
  flaws="A tiny bruise around a temple port, a stray curl.",
  avoid="No newspaper clipping frame, no cyborg armour.")

P("ZAL_victoria_iii", "Her Majesty Queen Victoria III, 41, former period-drama actress from Bath found to descend from a minor royal branch; wears the crown like a costume and the nation applauds",
  face="Same woman as the reference: dark auburn hair in a Victorian up-do, pale skin, green eyes, a gracious practised smile, a beauty spot near the lip.",
  wear="Full Victorian regalia: crimson velvet robe with ermine trim, a jewelled crown, pearl necklace, the Garter sash, white gloves.",
  pose="Seated on a velvet throne on a theatre stage, one gloved hand raised in a royal wave, smiling at an unseen audience.",
  fg="A row of old brass footlights at the edge of the stage, one bulb out; a single thrown rose on the boards.",
  mg="Her on the throne set: painted-wood throne made to look like gold, slightly too big for her.",
  bg="A red velvet theatre curtain half open on one side; the dark gilded auditorium of the Theatre Royal Bath in shadow, empty seats, boxes with gold cherubs.",
  cam="Full-frame, 50mm, f/2.8, from the first row of seats, slightly below the stage, 4 m away.",
  light="Warm footlights from below (theatrical, uncanny), a hard white follow-spot from above-front making a circle of light around her; the rest in darkness.",
  tech="Royal portrait painting in the manner of Franz Xaver Winterhalter.",
  palette="Crimson, gold, ivory, ermine white.",
  flaws="A loose thread on the robe.",
  avoid="No newspaper clipping frame.")

# =============================== Anarquías ===============================
P("ZAN_the_warlords", "The Warlords of the Lawless Lands (North America): nobody rules; the 'leader' is the name the meganations give to hundreds of warlords",
  face="The woman from the reference in the centre: long dark dreadlocks with beads, sharp face, black war paint stripe across the eyes, a scar on the lip, defiant half-closed eyes. Around her four other warlords, each completely different: an old bearded man with a cowboy hat, a young man with a gas mask pushed up, a heavy woman with a shaved head, a thin man in a rotting police uniform.",
  wear="Scavenged armour: football shoulder pads, ammunition belts, a red bandana, a road sign as a shield, leather and chain.",
  pose="The five around a fire in a barrel, she stands, the others seated or crouched, all looking at the viewer as if interrupted.",
  fg="Flames of the barrel fire, very close.",
  mg="The five figures.",
  bg="Ruins of an American city at night: a collapsed highway overpass, burned cars, a billboard with a faded ad, distant fires.",
  cam="Full-frame, 28mm, f/2.8, camera low through the flames, 2 m away.",
  light="Only firelight from below, orange, flickering; deep black night behind.",
  tech="Dark realistic oil painting in the manner of Caravaggio's tavern scenes, heavy shadows.",
  palette="Fire orange, black, rust, dirty denim blue.",
  flaws="Smoke, sparks, dirt and blood on clothes.",
  avoid="No mugshot frame like the reference, no Mad Max cosplay, no clean costumes.")

P("ZWB_coronel_barbosa", "Colonel Tiago Barbosa, 57, colonel of an army that no longer exists; rules the Amazon rivers from a gunboat and sells wood to whoever pays",
  face="Same man as the reference: thick dark curly hair greying, full greying beard, heavy-lidded eyes, broad nose, sweaty brown skin.",
  wear="A faded old Brazilian colonel's uniform with fringed epaulettes, open shirt, crossed bandoliers, a cigar, a panama hat in hand.",
  pose="Leaning on the railing of a rusty river gunboat, cigar in mouth, looking at the viewer with contempt.",
  fg="Brown river water splashing against the hull.",
  mg="Him at the railing; a heavy machine gun on the deck.",
  bg="Dense Amazon jungle walls, a timber raft being towed, stilts houses.",
  cam="Full-frame, 35mm, f/4, camera on the water level in a canoe, looking up.",
  light="Humid hazy green light, sun behind clouds.",
  tech="Cinematic film still in the manner of Werner Herzog's 'Aguirre' and 'Fitzcarraldo' (16mm-grain, humid haze).",
  palette="River brown, jungle green, faded khaki, cigar ember.",
  flaws="Rust on the gunboat, sweat stains on the uniform.",
  avoid="No torn poster frame like the reference.")

P("ZWE_ataman_grigorenko", "Ataman Oleksandr Grigorenko, 55, former commander of a Dnieper garrison; controls the grain silos between Kiev and the Volga and charges toll at every bridge",
  face="Same man as the reference: huge drooping black moustache, shaved chin, broad red face, small fierce eyes, a scar across the nose.",
  wear="Tall black fur papakha hat, a red Cossack coat with cartridge loops, a sabre, a modern assault rifle on his back.",
  pose="Mounted on a big chestnut horse, sabre resting on his shoulder, looking down at the viewer.",
  fg="Ripe wheat brushing the lens.",
  mg="Him on horseback.",
  bg="A huge concrete grain silo with a painted Cossack flag, an armoured train on a bridge.",
  cam="Full-frame, 24mm, f/8, camera low in the wheat.",
  light="Golden late afternoon light from behind as rim, warm.",
  tech="Epic oil painting in the manner of Ilya Repin's 'Reply of the Zaporozhian Cossacks' and Józef Brandt.",
  palette="Wheat gold, red coat, black fur, sky blue.",
  flaws="Dust on the horse, a torn coat sleeve.",
  avoid="No matryoshka doll like the reference.")

P("ZWI_rani_devika", "Rani Devika Rathore, 37, heiress of a Rajput house who rearmed the militias when Delhi fell; trades water with the Directorate and rice with the High Seas",
  face="Same woman as the reference: long thick black hair, a gold maang tikka on her forehead, a red bindi, kohl-lined eyes, a strong nose with a small nose ring, full lips, brown skin.",
  wear="Steel mail armour over a deep red-and-gold sari, gold necklace, a curved talwar sword across her knees.",
  pose="Seated on a carved marble throne in a fort, upright, sword across her knees, looking straight at the viewer.",
  fg="Brass oil lamps on the floor.",
  mg="Her on the throne.",
  bg="Inside a Rajasthani fort: carved jali screens, a courtyard with soldiers and trucks, a burning city on the horizon.",
  cam="Full-frame, 50mm, f/2.8, frontal at her eye level.",
  light="Warm lamp light from below and smoky orange sky light through the jali.",
  tech="Realistic oil painting inspired by Raja Ravi Varma.",
  palette="Deep red, gold, sandstone, smoke grey.",
  flaws="A dent in the mail, soot on the sari hem.",
  avoid="No comic style like the reference, no Bollywood glamour.")

P("ZWM_emir_al_rashid", "Emir Khalid al-Rashid, 58, lord of the dead oil wells; when the oil ran out he kept the desert, the trucks and the men who knew how to use them",
  face="Same man as the reference: grey trimmed beard, hawk nose, deep lines, dark eyes, sun-dark skin.",
  wear="Red-and-white keffiyeh with black agal, a desert robe over a modern armoured vest, a gold dagger, aviator sunglasses in his hand.",
  pose="Standing in front of his convoy of armed trucks, arms crossed, looking straight at the viewer.",
  fg="A broken, rusted oil pipeline running diagonally across the bottom of the frame, sand drifted against it.",
  mg="Him, sharp, a few steps in front of the lead truck; two of his fighters leaning on the bonnet behind him.",
  bg="A convoy of dusty white pickup trucks with mounted guns in a line; beyond them a dead oil field of rusting pump jacks frozen mid-stroke, a burned-out refinery tower, a dust storm rising on the horizon.",
  cam="Full-frame, 35mm, f/5.6, camera low at his knee height, 3 m away, slightly to his right.",
  light="Hard late-afternoon desert sun from camera-left, long shadows, a warm orange cast; the dust storm softens the background.",
  tech="Cinematic realism shot on 65mm film in the manner of 'Lawrence of Arabia' and Denis Villeneuve's 'Dune' desert photography, fine grain, enormous depth.",
  palette="Sand, red keffiyeh, rust, black.",
  flaws="Dust on the robe and in the creases of his face, a cracked lens in the sunglasses, oil-black fingernails.",
  avoid="No carpet style like the reference.")


# Lista corta en castellano: quién es y qué muestra la imagen
RES = {
 "EFE_aurelio_iv": "Aurelio IV hundido en su trono de quebracho vivo, con el fusil de Iguazú en las rodillas. Óleo de corte al estilo Sargent/Sorolla.",
 "EFE_anahi_quiroga": "Anahí metida en los helechos de las Yungas con su bastón de musgo. Foto documental en película.",
 "EFE_tupa_heredero": "Tupã I en la proa de la barcaza imperial, amaneciendo sobre Asunción. Óleo romántico tipo Turner.",
 "EFE_custodia_pereira": "Pereira jurando en una asamblea nocturna de guardaparques con antorchas. Foto de prensa histórica.",
 "EFE_regente_etchegaray": "Etchegaray en su mesa de guerra, con la corona sin tocar en primer plano. Claroscuro tipo Caravaggio.",
 "EFE_lider_rebelde": "Arregui arriba de un blindado en Rosario, con la insignia imperial arrancada. Foto de guerra en blanco y negro con celeste.",
 "NRE_lucius_varro": "Varro alzado en un escudo por sus legionarios en San Pedro, de noche. Pintura de historia tipo David.",
 "NRE_legado_arbogast": "Arbogast de perfil en la escotilla de un tanque, con la columna en el desierto libio. Cine épico en 65mm.",
 "NRE_irina_vasilescu": "Irina en la boca de un búnker de los Cárpatos, con su legión arrodillada en la nieve. Óleo tipo Repin.",
 "NRE_kerem_aydin": "Kerem partiendo pan con sus soldados en Capadocia, al atardecer. Óleo íntimo tipo Rembrandt.",
 "NRE_lider_rebelde": "Láskaris como ícono bizantino vivo en el ábside de Santa Sofía.",
 "SHD_lin_wenzhao": "Lin Wenzhao inmóvil en la sala de turbinas de una represa, en simetría perfecta. Foto arquitectónica tipo Gursky.",
 "SHD_zhou_mingyuan": "Zhou arriba de una compuerta abierta del Yangtsé, con el agua reventando. Realismo socialista chino.",
 "SHD_lider_rebelde": "Lin Xiaoyu frente a racks de servidores que forman una estrella roja. Retrato oficial con luz cyberpunk.",
 "NAS_amaru_quispe": "Amaru arrodillado en un templo al amanecer, con el sol de halo. Escuela cuzqueña con cara real.",
 "NAS_amaru_inca": "El mismo Amaru, ya Sapa Inca, bajando por el camino del inca con su ejército atrás. Cine histórico.",
 "NAS_lider_rebelde": "Mamani en un observatorio durante un eclipse total. Óleo gótico tipo Goya.",
 "ASC_allocation_council": "Los 41 delegados sorteados en semicírculo, vistos desde arriba. Foto tipo Gursky.",
 "ASC_plan_41": "La cara de PLAN-41 hecha de luz cian en una sala de servidores, detrás de una puerta cerrada. Cine tipo Villeneuve.",
 "ASC_lider_rebelde": "Ragnarsson con su martillo frente a un datacenter en llamas en un bosque nórdico. Óleo romántico.",
 "FCU_valeria_castellane": "Castellane en su planta desalinizadora, entre caños de vidrio con agua. Foto editorial de lujo.",
 "FCU_marcus_rourke": "Rourke con un whisky en un balcón sobre su fábrica de tanques y drones. Foto corporativa con clima noir.",
 "HSN_kofi_aldana": "Aldana con su pipa en el puente de un portacontenedores de noche, entre hologramas de fletes.",
 "HSN_ines_tavake": "Tavake con el megáfono arriba de los contenedores del puerto tomado, en plena tormenta. Fotoperiodismo.",
 "HSN_lider_rebelde": "Salas con la capa de la Cruz del Mar y sus marineros rezando en Malaca. Óleo barroco tipo Zurbarán.",
 "APF_amara_nwosu": "Amara bajo un baobab hablándole a una asamblea, con tiza en la mano. Óleo contemporáneo africano.",
 "APF_kwame_diallo": "Diallo en una duna del Sahel con su mapa y sus pickups abajo. Cine de guerra con contraste alto.",
 "APF_lider_rebelde": "Adeyemi-Sow de frente ante una pared de banderas de las viejas naciones africanas. Retrato oficial años 60.",
 "ZJP_kaede_mori": "Mori en la proa de su buque insignia en la bahía de Tokio, con la niebla del amanecer. Óleo con aire de Hokusai.",
 "ZJP_daisuke_kanemura": "Kanemura en su sala de directorio de vidrio, con el Mecha gigante afuera. Realismo cyberpunk.",
 "ZJP_ryuji_sakaguchi": "Sakaguchi en su oficina sobre los muelles de Osaka, con tatuajes, abanico y neón rojo. Cine yakuza tipo Kitano.",
 "ZJP_kenzo_akabane": "Akabane sonriendo en un pasillo de tanques de clones con su propia cara. Simetría tipo Kubrick.",
 "ZAL_tom_ashworth": "Ashworth arriba de una pila de servidores rotos en una fábrica de Manchester. Óleo de realismo social.",
 "ZAL_siobhan_cray": "Siobhan flotando conectada a la red de Londres, con ecos de su propia cara. Cine tipo Ex Machina.",
 "ZAL_victoria_iii": "Victoria III en un trono de utilería sobre el escenario de un teatro vacío. Retrato real tipo Winterhalter.",
 "ZAN_the_warlords": "Cinco caudillos alrededor de un barril en llamas en una ciudad yanqui en ruinas. Óleo oscuro tipo Caravaggio.",
 "ZWB_coronel_barbosa": "Barbosa con su cigarro en la baranda de una cañonera del Amazonas. Cine tipo Herzog.",
 "ZWE_ataman_grigorenko": "Grigorenko a caballo entre el trigo, frente a un silo y un tren blindado. Óleo épico tipo Repin.",
 "ZWI_rani_devika": "La Rani en su trono de mármol, con el talwar en las rodillas y una ciudad ardiendo afuera. Óleo tipo Ravi Varma.",
 "ZWM_emir_al_rashid": "Al-Rashid delante de su convoy y de un campo de pozos de petróleo muertos. Cine del desierto en 65mm.",
}

HEAD = """# RETRATOS DE ESTADO DE LOS LÍDERES - {n} imágenes
#
# Solo los líderes de las 8 potencias (con sus rutas), sus 7 rebeldes, Japón, Gran Bretaña y las anarquías.
# Satélites, ministros, generales y agentes NO cambian.
#
# Es EL retrato oficial del líder, un nivel por encima de los ministros: imagen real, auténtica, original y
# grandiosa. Cada pedido trae su cara, vestuario, pose, escena en tres planos, cámara, luz, técnica, paleta,
# imperfecciones y qué evitar. Respetá cada campo. Pedí UNA imagen por mensaje y adjuntá la referencia de su cara
# (referencias/<id>__actual.png del zip).
#
# ===================== REGLAS PARA TODAS (copialas al principio de cada mensaje) =====================
# NOT AN "AI IMAGE" LOOK. This must look like a real photograph or a real painting made by a master, never
# like a typical AI-generated picture. Specifically:
# - Real skin: pores, uneven tone, wrinkles, stubble, sun damage, small scars. NO smooth plastic skin, NO beauty
#   filter, NO airbrushing, NO glossy wax faces, NO perfect symmetric faces.
# - Real light from the source described in the request, and only that. NO glowing rim light everywhere, NO
#   halo glow, NO HDR look, NO teal-and-orange grade, NO lens-flare spam, NO bokeh orbs added for decoration.
# - Real materials: wool pills, leather cracks, metal scratches, dust, mud. Clothes hang with real weight.
# - Restrained colour: follow the palette given. NO oversaturation, NO neon unless the request asks for it.
# - Real camera and real technique: if the request says a film stock or a lens, imitate its grain, depth of
#   field and distortion. If it says a painter, imitate that painter's brushwork, ground colour and finish.
# - Composition as described (camera height, distance, angle). NOT the default centred chest-up AI portrait.
# - Hands: correct anatomy, five fingers, natural grip.
# - The person is the SAME as in the attached reference (same face shape, age, hair, scars, ethnicity), but as
#   a real human being, not as an icon, card, poster, statue or tattoo like the reference.
# - The year is 2100: clothes, weapons and technology are of the future in the style of their nation, but
#   worn, used and real, not shiny sci-fi costumes.
# - NO text, NO letters, NO logos with words, NO signature, NO frame or border, NO watermark.
# - Vertical format with ratio 156x210 (deliver at 1248x1680 or larger, PNG). The face must still read
#   clearly when the image is shrunk to 156x210: keep it in the upper third and large enough.
# =====================================================================================================
#
# LISTA (quién es y qué muestra cada imagen)
{lista}
"""


def main(out):
    lista = '\n'.join(f"# {i:2d}. {cid}: {RES[cid]}" for i, (cid, _, _) in enumerate(L, 1))
    txt = [HEAD.format(n=len(L), lista=lista)]
    for i, (cid, who, k) in enumerate(L, 1):
        txt.append(f"""===== {i} de {len(L)} =====
ASSET_REQUEST
type: leader_state_portrait
id: {cid}
filename: retrato_{cid}.png
reference: referencias/{cid}__actual.png (same face, NOT the same style)
size: 1248x1680 or larger, ratio 156x210, PNG
who: {who}
face: {k['face']}
wardrobe: {k['wear']}
pose: {k['pose']}
foreground: {k['fg']}
midground: {k['mg']}
background: {k['bg']}
camera: {k['cam']}
lighting: {k['light']}
technique: {k['tech']}
palette: {k['palette']}
imperfections: {k['flaws']}
avoid: {k['avoid']} Plus everything in the general rules (no AI look, no text, no frame).
""")
    open(out, 'w', encoding='utf-8').write('\n'.join(txt))


if __name__ == '__main__':
    main(sys.argv[1])
