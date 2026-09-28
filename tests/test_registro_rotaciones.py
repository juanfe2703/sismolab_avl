from src.model import Prioridad
from src.structures import (
    AVL,
    CasoBalanceo,
    ClaveEvento,
    ContadoresRotaciones,
    RotacionAplicada,
)


def _clave(id_: int) -> ClaveEvento:
    return ClaveEvento(Prioridad.MEDIA, 4.5, id_)


def _avl_con_ids(ids) -> AVL:
    avl = AVL()
    for id_ in ids:
        avl.insertar(_clave(id_), evento_ref=None)
    return avl


def test_insercion_sin_desbalance_no_registra_rotaciones():
    avl = _avl_con_ids([20, 10, 30])
    assert avl.contadores == ContadoresRotaciones()
    assert avl.rotaciones_recientes == []


def test_caso_ll_registra_un_caso_y_un_giro_a_la_derecha():
    avl = _avl_con_ids([30, 20, 10])
    assert avl.contadores.casos_ll == 1
    assert avl.contadores.giros_derecha == 1
    assert avl.contadores.giros_izquierda == 0
    assert avl.rotaciones_recientes == [RotacionAplicada(CasoBalanceo.LL, _clave(30))]


def test_caso_rr_registra_un_caso_y_un_giro_a_la_izquierda():
    avl = _avl_con_ids([10, 20, 30])
    assert avl.contadores.casos_rr == 1
    assert avl.contadores.giros_izquierda == 1
    assert avl.contadores.giros_derecha == 0


def test_caso_lr_cuenta_un_caso_y_dos_giros():
    # document section 14: a double case is ONE case and TWO elementary turns
    avl = _avl_con_ids([30, 10, 20])
    assert avl.contadores.casos_lr == 1
    assert avl.contadores.giros_izquierda == 1
    assert avl.contadores.giros_derecha == 1
    assert avl.contadores.total_giros == 2
    assert avl.contadores.casos_ll == 0


def test_caso_rl_cuenta_un_caso_y_dos_giros():
    avl = _avl_con_ids([10, 30, 20])
    assert avl.contadores.casos_rl == 1
    assert avl.contadores.total_giros == 2
    assert avl.rotaciones_recientes == [RotacionAplicada(CasoBalanceo.RL, _clave(10))]


def test_eliminacion_que_desbalancea_a_la_izquierda_registra_ll():
    avl = _avl_con_ids([20, 10, 30, 5])
    avl.eliminar(_clave(30))  # node 20: fb=2, left child 10 has fb=1
    assert avl.contadores.casos_ll == 1
    assert avl.rotaciones_recientes == [RotacionAplicada(CasoBalanceo.LL, _clave(20))]


def test_eliminacion_con_hijo_inclinado_al_lado_contrario_registra_lr():
    avl = _avl_con_ids([20, 10, 30, 15])
    avl.eliminar(_clave(30))  # node 20: fb=2, left child 10 has fb=-1
    assert avl.contadores.casos_lr == 1
    assert avl.contadores.total_giros == 2


def test_rotaciones_recientes_se_reinicia_pero_los_contadores_acumulan():
    avl = _avl_con_ids([30, 20, 10])
    assert len(avl.rotaciones_recientes) == 1

    avl.insertar(_clave(40), evento_ref=None)  # no rotation needed
    assert avl.rotaciones_recientes == []
    assert avl.contadores.casos_ll == 1


def test_copiar_contadores_produce_una_copia_independiente():
    original = ContadoresRotaciones(casos_ll=2)
    copia = original.copiar()
    copia.registrar(CasoBalanceo.RR)
    assert original.casos_rr == 0
    assert copia.casos_rr == 1
    assert copia.casos_ll == 2