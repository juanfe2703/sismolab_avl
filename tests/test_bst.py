import math
import random

import pytest

from src.model import Prioridad
from src.structures import (
    AVL,
    BST,
    ClaveDuplicadaError,
    ClaveEvento,
    ClaveNoEncontradaError,
    altura_recalculada,
    cantidad_hojas,
    cantidad_nodos,
    recorrido_inorden,
)


def _clave(id_: int) -> ClaveEvento:
    return ClaveEvento(Prioridad.MEDIA, 4.5, id_)


def _bst_con_ids(ids):
    bst = BST()
    for id_ in ids:
        bst.insertar(_clave(id_), evento_ref=None)
    return bst


def _ids_inorden(arbol):
    return [c.identificador for c in recorrido_inorden(arbol.raiz)]


# ---------- operaciones basicas del BST ----------

def test_insertar_no_rebalancea_la_forma_es_la_de_un_bst_clasico():
    bst = _bst_con_ids([10, 20, 30])  # un AVL habria rotado aqui
    assert bst.raiz.clave.identificador == 10
    assert bst.raiz.derecho.clave.identificador == 20
    assert bst.raiz.derecho.derecho.clave.identificador == 30


def test_insertar_clave_duplicada_lanza_error():
    bst = _bst_con_ids([10])
    with pytest.raises(ClaveDuplicadaError):
        bst.insertar(_clave(10), evento_ref=None)


def test_buscar_cuenta_nodos_visitados():
    bst = _bst_con_ids([10, 20, 30])
    assert bst.buscar(_clave(30)).nodos_visitados == 3


def test_eliminar_hoja():
    bst = _bst_con_ids([20, 10, 30])
    bst.eliminar(_clave(10))
    assert _ids_inorden(bst) == [20, 30]


def test_eliminar_nodo_con_un_hijo():
    bst = _bst_con_ids([20, 10, 30, 5])
    bst.eliminar(_clave(10))
    assert _ids_inorden(bst) == [5, 20, 30]


def test_eliminar_nodo_con_dos_hijos():
    bst = _bst_con_ids([20, 10, 30, 25, 40])
    bst.eliminar(_clave(20))
    assert _ids_inorden(bst) == [10, 25, 30, 40]


def test_eliminar_raiz_con_dos_hijos_cuando_el_sucesor_es_hijo_directo():
    bst = _bst_con_ids([20, 10, 30])  # sucesor de 20 es 30, hijo directo
    bst.eliminar(_clave(20))
    assert _ids_inorden(bst) == [10, 30]


def test_eliminar_unico_nodo_deja_arbol_vacio():
    bst = _bst_con_ids([1])
    bst.eliminar(_clave(1))
    assert bst.raiz is None


def test_eliminar_clave_inexistente_lanza_error():
    bst = _bst_con_ids([10, 20])
    with pytest.raises(ClaveNoEncontradaError):
        bst.eliminar(_clave(99))


# ---------- comparacion AVL vs BST (seccion 11) ----------

def _comparaciones_totales(arbol, ids):
    return sum(arbol.buscar(_clave(i)).nodos_visitados for i in ids)


def test_orden_ascendente_degenera_el_bst_pero_no_el_avl():
    ids = list(range(1, 201))
    bst, avl = BST(), AVL()
    for id_ in ids:
        bst.insertar(_clave(id_), None)
        avl.insertar(_clave(id_), None)

    # BST: cadena de 200 nodos
    assert altura_recalculada(bst.raiz) == 199
    assert cantidad_hojas(bst.raiz) == 1
    # buscar todas las claves cuesta 1 + 2 + ... + 200
    assert _comparaciones_totales(bst, ids) == 200 * 201 // 2

    # AVL: altura logaritmica y muchisimas menos comparaciones
    assert altura_recalculada(avl.raiz) <= 1.45 * math.log2(len(ids) + 2)
    assert _comparaciones_totales(avl, ids) < _comparaciones_totales(bst, ids) / 10


def test_mismo_conjunto_distinto_orden_produce_mismo_inorden():
    ids = list(range(1, 101))
    mezclado = ids[:]
    random.Random(42).shuffle(mezclado)

    bst_orden, bst_mezclado = _bst_con_ids(ids), _bst_con_ids(mezclado)
    avl = AVL()
    for id_ in mezclado:
        avl.insertar(_clave(id_), None)

    # la forma cambia con el orden de insercion, el orden logico no
    assert _ids_inorden(bst_orden) == ids
    assert _ids_inorden(bst_mezclado) == ids
    assert _ids_inorden(avl) == ids
    assert altura_recalculada(bst_orden.raiz) > altura_recalculada(bst_mezclado.raiz)


def test_altura_recalculada_coincide_con_la_altura_guardada_del_avl():
    avl = AVL()
    for id_ in [50, 30, 70, 20, 40, 60, 80, 10, 90, 5]:
        avl.insertar(_clave(id_), None)
    assert altura_recalculada(avl.raiz) == avl.raiz.altura
    assert cantidad_nodos(avl.raiz) == 10


def test_altura_recalculada_de_arbol_vacio_es_menos_uno():
    assert altura_recalculada(None) == -1