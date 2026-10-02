"""ArbolDemostracion: a PLACEHOLDER implementing ArbolAVLProtocol as a
plain (unbalanced) BST.

This is NOT the project's AVL deliverable. It exists only so this GUI
can be launched and clicked through today, before `structures`
delivers the real, hand-written AVL with real rotations. It satisfies
the full contract in `src/services/contratos.py` - insert/delete/search,
the id index, clonar/restaurar_desde for undo, obtener_raiz/
instalar_topologia for persistence - so every service built in this
project already works against it unmodified.

Swapping it out later is a ONE-LINE change in `app.py`'s composition
root (the `fabrica_arbol_avl` argument), because every service in this
project was written against the `ArbolAVLProtocol` Protocol, never
against this class directly - which was the whole point of using
Protocols from the start (see `src/services/contratos.py`'s own
docstring).

`activar_modo_estres` / `recuperar_balance` only toggle a flag here;
this placeholder never actually rotates, so "recovering balance" is a
no-op beyond clearing the flag. Real rotation counting, rotation
mechanics (LL/RR/LR/RL) and genuine stress-mode deferral belong to the
real AVL, not here.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Iterator, Optional

from src.model import Evento
from src.structures import ClaveEvento, NodoAVL, altura, comparar_claves, factor_balance


class ArbolDemostracion:
    def __init__(self) -> None:
        self._raiz: Optional[NodoAVL] = None
        self._indice_por_id: dict[int, NodoAVL] = {}
        self.modo_estres: bool = False

    def _reindexar(self) -> None:
        self._indice_por_id = {}

        def visitar(nodo: Optional[NodoAVL]) -> None:
            if nodo is None:
                return
            self._indice_por_id[nodo.clave.identificador] = nodo
            visitar(nodo.izquierdo)
            visitar(nodo.derecho)

        visitar(self._raiz)

    def _recalcular_alturas(self, nodo: Optional[NodoAVL]) -> int:
        if nodo is None:
            return -1
        izq = self._recalcular_alturas(nodo.izquierdo)
        der = self._recalcular_alturas(nodo.derecho)
        nodo.altura = 1 + max(izq, der)
        return nodo.altura

    def insertar(self, clave: ClaveEvento, evento: Evento) -> int:
        nuevo = NodoAVL(clave, evento)
        if self._raiz is None:
            self._raiz = nuevo
        else:
            actual = self._raiz
            while True:
                if comparar_claves(clave, actual.clave) < 0:
                    if actual.izquierdo is None:
                        actual.izquierdo = nuevo
                        break
                    actual = actual.izquierdo
                else:
                    if actual.derecho is None:
                        actual.derecho = nuevo
                        break
                    actual = actual.derecho
        self._recalcular_alturas(self._raiz)
        self._reindexar()
        return 0

    def eliminar(self, clave: ClaveEvento) -> int:
        def _quitar(nodo, buscada):
            comp = comparar_claves(buscada, nodo.clave)
            if comp < 0:
                nodo.izquierdo = _quitar(nodo.izquierdo, buscada)
                return nodo
            if comp > 0:
                nodo.derecho = _quitar(nodo.derecho, buscada)
                return nodo
            return nodo.derecho if nodo.izquierdo is None else nodo.izquierdo

        def _eliminar_rec(nodo):
            if nodo is None:
                raise KeyError(clave)
            comp = comparar_claves(clave, nodo.clave)
            if comp < 0:
                nodo.izquierdo = _eliminar_rec(nodo.izquierdo)
            elif comp > 0:
                nodo.derecho = _eliminar_rec(nodo.derecho)
            else:
                if nodo.izquierdo is None:
                    return nodo.derecho
                if nodo.derecho is None:
                    return nodo.izquierdo
                sucesor = nodo.derecho
                while sucesor.izquierdo is not None:
                    sucesor = sucesor.izquierdo
                nodo.clave, nodo.evento_ref = sucesor.clave, sucesor.evento_ref
                nodo.derecho = _quitar(nodo.derecho, sucesor.clave)
            return nodo

        self._raiz = _eliminar_rec(self._raiz)
        self._recalcular_alturas(self._raiz)
        self._reindexar()
        return 0

    def buscar_por_id(self, identificador: int) -> Optional[Evento]:
        nodo = self._indice_por_id.get(identificador)
        return nodo.evento_ref if nodo is not None else None

    def nodos_visitados_ultima_operacion(self) -> int:
        return 1

    def _recorrido(self, orden: str) -> Iterator[Evento]:
        resultado: list[Evento] = []

        def visitar(nodo):
            if nodo is None:
                return
            if orden == "pre":
                resultado.append(nodo.evento_ref)
            visitar(nodo.izquierdo)
            if orden == "in":
                resultado.append(nodo.evento_ref)
            visitar(nodo.derecho)
            if orden == "post":
                resultado.append(nodo.evento_ref)

        visitar(self._raiz)
        return iter(resultado)

    def recorrido_inorden(self) -> Iterator[Evento]:
        return self._recorrido("in")

    def recorrido_preorden(self) -> Iterator[Evento]:
        return self._recorrido("pre")

    def recorrido_postorden(self) -> Iterator[Evento]:
        return self._recorrido("post")

    def recorrido_por_niveles(self) -> Iterator[Evento]:
        resultado = []
        cola = [self._raiz] if self._raiz is not None else []
        while cola:
            nodo = cola.pop(0)
            resultado.append(nodo.evento_ref)
            if nodo.izquierdo is not None:
                cola.append(nodo.izquierdo)
            if nodo.derecho is not None:
                cola.append(nodo.derecho)
        return iter(resultado)

    def altura(self) -> int:
        return altura(self._raiz)

    def cantidad_nodos(self) -> int:
        return len(self._indice_por_id)

    def cantidad_hojas(self) -> int:
        return sum(
            1 for n in self._indice_por_id.values() if n.izquierdo is None and n.derecho is None
        )

    def clonar(self) -> "ArbolDemostracion":
        copia = ArbolDemostracion()
        copia._raiz = deepcopy(self._raiz)
        copia.modo_estres = self.modo_estres
        copia._reindexar()
        return copia

    def restaurar_desde(self, otro: "ArbolDemostracion") -> None:
        self._raiz = deepcopy(otro._raiz)
        self.modo_estres = otro.modo_estres
        self._reindexar()

    def activar_modo_estres(self) -> None:
        self.modo_estres = True

    def recuperar_balance(self) -> int:
        self.modo_estres = False
        return 0

    def profundidad_de(self, identificador: int) -> int:
        objetivo = self._indice_por_id.get(identificador)
        if objetivo is None:
            raise KeyError(identificador)
        profundidad = 0
        actual = self._raiz
        while actual is not objetivo:
            comp = comparar_claves(objetivo.clave, actual.clave)
            actual = actual.izquierdo if comp < 0 else actual.derecho
            profundidad += 1
        return profundidad

    def factor_balance_de(self, identificador: int) -> int:
        nodo = self._indice_por_id.get(identificador)
        return factor_balance(nodo) if nodo is not None else 0

    def obtener_raiz(self) -> Optional[NodoAVL]:
        return self._raiz

    def instalar_topologia(self, raiz: Optional[NodoAVL]) -> None:
        self._raiz = raiz
        self._recalcular_alturas(self._raiz)
        self._reindexar()
