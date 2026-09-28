"""Manually implemented AVL tree (document, sections 5, 8 and 10).

Public API: insertar(clave, evento_ref), eliminar(clave), buscar(clave).
Callers build the ClaveEvento beforehand: this class knows nothing about
priorities or populated zones.

Every rotation applied is recorded in `contadores` (cumulative) and in
`rotaciones_recientes` (only the last public operation).
"""

from __future__ import annotations

from typing import Any, Optional

from .busqueda import buscar_en_arbol
from .clave_evento import ClaveEvento
from .comparador import comparar_claves
from .excepciones import ClaveDuplicadaError, ClaveNoEncontradaError
from .nodo_avl import NodoAVL, actualizar_altura, factor_balance
from .registro_rotaciones import CasoBalanceo, ContadoresRotaciones, RotacionAplicada
from .resultado_busqueda import ResultadoBusqueda
from .rotaciones import rotar_derecha, rotar_izquierda


def _caso_por_insercion(
    nodo: NodoAVL, clave_insertada: ClaveEvento
) -> Optional[CasoBalanceo]:
    """Case selection right after an insertion: compare the inserted key
    against the heavy child to tell a straight line (LL/RR) from a zigzag."""
    fb = factor_balance(nodo)
    if fb > 1:
        if comparar_claves(clave_insertada, nodo.izquierdo.clave) < 0:
            return CasoBalanceo.LL
        return CasoBalanceo.LR
    if fb < -1:
        if comparar_claves(clave_insertada, nodo.derecho.clave) > 0:
            return CasoBalanceo.RR
        return CasoBalanceo.RL
    return None


def _caso_segun_hijo(nodo: NodoAVL) -> Optional[CasoBalanceo]:
    """Case selection from the heavy child's balance factor. Needs no
    'inserted key', so it also serves deletions and the global recovery."""
    fb = factor_balance(nodo)
    if fb > 1:
        if factor_balance(nodo.izquierdo) >= 0:
            return CasoBalanceo.LL
        return CasoBalanceo.LR
    if fb < -1:
        if factor_balance(nodo.derecho) <= 0:
            return CasoBalanceo.RR
        return CasoBalanceo.RL
    return None


class AVL:
    def __init__(self) -> None:
        self._modo_estres: bool = False
        self.raiz: Optional[NodoAVL] = None
        self.contadores: ContadoresRotaciones = ContadoresRotaciones()
        self.rotaciones_recientes: list[RotacionAplicada] = []

    # ---------- public API ----------

    @property
    def modo_estres(self) -> bool:
        return self._modo_estres

    def activar_modo_estres(self) -> None:
        """Defers rotations from now on. There is deliberately no way back
        here: returning to normal mode requires the global recovery plus a
        successful audit (document, section 8)."""
        self._modo_estres = True

    def buscar(self, clave: ClaveEvento) -> ResultadoBusqueda:
        return buscar_en_arbol(self.raiz, clave)

    def insertar(self, clave: ClaveEvento, evento_ref: Any) -> None:
        self.rotaciones_recientes = []
        self.raiz = self._insertar(self.raiz, clave, evento_ref)

    def eliminar(self, clave: ClaveEvento) -> None:
        self.rotaciones_recientes = []
        self.raiz = self._eliminar(self.raiz, clave)

    # ---------- insertion ----------

    def _insertar(
        self, nodo: Optional[NodoAVL], clave: ClaveEvento, evento_ref: Any
    ) -> NodoAVL:
        if nodo is None:
            return NodoAVL(clave, evento_ref)

        comparacion = comparar_claves(clave, nodo.clave)
        if comparacion < 0:
            nodo.izquierdo = self._insertar(nodo.izquierdo, clave, evento_ref)
        elif comparacion > 0:
            nodo.derecho = self._insertar(nodo.derecho, clave, evento_ref)
        else:
            raise ClaveDuplicadaError(
                f"la clave {clave} ya existe en el arbol (esto no deberia "
                "ocurrir si la unicidad de ID se respeta en services/)"
            )

        actualizar_altura(nodo)
        if self._modo_estres:
            return nodo  # stress mode: keep BST order and heights, skip rotations
        caso = _caso_por_insercion(nodo, clave)
        return self._aplicar_caso(nodo, caso) if caso is not None else nodo

    # ---------- deletion ----------

    def _eliminar(
        self, nodo: Optional[NodoAVL], clave: ClaveEvento
    ) -> Optional[NodoAVL]:
        if nodo is None:
            raise ClaveNoEncontradaError(f"la clave {clave} no existe en el arbol")

        comparacion = comparar_claves(clave, nodo.clave)
        if comparacion < 0:
            nodo.izquierdo = self._eliminar(nodo.izquierdo, clave)
        elif comparacion > 0:
            nodo.derecho = self._eliminar(nodo.derecho, clave)
        else:
            if nodo.izquierdo is None:
                return nodo.derecho
            if nodo.derecho is None:
                return nodo.izquierdo
            # two children: take the inorder successor's content, then
            # remove the successor from its original position
            sucesor = _minimo(nodo.derecho)
            nodo.clave = sucesor.clave
            nodo.evento_ref = sucesor.evento_ref
            nodo.derecho = self._eliminar(nodo.derecho, sucesor.clave)

        actualizar_altura(nodo)
        if self._modo_estres:
            return nodo
        caso = _caso_segun_hijo(nodo)
        return self._aplicar_caso(nodo, caso) if caso is not None else nodo

    # ---------- rebalancing ----------

    def _aplicar_caso(self, nodo: NodoAVL, caso: CasoBalanceo) -> NodoAVL:
        """Performs the rotation(s) of `caso` at `nodo`, records them and
        returns the new root of that subtree."""
        clave_nodo = nodo.clave
        if caso is CasoBalanceo.LL:
            nueva_raiz = rotar_derecha(nodo)
        elif caso is CasoBalanceo.RR:
            nueva_raiz = rotar_izquierda(nodo)
        elif caso is CasoBalanceo.LR:
            nodo.izquierdo = rotar_izquierda(nodo.izquierdo)
            nueva_raiz = rotar_derecha(nodo)
        else:  # RL
            nodo.derecho = rotar_derecha(nodo.derecho)
            nueva_raiz = rotar_izquierda(nodo)

        self.contadores.registrar(caso)
        self.rotaciones_recientes.append(RotacionAplicada(caso, clave_nodo))
        return nueva_raiz


def _minimo(nodo: NodoAVL) -> NodoAVL:
    """Left-most node of a subtree (source of the inorder successor)."""
    while nodo.izquierdo is not None:
        nodo = nodo.izquierdo
    return nodo