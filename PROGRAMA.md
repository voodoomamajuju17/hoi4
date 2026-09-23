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
- [~] Fondo del menú principal: detección por las pantallas del menú (`frontend*.gui`); el reporte lista lo que reemplaza
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
- [ ] Ajustar con los números reales de `balance.txt` (objetivos de IC, pisos, tropas)
- [ ] Decidir si la FCU necesita una penalización propia (hoy es la más fuerte en la práctica)
- [ ] IA: estrategias por meganación (`common/ai_strategy`): a quién atacar, a quién aliarse, qué construir
- [ ] IA de la Anarquía: que se defienda sin atacar a lo loco
- [ ] Satélites: nivel de autonomía por bloque y cómo se liberan o anexan
- [ ] Revisar capitales provisorias de los satélites (hoy: la región con más población)

## 3. Identidad de las otras siete meganaciones

Cada una necesita lo mismo que ya tiene el EFE. Orden sugerido: de la
mecánica mejor definida en el documento a la menos definida.

Para cada una:
- [ ] Ideas nacionales de arranque (2 a 4)
- [ ] Mecánica propia como panel de decisiones o contador (como el BioSteel)
- [ ] Árbol de focos: 2 rutas políticas, 1 económica, 1 militar, con su enemigo natural
- [ ] 3 a 5 eventos atados al árbol y a la mecánica
- [ ] Rasgos de líder y un mariscal propio

Por facción:
- [ ] **ASC — Poder de Cómputo** (Q023): datacenters dan capacidad, los ejércitos autónomos la consumen, la sobrecarga penaliza
- [ ] **FCU — Equilibrio civil-militar** (Q024): barra de dos polos entre las cuatro corporaciones; militarizarse le cuesta a la economía
- [ ] **NRE — Legiones y Oficiales** (Q028): prestigio de legiones, aclamación del Imperator
- [ ] **HSN — Nodos comerciales / TFI** (Q025): control de estrechos, peajes, flota
- [ ] **SHD — Armonía** (Q026): medidor social que el Directorio corrige
- [ ] **APF — Integración regional** (Q027): consejos que se suman a la federación
- [ ] **NAS — Inti-Soma** (Q009): el Sol, el culto y la altura

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

- [x] Bandera, retratos e íconos del EFE; fondo del menú principal
- [ ] Banderas de las 28 facciones restantes (hoy son franjas provisorias)
- [ ] Retratos de líderes de las 7 meganaciones y los satélites
- [ ] Íconos de foco propios para los árboles nuevos
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
