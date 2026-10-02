# Las Ocho Potencias — diseño de los árboles de foco

Diseño aprobado por el usuario (2026-09-23). Resume el documento "Las Ocho
Potencias" y cómo se lleva al motor de HOI4. Lo que dice acá manda sobre la
propuesta anterior de 8 árboles.

## Reglas generales

- **Foco → problema → herramienta → decisión → consecuencia.** Nada de
  cadenas de bonus sueltos: integrar, transformar economías o crear imperios
  inicia **procesos** (misiones, decisiones, contadores), no botones mágicos.
- **44-52 focos por meganación**; una partida normal completa 28-35.
- **Duraciones** (campo `days` en el spec):

  | Tipo | Días |
  |---|---:|
  | Transición (eventos, desbloqueos) | 21 |
  | Normal (industria, ejército, política) | 35 |
  | Sustancial (mecánica nacional) | 42 |
  | Estratégico (integraciones, reformas) | 56 |
  | Capstone (guerras, régimen, slots) | 70 |

- **Revolución**: nunca cambia la ideología; cambia el juego. Ninguna es
  simplemente mejor: cada una gana algo grande y pierde algo estructural.
- **Economías A/B**: además de la idea, cambian qué decisiones se usan toda
  la partida.
- **Guerras grandes con ultimátum**: el foco manda un evento al rival, que
  puede ceder, negarse o movilizarse; solo si se niega llega el wargoal. Un
  tercero puede reaccionar (ej. la HSN vende seguros).
- **Interacción entre potencias**: 20-30 eventos chicos que conectan árboles.
- **IA con condiciones** (`ai.modifiers` en el spec): la ruta depende de lo
  que le pasa al país (guerra, estabilidad, contadores), no de una moneda.
- **Versión 1 sin interfaces propias**: variables + decisiones + ideas +
  tooltips. Las GUIs, si hacen falta, después.
- **Mecánicas atadas al mapa** cuando se pueda: BioSteel con bosques, Qhapaq
  Ñan con infraestructura, HSN con estrechos, NRE con legiones, APF con
  miembros concretos.

## Orden de implementación

1. **FCU** — cuatro influencias corporativas. *(v1 hecha)*
2. **EFE** — Aurelio vs Anahí, integración de satélites por etapas,
   reforestación. *(v1 hecha)*
3. **ASC** — Poder de Cómputo, Consejo Sorteado, PLAN-41. *(v1 hecha)*
4. **HSN** *(v1 hecha)*, **NAS, APF** — Qhapaq Ñan + Inti-Soma; integración
   federal (Desarrollo/Integración).
5. **SHD y NRE al final** *(v1 hechas)* — tres caudales; prestigio de legiones +
   Auctoritas Militaris + AVE IMPERATOR.

## Por nación (resumen)

| Nación | Status quo | Revolución | Mecánica |
|---|---|---|---|
| EFE | Aurelio IV: integración de YYG/PTA por misiones, ultimátum a la FCU, *La Corona de Gaia* | Anahí Quiroga: *Control del Monte* oculto antes del golpe; desurbanizar, guerrilla, reforestación Ocupada → Reforestándose → Integrada → Núcleo | BioSteel + territorio biológicamente integrado |
| ASC | Consejo Sorteado: 3 rasgos aleatorios por año cambian las decisiones | PLAN-41: −40% PP, drones como batallón propio, logística frágil | Cómputo en Economía / Investigación / Logística / Guerra |
| FCU | Castellane: gana manteniendo las cuatro equilibradas (Sinergia 40-60) | Rourke: la OPA se habilita por la mecánica; necesita guerras (caída de dividendos en paz) | Cuatro influencias 0-100 |
| HSN | Aldana: seguros, arbitraje, neutralidad armada; vender seguros a los que pelean | Tavake: sin peajes; Botín por interceptar y capturar; patentes de corso de 90 días | Red de nodos físicos (2/4/6/todos) |
| NAS | Corte del Sol | Tawantinsuyu: los Suyus como misiones geográficas | Qhapaq Ñan por decisiones + Inti-Soma 0-100 con *La Noche del Sol* si se abusa |
| SHD | Caudal Corregido: los tres entre 45-55 = Armonía Perfecta | Zhou: se pueden pasar los límites (Pueblo hasta 130): más desequilibrio, ejército más brutal | Producción / Orden / Pueblo |
| APF | Amara: integración lenta con núcleos completos | Diallo: integra rápido pero con autonomía alta y resistencia | Desarrollo + Integración por miembro; industria generosa al principio |
| NRE | Principado: Senado, Vías, provincialización de Dacia/Hispania | Cuatro Imperatores: AVE IMPERATOR cambia el líder por prestigio | Prestigio de legiones + Auctoritas Militaris |

## FCU v1 — cómo quedó en el motor

- `06_mechanics.yaml -> four_corporations`: `FCU_castellane`,
  `FCU_halvorsen`, `FCU_meridian`, `FCU_obsidian`, arrancan en 50.
- `14_decisions.yaml -> FCU_directorio_category`: 6 contratos que mueven las
  influencias + *Repartir el Dividendo de Guerra* (solo en guerra, ruta
  Rourke). Después de cada uno corre `FCU_recalcular_directorio`:
  - clamp 0-100;
  - las cuatro entre 40 y 60 → idea *Sinergia del Directorio*;
  - alguna < 15 → idea *Guerra Corporativa*;
  - Meridian ≥ 70 con dos rivales < 25 → bandera `FCU_opa_habilitada` +
    evento *Meridian Huele Sangre*.
- Árbol de 53 focos en 8 ramas: Directorio (Castellane), La OPA Hostil
  (Rourke), Dividendo Civil / Monopolio del Agua (excluyentes), Parques de
  Meridian, Contratistas Profesionales, Flota de Dos Océanos, Sala del
  Directorio.
- Ultimátums: *La Adquisición del Sur* (EFE; la HSN reacciona vendiendo
  seguros) y *Adquirir la Alta Mar* (HSN). Solo si el rival se niega, la FCU
  recibe el wargoal.
- *El Dividendo de Guerra*: informe trimestral cada 90 días; en paz aplica
  *Caída de Dividendos* por 90 días.

Pendiente de la FCU para v2: sabotajes y filtraciones como eventos propios de
la Guerra Corporativa, contratos con otras potencias, IA de contratos según
la situación.

## EFE v1 — cómo quedó en el motor

- Árbol de 56 focos en 7 ramas: La Dinastía Verde (Aurelio), El Monte se
  Levanta (Anahí), Autarquía del Bioacero / Diplomacia del Agua
  (excluyentes), Las Cubas de la Pampa, La Guardia Verde, Los Cóndores, El
  Ciclo del Bioacero.
- **Golpe con proceso**: *Los Incendios de Gaia* (21 días) abre el panel "El
  Monte se Levanta": cuatro decisiones mueven `EFE_control_del_monte`
  (oculto). En 60 salta *Los Guardaparques Están Listos* y se habilita *El
  Monte se Levanta* (14 días): asume Anahí Quiroga, el Mandato Verde pasa a
  ser el Mandato del Monte.
- **Integración por etapas**: *Las Misiones Guaraníes* e *Integrar la
  Patagonia Austral* abren tres decisiones cada una (PP + 1 Bioacero, −2%
  estabilidad, 60 días entre etapas). La tercera da núcleos y anexa.
- **Reforestación**: *Sembrar la Conquista* abre "Sembrar una región
  ocupada" (2 Bioacero, marca una región no propia) y "Consolidar el
  bosque" (las que llevan 120 días pasan a núcleo). Versión 1 con dos
  etapas por región (el motor guarda datos por región, no por provincia).
- **Economías**: la Autarquía abre proyectos de Bioacero; la Diplomacia del
  Agua abre contratos de agua con la ASC, la APF y la SHD.
- **Ultimátum**: *El Agua no se Vende* (pide Bioacero nivel 2) manda un
  evento a la FCU: si reconoce el agua, paga y el EFE cobra; si se niega,
  el EFE recibe el wargoal y la HSN vende seguros.
- IA: más probable el Monte con estabilidad baja o en guerra.

## ASC v1 — cómo quedó en el motor

- **Poder de Cómputo**: `ASC_computo` (0-150, arranca en 30). Lo suben los
  focos de datacenters y la decisión *Construir un Datacenter*. Se asigna a
  UNA prioridad (Economía, Investigación, Logística o Guerra); cambiarla deja
  una espera de 30 días. Cada prioridad tiene 3 niveles según la capacidad
  (<40, 40-79, 80+): 12 ideas, recalculadas por `ASC_recalcular_computo`.
- **Consejo Sorteado**: *El Sorteo del Año* dispara un evento anual que
  elige 3 inclinaciones al azar entre 6 (ingenieros, pacifistas,
  productivistas, agrarios, militaristas, tecnófilos); cada una habilita su
  decisión ese año.
- **PLAN-41**: pide 50 de cómputo; *QUÓRUM HUMANO: NO REQUERIDO*. −40% de
  poder político, +investigación y producción, estabilidad casi fija.
  *El Ejército sin Bajas* avisa a la APF (*El Hombre contra la Máquina*).
  *Asignar África* es un ultimátum a la APF.
- Plan Total (cuotas) contra Mercado de Créditos de Cómputo (emisiones).
- *Líneas sin Operarios* elimina el Cuello de Botella del Consejo.
- Los drones como batallón propio quedan para v2: una unidad nueva necesita
  equipo, sprites y modelos; en v1 son ideas y experiencia.
- Ids de foco alineados con el pack de íconos (`focus_2100_asc_NN_*`).

## HSN v1 — cómo quedó en el motor

- **Nodos físicos**: Malaca, Sunda, Kanto, Manila, Taiwán, Hong Kong,
  Okinawa y Tsushima, buscados por nombre en el juego instalado (el reporte
  avisa si alguno no existe). Un evento oculto cuenta cada 30 días los que la
  HSN controla: 2+, 4+, 6+ → Red de Nodos I/II/III; los 8 → Cámara Mundial de
  Compensación. Si el conteo baja, *Un Nodo Perdido* por 180 días. Hong Kong
  arranca en manos de la Anarquía: el foco del nodo lo reclama.
- **Kofi Aldana**: neutralidad armada, arbitraje, tratado de los estrechos;
  *Seguros Marítimos* abre decisiones para venderles cobertura a las
  meganaciones en guerra (no contra la HSN). *El Bloqueo Legal* es un
  ultimátum a la FCU.
- **Inés Tavake** (*El Motín de Kanto*): se apagan las ideas de peaje; los
  nodos y la guerra generan **Botín** cada mes, que se gasta en reparaciones,
  recursos, equipo y marines. *Patentes de Corso*: 90 días contra un enemigo
  concreto. *Abordaje del Mundo*: guerra directa a la FCU.
- Puerto Libre (puertos francos) contra Peaje de los Estrechos (subas).

## Tabla de premios (las 8 potencias; EFE, FCU, ASC y HSN ajustadas después)

| Duración | Premio típico |
|---|---|
| 21 días | desbloqueo + 50 PP |
| 35 días | uno de: 100 PP, 2 fábricas, idea del 10%, bono de investigación del 50% (1-2 usos) |
| 42 días | desbloqueo de mecánica + un premio de 35 días |
| 56 días | 3 fábricas, idea del 15-20% o mejora de una idea |
| 70 días | slot de investigación, idea del 20-25%, o guerra/ultimátum con premio |

Los bonos de investigación usan categorías leídas del juego; si una no
existe, se omite con aviso.

## NAS v1 — cómo quedó en el motor

- **Inti-Soma**: `NAS_inti` (arranca en 20, máximo `NAS_inti_max` = 100).
  Evento oculto mensual: suma `NAS_granjas`, recorta al máximo. Ceremonias:
  Raymi (20: +10% estabilidad 90 días), Solsticio de Guerra (35, en guerra:
  +10% ataque 45 días), Ofrenda de Luz (25: +10% producción 60 días).
  Templos-Batería y El Sol Eterno suben el máximo. *Inti Nunca se Pone*
  abre la sobrecarga (+50 por encima del máximo por 6 meses): cada mes
  arriba del máximo, 20% de *La Noche del Sol*.
- **Qhapaq Ñan**: *El Qhapaq Ñan* marca la capital; *Extender el Camino*
  suma una región vecina a la red (+2 infraestructura); a los 90 días las
  regiones conectadas se integran como núcleos.
- **Los cuatro Suyus**: Cuntisuyu (Lima, Arequipa, Tacna), Chinchaysuyu
  (Ecuador, La Libertad, Cundinamarca), Antisuyu (Loreto, Ucayali,
  Amazonas) y Collasuyu (La Paz, Santa Cruz, Antofagasta). El foco da
  reclamos; la decisión se completa al controlar las tres regiones y da
  núcleos. Con los cuatro: *Tawantinsuyu*. El Antisuyu avisa al EFE.
- **La Corte del Sol**: sacerdotes, Fortalezas de la Puna, integración de
  Nueva Granada y los Llanos en 3 etapas, *El Sol contra el Directorio*
  (ultimátum a la SHD), *El Trono del Sol*.
- **El Tawantinsuyu Renace**: Amaru se vuelve Sapa Inca (retrato
  alternativo), Mit'a de Guerra, los Suyus, *La Bajada de la Montaña*
  (guerra a los Caudillos del Amazonas).
- Terrazas contra Minería del Cielo.

## APF v1 — cómo quedó en el motor

- **Integración federal**: cada miembro (Tierras Altas, Cabo) tiene
  Desarrollo e Integración (0-100, arrancan en 20 y 10). *Invertir* suma +20
  de Desarrollo y construye una fábrica en el miembro. *Integrar* suma +10
  con Amara, y nunca puede superar al Desarrollo; con Diallo suma +25 sin
  esa traba. En 100: núcleos + anexión; con Diallo, *Territorios Difíciles*
  por 180 días.
- **Plan de Desarrollo Regional**: cada 90 días una región propia sin
  desarrollar recibe +2 infraestructura y una fábrica (se ve en el mapa).
- **Amara** (El Congreso Continental): Mil Consejos, el Cabo y las Tierras
  Altas se suman, la Constitución Continental, *Contra la Máquina*
  (ultimátum a la ASC), La Federación Plena.
- **Kwame Diallo** (La Marcha de los Consejos, retrato alternativo):
  Milicia Popular (+100.000 hombres), La Marcha al Este (abre *Liberar las
  Regiones Ocupadas*: núcleos inmediatos con territorios difíciles), guerra a
  los Emiratos del Desierto, La Federación sin Fronteras.
- Industria generosa al principio (Polo de Lagos, Katanga, el Nilo,
  Despegue Industrial con 3 fábricas), Aldea contra Corredor.

## SHD v1 — cómo quedó en el motor

- **Tres Caudales**: Producción (60), Orden (55) y Pueblo (40), de 0 a 100.
  Las decisiones de *Los Caudales* suben uno a costa de otro. Los tres entre
  45 y 55: *Armonía Perfecta*; entre 35 y 65: *Armonía Parcial*; alguno por
  debajo de 20: *Desborde*. Se recalcula cada mes (evento oculto).
- **Lin Wenzhao** (El Caudal Corregido): Ajuste Técnico nº 1, Ingenieros del
  Orden, Vigilancia Hidráulica, integración de Corea y la Estepa en tres
  etapas, El Caudal Perfecto y *Corregir el Sol* (ultimátum al NAS).
- **Zhou Mingyuan** (La Gran Crecida, retrato alternativo): el Pueblo puede
  llegar a 130 y sube solo +5 por mes (Orden −2); Crecida I/II/III en 80, 100
  y 120; con Orden bajo 30 hay 30% de huelgas. Oleadas, la Crecida del Norte
  y El Río se Desborda (guerra a los señores del Indostán).
- Economía opuesta: Las Grandes Obras (decisión de obras nuevas) contra La
  Economía de Precisión (calibraciones). Represas del Yangtsé como industria,
  Ejército del Caudal, El Cielo Armonioso (aire y la flota del Mar de China)
  y La Armonía como árbol extra de 8 focos.

## NRE v1 — cómo quedó en el motor

- **Legiones con nombre**: Legio I Italica (55), Legio V Macedonica (45) y
  Legio XII Fulminata (40), con prestigio de 0 a 100. En guerra, cada mes una
  legión al azar gana +6; en paz todas pierden 1. Suben también con focos y
  con los *Triunfos* (decisión, una por legión). En 60 dan *Legiones
  Veteranas*; en 80, *Privilegios Legionarios* (menos poder político); en 100,
  durante el Principado, aparece *Una Legión Exige* (donativo o pelea con el
  Senado).
- **Auctoritas Militaris** (0-100, arranca en 20): +3 por mes en guerra, +1
  en paz, y más con focos. Se gasta en Ascender Oficiales, Levantar una Nueva
  Legión, Planes de Campaña, los Pretorianos y los Donativos.
- **Varro** (El Principado): Senado Restaurado, Vías Imperiales (decisión
  *Construir una Vía* en regiones al azar), Cursus Honorum, Hispania y Dacia
  Provincia (provincialización en tres etapas, cada una con 50% de
  estabilidad; la de Hispania avisa al EFE), El Equilibrio de Varro, Pax
  Romana (pide 70% de estabilidad y paz: casilla de investigación + idea
  fuerte) y *Roma contra la Tierra* (ultimátum al EFE).
- **Arbogast** (El Año de los Cuatro Imperatores, retrato del usuario): La
  Legión Decide lo asciende. Desde ahí, si la legión de otro candidato llega a
  85, aparece **AVE IMPERATOR**: aceptar cambia el líder (Arbogast, Irina
  Vasilescu o Kerem Aydın) y cuesta 10% de estabilidad; comprarlos cuesta 25
  de Auctoritas; diezmar cuesta 15%. Después de cada aclamación hay 180 días
  de calma. Vasilescu y Aydın usan retratos provisorios.
- Annona (estabilidad y hombres) contra Tributo (poder político y fábricas),
  Forjas Imperiales, Las Legiones, Mare Nostrum (aire y mar) y Legiones y
  Oficiales como árbol extra de 6 focos. 53 focos en total.

## IA v1 — cómo quedó en el motor

- **Estrategias** (`spec/16_ai.yaml` → `common/ai_strategy/`): cada potencia
  tiene un blanco de conquista que se abandona solo cuando el blanco
  desaparece. Las revoluciones endurecen el plan: con Zhou la SHD declara al
  Indostán; con Diallo la APF declara a los Emiratos. Los tipos se validan
  contra los que usa el juego instalado.
- **Satélites y rivales**, automáticos: cada señor protege y apoya a sus
  satélites; las rivalidades de 04_diplomacy se antagonizan (30).
- **Decisiones con criterio** (campo `ai` en 14_decisions): la IA mira la
  mecánica antes de gastar.
- **Peso por rama** (`ai_factor` en la rama de 07_focus_trees): vale para
  todos los focos de la rama que no tengan uno propio.

## Mecánicas v2 (2026-09-26) — cada una con algo que crece solo y castiga

Pedido del usuario: "demasiada producción = efecto negativo", mecánicas menos
fáciles. Cada potencia tiene un pulso mensual (evento oculto `.20`) y una
explicación al arrancar (`.21`). Los números están en el panel de cada una.

| Potencia | Lo que crece | Castigo | Alivio |
|---|---|---|---|
| EFE | Saturación de las cubas (+6/+12/+15 por cosecha, -3 por mes) | 40 Cubas Forzadas, 70 Fiebre y Plaga del Micelio; Bioacero > 15 se pudre | Purgar las Cubas, Rotar los Cultivos |
| FCU | Escándalo (+8 por contrato, -2 por mes); corporaciones que divergen solas | 50 Bajo Sospecha, 80 Crisis de Confianza y la Filtración | Auditoría, Relaciones Públicas, La Prensa Amiga |
| ASC | Calor de la red (+4 desde 60 de cómputo, +8 desde 100); el cómputo decae 1 por mes | 50 Racionamiento Térmico, 80 Apagón | Enfriar los Centros de Datos, La Red Fría |
| HSN | Presión de las potencias (+3 con 4 nodos, +6 con 6) | 40 Bajo Vigilancia, 70 exigen un estrecho | Diplomacia de Puertos, Seguros para las Potencias |
| NAS | Los templos queman 3 de luz por mes | < 10 Sol Hambriento; ≥ 90 Fervor Solar; eclipses | Templos Eficientes, nuevas Granjas |
| SHD | Deriva: Producción +2, Pueblo +1, Orden -1 por mes | crecidas, huelgas y booms al azar | Sensores del Caudal (deriva a la mitad) |
| APF | Tensión regional (integrar +5 / +10 con Diallo) | 50 Consejos Inquietos, 75 levantamiento | Invertir, Asamblea de los Consejos, Radios Comunitarias |
| NRE | En paz la Auctoritas baja | Legiones Ociosas; motín de una legión famosa | Colonias de Veteranos, guerra, donativos |

## Mecánicas v3 — espíritus vivos y reglas de suma fija (2026-09-27)

Pedido del usuario después de jugar: "no se entiende qué gano", "la IA sube
todo y listo", "los caudales tienen números cualquiera", "el desarrollo
llega a 100 al toque y la tensión nunca sube".

- **Espíritus vivos** (`14_decisions.yaml -> dynamic_modifiers`): cada
  potencia tiene un espíritu nacional cuyos números salen de sus variables
  (`common/dynamic_modifiers/`). El pulso mensual (y cada decisión del panel)
  recalcula las variables `<TAG>_ef_*` con `effect: math`. El panel muestra
  el mismo número (`<TAG>_ef_*_ver`, en % y redondeado).
  Las variables de HOI4 tienen 3 decimales: un factor como 0.0015 se escribe
  como ×3 ÷2000.
- **FCU**: las cuatro corporaciones suman siempre 200 (se normalizan). Cada
  una por encima de 50 da su bonus y por debajo lo resta: Castellane →
  estabilidad, Halvorsen → bienes de consumo, Meridian → fábricas militares,
  Obsidian → poder político. Cada contrato sube una 10 y baja otra 10 (lo
  dice el nombre). Sin "el fuerte se hace más fuerte": cada mes una al azar
  hace lobby (+4). La OPA pide Meridian 70 con dos rivales bajo 35.
- **SHD**: los tres caudales suman siempre 150. Producción → fábricas,
  Orden → estabilidad, Pueblo → población reclutable. La Producción crece
  sola (+2 por mes) y se come a los otros dos. Seis decisiones de a pares
  (+10/−10) y el Ajuste Técnico. Zhou: el Pueblo hasta 130.
- **ASC**: el cómputo es un bonus lineal en la prioridad elegida (antes, 12
  ideas por niveles); 30 días sin bonus al cambiar. El calor resta
  estabilidad.
- **APF**: Invertir suma 10 de Desarrollo (antes 20) y 3 de tensión;
  Integrar suma 8 de tensión (15 con Diallo); cada miembro a medio integrar
  suma 2 por mes. El panel explica qué es el Desarrollo.
- **NRE**: el panel explica la Auctoritas (respeto del ejército y moneda de
  las decisiones militares). El prestigio da ataque; la Auctoritas,
  organización; cada legión en 80+ cuesta poder político (reemplaza la idea
  de Privilegios).
- **EFE** (Bioacero → blindaje y defensa; saturación → estabilidad),
  **NAS** (luz guardada → investigación: guardar o gastar), **HSN** (nodos
  → comercio; presión → estabilidad).
- **IA**: las decisiones de a pares solo se toman para corregir (subir lo
  que está bajo 45 bajando lo que está sobre 50); la ASC elige Guerra en
  guerra, Economía con poco cómputo e Investigación con mucho; la APF deja de
  invertir con tensión alta; el NAS guarda luz; los Triunfos se usan en paz
  cuando falta Auctoritas.

## IA militar, satélites y Anarquía (2026-09-27)

- **IA militar** (`16_ai.yaml -> military`): cada meganación tiene un plan en
  paz (25 de industria militar sobre civil, sus roles de división y la
  investigación de lo que sigue en su especialidad: `ai_next_techs` de
  `13_military`) y otro en guerra (75). Roles: EFE blindados, NRE y SHD
  infantería con artillería, HSN marina y astilleros, NAS montaña y cazas,
  ASC y FCU móviles, APF infantería. Tipos e ids se validan contra el juego
  instalado. Declarar la guerra va en un plan aparte que pide 12-16
  divisiones (`divisions_at_least`); prepararse, no.
- **Lealtad de los satélites** (`14_decisions.yaml -> <TAG>_satelites_category`):
  cada meganación guarda la lealtad de sus dos satélites (arranca en 60).
  Cada mes −1 (−2 en guerra), +1 con estabilidad 60%+. 75+: +0,10 de poder
  político por satélite; menos de 25: −0,10 y −3% de estabilidad, y 25% por
  mes de *Descontento* (evento .40/.41: concesiones o mano dura). Ayuda
  (+15, una fábrica en el satélite) y Tributo (−20; +60 PP y 15.000 hombres).
- **Caudillos** (`<TAG>_pulso_caudillos`, eventos .2-.6 de cada Anarquía):
  en paz 8% por mes de saqueo a un vecino (que elige perseguirlos o
  aguantar); 3% por mes de un Caudillo Supremo (idea permanente: org,
  ataque, estabilidad; avisa a los vecinos); en guerra 10% de Tregua de
  Caudillos (90 días de defensa).

## Lote Emiratos (2026-09-27)

- **Arreglo del lector**: los archivos del juego que el mod reescribe
  (regiones, tecnologías, equipo) perdían los operadores de comparación
  (`x < 16` quedaba `x = 16`; `==` rompía el archivo). Ahora se conservan.
- **Doctrina Monroe**: además del evento semanal que la saca, los scripts
  genéricos del juego que reparten espíritus de países vanilla se copian sin
  esos `add_ideas`. El reporte dice de qué archivo salía.
- **Tooltips**: toda variable con nombre (`variable_names`) muestra su cambio
  ("Granjas del Sol: +1"); los focos ya no dicen "no tiene efecto".
- **Emiratos**: 7 milicias, Guerra del Desierto +30% defensa, +15% ataque,
  +10% organización, levas propias y 20% de tregua por mes en guerra.
  Al capitular ante Roma (on_capitulation, eventos nre.50-83): anexar,
  provincia cliente (vasallo) o tomar la costa. Si anexa, 30-39 días
  después la Estepa (equipo), la Comuna (guerra contra Eurasia), la
  Federación (dos regiones) y Eurasia (tributo) exigen su precio. Si Roma
  paga: opinión +40. Si se niega: declaran la guerra por el territorio de
  los Emiratos con ¡Liberar los Emiratos! (+5% org., +15% apoyo bélico, 182
  días). Eventos desde cada punto de vista.
- **16 cadenas** (eventos 100-140 de cada potencia), cada una chequeada una
  vez por mes en el pulso de quien la empieza: Bioacero 12 (EFE→FCU→EFE),
  120 fábricas (ASC→APF→ASC), 15.000 fusiles (NRE→APF), 1.000.000 de
  hombres (SHD→Estepa→SHD), apoyo bélico 80% (NRE→ASC→NRE), 40 divisiones
  del EFE (NAS→EFE→NAS), máquina de cómputo mejorada (ASC→APF), elecciones
  de 2104 (FCU→HSN), Hispania provincia (EFE→NRE→EFE), Caudal Perfecto
  (SHD→HSN→SHD), 4 nodos de la HSN (FCU→HSN), estabilidad bajo 30%
  (APF→ASC→APF), luz 90 (NAS→EFE→NAS), lealtad de Corea bajo 30
  (HSN→SHD→HSN), 80 fábricas de la APF (NRE→APF), la Gran Sequía de 2106
  (EFE→FCU y SHD).
- **HSN**: el panel explica qué es un nodo, lista los 8 (1 = tuyo), qué da
  cada nivel, el precio (presión) y el botín.
- **Cómo se Juega**: decisión gratis en el panel principal de cada potencia
  que vuelve a mostrar la bienvenida (evento .29).
- **Marinas**: destructores heredados para HSN (hasta 6), FCU, NRE, ASC, EFE,
  SHD y APF (hasta 2); todas las meganaciones arrancan con el casco y la
  artillería naval básicos; la IA investiga lo naval (HSN mucho más).

## Lote Anarquías (2026-09-28)

- **Eventos**: cada evento visible escribe `MEGANATIONS evento <id> para <TAG>`
  en game.log, para ver qué saltó en una partida. La cadena de los Emiratos
  salta cuando ZWM capitula y Roma está en guerra con ellos (sin depender de
  ROOT/FROM), y hay respaldo en el pulso de Roma si el tratado de paz ya los
  borró. Gatillos de las cadenas más alcanzables.
- **Paz armada**: nadie arranca en guerra. Cada meganación que toca una
  anarquía (salvo las Tierras Sin Ley) tiene un casus belli que no vence
  (`MEGANATIONS_renovar_casus_belli`, cada mes) y Frontera de sangre (−150).
  La IA se prepara desde el día uno y declara desde su fecha
  (`16_ai.yaml -> anarchy_wars`), con 12 divisiones y sin otra guerra.
- **Leyes y PP**: movilización parcial (meganaciones), baja (satélites),
  economía de guerra (Anarquía); 200 PP de arranque y +0,5 a +0,85 por día en
  los rasgos de los líderes.
- **Tierras Sin Ley**: Alaska, norte de Canadá, Midwest, noroeste de México,
  Guatemala, Nicaragua, oeste de África y Kiev (por nombre de región; el
  reporte avisa si alguno no existe).
- **Árboles de la Anarquía**: una rama de 7 focos; cada uno se habilita al
  sobrevivir (medio año, 1, 1,5, 2, 3, 4 y 5 años) y sube el espíritu
  Resistencia. Amazonas: solo defensa; el 7mo firma paz blanca con todos
  (cada uno se queda con lo que controla) y lo vuelve intocable. Tierras Sin
  Ley: un foco por año con los premios pedidos.
- **Uniones**: Eurasia en Berlín o Londres convoca la Unión de los Señores
  de la Guerra (cada anarquía responde); si un tercero toma Bagdad, el
  Indostán forma el Pacto del Desierto y el Río y entra en las guerras de
  los Emiratos.
- **HSN**: cada nodo suma comercio, astilleros, fábricas y PP; niveles más
  fuertes; la rama de nodos construye de verdad; Reclamar Hong Kong.
- **Ministros y comandantes**: 5 ministros por meganación con rasgos
  propios; un mariscal y tres generales (dos almirantes en la HSN).
- **Debuffs**: 2-3 por meganación, se van con un foco o un objetivo.

## Lote Crisis y Terreno (2026-09-28)

- **Crisis entre potencias**: cuatro ultimátums entre vecinas (el EFE le
  exige Arequipa al Sol, Roma le exige tributo a África, la FCU quiere
  entrar en las aseguradoras de la HSN, la HSN quiere comprarle Taiwán al
  Directorio). Si el otro se niega: casus belli, y la IA se prepara y
  declara con 20 divisiones (eventos .150-.153 de quien exige).
- **Terreno**: ~10% para las cuatro más débiles: Reino del Sol (montaña),
  EFE (selva), Federación Africana (sabana y calor) y HSN (islas). Las
  claves que el juego no conozca se omiten con aviso.
- **La Anarquía recluta**: una milicia por mes (dos en guerra) hasta 40
  divisiones, con fusiles para equiparlas; su IA casi no producía.
- **HSN**: Taiwán pasa al Directorio, Okinawa y Kyushu a Corea; arranca con
  4 nodos de 8 y los focos de los que le faltan dan reclamos.
- **Correcciones del game.log**: las cadenas tienen una fecha mínima
  escalonada (varias saltaban el 2 de enero de 2100); la Anarquía sale cada
  mes de toda facción de meganaciones o satélites y le sacan las garantías
  (los Caudillos del Amazonas habían terminado en la facción de la FCU);
  Londres es "Greater London Area"; se sacan regiones y un rasgo de general
  que en 1.19.3 no existen.

## Lote Guerra Limitada (2026-09-29)

- **Guerra limitada** (`<TAG>_guerra_limitada`, revisada cada semana por el
  evento .159): hasta el 1/1/2104, cuando una meganación rival llega al 40%
  de rendición salta el armisticio (evento .160+4k). Firman todos los de un
  bando con todos los del otro (la potencia, sus satélites y su facción),
  cada uno se queda con lo que ocupa, `set_truce` impide volver a declarar
  durante un año y el perdedor recibe Revancha (+10% apoyo bélico, +5%
  organización, un año). Desde 2104 el ganador elige: firmar o ir hasta la
  capital (evento .161+4k). El perdedor ve su propio evento (.162+4k).
- **Caudales v4 (SHD)**: pronóstico del río (el panel dice qué caudal va a
  empujar +6 el mes que viene: Producción 40%, Orden 30%, Pueblo 30%);
  racha de armonía (+1 por mes en Armonía Perfecta, la Parcial la mantiene,
  salir la pierde) con premios a los 3 meses (100 PP), 6 (dos fábricas), 12
  (El Mandato del Cielo) y 24 (La Era de la Armonía y una casilla de
  investigación); decisión Cerrar las Compuertas (50 PP, cada 91 días)
  que anula el próximo empuje.
- **La IA construye** (`MEGANATIONS_obras_de_la_ia`, en el pulso de cada
  meganación, solo si la maneja la IA): dos niveles de infraestructura por
  mes donde falte y, la mitad de los meses, un espacio de construcción más,
  para que la cola no quede quieta.
- **Satélites del EFE**: Yvytu Ykua Guasu apunta a 22 de IC y la Patagonia
  Austral a 10 (hasta donde den los espacios libres), 4 y 3 divisiones de
  guarnición, e ideas propias (Protegidos del Imperio, Guardianes del
  Hielo) con defensa, organización, reclutamiento y construcción.
- **Correcciones del error.log**: `create_unit` solo vale dentro de una
  región: las divisiones de los focos de la Anarquía y las levas se creaban
  a nivel país y el juego las rechazaba (ahora salen en la capital, o en una
  región propia si está ocupada). La prioridad de investigación de la IA
  dejaba sin cerrar un bloque cuando la tecnología traía `ai_will_do` en un
  renglón, y desarmaba el resto de `electronic_mechanical_engineering.txt`.
  La condición de infraestructura usa `free_building_slots`, como el foco
  genérico del juego.
- **Prueba de scopes**: cada efecto y condición del mod se revisa contra su
  scope (país o región) según las reglas de CWTools.
- **Nombres por ideología**: cada país tiene nombre para los cuatro grupos
  ideológicos y a secas (con otro grupo que el de arranque, el nombre lleva
  el grupo entre paréntesis). En julio de 2101 tres facciones le declararon
  la guerra a un país sin nombre: el bando rebelde de una guerra civil en la
  Anarquía, que no tenía nombre para su ideología.
- **Arte compartido**: los 168 eventos de armisticio usan tres imágenes
  (`art` en el evento, `shared_art` en 12_events.yaml).

## Lote Doctrinas, Santuario y Satélites (2026-09-29)

- **Colores del mapa**: paleta de 30 colores con la máxima distancia visual
  (CIEDE2000): mínimo ~15 entre cualquier par y ~30 entre vecinos; cada
  potencia con el color de su identidad (NRE pasa a púrpura imperial).
- **Leyes por ideología**: los fascistas (EFE, Roma) en economía de guerra;
  la FCU y la HSN con libre comercio; la ASC planificada y cerrada; el Sol
  y la Federación exportando; los satélites un escalón debajo de su señor;
  la Anarquía en guerra con levas.
- **Doctrinas de arranque** (sistema 1.17+, `common/doctrines/` del juego):
  gran doctrina + subdoctrina con 100 de maestría por bloque (el señor y sus
  satélites). EFE movimiento/blindados, Roma asalto en masa/choque, SHD y FCU
  potencia de fuego (artillería / apoyo autopropulsado), ASC y APF plan de
  batalla (operaciones / antitanque), HSN corsaria, NAS aire, Anarquía
  infiltración. Se eligen por nombre o palabra clave; el reporte lista las
  doctrinas del juego.
- **Roma**: búnker 5 en cada provincia que toca a la ASC en los Alpes (las
  regiones que eran italianas y las propias que las tocan).
- **Eurasia y Amazonas**: 7 y 5 milicias, +5% defensa y organización, +10%
  reclutables, menos desgaste.
- **Bioacero v2**: el metal vivo come (la saturación sube la mitad del
  Bioacero guardado cada mes), los focos que dan Bioacero saturan, se pudre
  desde 13, cultivar satura más y la Plaga es más probable cuanto más llenas
  estén las cubas.
- **Altos mandos**: jefes de ejército, marina y aire y dos del alto mando
  por potencia; jefe de ejército y un alto mando por satélite y anarquía
  (82 personajes, 20 rasgos propios `mn_mando_*`).
- **Retratos chicos**: cada retrato con su versión de 65x67 explícita (sin
  ella el juego armaba "<grande>_small" y, con archivos, quedaba vacío: los
  miles de avisos del error.log). 39 retratos pedidos sin provisorio.
- **Democracias**: el Orden de Mercado justifica guerras sin esperar 100% de
  tensión y contra cualquiera (`rule_overrides` / `modifier_overrides`).
- **Eventos**: 5 menores por potencia (por fecha, 2100-2103) y 5 mundiales
  (eclipse, juegos de Ginebra, tormenta solar, gripe gris, cometa) que el
  pulso de cualquier potencia dispara una vez para todos.
- **La sorpresa: la Señal de Próxima** (12/4/2102): un panel compartido por
  las ocho potencias para descifrar 5 fragmentos; la primera escucha el
  mensaje (el Disco de Oro de las Voyager devuelto con TE ESCUCHAMOS) y gana
  La Voz de la Tierra (dos años); las demás reciben la noticia.
- **El lado del satélite**: panel propio con su lealtad; cooperar (+8),
  agitar (-10) y declarar la independencia (lealtad < 20 y el señor en
  guerra o perdiendo, o < 10); el señor la acepta o va a la guerra.
- **El Santuario de Gaia (ZSG)**: si el EFE protege el Amazonas, las regiones
  de la selva que ya son suyas forman una nación neutral con recursos extra
  y guardaparques, garantizada por el EFE para siempre y objetivo de guerra
  de la FCU, la NAS, la ASC y ZAF.
- **Nombres de 2100**: seis regiones clave por potencia fuera de Sudamérica.
- **error.log**: las decisiones de países vanilla quedan como cáscaras
  inertes (otros scripts las nombran).

## Lote Tierras Sin Ley y fronteras (2026-09-29)

- **La FCU y la Federación contra las Tierras Sin Ley**: cuando ZAN termina
  su tercer foco (El Pacto de la Frontera), el pulso mensual le manda a cada
  una un evento, una sola vez. La FCU ("La Frontera se Arma") puede
  justificar la guerra para recuperar lo que ZAN ocupa en Norteamérica
  (Alaska, el norte de Canadá, el Midwest, el noroeste de México, Guatemala
  y Nicaragua); la Federación ("El Oeste no es Tierra de Nadie"), lo que
  ocupa en el África occidental (de Senegal al Alto Volta). El objetivo de
  guerra es "tomar regiones" y lista solo las regiones de ZAN de ese
  continente (las mismas que le da 08_territory.yaml). ZAN recibe el aviso.
  La otra opción da 50 de poder político. La IA acepta casi siempre, se
  prepara y declara cuando tiene 20 divisiones y no está en otra guerra.
- **Fronteras**: el canal de Panamá y Puerto Rico pasan a la FCU (Colombia
  sigue en Nueva Granada); la República Checa y Danzig pasan a la ASC
  (Eslovaquia y la Rutenia se quedan en la Comuna Báltica). Un nombre
  explícito le gana al reparto por dueño.
- **Guerras contra la Anarquía**: si una anarquía pasa a ser satélite de otra
  potencia (por una conferencia de paz), la IA deja de prepararle la guerra y
  de declararle: declararle era declararle a su señor (partida 2026-09-29:
  Eurasia quedó satélite de la ASC y Roma terminó en guerra con la Comuna).
- **Trenes y camiones**: todos arrancan con `basic_train` y `tech_trucks`.
- **Construcción**: cada región arranca con espacios extra (meganaciones +3,
  satélites +2, Anarquía +1) y cada potencia con al menos 10 astilleros (los
  satélites 2) en sus regiones con costa: el NAS y la Federación no tenían.
- **Experiencia**: jefes de ejército, marina y aire dan +0,25 de experiencia
  diaria de su rama; el alto mando +0,1 de la suya.
- **Pantallas de carga**: nueve imágenes propias reparten las pantallas de
  carga del juego; el fondo del menú queda aparte.
- **Estado de Emergencia**: tres decisiones para cada potencia y anarquía,
  una sola vez por partida. I (150 PP): 4 divisiones de infantería, 10.000
  hombres, 1.000 fusiles, -5% estabilidad y apoyo a la guerra. II (200 PP): 6
  divisiones, 15.000 hombres, 1.200 fusiles. III (250 PP): 8 de infantería y
  6 de milicia, 20.000 hombres, 1.000 fusiles y 1.000 de equipo de apoyo. La
  IA las usa en guerra (la II desde 10% de rendición, la III desde 25%).
- **Tierras Sin Ley**: arrancan con La Frontera Armada y sus milicias se
  reparten en cada territorio (2 como mínimo, una más cada 2 regiones).
- **ASC, el Ejército de Máquinas**: el juego no tiene costo de hombres por
  unidad para un solo país; en su lugar, +35% reclutables, +1500 hombres por
  semana, 30% de las bajas vuelven, aviones y barcos con la mitad de
  tripulación.

## Guerras civiles, rama política extendida y forma final (2026-09-29)

- **Guerras civiles (5)**. Se elige bando: el país que se juega es siempre el
  bando elegido y el otro se separa (`start_civil_war`), con nombre y bandera
  propios (cosmetic tag) y su líder con nombre y retrato. Quien gane, sea el
  país original o el que se separó, recibe un espíritu (+15% estabilidad, +10%
  apoyo a la guerra, +0,4 PP, +10% organización, +10% producción).
  - Por foco (la rama de cambiar líder): EFE (El Monte se Levanta: Anahí contra
    la Dinastía de Aurelio IV), NRE (La Legión Decide: Arbogast contra el
    Senado de Varro), APF (Los Consejos se Arman: Diallo contra el Congreso de
    Amara).
  - Por condiciones, aunque no se siga la rama: ASC (PLAN-41 se desconecta si
    el Consejo gobierna con Cómputo ≥ 100 y Calor ≥ 50, sin guerra, desde
    2101.6; con el Cómputo en 100 el Calor sube solo) y SHD (Zhou se levanta
    si Lin gobierna y el Pueblo llega a 70 con el Orden en 35 o menos, o tras
    3 meses seguidos de Desborde; sin guerra, desde 2101. Los tres caudales
    suman 150: la versión anterior, Pueblo 80 y Orden 30, casi no se daba).
- **Rama política extendida**: rama "El Destino de ..." en las 8 potencias:
  tres focos políticos (consolidación, una ley con espíritu propio, el
  ejército) y el foco del destino, que destraba la forma final. Se llega
  desde cualquiera de las dos ramas políticas.
- **La forma final** (decisión, 150 PP): nombre y bandera nuevos, núcleos en
  todas las regiones propias y un gran espíritu nacional. Condiciones:
  - EFE, El Dominio de Gaia: Lima, La Paz, Amazonas, São Paulo, Río, Bogotá y
    Caracas; 45 divisiones; 8 de Bioacero.
  - ASC, La Comuna Continental: París, Roma, Madrid, Leningrado, Crimea y
    Kiev; 60 divisiones; 100 de Cómputo.
  - FCU, La Corporación de las Américas: Minnesota, Kansas, Cuba, Lima,
    Buenos Aires y Bogotá; 50 divisiones; Escándalo < 30.
  - HSN, La Talasocracia de los Siete Mares: Hong Kong, Cantón, Suez, Panamá,
    Gibraltar y el Cabo; 30 divisiones; 7 nodos.
  - NAS, El Imperio del Sol Eterno: Buenos Aires, Santiago, São Paulo,
    Amazonas, Bogotá y Caracas; 35 divisiones; 60 de Inti-Soma.
  - SHD, La Armonía Celeste: Tokio, Hong Kong, Madrás, Manila, Java y Kabul;
    60 divisiones; Orden 60.
  - APF, El Imperio Humano Original: toda África (Adís Abeba, el Cabo,
    Transvaal, Senegal, Liberia), Medio Oriente (Bagdad, Teherán, Néyed) y el
    sur de Europa (Roma, Madrid, Sofía); 60 divisiones.
  - NRE, El Imperio Romano Eterno: Madrid, Lisboa, Alejandría, Trípoli, Suez,
    Londres, Crimea y Sofía; 70 divisiones; 50 de Auctoritas.
  Todas piden además 50% de estabilidad.
- **Arte**: banderas de las 18 identidades nuevas (arte/pedidos 5_banderas;
  hasta que lleguen, la del país) y un archivo con lo nuevo de cada lote.
- **Guerras contra la Anarquía, sin apuro**: la IA recibe el casus belli
  contra su anarquía vecina recién en su fecha de guerra (16_ai.yaml ->
  declare_after); el jugador, desde el primer pulso. Prepararse sí desde el
  día uno; conquistar, desde la fecha (la Federación declaraba a los Emiratos
  en febrero de 2100 aunque su fecha era 2101).

## Caminos económicos con pros y contras (2026-09-29)

- **Ciudades Sedientas (EFE)**: la saca solo el Ministerio de Restauración,
  el foco que abre la rama. Diplomacia del Agua ya no la vuelve a sacar (antes
  las dos la sacaban y una dependía de la otra).
- **Dos focos más por lado** en la rama económica de las 8 potencias (32
  focos). El último cambia el espíritu del camino por uno de tercer nivel, con
  ventajas fuertes y un costo claro:
  - EFE: La Fortaleza Verde (recursos, fábricas; comercio −50%, investigación)
    / El Agua de la Vida (estabilidad, población, PP, comercio; apoyo a la
    guerra −10%, recursos).
  - ASC: El Plan Absoluto (construcción +20%, fábricas; investigación,
    estabilidad, comercio) / El Mercado Total de Datos (investigación +15%,
    comercio; PP, estabilidad).
  - FCU: El Sueño Corporativo (bienes de consumo −15%, estabilidad; apoyo a la
    guerra, reclutables) / El Cártel del Agua (PP +25%, construcción,
    recursos; comercio −30%, estabilidad).
  - HSN: La Bolsa del Mundo (comercio +40%, fábricas; apoyo a la guerra, PP)
    / El Imperio del Peaje (PP +25%, apoyo a la guerra, astilleros; comercio
    −35%, estabilidad).
  - NAS: El Granero del Mundo (estabilidad +20%, construcción, reclutables;
    fábricas, investigación) / La Montaña que Devora (recursos +35%, fábricas;
    estabilidad −10%, reclutables).
  - SHD: El País como Obra (construcción +35%; bienes de consumo, estabilidad)
    / La Economía Exacta (fábricas +25%, investigación +15%; construcción −10%,
    PP).
  - APF: La Federación de Aldeas (estabilidad, defensa +15%, reclutables;
    fábricas −10%, construcción) / El Continente Conectado (construcción +25%,
    recursos, fábricas; estabilidad −10%, bienes de consumo).
  - NRE: La Ciudad Alimentada (estabilidad, población, bienes de consumo −10%;
    fábricas, apoyo a la guerra) / El Tesoro de Saturno (PP +25%, fábricas;
    estabilidad −10%, bienes de consumo). El Nuevo Aureus se abre desde
    cualquiera de los dos finales.
- **El primer espíritu de cada camino** ahora también tiene un costo chico
  (antes eran solo ventajas).
- **Inconsistencias corregidas**: además de Ciudades Sedientas, Los Consejos se
  Arman (APF) sacaba Consejos Desorganizados, que ya había sacado un foco
  obligatorio anterior; ahora da +5% apoyo a la guerra.
- **Chequeo automático** (tools/tests: test_focus_idea_consistency): ningún
  foco saca un espíritu que ya sacó otro foco obligatorio de la misma cadena.
- **La guerra civil ya no borra los espíritus** (2026-09-30): el EFE terminó la
  guerra del Monte con solo La Paz Verde. Al empezar una guerra civil se anotan
  los espíritus del país y las variables de su mecánica; al terminar, el
  ganador recupera los espíritus que le falten (y, si el que ganó es el otro
  bando, también las variables). No vuelven los temporales ni los que un
  recálculo pone y saca solo.

## La Guerra en las Sombras (2026-09-30)

- **Operaciones en la pantalla de inteligencia** (spec/18_intelligence.yaml,
  tools/gen/emitters/intelligence.py): 6 por meganación objetivo, contra
  cualquier otra meganación donde tengas red de espías. La estructura (fases,
  riesgo, equipo) se copia de una operación del juego instalado.
- **Infiltración por pareja (0-100)**: cada operación pide un mínimo y la sube.
  Infiltrar (0, +12) · Robo de Tecnología (20: +8% investigación 6 meses) ·
  Sabotaje Industrial (35: -10% fábricas, -15% construcción 3 meses) · Golpe
  al Corazón (50: pega en la mecánica: calor de la ASC, escándalo de la FCU,
  cubas del EFE, presión del HSN, Inti-Soma del NAS, Pueblo/Orden del SHD,
  tensión de la APF, auctoritas del NRE) · Desestabilización (70) · Encender
  la Rebelión (90: gasta 45; -20 de lealtad en sus dos satélites, evento de
  levantamiento, y en la ASC/SHD acerca su guerra civil).
- **Riesgo**: 10% de que te descubran (35% si se blindaron contra vos): -15 de
  infiltración, -25 PP y el otro se entera.
- **Contrainteligencia** (decisiones): hasta 4 blindajes por ciclo de 3 meses;
  contra quien te blindás, sus operaciones suben la mitad y su infiltración
  baja 4 por mes. Purga Interna (-20 a todos, -5% estabilidad) y Pacto de
  Sombras (-30 de cada lado y un año sin operaciones).
- **Fondos de las pestañas**: 11_scenario -> tab_backgrounds. Por ahora el
  generador lista en el reporte qué texturas usa cada pestaña y su tamaño;
  con eso se piden las imágenes y se completan las rutas.
- **Balance**: anarquías -5% en sus espíritus de combate (ataque, defensa,
  organización, reclutables); FCU con tope de 108 IC y -8% organización.
- **Espías equilibrados** (2026-09-30): las 8 arrancan con su agencia de
  inteligencia (pulso de arranque, `create_intelligence_agency`) y el espíritu
  Servicio de Inteligencia (+2 espacios de agente; con el de la agencia, 3).
  Un sexto ministro por potencia, el de inteligencia, suma espacios y un bonus
  propio: EFE Ojos del Monte (+1, redes +25%), FCU Inteligencia Privada (+2,
  inteligencia civil, -5% PP), ASC Vigilancia Algorítmica (+1, descifrado,
  detecta agentes), HSN Informantes de los Puertos (+2, redes +10%), NAS Los
  Chasquis (+1, redes +15%, cifrado), SHD Censo Total (+1, detecta agentes
  +30%, cifrado), APF Redes de la Diáspora (+2, inteligencia civil), NRE
  Frumentarii (+1, inteligencia militar, redes +10%). Los modificadores de
  inteligencia son opcionales: si el juego no tiene alguno, se omite con aviso.
- **Lote OIM, agencia y mapa** (2026-09-30):
  - OIM propias: cada OIM genérica del juego se copia por meganación con su
    nombre (13_military -> mio) y la genérica deja de estar para las 8. Los 4
    puntos de arranque: el reporte muestra de dónde salen (diagnóstico).
  - Mejoras de la agencia con nombres de 2100 (se buscan por el texto en
    español que muestra el juego) y pedidos de íconos (6_agencia); íconos
    propios para las 6 operaciones (6_operaciones). Molde de las operaciones:
    operation_collaboration_government.
  - Sin zonas desmilitarizadas de 1936 (Rin, Estrechos).
  - Pantallas de carga: también se pisan las de las expansiones que vienen
    dentro de un .zip.
  - Fondos de pestañas: el diagnóstico ahora resuelve las texturas de los
    mosaicos (corneredTileSpriteType).
- **OIM desde cero** (2026-09-30): el juego (09_aat_on_actions) les suma
  tamaño al arrancar según la fecha y en 2100 arrancaban con 4. A los 2 días
  de partida, una sola vez, todas las OIM del mundo bajan a tamaño 1
  (meganations_sombras.4, efecto mio_reset).
- **Fondos**: 11 pedidos (arte/pedidos 7_fondos) con el tamaño real de cada
  textura: fondo del árbol de focos, de investigación, los mosaicos comunes
  (23 y 42 ventanas), el papel de la agencia y las cabeceras de producción,
  oficiales y agencia. Cuando llegan, reemplazan la textura del juego.
- **Interfaz** (2026-09-30): el reporte lista las piezas de estilo del juego
  (barra superior, marcos de ventana con su borde, botones, logos, ventanas
  de eventos y decisiones) con el tamaño de su textura. Se cambian igual que
  los fondos: 11_scenario -> tab_backgrounds -> items (cualquier textura).
  Sin tocar los .gui (la disposición): eso se rompe con cada parche.
- **Individualidad militar** (2026-09-30): además de su rama de especialidad,
  cada potencia arranca con lo que necesitan SUS tropas (13_military ->
  research.country_techs): marina para la HSN, montaña para el NAS,
  ingenieros/reconocimiento/artillería para NRE, SHD y APF, mecanizada para
  ASC y FCU, y el EFE su tanque. La IA (16_ai) arma y produce según eso.
- **Arte** (2026-09-30): 11 fondos de interfaz, 55 focos de la FCU, 18 íconos
  de la agencia, 6 de operaciones y 5 pantallas de carga nuevas (14 en total).
  arte/focos_faltantes.txt: solo los focos que faltan de las naciones que ya
  tienen íconos.
- **Revisión de unidades únicas y logs** (2026-10-01):
  - El superpesado es compañía de apoyo en 1.19.3: la plantilla del
    Gliptodonte lo pone en `support` (fallaba: "Subunit is of support type").
  - OIM: el juego no deja restar tamaño; se saca `add_mio_size` de los
    on_actions del juego (el que les daba 3-4 al arrancar).
  - Levas de la Anarquía: plantilla propia "Leva_Anarquica", que se recrea
    si la IA la borra (las "Milicia" fallaban).
  - Emergencias: el castigo es la Leva Forzosa (modificador con duración):
    6, 9 y 12 meses; se suman si se usan varias.
- **Unidades únicas: costo según poder y mecánica propia** (2026-10-01):
  EFE Gliptodonte 175 PP (Bioacero 6, gasta 4, +10 saturación); FCU Ala de
  Obsidiana 175 (Obsidian 55, −10 Obsidian, +10 Escándalo); HSN Leviatán 150
  (4 nodos, −6 Botín); NRE Onagro 125 (Auctoritas 35, −15); SHD Dragón 125
  (Producción 50, 10 pasan al Orden); APF Kiboko 110 (tensión < 50, +15);
  ASC Centinela 100 (Cómputo 60, −20, +10 calor); NAS Hijos del Cóndor 100
  (Luz 35, −25).
- **Rutas sin callejones** (2026-10-01, análisis de rutas y flow, prioridades 1 a 5):
  1. La IA hace lo político temprano: las dos ramas políticas pesan 3 y la de
     destino 2,5 (antes 1, contra 1,5 a 2 de economía e industria; 5 y 4 fueron demasiado, 2026-10-02). El peso de
     la rama multiplica el del foco, así la elección statu quo/revolución
     mantiene su proporción (el Mandato Renovado del EFE: 3 x 5 = 15).
  2. Los 6 focos que pedían una anarquía viva (Ofensiva Verde, Bajada de la
     Montaña, Liberación del Este, Marcha al Norte, Río se Desborda, Liberar
     el Sinaí) se toman siempre. Si la anarquía sigue libre: objetivo de
     guerra. Si cayó o es satélite de alguien: núcleos en lo que ya es tuyo
     de su tierra y reclamos sobre el resto; si es tu satélite, se anexa.
     Efecto `or_cores` (kind anarchy); la descripción del foco lo explica.
  3. Los Emiratos Caen: también si los Emiratos son satélite de alguien (la
     provincia cliente de Roma) o si la Federación controla Suez y Bagdad.
  4. El Dominio de Gaia: en vez del Amazonas acepta que el Santuario exista
     bajo garantía del EFE. La Ofensiva Verde no reclama tierra del Santuario.
  5. Los 10 focos de satélites (Misiones, Patagonia, Nueva Granada, Llanos,
     Corea, Estepa, Cabo, Tierras Altas, Hispania, Dacia) se toman siempre:
     con el satélite propio, lo de siempre; si ya no es tuyo, núcleos y
     reclamos (`or_cores` kind satellite).
- **Rutas, prioridades 6 a 11** (2026-10-02):
  6. Collasuyu: Antofagasta sigue siendo del EFE, pero ahora se dice. El foco
     abre la Crisis de los Salares (meganations_nas.240-242): el Imperio cede
     (35%) o se niega y el Sol recibe objetivo de guerra por Antofagasta; la
     IA del Sol se prepara y declara (NAS_contra_EFE).
  7. Pax Romana: 70% de estabilidad y paz con las otras meganaciones; la
     guerra contra anarquías ya no la rompe.
  8. La Unión: el plan viejo apuntaba al Amazonas por el Canal (que ya es
     suyo). Ahora se prepara contra la Frontera desde 2101, y La Frontera se
     Arma (casus belli contra ZAN) llega con el Pacto o el 1/6/2101.
  9. PLAN-41 no se desconecta con la rama de destino de la Comuna abierta (la
     forma final pide Cómputo 100, lo que antes derrocaba al Consejo).
  10. Armonía: el río empuja 8 en vez de 6, y con 6+ meses de racha las crisis
      del río pasan de 20% a 30% por mes.
  11. Ultimátums rechazados entre potencias (9): el que exigía recibe la
      bandera <A>_contra_<B> (planes de IA: prepararse, enemistarse y declarar
      con 20 divisiones) y +20 de infiltración contra el que se negó.
- **Segunda etapa, prioridad 12** (2026-10-02):
  - Crisis del siglo: desde 2106, cada 240 días, una de 8 crisis mundiales al
    azar (Sequía, Pandemia del Micelio, Tormenta Solar, Éxodo Climático, Marea
    Negra, Gran Crac, Cumbre de las Ocho, Carrera Orbital) a las 8 potencias:
    pagar para evitarla o comerse un modificador temporal (meganations_mundo.20-27).
  - Elecciones: las del Directorio de la Unión se repiten cada 4 años (2102,
    2106...); la Alta Mar tiene la Asamblea de Armadores cada 4 años desde 2104
    (meganations_hsn.240).
  - La Diplomacia de las Potencias (panel compartido desde 2106): Pacto con X
    (no agresión + garantía mutua; nunca con el rival de bloque) y Ofrecer la
    Paz a X (paz blanca si acepta). Eventos meganations_mundo.40-45.
  - La Era de la Hegemonía (tras la forma final): Integrar lo Conquistado
    (núcleos, una vez por año), La Gran Obra (+10% fábricas, +15% construcción)
    y Hegemonía Mundial (250 fábricas y 100 divisiones; solo una potencia;
    meganations_mundo.50 a las demás).
  - Generador: global_flag con days, efecto relation (diplomatic_relation) y
    FROM/ROOT/PREV como destino de eventos y alcances.
- **Enciclopedia** (2026-10-02): costos nuevos de las unidades únicas, el
  Gliptodonte como tanque moderno y las elecciones de la Unión (2102 y cada 4 años).
- **Avisos del reporte** (2026-10-02):
  - Fondos que el juego estira (árbol de focos, fondo liso 2): ya no se
    descartan. El dibujo queda en las cuatro esquinas, que no se estiran, y se
    funde en un color liso en la cruz del centro: sin rayas.
  - Fondo de blindados: 1.19 no tiene GFX_armor_techtree_bg; el generador
    busca en los .gui de investigación la ventana de blindados y usa el
    sprite más grande que dibuja (search: armor/armour/tank). Si no lo
    encuentra, el reporte lista los candidatos.
- **El Sol y el Directorio, aliados del Mandato** (2026-10-02, pedido del
  usuario: la rivalidad cruzando el Pacífico no tenía sentido). Se saca la
  rivalidad de bloque y los planes de guerra entre ellos. La cadena es ahora
  una alianza en tres pasos:
  1. El Pacto del Mandato (foco del NAS, antes El Sol contra el Directorio):
     el Directorio firma (85%) no agresión + garantía mutua + "Aliados del
     Mandato" (+80 de opinión).
  2. Ingenieros para el Sol (foco del SHD, antes Corregir el Sol): el Sol
     recibe ingenieros (80%): estabilidad, PP e Inti.
  3. Con los dos hechos, los dos reciben El Mandato Compartido (+5%
     investigación, +5% PP, +3% estabilidad).
  Si el otro ya no existe, el foco igual se toma (no traba El Trono del Sol).
- **Nombre de las UU al rediseñarlas** (2026-10-02): el juego nombra cada
  diseño nuevo con el arquetipo + Mk N ("Tanque moderno Mk2"). Si el equipo de
  la UU está bloqueado para el resto, el arquetipo lleva el nombre de la UU
  ("Gliptodonte Mk2", "Leviatán Mk2"...). Los equipos compartidos (los
  tiltrotores del NAS) no se renombran.
- **Tierras Sin Ley: refuerzo anual** (2026-10-02): desde 2101, cada año 5
  divisiones (Leva Anárquica, 4 infanterías) en cada zona: Alaska, norte de
  Canadá, Midwest, noroeste de México, Centroamérica, oeste de África y Kiev.
  Salen en la primera región de la zona que todavía controlen; zona perdida,
  no hay refuerzo ahí. Generador: create_units con `zones`.
- **Logs y crash del 2026-10-03**:
  - Las banderas con vencimiento no frenaban (sin `value = 1`): las
    elecciones de la Unión salían todos los meses, la Asamblea también y las
    crisis del siglo 64 veces por mes. Crash en noviembre de 2106, con
    modificadores de crisis apilados 8 veces. El generador ahora escribe
    { flag value = 1 days } (502 usos: treguas, pactos, esperas).
  - Además, elecciones, Asamblea, crisis y refuerzo de las Tierras Sin Ley
    usan un freno que no depende del vencimiento: bandera permanente que se
    reemplaza y condición has_country_flag = { flag days > N }.
  - Un modificador con duración nunca se agrega si ya está.
  - El Dragón del Gran Canal ya no se regala al depósito (el juego no acepta
    cañones ferroviarios ahí); sale de la producción.
