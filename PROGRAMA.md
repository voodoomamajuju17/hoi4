# 2100 Meganations — Programa de trabajo

Checklist de todo lo que sigue, en orden de importancia: de lo general
(que el mod funcione y el mundo tenga sentido) a lo específico (identidad de
cada facción) y terminando en flavor puro. Dentro de cada bloque, los
elementos también van por importancia.

`[x]` hecho · `[~]` hecho pero sin probar en el juego · `[ ]` pendiente

---

## 0. Verificación en el juego (antes de cada bloque nuevo)

- [ ] Correr `empezar.bat` con la última versión y pasar `reporte.txt`
- [ ] Abrir partida con el EFE y con otra meganación: que cargue sin crash
- [ ] Pasar `error.log` para limpiar lo nuevo
- [ ] Mirar `balance.txt`: reparto, industria, recursos (totales OK), tropas, barcos y aviones

## 1. Estabilidad técnica

- [x] El mod carga, la partida arranca en 2100
- [x] Sin crash por la historia de 1936 (países vanilla reducidos)
- [x] Colores, ideologías y localisation en replace/
- [~] Listas de nombres de personajes para los 29 países
- [ ] Limpiar el ruido de error.log:
  - [ ] on_actions vanilla que apuntan a eventos que ya no cargan (evaluar `replace_path` de `common/on_actions` conservando los esenciales)
  - [~] decisiones nacionales vanilla de países que no existen (China, Congo...): archivos vaciados
  - [ ] "AI tried to post an invalid command: unlock_trait_command"
- [~] Culturas gráficas por región (Q013): sudamericana, asiática, africana, Commonwealth, Europa oriental, Medio Oriente
- [x] Fondo del menú principal: se pisan todas las pantallas de carga grandes (confirmado por el usuario)
- [ ] Rendimiento: medir días por segundo con 29 países + guerras activas

## 2. Mundo y balance global

- [x] Reparto del mundo: 8 meganaciones, 16 satélites, la Anarquía
- [~] La Anarquía en 5 señores de la guerra unidos en una facción
- [~] Recursos invariables: mínimos por transferencia, total mundial = vanilla
- [~] Industria en franja (meganaciones 95-115 IC, satélites hasta 35); la NAS no llega por falta de slots
- [~] Leyes de reclutamiento según población
- [~] Población comprimida (2026-09-26): ~15% de la real y achicando la brecha entre potencias (SHD ~35M, NAS ~5M), así el crecimiento queda parejo
- [~] La Anarquía resiste: 3 milicias por país, espíritus defensivos, levas mensuales en guerra (hombres + fusiles); los Emiratos con "Guerra del Desierto"
- [~] Ejército inicial mínimo (2 infanterías por meganación, 1 por satélite y por país anárquico), tecnologías base + especialidad, depósitos
- [~] Armada: solo 3 destructores de la HSN; sin aviones
- [~] Mundo vivo: reclamos, rivalidades, tensión mundial, 2 guerras al arranque
- [~] 9 facciones: cada meganación con sus 2 satélites, más la Anarquía
- [~] Congo: dueños dentro de bloques condicionales borrados + red de seguridad al arrancar
- [ ] Ajustar con los números reales de `balance.txt` (objetivos de IC, pisos, tropas)
- [ ] Decidir si la FCU necesita una penalización propia (hoy es la más fuerte en la práctica)
- [~] IA: estrategias por meganación (a quién atacar y proteger); IA militar 2026-09-27: tropas según especialidad, investigación de su especialidad, industria en armas (más en guerra), declarar guerra solo con 12-16 divisiones
- [ ] IA de la Anarquía: que se defienda sin atacar a lo loco
- [~] Satélites: lealtad 0-100 por satélite con panel del señor (Ayuda / Tributo), espíritu vivo y rebeliones (2026-09-27); falta que se liberen
- [ ] Revisar capitales provisorias de los satélites (hoy: la región con más población)

## 3. Identidad de las ocho meganaciones

Diseño: `DISENO_OCHO_POTENCIAS.md` ("Las Ocho Potencias", aprobado 2026-09-23).
Cada una: 44-52 focos (status quo, revolución, dos economías excluyentes,
industria, ejército, aire/mar, árbol propio de su mecánica), ideas, decisiones,
eventos con ultimátum e IA con condiciones.

- [x] Infraestructura: duraciones en días, IA condicionada, prerrequisitos
  "cualquiera de", variables, banderas, `if`, eventos entre países, cambio de
  líder, ideas temporales, efectos reutilizables
- [~] **FCU** — el Directorio de las Cuatro (4 influencias, contratos, OPA de
  Rourke, ultimátums al EFE y a la HSN), árbol de 53 focos
- [~] **EFE** — árbol de 56 focos: Aurelio (Dinastía Verde) vs Anahí Quiroga
  (El Monte se Levanta, con crisis previa), integración de YYG/PTA en 3
  etapas, reforestación (120 días → núcleo), Autarquía vs Diplomacia del
  Agua, ultimátum a la FCU
- [~] **ASC** — árbol de 55 focos: Poder de Cómputo (capacidad + una prioridad,
  30 días para cambiarla, 3 niveles), Consejo Sorteado (3 rasgos al azar por año),
  PLAN-41, Plan Total vs Mercado de Cómputo, ultimátum a la APF
- [x] Íconos propios de los focos (pack de 96 del usuario, 12 por meganación)
- [~] **HSN** — árbol de 50 focos: 8 nodos reales del mapa (conteo mensual, 2/4/6/8,
  perder uno duele), Aldana (seguros, arbitraje, Bloqueo Legal a la FCU) vs Inés
  Tavake (sin peajes: Botín, patentes de corso), Puerto Libre vs Peaje
- [~] **NAS** — árbol de 54 focos con la tabla nueva de premios: Inti-Soma (granjas,
  ceremonias, templos-batería, sobrecarga y La Noche del Sol), Qhapaq Ñan (camino que
  crece por regiones vecinas e integra), los cuatro Suyus como misiones, La Corte del
  Sol vs El Tawantinsuyu Renace, ultimátum a la SHD
- [x] Pasada de ajuste de premios para EFE, FCU, ASC y HSN (tabla nueva): 118 focos, fábricas en
  regiones al azar (cada una con su slot; astilleros solo en la costa), bonos de investigación en vez
  de experiencia suelta, ideas flojas llevadas al 10-20%. Tabla "VALOR DE LOS ARBOLES" en balance.txt
- [x] El EFE arranca con la justificación lista contra los Caudillos del Amazonas (sin guerra declarada)
- [~] **APF** — árbol de 48 focos con la tabla nueva: Desarrollo + Integración por
  miembro (Amara: integra despacio, no pasa al desarrollo; Diallo: rápido, territorios
  difíciles), Plan de Desarrollo Regional región por región, industria acelerada,
  Aldea vs Corredor, ultimátum a la ASC
- [~] **SHD** — árbol de 51 focos con la tabla nueva: Producción, Orden y Pueblo con
  Armonía Perfecta/Parcial y Desborde, Lin (integración de Corea y la Estepa, ultimátum
  al NAS) vs Zhou (la Gran Crecida: el Pueblo hasta 130), Grandes Obras vs Precisión
- [~] **NRE** — árbol de 53 focos con la tabla nueva: tres legiones con prestigio,
  Auctoritas Militaris como moneda, Varro (Senado, Vías, Hispania y Dacia en tres etapas,
  Pax Romana, ultimátum al EFE) vs Arbogast (AVE IMPERATOR cambia el líder entre cuatro
  imperatores), Annona vs Tributo. Faltan retratos de Vasilescu y Aydın
- [x] Íconos propios: 96 focos (12 por potencia) con el pack del usuario
- [x] Tooltips: las recalculaciones (ASC, HSN, SHD, NRE) ya no muestran "quita X / pone X"; solo
  cambian una idea cuando cambia de nivel (efecto idea_tiers)
- [x] Investigación de arranque: nadie tiene nada, salvo 5 tecnologías de la especialidad de cada
  meganación (NRE infantería, APF apoyo, EFE blindados, SHD artillería, HSN naval + apoyo naval,
  NAS aviación, ASC ingeniería, FCU industria)
- [x] Investigación de 2100 v1 (spec/17_research.yaml): años +164 (1936 -> 2100) en tecnologías,
  equipo y pantalla de investigación; 192 tecnologías y 72 equipos con nombre de 2100
- [x] Sin unidades: 2 infanterías básicas en la capital por meganación (HSN: 1 + 3 destructores),
  1 por satélite, 1 milicia por país de la Anarquía; sin aviones. Todos con equipo de infantería y
  de apoyo investigado y en depósito
- [x] Industria en franja: meganaciones 95-115 IC, satélites hasta 35
- [x] Espíritus vanilla repartidos por región (Doctrina Monroe...) se sacan al día 1 y cada mes
- [ ] Rediseño completo de la investigación (ramas propias): más adelante
- [~] **IA v1** (spec/16_ai.yaml): planes de conquista por potencia (EFE→Amazonas, ASC→Eurasia,
  NRE→Emiratos y después Eurasia, SHD→Indostán, APF→Emiratos, NAS→Amazonas, FCU→el Canal,
  HSN→costas del Indostán), señores que protegen a sus satélites, rivales que se antagonizan;
  35 decisiones con criterio (SHD sube el caudal más bajo, FCU la influencia más baja, NRE calma
  a las legiones antes de 85, ASC asigna cómputo a la guerra si está en guerra) y peso por rama
  (industria ×2, mecánica propia ×1,5-2, aire de las potencias sin vocación ×0,7). Falta: plantillas
  de división y producción por potencia
- [x] Mecánicas v2 (2026-09-26): pulso mensual y un riesgo en cada potencia (saturación de las cubas,
  escándalo, calor de la red, presión de las potencias, templos que consumen, deriva de los caudales,
  tensión regional, legiones ociosas), crisis por evento y explicación de la mecánica al arrancar
- [x] 6 focos nuevos por meganación (rama ligada a su mecánica v2) y +50% de duración en todos
- [~] Interacciones entre potencias: 4 hechas (Bioacero en venta, Árbitro de los Mares, Cómputo para
  la Tierra, Puertos para el Directorio) de 20-30

## 4. El EFE, a fondo

- [x] Árbol de 31 focos, 4 eventos, BioSteel como minijuego, arte propio
- [ ] EPI (Q022): segundo sistema del EFE, falta definir qué es
- [ ] Más eventos: reacciones de la FCU, la NAS y los satélites a cada ruta
- [ ] Decisiones de los satélites (PTA, YYG): integración, rebelión, recursos
- [ ] Equipamiento de BioSteel: una variante de tanque "Armadura Viviente"

## 5. Satélites y Anarquía como gameplay

- [~] Panel de lealtad de los satélites (del lado del señor); falta el lado del satélite si se lo juega
- [~] Señores de la guerra: saqueos a los vecinos, un Caudillo Supremo que unifica, tregua de caudillos en guerra (2026-09-27)
- [ ] Liberar países de la Anarquía: qué pasa con una región conquistada
- [~] Mecánicas v3 (2026-09-27): espíritus vivos con el bonus del momento, FCU y SHD de suma fija, APF más lenta y con tensión real, paneles que explican qué ganás, IA que corrige en vez de subir todo
- [~] Conquistas con dilema: cada meganación, al tomar su región clave, elige proteger o explotar (evento + decisiones que se abren); más un evento de hito por mecánica

## 6. Diplomacia avanzada

- [ ] Facciones por bloque ideológico: cuándo se forman y quién entra
- [ ] Eventos de tensión mundial ligados al Gran Desarme
- [ ] Mecánica de acuerdos entre meganaciones (agua, rutas, cómputo)
- [ ] Guerras frías: espionaje y operaciones (si aplica con los DLC)

## 7. Presentación y arte

- [x] Bandera, retratos e íconos del EFE
- [x] Retratos de los líderes de las 7 meganaciones (arte del usuario)
- [~] Banderas de las 8 meganaciones (arte del usuario)
- [x] Banderas de los 16 satélites y los 5 señores de la guerra (arte del usuario)
- [ ] Retratos de los satélites y de Irina Vasilescu y Kerem Aydın (NRE, hoy provisorios)
- [x] Íconos de foco propios: el pack de 96, conectado
- [ ] Íconos de los espíritus nacionales propios (hoy muchos salen con "?")
- [x] Circuito de arte con ChatGPT (tools/arte): pedidos ASSET_REQUEST en arte/pedidos/, importador
  que convierte y ubica por id; focos, espíritus, retratos y eventos se conectan solos por nombre
- [x] Espíritus sin dibujo: ícono genérico del juego según su efecto (se acabaron los "?")
- [ ] Imágenes de eventos propias (pedidas en arte/pedidos/4_eventos_*)
- [ ] Íconos de los paneles de decisiones
- [ ] Pantallas de carga

## 8. Texto y localización

- [ ] Revisar todo el texto en español e inglés (tono, consistencia de nombres)
- [ ] Nombres de 2100 para las regiones de las otras meganaciones
- [ ] Nombres de ciudades (puntos de victoria) de las capitales
- [ ] Listas de nombres de divisiones y barcos por facción

## 9. Flavor

- [ ] Eventos de noticias del mundo de 2100 (el Invierno de Ceniza, las cubas, la Alta Mar)
- [ ] Textos de ayuda con lore en ideologías, ideas y decisiones
- [ ] Música del menú o de facción (si se consigue)
- [ ] Easter eggs del borrador histórico (la línea 2060/2080, Q020)
