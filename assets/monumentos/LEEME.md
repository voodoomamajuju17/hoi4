# Monumentos de las capitales (2026-11-24)

Llegaron los 10 de la parte E de `arte/pedidos_fijos/60_modelos_3d_mundo_2100.txt` (66 a 75): las ocho meganaciones,
Japón y Albión. Cada carpeta tiene el `.blend`, la vista y lo que va al juego (`gfx/entities/<id>.asset` con la entidad
`<TAG>_landmark_entity`, `gfx/entities/<id>.gfx` con la malla, y la malla y sus tres `.dds` en
`gfx/models/landmarks/<id>/`). Mallas fijas, sin huesos.

Todavía NO entran al juego: un monumento es un edificio especial del juego (landmark) que se define en
`common/buildings/` y se ubica en el mapa (`map/buildings.txt`), y ese formato no está verificado contra los archivos
del juego. Hasta que se conecten, el armado no los toca (no están en `assets/modelos/`).
