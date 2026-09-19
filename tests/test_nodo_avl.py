from src.model import Prioridad
from src.structures import ClaveEvento, NodoAVL, altura, factor_balance


def _clave(id_: int) -> ClaveEvento:
    return ClaveEvento(Prioridad.MEDIA, 4.5, id_)


def test_altura_de_arbol_vacio_es_menos_uno():
    assert altura(None) == -1


def test_nodo_nuevo_es_hoja_con_altura_cero():
    nodo = NodoAVL(_clave(1), evento_ref=None)
    assert nodo.altura == 0
    assert altura(nodo) == 0


def test_factor_balance_de_hoja_es_cero():
    nodo = NodoAVL(_clave(1), evento_ref=None)
    assert factor_balance(nodo) == 0


def test_factor_balance_de_arbol_vacio_es_cero():
    assert factor_balance(None) == 0


def test_factor_balance_refleja_desbalance_manual():
    raiz = NodoAVL(_clave(10), evento_ref=None)
    hijo_izq = NodoAVL(_clave(5), evento_ref=None)
    nieto_izq = NodoAVL(_clave(2), evento_ref=None)

    raiz.izquierdo = hijo_izq
    hijo_izq.izquierdo = nieto_izq

    # alturas actualizadas a mano, todavia sin logica automatica (eso es Fase 5)
    hijo_izq.altura = 1
    raiz.altura = 2

    assert factor_balance(raiz) == 2  # altura(izq)=1 - altura(der)=-1