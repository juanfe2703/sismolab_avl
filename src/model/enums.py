from enum import Enum


class EstadoAtencion(Enum):
    """Attention state of an active event (document, section 3)."""
    PENDIENTE = "pendiente"
    REVISADO = "revisado"


class Prioridad(Enum):
    """The three priority levels. The numeric value IS the comparison
    weight used by the AVL key (P, M, I) — do not change these numbers."""
    BAJA = 1
    MEDIA = 2
    ALTA = 3