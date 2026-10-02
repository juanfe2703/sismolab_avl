"""Tests for ProcesadorCola. Run via run_tests.py (see repo root)."""
from datetime import datetime, timezone

from src.services.cola_reportes import ColaReportes
from src.services.gestor_asociaciones import GestorAsociaciones
from src.services.historico import Historico
from src.services.procesador_cola import ProcesadorCola
from src.services.reporte import Reporte
from src.services.servicio_eventos import ServicioEventos, TipoResultado
from src.undo.pila_deshacer import PilaDeshacer

from .fakes import ArbolFalso, RelojFalso, ZonaFalsa


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def _procesador(ahora=_utc(2026, 9, 19, 12, 0, 0)):
    arbol = ArbolFalso()
    historico = Historico()
    zona = ZonaFalsa(True)
    reloj = RelojFalso(ahora)
    pila = PilaDeshacer()
    gestor = GestorAsociaciones(arbol, historico)
    servicio_eventos = ServicioEventos(arbol, historico, zona, reloj, pila, gestor)
    cola = ColaReportes()
    procesador = ProcesadorCola(cola, servicio_eventos, pila)
    return procesador, arbol, historico, cola, pila, servicio_eventos


# -------------------------------------------------------------- orden ----

def test_preparar_rafaga_no_aplica_nada_todavia():
    procesador, arbol, _, cola, pila, _ = _procesador()
    procesador.preparar_rafaga([
        Reporte(1, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), 1, "EST-A"),
        Reporte(2, 4.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 5, 0), 1, "EST-B"),
    ])
    assert cola.cantidad_pendientes() == 2
    assert arbol.cantidad_nodos() == 0  # nada se aplica hasta procesar
    assert len(pila) == 0  # encolar no es una accion de deshacer


def test_procesar_un_paso_respeta_orden_fifo_no_prioridad():
    """La prioridad del terremoto decide su posicion en el AVL, NUNCA
    su posicion en la cola (section 8)."""
    procesador, arbol, _, cola, _, _ = _procesador()
    # El segundo reporte en llegar tiene MUCHA mayor prioridad (M=6.5),
    # pero debe procesarse DESPUES porque llego despues.
    procesador.preparar_rafaga([
        Reporte(1, 3.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), 1, "EST-A"),
        Reporte(2, 6.5, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 5, 0), 1, "EST-B"),
    ])
    paso1 = procesador.procesar_un_paso()
    paso2 = procesador.procesar_un_paso()
    assert paso1.identificador == 1
    assert paso2.identificador == 2
    assert cola.esta_vacia()


def test_procesar_un_paso_con_cola_vacia_no_rompe_nada():
    procesador, *_ = _procesador()
    paso = procesador.procesar_un_paso()
    assert paso.hubo_reporte is False


# -------------------------------------------------------- resultado/paso ----

def test_resultado_del_paso_muestra_estacion_evento_revision_y_decision():
    procesador, arbol, *_ = _procesador()
    procesador.preparar_rafaga([
        Reporte(10, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), 1, "EST-X"),
    ])
    paso = procesador.procesar_un_paso()
    assert paso.estacion == "EST-X"
    assert paso.identificador == 10
    assert paso.revision == 1
    assert paso.resultado.tipo == TipoResultado.ALTA


def test_rotaciones_del_paso_se_propagan_desde_el_arbol():
    """El fake no rota de verdad, pero se simula para confirmar que
    ServicioEventos y ProcesadorCola SI propagan lo que el arbol
    reporte (contrato: insertar/eliminar devuelven rotaciones)."""
    procesador, arbol, *_ = _procesador()
    arbol.rotaciones_simuladas = 2
    procesador.preparar_rafaga([
        Reporte(20, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), 1, "EST-A"),
    ])
    paso = procesador.procesar_un_paso()
    assert paso.rotaciones == 2


def test_rafaga_incluye_alta_confirmacion_antiguo_y_correccion_de_clave():
    """Caso obligatorio de la seccion 8: una rafaga con altas,
    confirmaciones, reportes antiguos y correcciones que cambian la
    clave, procesados uno por uno."""
    procesador, arbol, _, cola, _, _ = _procesador()
    fecha = _utc(2026, 9, 19, 8, 0, 0)
    procesador.preparar_rafaga([
        Reporte(1, 4.8, 70.0, 1.0, 1.0, fecha, 1, "EST-A"),          # alta
        Reporte(1, 4.8, 70.0, 1.0, 1.0, fecha, 1, "EST-B"),          # confirmacion
        Reporte(1, 1.0, 1.0, 1.0, 1.0, fecha, 0, "EST-C"),           # antiguo (revision 0)
        Reporte(1, 6.2, 15.0, 1.0, 1.0, fecha, 2, "EST-D"),          # revision mayor, cambia P
    ])
    tipos = [procesador.procesar_un_paso().resultado.tipo for _ in range(4)]
    assert tipos == [
        TipoResultado.ALTA, TipoResultado.CONFIRMACION,
        TipoResultado.REPORTE_ANTIGUO, TipoResultado.ACTUALIZACION,
    ]
    assert arbol.buscar_por_id(1).magnitud == 6.2
    assert cola.esta_vacia()


# ------------------------------------------------------- modo continuo ----

def test_procesar_continuo_es_un_generador_paso_a_paso():
    procesador, arbol, *_ = _procesador()
    fecha = _utc(2026, 9, 19, 8, 0, 0)
    procesador.preparar_rafaga([
        Reporte(1, 5.0, 10.0, 1.0, 1.0, fecha, 1, "EST-A"),
        Reporte(2, 5.0, 10.0, 1.0, 1.0, fecha, 1, "EST-B"),
        Reporte(3, 5.0, 10.0, 1.0, 1.0, fecha, 1, "EST-C"),
    ])
    generador = procesador.procesar_continuo()
    primero = next(generador)
    assert primero.identificador == 1
    assert arbol.cantidad_nodos() == 1  # SOLO se proceso un paso, no los tres
    segundo = next(generador)
    assert segundo.identificador == 2
    assert arbol.cantidad_nodos() == 2


def test_procesar_continuo_respeta_el_limite():
    procesador, arbol, *_ = _procesador()
    fecha = _utc(2026, 9, 19, 8, 0, 0)
    procesador.preparar_rafaga([
        Reporte(i, 5.0, 10.0, 1.0, 1.0, fecha, 1, "EST-A") for i in range(1, 6)
    ])
    pasos = list(procesador.procesar_continuo(limite=2))
    assert len(pasos) == 2
    assert arbol.cantidad_nodos() == 2


# --------------------------------------------------------------- undo ----

def test_deshacer_un_paso_restaura_arbol_y_posicion_en_la_cola():
    procesador, arbol, _, cola, pila, _ = _procesador()
    fecha = _utc(2026, 9, 19, 8, 0, 0)
    procesador.preparar_rafaga([
        Reporte(1, 5.0, 10.0, 1.0, 1.0, fecha, 1, "EST-A"),
        Reporte(2, 5.0, 10.0, 1.0, 1.0, fecha, 1, "EST-B"),
    ])
    procesador.procesar_un_paso()
    assert arbol.cantidad_nodos() == 1
    assert cola.cantidad_pendientes() == 1

    pila.deshacer()
    assert arbol.cantidad_nodos() == 0
    assert cola.cantidad_pendientes() == 2
    assert next(cola.en_orden()).identificador == 1  # vuelve exactamente al frente


def test_deshacer_un_paso_que_descarto_el_reporte_lo_devuelve_a_la_cola():
    """Caso critico de la seccion 13: 'incluso si ese paso habia
    descartado un reporte'. El arbol no cambia, pero la cola si, y
    deshacer debe devolver el reporte al frente de todas formas."""
    procesador, arbol, historico, cola, pila, servicio_eventos = _procesador()
    fecha = _utc(2026, 9, 19, 8, 0, 0)

    servicio_eventos.dar_alta_manual(1, 5.0, 10.0, 1.0, 1.0, fecha, "EST-A")
    tam_pila_antes = len(pila)

    reporte_viejo = Reporte(1, 9.0, 1.0, 1.0, 1.0, fecha, 0, "EST-B")  # revision 0 < 1
    procesador.preparar_rafaga([reporte_viejo])
    paso = procesador.procesar_un_paso()
    assert paso.resultado.tipo == TipoResultado.REPORTE_ANTIGUO
    assert cola.esta_vacia()  # el reporte SALIO de la cola aunque se rechazo
    assert len(pila) == tam_pila_antes + 1  # SI se registro una accion

    pila.deshacer()
    assert cola.cantidad_pendientes() == 1  # vuelve, aunque fue descartado
    assert next(cola.en_orden()).estacion == "EST-B"
    assert arbol.buscar_por_id(1).magnitud == 5.0  # el arbol seguia intacto igual


def test_deshacer_un_paso_con_reactivacion_restaura_el_historico():
    procesador, arbol, historico, cola, pila, servicio_eventos = _procesador()
    fecha = _utc(2026, 9, 19, 8, 0, 0)
    servicio_eventos.dar_alta_manual(1, 5.0, 10.0, 1.0, 1.0, fecha, "EST-A")
    servicio_eventos.eliminar_individual(1)  # pasa a "eliminados", no "archivados"
    historico.archivados[1] = historico.eliminados.pop(1)  # simular que fue archivado, no eliminado

    procesador.preparar_rafaga([
        Reporte(1, 6.0, 10.0, 1.0, 1.0, fecha, 2, "EST-B"),  # revision mayor -> reactiva
    ])
    paso = procesador.procesar_un_paso()
    assert paso.resultado.tipo == TipoResultado.REACTIVACION
    assert arbol.buscar_por_id(1) is not None
    assert not historico.esta_archivado(1)

    pila.deshacer()
    assert arbol.buscar_por_id(1) is None
    assert historico.esta_archivado(1)
    assert cola.cantidad_pendientes() == 1
