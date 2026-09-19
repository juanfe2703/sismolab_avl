class ClaveDuplicadaError(Exception):
    """Raised if the AVL is asked to insert a key that already exists."""


class ClaveNoEncontradaError(Exception):
    """Raised if the AVL is asked to delete a key that does not exist."""