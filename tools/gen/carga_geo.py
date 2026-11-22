"""Geometría de los marcos de la pantalla de carga (2026-11-22).

Pedido: "Esos marcos quiero cambiarlos completamente, podés hacer los pedidos que hagan falta" (la barra de
arriba con "Cargando bases de datos" y la caja de abajo con la frase). La comparten el armado
(tools/gen/emitters/marcos_carga.py: dónde va cada texto) y el arte (tools/arte/arte.py: el tamaño de
cada pieza y el pedido en arte/pedidos_marcos_pantalla_carga.txt). Sin PIL.

Coordenadas dentro de cada imagen (x, y, ancho, alto). Las dos ventanas del juego están centradas: la de
arriba (CENTER_UP) y la de abajo (CENTER_DOWN), así que el marco va en x = -ancho/2.
"""

from __future__ import annotations

# la barra de arriba: placa del título + ranura de la barra de progreso
ESTADO = (1400, 120)
ESTADO_TITULO = (300, 12, 800, 44)      # el juego escribe "Cargando ..." centrado acá
ESTADO_RANURA = (233, 70, 934, 35)      # la barra de progreso va encima, exacta

# la caja de la frase de abajo
FRASE = (1400, 190)
FRASE_TEXTO = (150, 28, 1100, 134)      # la frase y su firma, centradas
FRASE_MARGEN_ABAJO = 12                 # cuánto queda entre la caja y el borde de la pantalla

# la barra de progreso (las dos imágenes del mismo tamaño que la ranura)
BARRA = (934, 35)

PIEZAS = {
    "carga_marco_estado": {"size": ESTADO, "transparent": True},
    "carga_marco_frase": {"size": FRASE, "transparent": True},
    "carga_barra_llena": {"size": BARRA, "transparent": False},
    "carga_barra_vacia": {"size": BARRA, "transparent": False},
}
