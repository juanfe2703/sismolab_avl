"""Pestana 'Persistencia' (document, section 12). Every button here
does exactly two things: open a file dialog, and call one
`ServicioPersistencia` method - never parses or validates JSON itself.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk

from .contexto import ContextoApp


def construir(padre: ttk.Notebook, contexto: ContextoApp) -> ttk.Frame:
    marco = ttk.Frame(padre)

    texto_resultado = tk.Text(marco, height=20, wrap="word", state="disabled")

    def _mostrar(resultado) -> None:
        texto_resultado.config(state="normal")
        texto_resultado.delete("1.0", "end")
        encabezado = "EXITO" if resultado.exito else "FALLO"
        texto_resultado.insert("1.0", f"{encabezado}: {resultado.mensaje}\n")
        for error in resultado.errores:
            texto_resultado.insert("end", f"  - {error}\n")
        texto_resultado.config(state="disabled")

    def _cargar_por_inserciones() -> None:
        ruta = filedialog.askopenfilename(title="Cargar por inserciones", filetypes=[("JSON", "*.json")])
        if not ruta:
            return
        resultado = contexto.servicio_persistencia.cargar_por_inserciones(ruta)
        _mostrar(resultado)
        contexto.notificar_cambio()

    def _cargar_por_topologia() -> None:
        ruta = filedialog.askopenfilename(title="Cargar por topologia", filetypes=[("JSON", "*.json")])
        if not ruta:
            return
        resultado = contexto.servicio_persistencia.cargar_por_topologia(ruta)
        _mostrar(resultado)
        contexto.notificar_cambio()

    def _cargar_estructural() -> None:
        ruta = filedialog.askopenfilename(title="Cargar escenario completo", filetypes=[("JSON", "*.json")])
        if not ruta:
            return
        resultado = contexto.servicio_persistencia.cargar_estructural(ruta)
        _mostrar(resultado)
        contexto.notificar_cambio()

    def _guardar_estructural() -> None:
        ruta = filedialog.asksaveasfilename(
            title="Guardar escenario completo", defaultextension=".json", filetypes=[("JSON", "*.json")]
        )
        if not ruta:
            return
        contexto.servicio_persistencia.guardar_estructural(ruta)
        texto_resultado.config(state="normal")
        texto_resultado.delete("1.0", "end")
        texto_resultado.insert("1.0", f"Escenario guardado en {ruta}")
        texto_resultado.config(state="disabled")

    ttk.Label(marco, text="Cargas parciales (solo reemplazan el catalogo activo):").pack(anchor="w")
    fila1 = ttk.Frame(marco)
    fila1.pack(fill="x", pady=4)
    ttk.Button(fila1, text="Cargar por inserciones...", command=_cargar_por_inserciones).pack(side="left", expand=True, fill="x")
    ttk.Button(fila1, text="Cargar por topologia...", command=_cargar_por_topologia).pack(side="left", expand=True, fill="x")

    ttk.Label(marco, text="Escenario completo:").pack(anchor="w", pady=(8, 0))
    fila2 = ttk.Frame(marco)
    fila2.pack(fill="x", pady=4)
    ttk.Button(fila2, text="Cargar escenario completo...", command=_cargar_estructural).pack(side="left", expand=True, fill="x")
    ttk.Button(fila2, text="Guardar escenario completo...", command=_guardar_estructural).pack(side="left", expand=True, fill="x")

    texto_resultado.pack(fill="both", expand=True, pady=(12, 0))
    return marco
