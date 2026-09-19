from src.model import Prioridad
from src.structures import ClaveEvento, NodoAVL, altura, rotar_derecha, rotar_izquierda


def _clave(id_: int) -> ClaveEvento:
    return ClaveEvento(Prioridad.MEDIA, 4.5, id_)


def _nodo(id_: int) -> NodoAVL:
    return NodoAVL(_clave(id_), evento_ref=None)


def test_rotar_derecha_reestructura_correctamente():
    # y=30 con hijo izquierdo x=20, y este con hijo izquierdo t1=10
    # (caso LL manual, sin insercion)
    y = _nodo(30)
    x = _nodo(20)
    t1 = _nodo(10)

    y.izquierdo = x
    x.izquierdo = t1
    x.altura = 1
    y.altura = 2

    nueva_raiz = rotar_derecha(y)

    assert nueva_raiz is x
    assert x.izquierdo is t1
    assert x.derecho is y
    assert y.izquierdo is None
    assert y.derecho is None


def test_rotar_derecha_actualiza_alturas():
    y = _nodo(30)
    x = _nodo(20)
    t1 = _nodo(10)
    y.izquierdo = x
    x.izquierdo = t1
    x.altura = 1
    y.altura = 2

    nueva_raiz = rotar_derecha(y)

    assert altura(nueva_raiz) == 1  # x ahora tiene 2 hijos hoja: t1 y y
    assert altura(nueva_raiz.izquierdo) == 0
    assert altura(nueva_raiz.derecho) == 0


def test_rotar_derecha_preserva_t2():
    # y=30, x=20 con hijos t1=10 y t2=25 -> t2 debe terminar como
    # hijo izquierdo de y tras la rotacion (sigue entre x y y en valor)
    y = _nodo(30)
    x = _nodo(20)
    t1 = _nodo(10)
    t2 = _nodo(25)

    y.izquierdo = x
    x.izquierdo = t1
    x.derecho = t2
    x.altura = 1
    y.altura = 2

    nueva_raiz = rotar_derecha(y)

    assert nueva_raiz.derecho is y
    assert y.izquierdo is t2


def test_rotar_izquierda_es_espejo_de_rotar_derecha():
    # x=10 con hijo derecho y=20, este con hijo derecho t3=30
    x = _nodo(10)
    y = _nodo(20)
    t3 = _nodo(30)

    x.derecho = y
    y.derecho = t3
    y.altura = 1
    x.altura = 2

    nueva_raiz = rotar_izquierda(x)

    assert nueva_raiz is y
    assert y.izquierdo is x
    assert y.derecho is t3
    assert x.izquierdo is None
    assert x.derecho is None


def test_rotaciones_son_inversas_entre_si():
    # rotar a la derecha y luego a la izquierda debe devolver
    # la forma original (mismos nodos, misma disposicion)
    y = _nodo(30)
    x = _nodo(20)
    t1 = _nodo(10)
    y.izquierdo = x
    x.izquierdo = t1
    x.altura = 1
    y.altura = 2

    raiz_intermedia = rotar_derecha(y)
    raiz_final = rotar_izquierda(raiz_intermedia)

    assert raiz_final is y
    assert y.izquierdo is x
    assert x.izquierdo is t1
