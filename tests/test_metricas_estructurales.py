from src.model import Prioridad
from src.structures import AVL, ClaveEvento, altura_arbol, cantidad_hojas, cantidad_nodos


def _clave(id_: int) -> ClaveEvento:
    return ClaveEvento(Prioridad.MEDIA, 4.5, id_)


def _avl_con_ids(ids: list[int]) -> AVL:
    avl = AVL()
    for id_ in ids:
        avl.insertar(_clave(id_), evento_ref=None)
    return avl


def test_metricas_de_arbol_vacio():
    avl = AVL()
    assert cantidad_nodos(avl.raiz) == 0
    assert altura_arbol(avl.raiz) == -1
    assert cantidad_hojas(avl.raiz) == 0


def test_metricas_de_arbol_un_nodo():
    avl = _avl_con_ids([1])
    assert cantidad_nodos(avl.raiz) == 1
    assert altura_arbol(avl.raiz) == 0
    assert cantidad_hojas(avl.raiz) == 1


def test_metricas_de_arbol_balanceado_conocido():
    # 20,10,30,5,15,25,35 -> arbol perfecto de 7 nodos, altura 2
    avl = _avl_con_ids([20, 10, 30, 5, 15, 25, 35])
    assert cantidad_nodos(avl.raiz) == 7
    assert altura_arbol(avl.raiz) == 2
    assert cantidad_hojas(avl.raiz) == 4


def test_cantidad_nodos_tras_eliminaciones():
    avl = _avl_con_ids(list(range(1, 21)))
    for id_ in range(1, 11):
        avl.eliminar(_clave(id_))
    assert cantidad_nodos(avl.raiz) == 10