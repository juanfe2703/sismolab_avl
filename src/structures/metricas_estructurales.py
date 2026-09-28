"""Basic structural metrics of a tree (document, section 14):
node count, height, leaf count.
"""

from __future__ import annotations

from typing import Optional

from .nodo_avl import NodoAVL, altura

from .nodo_bst import NodoBinario

def cantidad_nodos(raiz: Optional[NodoBinario]) -> int:
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


def altura_recalculada(raiz) -> int:
    """Real height computed by walking the tree level by level.

    Ignores any stored `.altura` field, so it works for the BST (which
    stores none) and lets the audit (Fase 14) compare stored vs real height.
    Iterative on purpose: a degenerate BST can be n levels deep.
    """
    if raiz is None:
        return -1
    altura_actual = -1
    nivel = [raiz]
    while nivel:
        altura_actual += 1
        siguiente = []
        for nodo in nivel:
            if nodo.izquierdo is not None:
                siguiente.append(nodo.izquierdo)
            if nodo.derecho is not None:
                siguiente.append(nodo.derecho)
        nivel = siguiente
    return altura_actual