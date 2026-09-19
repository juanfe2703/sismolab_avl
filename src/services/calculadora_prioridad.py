"""Priority calculation (document, section 4).

Pure and stateless on purpose: given the event's CURRENT magnitude,
hypocenter depth and whether its epicenter falls in a populated zone,
returns the mandatory Prioridad. Kept separate from ServicioEventos so
it can be unit-tested directly against the document's worked examples,
e.g.:
    calcular_prioridad(4.5, 30.0, True)  -> Prioridad.ALTA
    calcular_prioridad(4.5, 30.0, False) -> Prioridad.MEDIA

The rules are fixed and MUST be applied in this order (section 4):
    3 Alta:  M >= 6.0; or M >= 4.5 and H <= 30.0 and zona poblada.
    2 Media: no cumple Alta y M >= 4.5.
    1 Baja:  ninguna de las anteriores.
All limits are inclusive.
"""
from src.model import Prioridad


def calcular_prioridad(magnitud: float, profundidad_hipocentro: float,
                        zona_poblada: bool) -> Prioridad:
    if magnitud >= 6.0:
        return Prioridad.ALTA
    if magnitud >= 4.5 and profundidad_hipocentro <= 30.0 and zona_poblada:
        return Prioridad.ALTA
    if magnitud >= 4.5:
        return Prioridad.MEDIA
    return Prioridad.BAJA
