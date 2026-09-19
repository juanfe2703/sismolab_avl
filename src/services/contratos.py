"""Interfaces (contracts) this services layer depends on.

These are Protocols, not concrete classes: the actual AVL, BST and
zone-lookup implementations live in `structures` / `model` (built by
other teammates). Writing services against these contracts lets this
layer be developed and unit-tested with fakes before those pieces are
final, and lets teammates adjust their implementation independently as
long as it satisfies these method signatures.

If the real classes end up with different method names, only this file
(or a thin adapter around it) needs to change - not every service.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterator, Optional, Protocol, runtime_checkable

from src.model import Evento
from src.structures import ClaveEvento


@runtime_checkable
class ArbolBusquedaProtocol(Protocol):
    """Shared contract for the AVL and the comparison BST.

    Section 2 of the document forbids delegating tree operations to a
    library, so both are hand-implemented in `structures`, not here.
    """

    def insertar(self, clave: ClaveEvento, evento: Evento) -> int:
        """Insert `evento` under `clave`. Returns rotations performed
        (always 0 for the plain BST, which never rotates)."""
        ...

    def eliminar(self, clave: ClaveEvento) -> int:
        """Remove the node whose key is exactly `clave`. Returns
        rotations performed. Raises KeyError if not present."""
        ...

    def buscar_por_id(self, identificador: int) -> Optional[Evento]:
        """Locate the active event with this id. The tree orders by K,
        not by id, so this relies on whatever auxiliary index the
        `structures` team chose (to be documented/justified there,
        section 11: 'El equipo debe decidir como localizarlo
        eficientemente')."""
        ...

    def nodos_visitados_ultima_operacion(self) -> int:
        """Cost counter (section 11 / section 9): number of nodes
        visited by the most recent search/insert/delete call."""
        ...

    def recorrido_inorden(self) -> Iterator[Evento]: ...
    def recorrido_preorden(self) -> Iterator[Evento]: ...
    def recorrido_postorden(self) -> Iterator[Evento]: ...
    def recorrido_por_niveles(self) -> Iterator[Evento]: ...
    def altura(self) -> int: ...
    def cantidad_nodos(self) -> int: ...
    def cantidad_hojas(self) -> int: ...

    def clonar(self) -> "ArbolBusquedaProtocol":
        """Deep copy of the whole tree (nodes + evento references),
        used ONLY by the undo snapshot mechanism (section 13). O(n).

        Why the tree itself must support this, instead of `services`
        walking it from outside: only `structures` knows the real node
        layout (left/right/height/whatever balance bookkeeping the AVL
        keeps), so only it can copy that layout correctly and cheaply.
        `services` treats the result as an opaque snapshot.
        """
        ...

    def restaurar_desde(self, otro: "ArbolBusquedaProtocol") -> None:
        """Overwrite THIS tree's internal state with a deep copy of
        `otro`'s state, in place (does not rebind `self`). Required
        because other components (GUI, the future queue processor)
        hold a reference to this same tree object; undo must mutate
        what they are already pointing at, not swap it out from under
        them. This is the exact mirror of `clonar()`."""
        ...


@runtime_checkable
class ArbolAVLProtocol(ArbolBusquedaProtocol, Protocol):
    """The active-catalog AVL. Adds the deferred-balancing (modo
    estres) behaviour required by section 8, and the per-node depth
    query needed for the 'acceso costoso' marking in section 9."""

    modo_estres: bool

    def activar_modo_estres(self) -> None:
        """From now on, insert/delete keep BST order but do NOT
        rotate. The tree may stop satisfying the AVL property."""
        ...

    def recuperar_balance(self) -> int:
        """Detect every unbalanced node and rotate until the AVL
        property holds again, even where |factor_balance| > 2. Must
        terminate and preserve BST order (section 8). Returns total
        rotations performed and turns `modo_estres` back off."""
        ...

    def profundidad_de(self, identificador: int) -> int:
        """Depth of the node holding this id (root = 0)."""
        ...

    def factor_balance_de(self, identificador: int) -> int: ...


@runtime_checkable
class VerificadorZonaProtocol(Protocol):
    """Answers whether an epicenter falls in a populated zone, per the
    fixed rectangle geometry of section 3 (border belongs to the zone;
    a point on the border of two zones counts as populated if either
    of the two is populated). Implemented against the scenario's fixed
    zone list, not by this layer."""

    def es_zona_poblada(self, x: float, y: float) -> bool: ...


@runtime_checkable
class RelojSimulacionProtocol(Protocol):
    """The scenario's simulation clock (section 3): event occurrence
    times may never be later than this."""

    def ahora(self) -> datetime: ...
    def avanzar(self, nuevo_instante: datetime) -> None: ...
