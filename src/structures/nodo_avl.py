"""AVL node.

Document (section 14): height of an empty tree is -1, height of a leaf
is 0. Balance factor = height(left) - height(right).

A node does not know about rotations or insertion logic — that lives
in the AVL class (next phases). This module only defines the data
shape and the height helper both AVL and BST-adjacent code will share.
"""

from __future__ import annotations

from typing import Any, Optional

from .clave_evento import ClaveEvento


class NodoAVL:
    def __init__(self, clave: ClaveEvento, evento_ref: Any) -> None:
        self.clave: ClaveEvento = clave
        self.evento_ref: Any = evento_ref
        self.izquierdo: Optional["NodoAVL"] = None
        self.derecho: Optional["NodoAVL"] = None
        self.altura: int = 0  # a newly created node is always a leaf


def altura(nodo: Optional[NodoAVL]) -> int:
    """Height of `nodo`, treating an empty tree (None) as -1."""
    return nodo.altura if nodo is not None else -1


def factor_balance(nodo: Optional[NodoAVL]) -> int:
    """Balance factor = height(left) - height(right). 0 for an empty tree."""
    if nodo is None:
        return 0
    return altura(nodo.izquierdo) - altura(nodo.derecho)


def actualizar_altura(nodo: NodoAVL) -> None:
    """Recomputes `nodo.altura` from its current children's heights.

    Shared by rotations and insertion/deletion — every operation that
    reshapes the tree calls this on every node it touches.
    """
    nodo.altura = 1 + max(altura(nodo.izquierdo), altura(nodo.derecho))