"""Interfaz web para el Sistema de Gestión de Incidencias."""

from flask import Flask, render_template, request, redirect, url_for, flash
from incidencias.database import init_db
from incidencias import modelos, reportes

app = Flask(__name__)
app.secret_key = "incidencias-soporte-2024"

ESTADOS = ["abierta", "en_progreso", "en_espera", "resuelta", "cerrada"]
PRIORIDADES = ["baja", "media", "alta", "critica"]
CATEGORIAS = ["hardware", "software", "red", "email", "seguridad", "otro"]

ESTADO_COLOR = {
    "abierta": "primary",
    "en_progreso": "warning",
    "en_espera": "secondary",
    "resuelta": "success",
    "cerrada": "dark",
}
PRIORIDAD_COLOR = {
    "baja": "info",
    "media": "primary",
    "alta": "warning",
    "critica": "danger",
}


@app.context_processor
def utilidades():
    return dict(estado_color=ESTADO_COLOR, prioridad_color=PRIORIDAD_COLOR)


# ── Dashboard ────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    resumen = reportes.resumen_general()
    recientes = modelos.listar_incidencias()[:5]
    return render_template("dashboard.html", resumen=resumen, recientes=recientes)


# ── Incidencias ──────────────────────────────────────────────────────────

@app.route("/incidencias")
def lista_incidencias():
    estado = request.args.get("estado")
    prioridad = request.args.get("prioridad")
    items = modelos.listar_incidencias(estado=estado, prioridad=prioridad)
    return render_template("incidencias/lista.html", incidencias=items,
                           estados=ESTADOS, prioridades=PRIORIDADES,
                           filtro_estado=estado, filtro_prioridad=prioridad)


@app.route("/incidencias/nueva", methods=["GET", "POST"])
def nueva_incidencia():
    if request.method == "POST":
        modelos.crear_incidencia(
            titulo=request.form["titulo"],
            descripcion=request.form.get("descripcion") or None,
            prioridad=request.form.get("prioridad", "media"),
            categoria=request.form.get("categoria") or None,
            cliente_id=request.form.get("cliente_id") or None,
            tecnico_id=request.form.get("tecnico_id") or None,
        )
        flash("Incidencia creada correctamente", "success")
        return redirect(url_for("lista_incidencias"))
    clientes = modelos.listar_clientes()
    tecnicos = modelos.listar_tecnicos()
    return render_template("incidencias/form.html", incidencia=None,
                           clientes=clientes, tecnicos=tecnicos,
                           prioridades=PRIORIDADES, categorias=CATEGORIAS)


@app.route("/incidencias/<int:inc_id>")
def detalle_incidencia(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        flash("Incidencia no encontrada", "danger")
        return redirect(url_for("lista_incidencias"))
    notas = modelos.listar_notas(inc_id)
    tecnicos = modelos.listar_tecnicos()
    return render_template("incidencias/detalle.html", inc=inc, notas=notas,
                           estados=ESTADOS, tecnicos=tecnicos)


@app.route("/incidencias/<int:inc_id>/estado", methods=["POST"])
def cambiar_estado(inc_id):
    modelos.actualizar_incidencia(inc_id, estado=request.form["estado"])
    flash("Estado actualizado", "success")
    return redirect(url_for("detalle_incidencia", inc_id=inc_id))


@app.route("/incidencias/<int:inc_id>/asignar", methods=["POST"])
def asignar_tecnico(inc_id):
    tecnico_id = request.form.get("tecnico_id") or None
    modelos.actualizar_incidencia(inc_id, tecnico_id=tecnico_id)
    flash("Técnico asignado", "success")
    return redirect(url_for("detalle_incidencia", inc_id=inc_id))


@app.route("/incidencias/<int:inc_id>/nota", methods=["POST"])
def agregar_nota(inc_id):
    modelos.agregar_nota(
        incidencia_id=inc_id,
        contenido=request.form["contenido"],
        autor=request.form.get("autor") or None,
    )
    flash("Nota agregada", "success")
    return redirect(url_for("detalle_incidencia", inc_id=inc_id))


@app.route("/incidencias/<int:inc_id>/eliminar", methods=["POST"])
def eliminar_incidencia(inc_id):
    modelos.eliminar_incidencia(inc_id)
    flash("Incidencia eliminada", "success")
    return redirect(url_for("lista_incidencias"))


# ── Clientes ─────────────────────────────────────────────────────────────

@app.route("/clientes")
def lista_clientes():
    items = modelos.listar_clientes()
    return render_template("clientes/lista.html", clientes=items)


@app.route("/clientes/nuevo", methods=["GET", "POST"])
def nuevo_cliente():
    if request.method == "POST":
        modelos.crear_cliente(
            nombre=request.form["nombre"],
            email=request.form.get("email") or None,
            telefono=request.form.get("telefono") or None,
            empresa=request.form.get("empresa") or None,
        )
        flash("Cliente registrado", "success")
        return redirect(url_for("lista_clientes"))
    return render_template("clientes/form.html", cliente=None)


@app.route("/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
def editar_cliente(cliente_id):
    cliente = modelos.obtener_cliente(cliente_id)
    if not cliente:
        flash("Cliente no encontrado", "danger")
        return redirect(url_for("lista_clientes"))
    if request.method == "POST":
        modelos.actualizar_cliente(
            cliente_id,
            nombre=request.form["nombre"],
            email=request.form.get("email") or None,
            telefono=request.form.get("telefono") or None,
            empresa=request.form.get("empresa") or None,
        )
        flash("Cliente actualizado", "success")
        return redirect(url_for("lista_clientes"))
    return render_template("clientes/form.html", cliente=cliente)


@app.route("/clientes/<int:cliente_id>/eliminar", methods=["POST"])
def eliminar_cliente(cliente_id):
    modelos.eliminar_cliente(cliente_id)
    flash("Cliente eliminado", "success")
    return redirect(url_for("lista_clientes"))


# ── Técnicos ─────────────────────────────────────────────────────────────

@app.route("/tecnicos")
def lista_tecnicos():
    items = modelos.listar_tecnicos(solo_activos=False)
    return render_template("tecnicos/lista.html", tecnicos=items)


@app.route("/tecnicos/nuevo", methods=["GET", "POST"])
def nuevo_tecnico():
    if request.method == "POST":
        modelos.crear_tecnico(
            nombre=request.form["nombre"],
            especialidad=request.form.get("especialidad") or None,
            email=request.form.get("email") or None,
            telefono=request.form.get("telefono") or None,
        )
        flash("Técnico registrado", "success")
        return redirect(url_for("lista_tecnicos"))
    return render_template("tecnicos/form.html", tecnico=None)


@app.route("/tecnicos/<int:tecnico_id>/editar", methods=["GET", "POST"])
def editar_tecnico(tecnico_id):
    tecnico = modelos.obtener_tecnico(tecnico_id)
    if not tecnico:
        flash("Técnico no encontrado", "danger")
        return redirect(url_for("lista_tecnicos"))
    if request.method == "POST":
        modelos.actualizar_tecnico(
            tecnico_id,
            nombre=request.form["nombre"],
            especialidad=request.form.get("especialidad") or None,
            email=request.form.get("email") or None,
            telefono=request.form.get("telefono") or None,
        )
        flash("Técnico actualizado", "success")
        return redirect(url_for("lista_tecnicos"))
    return render_template("tecnicos/form.html", tecnico=tecnico)


@app.route("/tecnicos/<int:tecnico_id>/desactivar", methods=["POST"])
def desactivar_tecnico(tecnico_id):
    modelos.desactivar_tecnico(tecnico_id)
    flash("Técnico desactivado", "success")
    return redirect(url_for("lista_tecnicos"))


# ── Reportes ─────────────────────────────────────────────────────────────

@app.route("/reportes")
def vista_reportes():
    resumen = reportes.resumen_general()
    por_tecnico = reportes.incidencias_por_tecnico()
    por_cliente = reportes.incidencias_por_cliente()
    por_categoria = reportes.incidencias_por_categoria()
    return render_template("reportes.html", resumen=resumen,
                           por_tecnico=por_tecnico, por_cliente=por_cliente,
                           por_categoria=por_categoria)


# ── Inicio ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
