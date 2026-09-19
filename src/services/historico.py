"""Historico: everything that left the active AVL but must still be
addressable (document, sections 6 and 10).

Two independent collections, on purpose, because they have different
rules:
    - `archivados`: events removed by "Archivar rama" (section 10).
      They keep their identity AND data, and a strictly-greater valid
      revision reactivates them as pendiente (section 6).
    - `eliminados`: events removed by individual deletion (section 6).
      Their id can NEVER be reused or reactivated by a later report;
      the document is explicit ("sus reportes posteriores se rechazan
      hasta deshacer esa eliminacion"). We still keep the data (not
      just the id) so `deshacer` can restore it exactly, and so a
      lookup can say "eliminado" instead of just "no encontrado".

Both are plain dicts keyed by `identificador`, not a third copy of the
AVL: this project does not need ordered access to the historico by K,
only point lookups by id, so a dict is the right (O(1)) structure and
does not compete with "the AVL is the central structure" requirement
in section 2, which only applies to the ACTIVE catalog.
"""
from __future__ import annotations

from copy import deepcopy

from src.model import Evento


class Historico:
    def __init__(self) -> None:
        self.archivados: dict[int, Evento] = {}
        self.eliminados: dict[int, Evento] = {}

    # ---------- archivados ----------

    def archivar(self, evento: Evento) -> None:
        self.archivados[evento.identificador] = evento

    def esta_archivado(self, identificador: int) -> bool:
        return identificador in self.archivados

    def obtener_archivado(self, identificador: int) -> Evento | None:
        return self.archivados.get(identificador)

    def reactivar(self, identificador: int) -> Evento:
        """Remove and return the archived event so the caller can move
        it back into the active AVL. Raises KeyError if not archived -
        callers must check `esta_archivado` first."""
        return self.archivados.pop(identificador)

    # ---------- eliminados ----------

    def eliminar(self, evento: Evento) -> None:
        self.eliminados[evento.identificador] = evento

    def esta_eliminado(self, identificador: int) -> bool:
        return identificador in self.eliminados

    def obtener_eliminado(self, identificador: int) -> Evento | None:
        return self.eliminados.get(identificador)

    def deshacer_eliminacion(self, identificador: int) -> Evento:
        """Used only by undo: pop the record back out of `eliminados`
        so the caller can reinsert it into the active AVL."""
        return self.eliminados.pop(identificador)

    # ---------- snapshot support (undo, section 13) ----------

    def clonar(self) -> "Historico":
        copia = Historico()
        copia.archivados = deepcopy(self.archivados)
        copia.eliminados = deepcopy(self.eliminados)
        return copia

    def restaurar_desde(self, otro: "Historico") -> None:
        """In-place overwrite, mirroring ArbolAVLProtocol.restaurar_desde
        - other components may hold a reference to this same object."""
        self.archivados = deepcopy(otro.archivados)
        self.eliminados = deepcopy(otro.eliminados)
