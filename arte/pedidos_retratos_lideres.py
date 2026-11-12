"""Pedido de retratos de Estado de los líderes (2026-11-12).

Los ministros, generales y agentes ya tienen su retrato; esto es SOLO para los
líderes de país (country_leader) y los líderes rebeldes de las guerras civiles.
Cada uno tiene su propia cámara, encuadre, luz y técnica.

    python3 arte/pedidos_retratos_lideres.py arte/pedidos_retratos_lideres.txt
"""
import sys

# id, nombre en el juego, escena (cámara, pose, lugar, luz, técnica)
L = [
 # ---------------- EFE ----------------
 ("EFE_aurelio_iv", "Emperador Aurelio IV (54, founder of the Ecofascist Empire, former green-militia commander, Buenos Aires)",
  "Seated on a throne carved from a single trunk of quebracho wood whose living roots still grip the marble floor; green-and-gold imperial uniform with a mantle of woven palm fibre, a crown of bronze laurel and yerba leaves. Camera low and slightly to his left, 50mm, looking up at him; he rests one hand on an old hunting rifle laid across his knees (the rifle of Iguazú). Late-afternoon light falls through a jungle-glass cupola in shafts full of floating pollen. Technique: large academic oil painting in the manner of a 19th-century imperial court portrait, visible brushwork, deep varnished greens."),
 ("EFE_anahi_quiroga", "Anahí Quiroga, la Voz del Monte (32, Yungas park ranger who leads the forest uprising)",
  "Standing waist-deep in wet ferns in a cloud forest, ranger jacket torn at one shoulder, a machete on her back and a carved wooden staff in her fist; moss and orchids already growing on the staff. Camera at eye level, very close (85mm), she looks straight into the lens, mist behind her swallowing the trees. Soft grey-green light, raindrops on her face. Technique: photorealistic documentary photograph, shallow depth of field, cinematic colour grade."),
 ("EFE_tupa_heredero", "Emperador Tupã I, del Agua (28, Aurelio's nephew, crowned heir; reigns from Asunción)",
  "Standing at the prow of a white imperial river barge on the Paraná at dawn, coronation mantle soaked at the hem, one hand on the gilded rail; a long wake and the Asunción skyline behind. Wide 35mm shot from the water, camera at river level so the barge towers over the viewer; he is framed small but central with the sunrise as a halo. Golden mist light. Technique: grand romantic painting (Turner-like atmosphere) with a crisp, realistic face."),
 ("EFE_custodia_pereira", "Custodia Electa Yara Pereira (elected Custodian, former chief of park rangers)",
  "Standing at a lectern made from a fallen tree stump, in front of an open-air assembly of rangers holding torches (only as soft bokeh lights behind her); simple ranger uniform with one green sash of office, no crown. Medium shot from slightly below and to the right, 70mm, her hand raised mid-oath. Warm torchlight on her face, blue night behind. Technique: photorealistic press photograph of a historic moment, slight film grain."),
 ("EFE_regente_etchegaray", "Regente Bruno Etchegaray (51, marshal of the Green Guard ruling as regent)",
  "In his barracks office, standing behind a war table covered in maps, in full Green Guard field uniform; the imperial crown sits on a cushion at the edge of the table, deliberately untouched, closer to the viewer than he is. Camera over the crown (crown in soft focus foreground, him sharp behind), 50mm, cold window light from the left. Technique: dramatic chiaroscuro oil painting in the style of Caravaggio."),
 ("EFE_lider_rebelde", "General Martín Arregui (commander of the Rosario garrison, leader of the Liberal Movement of the Southern Cone)",
  "Standing on the hood of an armoured car on a Rosario boulevard, megaphone lowered, plain olive uniform with the imperial insignia torn off (pale outline still visible); blue-and-white liberal banners and smoke in the street behind. Camera low on the asphalt, 24mm wide angle, him dominating the frame against an overcast sky. Technique: gritty black-and-white war photojournalism with one touch of colour: the blue of the banners."),
 ("YYG_tupa_benitez", "Mburuvicha Tupã Benítez (26, nephew of the Emperor, governor of the Paraguayan satellite)",
  "Seated on the steps of a colonial Jesuit ruin overgrown with vines near Asunción, white linen guayabera with an embroidered ñandutí sash, ceremonial guaraní feathered staff leaning on his shoulder; watching the viewer with a guarded half-smile. Camera at the same height, three-quarter angle from his right, 85mm. Humid golden-hour light. Technique: realistic painted portrait with warm earth tones, like a contemporary official portrait."),
 ("PTA_ingrid_paillacar", "Custodia Austral Ingrid Paillacar (glaciologist governing Patagonia and Antarctica)",
  "Standing alone on a blue glacier tongue in Magallanes, heavy white-and-green polar uniform, ice axe planted at her side, a mapuche trarilonko headband under her hood; a research station far below. Camera behind and above her shoulder, high angle drone shot (28mm) as she turns her head back to the lens. Hard white Antarctic light, wind-blown snow. Technique: hyperreal photography, cold palette."),
 # ---------------- NRE ----------------
 ("NRE_lucius_varro", "Imperator Lucius Varro (legion commander acclaimed emperor by his troops, Rome)",
  "Raised on a legion shield by soldiers in modern composite armour with red plumes (only their arms and helmets visible at the bottom of the frame), modern lorica of carbon plates and a purple paludamentum cloak, laurel wreath of gilded titanium. Camera very low among the soldiers looking straight up, 24mm, the dome of St Peter and drone lights behind. Torchlight and red smoke. Technique: neoclassical history painting (Jacques-Louis David) rendered with photographic detail."),
 ("NRE_legado_arbogast", "Legado Flavius Arbogast (legate of Legio I Italica, back from the desert)",
  "Standing in the open hatch of a sand-scoured tank in the Libyan desert, desert-camouflage armour, cloak wrapped around his face like a scarf, aquila standard planted on the turret beside him. Profile view from far away with a 200mm telephoto, heat haze compressing a column of tanks behind him. Blinding noon light, ochre palette. Technique: cinematic epic film still."),
 ("NRE_irina_vasilescu", "Legada Irina Vasilescu (legate of Legio V Macedonica on the Danube, daughter of the Dacian bunker junta)",
  "Standing in the concrete mouth of a Carpathian bunker, legate's armour over a bunker-army greatcoat, helmet under her arm, short grey hair; legionaries kneeling in rows outside in the snow, seen past her. Camera inside the bunker looking out (she is backlit, silhouetted rim light), 35mm, then her face lit by a single red emergency lamp. Technique: dramatic realistic oil painting, cold blues and one red."),
 ("NRE_kerem_aydin", "Legado Kerem Aydın (old, patient legate of Legio XII Fulminata in Anatolia)",
  "Seated on a camp chair among ancient Hittite stones in Cappadocia, white beard, armour unbuckled, sharing bread with soldiers off-frame; his helmet with a thunderbolt crest on the ground. Close-up from slightly above, 85mm, warm smile but sharp eyes. Sunset light through the fairy chimneys. Technique: intimate realistic painting with soft Rembrandt lighting."),
 ("NRE_lider_rebelde", "Basileus Constantino Láskaris (governor of the eastern provinces, crowned in Constantinople)",
  "Standing frontally in the apse of Hagia Sophia, Byzantine gold mosaic of a Christ Pantocrator behind his head acting as a halo; purple-and-gold loros over modern armour, closed crown with pendilia. Perfectly symmetric frontal composition, 50mm, camera at chest height. Candle and gold reflected light. Technique: modern painting that imitates a Byzantine icon (gold leaf, flat background) but with a realistic, living face."),
 ("ZHI_alvaro_sandoval", "Gobernador Álvaro Sandoval (nationalist governor of Hispania for Rome)",
  "Seated alone at night at a long table in an empty royal palace in Madrid, Roman governor's sash over a Spanish officer's tunic, a folded old Spanish flag under his hand; the Roman eagle banner hangs officially behind him, slightly crooked. Camera at the far end of the table, 135mm, symmetric. Single desk lamp. Technique: melancholic realistic painting, Velázquez palette."),
 ("ZDA_mihai_dragomir", "General Mihai Dragomir (bunker junta of the Carpathians, loyal to the Imperator)",
  "Emerging from a steel blast door, gas mask hanging at his chest, old bunker-army uniform with a new Roman eagle pinned on; behind him a tunnel of soldiers' helmet lamps. Camera very close and slightly below, 28mm, face filling a third of the frame, steam around him. Harsh sodium-yellow light. Technique: photorealistic, gritty cinematic still."),
 # ---------------- SHD ----------------
 ("SHD_lin_wenzhao", "Director de la Armonía Lin Wenzhao (former irrigation engineer, never gives speeches)",
  "Standing on a catwalk inside a colossal hydroelectric dam turbine hall, plain grey high-collared suit, hands behind his back; giant turbines in perfect rows recede behind him. Strict one-point perspective, symmetric, camera at his eye level from 10 m away, 35mm. Cool even industrial light, no shadows. Technique: precise architectural photography, almost clinical."),
 ("SHD_zhou_mingyuan", "Comisario Zhou Mingyuan (youngest of the Directorate, commissioner of the Yangtze works)",
  "Standing on top of an open sluice gate as water bursts out below him, hard hat in hand, sleeves rolled up, red commissioner armband; spray and a rainbow in the air. Camera on the opposite bank, low, 50mm, slight Dutch angle. Bright afternoon backlight through the spray. Technique: heroic poster-realism painting, saturated colours."),
 ("SHD_lider_rebelde", "Comisaria Lin Xiaoyu (commissar of the old algorithmic party, AI communists)",
  "Seated in front of a wall of old server racks with blinking red lights arranged like a star, Mao-style tunic with a small circuit badge, hands folded; her face lit from below by a tablet. Camera directly in front, slightly above, 40mm, the racks filling the background. Red-and-green LED light. Technique: cold realistic digital painting, socialist-realism pose with cyberpunk light."),
 ("ZKR_park_seo_yeon", "Directora Residente Park Seo-yeon (network engineer who reunified Korea with a 12-line decree)",
  "Standing at night on a bridge over the old DMZ while the city lights of both sides switch on behind her at the same time; long dark coat, a slim headset at her ear. Wide shot, camera far back at knee height, 24mm, her silhouette against the double skyline. Blue night and warm city light. Technique: cinematic photograph, long exposure light trails."),
 ("ZST_batu_erdene", "Lector del Cielo Batu Erdene (Mongolian herder, meteorologist and shaman)",
  "On horseback on the open steppe, deel robe with a shaman's fringed headdress and a weather-station antenna strapped to the saddle; a storm front is coming behind him. Camera low in the grass, 35mm, the horse rearing slightly, he holds a drum raised to the sky. Dark violet storm light with a single sun ray on him. Technique: epic realistic painting."),
 # ---------------- NAS ----------------
 ("NAS_amaru_quispe", "Sapa Inti Amaru Quispe II (young and pious solar monarch, Cusco)",
  "Kneeling at sunrise on the stone platform of a mountain temple, gold sun-disc headdress and tunic of tocapu patterns, eyes closed, palms open to the light; priests as distant figures. Camera frontal and centred, the rising sun exactly behind his head, 85mm. Pure golden light, sun flare. Technique: devotional realistic painting, Cusco school gold accents."),
 ("NAS_amaru_inca", "Sapa Inca Amaru Quispe II (the same king after breaking with the priests; lord of the four suyus)",
  "Striding down an ancient Inca road toward the viewer, armour of hammered gold and black composite plates, a staff of command with a modern antenna, army columns winding along the mountain road behind. Camera on the road ahead of him, low, 50mm, him walking into frame. Stormy midday light, clouds below the mountains. Technique: cinematic film still, majestic and harsh."),
 ("NAS_lider_rebelde", "General Huáscar Mamani (head of the Black Sun Junta, esoteric and paranoid)",
  "In a dark observatory during a total solar eclipse visible through the open dome, black uniform with a black sun emblem; face half lit by the corona light. Camera behind a telescope, his face partly framed by it, 50mm. Cold silver eclipse light. Technique: dark gothic oil painting."),
 ("ZNG_mariana_otalora", "Alta Guardiana de las Lluvias Mariana Otálora (climate priestess of the Chocó)",
  "Standing barefoot on a rock in the middle of a jungle river during a downpour, white priestly robes soaked, arms spread, eyes upward; rain streaks frozen. Camera from far below on the river bank, 70mm. Dark green light with lightning. Technique: photorealistic, high-speed photography."),
 ("ZLL_rafael_urdaneta", "Virrey del Sol Rafael Urdaneta (heir of an oil family converted to the sun cult)",
  "Seated on a throne made from an old rusted oil pump jack in the Venezuelan plains, gold solar viceroy robes, rings on every finger; dry oil wells behind him reflect sunset. Camera frontal, symmetrical, slight wide angle 35mm. Saturated orange sunset. Technique: satirical-grand painting like Botero's palette but realistic proportions."),
 # ---------------- ASC ----------------
 ("ASC_allocation_council", "El Consejo de Asignación (41 delegates drawn by lot every year; no face on purpose)",
  "The 41 delegates seated in a semicircle in a white amphitheatre, all in identical grey overalls, faces partly lit by a huge circular screen; seen from the very top of the room. Overhead camera, 24mm, the people form a perfect arc. Cool white light. Technique: clean photorealistic architectural shot."),
 ("ASC_plan_41", "PLAN-41 (the Commune's planning AI)",
  "No human face: a vast hall of server pillars receding into darkness, and in the centre a calm human-like face assembled from thousands of floating points of cyan light, looking straight at the viewer. Camera at eye level with the face, 50mm, symmetric. Only cyan and black. Technique: photorealistic render with volumetric light."),
 ("ASC_lider_rebelde", "Jarl Sven Ragnarsson (prophet of the Sons of Odin, neo-pagan, destroys datacenters)",
  "Standing before a burning datacenter in a Nordic forest at night, fur cloak over improvised armour, runes painted on his face, a hammer resting on his shoulder; sparks swirl. Camera low and to the side, 35mm, flames rim lighting him. Orange fire against blue snow. Technique: dramatic romantic painting."),
 ("ZBC_aino_kask", "Presidenta de las Cooperativas Aino Kask (Estonian agronomist)",
  "Kneeling in a rye field holding a handful of soil, sturdy work jacket, a repaired old tractor behind her; she looks up at the viewer. Camera standing above her, high angle, 50mm. Soft northern summer light. Technique: Nordic realist painting."),
 ("ZAL_siobhan_cray", "Primera Ascendida Siobhan Cray (neuro-engineer, first person to live a year connected to the London network)",
  "Floating slightly above the floor in a white room, thin glowing filaments run from her temples into the walls, eyes open with faint light in the irises, calm smile; multiple translucent copies of her face overlap at the edges. Camera frontal, close-up 85mm. Bright white diffused light. Technique: photorealistic sci-fi still."),
 ("ZAL_tom_ashworth", "Presidente Tom Ashworth (grandson of Yorkshire miners, led the Night of Broken Servers in Manchester)",
  "Standing on a pile of smashed servers in a Manchester mill, flat cap, miner's jacket, sledgehammer resting on the ground; workers' banners hang from the iron beams. Camera low, 28mm. Grey industrial daylight through broken windows. Technique: social realist oil painting."),
 ("ZAL_victoria_iii", "Su Majestad la Reina Victoria III (former period-drama actress, restored queen)",
  "Seated on a velvet throne on a theatre stage, full Victorian regalia and crown, a red curtain half open and footlights below; an empty auditorium is suggested in shadow. Camera from the front row, slightly below, 50mm. Warm stage light. Technique: Winterhalter-style royal portrait painting."),
 # ---------------- HSN ----------------
 ("HSN_kofi_aldana", "Capitán General de Puertos Kofi Aldana (born on a freighter, controls the freight clearing house)",
  "On the bridge of a giant container ship at night, merchant captain uniform with gold-braided epaulettes, holographic freight manifests in the air around him; port cranes lit through the windows. Camera behind the helm, 35mm. Teal holographic light and orange port lights. Technique: cinematic sci-fi still."),
 ("HSN_ines_tavake", "Capitana Inés Tavake (Rapa Nui container ship captain who took Kanto port with 400 sailors and a megaphone)",
  "Standing on top of a stack of containers in a captured port, megaphone in one hand, sailors cheering below; tattoos on her arms, rain jacket. Camera from below the containers, wide 24mm. Stormy sky with sunbreak. Technique: heroic photojournalism in colour."),
 ("HSN_lider_rebelde", "Almirante Teodoro Salas (leader of the Sea Cross, religious-military order)",
  "On the deck of a warship, white naval uniform with a large cross embroidered on a cape; sailors kneel praying. Camera from the mast looking down, 35mm. Sunset over the Malacca strait. Technique: baroque religious painting."),
 ("ZAF_celestine_joseph", "Gobernadora de Puertos Célestine Joseph (born in Port-au-Prince, collects tolls on everything that floats)",
  "Seated in a toll booth tower over a Caribbean shipping lane, colourful coat, ledger tablet in hand. Camera through the glass window from outside, 50mm, ships reflected. Bright tropical sunlight. Technique: vivid naïve-Haitian-painting palette but realistic figure."),
 ("ZAS_liam_whitford", "Presidente Liam Whitford (presides a shareholders' parliament in Canberra)",
  "Standing in a parliament with shareholders' screens instead of seats, dark suit, hands on a dispatch box; tired eyes. Camera at the back, 85mm compressed. Neutral daylight. Technique: realistic photojournalism."),
 # ---------------- FCU ----------------
 ("FCU_valeria_castellane", "Presidenta Valeria Castellane (rotating president of the Union board, desalination water trust)",
  "Standing in front of a floor-to-ceiling glass wall inside a desalination plant; behind her, water flows through glass pipes like a sculpture. Tailored white suit, a small glass vial of water as a pendant. Camera three-quarter from the left, 85mm. Clean blue-white light. Technique: luxury editorial photography."),
 ("FCU_marcus_rourke", "Director Ejecutivo Marcus Rourke (director of Meridian Kinetics, war is his business)",
  "Seated in an executive chair on a factory balcony overlooking an assembly line of tanks and drones; dark suit, holding a glass of whisky. Camera behind and to his side, 35mm, the factory floor stretching below. Red warning lights and steel blue. Technique: corporate portrait photography with ominous mood."),
 ("ZNR_margaret_tsang", "Primera Ministra Margaret Tsang (won three elections with the largest share portfolio)",
  "Standing at a podium with stock tickers scrolling behind, pearl necklace, confident smile. Camera from the audience, 70mm. Spotlights. Technique: political campaign poster, realistic."),
 ("ZSE_ernesto_villalobos", "Administrador de Zona Ernesto Villalobos (general manager, contract expires 2104)",
  "Seated in a corner office with a corporate logo on the wall, loosened tie, signing a contract. Camera from above his desk, top-down 35mm. Office fluorescent light. Technique: realistic photography."),
 # ---------------- APF ----------------
 ("APF_amara_nwosu", "Portavoz Amara Nwosu-Keïta (spokesperson elected by 1,200 local councils, former rural teacher)",
  "Standing in front of a vast gathering under a baobab tree; colourful wax-print dress, a simple microphone. Camera from among the crowd, 50mm, heads and raised hands in the foreground out of focus. Warm afternoon light. Technique: realistic oil painting with vibrant colours."),
 ("APF_kwame_diallo", "Comandante Kwame Diallo (commander of the Sahel militias)",
  "Standing on a dune with a map in hand, tagelmust scarf, desert fatigues, rifle slung; pickup trucks behind. Camera low on the dune, wide 24mm. Harsh noon light. Technique: cinematic still."),
 ("APF_lider_rebelde", "General Kwame Adeyemi-Sow (Sinai veteran, voice of the nationalist movements)",
  "Standing in front of a wall covered in many different national flags of Africa, uniform with medals, jaw set. Camera frontal, 50mm, symmetric. Dramatic side lighting. Technique: socialist-realism painting."),
 ("ZAO_ana_tchissola", "Portavoz Ana Tchissola (oil unionist of Cabinda)",
  "Standing on an offshore platform, hard hat, union armband, the sea behind her. Camera from a lower deck looking up, 35mm. Overcast light. Technique: realistic photograph."),
 ("ZCO_nsimba_lukusa", "Portavoz Nsimba Lukusa (engineer of the Inga dams)",
  "Standing on top of a massive dam spillway, engineer's vest, holding a tablet; mist from the Congo river rises. Camera from the riverbed far below, 135mm. Green-gold light. Technique: grand realistic painting."),
 ("ZMZ_tomas_machava", "Portavoz Tomás Machava (port captain of Beira)",
  "On a dock at Beira with ships behind, captain's cap, holding a ledger. Camera at dock level, 50mm. Warm morning light. Technique: realistic painting."),
 ("ZMG_hery_rakoto", "Portavoz Hery Rakoto (agronomist of the highland rice terraces of Madagascar)",
  "Standing in a flooded rice terrace, trousers rolled up, a lamba scarf over his shoulder. Camera high on the terrace above, 70mm. Soft morning mist. Technique: realistic watercolour-like painting."),
 ("ZKE_wanjiru_odhiambo", "Portavoz Wanjiru Odhiambo (founder of the Rift councils)",
  "Standing on the edge of the Great Rift Valley, red shuka cloak, holding a council staff. Camera behind her, wide 24mm, the valley below. Golden light. Technique: epic realistic painting."),
 ("ZSA_thabo_mokoena", "Portavoz Thabo Mokoena (Rand unionist who brought the Cape into the Federation)",
  "Standing at a mine head with miners behind, overalls with union badge, fist raised. Camera low, 28mm. Dusty sunset. Technique: social-realist poster painting."),
 ("ZET_selam_tesfaye", "Guardiana de las Semillas Selam Tesfaye (keeper of Africa's largest seed bank)",
  "Inside a seed vault holding a glass jar of seeds up to the light, white Ethiopian shawl. Camera close-up, 85mm, rows of jars behind. Warm amber light. Technique: realistic painting."),
 # ---------------- ZJP ----------------
 ("ZJP_kaede_mori", "Shōgun Almirante Kaede Mori (Yokosuka admiral who became shōgun)",
  "Standing at the bow of her flagship with an old Japanese flag behind her, admiral's coat and a katana at her hip. Camera from the deck below, 35mm. Dawn mist over Tokyo Bay. Technique: ukiyo-e inspired realistic painting."),
 ("ZJP_daisuke_kanemura", "CyberShogun Daisuke Kanemura (heir of the oldest zaibatsu; black suit, green glasses)",
  "Seated in a glass boardroom at the top of a skyscraper, a giant Mecha visible outside the window. Camera from behind the Mecha's shoulder, 50mm. Neon green light. Technique: cyberpunk realism."),
 ("ZJP_ryuji_sakaguchi", "CyberShogun Ryūji Sakaguchi (yakuza oyabun of Osaka docks)",
  "Seated in a dim office, shirt open showing dragon tattoos, katana on the wall, red neon at the door. Camera low, 35mm. Red neon light. Technique: noir realism."),
 ("ZJP_kenzo_akabane", "CyberShogun Kenzō Akabane (president of SRS pharmaceuticals, clones in the basement)",
  "Standing in a white laboratory with clone tanks behind him, immaculate white coat, propaganda smile. Camera symmetric, 50mm. Cold clinical light. Technique: unsettling clean realism."),
 # ---------------- anarquías ----------------
 ("ZAN_the_warlords", "Los Señores de la Guerra (the hundreds of warlords of the Lawless Lands)",
  "A group of five warlords around a fire in a ruined city at night, each wearing different scavenged armour. Camera low through the flames, 28mm. Firelight. Technique: dark realistic painting."),
 ("ZWB_coronel_barbosa", "Coronel Tiago Barbosa (colonel of a vanished army, rules the Amazon rivers from a gunboat)",
  "Standing on the deck of a rusty river gunboat, faded colonel uniform, cigar. Camera from the water, 35mm. Humid green light. Technique: cinematic still."),
 ("ZWE_ataman_grigorenko", "Atamán Oleksandr Grigorenko (controls the grain silos between Kiev and the Volga)",
  "On horseback in front of a grain silo with a train behind, fur hat and saber. Camera low, 24mm. Golden wheat light. Technique: epic oil painting."),
 ("ZWI_rani_devika", "Rani Devika Rathore (heiress of a Rajput house who re-armed the militias)",
  "Seated on a carved throne in a fort, armour over a sari, sword across her knees. Camera frontal, 50mm. Warm lamp light. Technique: Mughal-miniature-inspired realistic painting."),
 ("ZWM_emir_al_rashid", "Emir Khalid al-Rashid (lord of the dead oil wells)",
  "Standing in front of a convoy of armed trucks, desert robes and a keffiyeh, sunglasses. Camera low, 35mm. Hard desert light. Technique: cinematic realism."),
 ("ZSG_yara_tupinamba", "Custodia Mayor Yara Tupinambá (park ranger of the Alto Río Negro)",
  "Standing among giant trees with a bow and ranger uniform, facial paint. Camera low, 28mm. Green filtered light. Technique: realistic painting."),
]

HEAD = """# RETRATOS DE ESTADO DE LOS LÍDERES - {n} imágenes
#
# Solo los líderes de país y de las rebeliones. Ministros, generales y agentes ya tienen su retrato y NO cambian.
# Tienen que verse "un nivel arriba" que los ministros: no es una foto de credencial, es EL retrato oficial
# del líder, el que su régimen cuelga en los edificios públicos. Imagen real (pintura o foto según cada pedido),
# auténtica, original y grandiosa. Cada pedido tiene su propia cámara, encuadre, luz y técnica: respetalas.
#
# REGLAS PARA TODAS
# - Formato vertical 156x210 (o más grande con la misma proporción, por ejemplo 624x840). PNG.
# - La cara del líder ocupa el tercio superior y se lee claramente achicada a 156x210.
# - El año es 2100: ropa, armas y tecnología del futuro, con el estilo de su nación.
# - Sin texto, sin letras, sin marcos ni bordes dibujados.
# - Si te paso su retrato actual (zip referencias/), mantené la misma cara, edad y rasgos.
# - El nombre de archivo tiene que ser exacto.
"""


def main(out):
    txt = [HEAD.format(n=len(L))]
    for i, (cid, who, scene) in enumerate(L, 1):
        txt.append(f"""===== {i} de {len(L)} =====
ASSET_REQUEST
type: leader_state_portrait
id: {cid}
filename: retrato_{cid}.png
size: 156x210 (o más grande con la misma proporción)
who: {who}
scene: {scene}
""")
    open(out, 'w', encoding='utf-8').write('\n'.join(txt))


if __name__ == '__main__':
    main(sys.argv[1])
