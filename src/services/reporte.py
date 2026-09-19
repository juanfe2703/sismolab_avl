"""Incoming report data (document, section 6 - 'Procesamiento de
reportes recibidos').

A Reporte is deliberately NOT an Evento: it is raw input from a
station, before ServicioEventos decides whether it is an alta,
confirmation, correction (revision mayor), conflict, or an old report
to discard. Keeping the two separate means the FIFO queue and the
resolution logic never touch Evento's own validation/mutation
directly, and a rejected report never partially constructs one.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Reporte:
    identificador: int
    magnitud: float
    profundidad_hipocentro: float
    epicentro_x: float
    epicentro_y: float
    fecha_hora: datetime
    revision: int
    estacion: str
