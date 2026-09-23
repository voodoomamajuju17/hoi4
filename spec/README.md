# spec/ — Fuente de verdad del mod

Este directorio es **la única fuente editable a mano** del proyecto.

A partir de la Fase 2, todo `.txt` dentro de `common/`, `events/`, `history/`,
`localisation/` y `gfx/` será **salida** del generador Python. Si cambia el lore,
se cambia el spec y se regenera. Nunca al revés.

## Archivos

| Archivo | Contenido |
|---|---|
| `00_project.yaml` | Metadatos del mod, convenciones, decisiones de arquitectura pendientes |
| `01_ideologies.yaml` | Ideologías custom y su mapeo a los grupos vanilla |
| `02_countries.yaml` | Los 8 TAGs principales + satélites: nombres, colores, capitales |
| `03_leaders.yaml` | Líderes de país y personajes |
| `04_diplomacy.yaml` | Relaciones iniciales: sujeciones, facciones, opiniones, guerras |
| `05_ideas.yaml` | Ideas nacionales (spirits) por país |
| `06_mechanics.yaml` | Los sistemas nacionales asimétricos, con su estado de definición |
| `07_focus_trees.yaml` | Esqueleto de árboles de foco |
| `08_territory.yaml` | Reparto territorial sobre el mapa vanilla |
| `09_free_countries.yaml` | Los 30 países libres |
| `10_legacy_lore.yaml` | Material histórico / no canon, conservado como banco de ideas |
| `11_scenario.yaml` | Bookmark de 2100, fechas de inicio y fin del juego |
| `99_open_questions.yaml` | Preguntas abiertas, en formato legible por máquina |

## Convención de procedencia

**Todo** nodo con contenido sustantivo lleva un campo `src` con uno de estos valores:

| `src` | Significado |
|---|---|
| `canon` | Está literal en la biblia de diseño. |
| `canon_superseded` | Estaba en el doc, pero una revisión posterior lo reemplazó. Se conserva para trazabilidad. |
| `inferred` | Deducido del doc por lectura razonable, no literal. Revisable. |
| `invented` | **No está en el doc.** Lo puse yo porque HOI4 no carga sin ese dato. Siempre lleva `why`. |
| `non_canon_legacy` | Material 2023 / cronología 2080. No es canon; banco de ideas. |
| `unknown` | Falta el dato. Siempre tiene una entrada correspondiente en `99_open_questions.yaml`. |

Regla: si al leer el spec no sabés de dónde salió un dato, es un bug del spec.

## Estado de cobertura

El documento tiene una asimetría enorme de detalle: el EFE está muy desarrollado
y las otras siete potencias están definidas casi solo por nombre de mecánica.
Eso está reflejado tal cual en el spec — no se rellenó por inferencia.

| TAG | Territorio | Líder | Mecánica | Ideas | Focus tree |
|---|---|---|---|---|---|
| EFE | canon | canon | parcial | inferido | esqueleto |
| ASC | unknown | unknown | canon (loop claro) | unknown | unknown |
| FCU | unknown | unknown | parcial | unknown | unknown |
| HSN | unknown | unknown | solo nombre | unknown | unknown |
| NAS | unknown | unknown | solo nombre | unknown | unknown |
| SHD | unknown | unknown | solo nombre | unknown | unknown |
| APF | unknown | unknown | parcial | unknown | unknown |
| NRE | unknown | unknown | solo nombre | unknown | unknown |

Por eso la vertical slice de la Fase 3 es **EFE**: es la única facción que se
puede implementar de punta a punta sin inventar canon.
