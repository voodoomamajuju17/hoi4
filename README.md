# 2100 Meganations

Total conversion de Hearts of Iron IV ambientado en el año 2100. Ocho
mega-naciones con mecánicas nacionales asimétricas, más treinta países libres.

> **Nota de nombre.** El pedido original hablaba de *"Seven Dominions"*, 2137 y
> siete facciones. La biblia de diseño dice *2100 Meganations*, año 2100 y ocho
> mega-naciones. Confirmado: manda el documento.

## Regla dura

**Los `.txt` del mod son SALIDA del generador. Nunca se editan a mano.**

Si cambia el lore, cambia `spec/` y se regenera todo. `make check` falla si
alguien tocó `build/` a mano, y muestra qué archivo.

```
spec/*.yaml   ──►   tools/gen   ──►   build/meganations_2100/
assets/             (Python)          (generado, no tocar)
(a mano)
```

## Uso

```bash
make validate                                   # valida spec/ sin escribir nada
make build   HOI4_PATH="/ruta/a/Hearts of Iron IV"
make check   HOI4_PATH="..."                    # ¿build/ coincide con spec/?
make install HOI4_PATH="..."                    # copia a la carpeta de mods
make test                                       # tests del generador
```

Única dependencia: **PyYAML**. El resto es stdlib — los TGA y DDS placeholder
se escriben a mano con `struct` para no depender de Pillow.

### Por qué hace falta `HOI4_PATH`

No es opcional de hecho. El generador lee la instalación vanilla para tres
cosas, todas para no adivinar:

| Qué | Por qué se lee en vez de escribirse |
|---|---|
| `documentation/` e `interface/` | Cada modificador, trigger y efecto que emitimos se busca ahí, y cada ícono de foco en los `.gfx`. Un nombre que no existe frena el build en vez de aparecer en `error.log`. |
| `localisation/` | BioSteel es el carbón vanilla renombrado. Las claves a pisar se buscan por texto ("Coal"), no se escriben de memoria. |
| `common/ideologies/` | La estrategia de reskin inyecta nuestras sub-ideologías en los cuatro grupos vanilla. Escribir el archivo de cero significaría reproducir de memoria los bloques `rules`, `ai` y `dynamic_faction_names`: un campo olvidado rompe la carga. |
| `history/states/` | El reparto territorial del spec está por nombre de región. Un state ID inventado reasigna territorio ajeno **en silencio**, sin error de carga. |
| `launcher-settings.json` | `supported_version` sale de ahí en vez de un número hardcodeado que envejece. |

Sin `HOI4_PATH` el generador igual corre, pero **salta las ideologías y avisa
fuerte**: el mod no va a cargar porque los países apuntan a ideologías que no
existen. No inventa nada para tapar el hueco.

`build/` no está en git justamente porque su contenido depende de tu
instalación. Se genera local.

## Estructura

```
spec/                 fuente de verdad, editable a mano
assets/               arte hecho a mano (banderas, retratos, íconos). El spec
                      dice dónde va cada archivo; el generador lo copia tal cual
  00_project.yaml     metadatos, restricciones, decisiones de arquitectura
  01_ideologies.yaml  ... (ver spec/README.md)
  99_open_questions.yaml   43 preguntas, por fase que bloquean

tools/gen/            el generador
  pdx.py              lee y escribe Paradox script
  loc.py              localisation con garantía de cero claves huérfanas
  art.py              TGA/DDS placeholder sin dependencias
  vanilla.py          puente con la instalación del juego
  specload.py         carga y valida spec/
  emitters/           un módulo por dominio de salida:
                      descriptor, ideologies, countries, resources,
                      ideas, characters, focus_trees, events,
                      territory, history, scenario
tools/tests/          751 checks, corren sin el juego instalado

build/                SALIDA. Generada, no versionada, no editable.
```

## Procedencia

Todo nodo del spec lleva un campo `src`: `canon` (literal del documento),
`inferred` (deducido), `invented` (**mío, porque HOI4 no carga sin ese dato**,
siempre con un `why`), `canon_superseded`, `non_canon_legacy` o `unknown`.

Si al leer el spec no sabés de dónde salió un dato, es un bug del spec.

## Estado

| Fase | Estado |
|---|---|
| 1 — Spec | listo |
| 2 — Arquitectura y generador | listo |
| 3 — Vertical slice del EFE | jugable en 1.19.3: árbol de 31 focos, 4 eventos, minijuego del BioSteel, arte propio |
| 4 — Loop de debug con `error.log` | en curso: cada prueba en el juego alimenta el generador |
| 5 — Las otras siete | territorio, líder, ideología, ejército y balance listos; faltan árboles, ideas y mecánicas propias (Q030, Q032) y la diplomacia (Q018) |

El mundo entero es del mod: 8 meganaciones, 16 satélites y la Anarquía. Los
países del juego base quedan sin territorio. `build/balance.txt` resume con qué
arranca cada facción.

Lo que **no** cubren los tests, y por eso existe la Fase 4: si HOI4 acepta los
nombres de campo que emitimos. Eso solo lo dice `error.log`.
