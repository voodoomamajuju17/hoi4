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
