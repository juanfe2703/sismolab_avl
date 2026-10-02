"""ContextoApp: the one object every tab receives.

It only carries REFERENCES to already-built services plus a tiny
pub/sub for "something changed, please refresh your view" - it holds
no business logic itself, same rule as every tab module in this
package (section 2: 'debe haber una separacion de GUI y negocio').

Any tab that performs a mutating action calls `notificar_cambio()`
afterwards so every other open tab (catalogo, mapa, auditoria...) can
redraw itself from the now-current state, without tabs needing direct
references to each other.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from src.persistence.servicio_persistencia import ServicioPersistencia
from src.persistence.servicio_versiones import ServicioVersiones
from src.services.escenario import Escenario
from src.services.procesador_cola import ProcesadorCola
from src.services.servicio_auditoria import ServicioAuditoria
from src.services.servicio_eventos import ServicioEventos
from src.undo.pila_deshacer import PilaDeshacer


@dataclass
class ContextoApp:
    escenario: Escenario
    pila: PilaDeshacer
    servicio_eventos: ServicioEventos
    procesador_cola: ProcesadorCola
    servicio_persistencia: ServicioPersistencia
    servicio_versiones: ServicioVersiones
    servicio_auditoria: ServicioAuditoria
    _suscriptores: list[Callable[[], None]] = field(default_factory=list)

    @property
    def gestor_asociaciones(self):
        return self.escenario.gestor_asociaciones

    def suscribirse(self, callback: Callable[[], None]) -> None:
        """A tab calls this once, when it builds its widgets, to be
        told whenever another tab changes shared state."""
        self._suscriptores.append(callback)

    def notificar_cambio(self) -> None:
        for callback in self._suscriptores:
            callback()
