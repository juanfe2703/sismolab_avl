from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ResultadoBusqueda:
    """Outcome of a key lookup, with its simulated cost.

    `nodos_visitados` counts every node examined from the root
    (document, section 9). Callers may READ `nodo` but must not keep it:
    the physical position of an event can change with rotations.
    """

    nodo: Optional[Any]
    nodos_visitados: int

    @property
    def encontrado(self) -> bool:
        return self.nodo is not None

    @property
    def profundidad(self) -> Optional[int]:
        """Node depth (root = 0). Only defined when the key was found."""
        return self.nodos_visitados - 1 if self.encontrado else None