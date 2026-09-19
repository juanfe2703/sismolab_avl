import pytest

from src.model import Prioridad
from src.structures import ClaveEvento, comparar_claves


def _clave(prioridad_valor: int, magnitud: float, identificador: int) -> ClaveEvento:
    prioridad = {1: Prioridad.BAJA, 2: Prioridad.MEDIA, 3: Prioridad.ALTA}[prioridad_valor]
    return ClaveEvento(prioridad, magnitud, identificador)


BASE = _clave(3, 5.2, 10)


@pytest.mark.parametrize(
    "entrante, resultado_esperado, motivo",
    [
        (_clave(2, 5.8, 20), -1, "prioridad 2 < 3, aunque magnitud sea mayor"),
        (_clave(3, 6.1, 30), 1, "empatan prioridad, 6.1 > 5.2"),
        (_clave(3, 5.2, 5), -1, "empatan prioridad y magnitud, 5 < 10"),
        (_clave(3, 5.2, 25), 1, "empatan prioridad y magnitud, 25 > 10"),
        (_clave(3, 5.2, 10), 0, "misma clave exacta"),
    ],
)
def test_ejemplos_del_documento(entrante, resultado_esperado, motivo):
    assert comparar_claves(entrante, BASE) == resultado_esperado, motivo


def test_comparacion_es_antisimetrica():
    a = _clave(2, 5.8, 20)
    b = BASE
    assert comparar_claves(a, b) == -comparar_claves(b, a)


def test_prioridad_tiene_precedencia_absoluta():
    # magnitud e identificador muy superiores no deberian compensar prioridad menor
    baja_magnitud_alta_id = _clave(1, 9.9, 999_999)
    alta_prioridad_minima = _clave(3, -2.0, 1)
    assert comparar_claves(baja_magnitud_alta_id, alta_prioridad_minima) == -1