"""Small, standalone undoable actions on the Escenario that do not
belong to ServicioEventos (document, section 13 lists 'cambio de
parametros' and 'avance del reloj' among the actions that must be
undoable, same as an alta or a correccion).

These exist here, as plain functions taking the escenario and the
pila explicitly, rather than as GUI code, because of section 2's
GUI/negocio split: even a one-line mutation like "set w_horas" must go
through something that knows how to snapshot and register undo for
it - the GUI is only allowed to trigger it and show the result.

Each function follows the exact same pattern already used everywhere
else: snapshot the smallest piece that changes, mutate, register.
"""
from __future__ import annotations

from datetime import datetime

from src.undo.pila_deshacer import PilaDeshacer

from .escenario import Escenario


def avanzar_reloj(escenario: Escenario, pila: PilaDeshacer, nuevo_instante: datetime) -> None:
    """Section 3: 'Su avance se realiza por una accion del usuario'.
    `RelojSimulacion.avanzar` itself already refuses to go backward;
    this only adds the undo registration around it."""
    snapshot = escenario.reloj.clonar()
    escenario.reloj.avanzar(nuevo_instante)
    pila.registrar(
        f"Avance del reloj a {nuevo_instante.isoformat()}",
        snapshot, escenario.reloj.restaurar_desde,
    )


def cambiar_parametros_asociacion(escenario: Escenario, pila: PilaDeshacer,
                                   w_horas: float | None = None,
                                   r_km: float | None = None) -> None:
    """Section 7: W and R changes must update the affected associations
    (already handled inside `cambiar_parametros` itself) AND must be
    undoable (section 13). `GestorAsociaciones.cambiar_parametros` only
    does the first half; this adds the second."""
    snapshot = escenario.gestor_asociaciones.clonar()
    escenario.gestor_asociaciones.cambiar_parametros(w_horas=w_horas, r_km=r_km)
    pila.registrar(
        f"Cambio de parametros W={escenario.gestor_asociaciones.w_horas}h, "
        f"R={escenario.gestor_asociaciones.r_km}km",
        snapshot, escenario.gestor_asociaciones.restaurar_desde,
    )


def cambiar_parametros_generales(escenario: Escenario, pila: PilaDeshacer,
                                  limite_acceso_l: int | None = None,
                                  umbral_archivo_t_horas: float | None = None) -> None:
    """L (section 9) and T (section 10). Kept here even though no
    service in this delivery consumes them yet (archivado masivo and
    la marca de acceso costoso are outside this assignment's scope) -
    the document still requires any parameter change to be undoable,
    so the plumbing is in place for whoever wires L/T to behavior."""
    from dataclasses import replace
    snapshot = replace(escenario.parametros)
    nuevos = replace(
        escenario.parametros,
        limite_acceso_l=limite_acceso_l if limite_acceso_l is not None
        else escenario.parametros.limite_acceso_l,
        umbral_archivo_t_horas=umbral_archivo_t_horas if umbral_archivo_t_horas is not None
        else escenario.parametros.umbral_archivo_t_horas,
    )
    escenario.parametros = nuevos
    pila.registrar(
        f"Cambio de parametros L={nuevos.limite_acceso_l}, T={nuevos.umbral_archivo_t_horas}h",
        snapshot, lambda anterior: setattr(escenario, "parametros", replace(anterior)),
    )
