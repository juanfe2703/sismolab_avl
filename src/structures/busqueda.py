"""Single key-lookup routine shared by the AVL and the comparison BST.

Both trees descend the same way; sharing the code guarantees that any
difference in cost comes from the SHAPE of the tree, not from the code.
"""

from __future__ import annotations

from typing import Any, Optional

from .clave_evento import ClaveEvento
from .comparador import comparar_claves
from .resultado_busqueda import ResultadoBusqueda


def buscar_en_arbol(raiz: Optional[Any], clave: ClaveEvento) -> ResultadoBusqueda:
    visitados = 0
    actual = raiz
    while actual is not None:
        visitados += 1  # one comparison per visited node
        comparacion = comparar_claves(clave, actual.clave)
        if comparacion == 0:
            return ResultadoBusqueda(actual, visitados)
        actual = actual.izquierdo if comparacion < 0 else actual.derecho
    return ResultadoBusqueda(None, visitados)