"""Escenario: the aggregate of every live object that makes up one
operating scenario (document, sections 3 and 12).

It only GROUPS references; it holds no business logic. The composition
root (main.py / GUI bootstrap) builds one Escenario and hands the same
instance to ServicioEventos, ServicioPersistencia, etc. Loads and undo
mutate these objects IN PLACE, never rebind them, because every service
holds a reference to the same instances.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Optional

from src.model import ValorInvalidoError

from .cola_reportes import ColaReportes
from .contratos import ArbolAVLProtocol, ArbolBusquedaProtocol
from .gestor_asociaciones import GestorAsociaciones
from .historico import Historico
from .zonas import VerificadorZonasRectangulares


class RelojSimulacion:
    """Explicit simulation clock (section 3). It only moves forward by a
    user action; `establecer` exists for loads/undo, which restore an
    exact prior instant."""

    def __init__(self, ahora: datetime) -> None:
        self._ahora = ahora

    def ahora(self) -> datetime:
        return self._ahora

    def avanzar(self, nuevo_instante: datetime) -> None:
        if nuevo_instante < self._ahora:
            raise ValorInvalidoError("el reloj de simulacion no puede retroceder")
        self._ahora = nuevo_instante

    def establecer(self, instante: datetime) -> None:
        self._ahora = instante

    # ---------- snapshot support (undo, section 13) ----------

    def clonar(self) -> "RelojSimulacion":
        return RelojSimulacion(self._ahora)

    def restaurar_desde(self, otro: "RelojSimulacion") -> None:
        self._ahora = otro._ahora


@dataclass
class ParametrosEscenario:
    """L (section 9) and T (section 10). W and R live in
    GestorAsociaciones, which owns them."""
    limite_acceso_l: int = 3
    umbral_archivo_t_horas: float = 72.0


@dataclass
class Escenario:
    arbol: ArbolAVLProtocol
    historico: Historico
    gestor_asociaciones: GestorAsociaciones
    cola: ColaReportes
    reloj: RelojSimulacion
    zonas: VerificadorZonasRectangulares
    estaciones: list[str]
    parametros: ParametrosEscenario = field(default_factory=ParametrosEscenario)
    metricas: dict[str, int] = field(default_factory=dict)
    # Comparison BST produced by a "carga por inserciones". Derived and
    # transient: it is NOT part of the persisted scenario.
    bst_comparacion: Optional[ArbolBusquedaProtocol] = None

    # ---------- snapshot support (undo, section 13) ----------
    #
    # Composes every sub-object's own clonar()/restaurar_desde(). This
    # is what lets a whole-scenario load (persistence) be undone with
    # the exact same mechanism as a single alta in ServicioEventos:
    # snapshot before, restaurar_desde on undo. `estaciones` and
    # `metricas` are plain data (list/dict), so they are copied
    # in place rather than rebound, for the same reason every other
    # `restaurar_desde` mutates in place: other components hold
    # references to these same container objects.

    def clonar(self) -> "Escenario":
        return Escenario(
            arbol=self.arbol.clonar(),
            historico=self.historico.clonar(),
            gestor_asociaciones=self.gestor_asociaciones.clonar(),
            cola=self.cola.clonar(),
            reloj=self.reloj.clonar(),
            zonas=self.zonas.clonar(),
            estaciones=list(self.estaciones),
            parametros=replace(self.parametros),
            metricas=dict(self.metricas),
            bst_comparacion=self.bst_comparacion.clonar()
            if self.bst_comparacion is not None else None,
        )

    def restaurar_desde(self, otro: "Escenario") -> None:
        self.arbol.restaurar_desde(otro.arbol)
        self.historico.restaurar_desde(otro.historico)
        self.gestor_asociaciones.restaurar_desde(otro.gestor_asociaciones)
        self.cola.restaurar_desde(otro.cola)
        self.reloj.restaurar_desde(otro.reloj)
        self.zonas.restaurar_desde(otro.zonas)
        self.estaciones[:] = otro.estaciones
        self.parametros = replace(otro.parametros)
        self.metricas.clear()
        self.metricas.update(otro.metricas)
        if otro.bst_comparacion is not None:
            if self.bst_comparacion is None:
                self.bst_comparacion = otro.bst_comparacion.clonar()
            else:
                self.bst_comparacion.restaurar_desde(otro.bst_comparacion)
        else:
            self.bst_comparacion = None
