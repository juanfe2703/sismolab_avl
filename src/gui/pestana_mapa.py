"""Pestana 'Mapa' (document, section 15: 'una grafica donde se observe
el plano geografico con los eventos representados').

Plain Canvas, no external plotting library: the scenario's plane is
fixed at 0..1000 km on both axes (section 3), so mapping to pixels is
a single linear scale factor. Color encodes priority, read straight
from each node's own key (`clave.prioridad`) by walking the real node
graph - never recomputed here, since computing a priority is
`calcular_prioridad`'s job, not the GUI's.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .contexto import ContextoApp

_LADO_CANVAS = 560
_COLOR_POR_PRIORIDAD = {"ALTA": "#d9534f", "MEDIA": "#f0ad4e", "BAJA": "#5bc0de"}


def construir(padre: ttk.Notebook, contexto: ContextoApp) -> ttk.Frame:
    marco = ttk.Frame(padre)
    canvas = tk.Canvas(marco, width=_LADO_CANVAS, height=_LADO_CANVAS, background="white")
    canvas.pack(side="left", padx=8, pady=8)

    leyenda = ttk.Frame(marco)
    leyenda.pack(side="left", fill="y", padx=8, pady=8)
    ttk.Label(leyenda, text="Leyenda", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
    for nombre, color in _COLOR_POR_PRIORIDAD.items():
        fila = ttk.Frame(leyenda)
        fila.pack(anchor="w", pady=2)
        lienzo = tk.Canvas(fila, width=14, height=14, highlightthickness=0)
        lienzo.create_oval(2, 2, 12, 12, fill=color, outline="")
        lienzo.pack(side="left")
        ttk.Label(fila, text=nombre).pack(side="left", padx=4)
    ttk.Label(leyenda, text="Zona poblada", foreground="#333").pack(anchor="w", pady=(12, 0))
    ttk.Label(leyenda, text="Zona no poblada", foreground="#999").pack(anchor="w")

    def _escala(valor: float) -> float:
        # El plano del escenario va de 0 a 1000 km en ambos ejes (section 3).
        return (valor / 1000.0) * _LADO_CANVAS

    def _dibujar_evento(clave, evento) -> None:
        color = _COLOR_POR_PRIORIDAD.get(clave.prioridad.name, "black")
        cx = _escala(evento.epicentro_x)
        cy = _LADO_CANVAS - _escala(evento.epicentro_y)  # y hacia arriba en el mapa
        radio = 5
        canvas.create_oval(cx - radio, cy - radio, cx + radio, cy + radio, fill=color, outline="black")

    def _recorrer_y_dibujar(nodo) -> None:
        if nodo is None:
            return
        _dibujar_evento(nodo.clave, nodo.evento_ref)
        _recorrer_y_dibujar(nodo.izquierdo)
        _recorrer_y_dibujar(nodo.derecho)

    def _refrescar() -> None:
        canvas.delete("all")
        for zona in contexto.escenario.zonas.zonas():
            color = "#333333" if zona.poblada else "#cccccc"
            canvas.create_rectangle(
                _escala(zona.x_min), _LADO_CANVAS - _escala(zona.y_max),
                _escala(zona.x_max), _LADO_CANVAS - _escala(zona.y_min),
                outline=color, width=2,
            )
            canvas.create_text(
                _escala(zona.x_min) + 4, _LADO_CANVAS - _escala(zona.y_max) + 10,
                text=zona.identificador, anchor="w", fill=color, font=("TkDefaultFont", 8),
            )

        _recorrer_y_dibujar(contexto.escenario.arbol.obtener_raiz())

    contexto.suscribirse(_refrescar)
    _refrescar()
    return marco
