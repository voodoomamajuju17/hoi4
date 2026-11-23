# Estabilidad del Directorio: simulación 2100-2119

Generado con `python3 -m tools.simulador.estabilidad_shd --antes HEAD` el 2026-11-23 (antes = la mecha del 2026-11-22, 3% bajo 65% y 4% bajo 50%; después = 1,5% y 2,5%, pedido "bajar también la posibilidad en SHD"). Es un modelo: lo que no sale del spec (cuándo conquista, cuándo pasan los eventos, lo que pone el motor) es un supuesto.

2000 partidas por escenario. Lo que pone el juego en el primer año (partido, leyes) calibrado con la partida del 2026-11-22: +11 puntos.

Chances de que estalle el Ultimátum de los Generales (por mes):
  - estabilidad 0-35%: 3.0% (MEGANATIONS_crisis_ultimatum)
  - estabilidad 35-50%: 1.5% (MEGANATIONS_crisis_ultimatum)
  - estabilidad 0-65%: 1.5% (mecha del Directorio)
  - estabilidad 0-50%: 2.5% (mecha del Directorio)
  - si estalla, el líder resiste (guerra civil) el 55% de las veces; si no, cae (-10%).
  - Siberia se levanta si le declara a Eurasia con menos de 80%.

## como la partida

| año | regiones | antes: estab. (10-90%) | antes: guerra civil | después: estab. (10-90%) | después: guerra civil |
|---|---|---|---|---|---|
| 2100 | 71 | 67% (67-67) | 0% | 67% (67-67) | 0% |
| 2101 | 71 | 88% (79-97) | 0% | 87% (78-97) | 0% |
| 2102 | 69 | 100% (100-100) | 0% | 100% (100-100) | 0% |
| 2103 | 171 | 100% (88-100) | 0% | 100% (88-100) | 0% |
| 2104 | 226 | 86% (67-100) | 1% | 86% (68-100) | 1% |
| 2105 | 290 | 76% (55-95) | 4% | 76% (56-95) | 3% |
| 2106 | 347 | 57% (33-77) | 16% | 57% (34-78) | 11% |
| 2108 | 493 | 72% (44-96) | 41% | 73% (45-97) | 31% |
| 2110 | 537 | 65% (34-90) | 49% | 65% (36-92) | 37% |
| 2112 | 621 | 57% (25-85) | 56% | 58% (26-86) | 45% |
| 2115 | 672 | 45% (12-76) | 67% | 46% (13-78) | 58% |
| 2119 | 671 | 30% (0-65) | 81% | 29% (0-66) | 73% |
- antes: 9.6 años bajo 60% en promedio; Siberia se levanta en el 0%; el líder cae por un ultimátum en el 41%.
- después: 9.5 años bajo 60% en promedio; Siberia se levanta en el 0%; el líder cae por un ultimátum en el 38%.

## conquista moderada

| año | regiones | antes: estab. (10-90%) | antes: guerra civil | después: estab. (10-90%) | después: guerra civil |
|---|---|---|---|---|---|
| 2100 | 71 | 67% (67-67) | 0% | 67% (67-67) | 0% |
| 2101 | 71 | 88% (78-97) | 0% | 88% (78-98) | 0% |
| 2102 | 71 | 100% (100-100) | 0% | 100% (100-100) | 0% |
| 2103 | 120 | 100% (92-100) | 0% | 100% (93-100) | 0% |
| 2104 | 140 | 100% (86-100) | 0% | 100% (85-100) | 0% |
| 2105 | 160 | 99% (79-100) | 0% | 98% (79-100) | 0% |
| 2106 | 173 | 94% (73-100) | 0% | 94% (73-100) | 1% |
| 2108 | 200 | 74% (50-97) | 7% | 74% (50-96) | 5% |
| 2110 | 204 | 81% (50-100) | 19% | 80% (52-100) | 14% |
| 2112 | 207 | 74% (40-98) | 25% | 73% (41-99) | 18% |
| 2115 | 213 | 61% (25-89) | 37% | 61% (26-92) | 30% |
| 2119 | 220 | 43% (8-78) | 58% | 43% (8-79) | 50% |
- antes: 5.6 años bajo 60% en promedio; Siberia se levanta en el 1%; el líder cae por un ultimátum en el 35%.
- después: 5.6 años bajo 60% en promedio; Siberia se levanta en el 1%; el líder cae por un ultimátum en el 31%.

## sin conquistar

| año | regiones | antes: estab. (10-90%) | antes: guerra civil | después: estab. (10-90%) | después: guerra civil |
|---|---|---|---|---|---|
| 2100 | 71 | 67% (67-67) | 0% | 67% (67-67) | 0% |
| 2101 | 71 | 87% (78-98) | 0% | 88% (78-98) | 0% |
| 2102 | 72 | 100% (100-100) | 0% | 100% (100-100) | 0% |
| 2103 | 72 | 100% (96-100) | 0% | 100% (95-100) | 0% |
| 2104 | 73 | 100% (92-100) | 0% | 100% (91-100) | 0% |
| 2105 | 73 | 100% (87-100) | 0% | 100% (86-100) | 0% |
| 2106 | 74 | 100% (82-100) | 0% | 100% (82-100) | 0% |
| 2108 | 75 | 95% (73-100) | 1% | 96% (73-100) | 1% |
| 2110 | 76 | 88% (64-100) | 3% | 88% (65-100) | 2% |
| 2112 | 77 | 86% (57-100) | 8% | 85% (58-100) | 6% |
| 2115 | 78 | 75% (41-100) | 16% | 75% (42-100) | 13% |
| 2119 | 80 | 60% (21-90) | 36% | 60% (23-92) | 29% |
- antes: 3.0 años bajo 60% en promedio; Siberia se levanta en el 0%; el líder cae por un ultimátum en el 23%.
- después: 3.0 años bajo 60% en promedio; Siberia se levanta en el 0%; el líder cae por un ultimátum en el 19%.

