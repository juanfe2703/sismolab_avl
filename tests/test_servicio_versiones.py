"""Tests for ServicioVersiones. Run via run_tests.py (see repo root)."""
import shutil
import tempfile
from datetime import datetime, timezone

from src.persistence.servicio_persistencia import ServicioPersistencia
from src.persistence.servicio_versiones import ServicioVersiones
from src.services.cola_reportes import ColaReportes
from src.services.escenario import Escenario, RelojSimulacion
from src.services.gestor_asociaciones import GestorAsociaciones
from src.services.historico import Historico
from src.services.servicio_eventos import ServicioEventos
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
    return Escenario(
        arbol=arbol, historico=historico, gestor_asociaciones=gestor,
        cola=ColaReportes(), reloj=RelojSimulacion(ahora), zonas=zonas,
        estaciones=["EST-A"],
    )


def _montaje(directorio, escenario=None, pila=None):
    escenario = escenario or _escenario_vacio()
    pila = pila or PilaDeshacer()
    persistencia = ServicioPersistencia(
        escenario, pila, fabrica_arbol_avl=ArbolFalso, fabrica_bst=ArbolFalso,
    )
    versiones = ServicioVersiones(persistencia, directorio)
    servicio_eventos = ServicioEventos(
        escenario.arbol, escenario.historico, escenario.zonas, escenario.reloj,
        pila, escenario.gestor_asociaciones,
    )
    return escenario, pila, persistencia, versiones, servicio_eventos


class _DirectorioTemporal:
    def __enter__(self):
        self.ruta = tempfile.mkdtemp(prefix="sismolab_versiones_")
        return self.ruta

    def __exit__(self, *exc):
        shutil.rmtree(self.ruta, ignore_errors=True)


# ------------------------------------------------------- guardar/listar ----

def test_guardar_version_la_deja_disponible_en_listar():
    with _DirectorioTemporal() as directorio:
        escenario, pila, persistencia, versiones, eventos = _montaje(directorio)
        eventos.dar_alta_manual(1, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")

        versiones.guardar_version("antes del terremoto grande")

        listado = versiones.listar_versiones()
        assert len(listado) == 1
        assert listado[0].nombre == "antes del terremoto grande"


def test_guardar_version_no_requiere_que_el_nombre_sea_un_slug():
    """El nombre puede tener espacios, acentos, barras: la
    sanitizacion de archivo es un detalle interno, invisible al usuario."""
    with _DirectorioTemporal() as directorio:
        escenario, pila, persistencia, versiones, eventos = _montaje(directorio)
        versiones.guardar_version("v1 / sismo región sur")
        versiones.guardar_version("v2 / sismo región sur")  # casi igual, debe quedar aparte

        nombres = {v.nombre for v in versiones.listar_versiones()}
        assert nombres == {"v1 / sismo región sur", "v2 / sismo región sur"}


def test_guardar_version_con_nombre_vacio_falla():
    with _DirectorioTemporal() as directorio:
        _, _, _, versiones, _ = _montaje(directorio)
        try:
            versiones.guardar_version("   ")
            assert False, "debia lanzar ValueError"
        except ValueError:
            pass


def test_guardar_dos_veces_con_el_mismo_nombre_sobrescribe():
    with _DirectorioTemporal() as directorio:
        escenario, pila, persistencia, versiones, eventos = _montaje(directorio)
        eventos.dar_alta_manual(1, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
        versiones.guardar_version("snapshot")
        eventos.dar_alta_manual(2, 6.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 9, 0, 0), "EST-B")
        versiones.guardar_version("snapshot")  # mismo nombre, nuevo contenido

        assert len(versiones.listar_versiones()) == 1  # no se duplico la entrada

        escenario2, pila2, persistencia2, versiones2, _ = _montaje(directorio)
        resultado = versiones2.restaurar_version("snapshot")
        assert resultado.exito
        assert escenario2.arbol.buscar_por_id(2) is not None  # quedo la version mas reciente


# ------------------------------------------------------------- restaurar ----

def test_restaurar_version_es_una_accion_deshacer():
    with _DirectorioTemporal() as directorio:
        escenario, pila, persistencia, versiones, eventos = _montaje(directorio)
        eventos.dar_alta_manual(1, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
        versiones.guardar_version("con un evento")

        eventos.dar_alta_manual(2, 6.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 9, 0, 0), "EST-B")
        assert escenario.arbol.cantidad_nodos() == 2

        tam_pila_antes = len(pila)
        resultado = versiones.restaurar_version("con un evento")
        assert resultado.exito, resultado.errores
        assert escenario.arbol.cantidad_nodos() == 1
        assert escenario.arbol.buscar_por_id(1) is not None
        assert len(pila) == tam_pila_antes + 1

        pila.deshacer()
        assert escenario.arbol.cantidad_nodos() == 2  # vuelve a como estaba ANTES de restaurar


def test_restaurar_version_inexistente_no_falla_ni_toca_nada():
    with _DirectorioTemporal() as directorio:
        escenario, pila, persistencia, versiones, eventos = _montaje(directorio)
        eventos.dar_alta_manual(1, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
        tam_pila_antes = len(pila)

        resultado = versiones.restaurar_version("no existe")
        assert not resultado.exito
        assert escenario.arbol.cantidad_nodos() == 1  # sin cambios
        assert len(pila) == tam_pila_antes


# --------------------------------------------- persistencia entre "reinicios" ----

def test_version_sobrevive_a_un_reinicio_del_programa():
    """Simula cerrar el programa (descartar todos los objetos en
    memoria) y volver a abrirlo apuntando al mismo directorio."""
    with _DirectorioTemporal() as directorio:
        escenario1, pila1, persistencia1, versiones1, eventos1 = _montaje(directorio)
        eventos1.dar_alta_manual(42, 6.5, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
        versiones1.guardar_version("antes de cerrar")
        # "Cerrar el programa": se descartan escenario1/pila1/versiones1.
        del escenario1, pila1, persistencia1, versiones1, eventos1

        escenario2, pila2, persistencia2, versiones2, _ = _montaje(directorio)
        listado = versiones2.listar_versiones()
        assert any(v.nombre == "antes de cerrar" for v in listado)

        resultado = versiones2.restaurar_version("antes de cerrar")
        assert resultado.exito, resultado.errores
        assert escenario2.arbol.buscar_por_id(42) is not None
        assert escenario2.arbol.buscar_por_id(42).magnitud == 6.5


def test_version_no_contiene_la_pila_de_deshacer_ni_otras_versiones():
    """Section 13: 'No necesitan contener la pila de retroceso ni
    otras versiones.'"""
    with _DirectorioTemporal() as directorio:
        escenario, pila, persistencia, versiones, eventos = _montaje(directorio)
        eventos.dar_alta_manual(1, 5.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 8, 0, 0), "EST-A")
        eventos.dar_alta_manual(2, 6.0, 10.0, 1.0, 1.0, _utc(2026, 9, 19, 9, 0, 0), "EST-B")
        assert len(pila) == 2
        versiones.guardar_version("v1")
        versiones.guardar_version("v2")

        import json
        with open(versiones._ruta_indice(), "r", encoding="utf-8") as f:
            indice = json.load(f)
        ruta_v1 = f"{directorio}/{indice['versiones']['v1']['archivo']}"
        with open(ruta_v1, "r", encoding="utf-8") as f:
            contenido = json.load(f)
        assert "pila" not in contenido
        assert "versiones" not in contenido


# ------------------------------------------------------------- eliminar ----

def test_eliminar_version_la_quita_del_listado_y_del_disco():
    with _DirectorioTemporal() as directorio:
        escenario, pila, persistencia, versiones, eventos = _montaje(directorio)
        versiones.guardar_version("temporal")
        assert len(versiones.listar_versiones()) == 1

        assert versiones.eliminar_version("temporal") is True
        assert versiones.listar_versiones() == []
        assert versiones.eliminar_version("temporal") is False  # ya no existe
