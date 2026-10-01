"""Rectangular zones of the scenario (document, section 3).

Zones are rectangles in the 0..1000 km plane. An epicenter belongs to a
zone when it is inside it OR ON ITS BORDER (inclusive). A point on the
border of two zones counts as populated if either of them is populated.
Both rules collapse into one: a point is populated if ANY populated zone
contains it (inclusively). Points inside no zone are not populated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.model import ValorInvalidoError

LIMITE_MIN, LIMITE_MAX = 0.0, 1000.0


@dataclass(frozen=True)
class ZonaRectangular:
    identificador: str
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    poblada: bool

    def __post_init__(self) -> None:
        for nombre in ("x_min", "y_min", "x_max", "y_max"):
            valor = getattr(self, nombre)
            if not (LIMITE_MIN <= valor <= LIMITE_MAX):
                raise ValorInvalidoError(
                    f"zona {self.identificador}: {nombre} fuera de "
                    f"[{LIMITE_MIN}, {LIMITE_MAX}]"
                )
        if self.x_min > self.x_max or self.y_min > self.y_max:
            raise ValorInvalidoError(
                f"zona {self.identificador}: limites minimos mayores que los maximos"
            )

    def contiene(self, x: float, y: float) -> bool:
        """Inclusive of the border."""
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max


class VerificadorZonasRectangulares:
    """Implements VerificadorZonaProtocol. Mutable ONLY through
    `reemplazar`, so a scenario load can swap the geometry in place
    (ServicioEventos keeps a reference to this same object)."""

    def __init__(self, zonas: Iterable[ZonaRectangular] = ()) -> None:
        self._zonas: list[ZonaRectangular] = list(zonas)

    def es_zona_poblada(self, x: float, y: float) -> bool:
        return any(z.poblada and z.contiene(x, y) for z in self._zonas)

    def zonas(self) -> list[ZonaRectangular]:
        return list(self._zonas)

    def reemplazar(self, zonas: Iterable[ZonaRectangular]) -> None:
        self._zonas = list(zonas)

    # ---------- snapshot support (undo, section 13) ----------

    def clonar(self) -> "VerificadorZonasRectangulares":
        # ZonaRectangular is a frozen dataclass: safe to share the
        # instances themselves between the copy and the original.
        return VerificadorZonasRectangulares(self._zonas)

    def restaurar_desde(self, otro: "VerificadorZonasRectangulares") -> None:
        self._zonas = list(otro._zonas)
