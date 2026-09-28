import pytest

from src.model import Prioridad
from src.structures import (
    AVL,
    ClaveDuplicadaError,
    ClaveEvento,
    ContadoresRotaciones,
    altura_recalculada,
    factor_balance,
    recorrido_inorden,
    recorrido_preorden,
)


def _clave(id_: int) -> ClaveEvento:
    return ClaveEvento(Prioridad.MEDIA, 4.5, id_)


def _avl_estres(ids) -> AVL:
    avl = AVL()
    avl.activar_modo_estres()
    for id_ in ids:
        avl.insertar(_clave(id_), evento_ref=None)
    return avl


def _ids_inorden(avl: AVL) -> list[int]:
    return [c.identificador for c in recorrido_inorden(avl.raiz)]


def _verificar_alturas_guardadas(nodo) -> int:
    """Asserts every stored height equals the real one; returns the height."""
    if nodo is None:
        return -1
    real = 1 + max(
        _verificar_alturas_guardadas(nodo.izquierdo),
        _verificar_alturas_guardadas(nodo.derecho),
    )
    assert nodo.altura == real
    return real


def test_modo_normal_es_el_valor_por_defecto():
    assert AVL().modo_estres is False


def test_activar_modo_estres():
    avl = AVL()
    avl.activar_modo_estres()
    assert avl.modo_estres is True


def test_estres_no_rota_y_conserva_el_orden_bst():
    avl = _avl_estres([10, 20, 30])  # in normal mode the root would be 20
    assert avl.raiz.clave.identificador == 10
    assert avl.contadores == ContadoresRotaciones()
    assert avl.rotaciones_recientes == []
    assert _ids_inorden(avl) == [10, 20, 30]
    assert factor_balance(avl.raiz) == -2  # not an AVL, on purpose


def test_estres_permite_desbalances_mayores_que_dos():
    avl = _avl_estres(range(1, 11))  # chain of 10 nodes
    assert factor_balance(avl.raiz) == -9


def test_estres_mantiene_las_alturas_guardadas_correctas():
    avl = _avl_estres(range(1, 101))
    _verificar_alturas_guardadas(avl.raiz)
    assert avl.raiz.altura == 99


def test_estres_busqueda_cuesta_la_posicion_en_la_cadena():
    avl = _avl_estres(range(1, 51))
    assert avl.buscar(_clave(50)).nodos_visitados == 50


def test_estres_eliminar_conserva_orden_y_alturas_sin_rotar():
    avl = _avl_estres([5, 3, 8, 1, 4, 7, 9, 2, 6])
    avl.eliminar(_clave(5))  # two children
    avl.eliminar(_clave(1))  # one child
    assert _ids_inorden(avl) == [2, 3, 4, 6, 7, 8, 9]
    _verificar_alturas_guardadas(avl.raiz)
    assert avl.contadores == ContadoresRotaciones()


def test_estres_clave_duplicada_no_modifica_el_arbol():
    avl = _avl_estres([10, 20, 30])
    antes = [c.identificador for c in recorrido_preorden(avl.raiz)]
    with pytest.raises(ClaveDuplicadaError):
        avl.insertar(_clave(20), evento_ref=None)
    despues = [c.identificador for c in recorrido_preorden(avl.raiz)]
    assert antes == despues
    _verificar_alturas_guardadas(avl.raiz)


def test_mismo_conjunto_en_normal_y_estres_da_mismo_inorden_y_distinta_forma():
    ids = list(range(1, 32))
    normal = AVL()
    for id_ in ids:
        normal.insertar(_clave(id_), evento_ref=None)
    estres = _avl_estres(ids)

    assert _ids_inorden(normal) == _ids_inorden(estres) == ids
    assert altura_recalculada(normal.raiz) <= 7
    assert altura_recalculada(estres.raiz) == 30


def test_activar_estres_a_mitad_solo_aplaza_las_rotaciones_siguientes():
    avl = AVL()
    for id_ in (30, 20, 10):  # LL rotation happens in normal mode
        avl.insertar(_clave(id_), evento_ref=None)
    assert avl.contadores.casos_ll == 1

    avl.activar_modo_estres()
    for id_ in (40, 50, 60):  # would trigger an RR case in normal mode
        avl.insertar(_clave(id_), evento_ref=None)

    assert avl.contadores.casos_ll == 1
    assert avl.contadores.casos_rr == 0
    assert factor_balance(avl.raiz) == -3
    _verificar_alturas_guardadas(avl.raiz)