"""Simple AVL rotations.

Document (section 8): rotacion izquierda, rotacion derecha, actualizacion
de alturas. These functions are pure structural operations: they do not
decide WHEN to rotate (that belongs to insertion logic, next phase).
"""

from __future__ import annotations

from .nodo_avl import NodoAVL, altura


def _actualizar_altura(nodo: NodoAVL) -> None:
    """Recomputes `nodo.altura` from its current children's heights."""
    nodo.altura = 1 + max(altura(nodo.izquierdo), altura(nodo.derecho))


def rotar_derecha(y: NodoAVL) -> NodoAVL:
    """Right rotation. Assumes y.izquierdo is not None.

    Returns the new root of this subtree (previously y.izquierdo).
    """
    x = y.izquierdo
    assert x is not None, "rotar_derecha requiere un hijo izquierdo"

    t2 = x.derecho

    x.derecho = y
    y.izquierdo = t2

    # y quedo mas abajo: se actualiza primero.
    _actualizar_altura(y)
    _actualizar_altura(x)

    return x


def rotar_izquierda(x: NodoAVL) -> NodoAVL:
    """Left rotation. Assumes x.derecho is not None.

    Returns the new root of this subtree (previously x.derecho).
    """
    y = x.derecho
    assert y is not None, "rotar_izquierda requiere un hijo derecho"

    t2 = y.izquierdo

    y.izquierdo = x
    x.derecho = t2

    # x quedo mas abajo: se actualiza primero.
    _actualizar_altura(x)
    _actualizar_altura(y)

    return y