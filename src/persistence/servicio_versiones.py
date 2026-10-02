"""ServicioVersiones (document, section 13: 'Ademas de deshacer, el
usuario podra guardar versiones con nombre y restaurarlas por
seleccion').

This module adds almost no new logic on purpose: a named version IS a
structural export/import (section 13: 'Las versiones persisten
despues de cerrar el programa e incluyen el mismo estado operativo
definido para la exportacion'), so saving and restoring a version
reuse `ServicioPersistencia.guardar_estructural` /
`.cargar_estructural` verbatim - same atomicity, same validation, same
undo registration for restores. This file only adds:

    1. A NAME -> FILE index, so versions can be listed and looked up
       by the human-readable name the user chose, persisted alongside
       the version files themselves (so it survives a restart too).
    2. Filename sanitization, since a version name is free text (it
       could contain spaces, slashes, accents, emoji) but must become
       a safe path on disk.

Deliberately NOT stored inside a version file (section 13 is explicit
about both): the undo stack ('no necesitan contener la pila de
retroceso') and other versions ('ni otras versiones') - each version
file is exactly one `guardar_estructural` snapshot, nothing more.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from .esquema import fecha_a_texto, fecha_desde_texto
from .servicio_persistencia import ResultadoCarga, ServicioPersistencia, _escribir_json_atomico


@dataclass
class InfoVersion:
    nombre: str
    guardado_en: datetime
    archivo: str


class ServicioVersiones:
    def __init__(self, persistencia: ServicioPersistencia, directorio: str) -> None:
        self._persistencia = persistencia
        self._directorio = directorio
        os.makedirs(directorio, exist_ok=True)

    # ------------------------------------------------------------------
    # Indice nombre -> archivo (persistente, en el mismo directorio)
    # ------------------------------------------------------------------

    def _ruta_indice(self) -> str:
        return os.path.join(self._directorio, "versiones_index.json")

    def _leer_indice(self) -> dict:
        ruta = self._ruta_indice()
        if not os.path.exists(ruta):
            return {}
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f).get("versiones", {})
        except (OSError, json.JSONDecodeError):
            # Un indice corrupto no debe tumbar el programa: se trata
            # como "sin versiones" en vez de propagar la excepcion. Los
            # archivos de version en si no se tocan ni se pierden.
            return {}

    def _escribir_indice(self, versiones: dict) -> None:
        _escribir_json_atomico(self._ruta_indice(), {"versiones": versiones})

    @staticmethod
    def _archivo_para(nombre: str) -> str:
        """Deterministic, filesystem-safe filename for a free-text
        version name: a readable slug plus a short hash so two very
        different names that slugify to the same thing (e.g. 'a/b' and
        'a b') never collide."""
        slug = re.sub(r"[^A-Za-z0-9_-]+", "_", nombre).strip("_") or "version"
        sufijo = hashlib.sha1(nombre.encode("utf-8")).hexdigest()[:8]
        return f"{slug}_{sufijo}.json"

    # ------------------------------------------------------------------
    # Guardar (section 13)
    # ------------------------------------------------------------------

    def guardar_version(self, nombre: str) -> None:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("el nombre de la version no puede estar vacio")

        archivo = self._archivo_para(nombre)
        ruta = os.path.join(self._directorio, archivo)
        # Reutiliza el mismo guardado atomico que la exportacion
        # estructural: ya cubre topologia, historico, cola, reloj,
        # zonas, parametros, modo y metricas en un solo archivo.
        self._persistencia.guardar_estructural(ruta)

        indice = self._leer_indice()
        indice[nombre] = {
            "archivo": archivo,
            "guardado_en": fecha_a_texto(datetime.now(timezone.utc)),
        }
        self._escribir_indice(indice)

    # ------------------------------------------------------------------
    # Listar (para que el usuario elija, section 13: 'restaurarlas por
    # seleccion')
    # ------------------------------------------------------------------

    def listar_versiones(self) -> list[InfoVersion]:
        indice = self._leer_indice()
        versiones = [
            InfoVersion(
                nombre=nombre,
                guardado_en=fecha_desde_texto(datos["guardado_en"]),
                archivo=datos["archivo"],
            )
            for nombre, datos in indice.items()
        ]
        return sorted(versiones, key=lambda v: v.guardado_en, reverse=True)

    # ------------------------------------------------------------------
    # Restaurar (section 13: 'Restaurar una version es una accion que
    # puede deshacerse') - gratis, porque cargar_estructural YA
    # registra una accion de deshacer por su cuenta.
    # ------------------------------------------------------------------

    def restaurar_version(self, nombre: str) -> ResultadoCarga:
        indice = self._leer_indice()
        info = indice.get(nombre)
        if info is None:
            return ResultadoCarga(False, f"No existe una version llamada '{nombre}'.", [])

        ruta = os.path.join(self._directorio, info["archivo"])
        if not os.path.exists(ruta):
            return ResultadoCarga(
                False, f"El archivo de la version '{nombre}' no se encuentra en disco.", [],
            )

        return self._persistencia.cargar_estructural(
            ruta, descripcion=f"Restaurar version '{nombre}'"
        )

    # ------------------------------------------------------------------
    # Eliminar una version guardada. No es una accion de deshacer: el
    # documento no la menciona entre las acciones de la pila (seccion
    # 13 solo habla de guardar/restaurar versiones), y borrar un
    # archivo de version no toca el escenario en ejecucion en absoluto.
    # ------------------------------------------------------------------

    def eliminar_version(self, nombre: str) -> bool:
        indice = self._leer_indice()
        info = indice.pop(nombre, None)
        if info is None:
            return False
        ruta = os.path.join(self._directorio, info["archivo"])
        if os.path.exists(ruta):
            os.remove(ruta)
        self._escribir_indice(indice)
        return True
