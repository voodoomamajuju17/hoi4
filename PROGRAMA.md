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
- [ ] Fondo del menú principal: en 1.19 hay un selector ("Cambiar fondo"); el reporte trae un diagnóstico para encontrar dónde se define
- [ ] Rendimiento: medir días por segundo con 29 países + guerras activas

## 2. Mundo y balance global

- [x] Reparto del mundo: 8 meganaciones, 16 satélites, la Anarquía
- [~] La Anarquía en 5 señores de la guerra unidos en una facción
- [~] Recursos invariables: mínimos por transferencia, total mundial = vanilla
- [~] Industrialización de EFE, NAS y APF; penalización de la ASC
- [~] Leyes de reclutamiento según población
- [~] Ejército inicial (piso 20 para meganaciones), tecnologías por nivel, depósitos
- [~] Armada y aviación heredadas de 1936 según la base, recortadas al 10% (flota solo HSN, FCU, NRE y ASC)
- [~] Mundo vivo: reclamos, rivalidades, tensión mundial, 2 guerras al arranque
- [~] 9 facciones: cada meganación con sus 2 satélites, más la Anarquía
- [~] Congo: dueños dentro de bloques condicionales borrados + red de seguridad al arrancar
- [ ] Ajustar con los números reales de `balance.txt` (objetivos de IC, pisos, tropas)
- [ ] Decidir si la FCU necesita una penalización propia (hoy es la más fuerte en la práctica)
- [ ] IA: estrategias por meganación (`common/ai_strategy`): a quién atacar, a quién aliarse, qué construir
- [ ] IA de la Anarquía: que se defienda sin atacar a lo loco
- [ ] Satélites: nivel de autonomía por bloque y cómo se liberan o anexan
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
- [ ] Íconos propios de los focos (pack de 96 del usuario, 12 por meganación): cargar cuando se pida
- [~] **HSN** — árbol de 50 focos: 8 nodos reales del mapa (conteo mensual, 2/4/6/8,
  perder uno duele), Aldana (seguros, arbitraje, Bloqueo Legal a la FCU) vs Inés
  Tavake (sin peajes: Botín, patentes de corso), Puerto Libre vs Peaje
- [~] **NAS** — árbol de 54 focos con la tabla nueva de premios: Inti-Soma (granjas,
  ceremonias, templos-batería, sobrecarga y La Noche del Sol), Qhapaq Ñan (camino que
  crece por regiones vecinas e integra), los cuatro Suyus como misiones, La Corte del
  Sol vs El Tawantinsuyu Renace, ultimátum a la SHD
- [ ] Pasada de ajuste de premios para EFE, FCU, ASC y HSN (tabla nueva)
- [ ] **APF** — Desarrollo + Integración, Amara vs Diallo
- [ ] **SHD** — los tres caudales, la Gran Crecida
- [ ] **NRE** — prestigio de legiones, Auctoritas Militaris, AVE IMPERATOR
- [ ] Interacciones entre potencias (20-30 eventos chicos)

## 4. El EFE, a fondo

- [x] Árbol de 31 focos, 4 eventos, BioSteel como minijuego, arte propio
- [ ] EPI (Q022): segundo sistema del EFE, falta definir qué es
- [ ] Más eventos: reacciones de la FCU, la NAS y los satélites a cada ruta
- [ ] Decisiones de los satélites (PTA, YYG): integración, rebelión, recursos
- [ ] Equipamiento de BioSteel: una variante de tanque "Armadura Viviente"

## 5. Satélites y Anarquía como gameplay

- [ ] Árbol corto o panel de decisiones para cada satélite (independencia vs lealtad)
- [ ] Señores de la guerra: eventos de raid, alianzas temporales, reunificación
- [ ] Liberar países de la Anarquía: qué pasa con una región conquistada
- [ ] Decisiones de "pacificación" para las meganaciones que conquistan territorio anárquico

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
- [ ] Retratos de los satélites, Marcus Rourke y Anahí Quiroga
- [ ] Íconos de foco propios: el pack de 96 ya está; falta conectarlo
- [ ] Imágenes de eventos propias
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
