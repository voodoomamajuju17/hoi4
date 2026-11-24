# El mundo 2100: monumentos, ciudades y edificios del mapa (2026-11-24)

Lo que llega de `arte/pedidos_fijos/60_modelos_3d_mundo_2100.txt` y todavía NO entra al juego. Cada carpeta tiene el
`.blend`, la vista y lo que va al juego (`gfx/entities/<id>.asset` y `.gfx`, la malla y sus tres `.dds`). Mallas fijas.

- `monumentos/`: los 10 de la parte E (66 a 75), uno por capital de las ocho meganaciones, Japón y Albión.
- `ciudades/`: las de la parte D (45 a 65) que van llegando.

Por qué no entran todavía: un monumento es un edificio especial del juego (landmark) que se define en
`common/buildings/` y se ubica en `map/buildings.txt`; las ciudades reemplazan las del juego por región gráfica. Esos
formatos no están verificados contra los archivos del juego, y un archivo de gráficos mal armado hace caer el juego al
arrancar (pasó con la pantalla de carga, 2026-11-22). El armado no toca esta carpeta.

Los trenes (parte C) sí entran: son unidades y van en `assets/modelos/` como los tanques y los barcos.
