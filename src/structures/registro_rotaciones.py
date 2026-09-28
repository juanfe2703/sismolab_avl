"""Bookkeeping of applied rotations (document, sections 8 and 14).

A "case" is the classic pattern (LL, RR, LR, RL). A "giro" is one
elementary rotation: a double case counts as ONE case and TWO giros.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .clave_evento import ClaveEvento


class CasoBalanceo(Enum):
    LL = "LL"  # left-left: one right rotation
    RR = "RR"  # right-right: one left rotation
    LR = "LR"  # left-right: left rotation on the child, then right on the node
    RL = "RL"  # right-left: right rotation on the child, then left on the node


@dataclass(frozen=True)
class RotacionAplicada:
    """One case applied by the AVL, kept so the UI can explain what happened."""

    caso: CasoBalanceo
    clave_nodo: ClaveEvento  # key of the node where the imbalance was found


@dataclass
class ContadoresRotaciones:
    """Cumulative counters. Part of the restorable state (undo, versions)."""

    casos_ll: int = 0
    casos_rr: int = 0
    casos_lr: int = 0
    casos_rl: int = 0
    giros_izquierda: int = 0
    giros_derecha: int = 0

    def registrar(self, caso: CasoBalanceo) -> None:
        if caso is CasoBalanceo.LL:
            self.casos_ll += 1
            self.giros_derecha += 1
        elif caso is CasoBalanceo.RR:
            self.casos_rr += 1
            self.giros_izquierda += 1
        elif caso is CasoBalanceo.LR:
            self.casos_lr += 1
            self.giros_izquierda += 1
            self.giros_derecha += 1
        else:  # RL
            self.casos_rl += 1
            self.giros_izquierda += 1
            self.giros_derecha += 1

    @property
    def total_giros(self) -> int:
        return self.giros_izquierda + self.giros_derecha

    def copiar(self) -> "ContadoresRotaciones":
        """Independent copy (all fields are ints), used for undo snapshots."""
        return replace(self)