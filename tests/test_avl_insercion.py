from src.model import Prioridad
from src.structures import AVL, ClaveEvento


def _clave(id_: int) -> ClaveEvento:
    return ClaveEvento(Prioridad.MEDIA, 4.5, id_)


def _insertar_ids(avl: AVL, ids: list[int]) -> None:
    for id_ in ids:
        avl.insertar(_clave(id_), evento_ref=None)


def _inorden(nodo) -> list[int]:
    if nodo is None:
        return []
    return _inorden(nodo.izquierdo) + [nodo.clave.identificador] + _inorden(nodo.derecho)


def test_caso_ll_rota_derecha():
    avl = AVL()
    _insertar_ids(avl, [30, 20, 10])
    assert avl.raiz.clave.identificador == 20
    assert avl.raiz.izquierdo.clave.identificador == 10
    assert avl.raiz.derecho.clave.identificador == 30


def test_caso_rr_rota_izquierda():
    avl = AVL()
    _insertar_ids(avl, [10, 20, 30])
    assert avl.raiz.clave.identificador == 20
    assert avl.raiz.izquierdo.clave.identificador == 10
    assert avl.raiz.derecho.clave.identificador == 30


def test_caso_lr_rota_izquierda_luego_derecha():
    avl = AVL()
    _insertar_ids(avl, [30, 10, 20])
    assert avl.raiz.clave.identificador == 20
    assert avl.raiz.izquierdo.clave.identificador == 10
    assert avl.raiz.derecho.clave.identificador == 30


def test_caso_rl_rota_derecha_luego_izquierda():
    avl = AVL()
    _insertar_ids(avl, [10, 30, 20])
    assert avl.raiz.clave.identificador == 20
    assert avl.raiz.izquierdo.clave.identificador == 10
    assert avl.raiz.derecho.clave.identificador == 30


def test_insercion_multiple_mantiene_orden_inorden():
    avl = AVL()
    ids = [50, 30, 70, 20, 40, 60, 80, 10, 90, 5]
    _insertar_ids(avl, ids)
    assert _inorden(avl.raiz) == sorted(ids)


def test_altura_se_mantiene_logaritmica():
    # con balanceo, 100 inserciones no deberian producir una altura
    # mayor a ~2*log2(100) (cota laxa, solo para detectar degeneracion)
    import math

    avl = AVL()
    _insertar_ids(avl, list(range(1, 101)))
    assert avl.raiz.altura <= 2 * math.log2(101)


def test_factor_balance_de_todos_los_nodos_respeta_avl():
    from src.structures import factor_balance

    def _verificar(nodo):
        if nodo is None:
            return
        assert factor_balance(nodo) in (-1, 0, 1)
        _verificar(nodo.izquierdo)
        _verificar(nodo.derecho)

    avl = AVL()
    _insertar_ids(avl, [50, 30, 70, 20, 40, 60, 80, 10, 90, 5, 15, 25, 35])
    _verificar(avl.raiz)