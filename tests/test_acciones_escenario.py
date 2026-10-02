"""Tests for acciones_escenario. Run via run_tests.py."""
from datetime import datetime, timezone

from src.services.acciones_escenario import (
    avanzar_reloj,
    cambiar_parametros_asociacion,
    cambiar_parametros_generales,
)
from src.services.cola_reportes import ColaReportes
from src.services.escenario import Escenario, RelojSimulacion
from src.services.gestor_asociaciones import GestorAsociaciones
from src.services.historico import Historico
from src.services.zonas import VerificadorZonasRectangulares
from src.undo.pila_deshacer import PilaDeshacer

from .fakes import ArbolFalso


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def _escenario(ahora=_utc(2026, 9, 19, 12, 0, 0)):
    arbol = ArbolFalso()
    historico = Historico()
    gestor = GestorAsociaciones(arbol, historico)
    return Escenario(
        arbol=arbol, historico=historico, gestor_asociaciones=gestor,
        cola=ColaReportes(), reloj=RelojSimulacion(ahora),
        zonas=VerificadorZonasRectangulares([]), estaciones=[],
    )


def test_avanzar_reloj_es_undoable():
    escenario = _escenario()
    pila = PilaDeshacer()
    avanzar_reloj(escenario, pila, _utc(2026, 9, 20, 0, 0, 0))
    assert escenario.reloj.ahora() == _utc(2026, 9, 20, 0, 0, 0)
    assert len(pila) == 1

    pila.deshacer()
    assert escenario.reloj.ahora() == _utc(2026, 9, 19, 12, 0, 0)


def test_cambiar_parametros_asociacion_es_undoable_y_recalcula():
    escenario = _escenario()
    pila = PilaDeshacer()
    assert escenario.gestor_asociaciones.w_horas == 48.0

    cambiar_parametros_asociacion(escenario, pila, w_horas=10.0, r_km=5.0)
    assert escenario.gestor_asociaciones.w_horas == 10.0
    assert escenario.gestor_asociaciones.r_km == 5.0
    assert len(pila) == 1

    pila.deshacer()
    assert escenario.gestor_asociaciones.w_horas == 48.0
    assert escenario.gestor_asociaciones.r_km == 40.0


def test_cambiar_parametros_generales_es_undoable():
    escenario = _escenario()
    pila = PilaDeshacer()
    cambiar_parametros_generales(escenario, pila, limite_acceso_l=5, umbral_archivo_t_horas=100.0)
    assert escenario.parametros.limite_acceso_l == 5
    assert escenario.parametros.umbral_archivo_t_horas == 100.0

    pila.deshacer()
    assert escenario.parametros.limite_acceso_l == 3
    assert escenario.parametros.umbral_archivo_t_horas == 72.0
