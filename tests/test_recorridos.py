from src.model import Prioridad
from src.structures import (
    AVL,
    ClaveEvento,
    recorrido_inorden,
    recorrido_por_niveles,
    recorrido_postorden,
    recorrido_preorden,
)


def _clave(id_: int) -> ClaveEvento:
    return ClaveEvento(Prioridad.MEDIA, 4.5, id_)


def _avl_con_ids(ids: list[int]) -> AVL:
    avl = AVL()
    for id_ in ids:
        avl.insertar(_clave(id_), evento_ref=None)
    return avl


def _ids(claves: list[ClaveEvento]) -> list[int]:
    return [c.identificador for c in claves]


def test_recorrido_arbol_vacio_es_lista_vacia():
    avl = AVL()
    assert recorrido_inorden(avl.raiz) == []
    assert recorrido_preorden(avl.raiz) == []
    assert recorrido_postorden(avl.raiz) == []
    assert recorrido_por_niveles(avl.raiz) == []


def test_inorden_produce_claves_ascendentes():
    avl = _avl_con_ids([50, 30, 70, 20, 40, 60, 80, 10, 90, 5])
    resultado = _ids(recorrido_inorden(avl.raiz))
    assert resultado == sorted(resultado)


def test_preorden_empieza_por_la_raiz():
    avl = _avl_con_ids([20, 10, 30])  # queda balanceado con raiz 20
    resultado = _ids(recorrido_preorden(avl.raiz))
    assert resultado[0] == avl.raiz.clave.identificador


def test_postorden_termina_en_la_raiz():
    avl = _avl_con_ids([20, 10, 30])
    resultado = _ids(recorrido_postorden(avl.raiz))
    assert resultado[-1] == avl.raiz.clave.identificador


def test_por_niveles_respeta_orden_de_profundidad():
    avl = _avl_con_ids([20, 10, 30, 5, 15, 25, 35])
    resultado = _ids(recorrido_por_niveles(avl.raiz))
    assert resultado[0] == 20  # raiz primero
    assert set(resultado[1:3]) == {10, 30}  # nivel 1
    assert set(resultado[3:7]) == {5, 15, 25, 35}  # nivel 2
