"""GestorAsociaciones: candidate detection and deterministic reference
selection between events (document, section 7).

Rule (section 7): event A is a candidate reference for event B when
    - A.magnitud > B.magnitud (strictly greater)
    - A occurred strictly before B (A.fecha_hora < B.fecha_hora)
    - the time gap is at most W hours
    - the epicenter distance is at most R km (euclidean, in-plane)
Only active and archived events are considered; eliminated ones never
are (section 7: 'Se consideran eventos activos y archivados, pero no
eliminados'). Each B keeps at most one chosen reference (a "posible
replica" link); if there are no candidates, B has none.

Open decisions NOT fixed by the document, documented here as section 2
requires for every open decision:

1. Tie-break when B has several candidates. We chose, in this order:
   (1) greater magnitude, (2) smaller epicentral distance, (3) smaller
   time gap, (4) smaller identificador as a final, purely-technical
   tie-break so the result never depends on iteration order. This
   depends ONLY on the events' own data, never on arrival order or AVL
   topology, satisfying section 7's requirement for a deterministic,
   data-driven criterion.

2. Recompute strategy. Whenever an alta, a correccion, an eliminacion,
   or a change to W/R happens, EVERY event's reference is recomputed
   from scratch (`recalcular_todas`), instead of trying to identify
   only the "affected" events incrementally.
       Why: a single alta can change the best reference for OTHER,
       unrelated events too - a new, larger, well-placed event can
       outrank an existing reference for several B's at once, and
       deleting someone's reference can promote a different event's
       second-best candidate. Proving an incremental update touches
       exactly that set, and only that set, is easy to get subtly
       wrong. A full recompute is trivially correct by construction.
       Cost: O(n^2) worst case (each of n events scans up to n
       others). For this lab's scale this is an accepted, documented
       trade-off; the discarded alternative - maintaining per-event
       candidate sets incrementally - is asymptotically better but
       requires much more bookkeeping and is far easier to get wrong.

3. Cycles. Structurally impossible without any extra bookkeeping: a
   candidate must have occurred STRICTLY before the event it
   references, so a chain of references is a chain of strictly
   decreasing occurrence times. Such a chain cannot loop back to an
   event that occurred later than itself, so no cycle-detection code
   is needed - it follows from the temporal ordering rule itself.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import hypot
from typing import Iterator, Optional

from src.model import Evento

from .contratos import ArbolBusquedaProtocol
from .estado_evento import EstadoEvento
from .historico import Historico


@dataclass
class ResultadoAsociacion:
    """Return shape for section 11's association query: 'Candidatos y
    referencia elegida para un evento, asi como los eventos que lo
    utilizan como referencia. Se identifica si cada resultado esta
    activo o archivado.'"""
    evento: Evento
    candidatos: list[tuple[Evento, EstadoEvento]]
    referencia_elegida: Optional[tuple[Evento, EstadoEvento]]
    eventos_que_lo_referencian: list[tuple[Evento, EstadoEvento]]


class GestorAsociaciones:
    def __init__(self, arbol: ArbolBusquedaProtocol, historico: Historico,
                 w_horas: float = 48.0, r_km: float = 40.0) -> None:
        if w_horas <= 0 or r_km <= 0:
            raise ValueError("W y R deben ser positivos (section 7)")
        self._arbol = arbol
        self._historico = historico
        self.w_horas = w_horas
        self.r_km = r_km
        # id de B -> id de A elegido como su referencia. Solo contiene
        # entradas para los B que SI tienen una referencia elegida.
        self._referencia_elegida: dict[int, int] = {}

    # ------------------------------------------------------------------
    # Fuente de eventos considerados: activos + archivados, nunca
    # eliminados (section 7).
    # ------------------------------------------------------------------

    def _eventos_considerados(self) -> Iterator[Evento]:
        yield from self._arbol.recorrido_inorden()
        yield from self._historico.archivados.values()

    def _buscar_por_id(self, identificador: int) -> Optional[Evento]:
        for evento in self._eventos_considerados():
            if evento.identificador == identificador:
                return evento
        return None

    def estado_de(self, identificador: int) -> EstadoEvento:
        if self._arbol.buscar_por_id(identificador) is not None:
            return EstadoEvento.ACTIVO
        if self._historico.esta_archivado(identificador):
            return EstadoEvento.ARCHIVADO
        if self._historico.esta_eliminado(identificador):
            return EstadoEvento.ELIMINADO
        return EstadoEvento.DESCONOCIDO

    # ------------------------------------------------------------------
    # Distancia y candidatos
    # ------------------------------------------------------------------

    @staticmethod
    def _distancia(a: Evento, b: Evento) -> float:
        """Euclidean distance in the scenario's plane (section 7: 'Se
        usa distancia euclidiana en el plano del escenario')."""
        return hypot(a.epicentro_x - b.epicentro_x, a.epicentro_y - b.epicentro_y)

    def _es_candidato(self, a: Evento, b: Evento) -> bool:
        if a.identificador == b.identificador:
            return False
        if not (a.magnitud > b.magnitud):
            return False
        if not (a.fecha_hora < b.fecha_hora):
            return False
        diferencia_horas = (b.fecha_hora - a.fecha_hora).total_seconds() / 3600.0
        if diferencia_horas > self.w_horas:
            return False
        if self._distancia(a, b) > self.r_km:
            return False
        return True

    def candidatos_de(self, evento_b: Evento) -> list[Evento]:
        """O(n) over the considered events: a full scan, honestly
        documented rather than assumed logarithmic (section 11 warns
        explicitly against that assumption for any query)."""
        return [a for a in self._eventos_considerados() if self._es_candidato(a, evento_b)]

    def _elegir_mejor(self, candidatos: list[Evento], evento_b: Evento) -> Optional[Evento]:
        if not candidatos:
            return None

        def clave_orden(a: Evento):
            distancia = self._distancia(a, evento_b)
            diferencia_horas = (evento_b.fecha_hora - a.fecha_hora).total_seconds() / 3600.0
            # Orden ascendente en esta tupla = mejor candidato primero:
            # mayor magnitud (de ahi el signo), luego menor distancia,
            # luego menor diferencia temporal, y por ultimo menor
            # identificador como desempate final, puramente tecnico y
            # totalmente determinista.
            return (-a.magnitud, distancia, diferencia_horas, a.identificador)

        return min(candidatos, key=clave_orden)

    # ------------------------------------------------------------------
    # Recalculo (llamado por ServicioEventos tras alta / correccion /
    # eliminacion, y aqui mismo tras un cambio de W o R - section 7)
    # ------------------------------------------------------------------

    def recalcular_todas(self) -> None:
        nueva: dict[int, int] = {}
        for evento_b in self._eventos_considerados():
            mejor = self._elegir_mejor(self.candidatos_de(evento_b), evento_b)
            if mejor is not None:
                nueva[evento_b.identificador] = mejor.identificador
        self._referencia_elegida = nueva

    def cambiar_parametros(self, w_horas: Optional[float] = None,
                            r_km: Optional[float] = None) -> None:
        """Section 7: 'W = 48 horas y R = 40 km; ambos son positivos y
        modificables por el usuario.' Any change forces a full
        recompute, same as an alta/correccion/eliminacion."""
        if w_horas is not None:
            if w_horas <= 0:
                raise ValueError("W debe ser positivo")
            self.w_horas = w_horas
        if r_km is not None:
            if r_km <= 0:
                raise ValueError("R debe ser positivo")
            self.r_km = r_km
        self.recalcular_todas()

    # ------------------------------------------------------------------
    # Consultas (section 11)
    # ------------------------------------------------------------------

    def referencia_elegida_de(self, identificador: int) -> Optional[Evento]:
        id_referencia = self._referencia_elegida.get(identificador)
        return self._buscar_por_id(id_referencia) if id_referencia is not None else None

    def eventos_que_usan_como_referencia(self, identificador: int) -> list[Evento]:
        """O(n): scans the reference map. No incremental reverse index
        is kept, because `recalcular_todas` already rebuilds the whole
        forward map on every relevant change; a reverse index would be
        extra state to keep in sync for a query that is O(n) in the
        worst case regardless (up to n events could all reference the
        same one)."""
        ids = {id_b for id_b, id_a in self._referencia_elegida.items() if id_a == identificador}
        return [e for e in self._eventos_considerados() if e.identificador in ids]

    def consultar(self, identificador: int) -> Optional[ResultadoAsociacion]:
        evento_b = self._buscar_por_id(identificador)
        if evento_b is None:
            return None

        referencia = self.referencia_elegida_de(identificador)
        return ResultadoAsociacion(
            evento=evento_b,
            candidatos=[(e, self.estado_de(e.identificador))
                        for e in self.candidatos_de(evento_b)],
            referencia_elegida=(referencia, self.estado_de(referencia.identificador))
            if referencia is not None else None,
            eventos_que_lo_referencian=[
                (e, self.estado_de(e.identificador))
                for e in self.eventos_que_usan_como_referencia(identificador)
            ],
        )

    # ------------------------------------------------------------------
    # Snapshot support (se integra a la pila de deshacer de
    # ServicioEventos, section 13). Solo el mapa de referencias y los
    # parametros W/R son estado propio de este gestor: arbol e
    # historico son recursos compartidos que ServicioEventos snapshotea
    # por su cuenta.
    # ------------------------------------------------------------------

    def clonar(self) -> "GestorAsociaciones":
        copia = GestorAsociaciones(self._arbol, self._historico, self.w_horas, self.r_km)
        copia._referencia_elegida = deepcopy(self._referencia_elegida)
        return copia

    def restaurar_desde(self, otro: "GestorAsociaciones") -> None:
        self.w_horas = otro.w_horas
        self.r_km = otro.r_km
        self._referencia_elegida = deepcopy(otro._referencia_elegida)
