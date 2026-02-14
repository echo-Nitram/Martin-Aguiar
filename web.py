"""Interfaz web para el Sistema de Gestión de Incidencias."""

import os
import csv
import io
import uuid
import logging
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    jsonify, Response, send_from_directory,
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user,
)
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename

from incidencias.database import init_db
from incidencias import modelos, reportes, ia
from incidencias.ia import IAError, IAConfigError, IALimitError

# ── Configuracion ────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "incidencias-soporte-2024")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "doc", "docx", "txt", "log", "csv", "xlsx"}

# ── Extensiones Flask ────────────────────────────────────────────────────

csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour"],
                  storage_uri="memory://")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Inicia sesion para acceder al sistema."
login_manager.login_message_category = "warning"

# ── Logging ──────────────────────────────────────────────────────────────

logging.basicConfig(
    filename="soporte.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Constantes ───────────────────────────────────────────────────────────

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
SLA_COLOR = {
    "en_tiempo": "success",
    "por_vencer": "warning",
    "vencido": "danger",
    "cumplido": "success",
    "sin_sla": "secondary",
}


# ── Auth (Flask-Login) ───────────────────────────────────────────────────

class User(UserMixin):
    def __init__(self, user_dict):
        self.id = user_dict["id"]
        self.username = user_dict["username"]
        self.nombre = user_dict["nombre"]
        self.role = user_dict["role"]
        self.cliente_id = user_dict.get("cliente_id")

    @property
    def es_staff(self):
        return self.role in ("admin", "tecnico")

    @property
    def es_cliente(self):
        return self.role == "cliente"

    @property
    def es_admin(self):
        return self.role == "admin"


@login_manager.user_loader
def load_user(user_id):
    u = modelos.obtener_usuario(int(user_id))
    return User(u) if u else None


# ── Filtros y Context Processor ──────────────────────────────────────────

@app.template_filter("hace")
def tiempo_relativo(fecha_str):
    if not fecha_str:
        return ""
    try:
        fecha = datetime.fromisoformat(str(fecha_str))
        delta = datetime.now() - fecha
        if delta.days > 30:
            return fecha.strftime("%d/%m/%Y")
        elif delta.days > 0:
            return f"hace {delta.days} dia{'s' if delta.days > 1 else ''}"
        elif delta.seconds > 3600:
            horas = delta.seconds // 3600
            return f"hace {horas} hora{'s' if horas > 1 else ''}"
        elif delta.seconds > 60:
            mins = delta.seconds // 60
            return f"hace {mins} minuto{'s' if mins > 1 else ''}"
        else:
            return "hace un momento"
    except (ValueError, TypeError):
        return str(fecha_str)


@app.context_processor
def utilidades():
    ia_disponible = bool(os.environ.get("ANTHROPIC_API_KEY"))
    notif_count = 0
    if current_user.is_authenticated:
        notif_count = modelos.contar_notificaciones_no_leidas(current_user.id)
    return dict(
        estado_color=ESTADO_COLOR,
        prioridad_color=PRIORIDAD_COLOR,
        sla_color=SLA_COLOR,
        ia_disponible=ia_disponible,
        notif_count=notif_count,
    )


# ── Validacion ───────────────────────────────────────────────────────────

def validar_texto(valor, max_len=500, campo="campo"):
    if not valor or not valor.strip():
        return None, f"El {campo} es obligatorio"
    valor = valor.strip()
    if len(valor) > max_len:
        return None, f"El {campo} no puede exceder {max_len} caracteres"
    return valor, None


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def staff_required(f):
    """Decorador que requiere rol admin o tecnico."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.es_staff:
            flash("No tenes permisos para acceder a esta seccion.", "danger")
            return redirect(url_for("landing"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorador que requiere rol admin."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.es_admin:
            flash("Solo los administradores pueden acceder a esta seccion.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


# ── Error Handlers ───────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", error="Pagina no encontrada", codigo=404), 404


@app.errorhandler(500)
def internal_error(error):
    logger.exception("Error interno del servidor")
    return render_template("error.html", error="Error interno del servidor", codigo=500), 500


# ── Login / Logout ───────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user_data = modelos.autenticar_usuario(username, password)
        if user_data:
            user = User(user_data)
            login_user(user)
            flash(f"Bienvenido, {user_data['nombre']}!", "success")
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            if user.es_cliente:
                return redirect(url_for("portal_dashboard"))
            return redirect(url_for("dashboard"))
        flash("Usuario o contrasena incorrectos", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesion cerrada", "info")
    return redirect(url_for("landing"))


# ── Landing Page (publica) ───────────────────────────────────────────────

@app.route("/")
def landing():
    if current_user.is_authenticated:
        if current_user.es_cliente:
            return redirect(url_for("portal_dashboard"))
        return redirect(url_for("dashboard"))
    # Mostrar articulos KB publicos en landing
    articulos = modelos.listar_articulos_kb(solo_publicados=True)[:3]
    return render_template("landing.html", articulos_kb=articulos)


# ── Registro de Clientes (publico) ──────────────────────────────────────

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("landing"))
    if request.method == "POST":
        nombre, err = validar_texto(request.form.get("nombre"), 200, "nombre")
        if err:
            flash(err, "danger")
            return redirect(url_for("registro"))
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        email = request.form.get("email", "").strip() or None
        telefono = request.form.get("telefono", "").strip() or None
        empresa = request.form.get("empresa", "").strip() or None

        if not username or len(username) < 3:
            flash("El usuario debe tener al menos 3 caracteres", "danger")
            return redirect(url_for("registro"))
        if len(password) < 6:
            flash("La contrasena debe tener al menos 6 caracteres", "danger")
            return redirect(url_for("registro"))
        if password != password2:
            flash("Las contrasenas no coinciden", "danger")
            return redirect(url_for("registro"))
        if modelos.usuario_existe(username):
            flash("Ese nombre de usuario ya esta en uso", "danger")
            return redirect(url_for("registro"))

        cliente_id, user_id = modelos.registrar_cliente_usuario(
            nombre, email, telefono, empresa, username, password,
        )
        user_data = modelos.obtener_usuario(user_id)
        login_user(User(user_data))
        flash(f"Bienvenido {nombre}! Tu cuenta ha sido creada.", "success")
        return redirect(url_for("portal_dashboard"))
    return render_template("registro.html")


# ── Dashboard (staff) ───────────────────────────────────────────────────

@app.route("/panel")
@login_required
def dashboard():
    if current_user.es_cliente:
        return redirect(url_for("portal_dashboard"))
    resumen = reportes.resumen_general()
    recientes, _ = modelos.listar_incidencias(per_page=5)
    sla_stats = modelos.metricas_sla()
    satisf = modelos.promedio_satisfaccion()
    return render_template("dashboard.html", resumen=resumen, recientes=recientes,
                           sla_stats=sla_stats, satisfaccion=satisf)


# ── Dashboard Tecnico ───────────────────────────────────────────────────

@app.route("/mi-panel")
@login_required
@staff_required
def dashboard_tecnico():
    # Buscar tecnico_id que coincida con el nombre del usuario
    tecnicos = modelos.listar_tecnicos()
    mi_tecnico = None
    for t in tecnicos:
        if t["nombre"] == current_user.nombre:
            mi_tecnico = t
            break

    mis_incidencias = []
    total = 0
    if mi_tecnico:
        mis_incidencias, total = modelos.listar_incidencias(
            tecnico_id=mi_tecnico["id"], per_page=50
        )

    # Separar por estado
    activas = [i for i in mis_incidencias if i["estado"] not in ("resuelta", "cerrada")]
    resueltas = [i for i in mis_incidencias if i["estado"] in ("resuelta", "cerrada")]

    # Calcular SLA para activas
    for inc in activas:
        inc["sla"] = modelos.calcular_sla_incidencia(inc)

    return render_template(
        "mi_panel.html", activas=activas, resueltas=resueltas,
        total=total, tecnico=mi_tecnico,
    )


# ── Busqueda ─────────────────────────────────────────────────────────────

@app.route("/buscar")
@login_required
def buscar():
    q = request.args.get("q", "").strip()
    estado = request.args.get("estado")
    prioridad = request.args.get("prioridad")
    page = request.args.get("page", 1, type=int)
    if not q:
        return redirect(url_for("lista_incidencias"))
    resultados, total = modelos.buscar_incidencias(q, estado, prioridad, page)
    total_paginas = (total + 19) // 20
    return render_template(
        "incidencias/lista.html", incidencias=resultados,
        estados=ESTADOS, prioridades=PRIORIDADES,
        filtro_estado=estado, filtro_prioridad=prioridad,
        busqueda=q, page=page, total=total, total_paginas=total_paginas,
    )


# ── Incidencias ──────────────────────────────────────────────────────────

@app.route("/incidencias")
@login_required
def lista_incidencias():
    estado = request.args.get("estado")
    prioridad = request.args.get("prioridad")
    page = request.args.get("page", 1, type=int)
    items, total = modelos.listar_incidencias(estado=estado, prioridad=prioridad, page=page)
    total_paginas = (total + 19) // 20
    return render_template(
        "incidencias/lista.html", incidencias=items,
        estados=ESTADOS, prioridades=PRIORIDADES,
        filtro_estado=estado, filtro_prioridad=prioridad,
        page=page, total=total, total_paginas=total_paginas,
    )


@app.route("/incidencias/nueva", methods=["GET", "POST"])
@login_required
def nueva_incidencia():
    if request.method == "POST":
        titulo, err = validar_texto(request.form.get("titulo"), 200, "titulo")
        if err:
            flash(err, "danger")
            return redirect(url_for("nueva_incidencia"))
        inc_id = modelos.crear_incidencia(
            titulo=titulo,
            descripcion=request.form.get("descripcion") or None,
            prioridad=request.form.get("prioridad", "media"),
            categoria=request.form.get("categoria") or None,
            cliente_id=request.form.get("cliente_id") or None,
            tecnico_id=request.form.get("tecnico_id") or None,
        )
        modelos.registrar_auditoria(inc_id, current_user.nombre, "creacion")
        modelos.notificar_cambio_incidencia(
            inc_id, "Nueva incidencia",
            f"Se creo la incidencia #{inc_id}: {titulo}",
            url_for("detalle_incidencia", inc_id=inc_id),
        )
        flash("Incidencia creada correctamente", "success")
        return redirect(url_for("lista_incidencias"))
    clientes = modelos.listar_clientes()
    tecnicos = modelos.listar_tecnicos()
    return render_template(
        "incidencias/form.html", incidencia=None,
        clientes=clientes, tecnicos=tecnicos,
        prioridades=PRIORIDADES, categorias=CATEGORIAS,
    )


@app.route("/incidencias/<int:inc_id>")
@login_required
def detalle_incidencia(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        flash("Incidencia no encontrada", "danger")
        return redirect(url_for("lista_incidencias"))
    notas = modelos.listar_notas(inc_id)
    tecnicos = modelos.listar_tecnicos()
    adjuntos = modelos.listar_adjuntos(inc_id)
    historial_ia = modelos.listar_historial_ia(inc_id)
    auditoria = modelos.listar_auditoria(inc_id)
    sla = modelos.calcular_sla_incidencia(inc)
    satisf = modelos.obtener_satisfaccion(inc_id)
    return render_template(
        "incidencias/detalle.html", inc=inc, notas=notas,
        estados=ESTADOS, tecnicos=tecnicos, adjuntos=adjuntos,
        historial_ia=historial_ia, auditoria=auditoria,
        sla=sla, satisfaccion=satisf,
    )


@app.route("/incidencias/<int:inc_id>/estado", methods=["POST"])
@login_required
def cambiar_estado(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        flash("Incidencia no encontrada", "danger")
        return redirect(url_for("lista_incidencias"))
    nuevo_estado = request.form["estado"]
    viejo_estado = inc["estado"]
    modelos.actualizar_incidencia(inc_id, estado=nuevo_estado)
    modelos.registrar_auditoria(
        inc_id, current_user.nombre, "cambio_estado",
        "estado", viejo_estado, nuevo_estado,
    )
    modelos.notificar_cambio_incidencia(
        inc_id, "Estado actualizado",
        f"Incidencia #{inc_id} cambio de {viejo_estado} a {nuevo_estado}",
        url_for("detalle_incidencia", inc_id=inc_id),
    )
    flash("Estado actualizado", "success")
    return redirect(url_for("detalle_incidencia", inc_id=inc_id))


@app.route("/incidencias/<int:inc_id>/asignar", methods=["POST"])
@login_required
def asignar_tecnico(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        flash("Incidencia no encontrada", "danger")
        return redirect(url_for("lista_incidencias"))
    tecnico_id = request.form.get("tecnico_id") or None
    viejo = inc.get("tecnico_nombre") or "Ninguno"
    modelos.actualizar_incidencia(inc_id, tecnico_id=tecnico_id)
    nuevo = "Ninguno"
    if tecnico_id:
        t = modelos.obtener_tecnico(int(tecnico_id))
        nuevo = t["nombre"] if t else "Desconocido"
    modelos.registrar_auditoria(
        inc_id, current_user.nombre, "asignacion",
        "tecnico", viejo, nuevo,
    )
    modelos.notificar_cambio_incidencia(
        inc_id, "Tecnico asignado",
        f"Incidencia #{inc_id} asignada a {nuevo}",
        url_for("detalle_incidencia", inc_id=inc_id),
    )
    flash("Tecnico asignado", "success")
    return redirect(url_for("detalle_incidencia", inc_id=inc_id))


@app.route("/incidencias/<int:inc_id>/nota", methods=["POST"])
@login_required
def agregar_nota(inc_id):
    contenido, err = validar_texto(request.form.get("contenido"), 2000, "contenido")
    if err:
        flash(err, "danger")
        return redirect(url_for("detalle_incidencia", inc_id=inc_id))
    modelos.agregar_nota(
        incidencia_id=inc_id,
        contenido=contenido,
        autor=request.form.get("autor") or current_user.nombre,
    )
    modelos.registrar_auditoria(inc_id, current_user.nombre, "nota_agregada")
    modelos.notificar_cambio_incidencia(
        inc_id, "Nueva nota",
        f"Nueva nota en incidencia #{inc_id}",
        url_for("detalle_incidencia", inc_id=inc_id),
    )
    flash("Nota agregada", "success")
    return redirect(url_for("detalle_incidencia", inc_id=inc_id))


@app.route("/incidencias/<int:inc_id>/eliminar", methods=["POST"])
@login_required
def eliminar_incidencia(inc_id):
    modelos.eliminar_incidencia(inc_id)
    flash("Incidencia eliminada", "success")
    return redirect(url_for("lista_incidencias"))


# ── Satisfaccion ─────────────────────────────────────────────────────────

@app.route("/incidencias/<int:inc_id>/satisfaccion", methods=["POST"])
@login_required
def calificar_incidencia(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        flash("Incidencia no encontrada", "danger")
        return redirect(url_for("lista_incidencias"))
    puntuacion = request.form.get("puntuacion", type=int)
    if not puntuacion or puntuacion < 1 or puntuacion > 5:
        flash("Puntuacion invalida", "danger")
        return redirect(url_for("detalle_incidencia", inc_id=inc_id))
    comentario = request.form.get("comentario", "").strip() or None
    modelos.guardar_satisfaccion(inc_id, puntuacion, comentario)
    flash("Gracias por tu calificacion!", "success")
    # Redirect depends on role
    if current_user.es_cliente:
        return redirect(url_for("portal_detalle", inc_id=inc_id))
    return redirect(url_for("detalle_incidencia", inc_id=inc_id))


# ── Adjuntos ─────────────────────────────────────────────────────────────

@app.route("/incidencias/<int:inc_id>/adjunto", methods=["POST"])
@login_required
def subir_adjunto(inc_id):
    if "archivo" not in request.files:
        flash("No se selecciono ningun archivo", "danger")
        return redirect(url_for("detalle_incidencia", inc_id=inc_id))
    archivo = request.files["archivo"]
    if archivo.filename == "":
        flash("No se selecciono ningun archivo", "danger")
        return redirect(url_for("detalle_incidencia", inc_id=inc_id))
    if not allowed_file(archivo.filename):
        flash("Tipo de archivo no permitido", "danger")
        return redirect(url_for("detalle_incidencia", inc_id=inc_id))

    nombre_original = secure_filename(archivo.filename)
    ext = nombre_original.rsplit(".", 1)[1].lower() if "." in nombre_original else ""
    nombre_archivo = f"{uuid.uuid4().hex}.{ext}"
    ruta = os.path.join(UPLOAD_FOLDER, nombre_archivo)
    archivo.save(ruta)
    tamano = os.path.getsize(ruta)

    modelos.guardar_adjunto(
        incidencia_id=inc_id,
        nombre_archivo=nombre_archivo,
        nombre_original=nombre_original,
        mime_type=archivo.content_type,
        tamano=tamano,
        subido_por=current_user.nombre,
    )
    flash("Archivo adjuntado", "success")
    return redirect(url_for("detalle_incidencia", inc_id=inc_id))


@app.route("/adjuntos/<int:adjunto_id>")
@login_required
def descargar_adjunto(adjunto_id):
    adj = modelos.obtener_adjunto(adjunto_id)
    if not adj:
        flash("Adjunto no encontrado", "danger")
        return redirect(url_for("dashboard"))
    return send_from_directory(
        UPLOAD_FOLDER, adj["nombre_archivo"],
        download_name=adj["nombre_original"],
        as_attachment=True,
    )


# ── Exportar CSV ─────────────────────────────────────────────────────────

@app.route("/incidencias/exportar")
@login_required
def exportar_csv():
    estado = request.args.get("estado")
    prioridad = request.args.get("prioridad")
    items, _ = modelos.listar_incidencias(estado=estado, prioridad=prioridad, per_page=10000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Titulo", "Estado", "Prioridad", "Categoria",
                     "Cliente", "Tecnico", "Creada", "Actualizada"])
    for i in items:
        writer.writerow([
            i["id"], i["titulo"], i["estado"], i["prioridad"],
            i.get("categoria", ""), i.get("cliente_nombre", ""),
            i.get("tecnico_nombre", ""), i["creado_en"], i["actualizado_en"],
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=incidencias.csv"},
    )


# ── Clientes ─────────────────────────────────────────────────────────────

@app.route("/clientes")
@login_required
def lista_clientes():
    items = modelos.listar_clientes()
    return render_template("clientes/lista.html", clientes=items)


@app.route("/clientes/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_cliente():
    if request.method == "POST":
        nombre, err = validar_texto(request.form.get("nombre"), 200, "nombre")
        if err:
            flash(err, "danger")
            return redirect(url_for("nuevo_cliente"))
        modelos.crear_cliente(
            nombre=nombre,
            email=request.form.get("email") or None,
            telefono=request.form.get("telefono") or None,
            empresa=request.form.get("empresa") or None,
        )
        flash("Cliente registrado", "success")
        return redirect(url_for("lista_clientes"))
    return render_template("clientes/form.html", cliente=None)


@app.route("/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
@login_required
def editar_cliente(cliente_id):
    cliente = modelos.obtener_cliente(cliente_id)
    if not cliente:
        flash("Cliente no encontrado", "danger")
        return redirect(url_for("lista_clientes"))
    if request.method == "POST":
        nombre, err = validar_texto(request.form.get("nombre"), 200, "nombre")
        if err:
            flash(err, "danger")
            return redirect(url_for("editar_cliente", cliente_id=cliente_id))
        modelos.actualizar_cliente(
            cliente_id,
            nombre=nombre,
            email=request.form.get("email") or None,
            telefono=request.form.get("telefono") or None,
            empresa=request.form.get("empresa") or None,
        )
        flash("Cliente actualizado", "success")
        return redirect(url_for("lista_clientes"))
    return render_template("clientes/form.html", cliente=cliente)


@app.route("/clientes/<int:cliente_id>/eliminar", methods=["POST"])
@login_required
def eliminar_cliente(cliente_id):
    modelos.eliminar_cliente(cliente_id)
    flash("Cliente eliminado", "success")
    return redirect(url_for("lista_clientes"))


# ── Técnicos ─────────────────────────────────────────────────────────────

@app.route("/tecnicos")
@login_required
def lista_tecnicos():
    items = modelos.listar_tecnicos(solo_activos=False)
    return render_template("tecnicos/lista.html", tecnicos=items)


@app.route("/tecnicos/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_tecnico():
    if request.method == "POST":
        nombre, err = validar_texto(request.form.get("nombre"), 200, "nombre")
        if err:
            flash(err, "danger")
            return redirect(url_for("nuevo_tecnico"))
        modelos.crear_tecnico(
            nombre=nombre,
            especialidad=request.form.get("especialidad") or None,
            email=request.form.get("email") or None,
            telefono=request.form.get("telefono") or None,
        )
        flash("Tecnico registrado", "success")
        return redirect(url_for("lista_tecnicos"))
    return render_template("tecnicos/form.html", tecnico=None)


@app.route("/tecnicos/<int:tecnico_id>/editar", methods=["GET", "POST"])
@login_required
def editar_tecnico(tecnico_id):
    tecnico = modelos.obtener_tecnico(tecnico_id)
    if not tecnico:
        flash("Tecnico no encontrado", "danger")
        return redirect(url_for("lista_tecnicos"))
    if request.method == "POST":
        nombre, err = validar_texto(request.form.get("nombre"), 200, "nombre")
        if err:
            flash(err, "danger")
            return redirect(url_for("editar_tecnico", tecnico_id=tecnico_id))
        modelos.actualizar_tecnico(
            tecnico_id,
            nombre=nombre,
            especialidad=request.form.get("especialidad") or None,
            email=request.form.get("email") or None,
            telefono=request.form.get("telefono") or None,
        )
        flash("Tecnico actualizado", "success")
        return redirect(url_for("lista_tecnicos"))
    return render_template("tecnicos/form.html", tecnico=tecnico)


@app.route("/tecnicos/<int:tecnico_id>/desactivar", methods=["POST"])
@login_required
def desactivar_tecnico(tecnico_id):
    modelos.desactivar_tecnico(tecnico_id)
    flash("Tecnico desactivado", "success")
    return redirect(url_for("lista_tecnicos"))


# ── IA ───────────────────────────────────────────────────────────────────

def _ia_error_response(e):
    if isinstance(e, IAConfigError):
        return jsonify(error=str(e)), 503
    if isinstance(e, IALimitError):
        return jsonify(error=str(e)), 429
    return jsonify(error=str(e)), 500


@app.route("/incidencias/<int:inc_id>/ia/respuesta", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def ia_respuesta(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        return jsonify(error="Incidencia no encontrada"), 404
    notas = modelos.listar_notas(inc_id)
    contexto = request.form.get("contexto", "").strip()
    try:
        texto = ia.redactar_respuesta(inc, notas, contexto_usuario=contexto or None)
        modelos.guardar_historial_ia(inc_id, "respuesta", texto, contexto or None)
        return jsonify(resultado=texto)
    except IAError as e:
        return _ia_error_response(e)


@app.route("/incidencias/<int:inc_id>/ia/diagnostico", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def ia_diagnostico(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        return jsonify(error="Incidencia no encontrada"), 404
    notas = modelos.listar_notas(inc_id)
    try:
        texto = ia.diagnosticar(inc, notas)
        modelos.guardar_historial_ia(inc_id, "diagnostico", texto)
        return jsonify(resultado=texto)
    except IAError as e:
        return _ia_error_response(e)


@app.route("/incidencias/<int:inc_id>/ia/resumen", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def ia_resumen(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        return jsonify(error="Incidencia no encontrada"), 404
    notas = modelos.listar_notas(inc_id)
    try:
        texto = ia.resumir_incidencia(inc, notas)
        modelos.guardar_historial_ia(inc_id, "resumen", texto)
        return jsonify(resultado=texto)
    except IAError as e:
        return _ia_error_response(e)


@app.route("/ia/clasificar", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def ia_clasificar():
    titulo = request.form.get("titulo", "")
    descripcion = request.form.get("descripcion", "")
    if not titulo:
        return jsonify(error="Se requiere un titulo"), 400
    try:
        resultado = ia.auto_clasificar(titulo, descripcion)
        return jsonify(resultado)
    except IAError as e:
        return _ia_error_response(e)


# ── Chat IA ──────────────────────────────────────────────────────────────

@app.route("/incidencias/<int:inc_id>/ia/chat", methods=["POST"])
@login_required
@limiter.limit("15 per minute")
def ia_chat(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        return jsonify(error="Incidencia no encontrada"), 404
    mensaje = request.form.get("mensaje", "").strip()
    if not mensaje:
        return jsonify(error="Escribe un mensaje"), 400

    notas = modelos.listar_notas(inc_id)
    historial = modelos.listar_chat(inc_id)

    try:
        respuesta = ia.chat_incidencia(inc, notas, historial, mensaje)
        modelos.guardar_mensaje_chat(inc_id, "user", mensaje)
        modelos.guardar_mensaje_chat(inc_id, "assistant", respuesta)
        return jsonify(resultado=respuesta)
    except IAError as e:
        return _ia_error_response(e)


@app.route("/incidencias/<int:inc_id>/ia/chat/historial")
@login_required
def ia_chat_historial(inc_id):
    mensajes = modelos.listar_chat(inc_id)
    return jsonify(mensajes=mensajes)


@app.route("/incidencias/<int:inc_id>/ia/chat/limpiar", methods=["POST"])
@login_required
def ia_chat_limpiar(inc_id):
    modelos.limpiar_chat(inc_id)
    return jsonify(ok=True)


# ── Notificaciones ──────────────────────────────────────────────────────

@app.route("/notificaciones")
@login_required
def lista_notificaciones():
    notifs = modelos.listar_notificaciones(current_user.id)
    return render_template("notificaciones.html", notificaciones=notifs)


@app.route("/notificaciones/json")
@login_required
def notificaciones_json():
    notifs = modelos.listar_notificaciones(current_user.id, limite=10)
    count = modelos.contar_notificaciones_no_leidas(current_user.id)
    return jsonify(notificaciones=notifs, no_leidas=count)


@app.route("/notificaciones/<int:notif_id>/leer", methods=["POST"])
@login_required
def marcar_notificacion_leida(notif_id):
    modelos.marcar_notificacion_leida(notif_id, current_user.id)
    return jsonify(ok=True)


@app.route("/notificaciones/leer-todas", methods=["POST"])
@login_required
def marcar_todas_leidas():
    modelos.marcar_todas_leidas(current_user.id)
    flash("Todas las notificaciones marcadas como leidas", "success")
    return redirect(url_for("lista_notificaciones"))


# ── Base de Conocimiento ────────────────────────────────────────────────

@app.route("/conocimiento")
def kb_lista():
    categoria = request.args.get("categoria")
    termino = request.args.get("q", "").strip() or None
    articulos = modelos.listar_articulos_kb(categoria=categoria, termino=termino)
    return render_template(
        "kb/lista.html", articulos=articulos,
        categorias=CATEGORIAS, filtro_categoria=categoria, busqueda=termino,
    )


@app.route("/conocimiento/<int:art_id>")
def kb_detalle(art_id):
    art = modelos.obtener_articulo_kb(art_id)
    if not art or (not art["publicado"] and not (current_user.is_authenticated and current_user.es_staff)):
        flash("Articulo no encontrado", "danger")
        return redirect(url_for("kb_lista"))
    modelos.incrementar_visitas_kb(art_id)
    return render_template("kb/detalle.html", articulo=art)


@app.route("/conocimiento/nuevo", methods=["GET", "POST"])
@login_required
@staff_required
def kb_nuevo():
    if request.method == "POST":
        titulo, err = validar_texto(request.form.get("titulo"), 200, "titulo")
        if err:
            flash(err, "danger")
            return redirect(url_for("kb_nuevo"))
        contenido, err = validar_texto(request.form.get("contenido"), 10000, "contenido")
        if err:
            flash(err, "danger")
            return redirect(url_for("kb_nuevo"))
        modelos.crear_articulo_kb(
            titulo=titulo, contenido=contenido,
            categoria=request.form.get("categoria") or None,
            autor=current_user.nombre,
        )
        flash("Articulo publicado", "success")
        return redirect(url_for("kb_lista"))
    return render_template("kb/form.html", articulo=None, categorias=CATEGORIAS)


@app.route("/conocimiento/<int:art_id>/editar", methods=["GET", "POST"])
@login_required
@staff_required
def kb_editar(art_id):
    art = modelos.obtener_articulo_kb(art_id)
    if not art:
        flash("Articulo no encontrado", "danger")
        return redirect(url_for("kb_lista"))
    if request.method == "POST":
        titulo, err = validar_texto(request.form.get("titulo"), 200, "titulo")
        if err:
            flash(err, "danger")
            return redirect(url_for("kb_editar", art_id=art_id))
        contenido, err = validar_texto(request.form.get("contenido"), 10000, "contenido")
        if err:
            flash(err, "danger")
            return redirect(url_for("kb_editar", art_id=art_id))
        modelos.actualizar_articulo_kb(
            art_id, titulo=titulo, contenido=contenido,
            categoria=request.form.get("categoria") or None,
            publicado=1 if request.form.get("publicado") else 0,
        )
        flash("Articulo actualizado", "success")
        return redirect(url_for("kb_detalle", art_id=art_id))
    return render_template("kb/form.html", articulo=art, categorias=CATEGORIAS)


@app.route("/conocimiento/<int:art_id>/eliminar", methods=["POST"])
@login_required
@staff_required
def kb_eliminar(art_id):
    modelos.eliminar_articulo_kb(art_id)
    flash("Articulo eliminado", "success")
    return redirect(url_for("kb_lista"))


# ── Portal del Cliente ───────────────────────────────────────────────────

@app.route("/portal")
@login_required
def portal_dashboard():
    if current_user.es_staff:
        return redirect(url_for("dashboard"))
    items, total = modelos.listar_incidencias(cliente_id=current_user.cliente_id)

    activas = [i for i in items if i["estado"] not in ("resuelta", "cerrada")]
    historial = [i for i in items if i["estado"] in ("resuelta", "cerrada")]

    return render_template(
        "portal/dashboard.html", incidencias=items,
        activas=activas, historial=historial, total=total,
        estado_color=ESTADO_COLOR, prioridad_color=PRIORIDAD_COLOR,
    )


@app.route("/portal/nueva", methods=["GET", "POST"])
@login_required
def portal_nueva_incidencia():
    if current_user.es_staff:
        return redirect(url_for("nueva_incidencia"))
    if request.method == "POST":
        titulo, err = validar_texto(request.form.get("titulo"), 200, "titulo")
        if err:
            flash(err, "danger")
            return redirect(url_for("portal_nueva_incidencia"))
        inc_id = modelos.crear_incidencia(
            titulo=titulo,
            descripcion=request.form.get("descripcion") or None,
            prioridad=request.form.get("prioridad", "media"),
            categoria=request.form.get("categoria") or None,
            cliente_id=current_user.cliente_id,
        )
        modelos.registrar_auditoria(inc_id, current_user.nombre, "creacion")
        modelos.notificar_cambio_incidencia(
            inc_id, "Nueva incidencia del cliente",
            f"El cliente creo la incidencia #{inc_id}: {titulo}",
            url_for("detalle_incidencia", inc_id=inc_id),
        )
        flash("Incidencia creada correctamente. Nuestro equipo la revisara pronto.", "success")
        return redirect(url_for("portal_dashboard"))
    return render_template(
        "portal/nueva_incidencia.html",
        prioridades=PRIORIDADES, categorias=CATEGORIAS,
    )


@app.route("/portal/incidencia/<int:inc_id>")
@login_required
def portal_detalle(inc_id):
    if current_user.es_staff:
        return redirect(url_for("detalle_incidencia", inc_id=inc_id))
    inc = modelos.obtener_incidencia(inc_id)
    if not inc or inc["cliente_id"] != current_user.cliente_id:
        flash("Incidencia no encontrada", "danger")
        return redirect(url_for("portal_dashboard"))
    notas = modelos.listar_notas(inc_id)
    adjuntos = modelos.listar_adjuntos(inc_id)
    sla = modelos.calcular_sla_incidencia(inc)
    satisf = modelos.obtener_satisfaccion(inc_id)
    return render_template(
        "portal/detalle.html", inc=inc, notas=notas, adjuntos=adjuntos,
        sla=sla, satisfaccion=satisf,
    )


@app.route("/portal/incidencia/<int:inc_id>/nota", methods=["POST"])
@login_required
def portal_agregar_nota(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc or inc["cliente_id"] != current_user.cliente_id:
        flash("Incidencia no encontrada", "danger")
        return redirect(url_for("portal_dashboard"))
    contenido, err = validar_texto(request.form.get("contenido"), 2000, "contenido")
    if err:
        flash(err, "danger")
        return redirect(url_for("portal_detalle", inc_id=inc_id))
    modelos.agregar_nota(inc_id, contenido, autor=current_user.nombre)
    modelos.notificar_cambio_incidencia(
        inc_id, "Nuevo mensaje del cliente",
        f"El cliente envio un mensaje en la incidencia #{inc_id}",
        url_for("detalle_incidencia", inc_id=inc_id),
    )
    flash("Mensaje enviado", "success")
    return redirect(url_for("portal_detalle", inc_id=inc_id))


@app.route("/portal/incidencia/<int:inc_id>/adjunto", methods=["POST"])
@login_required
def portal_subir_adjunto(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc or inc["cliente_id"] != current_user.cliente_id:
        flash("Incidencia no encontrada", "danger")
        return redirect(url_for("portal_dashboard"))
    if "archivo" not in request.files:
        flash("No se selecciono ningun archivo", "danger")
        return redirect(url_for("portal_detalle", inc_id=inc_id))
    archivo = request.files["archivo"]
    if archivo.filename == "" or not allowed_file(archivo.filename):
        flash("Archivo no valido o tipo no permitido", "danger")
        return redirect(url_for("portal_detalle", inc_id=inc_id))

    nombre_original = secure_filename(archivo.filename)
    ext = nombre_original.rsplit(".", 1)[1].lower() if "." in nombre_original else ""
    nombre_archivo = f"{uuid.uuid4().hex}.{ext}"
    ruta = os.path.join(UPLOAD_FOLDER, nombre_archivo)
    archivo.save(ruta)
    tamano = os.path.getsize(ruta)

    modelos.guardar_adjunto(inc_id, nombre_archivo, nombre_original,
                            archivo.content_type, tamano, current_user.nombre)
    flash("Archivo adjuntado", "success")
    return redirect(url_for("portal_detalle", inc_id=inc_id))


@app.route("/portal/incidencia/<int:inc_id>/reabrir", methods=["POST"])
@login_required
def portal_reabrir(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc or inc["cliente_id"] != current_user.cliente_id:
        flash("Incidencia no encontrada", "danger")
        return redirect(url_for("portal_dashboard"))
    if inc["estado"] not in ("resuelta", "cerrada"):
        flash("Solo se pueden reabrir incidencias resueltas o cerradas", "warning")
        return redirect(url_for("portal_detalle", inc_id=inc_id))
    modelos.actualizar_incidencia(inc_id, estado="abierta", cerrado_en=None)
    modelos.registrar_auditoria(inc_id, current_user.nombre, "reapertura",
                                "estado", inc["estado"], "abierta")
    modelos.notificar_cambio_incidencia(
        inc_id, "Incidencia reabierta",
        f"El cliente reabrio la incidencia #{inc_id}",
        url_for("detalle_incidencia", inc_id=inc_id),
    )
    flash("Incidencia reabierta. Nuestro equipo la revisara.", "success")
    return redirect(url_for("portal_detalle", inc_id=inc_id))


# ── API REST ─────────────────────────────────────────────────────────────

@app.route("/api/incidencias")
@login_required
def api_listar_incidencias():
    estado = request.args.get("estado")
    prioridad = request.args.get("prioridad")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)

    if current_user.es_cliente:
        items, total = modelos.listar_incidencias(
            estado=estado, prioridad=prioridad,
            cliente_id=current_user.cliente_id, page=page, per_page=per_page,
        )
    else:
        items, total = modelos.listar_incidencias(
            estado=estado, prioridad=prioridad, page=page, per_page=per_page,
        )

    return jsonify(incidencias=items, total=total, page=page, per_page=per_page)


@app.route("/api/incidencias/<int:inc_id>")
@login_required
def api_detalle_incidencia(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        return jsonify(error="No encontrada"), 404
    if current_user.es_cliente and inc["cliente_id"] != current_user.cliente_id:
        return jsonify(error="No autorizado"), 403
    notas = modelos.listar_notas(inc_id)
    sla = modelos.calcular_sla_incidencia(inc)
    return jsonify(incidencia=inc, notas=notas, sla=sla)


@app.route("/api/incidencias", methods=["POST"])
@login_required
def api_crear_incidencia():
    data = request.get_json() or {}
    titulo = (data.get("titulo") or "").strip()
    if not titulo:
        return jsonify(error="El titulo es obligatorio"), 400
    cliente_id = current_user.cliente_id if current_user.es_cliente else data.get("cliente_id")
    inc_id = modelos.crear_incidencia(
        titulo=titulo,
        descripcion=data.get("descripcion"),
        prioridad=data.get("prioridad", "media"),
        categoria=data.get("categoria"),
        cliente_id=cliente_id,
        tecnico_id=data.get("tecnico_id"),
    )
    modelos.registrar_auditoria(inc_id, current_user.nombre, "creacion")
    return jsonify(id=inc_id, mensaje="Incidencia creada"), 201


@app.route("/api/incidencias/<int:inc_id>/estado", methods=["PUT"])
@login_required
def api_cambiar_estado(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        return jsonify(error="No encontrada"), 404
    data = request.get_json() or {}
    nuevo_estado = data.get("estado")
    if nuevo_estado not in ESTADOS:
        return jsonify(error="Estado invalido"), 400
    modelos.actualizar_incidencia(inc_id, estado=nuevo_estado)
    modelos.registrar_auditoria(inc_id, current_user.nombre, "cambio_estado",
                                "estado", inc["estado"], nuevo_estado)
    return jsonify(ok=True, estado=nuevo_estado)


@app.route("/api/incidencias/<int:inc_id>/notas", methods=["POST"])
@login_required
def api_agregar_nota(inc_id):
    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        return jsonify(error="No encontrada"), 404
    if current_user.es_cliente and inc["cliente_id"] != current_user.cliente_id:
        return jsonify(error="No autorizado"), 403
    data = request.get_json() or {}
    contenido = (data.get("contenido") or "").strip()
    if not contenido:
        return jsonify(error="El contenido es obligatorio"), 400
    nota_id = modelos.agregar_nota(inc_id, contenido, autor=current_user.nombre)
    return jsonify(id=nota_id, mensaje="Nota agregada"), 201


@app.route("/api/estadisticas")
@login_required
@staff_required
def api_estadisticas():
    resumen = reportes.resumen_general()
    sla_stats = modelos.metricas_sla()
    satisf = modelos.promedio_satisfaccion()
    return jsonify(resumen=resumen, sla=sla_stats, satisfaccion=satisf)


# ── Reportes ─────────────────────────────────────────────────────────────

@app.route("/reportes")
@login_required
def vista_reportes():
    resumen = reportes.resumen_general()
    por_tecnico = reportes.incidencias_por_tecnico()
    por_cliente = reportes.incidencias_por_cliente()
    por_categoria = reportes.incidencias_por_categoria()
    sla_stats = modelos.metricas_sla()
    satisf = modelos.promedio_satisfaccion()
    return render_template(
        "reportes.html", resumen=resumen,
        por_tecnico=por_tecnico, por_cliente=por_cliente,
        por_categoria=por_categoria, sla_stats=sla_stats,
        satisfaccion=satisf,
    )


# ── Inicio ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    # Crear usuario admin si no existe
    if not modelos.usuario_existe("admin"):
        modelos.crear_usuario("admin", "admin123", "Administrador", "admin")
    app.run(debug=True, host="0.0.0.0", port=5000)
