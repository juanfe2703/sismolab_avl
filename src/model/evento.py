"""Minimal physical model of a seismic event (SismoLab AVL, section 3).

This class holds ONLY the event's own data. It knows nothing about the
AVL, priority calculation, populated zones, or persistence.
"""

from dataclasses import dataclass, field
from datetime import datetime

from .enums import EstadoAtencion
from .excepciones import ValorInvalidoError

ID_MIN, ID_MAX = 1, 999_999
MAGNITUD_MIN, MAGNITUD_MAX = -2.0, 10.0
PROFUNDIDAD_MIN, PROFUNDIDAD_MAX = 0.0, 700.0
COORDENADA_MIN, COORDENADA_MAX = 0.0, 1000.0


def _tiene_maximo_un_decimal(valor: float) -> bool:
    """True if `valor` has at most one decimal digit (document constraint)."""
    return abs(valor * 10 - round(valor * 10)) < 1e-9


@dataclass
class Evento:
    identificador: int
    magnitud: float
    profundidad_hipocentro: float
    epicentro_x: float
    epicentro_y: float
    fecha_hora: datetime
    revision: int
    estado_atencion: EstadoAtencion = EstadoAtencion.PENDIENTE
    estaciones_reportes: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self._validar_identificador()
        self._validar_magnitud()
        self._validar_profundidad()
        self._validar_epicentro()
        self._validar_fecha_hora()
        self._validar_revision()

    def _validar_identificador(self) -> None:
        if not (ID_MIN <= self.identificador <= ID_MAX):
            raise ValorInvalidoError(
                f"identificador debe estar en [{ID_MIN}, {ID_MAX}], "
                f"recibido {self.identificador}"
            )

    def _validar_magnitud(self) -> None:
        if not (MAGNITUD_MIN <= self.magnitud <= MAGNITUD_MAX):
            raise ValorInvalidoError(
                f"magnitud debe estar en [{MAGNITUD_MIN}, {MAGNITUD_MAX}], "
                f"recibido {self.magnitud}"
            )
        if not _tiene_maximo_un_decimal(self.magnitud):
            raise ValorInvalidoError("magnitud debe tener maximo un decimal")

    def _validar_profundidad(self) -> None:
        if not (PROFUNDIDAD_MIN <= self.profundidad_hipocentro <= PROFUNDIDAD_MAX):
            raise ValorInvalidoError(
                f"profundidad_hipocentro debe estar en "
                f"[{PROFUNDIDAD_MIN}, {PROFUNDIDAD_MAX}], "
                f"recibido {self.profundidad_hipocentro}"
            )
        if not _tiene_maximo_un_decimal(self.profundidad_hipocentro):
            raise ValorInvalidoError(
                "profundidad_hipocentro debe tener maximo un decimal"
            )

    def _validar_epicentro(self) -> None:
        for nombre, valor in (
            ("epicentro_x", self.epicentro_x),
            ("epicentro_y", self.epicentro_y),
        ):
            if not (COORDENADA_MIN <= valor <= COORDENADA_MAX):
                raise ValorInvalidoError(
                    f"{nombre} debe estar en [{COORDENADA_MIN}, {COORDENADA_MAX}], "
                    f"recibido {valor}"
                )
            if not _tiene_maximo_un_decimal(valor):
                raise ValorInvalidoError(f"{nombre} debe tener maximo un decimal")

    def _validar_fecha_hora(self) -> None:
        if self.fecha_hora.tzinfo is None:
            raise ValorInvalidoError("fecha_hora debe incluir zona horaria (UTC)")

    def _validar_revision(self) -> None:
        if self.revision < 1:
            raise ValorInvalidoError("revision debe ser un entero positivo")