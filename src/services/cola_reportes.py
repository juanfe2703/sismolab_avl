"""Explicit FIFO queue for pending reports (document, section 8).

Backed by collections.deque, which CPython implements as a doubly
linked list of fixed-size blocks: append() and popleft() are both O(1)
amortized, unlike a plain list's pop(0), which is O(n) because every
remaining element has to shift. Since bursts can hold N stations'
worth of reports and we process/undo one at a time, O(1) enqueue and
dequeue matters.

The queue is NEVER reordered by priority: the document is explicit
that priority determines an event's position in the AVL, not its
position in the queue (section 8, 'La prioridad de un terremoto
determina su posicion en el AVL, no su posicion en la cola').
"""
from collections import deque
from typing import Iterator, Optional

from .reporte import Reporte


class ColaReportes:
    def __init__(self) -> None:
        self._cola: "deque[Reporte]" = deque()

    def encolar(self, reporte: Reporte) -> None:
        """O(1) amortized."""
        self._cola.append(reporte)

    def encolar_rafaga(self, reportes: list[Reporte]) -> None:
        """Enqueue several reports at once, preserving the given
        order. O(k) for k reportes."""
        self._cola.extend(reportes)

    def procesar_uno(self) -> Optional[Reporte]:
        """Pop and return the oldest pending report, or None if the
        queue is empty. O(1) amortized.

        The caller (ServicioEventos) is responsible for resolving the
        report and for recording the whole step as ONE undo action -
        this method only manages queue position."""
        if not self._cola:
            return None
        return self._cola.popleft()

    def reinsertar_al_frente(self, reporte: Reporte) -> None:
        """Used ONLY when undoing a processed step: restores the
        report to the exact front position it had before, even if that
        step had discarded it (a discarded report must come back too).
        O(1) amortized."""
        self._cola.appendleft(reporte)

    def esta_vacia(self) -> bool:
        return not self._cola

    def cantidad_pendientes(self) -> int:
        """O(1): deque tracks its own length."""
        return len(self._cola)

    def en_orden(self) -> Iterator[Reporte]:
        """Iterate front-to-back WITHOUT consuming the queue, for
        display and for structural export (section 12: 'Cola en su
        orden original'). O(n) to materialize, as any full listing
        must be."""
        return iter(self._cola)

    def a_lista(self) -> list[Reporte]:
        """Snapshot as a plain list, e.g. for JSON export or for an
        undo snapshot of the whole scenario."""
        return list(self._cola)

    @classmethod
    def desde_lista(cls, reportes: list[Reporte]) -> "ColaReportes":
        """Rebuild a queue in the exact given order (loading a saved
        scenario, or restoring an undo/version snapshot)."""
        cola = cls()
        cola._cola = deque(reportes)
        return cola
