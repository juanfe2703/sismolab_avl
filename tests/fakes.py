"""A fake tree satisfying ArbolAVLProtocol, used ONLY to test the
services layer before the real AVL exists. It maintains a REAL linked
node graph (so persistence's topology export/import has something
genuine to walk), inserted as a plain BST by `comparar_claves` - but it
never rotates. `recuperar_balance` only clears the `modo_estres` flag;
it does not actually rebalance. None of this is delivered code: it
exists purely so the business-rule tests in this folder can run
against something that honors the Protocol contract in
`src/services/contratos.py`.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Iterator, Optional

from src.model import Evento
from src.structures import ClaveEvento, NodoAVL, altura, comparar_claves, factor_balance


class ArbolFalso:
    def __init__(self) -> None:
        self._raiz: Optional[NodoAVL] = None
        self._indice_por_id: dict[int, NodoAVL] = {}
        self.modo_estres: bool = False

    # ---------- internals ----------

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

    def _tras_cambio_estructural(self) -> None:
        self._recalcular_alturas(self._raiz)
        self._reindexar()

    # ---------- ArbolBusquedaProtocol ----------

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
        self._tras_cambio_estructural()
        return 0  # el fake nunca rota

    def eliminar(self, clave: ClaveEvento) -> int:
        def _eliminar_rec_por_clave(nodo: Optional[NodoAVL], clave_obj: ClaveEvento) -> Optional[NodoAVL]:
            comparacion = comparar_claves(clave_obj, nodo.clave)
            if comparacion < 0:
                nodo.izquierdo = _eliminar_rec_por_clave(nodo.izquierdo, clave_obj)
                return nodo
            if comparacion > 0:
                nodo.derecho = _eliminar_rec_por_clave(nodo.derecho, clave_obj)
                return nodo
            return nodo.derecho if nodo.izquierdo is None else nodo.izquierdo

        def _eliminar_rec(nodo: Optional[NodoAVL]) -> Optional[NodoAVL]:
            if nodo is None:
                raise KeyError(clave)
            comparacion = comparar_claves(clave, nodo.clave)
            if comparacion < 0:
                nodo.izquierdo = _eliminar_rec(nodo.izquierdo)
            elif comparacion > 0:
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
                nodo.derecho = _eliminar_rec_por_clave(nodo.derecho, sucesor.clave)
            return nodo

        self._raiz = _eliminar_rec(self._raiz)
        self._tras_cambio_estructural()
        return 0

    def buscar_por_id(self, identificador: int) -> Optional[Evento]:
        nodo = self._indice_por_id.get(identificador)
        return nodo.evento_ref if nodo is not None else None

    def nodos_visitados_ultima_operacion(self) -> int:
        return 1  # no medido en el fake; no usado por las pruebas actuales

    def _recorrido(self, orden: str) -> Iterator[Evento]:
        resultado: list[Evento] = []

        def visitar(nodo: Optional[NodoAVL]) -> None:
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

    def clonar(self) -> "ArbolFalso":
        copia = ArbolFalso()
        copia._raiz = deepcopy(self._raiz)
        copia.modo_estres = self.modo_estres
        copia._reindexar()
        return copia

    def restaurar_desde(self, otro: "ArbolFalso") -> None:
        self._raiz = deepcopy(otro._raiz)
        self.modo_estres = otro.modo_estres
        self._reindexar()

    # ---------- ArbolAVLProtocol ----------

    def activar_modo_estres(self) -> None:
        self.modo_estres = True

    def recuperar_balance(self) -> int:
        # El fake nunca desbalancea nada de verdad, asi que "recuperar"
        # solo apaga la bandera. Lo que se prueba con este doble es la
        # logica de negocio de los servicios, no el balanceo del AVL.
        self.modo_estres = False
        return 0

    def profundidad_de(self, identificador: int) -> int:
        nodo_objetivo = self._indice_por_id.get(identificador)
        if nodo_objetivo is None:
            raise KeyError(identificador)
        profundidad = 0
        actual = self._raiz
        while actual is not nodo_objetivo:
            comparacion = comparar_claves(nodo_objetivo.clave, actual.clave)
            actual = actual.izquierdo if comparacion < 0 else actual.derecho
            profundidad += 1
        return profundidad

    def factor_balance_de(self, identificador: int) -> int:
        nodo = self._indice_por_id.get(identificador)
        return factor_balance(nodo) if nodo is not None else 0

    # ---------- extensiones para persistencia ----------

    def obtener_raiz(self) -> Optional[NodoAVL]:
        return self._raiz

    def instalar_topologia(self, raiz: Optional[NodoAVL]) -> None:
        self._raiz = raiz
        self._recalcular_alturas(self._raiz)
        self._reindexar()


class ZonaFalsa:
    """Everything is populated - or configure `poblados` per call, used
    to reproduce section 4's own worked example (M=4.5, H=30.0)."""

    def __init__(self, poblado_por_defecto: bool = True) -> None:
        self.poblado_por_defecto = poblado_por_defecto

    def es_zona_poblada(self, x: float, y: float) -> bool:
        return self.poblado_por_defecto


class RelojFalso:
    def __init__(self, ahora):
        self._ahora = ahora

    def ahora(self):
        return self._ahora

    def avanzar(self, nuevo_instante) -> None:
        self._ahora = nuevo_instante
