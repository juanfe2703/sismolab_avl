"""Undo stack (document, section 13).

Design choice: full-STATE-SNAPSHOT commands, not inverse-operation
logs. Every business action - alta, correccion, eliminacion, archivo
masivo, cambio de parametros, avance del reloj, cambio de atencion,
carga, recuperacion global, un paso de cola, restaurar version - is
captured as ONE Comando whose `deshacer()` puts back the exact prior
snapshot (topologia, historico, cola, reloj, parametros, modo,
metricas) in a single call. Internal rotations triggered by a
correction or a mass archive are NEVER separately undoable, which is
exactly what section 13 requires ("Las inserciones y rotaciones
internas de una correccion o archivo masivo no se deshacen por
separado").


`EstadoRestaurable` is intentionally an opaque Protocol: this module
has zero knowledge of what a snapshot actually contains. The service
layer (ServicioEventos, etc.) decides what to capture and how to deep
copy it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class EstadoRestaurable(Protocol):
    """Marker only: a snapshot is whatever the caller says it is. This
    module never inspects it - it just holds it and hands it back."""
    ...


@dataclass
class Comando:
    """One undoable business action.

    `descripcion` feeds the visible action history (sections 13/14
    ask that the history explain how displayed metrics were reached).
    `snapshot_previo` was captured BEFORE the action ran; `restaurar`
    is the single callback that reinstates it.
    """
    descripcion: str
    snapshot_previo: EstadoRestaurable
    restaurar: Callable[[EstadoRestaurable], None]


class PilaDeshacer:
    """A plain Python list used as a stack: append/pop from the end
    are both O(1) amortized, which is all a LIFO undo history needs."""

    def __init__(self) -> None:
        self._pila: list[Comando] = []

    def registrar(self, descripcion: str, snapshot_previo: EstadoRestaurable,
                  restaurar: Callable[[EstadoRestaurable], None]) -> None:
        """Call this right after a service method finishes ONE
        business action successfully, passing the snapshot taken
        BEFORE that action was applied. If the action is rejected
        (invalid data, conflict, old report, unknown id to delete...)
        nothing is registered - there is nothing to undo."""
        self._pila.append(Comando(descripcion, snapshot_previo, restaurar))

    def deshacer(self) -> str:
        """Undo the most recent action and return its description.
        O(1) plus the cost of `restaurar` itself. Raises IndexError if
        the stack is empty - callers should check `puede_deshacer`
        first so the GUI can disable the button instead of catching."""
        comando = self._pila.pop()
        comando.restaurar(comando.snapshot_previo)
        return comando.descripcion

    def puede_deshacer(self) -> bool:
        return bool(self._pila)

    def historial_descripciones(self) -> list[str]:
        """Oldest first, for display in the action history panel."""
        return [c.descripcion for c in self._pila]

    def vaciar(self) -> None:
        """Called after loading a new scenario or restoring a named
        version (section 12/13): a fresh scenario starts a fresh undo
        history, it does not inherit the previous one's actions."""
        self._pila.clear()

    def __len__(self) -> int:
        return len(self._pila)
