"""Pestana 'Versiones' (document, section 13)."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .contexto import ContextoApp


def construir(padre: ttk.Notebook, contexto: ContextoApp) -> ttk.Frame:
    marco = ttk.Frame(padre)

    lista = tk.Listbox(marco)
    lista.pack(side="left", fill="both", expand=True, padx=(0, 8))

    panel = ttk.Frame(marco, width=220)
    panel.pack(side="left", fill="y")
    panel.pack_propagate(False)

    def _refrescar() -> None:
        lista.delete(0, "end")
        for info in contexto.servicio_versiones.listar_versiones():
            lista.insert("end", f"{info.nombre}  ({info.guardado_en.isoformat()})")

    def _nombre_seleccionado():
        seleccion = lista.curselection()
        if not seleccion:
            return None
        versiones = contexto.servicio_versiones.listar_versiones()
        return versiones[seleccion[0]].nombre

    def _guardar() -> None:
        nombre = simpledialog.askstring("Guardar version", "Nombre de la version:", parent=marco)
        if not nombre:
            return
        try:
            contexto.servicio_versiones.guardar_version(nombre)
        except ValueError as exc:
            messagebox.showerror("Guardar version", str(exc))
            return
        _refrescar()

    def _restaurar() -> None:
        nombre = _nombre_seleccionado()
        if nombre is None:
            messagebox.showwarning("Restaurar", "Seleccione una version de la lista.")
            return
        if not messagebox.askyesno("Restaurar", f"¿Restaurar la version '{nombre}'? Puede deshacerse despues."):
            return
        resultado = contexto.servicio_versiones.restaurar_version(nombre)
        if not resultado.exito:
            messagebox.showerror("Restaurar", resultado.mensaje + "\n" + "\n".join(resultado.errores))
            return
        contexto.notificar_cambio()

    def _eliminar() -> None:
        nombre = _nombre_seleccionado()
        if nombre is None:
            messagebox.showwarning("Eliminar", "Seleccione una version de la lista.")
            return
        if not messagebox.askyesno("Eliminar", f"¿Eliminar la version '{nombre}' del disco?"):
            return
        contexto.servicio_versiones.eliminar_version(nombre)
        _refrescar()

    ttk.Button(panel, text="Guardar version actual...", command=_guardar).pack(fill="x", pady=4)
    ttk.Button(panel, text="Restaurar seleccionada", command=_restaurar).pack(fill="x", pady=4)
    ttk.Button(panel, text="Eliminar seleccionada", command=_eliminar).pack(fill="x", pady=4)
    ttk.Label(
        panel, wraplength=200,
        text="Las versiones se guardan en disco y persisten al cerrar el programa. "
             "No incluyen la pila de deshacer ni otras versiones.",
    ).pack(fill="x", pady=(16, 0))

    contexto.suscribirse(_refrescar)
    _refrescar()
    return marco
