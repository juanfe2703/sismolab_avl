"""ServicioAuditoria (document, section 14: 'Auditoria e indicadores').

Exists so the GUI's "Verificar estructura" button has a service to
call instead of walking tree nodes itself - section 2's GUI/negocio
split applies here as much as anywhere else: the GUI only triggers
`verificar` and renders the `ReporteAuditoria` it gets back.

Checks performed, per section 14 ('comprobar el orden global por K,
unicidad, referencias, alturas recalculadas y factores de balance'):
  - Global order by K: an inorder walk must be strictly ascending by
    `comparar_claves` (section 5).
  - Uniqueness: no two active nodes share an identificador.
  - Identity consistency ('referencias'): each node's
    `evento_ref.identificador` must match its own `clave.identificador`
    - this is what would catch a node left holding stale data after a
    mutation that forgot to keep key and event in sync.
  - Heights: recomputed bottom-up from the real node graph must match
    the stored `nodo.altura` (section 14: alturas del arbol vacio = -1,
    de una hoja = 0).
  - Balance factor: in modo normal every node's factor must be in
    {-1, 0, 1}; in modo estres, a factor outside that range is expected
    and reported separately as informational, not as an error -
    section 14: 'se informa el desbalance esperado y se distinguen los
    errores de orden o de metadatos' from genuine structural problems.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.structures import ClaveEvento, comparar_claves

from .contratos import ArbolAVLProtocol


@dataclass
class ProblemaAuditoria:
    identificador: int
    descripcion: str


@dataclass
class ReporteAuditoria:
    ok: bool
    problemas: list[ProblemaAuditoria] = field(default_factory=list)
    # Solo con contenido en modo estres: desbalance EXPERADO, no un
    # error (section 14 pide distinguirlo de un problema real).
    nodos_en_desbalance_esperado: list[int] = field(default_factory=list)


class ServicioAuditoria:
    def verificar(self, arbol: ArbolAVLProtocol, modo_estres: bool) -> ReporteAuditoria:
        raiz = arbol.obtener_raiz()
        problemas: list[ProblemaAuditoria] = []
        desbalanceados: list[int] = []
        vistos: set[int] = set()
        anterior: list[Optional[ClaveEvento]] = [None]  # lista para mutar desde el closure

        def recorrer(nodo) -> int:
            if nodo is None:
                return -1  # altura del arbol vacio (section 14)

            altura_izq = recorrer(nodo.izquierdo)

            if anterior[0] is not None and comparar_claves(anterior[0], nodo.clave) >= 0:
                problemas.append(ProblemaAuditoria(
                    nodo.clave.identificador,
                    f"orden global violado: {anterior[0]} deberia ser menor que {nodo.clave}",
                ))
            anterior[0] = nodo.clave

            if nodo.clave.identificador in vistos:
                problemas.append(ProblemaAuditoria(
                    nodo.clave.identificador, "identificador duplicado en el arbol activo",
                ))
            vistos.add(nodo.clave.identificador)

            if nodo.evento_ref.identificador != nodo.clave.identificador:
                problemas.append(ProblemaAuditoria(
                    nodo.clave.identificador,
                    "el identificador de evento_ref no coincide con la clave del nodo",
                ))

            altura_der = recorrer(nodo.derecho)
            altura_real = 1 + max(altura_izq, altura_der)
            if nodo.altura != altura_real:
                problemas.append(ProblemaAuditoria(
                    nodo.clave.identificador,
                    f"altura almacenada ({nodo.altura}) no coincide con la "
                    f"recalculada ({altura_real})",
                ))

            factor = altura_izq - altura_der
            if factor not in (-1, 0, 1):
                if modo_estres:
                    desbalanceados.append(nodo.clave.identificador)
                else:
                    problemas.append(ProblemaAuditoria(
                        nodo.clave.identificador,
                        f"factor de balance {factor} fuera de [-1, 1] en modo normal",
                    ))
            return altura_real

        recorrer(raiz)
        return ReporteAuditoria(
            ok=not problemas, problemas=problemas,
            nodos_en_desbalance_esperado=desbalanceados,
        )
