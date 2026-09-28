"""Plain BST node: no height, no balance factor (the BST never rebalances)."""

from __future__ import annotations

from typing import Any, Optional, Union

from .clave_evento import ClaveEvento
from .nodo_avl import NodoAVL


class NodoBST:
    def __init__(self, clave: ClaveEvento, evento_ref: Any) -> None:
        self.clave: ClaveEvento = clave
        self.evento_ref: Any = evento_ref
        self.izquierdo: Optional["NodoBST"] = None
        self.derecho: Optional["NodoBST"] = None


# Traversals and structural metrics work on either kind of node.
NodoBinario = Union[NodoAVL, NodoBST]