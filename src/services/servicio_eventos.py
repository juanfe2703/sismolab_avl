"""ServicioEventos (document, section 6: 'Gestion de eventos y
revisiones').

This is the only place that decides:
    - what a report does: alta / confirmacion / revision mayor /
      conflicto / reporte antiguo / reactivacion / bloqueado (table in
      section 6, plus the archived/eliminated cross-rules that follow
      it);
    - how a manual correction runs as a SINGLE retira+reinserta action
      (or an in-place update when the key does not change, per the
      document's explicit optimization);
    - the pendiente/revisado toggle;
    - individual deletion.

It never touches Tkinter, JSON, or the undo pila's internals beyond
calling `registrar`. GUI and persistence both go through this class
instead of the AVL/Historico directly (section 2's GUI/negocio split).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional

from src.model import Evento, EstadoAtencion, ValorInvalidoError
from src.structures import ClaveEvento
from src.undo.pila_deshacer import PilaDeshacer

from .calculadora_prioridad import calcular_prioridad
from .contratos import ArbolAVLProtocol, RelojSimulacionProtocol, VerificadorZonaProtocol
from .historico import Historico
from .reporte import Reporte


class TipoResultado(Enum):
    ALTA = auto()
    CONFIRMACION = auto()
    ACTUALIZACION = auto()            # revision mayor sobre un evento activo
    REACTIVACION = auto()             # revision mayor sobre un evento archivado
    CONFLICTO = auto()
    REPORTE_ANTIGUO = auto()
    ARCHIVADO_SIN_REACTIVAR = auto()  # confirmacion/antiguo sobre un archivado
    RECHAZADO_ID_ELIMINADO = auto()
    RECHAZADO_INVALIDO = auto()
    CORRECCION_APLICADA = auto()
    MARCADO_REVISADO = auto()
    ELIMINADO = auto()
    NO_ENCONTRADO = auto()


class EstadoEvento(Enum):
    """For `localizar_evento` (section 6: 'el resultado debe indicar
    si esta activo, archivado o eliminado')."""
    ACTIVO = auto()
    ARCHIVADO = auto()
    ELIMINADO = auto()
    DESCONOCIDO = auto()


@dataclass
class ResultadoOperacion:
    """One return shape for every operation in this service, so the
    GUI can render a result without knowing which branch of section
    6's table produced it."""
    tipo: TipoResultado
    mensaje: str
    evento: Optional[Evento] = None


@dataclass
class _Snapshot:
    """Opaque to PilaDeshacer; concrete here. `arbol.clonar()` /
    `historico.clonar()` are O(n) - the accepted cost of the
    snapshot-based undo design (see pila_deshacer.py)."""
    arbol: ArbolAVLProtocol
    historico: Historico


class ServicioEventos:
    def __init__(self, arbol: ArbolAVLProtocol, historico: Historico,
                 verificador_zona: VerificadorZonaProtocol,
                 reloj: RelojSimulacionProtocol,
                 pila_deshacer: PilaDeshacer) -> None:
        self._arbol = arbol
        self._historico = historico
        self._verificador_zona = verificador_zona
        self._reloj = reloj
        self._pila = pila_deshacer

    # ------------------------------------------------------------------
    # Undo plumbing
    # ------------------------------------------------------------------

    def _snapshot(self) -> _Snapshot:
        return _Snapshot(arbol=self._arbol.clonar(), historico=self._historico.clonar())

    def _restaurar(self, snapshot: _Snapshot) -> None:
        # In-place restore, not reference swap: the GUI / composition
        # root holds the SAME arbol/historico objects this service was
        # built with, so undo must mutate what they already point to.
        self._arbol.restaurar_desde(snapshot.arbol)
        self._historico.restaurar_desde(snapshot.historico)

    def _registrar_undo(self, descripcion: str, snapshot_previo: _Snapshot) -> None:
        self._pila.registrar(descripcion, snapshot_previo, self._restaurar)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _construir_clave(self, evento: Evento) -> ClaveEvento:
        zona_poblada = self._verificador_zona.es_zona_poblada(
            evento.epicentro_x, evento.epicentro_y
        )
        prioridad = calcular_prioridad(
            evento.magnitud, evento.profundidad_hipocentro, zona_poblada
        )
        return ClaveEvento(prioridad, evento.magnitud, evento.identificador)

    def _validar_no_futuro(self, fecha_hora: datetime) -> None:
        """Section 3: 'Los tiempos de ocurrencia no pueden ser
        posteriores a ese reloj.' Not part of Evento's own validation
        because Evento does not know the simulation clock exists."""
        if fecha_hora > self._reloj.ahora():
            raise ValorInvalidoError(
                "fecha_hora es posterior al reloj de simulacion"
            )

    @staticmethod
    def _mismos_datos(evento: Evento, r: Reporte) -> bool:
        """Section 6: 'La igualdad de datos se refiere a magnitud,
        profundidad, epicentro y tiempo de ocurrencia; no al emisor
        del reporte ni al formato del texto.'"""
        return (
            evento.magnitud == r.magnitud
            and evento.profundidad_hipocentro == r.profundidad_hipocentro
            and evento.epicentro_x == r.epicentro_x
            and evento.epicentro_y == r.epicentro_y
            and evento.fecha_hora == r.fecha_hora
        )

    def _construir_evento_validado(self, identificador: int, magnitud: float,
                                    profundidad_hipocentro: float, epicentro_x: float,
                                    epicentro_y: float, fecha_hora: datetime,
                                    revision: int, estacion: str) -> Evento:
        """Reuses Evento's own __post_init__ validation (ranges, one
        decimal, tz-aware date, revision >= 1) instead of duplicating
        it here. Raises ValorInvalidoError on any violation, including
        the clock check this service adds on top."""
        self._validar_no_futuro(fecha_hora)
        return Evento(
            identificador=identificador,
            magnitud=magnitud,
            profundidad_hipocentro=profundidad_hipocentro,
            epicentro_x=epicentro_x,
            epicentro_y=epicentro_y,
            fecha_hora=fecha_hora,
            revision=revision,
            estado_atencion=EstadoAtencion.PENDIENTE,
            estaciones_reportes={estacion},
        )

    # ------------------------------------------------------------------
    # Creacion manual (section 6, 'Creacion manual de un evento')
    # ------------------------------------------------------------------

    def dar_alta_manual(self, identificador: int, magnitud: float,
                         profundidad_hipocentro: float, epicentro_x: float,
                         epicentro_y: float, fecha_hora: datetime,
                         estacion: str) -> ResultadoOperacion:
        if (self._arbol.buscar_por_id(identificador) is not None
                or self._historico.esta_archivado(identificador)
                or self._historico.esta_eliminado(identificador)):
            return ResultadoOperacion(
                TipoResultado.RECHAZADO_INVALIDO,
                f"El identificador {identificador} ya pertenece a un "
                f"evento activo, archivado o eliminado.",
            )
        try:
            evento = self._construir_evento_validado(
                identificador, magnitud, profundidad_hipocentro,
                epicentro_x, epicentro_y, fecha_hora, revision=1,
                estacion=estacion,
            )
        except ValorInvalidoError as exc:
            return ResultadoOperacion(TipoResultado.RECHAZADO_INVALIDO, str(exc))

        snapshot = self._snapshot()
        clave = self._construir_clave(evento)
        self._arbol.insertar(clave, evento)
        self._registrar_undo(f"Alta manual del evento {identificador}", snapshot)
        return ResultadoOperacion(TipoResultado.ALTA, "Evento creado.", evento)

    # ------------------------------------------------------------------
    # Reportes de estacion (section 6, tabla de 'Procesamiento de
    # reportes recibidos')
    # ------------------------------------------------------------------

    def procesar_reporte(self, reporte: Reporte) -> ResultadoOperacion:
        """Public entry point: resolves ONE report and registers ONE
        undo action for it, end to end.

        A future queue-processing service (section 8) will call
        `_resolver_reporte` directly instead, so that one queue *step*
        - which also moves the report out of the FIFO - becomes a
        single Comando covering both the tree/historico change and
        the queue position, as section 13 requires. Calling the public
        method from there would register two separate undo entries for
        what must be one visible action.
        """
        snapshot = self._snapshot()
        resultado = self._resolver_reporte(reporte)
        if resultado.tipo not in (TipoResultado.CONFLICTO,
                                   TipoResultado.REPORTE_ANTIGUO,
                                   TipoResultado.RECHAZADO_ID_ELIMINADO,
                                   TipoResultado.RECHAZADO_INVALIDO,
                                   TipoResultado.ARCHIVADO_SIN_REACTIVAR):
            self._registrar_undo(
                f"Reporte de {reporte.estacion} sobre el evento "
                f"{reporte.identificador} ({resultado.tipo.name})",
                snapshot,
            )
        return resultado

    def _resolver_reporte(self, reporte: Reporte) -> ResultadoOperacion:
        idf = reporte.identificador

        # Bloqueo de IDs eliminados: nunca se reutilizan ni reactivan.
        if self._historico.esta_eliminado(idf):
            return ResultadoOperacion(
                TipoResultado.RECHAZADO_ID_ELIMINADO,
                f"El identificador {idf} fue eliminado y no admite "
                f"reportes hasta deshacer esa eliminacion.",
            )

        activo = self._arbol.buscar_por_id(idf)
        if activo is not None:
            return self._resolver_sobre_activo(activo, reporte)

        if self._historico.esta_archivado(idf):
            return self._resolver_sobre_archivado(
                self._historico.obtener_archivado(idf), reporte
            )

        # Identificador desconocido: alta automatica. La primera
        # revision recibida puede ser mayor que 1 (section 6).
        try:
            evento = self._construir_evento_validado(
                idf, reporte.magnitud, reporte.profundidad_hipocentro,
                reporte.epicentro_x, reporte.epicentro_y, reporte.fecha_hora,
                revision=reporte.revision, estacion=reporte.estacion,
            )
        except ValorInvalidoError as exc:
            return ResultadoOperacion(TipoResultado.RECHAZADO_INVALIDO, str(exc))

        clave = self._construir_clave(evento)
        self._arbol.insertar(clave, evento)
        return ResultadoOperacion(
            TipoResultado.ALTA, f"Nuevo evento {idf} registrado.", evento
        )

    def _resolver_sobre_activo(self, evento: Evento, reporte: Reporte) -> ResultadoOperacion:
        if reporte.revision > evento.revision:
            return self._aplicar_revision_mayor(evento, reporte, era_activo=True)

        if reporte.revision == evento.revision:
            if self._mismos_datos(evento, reporte):
                evento.estaciones_reportes.add(reporte.estacion)
                return ResultadoOperacion(
                    TipoResultado.CONFIRMACION,
                    f"Confirmado por {reporte.estacion}.", evento,
                )
            return ResultadoOperacion(
                TipoResultado.CONFLICTO,
                f"Conflicto: {reporte.estacion} reporta la misma revision "
                f"con datos distintos. Reporte rechazado.",
            )

        return ResultadoOperacion(
            TipoResultado.REPORTE_ANTIGUO,
            f"Revision {reporte.revision} es anterior a la vigente "
            f"({evento.revision}). Descartado.",
        )

    def _resolver_sobre_archivado(self, evento: Evento, reporte: Reporte) -> ResultadoOperacion:
        if reporte.revision > evento.revision:
            return self._aplicar_revision_mayor(evento, reporte, era_activo=False)
        # "Una confirmacion o un reporte antiguo no lo reactiva."
        return ResultadoOperacion(
            TipoResultado.ARCHIVADO_SIN_REACTIVAR,
            f"El evento {reporte.identificador} esta archivado; este "
            f"reporte no tiene revision suficiente para reactivarlo.",
        )

    def _aplicar_revision_mayor(self, evento: Evento, reporte: Reporte,
                                 era_activo: bool) -> ResultadoOperacion:
        try:
            self._validar_no_futuro(reporte.fecha_hora)
        except ValorInvalidoError as exc:
            return ResultadoOperacion(TipoResultado.RECHAZADO_INVALIDO, str(exc))

        clave_anterior = self._construir_clave(evento) if era_activo else None

        # Se reemplazan los datos vigentes (section 6). Las estaciones
        # que confirmaron la revision superada ya no describen el dato
        # vigente, por lo que se reinicia el conjunto con la estacion
        # que trae la nueva revision (decision documentada; el
        # documento no fija este punto explicitamente).
        try:
            temp = self._construir_evento_validado(
                evento.identificador, reporte.magnitud, reporte.profundidad_hipocentro,
                reporte.epicentro_x, reporte.epicentro_y, reporte.fecha_hora,
                revision=reporte.revision, estacion=reporte.estacion,
            )
        except ValorInvalidoError as exc:
            return ResultadoOperacion(TipoResultado.RECHAZADO_INVALIDO, str(exc))

        evento.magnitud = temp.magnitud
        evento.profundidad_hipocentro = temp.profundidad_hipocentro
        evento.epicentro_x = temp.epicentro_x
        evento.epicentro_y = temp.epicentro_y
        evento.fecha_hora = temp.fecha_hora
        evento.revision = reporte.revision
        evento.estado_atencion = EstadoAtencion.PENDIENTE
        evento.estaciones_reportes = {reporte.estacion}

        nueva_clave = self._construir_clave(evento)

        if era_activo:
            if clave_anterior != nueva_clave:
                self._arbol.eliminar(clave_anterior)
                self._arbol.insertar(nueva_clave, evento)
            return ResultadoOperacion(
                TipoResultado.ACTUALIZACION,
                f"Evento {evento.identificador} actualizado a revision "
                f"{evento.revision}.", evento,
            )

        # Reactivacion desde el historico.
        self._historico.reactivar(evento.identificador)
        self._arbol.insertar(nueva_clave, evento)
        return ResultadoOperacion(
            TipoResultado.REACTIVACION,
            f"Evento {evento.identificador} reactivado como pendiente.", evento,
        )

    # ------------------------------------------------------------------
    # Correccion manual (section 6, 'Correccion manual de un evento')
    # ------------------------------------------------------------------

    def corregir_manual(self, identificador: int, *, magnitud: float | None = None,
                         profundidad_hipocentro: float | None = None,
                         epicentro_x: float | None = None,
                         epicentro_y: float | None = None,
                         fecha_hora: datetime | None = None) -> ResultadoOperacion:
        """Only fields passed (not None) change; the rest keep their
        current value. Identificador is immutable (not a parameter).
        Revision always becomes r + 1, even if the resulting key is
        identical to the previous one (section 6)."""
        evento = self._arbol.buscar_por_id(identificador)
        if evento is None:
            return ResultadoOperacion(
                TipoResultado.NO_ENCONTRADO,
                f"No hay un evento activo con identificador {identificador}.",
            )

        try:
            temp = self._construir_evento_validado(
                identificador,
                magnitud if magnitud is not None else evento.magnitud,
                profundidad_hipocentro if profundidad_hipocentro is not None
                else evento.profundidad_hipocentro,
                epicentro_x if epicentro_x is not None else evento.epicentro_x,
                epicentro_y if epicentro_y is not None else evento.epicentro_y,
                fecha_hora if fecha_hora is not None else evento.fecha_hora,
                revision=evento.revision + 1,
                estacion=next(iter(evento.estaciones_reportes), "manual"),
            )
        except ValorInvalidoError as exc:
            return ResultadoOperacion(TipoResultado.RECHAZADO_INVALIDO, str(exc))

        snapshot = self._snapshot()
        clave_anterior = self._construir_clave(evento)

        evento.magnitud = temp.magnitud
        evento.profundidad_hipocentro = temp.profundidad_hipocentro
        evento.epicentro_x = temp.epicentro_x
        evento.epicentro_y = temp.epicentro_y
        evento.fecha_hora = temp.fecha_hora
        evento.revision += 1
        evento.estado_atencion = EstadoAtencion.PENDIENTE

        nueva_clave = self._construir_clave(evento)
        if nueva_clave != clave_anterior:
            # P o M cambiaron: retira e inserta como parte de esta
            # misma accion (no se registran las rotaciones internas
            # por separado, section 5 y 13).
            self._arbol.eliminar(clave_anterior)
            self._arbol.insertar(nueva_clave, evento)
        # Si la clave no cambio, el documento permite evitar el
        # retira+reinserta: el orden sigue siendo valido porque K no
        # cambio, y ya mutamos el evento en el sitio.

        self._registrar_undo(f"Correccion del evento {identificador}", snapshot)
        return ResultadoOperacion(
            TipoResultado.CORRECCION_APLICADA,
            f"Evento {identificador} corregido (revision {evento.revision}).",
            evento,
        )

    # ------------------------------------------------------------------
    # Estado de atencion
    # ------------------------------------------------------------------

    def marcar_revisado(self, identificador: int) -> ResultadoOperacion:
        """Does not touch P, M or I, so no reinsertion is needed
        (section 6). Still one undoable action."""
        evento = self._arbol.buscar_por_id(identificador)
        if evento is None:
            return ResultadoOperacion(
                TipoResultado.NO_ENCONTRADO,
                f"No hay un evento activo con identificador {identificador}.",
            )
        if evento.estado_atencion == EstadoAtencion.REVISADO:
            return ResultadoOperacion(
                TipoResultado.MARCADO_REVISADO,
                f"El evento {identificador} ya estaba revisado.", evento,
            )

        snapshot = self._snapshot()
        evento.estado_atencion = EstadoAtencion.REVISADO
        self._registrar_undo(f"Evento {identificador} marcado como revisado", snapshot)
        return ResultadoOperacion(
            TipoResultado.MARCADO_REVISADO,
            f"Evento {identificador} marcado como revisado.", evento,
        )

    # ------------------------------------------------------------------
    # Eliminacion individual (section 6 / 10)
    # ------------------------------------------------------------------

    def eliminar_individual(self, identificador: int) -> ResultadoOperacion:
        evento = self._arbol.buscar_por_id(identificador)
        if evento is None:
            return ResultadoOperacion(
                TipoResultado.NO_ENCONTRADO,
                f"No hay un evento activo con identificador {identificador}.",
            )

        snapshot = self._snapshot()
        clave = self._construir_clave(evento)
        self._arbol.eliminar(clave)
        self._historico.eliminar(evento)
        self._registrar_undo(f"Eliminacion del evento {identificador}", snapshot)
        return ResultadoOperacion(
            TipoResultado.ELIMINADO,
            f"Evento {identificador} eliminado.", evento,
        )

    # ------------------------------------------------------------------
    # Consulta (section 6: 'indicar si esta activo, archivado o
    # eliminado')
    # ------------------------------------------------------------------

    def localizar_evento(self, identificador: int) -> tuple[EstadoEvento, Optional[Evento]]:
        activo = self._arbol.buscar_por_id(identificador)
        if activo is not None:
            return EstadoEvento.ACTIVO, activo
        archivado = self._historico.obtener_archivado(identificador)
        if archivado is not None:
            return EstadoEvento.ARCHIVADO, archivado
        eliminado = self._historico.obtener_eliminado(identificador)
        if eliminado is not None:
            return EstadoEvento.ELIMINADO, eliminado
        return EstadoEvento.DESCONOCIDO, None
