# Estabilidad del Directorio: simulación 2100-2119

Generado con `python3 -m tools.simulador.estabilidad_shd --antes 9f4fa5e --salida SIMULADOR_ESTABILIDAD_SHD.md` (antes = el spec que jugó la partida del 2026-11-22; después = el de ahora). Es un modelo: lo que no sale del spec (cuándo conquista, cuándo pasan los eventos, lo que pone el motor) está en tools/simulador/supuestos_estabilidad_shd.yaml.

2000 partidas por escenario. Lo que pone el juego en el primer año (partido, leyes) calibrado con la partida del 2026-11-22: +5 puntos.

Chances de que estalle el Ultimátum de los Generales (por mes):
  - estabilidad 0-35%: 3.0% (MEGANATIONS_crisis_ultimatum)
  - estabilidad 35-50%: 1.5% (MEGANATIONS_crisis_ultimatum)
  - estabilidad 0-65%: 3.0% (mecha del Directorio)
  - estabilidad 0-50%: 4.0% (mecha del Directorio)
  - si estalla, el líder resiste (guerra civil) el 55% de las veces; si no, cae (-10%).
  - Siberia se levanta si le declara a Eurasia con menos de 80%.

## como la partida

| año | regiones | antes: estab. (10-90%) | antes: guerra civil | después: estab. (10-90%) | después: guerra civil |
|---|---|---|---|---|---|
| 2100 | 71 | 67% (67-67) | 0% | 64% (64-64) | 0% |
| 2101 | 71 | 88% (76-100) | 0% | 79% (69-88) | 2% |
| 2102 | 69 | 100% (100-100) | 0% | 100% (92-100) | 2% |
| 2103 | 171 | 100% (100-100) | 0% | 96% (78-100) | 2% |
| 2104 | 226 | 100% (91-100) | 0% | 76% (58-94) | 4% |
| 2105 | 290 | 100% (86-100) | 0% | 67% (44-85) | 10% |
| 2106 | 347 | 97% (71-100) | 0% | 47% (22-67) | 28% |
| 2108 | 493 | 100% (93-100) | 2% | 60% (35-86) | 56% |
| 2110 | 537 | 100% (84-100) | 2% | 53% (25-79) | 66% |
| 2112 | 621 | 100% (77-100) | 2% | 46% (15-75) | 74% |
| 2115 | 672 | 94% (65-100) | 4% | 34% (2-65) | 84% |
| 2119 | 671 | 81% (46-100) | 9% | 19% (0-52) | 92% |
- antes: 1.1 años bajo 60% en promedio; Siberia se levanta en el 0%; el líder cae por un ultimátum en el 8%.
- después: 12.1 años bajo 60% en promedio; Siberia se levanta en el 2%; el líder cae por un ultimátum en el 43%.

## conquista moderada

| año | regiones | antes: estab. (10-90%) | antes: guerra civil | después: estab. (10-90%) | después: guerra civil |
|---|---|---|---|---|---|
| 2100 | 71 | 67% (67-67) | 0% | 64% (64-64) | 0% |
| 2101 | 71 | 88% (76-100) | 0% | 78% (69-89) | 2% |
| 2102 | 71 | 100% (100-100) | 0% | 100% (92-100) | 2% |
| 2103 | 120 | 100% (100-100) | 0% | 100% (83-100) | 2% |
| 2104 | 140 | 100% (100-100) | 0% | 96% (77-100) | 3% |
| 2105 | 160 | 100% (96-100) | 0% | 90% (71-100) | 3% |
| 2106 | 173 | 100% (93-100) | 0% | 85% (66-100) | 4% |
| 2108 | 200 | 99% (74-100) | 0% | 65% (39-87) | 15% |
| 2110 | 204 | 100% (85-100) | 1% | 69% (42-96) | 32% |
| 2112 | 207 | 100% (76-100) | 2% | 62% (30-90) | 41% |
| 2115 | 213 | 95% (63-100) | 3% | 50% (14-82) | 55% |
| 2119 | 220 | 81% (45-100) | 9% | 33% (0-69) | 73% |
- antes: 1.1 años bajo 60% en promedio; Siberia se levanta en el 0%; el líder cae por un ultimátum en el 7%.
- después: 7.9 años bajo 60% en promedio; Siberia se levanta en el 6%; el líder cae por un ultimátum en el 40%.

## sin conquistar

| año | regiones | antes: estab. (10-90%) | antes: guerra civil | después: estab. (10-90%) | después: guerra civil |
|---|---|---|---|---|---|
| 2100 | 71 | 67% (67-67) | 0% | 64% (64-64) | 0% |
| 2101 | 71 | 88% (76-100) | 0% | 79% (69-88) | 2% |
| 2102 | 72 | 100% (100-100) | 0% | 100% (91-100) | 2% |
| 2103 | 72 | 100% (100-100) | 0% | 100% (86-100) | 2% |
| 2104 | 73 | 100% (100-100) | 0% | 100% (82-100) | 2% |
| 2105 | 73 | 100% (96-100) | 0% | 98% (78-100) | 2% |
| 2106 | 74 | 100% (92-100) | 0% | 94% (73-100) | 2% |
| 2108 | 75 | 100% (83-100) | 0% | 87% (63-100) | 5% |
| 2110 | 76 | 100% (74-100) | 0% | 79% (53-100) | 9% |
| 2112 | 77 | 100% (76-100) | 1% | 76% (46-100) | 16% |
| 2115 | 78 | 94% (64-100) | 3% | 66% (31-94) | 30% |
| 2119 | 80 | 80% (45-100) | 9% | 49% (13-81) | 52% |
- antes: 1.1 años bajo 60% en promedio; Siberia se levanta en el 0%; el líder cae por un ultimátum en el 7%.
- después: 4.6 años bajo 60% en promedio; Siberia se levanta en el 0%; el líder cae por un ultimátum en el 30%.

