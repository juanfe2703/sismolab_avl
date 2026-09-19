"""Tests for ServicioEventos against the fakes in tests/fakes.py.
Run with: python -m pytest tests/test_servicio_eventos.py -v
"""
from datetime import datetime, timezone

from src.model import EstadoAtencion, Prioridad
from src.services.historico import Historico
from src.services.reporte import Reporte
from src.services.servicio_eventos import EstadoEvento, ServicioEventos, TipoResultado
from src.undo.pila_deshacer import PilaDeshacer

from .fakes import ArbolFalso, RelojFalso, ZonaFalsa


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def _servicio(zona_poblada: bool = True, ahora=_utc(2026, 9, 19, 12, 0, 0)):
    arbol = ArbolFalso()
    historico = Historico()
    zona = ZonaFalsa(zona_poblada)
    reloj = RelojFalso(ahora)
    pila = PilaDeshacer()
    return ServicioEventos(arbol, historico, zona, reloj, pila), arbol, historico, pila


# ---------------------------------------------------------------- alta ----

def test_alta_manual_calcula_prioridad_segun_seccion_4():
    servicio, arbol, _, _ = _servicio(zona_poblada=True)
    r = servicio.dar_alta_manual(
        10, magnitud=4.5, profundidad_hipocentro=30.0,
        epicentro_x=500.0, epicentro_y=500.0,
        fecha_hora=_utc(2026, 9, 19, 10, 0, 0), estacion="EST-A",
    )
    assert r.tipo == TipoResultado.ALTA
    assert r.evento.estado_atencion == EstadoAtencion.PENDIENTE
    clave = arbol.buscar_por_id(10)
    assert clave is not None


def test_alta_manual_rechaza_id_duplicado():
    servicio, *_ = _servicio()
    servicio.dar_alta_manual(10, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 9, 0, 0), "EST-A")
    r = servicio.dar_alta_manual(10, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 9, 0, 0), "EST-A")
    assert r.tipo == TipoResultado.RECHAZADO_INVALIDO


# --------------------------------------------------------- reportes ----

def test_reporte_identificador_desconocido_es_alta():
    servicio, arbol, _, _ = _servicio()
    reporte = Reporte(20, 5.5, 15.0, 100.0, 100.0, _utc(2026, 9, 19, 10, 0, 0), 3, "EST-B")
    r = servicio.procesar_reporte(reporte)
    assert r.tipo == TipoResultado.ALTA
    assert r.evento.revision == 3  # "la primera revision recibida puede ser mayor que 1"


def test_reporte_revision_mayor_sustituye_datos():
    servicio, arbol, _, _ = _servicio()
    servicio.dar_alta_manual(30, 4.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
    reporte = Reporte(30, 6.2, 15.0, 200.0, 200.0, _utc(2026, 9, 19, 9, 0, 0), 2, "EST-B")
    r = servicio.procesar_reporte(reporte)
    assert r.tipo == TipoResultado.ACTUALIZACION
    assert r.evento.magnitud == 6.2
    assert r.evento.revision == 2
    assert arbol.buscar_por_id(30) is r.evento


def test_reporte_igual_revision_iguales_datos_confirma_y_no_duplica():
    servicio, arbol, _, _ = _servicio()
    fecha = _utc(2026, 9, 19, 8, 0, 0)
    servicio.dar_alta_manual(40, 5.0, 10.0, 1.0, 1.0, fecha, "EST-A")
    evento = arbol.buscar_por_id(40)
    reporte = Reporte(40, 5.0, 10.0, 1.0, 1.0, fecha, 1, "EST-A")  # misma estacion
    r1 = servicio.procesar_reporte(reporte)
    r2 = servicio.procesar_reporte(reporte)  # repetir no debe duplicar
    assert r1.tipo == TipoResultado.CONFIRMACION
    assert r2.tipo == TipoResultado.CONFIRMACION
    assert evento.estaciones_reportes == {"EST-A"}


def test_reporte_igual_revision_datos_distintos_es_conflicto():
    servicio, arbol, _, _ = _servicio()
    fecha = _utc(2026, 9, 19, 8, 0, 0)
    servicio.dar_alta_manual(50, 5.0, 10.0, 1.0, 1.0, fecha, "EST-A")
    reporte = Reporte(50, 5.9, 10.0, 1.0, 1.0, fecha, 1, "EST-B")
    r = servicio.procesar_reporte(reporte)
    assert r.tipo == TipoResultado.CONFLICTO
    assert arbol.buscar_por_id(50).magnitud == 5.0  # no se sobrescribio


def test_reporte_revision_menor_se_descarta():
    servicio, arbol, _, _ = _servicio()
    fecha = _utc(2026, 9, 19, 8, 0, 0)
    servicio.dar_alta_manual(60, 5.0, 10.0, 1.0, 1.0, fecha, "EST-A")
    evento = arbol.buscar_por_id(60)
    evento.revision = 5
    reporte = Reporte(60, 9.0, 1.0, 1.0, 1.0, fecha, 3, "EST-B")
    r = servicio.procesar_reporte(reporte)
    assert r.tipo == TipoResultado.REPORTE_ANTIGUO
    assert evento.magnitud == 5.0


def test_reporte_sobre_id_eliminado_se_bloquea():
    servicio, arbol, historico, _ = _servicio()
    fecha = _utc(2026, 9, 19, 8, 0, 0)
    servicio.dar_alta_manual(70, 5.0, 10.0, 1.0, 1.0, fecha, "EST-A")
    servicio.eliminar_individual(70)
    reporte = Reporte(70, 9.0, 1.0, 1.0, 1.0, fecha, 99, "EST-B")
    r = servicio.procesar_reporte(reporte)
    assert r.tipo == TipoResultado.RECHAZADO_ID_ELIMINADO
    assert arbol.buscar_por_id(70) is None


def test_reporte_reactiva_archivado_solo_con_revision_mayor():
    servicio, arbol, historico, _ = _servicio()
    fecha = _utc(2026, 9, 19, 8, 0, 0)
    servicio.dar_alta_manual(80, 5.0, 10.0, 1.0, 1.0, fecha, "EST-A")
    evento = arbol.buscar_por_id(80)
    clave = servicio._construir_clave(evento)
    historico.archivar(evento)
    arbol.eliminar(clave)

    reporte_viejo = Reporte(80, 5.0, 10.0, 1.0, 1.0, fecha, 1, "EST-B")
    r_no_reactiva = servicio.procesar_reporte(reporte_viejo)
    assert r_no_reactiva.tipo == TipoResultado.ARCHIVADO_SIN_REACTIVAR
    assert arbol.buscar_por_id(80) is None

    reporte_nuevo = Reporte(80, 6.5, 10.0, 1.0, 1.0, fecha, 2, "EST-C")
    r_reactiva = servicio.procesar_reporte(reporte_nuevo)
    assert r_reactiva.tipo == TipoResultado.REACTIVACION
    assert r_reactiva.evento.estado_atencion == EstadoAtencion.PENDIENTE
    assert arbol.buscar_por_id(80) is not None
    assert not historico.esta_archivado(80)


# ------------------------------------------------------------ correccion ----

def test_correccion_cambia_prioridad_y_reinserta_como_una_accion():
    """Caso obligatorio de la seccion 16: M=4.8/H=70.0 (prioridad 2) ->
    M=6.2/H=15.0 (prioridad 3)."""
    servicio, arbol, _, pila = _servicio()
    servicio.dar_alta_manual(90, 4.8, 70.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
    evento = arbol.buscar_por_id(90)
    assert evento.revision == 1

    tam_pila_antes = len(pila)
    r = servicio.corregir_manual(90, magnitud=6.2, profundidad_hipocentro=15.0)
    assert r.tipo == TipoResultado.CORRECCION_APLICADA
    assert r.evento.revision == 2
    assert r.evento.estado_atencion == EstadoAtencion.PENDIENTE
    assert len(pila) == tam_pila_antes + 1  # UNA sola accion, no varias

    clave = servicio._construir_clave(r.evento)
    assert clave.prioridad == Prioridad.ALTA
    assert arbol.buscar_por_id(90) is r.evento


def test_reporte_antiguo_despues_de_correccion_no_revierte_ni_duplica():
    servicio, arbol, _, _ = _servicio()
    fecha = _utc(2026, 9, 19, 8, 0, 0)
    servicio.dar_alta_manual(95, 4.8, 70.0, 1.0, 1.0, fecha, "EST-A")
    servicio.corregir_manual(95, magnitud=6.2, profundidad_hipocentro=15.0)
    evento = arbol.buscar_por_id(95)
    assert evento.revision == 2

    reporte_viejo = Reporte(95, 1.0, 1.0, 1.0, 1.0, fecha, 1, "EST-B")
    r = servicio.procesar_reporte(reporte_viejo)
    assert r.tipo == TipoResultado.REPORTE_ANTIGUO
    assert evento.magnitud == 6.2  # la correccion no se revierte
    assert arbol.cantidad_nodos() == 1  # no se creo un segundo nodo


def test_correccion_con_misma_clave_evita_retirar_reinsertar():
    servicio, arbol, _, _ = _servicio()
    servicio.dar_alta_manual(100, 3.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
    clave_antes = servicio._construir_clave(arbol.buscar_por_id(100))
    r = servicio.corregir_manual(100, epicentro_x=2.0)  # no cambia P ni M
    clave_despues = servicio._construir_clave(r.evento)
    assert clave_antes == clave_despues
    assert r.evento.revision == 2  # la revision SIEMPRE sube, aunque K no cambie


# ------------------------------------------------------- estado/eliminar ----

def test_marcar_revisado_no_cambia_clave():
    servicio, arbol, _, _ = _servicio()
    servicio.dar_alta_manual(110, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
    clave_antes = servicio._construir_clave(arbol.buscar_por_id(110))
    r = servicio.marcar_revisado(110)
    assert r.tipo == TipoResultado.MARCADO_REVISADO
    assert r.evento.estado_atencion == EstadoAtencion.REVISADO
    assert servicio._construir_clave(r.evento) == clave_antes


def test_eliminar_individual_bloquea_reportes_futuros():
    servicio, arbol, historico, _ = _servicio()
    servicio.dar_alta_manual(120, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
    r = servicio.eliminar_individual(120)
    assert r.tipo == TipoResultado.ELIMINADO
    assert historico.esta_eliminado(120)
    estado, _ = servicio.localizar_evento(120)
    assert estado == EstadoEvento.ELIMINADO


# --------------------------------------------------------------- undo ----

def test_undo_restaura_alta():
    servicio, arbol, historico, pila = _servicio()
    servicio.dar_alta_manual(130, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
    assert arbol.cantidad_nodos() == 1
    pila.deshacer()
    assert arbol.cantidad_nodos() == 0


def test_undo_restaura_correccion_completa_en_un_solo_paso():
    servicio, arbol, historico, pila = _servicio()
    servicio.dar_alta_manual(140, 4.8, 70.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
    servicio.corregir_manual(140, magnitud=6.2, profundidad_hipocentro=15.0)
    assert arbol.buscar_por_id(140).magnitud == 6.2

    pila.deshacer()  # deshace TODA la correccion, no una rotacion a la vez
    evento = arbol.buscar_por_id(140)
    assert evento.magnitud == 4.8
    assert evento.revision == 1


def test_undo_restaura_eliminacion():
    servicio, arbol, historico, pila = _servicio()
    servicio.dar_alta_manual(150, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
    servicio.eliminar_individual(150)
    assert historico.esta_eliminado(150)
    assert arbol.buscar_por_id(150) is None

    pila.deshacer()
    assert not historico.esta_eliminado(150)
    assert arbol.buscar_por_id(150) is not None


def test_reporte_conflicto_no_se_registra_en_la_pila_deshacer():
    servicio, arbol, _, pila = _servicio()
    fecha = _utc(2026, 9, 19, 8, 0, 0)
    servicio.dar_alta_manual(160, 5.0, 10.0, 1.0, 1.0, fecha, "EST-A")
    tam = len(pila)
    servicio.procesar_reporte(Reporte(160, 5.9, 10.0, 1.0, 1.0, fecha, 1, "EST-B"))
    assert len(pila) == tam  # el conflicto se rechazo, no hay nada que deshacer
