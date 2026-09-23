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
5. **SHD y NRE al final** — tres caudales; prestigio de legiones +
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
