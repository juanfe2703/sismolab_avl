"""Simple AVL rotations.

Document (section 8): rotacion izquierda, rotacion derecha, actualizacion
de alturas. These functions are pure structural operations: they do not
decide WHEN to rotate (that belongs to insertion logic, next phase).
"""

from __future__ import annotations

from .nodo_avl import NodoAVL, altura, actualizar_altura


def rotar_derecha(y: NodoAVL) -> NodoAVL:
    x = y.izquierdo
    assert x is not None, "rotar_derecha requiere un hijo izquierdo"

    t2 = x.derecho
    x.derecho = y
    y.izquierdo = t2

    actualizar_altura(y)
    actualizar_altura(x)
    return x


def rotar_izquierda(x: NodoAVL) -> NodoAVL:
    y = x.derecho
    assert y is not None, "rotar_izquierda requiere un hijo derecho"

    t2 = y.izquierdo
    y.izquierdo = x
    x.derecho = t2

    actualizar_altura(x)
    actualizar_altura(y)
    return y