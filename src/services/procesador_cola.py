"""ProcesadorCola (document, section 8: 'Recepcion mediante cola y
modo estres').

This is a thin orchestrator on top of two already-built pieces:
`ColaReportes` (FIFO position) and `ServicioEventos._resolver_reporte`
(business-rule resolution). It exists because a queue *step* is not
the same undoable unit as a standalone `ServicioEventos.procesar_reporte`
call - section 13 requires a step to restore BOTH the scenario and the
report's queue position in one action, "incluso si ese paso habia
descartado un reporte". That last clause is the key difference from
`procesar_reporte`:

    - `ServicioEventos.procesar_reporte` (standalone report, not from a
      queue) skips registering undo when the report is rejected,
      because nothing changed.
    - `ProcesadorCola.procesar_un_paso` ALWAYS registers one Comando
      per step, rejected or not - because the queue itself changed
      (the report left the front of the line) even when the tree did
      not. Undoing a step must put the report back, whatever the
      resolution was.

This is also why this module reaches into
`ServicioEventos._resolver_reporte` / `._snapshot()` / `._restaurar()`,
which look private: `ServicioEventos.procesar_reporte`'s own docstring
already flags this exact coupling as intentional, precisely so this
module would not have to duplicate report-resolution logic or
re-implement snapshotting.

Pacing ("pausa entre pasos", section 8) is deliberately NOT implemented
here with a sleep/timer: that is a GUI concern (section 2's GUI/negocio
split). `procesar_continuo` is a generator that performs exactly one
step per `next()` call; the GUI controls the pause by how often it
asks for the next one (e.g. via Tkinter's `after`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

from src.undo.pila_deshacer import PilaDeshacer

from .cola_reportes import ColaReportes
from .reporte import Reporte
from .servicio_eventos import ResultadoOperacion, ServicioEventos


@dataclass
class ResultadoPaso:
    """One step's outcome, with everything section 8 asks to display:
    'la estacion, el evento, la revision, la decision tomada y las
    rotaciones producidas'."""
    hubo_reporte: bool
    mensaje: str
    estacion: Optional[str] = None
    identificador: Optional[int] = None
    revision: Optional[int] = None
    resultado: Optional[ResultadoOperacion] = None

    @property
    def rotaciones(self) -> int:
        return self.resultado.rotaciones if self.resultado is not None else 0


@dataclass
class _SnapshotPaso:
    """Opaque to PilaDeshacer. Pairs a ServicioEventos-level snapshot
    (arbol+historico+asociaciones) with the exact report that was
    popped, so undo can restore both at once."""
    snapshot_eventos: object
    reporte: Reporte


class ProcesadorCola:
    def __init__(self, cola: ColaReportes, servicio_eventos: ServicioEventos,
                 pila_deshacer: PilaDeshacer) -> None:
        self._cola = cola
        self._servicio_eventos = servicio_eventos
        self._pila = pila_deshacer

    # ------------------------------------------------------------------
    # Preparar una rafaga (section 8). NO es una accion de deshacer:
    # section 13 solo lista "un paso de procesamiento de la cola" entre
    # las acciones undoable, nunca "encolar". Encolar no cambia nada
    # del escenario que el undo deba proteger, solo agrega trabajo
    # pendiente.
    # ------------------------------------------------------------------

    def preparar_rafaga(self, reportes: list[Reporte]) -> None:
        self._cola.encolar_rafaga(reportes)

    # ------------------------------------------------------------------
    # Procesamiento de un paso (section 8 + 13)
    # ------------------------------------------------------------------

    def procesar_un_paso(self) -> ResultadoPaso:
        if self._cola.esta_vacia():
            return ResultadoPaso(hubo_reporte=False, mensaje="No hay reportes pendientes en la cola.")

        # Snapshot ANTES de sacar el reporte de la cola, para que
        # deshacer no solo restaure el arbol/historico/asociaciones
        # sino tambien la posicion exacta del reporte en la cola.
        snapshot_eventos = self._servicio_eventos._snapshot()
        reporte = self._cola.procesar_uno()
        resultado = self._servicio_eventos._resolver_reporte(reporte)

        snapshot_paso = _SnapshotPaso(snapshot_eventos=snapshot_eventos, reporte=reporte)
        self._pila.registrar(
            f"Paso de cola: reporte de {reporte.estacion} sobre el evento "
            f"{reporte.identificador} (revision {reporte.revision}) -> "
            f"{resultado.tipo.name}",
            snapshot_paso, self._restaurar_paso,
        )

        return ResultadoPaso(
            hubo_reporte=True,
            mensaje=resultado.mensaje,
            estacion=reporte.estacion,
            identificador=reporte.identificador,
            revision=reporte.revision,
            resultado=resultado,
        )

    def _restaurar_paso(self, snapshot_paso: _SnapshotPaso) -> None:
        self._servicio_eventos._restaurar(snapshot_paso.snapshot_eventos)
        # Se reinserta SIEMPRE al frente, incluso si el reporte habia
        # sido rechazado (conflicto, antiguo, id eliminado...): la
        # cola tambien se restaura a su posicion exacta de antes,
        # como exige la seccion 13.
        self._cola.reinsertar_al_frente(snapshot_paso.reporte)

    # ------------------------------------------------------------------
    # Procesamiento continuo con pausa (section 8)
    # ------------------------------------------------------------------

    def procesar_continuo(self, limite: Optional[int] = None) -> Iterator[ResultadoPaso]:
        """A generator, not a loop that runs to completion: each
        `next()` performs exactly one step (one undo Comando). The
        caller (the GUI) decides how many steps to pull and how much
        time to leave between them - e.g. `root.after(500, lambda:
        next(generador, None))` - so the pacing lives entirely in the
        GUI layer, never here.

        Stops when the queue is empty or `limite` steps were taken,
        whichever comes first. Does NOT itself re-raise or swallow
        errors from `procesar_un_paso`; there are none to catch, since
        an invalid report resolves to a rejection result, not an
        exception (section 6's rejections are ordinary outcomes)."""
        realizados = 0
        while not self._cola.esta_vacia() and (limite is None or realizados < limite):
            yield self.procesar_un_paso()
            realizados += 1
