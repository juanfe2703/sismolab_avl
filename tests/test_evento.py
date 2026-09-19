from datetime import datetime, timezone

import pytest

from src.model import Evento, EstadoAtencion, ValorInvalidoError


def _evento_valido(**overrides):
    base = dict(
        identificador=10,
        magnitud=5.2,
        profundidad_hipocentro=15.0,
        epicentro_x=100.0,
        epicentro_y=200.0,
        fecha_hora=datetime(2026, 9, 7, 10, 0, 0, tzinfo=timezone.utc),
        revision=1,
    )
    base.update(overrides)
    return Evento(**base)


def test_evento_valido_se_crea_correctamente():
    evento = _evento_valido()
    assert evento.estado_atencion == EstadoAtencion.PENDIENTE
    assert evento.estaciones_reportes == set()


@pytest.mark.parametrize("identificador", [0, 1_000_000, -5])
def test_identificador_fuera_de_rango_falla(identificador):
    with pytest.raises(ValorInvalidoError):
        _evento_valido(identificador=identificador)


@pytest.mark.parametrize("magnitud", [-2.1, 10.1])
def test_magnitud_fuera_de_rango_falla(magnitud):
    with pytest.raises(ValorInvalidoError):
        _evento_valido(magnitud=magnitud)


def test_magnitud_con_mas_de_un_decimal_falla():
    with pytest.raises(ValorInvalidoError):
        _evento_valido(magnitud=5.25)


def test_magnitud_limite_inclusivo_es_valida():
    # limites del documento: -2.0 y 10.0 deben ser aceptados
    assert _evento_valido(magnitud=-2.0).magnitud == -2.0
    assert _evento_valido(magnitud=10.0).magnitud == 10.0


def test_profundidad_fuera_de_rango_falla():
    with pytest.raises(ValorInvalidoError):
        _evento_valido(profundidad_hipocentro=700.1)


def test_epicentro_fuera_de_rango_falla():
    with pytest.raises(ValorInvalidoError):
        _evento_valido(epicentro_x=1000.1)


def test_fecha_sin_zona_horaria_falla():
    with pytest.raises(ValorInvalidoError):
        _evento_valido(fecha_hora=datetime(2026, 9, 7, 10, 0, 0))


def test_revision_no_positiva_falla():
    with pytest.raises(ValorInvalidoError):
        _evento_valido(revision=0)