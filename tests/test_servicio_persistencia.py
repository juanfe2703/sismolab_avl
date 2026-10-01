"""Tests for ServicioPersistencia. Run via run_tests.py (see repo
root) - no pytest available in this sandbox.
"""
import json
import os
import tempfile
from datetime import datetime, timezone

from src.persistence.servicio_persistencia import ServicioPersistencia
from src.services.escenario import Escenario, ParametrosEscenario, RelojSimulacion
from src.services.gestor_asociaciones import GestorAsociaciones
from src.services.historico import Historico
from src.services.servicio_eventos import ServicioEventos, TipoResultado
from src.services.zonas import VerificadorZonasRectangulares, ZonaRectangular
from src.undo.pila_deshacer import PilaDeshacer

from .fakes import ArbolFalso


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def _escenario_vacio(ahora=_utc(2026, 9, 19, 12, 0, 0)):
    arbol = ArbolFalso()
    historico = Historico()
    zonas = VerificadorZonasRectangulares([
        ZonaRectangular("Z1", 0.0, 0.0, 1000.0, 1000.0, poblada=True),
    ])
    gestor = GestorAsociaciones(arbol, historico)
    from src.services.cola_reportes import ColaReportes
    escenario = Escenario(
        arbol=arbol, historico=historico, gestor_asociaciones=gestor,
        cola=ColaReportes(), reloj=RelojSimulacion(ahora), zonas=zonas,
        estaciones=["EST-A", "EST-B"],
    )
    return escenario


def _servicio_persistencia(escenario, pila):
    return ServicioPersistencia(
        escenario, pila,
        fabrica_arbol_avl=ArbolFalso,
        fabrica_bst=ArbolFalso,  # el fake sirve igual para "BST"
    )


class _ArchivoTemporal:
    def __init__(self):
        fd, self.ruta = tempfile.mkstemp(suffix=".json")
        os.close(fd)

    def escribir(self, contenido: dict) -> None:
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(contenido, f)

    def leer(self) -> dict:
        with open(self.ruta, "r", encoding="utf-8") as f:
            return json.load(f)

    def borrar(self) -> None:
        if os.path.exists(self.ruta):
            os.remove(self.ruta)


# ------------------------------------------------------ carga por inserciones ----

def test_carga_por_inserciones_exitosa():
    escenario = _escenario_vacio()
    pila = PilaDeshacer()
    persistencia = _servicio_persistencia(escenario, pila)
    archivo = _ArchivoTemporal()
    try:
        archivo.escribir({
            "eventos": [
                {
                    "identificador": 1, "magnitud": 6.0, "profundidad_hipocentro": 10.0,
                    "epicentro_x": 100.0, "epicentro_y": 100.0,
                    "fecha_hora": "2026-09-19T08:00:00Z", "revision": 1,
                    "estado_atencion": "pendiente", "estaciones_reportes": ["EST-A"],
                },
                {
                    "identificador": 2, "magnitud": 4.0, "profundidad_hipocentro": 10.0,
                    "epicentro_x": 200.0, "epicentro_y": 200.0,
                    "fecha_hora": "2026-09-19T09:00:00Z", "revision": 1,
                    "estado_atencion": "pendiente", "estaciones_reportes": ["EST-B"],
                },
            ]
        })
        resultado = persistencia.cargar_por_inserciones(archivo.ruta)
        assert resultado.exito, resultado.errores
        assert escenario.arbol.cantidad_nodos() == 2
        assert escenario.bst_comparacion.cantidad_nodos() == 2
        assert len(pila) == 1
    finally:
        archivo.borrar()


def test_carga_por_inserciones_rechaza_id_duplicado_y_no_toca_nada():
    escenario = _escenario_vacio()
    pila = PilaDeshacer()
    persistencia = _servicio_persistencia(escenario, pila)
    archivo = _ArchivoTemporal()
    try:
        archivo.escribir({
            "eventos": [
                {
                    "identificador": 1, "magnitud": 6.0, "profundidad_hipocentro": 10.0,
                    "epicentro_x": 100.0, "epicentro_y": 100.0,
                    "fecha_hora": "2026-09-19T08:00:00Z", "revision": 1,
                    "estado_atencion": "pendiente", "estaciones_reportes": [],
                },
                {
                    "identificador": 1, "magnitud": 5.0, "profundidad_hipocentro": 10.0,
                    "epicentro_x": 100.0, "epicentro_y": 100.0,
                    "fecha_hora": "2026-09-19T08:00:00Z", "revision": 1,
                    "estado_atencion": "pendiente", "estaciones_reportes": [],
                },
            ]
        })
        resultado = persistencia.cargar_por_inserciones(archivo.ruta)
        assert not resultado.exito
        assert any("duplicado" in e for e in resultado.errores)
        assert escenario.arbol.cantidad_nodos() == 0  # nada se toco
        assert len(pila) == 0
    finally:
        archivo.borrar()


# ------------------------------------------------------- carga por topologia ----

def test_carga_por_topologia_valida_y_balanceada():
    escenario = _escenario_vacio()
    pila = PilaDeshacer()
    persistencia = _servicio_persistencia(escenario, pila)
    archivo = _ArchivoTemporal()
    evento_raiz = {
        "identificador": 10, "magnitud": 5.0, "profundidad_hipocentro": 10.0,
        "epicentro_x": 100.0, "epicentro_y": 100.0,
        "fecha_hora": "2026-09-19T08:00:00Z", "revision": 1,
        "estado_atencion": "pendiente", "estaciones_reportes": [],
    }
    # M=5.0, H=10.0, zona poblada => prioridad Alta (3) segun seccion 4.
    try:
        archivo.escribir({
            "modo": "normal",
            "raiz": "10",
            "nodos": {
                "10": {
                    "evento": evento_raiz,
                    "prioridad_almacenada": 3,
                    "altura_almacenada": 0,
                    "factor_balance_almacenado": 0,
                    "izquierdo": None, "derecho": None,
                },
            },
        })
        resultado = persistencia.cargar_por_topologia(archivo.ruta)
        assert resultado.exito, resultado.errores
        assert escenario.arbol.buscar_por_id(10) is not None
        assert escenario.arbol.modo_estres is False
    finally:
        archivo.borrar()


def test_carga_por_topologia_rechaza_prioridad_almacenada_incorrecta():
    escenario = _escenario_vacio()
    pila = PilaDeshacer()
    persistencia = _servicio_persistencia(escenario, pila)
    archivo = _ArchivoTemporal()
    try:
        archivo.escribir({
            "modo": "normal",
            "raiz": "10",
            "nodos": {
                "10": {
                    "evento": {
                        "identificador": 10, "magnitud": 7.0, "profundidad_hipocentro": 10.0,
                        "epicentro_x": 100.0, "epicentro_y": 100.0,
                        "fecha_hora": "2026-09-19T08:00:00Z", "revision": 1,
                        "estado_atencion": "pendiente", "estaciones_reportes": [],
                    },
                    "prioridad_almacenada": 1,  # M=7.0 es prioridad Alta (3), no Baja (1)
                    "altura_almacenada": 0,
                    "factor_balance_almacenado": 0,
                    "izquierdo": None, "derecho": None,
                },
            },
        })
        resultado = persistencia.cargar_por_topologia(archivo.ruta)
        assert not resultado.exito
        assert any("prioridad" in e for e in resultado.errores)
        assert escenario.arbol.cantidad_nodos() == 0
    finally:
        archivo.borrar()


def test_carga_por_topologia_rechaza_ciclo():
    escenario = _escenario_vacio()
    pila = PilaDeshacer()
    persistencia = _servicio_persistencia(escenario, pila)
    archivo = _ArchivoTemporal()
    evento_a = {
        "identificador": 1, "magnitud": 3.0, "profundidad_hipocentro": 10.0,
        "epicentro_x": 1.0, "epicentro_y": 1.0,
        "fecha_hora": "2026-09-19T08:00:00Z", "revision": 1,
        "estado_atencion": "pendiente", "estaciones_reportes": [],
    }
    evento_b = dict(evento_a, identificador=2, magnitud=2.0)
    try:
        archivo.escribir({
            "modo": "normal",
            "raiz": "1",
            "nodos": {
                # 1 -> derecho -> 2 -> derecho -> 1 (ciclo)
                "1": {"evento": evento_a, "prioridad_almacenada": 1,
                      "altura_almacenada": 1, "factor_balance_almacenado": -1,
                      "izquierdo": None, "derecho": "2"},
                "2": {"evento": evento_b, "prioridad_almacenada": 1,
                      "altura_almacenada": 0, "factor_balance_almacenado": 0,
                      "izquierdo": None, "derecho": "1"},
            },
        })
        resultado = persistencia.cargar_por_topologia(archivo.ruta)
        assert not resultado.exito
        # El ciclo 1->2->1 hace que la raiz aparezca como hijo de otro
        # nodo, lo cual el validador detecta en el paso de "una sola
        # posicion por nodo" (antes incluso de llegar al chequeo de
        # alcanzabilidad); el mensaje exacto varia segun donde el ciclo
        # toca la raiz, pero en ambos casos la carga se rechaza.
        assert any("raiz no puede ser hijo" in e or "ciclo" in e or "mas de un nodo" in e
                   for e in resultado.errores)
    finally:
        archivo.borrar()


def test_carga_por_topologia_desbalanceada_requiere_modo_estres():
    escenario = _escenario_vacio()
    pila = PilaDeshacer()
    persistencia = _servicio_persistencia(escenario, pila)
    archivo = _ArchivoTemporal()

    def _evento(i, m):
        return {
            "identificador": i, "magnitud": m, "profundidad_hipocentro": 10.0,
            "epicentro_x": 1.0, "epicentro_y": 1.0,
            "fecha_hora": "2026-09-19T08:00:00Z", "revision": 1,
            "estado_atencion": "pendiente", "estaciones_reportes": [],
        }

    # Cadena hacia la derecha 1 -> 2 -> 3 (todas prioridad Baja=1,
    # magnitudes ascendentes para respetar el orden BST): desbalanceada.
    documento = {
        "raiz": "1",
        "nodos": {
            "1": {"evento": _evento(1, 1.0), "prioridad_almacenada": 1,
                  "altura_almacenada": 2, "factor_balance_almacenado": -2,
                  "izquierdo": None, "derecho": "2"},
            "2": {"evento": _evento(2, 2.0), "prioridad_almacenada": 1,
                  "altura_almacenada": 1, "factor_balance_almacenado": -1,
                  "izquierdo": None, "derecho": "3"},
            "3": {"evento": _evento(3, 3.0), "prioridad_almacenada": 1,
                  "altura_almacenada": 0, "factor_balance_almacenado": 0,
                  "izquierdo": None, "derecho": None},
        },
    }
    try:
        archivo.escribir({**documento, "modo": "normal"})
        resultado = persistencia.cargar_por_topologia(archivo.ruta)
        assert not resultado.exito
        assert any("desbalanceada" in e for e in resultado.errores)

        archivo.escribir({**documento, "modo": "estres"})
        resultado = persistencia.cargar_por_topologia(archivo.ruta)
        assert resultado.exito, resultado.errores
        assert escenario.arbol.modo_estres is True
    finally:
        archivo.borrar()


# ------------------------------------------------------- guardado estructural ----

def test_guardado_y_carga_estructural_son_un_ciclo_completo():
    escenario = _escenario_vacio()
    pila = PilaDeshacer()
    persistencia = _servicio_persistencia(escenario, pila)
    servicio_eventos = ServicioEventos(
        escenario.arbol, escenario.historico, escenario.zonas, escenario.reloj,
        pila, escenario.gestor_asociaciones,
    )
    servicio_eventos.dar_alta_manual(1, 6.5, 10.0, 500.0, 500.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
    servicio_eventos.dar_alta_manual(2, 3.0, 10.0, 500.0, 500.0, _utc(2026, 9, 19, 9, 0, 0), "EST-B")
    servicio_eventos.eliminar_individual(2)
    escenario.metricas["altas_totales"] = 2

    archivo = _ArchivoTemporal()
    try:
        persistencia.guardar_estructural(archivo.ruta)

        escenario2 = _escenario_vacio()
        pila2 = PilaDeshacer()
        persistencia2 = _servicio_persistencia(escenario2, pila2)
        resultado = persistencia2.cargar_estructural(archivo.ruta)
        assert resultado.exito, resultado.errores

        assert escenario2.arbol.buscar_por_id(1) is not None
        assert escenario2.arbol.buscar_por_id(1).magnitud == 6.5
        assert escenario2.historico.esta_eliminado(2)
        assert escenario2.metricas["altas_totales"] == 2
        assert len(escenario2.zonas.zonas()) == 1
        assert escenario2.reloj.ahora() == escenario.reloj.ahora()
        assert len(pila2) == 1  # la carga es UNA accion deshacer

        # Deshacer la carga vuelve al escenario2 vacio de antes.
        pila2.deshacer()
        assert escenario2.arbol.buscar_por_id(1) is None
        assert not escenario2.historico.esta_eliminado(2)
    finally:
        archivo.borrar()


def test_carga_estructural_rechaza_identificadores_duplicados_entre_colecciones():
    escenario = _escenario_vacio()
    pila = PilaDeshacer()
    persistencia = _servicio_persistencia(escenario, pila)
    archivo = _ArchivoTemporal()

    evento = {
        "identificador": 5, "magnitud": 3.0, "profundidad_hipocentro": 10.0,
        "epicentro_x": 1.0, "epicentro_y": 1.0,
        "fecha_hora": "2026-09-19T08:00:00Z", "revision": 1,
        "estado_atencion": "pendiente", "estaciones_reportes": [],
    }
    try:
        archivo.escribir({
            "modo": "normal",
            "arbol": {
                "raiz": "5",
                "nodos": {"5": {"evento": evento, "prioridad_almacenada": 1,
                                "altura_almacenada": 0, "factor_balance_almacenado": 0,
                                "izquierdo": None, "derecho": None}},
            },
            "historico": {"archivados": [evento], "eliminados": []},  # mismo id 5
            "estaciones": [],
            "cola": [],
            "reloj": "2026-09-19T12:00:00Z",
            "zonas": [],
            "parametros": {"w_horas": 48.0, "r_km": 40.0, "l": 3, "t_horas": 72.0},
            "metricas": {},
        })
        resultado = persistencia.cargar_estructural(archivo.ruta)
        assert not resultado.exito
        assert any("duplicados" in e for e in resultado.errores)
        assert escenario.arbol.cantidad_nodos() == 0  # nada se toco
    finally:
        archivo.borrar()
