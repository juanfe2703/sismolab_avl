class ClaveDuplicadaError(Exception):
    """Raised if the AVL is asked to insert a key that already exists.

    Should never happen in practice: uniqueness of the event identifier
    is guaranteed upstream, in the events service. If this fires, it
    signals a bug in that layer, not something the AVL should silently
    resolve.
    """