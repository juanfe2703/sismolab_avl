"""Pestana 'Auditoria' (document, section 14)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .contexto import ContextoApp


def construir(padre: ttk.Notebook, contexto: ContextoApp) -> ttk.Frame:
    marco = ttk.Frame(padre)

    panel_indicadores = ttk.LabelFrame(marco, text="Indicadores")
    panel_indicadores.pack(fill="x", pady=(0, 8))

    etiquetas = {}
    for i, clave in enumerate([
        "Eventos activos", "Archivados", "Eliminados", "Altura", "Hojas", "Modo",
    ]):
        ttk.Label(panel_indicadores, text=f"{clave}:").grid(row=0, column=2 * i, padx=4, pady=4, sticky="e")
        valor = ttk.Label(panel_indicadores, text="-")
        valor.grid(row=0, column=2 * i + 1, padx=(0, 12), sticky="w")
        etiquetas[clave] = valor

    panel_acciones = ttk.Frame(marco)
    panel_acciones.pack(fill="x", pady=(0, 8))

    texto = tk.Text(marco, height=18, wrap="word", state="disabled")

    def _mostrar(mensaje: str) -> None:
        texto.config(state="normal")
        texto.delete("1.0", "end")
        texto.insert("1.0", mensaje)
        texto.config(state="disabled")

    def _refrescar() -> None:
        arbol = contexto.escenario.arbol
        etiquetas["Eventos activos"].config(text=str(arbol.cantidad_nodos()))
        etiquetas["Archivados"].config(text=str(len(contexto.escenario.historico.archivados)))
        etiquetas["Eliminados"].config(text=str(len(contexto.escenario.historico.eliminados)))
        etiquetas["Altura"].config(text=str(arbol.altura()))
        etiquetas["Hojas"].config(text=str(arbol.cantidad_hojas()))
        etiquetas["Modo"].config(text="ESTRES" if arbol.modo_estres else "normal")

    def _formatear_evento(e) -> str:
        return f"SIS-{e.identificador:06d}(M{e.magnitud})"

    def _recorrido(nombre: str, generador) -> None:
        eventos = list(generador())
        _mostrar(f"Recorrido {nombre} ({len(eventos)} eventos):\n" +
                 ", ".join(_formatear_evento(e) for e in eventos))

    def _verificar_estructura() -> None:
        arbol = contexto.escenario.arbol
        reporte = contexto.servicio_auditoria.verificar(arbol, arbol.modo_estres)
        lineas = [f"Resultado: {'OK' if reporte.ok else 'CON PROBLEMAS'}"]
        if reporte.problemas:
            lineas.append("\nProblemas encontrados:")
            for p in reporte.problemas:
                lineas.append(f"  - evento {p.identificador}: {p.descripcion}")
        if reporte.nodos_en_desbalance_esperado:
            lineas.append(
                f"\nNodos en desbalance ESPERADO (modo estres): "
                f"{reporte.nodos_en_desbalance_esperado}"
            )
        _mostrar("\n".join(lineas))

    def _activar_modo_estres() -> None:
        contexto.escenario.arbol.activar_modo_estres()
        _refrescar()
        contexto.notificar_cambio()

    def _recuperar_balance() -> None:
        rotaciones = contexto.escenario.arbol.recuperar_balance()
        _mostrar(f"Balance recuperado. Rotaciones aplicadas: {rotaciones}")
        _refrescar()
        contexto.notificar_cambio()

    ttk.Button(panel_acciones, text="Verificar estructura", command=_verificar_estructura).pack(side="left", padx=2)
    ttk.Button(panel_acciones, text="Inorden", command=lambda: _recorrido("inorden", contexto.escenario.arbol.recorrido_inorden)).pack(side="left", padx=2)
    ttk.Button(panel_acciones, text="Preorden", command=lambda: _recorrido("preorden", contexto.escenario.arbol.recorrido_preorden)).pack(side="left", padx=2)
    ttk.Button(panel_acciones, text="Postorden", command=lambda: _recorrido("postorden", contexto.escenario.arbol.recorrido_postorden)).pack(side="left", padx=2)
    ttk.Button(panel_acciones, text="Por niveles", command=lambda: _recorrido("por niveles", contexto.escenario.arbol.recorrido_por_niveles)).pack(side="left", padx=2)
    ttk.Button(panel_acciones, text="Activar modo estres", command=_activar_modo_estres).pack(side="left", padx=(12, 2))
    ttk.Button(panel_acciones, text="Recuperar balance", command=_recuperar_balance).pack(side="left", padx=2)

    texto.pack(fill="both", expand=True)

    contexto.suscribirse(_refrescar)
    _refrescar()
    return marco
