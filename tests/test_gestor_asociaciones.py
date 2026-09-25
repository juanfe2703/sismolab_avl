"""Tests for GestorAsociaciones against the fakes in tests/fakes.py.
Run with: python3 run_tests.py (see repo root) or plug into pytest
once available in the real environment.
"""
from datetime import datetime, timezone

from src.services.estado_evento import EstadoEvento
from src.services.gestor_asociaciones import GestorAsociaciones
from src.services.historico import Historico

from .fakes import ArbolFalso


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


class _EventoSimple:
    """Local stand-in matching only the fields GestorAsociaciones reads,
    so these tests don't need to satisfy Evento's full validation
    (e.g. magnitudes/dates picked for the section 16 worked example)."""

    def __init__(self, identificador, magnitud, epicentro_x, epicentro_y, fecha_hora):
        self.identificador = identificador
        self.magnitud = magnitud
        self.epicentro_x = epicentro_x
        self.epicentro_y = epicentro_y
        self.fecha_hora = fecha_hora


def _gestor(w_horas=48.0, r_km=40.0):
    arbol = ArbolFalso()
    historico = Historico()
    gestor = GestorAsociaciones(arbol, historico, w_horas, r_km)
    return gestor, arbol, historico


def _insertar(arbol, evento):
    # ArbolFalso solo necesita una clave hashable y distinta por id;
    # el valor de la clave no importa para estas pruebas.
    arbol.insertar(("clave", evento.identificador), evento)


# --------------------------------------------------------- candidatos ----

def test_mayor_magnitud_antes_en_ventana_y_distancia_es_candidato():
    gestor, arbol, _ = _gestor()
    a = _EventoSimple(1, 6.0, 100.0, 100.0, _utc(2026, 9, 19, 8, 0, 0))
    b = _EventoSimple(2, 5.0, 110.0, 100.0, _utc(2026, 9, 19, 9, 0, 0))  # 1h despues, 10km
    _insertar(arbol, a)
    _insertar(arbol, b)
    gestor.recalcular_todas()
    assert gestor.referencia_elegida_de(2).identificador == 1


def test_menor_magnitud_no_es_candidato_aunque_este_cerca_y_antes():
    gestor, arbol, _ = _gestor()
    a = _EventoSimple(1, 4.0, 100.0, 100.0, _utc(2026, 9, 19, 8, 0, 0))
    b = _EventoSimple(2, 5.0, 100.0, 100.0, _utc(2026, 9, 19, 9, 0, 0))
    _insertar(arbol, a)
    _insertar(arbol, b)
    gestor.recalcular_todas()
    assert gestor.referencia_elegida_de(2) is None


def test_fuera_de_ventana_temporal_no_es_candidato():
    gestor, arbol, _ = _gestor(w_horas=1.0)
    a = _EventoSimple(1, 6.0, 100.0, 100.0, _utc(2026, 9, 19, 8, 0, 0))
    b = _EventoSimple(2, 5.0, 100.0, 100.0, _utc(2026, 9, 19, 10, 30, 0))  # 2.5h despues
    _insertar(arbol, a)
    _insertar(arbol, b)
    gestor.recalcular_todas()
    assert gestor.referencia_elegida_de(2) is None


def test_fuera_de_radio_no_es_candidato():
    gestor, arbol, _ = _gestor(r_km=10.0)
    a = _EventoSimple(1, 6.0, 0.0, 0.0, _utc(2026, 9, 19, 8, 0, 0))
    b = _EventoSimple(2, 5.0, 100.0, 100.0, _utc(2026, 9, 19, 9, 0, 0))  # muy lejos
    _insertar(arbol, a)
    _insertar(arbol, b)
    gestor.recalcular_todas()
    assert gestor.referencia_elegida_de(2) is None


def test_desempate_por_mayor_magnitud_primero():
    gestor, arbol, _ = _gestor()
    b = _EventoSimple(3, 3.0, 0.0, 0.0, _utc(2026, 9, 19, 12, 0, 0))
    fuerte = _EventoSimple(1, 7.0, 5.0, 5.0, _utc(2026, 9, 19, 10, 0, 0))
    debil_pero_cerca = _EventoSimple(2, 5.0, 0.5, 0.5, _utc(2026, 9, 19, 10, 0, 0))
    for e in (b, fuerte, debil_pero_cerca):
        _insertar(arbol, e)
    gestor.recalcular_todas()
    assert gestor.referencia_elegida_de(3).identificador == 1  # gana magnitud, no cercania


def test_desempate_por_menor_distancia_si_empata_magnitud():
    gestor, arbol, _ = _gestor()
    b = _EventoSimple(3, 3.0, 0.0, 0.0, _utc(2026, 9, 19, 12, 0, 0))
    lejos = _EventoSimple(1, 6.0, 30.0, 0.0, _utc(2026, 9, 19, 10, 0, 0))
    cerca = _EventoSimple(2, 6.0, 5.0, 0.0, _utc(2026, 9, 19, 10, 0, 0))
    for e in (b, lejos, cerca):
        _insertar(arbol, e)
    gestor.recalcular_todas()
    assert gestor.referencia_elegida_de(3).identificador == 2


# ------------------------------------------------------- historico/ids ----

def test_eliminado_no_es_candidato_ni_puede_ser_referenciado():
    gestor, arbol, historico = _gestor()
    a = _EventoSimple(1, 6.0, 0.0, 0.0, _utc(2026, 9, 19, 8, 0, 0))
    b = _EventoSimple(2, 5.0, 0.0, 0.0, _utc(2026, 9, 19, 9, 0, 0))
    _insertar(arbol, b)
    historico.eliminar(a)  # 'a' esta eliminado, no en el arbol ni archivado
    gestor.recalcular_todas()
    assert gestor.referencia_elegida_de(2) is None


def test_archivado_si_puede_ser_candidato():
    gestor, arbol, historico = _gestor()
    a = _EventoSimple(1, 6.0, 0.0, 0.0, _utc(2026, 9, 19, 8, 0, 0))
    b = _EventoSimple(2, 5.0, 0.0, 0.0, _utc(2026, 9, 19, 9, 0, 0))
    historico.archivar(a)
    _insertar(arbol, b)
    gestor.recalcular_todas()
    assert gestor.referencia_elegida_de(2).identificador == 1
    assert gestor.estado_de(1) == EstadoEvento.ARCHIVADO


def test_eventos_que_usan_como_referencia():
    gestor, arbol, _ = _gestor()
    a = _EventoSimple(1, 6.0, 0.0, 0.0, _utc(2026, 9, 19, 8, 0, 0))
    b = _EventoSimple(2, 5.0, 0.0, 0.0, _utc(2026, 9, 19, 9, 0, 0))
    c = _EventoSimple(3, 4.0, 0.0, 0.0, _utc(2026, 9, 19, 9, 30, 0))
    for e in (a, b, c):
        _insertar(arbol, e)
    gestor.recalcular_todas()
    referenciadores = {e.identificador for e in gestor.eventos_que_usan_como_referencia(1)}
    assert referenciadores == {2, 3}


# ------------------------------------------------------ caso seccion 16 ----

def test_reporte_tardio_caso_obligatorio_seccion_16():
    """5.6 a las 10:00 y 4.2 a las 10:20; luego llega 6.1 ocurrido a las
    09:55 (antes que ambos). El evento de 6.1 debe aparecer como
    candidato de los otros dos, y ser elegido si es el mejor."""
    gestor, arbol, _ = _gestor()
    e_56 = _EventoSimple(1, 5.6, 0.0, 0.0, _utc(2026, 9, 19, 10, 0, 0))
    e_42 = _EventoSimple(2, 4.2, 1.0, 1.0, _utc(2026, 9, 19, 10, 20, 0))
    _insertar(arbol, e_56)
    _insertar(arbol, e_42)
    gestor.recalcular_todas()
    assert gestor.referencia_elegida_de(1) is None  # nadie mas fuerte y antes, todavia
    # e_42 (4.2, 10:20) SI tiene a e_56 (5.6, 10:00) como candidato:
    # mayor magnitud y antes en el tiempo.
    assert gestor.referencia_elegida_de(2).identificador == 1

    # Llega tardiamente el evento de mayor magnitud, ocurrido antes que
    # los dos.
    e_61 = _EventoSimple(3, 6.1, 0.5, 0.5, _utc(2026, 9, 19, 9, 55, 0))
    _insertar(arbol, e_61)
    gestor.recalcular_todas()

    candidatos_de_56 = {e.identificador for e in gestor.candidatos_de(e_56)}
    candidatos_de_42 = {e.identificador for e in gestor.candidatos_de(e_42)}
    assert candidatos_de_56 == {3}
    assert 3 in candidatos_de_42

    # 6.1 gana por magnitud sobre 5.6 como referencia de 4.2.
    assert gestor.referencia_elegida_de(2).identificador == 3
    # Y ahora 5.6 (que antes no tenia referencia) si tiene una.
    assert gestor.referencia_elegida_de(1).identificador == 3


# --------------------------------------------------------- parametros ----

def test_cambiar_r_reduce_candidatos():
    gestor, arbol, _ = _gestor(r_km=100.0)
    a = _EventoSimple(1, 6.0, 0.0, 0.0, _utc(2026, 9, 19, 8, 0, 0))
    b = _EventoSimple(2, 5.0, 50.0, 0.0, _utc(2026, 9, 19, 9, 0, 0))
    _insertar(arbol, a)
    _insertar(arbol, b)
    gestor.recalcular_todas()
    assert gestor.referencia_elegida_de(2).identificador == 1

    gestor.cambiar_parametros(r_km=10.0)
    assert gestor.referencia_elegida_de(2) is None
