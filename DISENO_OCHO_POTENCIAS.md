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
2. **EFE** — rehacer el árbol actual con este formato: Aurelio vs Anahí,
   integración de satélites por misiones, reforestación por etapas.
3. **ASC** — Poder de Cómputo repartido en 4 áreas con espera de 30 días;
   Consejo Sorteado con rasgos anuales; PLAN-41 con drones.
4. **HSN, NAS, APF** — nodos + botín; Qhapaq Ñan + Inti-Soma; integración
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
