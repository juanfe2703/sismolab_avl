"""ServicioPersistencia (document, section 12: 'Persistencia y
reconstruccion del escenario').

Atomicity pattern used by EVERY operation here, without exception:
    1. Parse and validate EVERYTHING into brand-new, disconnected
       objects (never touching `self._escenario`).
    2. If any check fails, return before touching live state -
       "si algo falla, no se toca el estado actual" is enforced by
       construction, not by a try/rollback.
    3. Only once every check passed: snapshot the live Escenario
       (`clonar()`), install the new state (`restaurar_desde()`), and
       register ONE Comando in the undo stack.

Step 3 reuses EXACTLY the same undo mechanism as ServicioEventos - a
load is "just" another action whose snapshot happens to be the whole
scenario instead of a slice of it. Section 13 explicitly lists 'carga'
among the actions that must be undoable, so this is not an added
convenience, it is a requirement.

Design decision - what a partial load touches (NOT fixed by the
document, documented here as section 2 requires): 'carga por
inserciones' and 'carga por topologia' both describe ONLY events for
the active catalog (and, for insertions, the comparison BST). Neither
paragraph mentions historico, cola, reloj, zonas or parametros, so we
read them as replacing ONLY the active catalog (+ BST, for insertions)
and leaving the rest of the scenario untouched. 'Guardado estructural'
is the one operation that is explicit about covering everything
(section 12's three bullet points), so only `cargar_estructural`
replaces the whole Escenario. All three still snapshot the WHOLE
Escenario for undo, for one reason: reusing a single, already-tested
snapshot mechanism is safer than writing three narrower ones, at an
acceptable, documented memory cost (see pila_deshacer.py).
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import Callable, Optional

from src.services.calculadora_prioridad import calcular_prioridad
from src.services.cola_reportes import ColaReportes
from src.services.contratos import ArbolAVLProtocol, ArbolBusquedaProtocol
from src.services.escenario import Escenario, ParametrosEscenario, RelojSimulacion
from src.services.gestor_asociaciones import GestorAsociaciones
from src.services.historico import Historico
from src.services.reporte import Reporte
from src.services.zonas import VerificadorZonasRectangulares
from src.structures import ClaveEvento
from src.undo.pila_deshacer import PilaDeshacer

from .esquema import (
    arbol_a_documento,
    documento_a_nodos,
    evento_a_dict,
    evento_desde_dict,
    fecha_a_texto,
    fecha_desde_texto,
    zona_a_dict,
    zona_desde_dict,
)


@dataclass
class ResultadoCarga:
    exito: bool
    mensaje: str
    errores: list[str] = field(default_factory=list)


def _escribir_json_atomico(ruta: str, documento: dict) -> None:
    """Write-to-temp-then-replace so a crash or a full disk mid-write
    can never leave a half-written, corrupt file at `ruta` - the same
    atomicity principle the document asks for at the scenario level,
    applied here at the filesystem level too."""
    directorio = os.path.dirname(os.path.abspath(ruta)) or "."
    fd, ruta_temporal = tempfile.mkstemp(dir=directorio, prefix=".tmp_sismolab_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(documento, f, indent=2, ensure_ascii=False)
        os.replace(ruta_temporal, ruta)
    except BaseException:
        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)
        raise


class ServicioPersistencia:
    def __init__(self, escenario: Escenario, pila_deshacer: PilaDeshacer,
                 fabrica_arbol_avl: Callable[[], ArbolAVLProtocol],
                 fabrica_bst: Callable[[], ArbolBusquedaProtocol]) -> None:
        self._escenario = escenario
        self._pila = pila_deshacer
        self._fabrica_arbol_avl = fabrica_arbol_avl
        self._fabrica_bst = fabrica_bst

    # ------------------------------------------------------------------
    # Carga por inserciones (section 12)
    # ------------------------------------------------------------------

    def cargar_por_inserciones(self, ruta: str) -> ResultadoCarga:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                documento = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            return ResultadoCarga(False, "No se pudo leer el archivo.", [str(exc)])

        eventos_json = documento.get("eventos")
        if not isinstance(eventos_json, list) or not eventos_json:
            return ResultadoCarga(False, "El archivo no contiene una lista de eventos.", [])

        errores: list[str] = []
        vistos: set[int] = set()
        eventos = []
        for i, d in enumerate(eventos_json):
            try:
                evento = evento_desde_dict(d)
            except (ValueError, KeyError) as exc:
                errores.append(f"evento #{i}: {exc}")
                continue
            if evento.identificador in vistos:
                errores.append(
                    f"identificador {evento.identificador} duplicado en la "
                    f"secuencia de carga"
                )
                continue
            if evento.fecha_hora > self._escenario.reloj.ahora():
                errores.append(
                    f"evento {evento.identificador}: fecha_hora posterior "
                    f"al reloj de simulacion"
                )
                continue
            vistos.add(evento.identificador)
            eventos.append(evento)

        if errores:
            return ResultadoCarga(False, "Archivo invalido, no se aplico ningun cambio.", errores)

        # Construir AVL (con balanceo) y BST (sin balanceo) NUEVOS,
        # aplicando el MISMO comparador y el MISMO orden de insercion a
        # ambos (section 12), sin tocar el escenario en vivo todavia.
        nuevo_avl = self._fabrica_arbol_avl()
        nuevo_bst = self._fabrica_bst()
        for evento in eventos:
            zona_poblada = self._escenario.zonas.es_zona_poblada(
                evento.epicentro_x, evento.epicentro_y
            )
            prioridad = calcular_prioridad(evento.magnitud, evento.profundidad_hipocentro, zona_poblada)
            clave = ClaveEvento(prioridad, evento.magnitud, evento.identificador)
            nuevo_avl.insertar(clave, evento)
            nuevo_bst.insertar(clave, evento)

        snapshot_previo = self._escenario.clonar()
        self._escenario.arbol.restaurar_desde(nuevo_avl)
        self._escenario.bst_comparacion = nuevo_bst
        self._escenario.gestor_asociaciones.recalcular_todas()
        self._pila.registrar(
            f"Carga por inserciones ({len(eventos)} eventos) desde {ruta}",
            snapshot_previo, self._escenario.restaurar_desde,
        )
        return ResultadoCarga(True, f"{len(eventos)} eventos cargados en el AVL y el BST.")

    # ------------------------------------------------------------------
    # Carga por topologia (section 12)
    # ------------------------------------------------------------------

    def cargar_por_topologia(self, ruta: str) -> ResultadoCarga:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                documento = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            return ResultadoCarga(False, "No se pudo leer el archivo.", [str(exc)])

        modo = documento.get("modo", "normal")
        if modo not in ("normal", "estres"):
            return ResultadoCarga(
                False, "Archivo invalido.",
                [f"'modo' debe ser 'normal' o 'estres', recibido {modo!r}"],
            )

        raiz, errores = documento_a_nodos(
            documento,
            verificador_zona=self._escenario.zonas,
            calcular_prioridad_fn=calcular_prioridad,
            permitir_desbalance=(modo == "estres"),
        )
        if errores:
            return ResultadoCarga(False, "Topologia invalida, no se aplico ningun cambio.", errores)

        nuevo_avl = self._fabrica_arbol_avl()
        nuevo_avl.instalar_topologia(raiz)
        nuevo_avl.modo_estres = (modo == "estres")

        snapshot_previo = self._escenario.clonar()
        self._escenario.arbol.restaurar_desde(nuevo_avl)
        self._escenario.bst_comparacion = None  # no aplica a esta modalidad
        self._escenario.gestor_asociaciones.recalcular_todas()
        self._pila.registrar(
            f"Carga por topologia (modo {modo}) desde {ruta}",
            snapshot_previo, self._escenario.restaurar_desde,
        )
        return ResultadoCarga(True, f"Topologia cargada en modo {modo}.")

    # ------------------------------------------------------------------
    # Guardado estructural (section 12: exportacion completa)
    # ------------------------------------------------------------------

    def guardar_estructural(self, ruta: str) -> None:
        esc = self._escenario
        documento = {
            "arbol": arbol_a_documento(esc.arbol.obtener_raiz()),
            "modo": "estres" if esc.arbol.modo_estres else "normal",
            "historico": {
                "archivados": [evento_a_dict(e) for e in esc.historico.archivados.values()],
                "eliminados": [evento_a_dict(e) for e in esc.historico.eliminados.values()],
            },
            "estaciones": list(esc.estaciones),
            # Las asociaciones NO se serializan: se reconstruyen con la
            # politica determinista de GestorAsociaciones al cargar
            # (section 12 permite ambas opciones; reconstruir evita
            # guardar datos derivados que podrian desincronizarse del
            # resto del archivo).
            "cola": [_reporte_a_dict(r) for r in esc.cola.en_orden()],
            "reloj": fecha_a_texto(esc.reloj.ahora()),
            "zonas": [zona_a_dict(z) for z in esc.zonas.zonas()],
            "parametros": {
                "w_horas": esc.gestor_asociaciones.w_horas,
                "r_km": esc.gestor_asociaciones.r_km,
                "l": esc.parametros.limite_acceso_l,
                "t_horas": esc.parametros.umbral_archivo_t_horas,
            },
            "metricas": dict(esc.metricas),
        }
        _escribir_json_atomico(ruta, documento)

    def cargar_estructural(self, ruta: str, descripcion: Optional[str] = None) -> ResultadoCarga:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                documento = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            return ResultadoCarga(False, "No se pudo leer el archivo.", [str(exc)])

        errores: list[str] = []

        try:
            zonas = [zona_desde_dict(z) for z in documento.get("zonas", [])]
        except (ValueError, KeyError) as exc:
            errores.append(f"zonas: {exc}")
            zonas = []
        candidato_zonas = VerificadorZonasRectangulares(zonas)

        modo = documento.get("modo", "normal")
        if modo not in ("normal", "estres"):
            errores.append(f"'modo' debe ser 'normal' o 'estres', recibido {modo!r}")

        raiz, errores_arbol = documento_a_nodos(
            documento.get("arbol", {"raiz": None, "nodos": {}}),
            verificador_zona=candidato_zonas,
            calcular_prioridad_fn=calcular_prioridad,
            permitir_desbalance=(modo == "estres"),
        )
        errores.extend(errores_arbol)

        historico_doc = documento.get("historico", {})
        archivados: dict = {}
        eliminados: dict = {}
        try:
            for d in historico_doc.get("archivados", []):
                e = evento_desde_dict(d)
                archivados[e.identificador] = e
            for d in historico_doc.get("eliminados", []):
                e = evento_desde_dict(d)
                eliminados[e.identificador] = e
        except (ValueError, KeyError) as exc:
            errores.append(f"historico: {exc}")

        ids_activos: set[int] = set()

        def _recolectar_ids(nodo) -> None:
            if nodo is None:
                return
            ids_activos.add(nodo.clave.identificador)
            _recolectar_ids(nodo.izquierdo)
            _recolectar_ids(nodo.derecho)

        _recolectar_ids(raiz)

        # "Los eventos activos e historicos no pueden duplicar identidades."
        colecciones = [ids_activos, set(archivados), set(eliminados)]
        for i in range(len(colecciones)):
            for j in range(i + 1, len(colecciones)):
                interseccion = colecciones[i] & colecciones[j]
                if interseccion:
                    errores.append(
                        f"identificadores duplicados entre colecciones: {sorted(interseccion)}"
                    )

        try:
            reportes = [_reporte_desde_dict(d) for d in documento.get("cola", [])]
        except (ValueError, KeyError) as exc:
            errores.append(f"cola: {exc}")
            reportes = []

        try:
            instante_reloj = fecha_desde_texto(documento["reloj"])
        except (KeyError, ValueError) as exc:
            errores.append(f"reloj: {exc}")
            instante_reloj = None

        parametros_doc = documento.get("parametros", {})
        try:
            w_horas = float(parametros_doc["w_horas"])
            r_km = float(parametros_doc["r_km"])
            l = int(parametros_doc["l"])
            t_horas = float(parametros_doc["t_horas"])
            if w_horas <= 0 or r_km <= 0 or l < 0 or t_horas <= 0:
                raise ValueError("W, R y T deben ser positivos; L no puede ser negativo")
        except (KeyError, ValueError, TypeError) as exc:
            errores.append(f"parametros: {exc}")
            w_horas, r_km, l, t_horas = 48.0, 40.0, 3, 72.0

        if errores:
            return ResultadoCarga(False, "Escenario invalido, no se aplico ningun cambio.", errores)

        nuevo_avl = self._fabrica_arbol_avl()
        nuevo_avl.instalar_topologia(raiz)
        nuevo_avl.modo_estres = (modo == "estres")

        nuevo_historico = Historico()
        nuevo_historico.archivados = archivados
        nuevo_historico.eliminados = eliminados

        nuevo_gestor = GestorAsociaciones(nuevo_avl, nuevo_historico, w_horas, r_km)
        nuevo_gestor.recalcular_todas()

        nuevo_escenario = Escenario(
            arbol=nuevo_avl,
            historico=nuevo_historico,
            gestor_asociaciones=nuevo_gestor,
            cola=ColaReportes.desde_lista(reportes),
            reloj=RelojSimulacion(instante_reloj),
            zonas=candidato_zonas,
            estaciones=list(documento.get("estaciones", [])),
            parametros=ParametrosEscenario(limite_acceso_l=l, umbral_archivo_t_horas=t_horas),
            metricas=dict(documento.get("metricas", {})),
            bst_comparacion=None,
        )

        snapshot_previo = self._escenario.clonar()
        self._escenario.restaurar_desde(nuevo_escenario)
        self._pila.registrar(
            descripcion or f"Carga estructural desde {ruta}", snapshot_previo, self._escenario.restaurar_desde
        )
        return ResultadoCarga(True, "Escenario cargado.")


def _reporte_a_dict(r: Reporte) -> dict:
    return {
        "identificador": r.identificador,
        "magnitud": r.magnitud,
        "profundidad_hipocentro": r.profundidad_hipocentro,
        "epicentro_x": r.epicentro_x,
        "epicentro_y": r.epicentro_y,
        "fecha_hora": fecha_a_texto(r.fecha_hora),
        "revision": r.revision,
        "estacion": r.estacion,
    }


def _reporte_desde_dict(d: dict) -> Reporte:
    return Reporte(
        identificador=int(d["identificador"]),
        magnitud=float(d["magnitud"]),
        profundidad_hipocentro=float(d["profundidad_hipocentro"]),
        epicentro_x=float(d["epicentro_x"]),
        epicentro_y=float(d["epicentro_y"]),
        fecha_hora=fecha_desde_texto(d["fecha_hora"]),
        revision=int(d["revision"]),
        estacion=str(d["estacion"]),
    )
