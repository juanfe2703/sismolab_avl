"""Pestana 'Historico' (document, sections 6 and 10)."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from src.persistence.esquema import fecha_a_texto

from .contexto import ContextoApp


def construir(padre: ttk.Notebook, contexto: ContextoApp) -> ttk.Frame:
    marco = ttk.Frame(padre)

    marco_archivados = ttk.LabelFrame(marco, text="Archivados")
    marco_archivados.pack(side="left", fill="both", expand=True, padx=(0, 4))
    lista_archivados = tk.Listbox(marco_archivados)
    lista_archivados.pack(fill="both", expand=True)

    marco_eliminados = ttk.LabelFrame(marco, text="Eliminados")
    marco_eliminados.pack(side="left", fill="both", expand=True, padx=(4, 4))
    lista_eliminados = tk.Listbox(marco_eliminados)
    lista_eliminados.pack(fill="both", expand=True)

    marco_buscar = ttk.LabelFrame(marco, text="Buscar por identificador", width=320)
    marco_buscar.pack(side="left", fill="y", padx=(4, 0))
    marco_buscar.pack_propagate(False)

    entrada_id = ttk.Entry(marco_buscar)
    entrada_id.pack(fill="x", padx=4, pady=4)
    texto_resultado = tk.Text(marco_buscar, height=14, wrap="word", state="disabled")
    texto_resultado.pack(fill="both", expand=True, padx=4, pady=4)

    def _mostrar(mensaje: str) -> None:
        texto_resultado.config(state="normal")
        texto_resultado.delete("1.0", "end")
        texto_resultado.insert("1.0", mensaje)
        texto_resultado.config(state="disabled")

    def _buscar() -> None:
        try:
            identificador = int(entrada_id.get())
        except ValueError:
            messagebox.showerror("Buscar", "El identificador debe ser un numero entero.")
            return
        estado, evento = contexto.servicio_eventos.localizar_evento(identificador)
        if evento is None:
            _mostrar(f"Identificador {identificador}: {estado.name}")
            return
        _mostrar(
            f"Estado: {estado.name}\n"
            f"Magnitud: {evento.magnitud}  Profundidad: {evento.profundidad_hipocentro} km\n"
            f"Epicentro: ({evento.epicentro_x}, {evento.epicentro_y})\n"
            f"Fecha: {fecha_a_texto(evento.fecha_hora)}\n"
            f"Revision: {evento.revision}  Estado atencion: {evento.estado_atencion.value}\n"
            f"Estaciones: {', '.join(sorted(evento.estaciones_reportes)) or '-'}"
        )

    ttk.Button(marco_buscar, text="Buscar", command=_buscar).pack(fill="x", padx=4)

    def _refrescar() -> None:
        lista_archivados.delete(0, "end")
        for evento in contexto.escenario.historico.archivados.values():
            lista_archivados.insert(
                "end", f"SIS-{evento.identificador:06d}  M{evento.magnitud}  rev {evento.revision}"
            )
        lista_eliminados.delete(0, "end")
        for evento in contexto.escenario.historico.eliminados.values():
            lista_eliminados.insert(
                "end", f"SIS-{evento.identificador:06d}  M{evento.magnitud}  rev {evento.revision}"
            )

    contexto.suscribirse(_refrescar)
    _refrescar()
    return marco
