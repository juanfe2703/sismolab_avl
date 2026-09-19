"""Ordered key used by the AVL and the comparison BST.

Document (section 5): K = (P, M, I), where P is the calculated priority,
M is the current magnitude and I is the numeric identifier.
"""

from typing import NamedTuple

from src.model import Prioridad


class ClaveEvento(NamedTuple):
    prioridad: Prioridad
    magnitud: float
    identificador: int