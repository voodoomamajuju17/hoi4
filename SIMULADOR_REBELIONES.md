# Rebeliones, guerras civiles, divisiones y golpes: la chance de cada nación

4000 partidas por nación y escenario, 2100-2120, la IA jugando. Los números del mod se leen del spec; la estabilidad y las barras propias son supuestos (`tools/simulador/supuestos_rebeliones.yaml`). Es un dado cargado con los números del mod, no el juego.

## Las reglas (del spec)

- **El Ultimátum de los Generales**: con estabilidad bajo 50%, 1.5% por mes (3% bajo 35%); después, 12 meses de espera. La IA resiste el 55% (rebelión) y renuncia el resto (golpe: cae el líder, -10% de estabilidad). La rebelión propia pasa una vez por partida.
- **Por cada año entero bajo 50%**: 17% de Ultimátum, 9% de rebelión. Bajo 35%: 31% y 17%.
- **Mechas propias**: la HSN (infamia 50 o más) y la NAS (Sol Bajo) suman 2% por mes bajo 50%; el Directorio, 3% por mes bajo 65% y 4% por mes bajo 50%.
- **La rama forzada** (EFE, APF, Roma): bajo 50%, 4% por mes de que el foco que lleva a la guerra civil se complete solo.
- **El Rumor de Golpe** (El Peso del Poder): cada 5 meses sale una mala noticia del líder o una tregua (peso 3 contra 1 por noticia, de 8); el Rumor sale bajo 50% de estabilidad o con poca Astucia, y termina en Ultimátum el 6.25% de las veces (sin mirar la estabilidad).

## Escenarios de estabilidad

Media de la estabilidad de cada potencia (vuelve a la media y se mueve ±10 puntos): **tranquila** 70%, **tipica** 60%, **agitada** 50%.

## Resumen: alguna guerra civil antes de 2120

| Nación | tranquila | tipica | agitada |
|---|---|---|---|
| Imperio Ecofascista (EFE) | 23% | 43% | 73% |
| Comuna Socialista Automatizada (ASC) | 32% | 37% | 49% |
| Unión Libre de Capital Corporativo (FCU) | 100% | 100% | 100% |
| Nación de Mercado de Alta Mar (HSN) | 13% | 40% | 78% |
| Reino Celeste Neoandino (NAS) | 13% | 40% | 75% |
| Directorio Sino-Armónico (SHD) | 76% | 96% | 100% |
| Federación de los Pueblos Africanos (APF) | 38% | 52% | 78% |
| Neo Imperio Romano (NRE) | 36% | 51% | 77% |

## Nación por nación

### Imperio Ecofascista (EFE)

| Qué | Tipo | tranquila | tipica | agitada |
|---|---|---|---|---|
| El Cono Sur se Levanta (el líder resiste el Ultimátum) | guerra civil | 11% | 29% | 61% |
| Golpe: el líder renuncia ante el Ultimátum | golpe | 9% | 23% | 39% |
| La Guerra del Monte (los Incendios de Gaia → El Monte se Levanta) | guerra civil | 14% | 16% | 15% |
| *(partidas con un Ultimátum que vino del Rumor de Golpe)* | | 12% | 15% | 23% |

### Comuna Socialista Automatizada (ASC)

| Qué | Tipo | tranquila | tipica | agitada |
|---|---|---|---|---|
| Los Hijos de Odín (el líder resiste el Ultimátum) | crisis | 11% | 33% | 70% |
| Golpe: el líder renuncia ante el Ultimátum | golpe | 9% | 25% | 42% |
| Albión renace (división, si pierde contra Roma) | división | 15% | 15% | 15% |
| El Reino del Valhalla | guerra civil | 5% | 12% | 26% |
| PLAN-41 se Desconecta | guerra civil | 28% | 27% | 26% |
| *(partidas con un Ultimátum que vino del Rumor de Golpe)* | | 11% | 16% | 23% |

### Unión Libre de Capital Corporativo (FCU)

| Qué | Tipo | tranquila | tipica | agitada |
|---|---|---|---|---|
| Las Zonas Rompen con la Unión (el líder resiste el Ultimátum) | división | 11% | 32% | 69% |
| Golpe: el líder renuncia ante el Ultimátum | golpe | 9% | 25% | 43% |
| La Secesión de Meridian | guerra civil | 100% | 100% | 100% |
| *(partidas con un Ultimátum que vino del Rumor de Golpe)* | | 12% | 16% | 22% |

### Nación de Mercado de Alta Mar (HSN)

| Qué | Tipo | tranquila | tipica | agitada |
|---|---|---|---|---|
| La Cruz del Mar (el líder resiste el Ultimátum) | guerra civil | 13% | 40% | 78% |
| Golpe: el líder renuncia ante el Ultimátum | golpe | 11% | 31% | 47% |
| El Shogunato de los Astilleros | división | 29% | 29% | 29% |
| Nace la República Pirata | división | 90% | 89% | 90% |
| *(partidas con un Ultimátum que vino del Rumor de Golpe)* | | 12% | 15% | 22% |

### Reino Celeste Neoandino (NAS)

| Qué | Tipo | tranquila | tipica | agitada |
|---|---|---|---|---|
| El Sol Negro (el líder resiste el Ultimátum) | guerra civil | 13% | 40% | 75% |
| Golpe: el líder renuncia ante el Ultimátum | golpe | 11% | 28% | 45% |
| *(partidas con un Ultimátum que vino del Rumor de Golpe)* | | 13% | 16% | 23% |

### Directorio Sino-Armónico (SHD)

| Qué | Tipo | tranquila | tipica | agitada |
|---|---|---|---|---|
| La Máquina Roja (el líder resiste el Ultimátum) | guerra civil | 71% | 95% | 100% |
| Golpe: el líder renuncia ante el Ultimátum | golpe | 43% | 48% | 49% |
| El Río se Desborda | guerra civil | 11% | 7% | 4% |
| *(partidas con un Ultimátum que vino del Rumor de Golpe)* | | 12% | 15% | 24% |

### Federación de los Pueblos Africanos (APF)

| Qué | Tipo | tranquila | tipica | agitada |
|---|---|---|---|---|
| Los Pueblos se Levantan (el líder resiste el Ultimátum) | guerra civil | 10% | 24% | 49% |
| Golpe: el líder renuncia ante el Ultimátum | golpe | 8% | 20% | 33% |
| La Guerra de los Consejos (Los Consejos se Arman) | guerra civil | 30% | 30% | 34% |
| *(partidas con un Ultimátum que vino del Rumor de Golpe)* | | 12% | 15% | 23% |

### Neo Imperio Romano (NRE)

| Qué | Tipo | tranquila | tipica | agitada |
|---|---|---|---|---|
| El Cisma de Oriente (el líder resiste el Ultimátum) | guerra civil | 10% | 25% | 51% |
| Golpe: el líder renuncia ante el Ultimátum | golpe | 8% | 20% | 34% |
| La Guerra de las Legiones (La Legión Decide) | guerra civil | 27% | 29% | 31% |
| *(partidas con un Ultimátum que vino del Rumor de Golpe)* | | 12% | 15% | 22% |

## Japón, Albión y las anarquías

- **Japón (Shogunato de los Astilleros)**: no tiene Ultimátum propio (no está en la lista de rebeliones de las potencias); se parte solo en sus aventuras (abajo).
- **Albión**: además de sus aventuras, la Guerra de las Dos Eras (la Pompa cae dos veces bajo 10, o la Red cae dos veces): 25% estimado, con Albión ya formada (renace en el 15% de las partidas, si la Comuna pierde contra Roma).
- **Las anarquías** (Caudillos del Amazonas, Señores de la Guerra de Eurasia, del Indostán, Emiratos del Desierto, Tierras Sin Ley): sin Ultimátum; se parten en los finales malos de sus aventuras.

## Las aventuras (si las jugás eligiendo al azar)

Personaje y opciones al azar: la chance de llegar a un final o una opción con rebelión o crisis.

| Aventura | Nación | Qué puede pasar | Chance |
|---|---|---|---|
| La Semilla Madre | ZWE | guerra de NRE | 4% |
| La Semilla Madre | ZWE | rebelión: El Gran Molinero | 3% |
| El Sello del Río | ZWI | guerra de SHD | 3% |
| El Sello del Río | ZWI | rebelión: Su Santidad la Cabra | 4% |
| El Águila de Arbogast | ZWM | guerra de NRE | 1% |
| El Águila de Arbogast | ZWM | rebelión: Legado Gaius Severo | 6% |
| La Selva de Acero | ZWB | guerra de EFE | 3% |
| La Selva de Acero | ZWB | rebelión: La Santa Mano | 4% |
| El Censo | ZAN | guerra de FCU | 4% |
| El Censo | ZAN | rebelión: El Barón del Hielo | 3% |
| El Censo | ZAN | rebelión: Nadie | 4% |
| El Despertar | las meganaciones | crisis (el Ultimátum) | 10% |
| La Corona de Vapor | ZAL | rebelión: Presidente Tom Ashworth | 31% |
| La Gran Sincronía | ZAL | rebelión: Anciano Josiah Hale | 28% |
| La OPA Hostil | ZJP | guerra de HSN | 33% |
| El Último Oyabun | ZJP | rebelión: Oyabun Masaki Hayama | 25% |
| Los Hijos de la Cuba | ZJP | guerra de SHD | 14% |
| Los Hijos de la Cuba | ZJP | rebelión: Mariscal Nao Fujita | 12% |
| Los Hijos de la Cuba | ZJP | rebelión: Nanami 117 | 14% |

## Supuestos

- Ramas que elige la IA (SIMULADOR_IA.md, IA típica): EFE 26%, APF 30%, NRE 27%.
- Barras propias (estimadas a mano): EFE_monte 60%, ASC_plan41 30%, ASC_valhalla 35%, SHD_crecida 15%, HSN_reputacion_50 40%, NAS_sol_bajo 25%, HSN_australia_satelite 90%, ZJP_se_separa 30%, ZAL_renace 15%, ZAL_guerra_eras 25%.
- No simula el mapa: guerras, conquistas y derrotas cambian la estabilidad más que cualquier otra cosa; por eso van los tres escenarios.
- Nada de esto se probó dentro del juego.
