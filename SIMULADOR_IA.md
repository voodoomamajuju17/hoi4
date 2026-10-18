# Simulador de la IA: lo que hacen las ocho potencias si nadie las toca

1000 partidas por tabla, semilla 2100. Los pesos, condiciones y azares salen del spec; lo que el spec no sabe (guerras, estabilidad, cómo sube cada barra) sale de `tools/simulador/supuestos.yaml`. No simula el mapa ni las batallas. Es un dado cargado con los números del mod, no el juego.

## Ramas políticas

Porcentaje de partidas en que la IA elige el primer foco (el resto elige el otro). ⚠ marca un lado que sale más del 90%: el otro casi no existe para la IA.

| Potencia | Foco | contra | abre (aprox.) | en paz | IA típica | en guerra |
|---|---|---|---|---|---|---|
| EFE | El Mandato Renovado | Los Incendios de Gaia | 2100.6 | 72% | 74% | 59% |
| ASC | El Sorteo del Año | El Silencio del Consejo | 2100.6 | 75% | 74% | 75% |
| FCU | El Segundo Mandato de Castellane | Junta de Accionistas de Emergencia | 2100.6 | 82% | 80% | 71% |
| HSN | El Libro de Fletes | El Motín de Kanto | 2100.6 | 75% | 71% | 62% |
| NAS | La Coronación Renovada | El Inca Rompe el Silencio | 2100.6 | 75% | 71% | 25% |
| SHD | Ajuste Técnico nº 1 | Abrir las Compuertas | 2100.6 | 76% | 72% | 21% |
| APF | Mil Consejos | Los Consejos se Arman | 2100.6 | 73% | 70% | 16% |
| NRE | El Senado Restaurado | La Legión Decide | 2100.6 | 74% | 73% | 58% |

## Ramas económicas

Porcentaje de partidas en que la IA elige el primer foco (el resto elige el otro). ⚠ marca un lado que sale más del 90%: el otro casi no existe para la IA.

| Potencia | Foco | contra | abre (aprox.) | en paz | IA típica | en guerra |
|---|---|---|---|---|---|---|
| EFE | La Autarquía del Bioacero | La Diplomacia del Agua | 2100.6 | 49% | 53% | 78% |
| ASC | El Plan Total | El Mercado de Créditos de Cómputo | 2100.6 | 68% | 68% | 86% |
| FCU | El Dividendo | El Monopolio del Agua | 2100.6 | 67% | 67% | 32% |
| FCU | El Presupuesto Civil | El Presupuesto Militar | 2100.8 | 66% | 68% | 14% |
| HSN | El Puerto Libre | El Peaje de los Estrechos | 2100.6 | 68% | 64% | 48% |
| NAS | Las Terrazas | La Minería del Cielo | 2100.6 | 67% | 64% | 47% |
| SHD | Las Grandes Obras | La Economía de Precisión | 2100.6 | 70% | 67% | 51% |
| APF | La Aldea Autosuficiente | El Corredor Continental | 2100.6 | 34% | 36% | 53% |
| NRE | La Annona | El Tributo | 2100.6 | 52% | 52% | 38% |

## El Rearme Secreto

Se termina el disimulo (tercer descubrimiento): el 10% de las partidas antes de 2109.1, la mitad antes de 2120.6, el 90% antes de 2134.4. Nunca, hasta 2140.1: 11%.

| Potencia | veces descubierta por partida | la descubren primero | exposición máxima (media) |
|---|---|---|---|
| EFE | 0.35 | 13% | 44 |
| FCU | 0.37 | 14% | 44 |
| ASC | 0.37 | 12% | 45 |
| HSN | 0.37 | 12% | 45 |
| NAS | 0.39 | 15% | 45 |
| SHD | 0.32 | 10% | 45 |
| APF | 0.33 | 11% | 45 |
| NRE | 0.34 | 12% | 44 |

## La Sucesión del EFE

Muere Aurelio IV: el 10% antes de 2104.3, la mitad antes de 2105.3, el 90% antes de 2108.5. Sigue vivo en 2140.1: 0%.

| Al morir el Emperador | partidas |
|---|---|
| Tupã Benítez heredero | 54% |
| Yara Pereira, Custodia electa | 27% |
| Etchegaray regente | 19% |

Año en que la IA nombra heredero: 2101: 100%, 2102: 0%.

Colapsos del líder del EFE por partida (Salud en 0): 0: 3%, 1: 20%, 2: 35%, 3: 25%, 4: 13%, 5: 4%, 6: 0%.

## La crisis del siglo (2106-2200)

141 crisis por partida. La misma crisis dos veces seguidas: 0.0 veces por partida; pasa al menos una vez en el 0% de las partidas.

| Crisis | veces por partida |
|---|---|
| La Tormenta Solar | 17.8 |
| La Carrera Orbital | 17.7 |
| El Gran Crac | 17.7 |
| La Cumbre de las Ocho | 17.6 |
| La Gran Sequía | 17.6 |
| El Éxodo Climático | 17.6 |
| La Marea Negra | 17.5 |
| La Pandemia del Micelio | 17.5 |

Racha más larga de la misma crisis: 1 seguidas: 100%.

## Supuestos que se usaron

Condiciones del mapa que el motor no simula (probabilidad fija en supuestos.yaml): `country:YYG`, `divisions_at_least`, `in_faction_with: ROOT`, `subject: false`.

Efectos que no cambian lo que se mide y no se simulan: `build`, `army_experience`, `add_manpower`, `dynamic_modifier`, `air_experience`, `navy_experience`, `add_war_support`, `add_political_power`, `promote`, `end_puppet`, `scope`, `annex`, `retire_leader`, `civil_war`.

