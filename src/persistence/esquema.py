"""JSON schema: serialize/parse Evento, ClaveEvento, zones, and full
tree topologies. Centralized here so `carga_por_topologia` and
`guardado_estructural` (which both read/write the SAME node shape)
never drift apart, and so `carga_por_inserciones` reuses the same
Evento (de)serialization instead of a second copy of it.

No format is prescribed by the document ('No se exige un formato JSON
identico entre equipos', section 12) - this is OUR schema, documented
here as the design requires.

------------------------------------------------------------------
Evento (section 3 table): a flat object, e.g.
    {
      "identificador": 10,
      "magnitud": 4.5,
      "profundidad_hipocentro": 30.0,
      "epicentro_x": 500.0,
      "epicentro_y": 500.0,
      "fecha_hora": "2026-09-07T10:00:00Z",
      "revision": 1,
      "estado_atencion": "pendiente",
      "estaciones_reportes": ["EST-A", "EST-B"]
    }
The document's own example date format (with trailing 'Z') is used, and
'.' is the decimal separator everywhere (section 5: 'El punto se
utiliza como separador decimal... en JSON').

------------------------------------------------------------------
A tree topology (used both standalone for 'carga por topologia' and
embedded inside a full scenario save) is:
    {
      "raiz": 10,               // id of the root, or null if empty
      "nodos": {
        "10": {
          "evento": { ...evento fields... },
          "prioridad_almacenada": 3,     // section 5's P, stored
                                          // explicitly so we can check
                                          // it against the recalculated
                                          // value (section 12)
          "altura_almacenada": 2,
          "factor_balance_almacenado": 1,
          "izquierdo": "5",     // id of left child, or null
          "derecho": "20"
        },
        "5": { ... },
        ...
      }
    }
Ids are stored as JSON object keys, which are always strings; they are
converted back to int on load and cross-checked against the
'identificador' inside each node's own 'evento' payload.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.model import EstadoAtencion, Evento, Prioridad, ValorInvalidoError
from src.structures import ClaveEvento, NodoAVL, altura as altura_de, comparar_claves

from src.services.zonas import ZonaRectangular

VERSION_ESQUEMA = 1


# ---------------------------------------------------------------- fechas ----

def fecha_a_texto(fecha: datetime) -> str:
    return fecha.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fecha_desde_texto(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


# --------------------------------------------------------------- evento ----

def evento_a_dict(evento: Evento) -> dict:
    return {
        "identificador": evento.identificador,
        "magnitud": evento.magnitud,
        "profundidad_hipocentro": evento.profundidad_hipocentro,
        "epicentro_x": evento.epicentro_x,
        "epicentro_y": evento.epicentro_y,
        "fecha_hora": fecha_a_texto(evento.fecha_hora),
        "revision": evento.revision,
        "estado_atencion": evento.estado_atencion.value,
        "estaciones_reportes": sorted(evento.estaciones_reportes),
    }


def evento_desde_dict(d: dict) -> Evento:
    """Raises ValorInvalidoError (via Evento's own __post_init__) or
    KeyError/ValueError for a malformed/missing field - callers turn
    both into entries of ErrorCargaInvalida, never let them propagate
    raw to the GUI."""
    return Evento(
        identificador=int(d["identificador"]),
        magnitud=float(d["magnitud"]),
        profundidad_hipocentro=float(d["profundidad_hipocentro"]),
        epicentro_x=float(d["epicentro_x"]),
        epicentro_y=float(d["epicentro_y"]),
        fecha_hora=fecha_desde_texto(d["fecha_hora"]),
        revision=int(d["revision"]),
        estado_atencion=EstadoAtencion(d.get("estado_atencion", "pendiente")),
        estaciones_reportes=set(d.get("estaciones_reportes", [])),
    )


# ----------------------------------------------------------------- zona ----

def zona_a_dict(zona: ZonaRectangular) -> dict:
    return {
        "identificador": zona.identificador,
        "x_min": zona.x_min, "y_min": zona.y_min,
        "x_max": zona.x_max, "y_max": zona.y_max,
        "poblada": zona.poblada,
    }


def zona_desde_dict(d: dict) -> ZonaRectangular:
    return ZonaRectangular(
        identificador=str(d["identificador"]),
        x_min=float(d["x_min"]), y_min=float(d["y_min"]),
        x_max=float(d["x_max"]), y_max=float(d["y_max"]),
        poblada=bool(d["poblada"]),
    )


# ------------------------------------------------------------ topologia ----

def arbol_a_documento(raiz: Optional[NodoAVL]) -> dict:
    """Walk the REAL node graph (iterative, to avoid a recursion-depth
    surprise on a very unbalanced 'modo estres' tree) and produce the
    flat {"raiz":..., "nodos": {...}} shape."""
    nodos: dict = {}
    if raiz is None:
        return {"raiz": None, "nodos": nodos}

    pila = [raiz]
    while pila:
        nodo = pila.pop()
        clave_id = str(nodo.clave.identificador)
        if clave_id in nodos:
            continue  # ya visitado (no deberia ocurrir en un arbol valido)
        nodos[clave_id] = {
            "evento": evento_a_dict(nodo.evento_ref),
            "prioridad_almacenada": nodo.clave.prioridad.value,
            "altura_almacenada": nodo.altura,
            "factor_balance_almacenado": altura_de(nodo.izquierdo) - altura_de(nodo.derecho),
            "izquierdo": str(nodo.izquierdo.clave.identificador) if nodo.izquierdo else None,
            "derecho": str(nodo.derecho.clave.identificador) if nodo.derecho else None,
        }
        if nodo.izquierdo is not None:
            pila.append(nodo.izquierdo)
        if nodo.derecho is not None:
            pila.append(nodo.derecho)

    return {"raiz": str(raiz.clave.identificador), "nodos": nodos}


def documento_a_nodos(documento: dict, verificador_zona,
                       calcular_prioridad_fn,
                       permitir_desbalance: bool) -> tuple[Optional[NodoAVL], list[str]]:
    """The heavy validator (document, section 12: uniqueness,
    references, no cycles, single position, global BST order, heights,
    balance factors, and stored priority matching the recalculated
    one). Returns (raiz_construida, errores). If errores is non-empty,
    raiz_construida must be ignored/discarded by the caller - nothing
    here mutates the live scenario, this only builds a candidate graph
    in memory.
    """
    errores: list[str] = []
    raiz_id = documento.get("raiz")
    nodos_doc: dict = documento.get("nodos", {})

    if raiz_id is None:
        if nodos_doc:
            errores.append("raiz es null pero 'nodos' no esta vacio")
            return None, errores
        return None, errores  # arbol vacio, valido

    raiz_id = str(raiz_id)
    if raiz_id not in nodos_doc:
        return None, [f"la raiz declarada {raiz_id} no esta en 'nodos'"]

    # 1) Construir un Evento validado + ClaveEvento por cada nodo, y
    #    verificar que la prioridad almacenada coincide con la
    #    recalculada (section 12).
    eventos: dict[str, Evento] = {}
    claves: dict[str, ClaveEvento] = {}
    for id_texto, datos in nodos_doc.items():
        if str(datos.get("evento", {}).get("identificador")) != id_texto:
            errores.append(f"nodo '{id_texto}': el id de 'evento' no coincide con la llave")
            continue
        try:
            evento = evento_desde_dict(datos["evento"])
        except (ValorInvalidoError, KeyError, ValueError) as exc:
            errores.append(f"nodo '{id_texto}': evento invalido ({exc})")
            continue

        zona_poblada = verificador_zona.es_zona_poblada(evento.epicentro_x, evento.epicentro_y)
        prioridad_calculada = calcular_prioridad_fn(
            evento.magnitud, evento.profundidad_hipocentro, zona_poblada
        )
        try:
            prioridad_almacenada = Prioridad(int(datos["prioridad_almacenada"]))
        except (KeyError, ValueError) as exc:
            errores.append(f"nodo '{id_texto}': prioridad_almacenada invalida ({exc})")
            continue
        if prioridad_almacenada != prioridad_calculada:
            errores.append(
                f"nodo '{id_texto}': prioridad almacenada "
                f"({prioridad_almacenada.name}) no coincide con la "
                f"calculada ({prioridad_calculada.name})"
            )
            continue

        eventos[id_texto] = evento
        claves[id_texto] = ClaveEvento(prioridad_calculada, evento.magnitud, evento.identificador)

    if errores:
        return None, errores  # no seguir construyendo sobre datos invalidos

    # 2) Cada id referenciado como hijo debe existir y ser usado como
    #    hijo de UN SOLO padre (pertenencia a una sola posicion).
    padre_de: dict[str, str] = {}
    for id_texto, datos in nodos_doc.items():
        for lado in ("izquierdo", "derecho"):
            hijo = datos.get(lado)
            if hijo is None:
                continue
            hijo = str(hijo)
            if hijo not in nodos_doc:
                errores.append(f"nodo '{id_texto}': referencia a '{hijo}' inexistente")
                continue
            if hijo in padre_de:
                errores.append(
                    f"'{hijo}' aparece como hijo de mas de un nodo "
                    f"('{padre_de[hijo]}' y '{id_texto}')"
                )
                continue
            padre_de[hijo] = id_texto
    if raiz_id in padre_de:
        errores.append("la raiz no puede ser hijo de otro nodo")
    if errores:
        return None, errores

    # 3) Construir los NodoAVL y enlazarlos.
    construidos: dict[str, NodoAVL] = {
        id_texto: NodoAVL(claves[id_texto], eventos[id_texto]) for id_texto in nodos_doc
    }
    for id_texto, datos in nodos_doc.items():
        nodo = construidos[id_texto]
        izq = datos.get("izquierdo")
        der = datos.get("derecho")
        nodo.izquierdo = construidos[str(izq)] if izq is not None else None
        nodo.derecho = construidos[str(der)] if der is not None else None

    # 4) Alcanzabilidad desde la raiz == exactamente todos los nodos
    #    declarados (detecta ciclos y nodos desconectados con una sola
    #    pasada: si hay un ciclo o algo desconectado, el conteo de
    #    visitados no puede igualar la cantidad total de nodos).
    visitados: set[str] = set()
    pila = [raiz_id]
    while pila:
        actual = pila.pop()
        if actual in visitados:
            continue
        visitados.add(actual)
        nodo = construidos[actual]
        if nodo.izquierdo is not None:
            pila.append(str(nodo.izquierdo.clave.identificador))
        if nodo.derecho is not None:
            pila.append(str(nodo.derecho.clave.identificador))
    if visitados != set(nodos_doc.keys()):
        errores.append(
            "el grafo declarado no es un arbol conectado sin ciclos "
            "alcanzable desde la raiz"
        )
        return None, errores

    # 5) Orden global BST: el recorrido inorden debe ser estrictamente
    #    ascendente segun comparar_claves (section 5).
    orden: list[ClaveEvento] = []

    def _inorden(nodo: Optional[NodoAVL]) -> None:
        if nodo is None:
            return
        _inorden(nodo.izquierdo)
        orden.append(nodo.clave)
        _inorden(nodo.derecho)

    _inorden(construidos[raiz_id])
    for anterior, siguiente in zip(orden, orden[1:]):
        if comparar_claves(anterior, siguiente) >= 0:
            errores.append(
                f"orden BST violado entre las claves {anterior} y {siguiente}"
            )
    if errores:
        return None, errores

    # 6) Alturas recalculadas y factor de balance, comparados contra lo
    #    almacenado (section 14: 'alturas recalculadas y factores de
    #    balance'; metadatos inconsistentes obligan a rechazar).
    def _recalcular_altura(nodo: Optional[NodoAVL]) -> int:
        if nodo is None:
            return -1
        izq = _recalcular_altura(nodo.izquierdo)
        der = _recalcular_altura(nodo.derecho)
        nodo.altura = 1 + max(izq, der)
        return nodo.altura

    _recalcular_altura(construidos[raiz_id])

    desbalanceado = False
    for id_texto, nodo in construidos.items():
        datos = nodos_doc[id_texto]
        if nodo.altura != int(datos["altura_almacenada"]):
            errores.append(
                f"nodo '{id_texto}': altura almacenada "
                f"({datos['altura_almacenada']}) no coincide con la "
                f"recalculada ({nodo.altura})"
            )
        factor_real = altura_de(nodo.izquierdo) - altura_de(nodo.derecho)
        if factor_real != int(datos["factor_balance_almacenado"]):
            errores.append(
                f"nodo '{id_texto}': factor de balance almacenado "
                f"({datos['factor_balance_almacenado']}) no coincide "
                f"con el recalculado ({factor_real})"
            )
        if factor_real not in (-1, 0, 1):
            desbalanceado = True

    if errores:
        return None, errores

    if desbalanceado and not permitir_desbalance:
        errores.append(
            "la topologia esta desbalanceada (algun factor de balance "
            "fuera de {-1,0,1}) y el modo estres no esta activo"
        )
        return None, errores

    return construidos[raiz_id], errores
