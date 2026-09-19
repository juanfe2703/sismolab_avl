"""Single source of truth for comparing two ClaveEvento instances.

Document (section 5): lexicographic comparison using the first
differing component, in this precedence: priority > magnitud > id.

Every structure that needs to order events (AVL, BST, audit) MUST use
this function instead of comparing tuples or fields by hand.
"""

from .clave_evento import ClaveEvento


def comparar_claves(a: ClaveEvento, b: ClaveEvento) -> int:
    """Returns -1 if a < b, 0 if a == b, 1 if a > b (K = (P, M, I))."""
    if a.prioridad.value != b.prioridad.value:
        return -1 if a.prioridad.value < b.prioridad.value else 1
    if a.magnitud != b.magnitud:
        return -1 if a.magnitud < b.magnitud else 1
    if a.identificador != b.identificador:
        return -1 if a.identificador < b.identificador else 1
    return 0