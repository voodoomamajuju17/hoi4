# El mundo 2100: edificios del mapa, ciudades y monumentos (2026-11-24: llegaron todos)

Lo que llega de `arte/pedidos_fijos/60_modelos_3d_mundo_2100.txt` y todavía NO entra al juego. Cada carpeta tiene el
`.blend`, la vista y lo que va al juego (`gfx/entities/<id>.asset` y `.gfx`, la malla y sus tres `.dds`). Mallas fijas.

- `edificios/`: los 20 de la parte B (6 a 25): fábricas civil y militar, astillero, puerto, base aérea, fuerte, fuerte
  costero, antiaérea, radar, sitio de cohetes, reactor de fusión, refinería, silo, centro de suministro, puerto flotante,
  vía maglev (con su textura plana, por si el juego dibuja las vías como textura) y las 4 instalaciones de proyectos
  especiales. Algunos traen animación (grúas, radar, antiaérea).
- `ciudades/`: las 21 de la parte D (45 a 65): 7 regiones gráficas x pueblo, ciudad y capital.
- `monumentos/`: los 10 de la parte E (66 a 75), uno por capital de las ocho meganaciones, Japón y Albión.
- `trenes/`: el tren de carga (26): el juego no muestra trenes de suministro como unidades.
Las vistas van achicadas a 800 px.

Por qué no entran todavía: un monumento es un edificio especial del juego (landmark) que se define en
`common/buildings/` y se ubica en `map/buildings.txt`; las ciudades reemplazan las del juego por región gráfica. Esos
formatos no están verificados contra los archivos del juego, y un archivo de gráficos mal armado hace caer el juego al
arrancar (pasó con la pantalla de carga, 2026-11-22). El armado no toca esta carpeta.

Los trenes blindados y los cañones sobre rieles (parte C, 27 a 44) sí entran: son unidades y van en `assets/modelos/` como los tanques y los barcos.
