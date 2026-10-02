"""Pestana 'Reportes y cola' (document, section 8).

The local Python list `_rafaga_pendiente` below is just UI staging -
reports typed in the form but not yet sent to the real FIFO
(`ColaReportes`). Nothing here decides whether a report becomes an
alta, a confirmacion, a conflicto, etc.: `ProcesadorCola` /
`ServicioEventos` do, and this tab only renders `ResultadoPaso`.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from src.persistence.esquema import fecha_a_texto, fecha_desde_texto
from src.services.reporte import Reporte

from .contexto import ContextoApp


def construir(padre: ttk.Notebook, contexto: ContextoApp) -> ttk.Frame:
    marco = ttk.Frame(padre)
    _rafaga_pendiente: list[Reporte] = []
    _generador_continuo = {"activo": None}

    # ---------------- izquierda: formar la rafaga ----------------
    marco_izq = ttk.Frame(marco, width=340)
    marco_izq.pack(side="left", fill="y", padx=(0, 8))
    marco_izq.pack_propagate(False)

    campos = {}

    def _campo(etiqueta: str, valor_inicial: str = "") -> tk.Entry:
        ttk.Label(marco_izq, text=etiqueta).pack(anchor="w", pady=(4, 0))
        entrada = ttk.Entry(marco_izq)
        entrada.insert(0, valor_inicial)
        entrada.pack(fill="x")
        return entrada

    campos["identificador"] = _campo("Identificador")
    campos["magnitud"] = _campo("Magnitud")
    campos["profundidad"] = _campo("Profundidad (km)")
    campos["x"] = _campo("Epicentro X")
    campos["y"] = _campo("Epicentro Y")
    campos["fecha"] = _campo("Fecha y hora (ISO, UTC)", fecha_a_texto(contexto.escenario.reloj.ahora()))
    campos["revision"] = _campo("Revision", "1")

    ttk.Label(marco_izq, text="Estacion").pack(anchor="w", pady=(4, 0))
    combo_estacion = ttk.Combobox(marco_izq, values=contexto.escenario.estaciones, state="readonly")
    if contexto.escenario.estaciones:
        combo_estacion.current(0)
    combo_estacion.pack(fill="x")

    lista_pendiente = tk.Listbox(marco_izq, height=8)
    lista_pendiente.pack(fill="both", expand=True, pady=(8, 0))

    def _agregar_a_rafaga() -> None:
        try:
            reporte = Reporte(
                identificador=int(campos["identificador"].get()),
                magnitud=float(campos["magnitud"].get()),
                profundidad_hipocentro=float(campos["profundidad"].get()),
                epicentro_x=float(campos["x"].get()),
                epicentro_y=float(campos["y"].get()),
                fecha_hora=fecha_desde_texto(campos["fecha"].get()),
                revision=int(campos["revision"].get()),
                estacion=combo_estacion.get(),
            )
        except ValueError as exc:
            messagebox.showerror("Datos invalidos", str(exc))
            return
        _rafaga_pendiente.append(reporte)
        lista_pendiente.insert(
            "end", f"{reporte.estacion} -> evento {reporte.identificador} (rev {reporte.revision})"
        )

    def _enviar_rafaga_a_cola() -> None:
        if not _rafaga_pendiente:
            messagebox.showwarning("Rafaga", "Agregue al menos un reporte antes de enviar.")
            return
        contexto.procesador_cola.preparar_rafaga(list(_rafaga_pendiente))
        _rafaga_pendiente.clear()
        lista_pendiente.delete(0, "end")
        contexto.notificar_cambio()

    ttk.Button(marco_izq, text="Agregar a la rafaga", command=_agregar_a_rafaga).pack(fill="x", pady=(8, 0))
    ttk.Button(marco_izq, text="Enviar rafaga a la cola", command=_enviar_rafaga_a_cola).pack(fill="x", pady=(4, 0))

    # ---------------- derecha: cola real + procesamiento ----------------
    marco_der = ttk.Frame(marco)
    marco_der.pack(side="left", fill="both", expand=True)

    ttk.Label(marco_der, text="Cola (orden de llegada, NO de prioridad):").pack(anchor="w")
    lista_cola = tk.Listbox(marco_der, height=10)
    lista_cola.pack(fill="both", expand=True)

    texto_resultado = tk.Text(marco_der, height=8, wrap="word", state="disabled")
    texto_resultado.pack(fill="both", expand=True, pady=(8, 0))

    def _mostrar(mensaje: str) -> None:
        texto_resultado.config(state="normal")
        texto_resultado.insert("end", mensaje + "\n")
        texto_resultado.see("end")
        texto_resultado.config(state="disabled")

    def _refrescar() -> None:
        lista_cola.delete(0, "end")
        for reporte in contexto.escenario.cola.en_orden():
            lista_cola.insert(
                "end", f"{reporte.estacion} -> evento {reporte.identificador} (rev {reporte.revision})"
            )

    def _mostrar_resultado_paso(paso) -> None:
        if not paso.hubo_reporte:
            _mostrar(paso.mensaje)
            return
        _mostrar(
            f"[{paso.estacion}] evento {paso.identificador} rev {paso.revision} -> "
            f"{paso.resultado.tipo.name} (rotaciones: {paso.rotaciones}) - {paso.resultado.mensaje}"
        )

    def _procesar_un_paso() -> None:
        paso = contexto.procesador_cola.procesar_un_paso()
        _mostrar_resultado_paso(paso)
        _refrescar()
        contexto.notificar_cambio()

    def _detener_continuo() -> None:
        _generador_continuo["activo"] = None

    def _procesar_continuo() -> None:
        if _generador_continuo["activo"] is not None:
            return  # ya esta corriendo
        generador = contexto.procesador_cola.procesar_continuo()
        _generador_continuo["activo"] = generador

        def siguiente_paso() -> None:
            if _generador_continuo["activo"] is not generador:
                return  # se detuvo desde afuera
            paso = next(generador, None)
            if paso is None:
                _generador_continuo["activo"] = None
                _mostrar("-- fin de la rafaga --")
                return
            _mostrar_resultado_paso(paso)
            _refrescar()
            contexto.notificar_cambio()
            marco_der.after(600, siguiente_paso)  # la "pausa entre pasos" vive aqui, en la GUI

        siguiente_paso()

    botonera = ttk.Frame(marco_der)
    botonera.pack(fill="x", pady=(8, 0))
    ttk.Button(botonera, text="Procesar un paso", command=_procesar_un_paso).pack(side="left", expand=True, fill="x")
    ttk.Button(botonera, text="Procesar continuo", command=_procesar_continuo).pack(side="left", expand=True, fill="x")
    ttk.Button(botonera, text="Detener", command=_detener_continuo).pack(side="left", expand=True, fill="x")

    contexto.suscribirse(_refrescar)
    _refrescar()
    return marco
