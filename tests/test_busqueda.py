from src.model import Prioridad
from src.structures import AVL, ClaveEvento


def _clave(id_: int) -> ClaveEvento:
    return ClaveEvento(Prioridad.MEDIA, 4.5, id_)


def _avl_con_ids(ids):
    avl = AVL()
    for id_ in ids:
        avl.insertar(_clave(id_), evento_ref=None)
    return avl


def test_buscar_en_arbol_vacio_no_visita_nodos():
    resultado = AVL().buscar(_clave(1))
    assert not resultado.encontrado
    assert resultado.nodos_visitados == 0
    assert resultado.profundidad is None


def test_buscar_la_raiz_visita_un_nodo():
    avl = _avl_con_ids([20, 10, 30])
    resultado = avl.buscar(_clave(20))
    assert resultado.encontrado
    assert resultado.nodos_visitados == 1
    assert resultado.profundidad == 0


def test_costo_de_busqueda_es_profundidad_mas_uno():
    # 20,10,30,5,15,25,35 -> arbol perfecto: 5 esta en profundidad 2
    avl = _avl_con_ids([20, 10, 30, 5, 15, 25, 35])
    resultado = avl.buscar(_clave(5))
    assert resultado.profundidad == 2
    assert resultado.nodos_visitados == resultado.profundidad + 1


def test_buscar_clave_inexistente_cuenta_nodos_examinados():
    avl = _avl_con_ids([20, 10, 30])
    resultado = avl.buscar(_clave(99))  # 20 -> 30 -> None
    assert not resultado.encontrado
    assert resultado.nodos_visitados == 2


def test_busqueda_devuelve_el_nodo_con_la_clave_buscada():
    avl = _avl_con_ids([20, 10, 30])
    assert avl.buscar(_clave(10)).nodo.clave == _clave(10)