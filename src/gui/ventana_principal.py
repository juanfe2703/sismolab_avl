"""VentanaPrincipal: top bar (reloj + deshacer) and the tab notebook.

Like every other module in this package, it only wires widgets to
service calls - it never decides what a report does, what counts as a
valid correction, etc. Each tab module exposes a single
`construir(padre, contexto) -> ttk.Frame` function.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from src.persistence.esquema import fecha_desde_texto
from src.services.acciones_escenario import avanzar_reloj

from . import (
    pestana_asociaciones,
    pestana_auditoria,
    pestana_catalogo,
    pestana_historico,
    pestana_mapa,
    pestana_persistencia,
    pestana_reportes,
    pestana_versiones,
)
from .contexto import ContextoApp


class VentanaPrincipal:
    def __init__(self, raiz: tk.Tk, contexto: ContextoApp) -> None:
        self.raiz = raiz
        self.contexto = contexto

        self._construir_barra_superior()

        notebook = ttk.Notebook(raiz)
        notebook.pack(fill="both", expand=True, padx=4, pady=4)

        for titulo, modulo in [
            ("Catalogo activo", pestana_catalogo),
            ("Reportes y cola", pestana_reportes),
            ("Historico", pestana_historico),
            ("Asociaciones", pestana_asociaciones),
            ("Persistencia", pestana_persistencia),
            ("Versiones", pestana_versiones),
            ("Auditoria", pestana_auditoria),
            ("Mapa", pestana_mapa),
        ]:
            marco = modulo.construir(notebook, contexto)
            notebook.add(marco, text=titulo)

        contexto.suscribirse(self._refrescar_reloj)
        self._refrescar_reloj()

    def _construir_barra_superior(self) -> None:
        barra = ttk.Frame(self.raiz)
        barra.pack(fill="x", padx=4, pady=4)

        ttk.Label(barra, text="Reloj de simulacion:").pack(side="left")
        self.etiqueta_reloj = ttk.Label(barra, text="-", font=("TkDefaultFont", 10, "bold"))
        self.etiqueta_reloj.pack(side="left", padx=(4, 16))

        ttk.Button(barra, text="Avanzar reloj...", command=self._avanzar_reloj).pack(side="left")
        ttk.Button(barra, text="Deshacer (Ctrl+Z)", command=self._deshacer).pack(side="left", padx=(8, 0))

        self.raiz.bind_all("<Control-z>", lambda _evento: self._deshacer())

    def _refrescar_reloj(self) -> None:
        self.etiqueta_reloj.config(text=self.contexto.escenario.reloj.ahora().isoformat())

    def _avanzar_reloj(self) -> None:
        actual = self.contexto.escenario.reloj.ahora().isoformat()
        texto = simpledialog.askstring(
            "Avanzar reloj",
            "Nuevo instante (ISO 8601, UTC), por ejemplo 2026-09-20T10:00:00Z:",
            initialvalue=actual, parent=self.raiz,
        )
        if not texto:
            return
        try:
            nuevo_instante = fecha_desde_texto(texto)
            avanzar_reloj(self.contexto.escenario, self.contexto.pila, nuevo_instante)
        except ValueError as exc:  # fecha mal formada o ValorInvalidoError (ambas heredan de ValueError)
            messagebox.showerror("Reloj invalido", str(exc))
            return
        self.contexto.notificar_cambio()

    def _deshacer(self) -> None:
        if not self.contexto.pila.puede_deshacer():
            messagebox.showinfo("Deshacer", "No hay acciones para deshacer.")
            return
        descripcion = self.contexto.pila.deshacer()
        self.contexto.notificar_cambio()
        messagebox.showinfo("Deshacer", f"Se deshizo: {descripcion}")
