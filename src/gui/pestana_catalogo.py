"""Pestana 'Catalogo activo' (document, section 6 + section 15's
'vista grafica del AVL').

The Treeview is built by walking the REAL node graph
(`arbol.obtener_raiz()`, left/right), so the indentation the person
sees on screen is the actual tree shape - not a flat list re-sorted to
look like one. This tab never computes a key, a priority, or decides
what counts as a valid correction: every button below calls straight
into `ServicioEventos` and only renders whatever `ResultadoOperacion`
comes back.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from src.persistence.esquema import fecha_a_texto, fecha_desde_texto

from .contexto import ContextoApp


def construir(padre: ttk.Notebook, contexto: ContextoApp) -> ttk.Frame:
    marco = ttk.Frame(padre)

    # ---------------- izquierda: arbol real ----------------
    marco_izq = ttk.Frame(marco)
    marco_izq.pack(side="left", fill="both", expand=True, padx=(0, 8))

    columnas = ("prioridad", "magnitud", "revision", "estado", "profundidad")
    arbol_vista = ttk.Treeview(marco_izq, columns=columnas, show="tree headings")
    arbol_vista.heading("#0", text="Identificador")
    for col, titulo in zip(columnas, ("Prioridad", "Magnitud", "Revision", "Estado", "Prof. nodo")):
        arbol_vista.heading(col, text=titulo)
        arbol_vista.column(col, width=90, anchor="center")
    arbol_vista.pack(fill="both", expand=True)

    # ---------------- derecha: formulario ----------------
    marco_der = ttk.Frame(marco, width=320)
    marco_der.pack(side="right", fill="y")
    marco_der.pack_propagate(False)

    campos = {}

    def _campo(etiqueta: str, valor_inicial: str = "") -> tk.Entry:
        ttk.Label(marco_der, text=etiqueta).pack(anchor="w", pady=(6, 0))
        entrada = ttk.Entry(marco_der)
        entrada.insert(0, valor_inicial)
        entrada.pack(fill="x")
        return entrada

    campos["identificador"] = _campo("Identificador")
    campos["magnitud"] = _campo("Magnitud")
    campos["profundidad"] = _campo("Profundidad hipocentro (km)")
    campos["x"] = _campo("Epicentro X")
    campos["y"] = _campo("Epicentro Y")
    campos["fecha"] = _campo("Fecha y hora (ISO, UTC)", fecha_a_texto(contexto.escenario.reloj.ahora()))

    ttk.Label(marco_der, text="Estacion").pack(anchor="w", pady=(6, 0))
    combo_estacion = ttk.Combobox(marco_der, values=contexto.escenario.estaciones, state="readonly")
    if contexto.escenario.estaciones:
        combo_estacion.current(0)
    combo_estacion.pack(fill="x")

    texto_resultado = tk.Text(marco_der, height=10, wrap="word", state="disabled")
    texto_resultado.pack(fill="both", expand=True, pady=(12, 0))

    def _mostrar(mensaje: str) -> None:
        texto_resultado.config(state="normal")
        texto_resultado.delete("1.0", "end")
        texto_resultado.insert("1.0", mensaje)
        texto_resultado.config(state="disabled")

    def _leer_formulario():
        return (
            int(campos["identificador"].get()),
            float(campos["magnitud"].get()),
            float(campos["profundidad"].get()),
            float(campos["x"].get()),
            float(campos["y"].get()),
            fecha_desde_texto(campos["fecha"].get()),
            combo_estacion.get(),
        )

    def _refrescar() -> None:
        arbol_vista.delete(*arbol_vista.get_children())
        raiz = contexto.escenario.arbol.obtener_raiz()

        def insertar_nodo(nodo, padre_iid: str, profundidad: int) -> None:
            if nodo is None:
                return
            evento = nodo.evento_ref
            iid = str(nodo.clave.identificador)
            arbol_vista.insert(
                padre_iid, "end", iid=iid, text=f"SIS-{evento.identificador:06d}",
                values=(
                    nodo.clave.prioridad.name, f"{nodo.clave.magnitud:.1f}",
                    evento.revision, evento.estado_atencion.value, profundidad,
                ),
            )
            insertar_nodo(nodo.izquierdo, iid, profundidad + 1)
            insertar_nodo(nodo.derecho, iid, profundidad + 1)

        insertar_nodo(raiz, "", 0)
        arbol_vista.update()

    def _seleccionado_id():
        seleccion = arbol_vista.selection()
        return int(seleccion[0]) if seleccion else None

    def _al_crear() -> None:
        try:
            identificador, magnitud, profundidad, x, y, fecha, estacion = _leer_formulario()
        except ValueError as exc:
            messagebox.showerror("Datos invalidos", f"Revise los campos numericos/fecha: {exc}")
            return
        resultado = contexto.servicio_eventos.dar_alta_manual(
            identificador, magnitud, profundidad, x, y, fecha, estacion
        )
        _mostrar(f"{resultado.tipo.name}: {resultado.mensaje}")
        _refrescar()
        contexto.notificar_cambio()

    def _al_corregir() -> None:
        identificador = _seleccionado_id()
        if identificador is None:
            messagebox.showwarning("Corregir", "Seleccione un evento del arbol primero.")
            return
        try:
            _, magnitud, profundidad, x, y, fecha, _ = _leer_formulario()
        except ValueError as exc:
            messagebox.showerror("Datos invalidos", f"Revise los campos numericos/fecha: {exc}")
            return
        resultado = contexto.servicio_eventos.corregir_manual(
            identificador, magnitud=magnitud, profundidad_hipocentro=profundidad,
            epicentro_x=x, epicentro_y=y, fecha_hora=fecha,
        )
        _mostrar(f"{resultado.tipo.name}: {resultado.mensaje}\n"
                 f"Rotaciones producidas: {resultado.rotaciones}")
        _refrescar()
        contexto.notificar_cambio()

    def _al_marcar_revisado() -> None:
        identificador = _seleccionado_id()
        if identificador is None:
            messagebox.showwarning("Marcar revisado", "Seleccione un evento del arbol primero.")
            return
        resultado = contexto.servicio_eventos.marcar_revisado(identificador)
        _mostrar(f"{resultado.tipo.name}: {resultado.mensaje}")
        _refrescar()
        contexto.notificar_cambio()

    def _al_eliminar() -> None:
        identificador = _seleccionado_id()
        if identificador is None:
            messagebox.showwarning("Eliminar", "Seleccione un evento del arbol primero.")
            return
        if not messagebox.askyesno("Eliminar", f"¿Eliminar el evento {identificador}?"):
            return
        resultado = contexto.servicio_eventos.eliminar_individual(identificador)
        _mostrar(f"{resultado.tipo.name}: {resultado.mensaje}\n"
                 f"Rotaciones producidas: {resultado.rotaciones}")
        _refrescar()
        contexto.notificar_cambio()

    def _al_consultar() -> None:
        identificador = _seleccionado_id()
        if identificador is None:
            messagebox.showwarning("Consultar", "Seleccione un evento del arbol primero.")
            return
        estado, evento = contexto.servicio_eventos.localizar_evento(identificador)
        if evento is None:
            _mostrar(f"Evento {identificador}: {estado.name}")
            return
        profundidad = contexto.escenario.arbol.profundidad_de(identificador) \
            if estado.name == "ACTIVO" else "-"
        factor = contexto.escenario.arbol.factor_balance_de(identificador) \
            if estado.name == "ACTIVO" else "-"
        _mostrar(
            f"Estado: {estado.name}\n"
            f"Magnitud: {evento.magnitud}  Profundidad: {evento.profundidad_hipocentro} km\n"
            f"Epicentro: ({evento.epicentro_x}, {evento.epicentro_y})\n"
            f"Fecha: {fecha_a_texto(evento.fecha_hora)}\n"
            f"Revision: {evento.revision}  Estado atencion: {evento.estado_atencion.value}\n"
            f"Estaciones: {', '.join(sorted(evento.estaciones_reportes)) or '-'}\n"
            f"Profundidad en el arbol: {profundidad}  Factor de balance: {factor}"
        )

    botonera = ttk.Frame(marco_der)
    botonera.pack(fill="x", pady=(8, 0))
    ttk.Button(botonera, text="Crear", command=_al_crear).pack(side="left", expand=True, fill="x")
    ttk.Button(botonera, text="Corregir sel.", command=_al_corregir).pack(side="left", expand=True, fill="x")

    botonera2 = ttk.Frame(marco_der)
    botonera2.pack(fill="x")
    ttk.Button(botonera2, text="Marcar revisado", command=_al_marcar_revisado).pack(side="left", expand=True, fill="x")
    ttk.Button(botonera2, text="Consultar", command=_al_consultar).pack(side="left", expand=True, fill="x")

    ttk.Button(marco_der, text="Eliminar seleccionado", command=_al_eliminar).pack(fill="x", pady=(0, 8))

    contexto.suscribirse(_refrescar)
    _refrescar()
    return marco
