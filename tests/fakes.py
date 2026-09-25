"""A fake tree satisfying ArbolAVLProtocol, used ONLY to test
ServicioEventos before the real AVL exists. It does not rotate, does
not compute real heights, and is not what gets delivered - it exists
so the business-rule logic in ServicioEventos can be verified in
isolation, per the whole point of using a Protocol in contratos.py.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Iterator, Optional

from src.model import Evento
from src.structures import ClaveEvento


class ArbolFalso:
    def __init__(self) -> None:
        self._por_clave: dict[ClaveEvento, Evento] = {}
        self._por_id: dict[int, ClaveEvento] = {}
        self.modo_estres: bool = False

    def insertar(self, clave: ClaveEvento, evento: Evento) -> int:
        self._por_clave[clave] = evento
        self._por_id[evento.identificador] = clave
        return 0

    def eliminar(self, clave: ClaveEvento) -> int:
        evento = self._por_clave.pop(clave)
        del self._por_id[evento.identificador]
        return 0

    def buscar_por_id(self, identificador: int) -> Optional[Evento]:
        clave = self._por_id.get(identificador)
        return self._por_clave.get(clave) if clave is not None else None

    def nodos_visitados_ultima_operacion(self) -> int:
        return 1

    def recorrido_inorden(self) -> Iterator[Evento]:
        return iter(self._por_clave.values())

    def recorrido_preorden(self) -> Iterator[Evento]:
        return iter([])

    def recorrido_postorden(self) -> Iterator[Evento]:
        return iter([])

    def recorrido_por_niveles(self) -> Iterator[Evento]:
        return iter([])

    def altura(self) -> int:
        return 0

    def cantidad_nodos(self) -> int:
        return len(self._por_clave)

    def cantidad_hojas(self) -> int:
        return 0

    def activar_modo_estres(self) -> None:
        self.modo_estres = True

    def recuperar_balance(self) -> int:
        self.modo_estres = False
        return 0

    def profundidad_de(self, identificador: int) -> int:
        return 0

    def factor_balance_de(self, identificador: int) -> int:
        return 0

    def clonar(self) -> "ArbolFalso":
        copia = ArbolFalso()
        copia._por_clave = deepcopy(self._por_clave)
        copia._por_id = deepcopy(self._por_id)
        copia.modo_estres = self.modo_estres
        return copia

    def restaurar_desde(self, otro: "ArbolFalso") -> None:
        self._por_clave = deepcopy(otro._por_clave)
        self._por_id = deepcopy(otro._por_id)
        self.modo_estres = otro.modo_estres


class ZonaFalsa:
    """Everything is populated - or configure `poblados` per call, used
    to reproduce section 4's own worked example (M=4.5, H=30.0)."""

    def __init__(self, poblado_por_defecto: bool = True) -> None:
        self.poblado_por_defecto = poblado_por_defecto

    def es_zona_poblada(self, x: float, y: float) -> bool:
        return self.poblado_por_defecto


class RelojFalso:
    def __init__(self, ahora):
        self._ahora = ahora

    def ahora(self):
        return self._ahora

    def avanzar(self, nuevo_instante) -> None:
        self._ahora = nuevo_instante
