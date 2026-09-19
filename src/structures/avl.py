"""Manually implemented AVL tree.

Document (section 8): insercion, busqueda, eliminacion implemented
manually, with the four rebalancing cases (LL, RR, LR, RL).

Public API: insertar(clave, evento_ref) / eliminar(clave) (Fase 9).
Callers must compute ClaveEvento beforehand — this class has no idea
what "priority" or "populated zone" mean.
"""

from __future__ import annotations

from typing import Any, Optional

from .clave_evento import ClaveEvento
from .comparador import comparar_claves
from .excepciones import ClaveDuplicadaError
from .nodo_avl import NodoAVL, actualizar_altura, factor_balance


class AVL:
    def __init__(self) -> None:
        self.raiz: Optional[NodoAVL] = None

    def insertar(self, clave: ClaveEvento, evento_ref: Any) -> None:
        self.raiz = _insertar_recursivo(self.raiz, clave, evento_ref)


def _insertar_recursivo(
    nodo: Optional[NodoAVL], clave: ClaveEvento, evento_ref: Any
) -> NodoAVL:
    if nodo is None:
        return NodoAVL(clave, evento_ref)

    comparacion = comparar_claves(clave, nodo.clave)
    if comparacion < 0:
        nodo.izquierdo = _insertar_recursivo(nodo.izquierdo, clave, evento_ref)
    elif comparacion > 0:
        nodo.derecho = _insertar_recursivo(nodo.derecho, clave, evento_ref)
    else:
        raise ClaveDuplicadaError(
            f"la clave {clave} ya existe en el arbol (esto no deberia "
            "ocurrir si la unicidad de ID se respeta en services/)"
        )

    actualizar_altura(nodo)
    return _rebalancear(nodo, clave)


def _rebalancear(nodo: NodoAVL, clave_insertada: ClaveEvento) -> NodoAVL:
    from .rotaciones import rotar_derecha, rotar_izquierda  # avoid circular import

    fb = factor_balance(nodo)

    if fb > 1:
        assert nodo.izquierdo is not None
        if comparar_claves(clave_insertada, nodo.izquierdo.clave) < 0:
            return rotar_derecha(nodo)  # LL
        nodo.izquierdo = rotar_izquierda(nodo.izquierdo)  # LR
        return rotar_derecha(nodo)

    if fb < -1:
        assert nodo.derecho is not None
        if comparar_claves(clave_insertada, nodo.derecho.clave) > 0:
            return rotar_izquierda(nodo)  # RR
        nodo.derecho = rotar_derecha(nodo.derecho)  # RL
        return rotar_izquierda(nodo)

    return nodo