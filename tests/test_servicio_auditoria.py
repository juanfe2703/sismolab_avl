"""Tests for ServicioAuditoria. Run via run_tests.py."""
from datetime import datetime, timezone

from src.model import Prioridad
from src.services.servicio_auditoria import ServicioAuditoria
from src.structures import ClaveEvento

from .fakes import ArbolFalso


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


class _EventoSimple:
    def __init__(self, identificador):
        self.identificador = identificador


def _insertar(arbol, identificador, prioridad, magnitud):
    clave = ClaveEvento(prioridad, magnitud, identificador)
    arbol.insertar(clave, _EventoSimple(identificador))


def test_arbol_valido_en_modo_normal_no_tiene_problemas():
    arbol = ArbolFalso()
    # Orden de insercion elegido para que el fake (que no rota) quede
    # balanceado por si solo: raiz primero, luego menor y mayor.
    _insertar(arbol, 2, Prioridad.MEDIA, 5.0)
    _insertar(arbol, 1, Prioridad.BAJA, 1.0)
    _insertar(arbol, 3, Prioridad.ALTA, 7.0)
    reporte = ServicioAuditoria().verificar(arbol, modo_estres=False)
    assert reporte.ok
    assert reporte.problemas == []


def test_identidad_rota_detecta_evento_ref_desincronizado():
    arbol = ArbolFalso()
    _insertar(arbol, 1, Prioridad.BAJA, 1.0)
    # Rompemos la identidad a mano: el nodo dice ser el id 1 en su
    # clave pero su evento_ref apunta a otro id.
    arbol.obtener_raiz().evento_ref = _EventoSimple(99)
    reporte = ServicioAuditoria().verificar(arbol, modo_estres=False)
    assert not reporte.ok
    assert any("evento_ref" in p.descripcion for p in reporte.problemas)


def test_orden_global_roto_se_detecta():
    arbol = ArbolFalso()
    _insertar(arbol, 1, Prioridad.BAJA, 1.0)
    _insertar(arbol, 2, Prioridad.MEDIA, 5.0)
    # Rompemos el orden a mano: forzamos que el hijo derecho tenga una
    # clave MENOR que la raiz (viola BST).
    raiz = arbol.obtener_raiz()
    raiz.derecho.clave = ClaveEvento(Prioridad.BAJA, 0.5, 2)
    reporte = ServicioAuditoria().verificar(arbol, modo_estres=False)
    assert not reporte.ok
    assert any("orden global" in p.descripcion for p in reporte.problemas)


def test_desbalance_en_modo_estres_no_es_un_error():
    arbol = ArbolFalso()
    # Cadena hacia la derecha: desbalanceada a proposito.
    _insertar(arbol, 1, Prioridad.BAJA, 1.0)
    _insertar(arbol, 2, Prioridad.BAJA, 2.0)
    _insertar(arbol, 3, Prioridad.BAJA, 3.0)
    reporte_normal = ServicioAuditoria().verificar(arbol, modo_estres=False)
    assert not reporte_normal.ok
    assert any("factor de balance" in p.descripcion for p in reporte_normal.problemas)

    reporte_estres = ServicioAuditoria().verificar(arbol, modo_estres=True)
    assert reporte_estres.ok  # mismo arbol, pero el desbalance es esperado
    assert 1 in reporte_estres.nodos_en_desbalance_esperado
