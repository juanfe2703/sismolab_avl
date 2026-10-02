"""Pestana 'Asociaciones' (document, section 7)."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from src.services.acciones_escenario import cambiar_parametros_asociacion

from .contexto import ContextoApp


def construir(padre: ttk.Notebook, contexto: ContextoApp) -> ttk.Frame:
    marco = ttk.Frame(padre)

    marco_param = ttk.LabelFrame(marco, text="Parametros W y R")
    marco_param.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_param, text="W (horas)").grid(row=0, column=0, padx=4, pady=4)
    entrada_w = ttk.Entry(marco_param, width=10)
    entrada_w.insert(0, str(contexto.gestor_asociaciones.w_horas))
    entrada_w.grid(row=0, column=1)

    ttk.Label(marco_param, text="R (km)").grid(row=0, column=2, padx=4)
    entrada_r = ttk.Entry(marco_param, width=10)
    entrada_r.insert(0, str(contexto.gestor_asociaciones.r_km))
    entrada_r.grid(row=0, column=3)

    def _actualizar_parametros() -> None:
        try:
            w = float(entrada_w.get())
            r = float(entrada_r.get())
        except ValueError:
            messagebox.showerror("Parametros", "W y R deben ser numeros.")
            return
        try:
            cambiar_parametros_asociacion(contexto.escenario, contexto.pila, w_horas=w, r_km=r)
        except ValueError as exc:
            messagebox.showerror("Parametros", str(exc))
            return
        contexto.notificar_cambio()

    ttk.Button(marco_param, text="Actualizar (recalcula todo)", command=_actualizar_parametros).grid(
        row=0, column=4, padx=8
    )

    marco_consulta = ttk.Frame(marco)
    marco_consulta.pack(fill="both", expand=True)

    ttk.Label(marco_consulta, text="Identificador:").pack(side="top", anchor="w")
    fila_busqueda = ttk.Frame(marco_consulta)
    fila_busqueda.pack(fill="x")
    entrada_id = ttk.Entry(fila_busqueda)
    entrada_id.pack(side="left", fill="x", expand=True)

    texto_resultado = tk.Text(marco_consulta, height=18, wrap="word", state="disabled")

    def _formatear(evento, estado) -> str:
        return f"SIS-{evento.identificador:06d} (M{evento.magnitud}, {estado.name})"

    def _consultar() -> None:
        try:
            identificador = int(entrada_id.get())
        except ValueError:
            messagebox.showerror("Consultar", "El identificador debe ser un numero entero.")
            return
        resultado = contexto.gestor_asociaciones.consultar(identificador)
        texto_resultado.config(state="normal")
        texto_resultado.delete("1.0", "end")
        if resultado is None:
            texto_resultado.insert("1.0", "No se encontro un evento activo o archivado con ese id.")
            texto_resultado.config(state="disabled")
            return

        lineas = [f"Evento consultado: SIS-{resultado.evento.identificador:06d}\n"]
        lineas.append("Candidatos (mayor magnitud, antes, dentro de W/R):")
        if resultado.candidatos:
            for evento, estado in resultado.candidatos:
                lineas.append(f"  - {_formatear(evento, estado)}")
        else:
            lineas.append("  (ninguno)")

        lineas.append("\nReferencia elegida (criterio: magnitud > distancia > tiempo > id):")
        if resultado.referencia_elegida:
            evento, estado = resultado.referencia_elegida
            lineas.append(f"  {_formatear(evento, estado)}")
        else:
            lineas.append("  (sin asociacion)")

        lineas.append("\nEventos que usan este evento como referencia:")
        if resultado.eventos_que_lo_referencian:
            for evento, estado in resultado.eventos_que_lo_referencian:
                lineas.append(f"  - {_formatear(evento, estado)}")
        else:
            lineas.append("  (ninguno)")

        texto_resultado.insert("1.0", "\n".join(lineas))
        texto_resultado.config(state="disabled")

    ttk.Button(fila_busqueda, text="Consultar", command=_consultar).pack(side="left", padx=(4, 0))
    texto_resultado.pack(fill="both", expand=True, pady=(8, 0))

    return marco
