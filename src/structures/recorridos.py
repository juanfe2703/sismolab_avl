"""Traversals over an AVL/BST-shaped tree of NodoAVL.

Document (section 14): inorden, preorden, postorden, por niveles.
Document (section 5): inorder traversal must yield ascending keys —
these functions are what we use in tests to verify that invariant.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from .clave_evento import ClaveEvento
from .nodo_avl import NodoAVL


def recorrido_inorden(raiz: Optional[NodoAVL]) -> list[ClaveEvento]:
    if raiz is None:
        return []
    return (
        recorrido_inorden(raiz.izquierdo)
        + [raiz.clave]
        + recorrido_inorden(raiz.derecho)
    )


def recorrido_preorden(raiz: Optional[NodoAVL]) -> list[ClaveEvento]:
    if raiz is None:
        return []
    return (
        [raiz.clave]
        + recorrido_preorden(raiz.izquierdo)
        + recorrido_preorden(raiz.derecho)
    )


def recorrido_postorden(raiz: Optional[NodoAVL]) -> list[ClaveEvento]:
    if raiz is None:
        return []
    return (
        recorrido_postorden(raiz.izquierdo)
        + recorrido_postorden(raiz.derecho)
        + [raiz.clave]
    )


def recorrido_por_niveles(raiz: Optional[NodoAVL]) -> list[ClaveEvento]:
    """Breadth-first traversal. Uses a deque as an internal BFS worklist —
    unrelated to the pending-reports FIFO queue required elsewhere."""
    if raiz is None:
        return []

    resultado: list[ClaveEvento] = []
    pendientes: deque[NodoAVL] = deque([raiz])
    while pendientes:
        nodo = pendientes.popleft()
        resultado.append(nodo.clave)
        if nodo.izquierdo is not None:
            pendientes.append(nodo.izquierdo)
        if nodo.derecho is not None:
            pendientes.append(nodo.derecho)
    return resultado