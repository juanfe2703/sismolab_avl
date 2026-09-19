import pytest

from src.model import Prioridad
from src.structures import AVL, ClaveEvento, ClaveNoEncontradaError, factor_balance


def _clave(id_: int) -> ClaveEvento:
    return ClaveEvento(Prioridad.MEDIA, 4.5, id_)


def _insertar_ids(avl: AVL, ids: list[int]) -> None:
    for id_ in ids:
        avl.insertar(_clave(id_), evento_ref=None)


def _inorden(nodo) -> list[int]:
    if nodo is None:
        return []
    return _inorden(nodo.izquierdo) + [nodo.clave.identificador] + _inorden(nodo.derecho)


def _verificar_avl(nodo) -> None:
    if nodo is None:
        return
    assert factor_balance(nodo) in (-1, 0, 1)
    _verificar_avl(nodo.izquierdo)
    _verificar_avl(nodo.derecho)


def test_eliminar_hoja():
    avl = AVL()
    _insertar_ids(avl, [20, 10, 30])
    avl.eliminar(_clave(10))
    assert _inorden(avl.raiz) == [20, 30]


def test_eliminar_nodo_con_un_hijo():
    avl = AVL()
    _insertar_ids(avl, [20, 10, 30, 5])
    avl.eliminar(_clave(10))
    assert _inorden(avl.raiz) == [5, 20, 30]


def test_eliminar_nodo_con_dos_hijos():
    avl = AVL()
    _insertar_ids(avl, [20, 10, 30, 25, 40])
    avl.eliminar(_clave(20))  # tiene dos hijos: 10 y 30
    assert 20 not in _inorden(avl.raiz)
    assert _inorden(avl.raiz) == [10, 25, 30, 40]


def test_eliminar_raiz_con_arbol_de_un_solo_nodo():
    avl = AVL()
    _insertar_ids(avl, [1])
    avl.eliminar(_clave(1))
    assert avl.raiz is None


def test_eliminar_de_arbol_vacio_lanza_error():
    avl = AVL()
    with pytest.raises(ClaveNoEncontradaError):
        avl.eliminar(_clave(1))


def test_eliminar_clave_inexistente_lanza_error():
    avl = AVL()
    _insertar_ids(avl, [10, 20])
    with pytest.raises(ClaveNoEncontradaError):
        avl.eliminar(_clave(99))


def test_eliminacion_dispara_rebalanceo():
    avl = AVL()
    ids = [50, 30, 70, 20, 40, 60, 80, 10]
    _insertar_ids(avl, ids)
    avl.eliminar(_clave(60))
    avl.eliminar(_clave(70))
    avl.eliminar(_clave(80))
    _verificar_avl(avl.raiz)
    assert sorted(_inorden(avl.raiz)) == sorted(set(ids) - {60, 70, 80})


def test_eliminacion_masiva_mantiene_avl_valido():
    avl = AVL()
    ids = list(range(1, 51))
    _insertar_ids(avl, ids)
    for id_ in range(1, 51, 2):  # elimina todos los impares
        avl.eliminar(_clave(id_))
    _verificar_avl(avl.raiz)
    assert _inorden(avl.raiz) == [i for i in ids if i % 2 == 0]
