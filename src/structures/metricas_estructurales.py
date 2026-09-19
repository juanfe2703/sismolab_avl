"""Basic structural metrics of a tree (document, section 14):
node count, height, leaf count.
"""

from __future__ import annotations

from typing import Optional

from .nodo_avl import NodoAVL, altura


def cantidad_nodos(raiz: Optional[NodoAVL]) -> int:
    if raiz is None:
        return 0
    return 1 + cantidad_nodos(raiz.izquierdo) + cantidad_nodos(raiz.derecho)


def altura_arbol(raiz: Optional[NodoAVL]) -> int:
    """Height of the whole tree; -1 for an empty tree (section 14 convention)."""
    return altura(raiz)


def cantidad_hojas(raiz: Optional[NodoAVL]) -> int:
    if raiz is None:
        return 0
    if raiz.izquierdo is None and raiz.derecho is None:
        return 1
    return cantidad_hojas(raiz.izquierdo) + cantidad_hojas(raiz.derecho)