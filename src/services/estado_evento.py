"""Shared enum, split out of servicio_eventos.py so that
servicio_asociaciones.py can tag query results (activo/archivado)
without creating a circular import between the two services."""
from enum import Enum, auto


class EstadoEvento(Enum):
    ACTIVO = auto()
    ARCHIVADO = auto()
    ELIMINADO = auto()
    DESCONOCIDO = auto()
