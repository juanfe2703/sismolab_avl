"""Composition root (document, section 2's GUI/negocio split starts
here): this is the ONLY place in the whole project that decides which
concrete classes implement the Protocols every service was written
against. Every service module only ever imports `contratos` Protocols
or other services - never a concrete AVL. That design pays off here:
swapping `ArbolDemostracion` for the real AVL once `structures`
delivers it is a ONE-LINE change (the `fabrica_arbol_avl` argument
below), nothing else in this file or in any service needs to change.

Run with: python3 main.py (see repo root)
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.persistence.servicio_persistencia import ServicioPersistencia
from src.persistence.servicio_versiones import ServicioVersiones
from src.services.cola_reportes import ColaReportes
from src.services.escenario import Escenario, RelojSimulacion
from src.services.gestor_asociaciones import GestorAsociaciones
from src.services.historico import Historico
from src.services.procesador_cola import ProcesadorCola
from src.services.servicio_auditoria import ServicioAuditoria
from src.services.servicio_eventos import ServicioEventos
from src.services.zonas import VerificadorZonasRectangulares, ZonaRectangular
from src.undo.pila_deshacer import PilaDeshacer

from .arbol_demostracion import ArbolDemostracion
from .contexto import ContextoApp

# Tkinter (y ventana_principal, que lo importa) se cargan solo dentro
# de `iniciar()`, para que `construir_contexto()` - toda la composicion
# de servicios, sin nada visual - se pueda probar e importar incluso en
# un entorno sin Tkinter instalado.


def _escenario_inicial() -> Escenario:
    """Seed geometry/estaciones so the app has something to click on
    immediately. A real deployment would load these from a scenario
    file instead (section 3: zonas/estaciones are 'parametrizadas,
    pero inmutables durante la ejecucion') - this is just a starting
    point for manual testing."""
    zonas = VerificadorZonasRectangulares([
        ZonaRectangular("Zona-Urbana", 300.0, 300.0, 700.0, 700.0, poblada=True),
        ZonaRectangular("Zona-Rural", 0.0, 0.0, 1000.0, 1000.0, poblada=False),
    ])
    arbol = ArbolDemostracion()
    historico = Historico()
    gestor = GestorAsociaciones(arbol, historico)
    return Escenario(
        arbol=arbol,
        historico=historico,
        gestor_asociaciones=gestor,
        cola=ColaReportes(),
        reloj=RelojSimulacion(datetime.now(timezone.utc)),
        zonas=zonas,
        estaciones=["EST-NORTE", "EST-SUR", "EST-CENTRO"],
    )


def construir_contexto(directorio_versiones: str = "data/versiones") -> ContextoApp:
    escenario = _escenario_inicial()
    pila = PilaDeshacer()

    servicio_eventos = ServicioEventos(
        escenario.arbol, escenario.historico, escenario.zonas, escenario.reloj,
        pila, escenario.gestor_asociaciones,
    )
    procesador_cola = ProcesadorCola(escenario.cola, servicio_eventos, pila)
    servicio_persistencia = ServicioPersistencia(
        escenario, pila,
        fabrica_arbol_avl=ArbolDemostracion,  # <-- unico lugar a cambiar cuando llegue el AVL real
        fabrica_bst=ArbolDemostracion,
    )
    servicio_versiones = ServicioVersiones(servicio_persistencia, directorio_versiones)
    servicio_auditoria = ServicioAuditoria()

    return ContextoApp(
        escenario=escenario,
        pila=pila,
        servicio_eventos=servicio_eventos,
        procesador_cola=procesador_cola,
        servicio_persistencia=servicio_persistencia,
        servicio_versiones=servicio_versiones,
        servicio_auditoria=servicio_auditoria,
    )


def iniciar() -> None:
    import tkinter as tk

    from .ventana_principal import VentanaPrincipal

    contexto = construir_contexto()
    raiz = tk.Tk()
    raiz.title("SismoLab AVL")
    raiz.geometry("1100x700")
    VentanaPrincipal(raiz, contexto)
    raiz.mainloop()


if __name__ == "__main__":
    iniciar()
