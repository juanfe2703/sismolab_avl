"""Unbalanced BST used only to compare against the AVL (document, section 11).

Same comparator, same insertion rules, NO rotations. All operations are
iterative: ascending insertion degenerates this tree into a chain of n
nodes, and a recursive version would exceed Python's recursion limit.
"""

from __future__ import annotations

from typing import Any, Optional

from .busqueda import buscar_en_arbol
from .clave_evento import ClaveEvento
from .comparador import comparar_claves
from .excepciones import ClaveDuplicadaError, ClaveNoEncontradaError
from .nodo_bst import NodoBST
from .resultado_busqueda import ResultadoBusqueda


class BST:
    def __init__(self) -> None:
        self.raiz: Optional[NodoBST] = None

    def buscar(self, clave: ClaveEvento) -> ResultadoBusqueda:
        return buscar_en_arbol(self.raiz, clave)

    def insertar(self, clave: ClaveEvento, evento_ref: Any) -> None:
        nuevo = NodoBST(clave, evento_ref)
        if self.raiz is None:
            self.raiz = nuevo
            return

        actual = self.raiz
        while True:
            comparacion = comparar_claves(clave, actual.clave)
            if comparacion == 0:
                raise ClaveDuplicadaError(f"la clave {clave} ya existe en el BST")
            if comparacion < 0:
                if actual.izquierdo is None:
                    actual.izquierdo = nuevo
                    return
                actual = actual.izquierdo
            else:
                if actual.derecho is None:
                    actual.derecho = nuevo
                    return
                actual = actual.derecho

    def eliminar(self, clave: ClaveEvento) -> None:
        # 1. Locate the node, remembering its parent.
        padre: Optional[NodoBST] = None
        actual = self.raiz
        while actual is not None:
            comparacion = comparar_claves(clave, actual.clave)
            if comparacion == 0:
                break
            padre = actual
            actual = actual.izquierdo if comparacion < 0 else actual.derecho
        if actual is None:
            raise ClaveNoEncontradaError(f"la clave {clave} no existe en el BST")

        # 2. Two children: copy the inorder successor's content into this
        #    node, then physically remove the successor (at most one child).
        if actual.izquierdo is not None and actual.derecho is not None:
            padre_sucesor = actual
            sucesor = actual.derecho
            while sucesor.izquierdo is not None:
                padre_sucesor = sucesor
                sucesor = sucesor.izquierdo
            actual.clave = sucesor.clave
            actual.evento_ref = sucesor.evento_ref
            padre, actual = padre_sucesor, sucesor

        # 3. `actual` now has at most one child: splice it out.
        hijo = actual.izquierdo if actual.izquierdo is not None else actual.derecho
        if padre is None:
            self.raiz = hijo
        elif padre.izquierdo is actual:
            padre.izquierdo = hijo
        else:
            padre.derecho = hijo