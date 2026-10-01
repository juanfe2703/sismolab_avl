"""Errors raised by the persistence layer.

The document requires atomicity everywhere ('la carga debe ser
completa o no aplicarse'; 'si algo falla, no se toca el estado
actual'). Every load function in this package validates EVERYTHING
first and only mutates the live scenario after every check passed, so
this exception carries the FULL list of problems found, not just the
first one - useful for the GUI to show a complete report in one shot
instead of a fix-one-error-at-a-time loop.
"""


class ErrorCargaInvalida(Exception):
    def __init__(self, errores: list[str]) -> None:
        self.errores = errores
        super().__init__("; ".join(errores) if errores else "carga invalida")
