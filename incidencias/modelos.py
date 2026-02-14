"""Modelos de datos - Operaciones CRUD para clientes, técnicos e incidencias."""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from .database import get_connection


# ── Clientes ──────────────────────────────────────────────────────────────

def crear_cliente(nombre, email=None, telefono=None, empresa=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clientes (nombre, email, telefono, empresa) VALUES (?, ?, ?, ?)",
        (nombre, email, telefono, empresa),
    )
    conn.commit()
    cliente_id = cursor.lastrowid
    conn.close()
    return cliente_id


def listar_clientes():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM clientes ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_cliente(cliente_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_cliente(cliente_id, **campos):
    if not campos:
        return False
    sets = ", ".join(f"{k} = ?" for k in campos)
    vals = list(campos.values()) + [cliente_id]
    conn = get_connection()
    conn.execute(f"UPDATE clientes SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()
    return True


def eliminar_cliente(cliente_id):
    conn = get_connection()
    conn.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    conn.commit()
    conn.close()
    return True


# ── Técnicos ──────────────────────────────────────────────────────────────

def crear_tecnico(nombre, especialidad=None, email=None, telefono=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tecnicos (nombre, especialidad, email, telefono) VALUES (?, ?, ?, ?)",
        (nombre, especialidad, email, telefono),
    )
    conn.commit()
    tecnico_id = cursor.lastrowid
    conn.close()
    return tecnico_id


def listar_tecnicos(solo_activos=True):
    conn = get_connection()
    query = "SELECT * FROM tecnicos"
    if solo_activos:
        query += " WHERE activo = 1"
    query += " ORDER BY nombre"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_tecnico(tecnico_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tecnicos WHERE id = ?", (tecnico_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_tecnico(tecnico_id, **campos):
    if not campos:
        return False
    sets = ", ".join(f"{k} = ?" for k in campos)
    vals = list(campos.values()) + [tecnico_id]
    conn = get_connection()
    conn.execute(f"UPDATE tecnicos SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()
    return True


def desactivar_tecnico(tecnico_id):
    return actualizar_tecnico(tecnico_id, activo=0)


# ── Incidencias ───────────────────────────────────────────────────────────

def crear_incidencia(titulo, descripcion=None, prioridad="media", categoria=None,
                     cliente_id=None, tecnico_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO incidencias
           (titulo, descripcion, prioridad, categoria, cliente_id, tecnico_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (titulo, descripcion, prioridad, categoria, cliente_id, tecnico_id),
    )
    conn.commit()
    inc_id = cursor.lastrowid
    conn.close()
    return inc_id


def listar_incidencias(estado=None, prioridad=None, tecnico_id=None, cliente_id=None,
                       page=1, per_page=20):
    conn = get_connection()
    base_query = """
        FROM incidencias i
        LEFT JOIN clientes c ON i.cliente_id = c.id
        LEFT JOIN tecnicos t ON i.tecnico_id = t.id
        WHERE 1=1
    """
    params = []
    if estado:
        base_query += " AND i.estado = ?"
        params.append(estado)
    if prioridad:
        base_query += " AND i.prioridad = ?"
        params.append(prioridad)
    if tecnico_id:
        base_query += " AND i.tecnico_id = ?"
        params.append(tecnico_id)
    if cliente_id:
        base_query += " AND i.cliente_id = ?"
        params.append(cliente_id)

    count_row = conn.execute(
        f"SELECT COUNT(*) as total {base_query}", params
    ).fetchone()
    total = count_row["total"]

    select_query = (
        f"SELECT i.*, c.nombre AS cliente_nombre, t.nombre AS tecnico_nombre {base_query}"
        f" ORDER BY i.creado_en DESC LIMIT ? OFFSET ?"
    )
    params.extend([per_page, (page - 1) * per_page])
    rows = conn.execute(select_query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


def buscar_incidencias(termino, estado=None, prioridad=None, page=1, per_page=20):
    conn = get_connection()
    base_query = """
        FROM incidencias i
        LEFT JOIN clientes c ON i.cliente_id = c.id
        LEFT JOIN tecnicos t ON i.tecnico_id = t.id
        WHERE (i.titulo LIKE ? OR i.descripcion LIKE ?)
    """
    params = [f"%{termino}%", f"%{termino}%"]
    if estado:
        base_query += " AND i.estado = ?"
        params.append(estado)
    if prioridad:
        base_query += " AND i.prioridad = ?"
        params.append(prioridad)

    count_row = conn.execute(
        f"SELECT COUNT(*) as total {base_query}", params
    ).fetchone()
    total = count_row["total"]

    select_query = (
        f"SELECT i.*, c.nombre AS cliente_nombre, t.nombre AS tecnico_nombre {base_query}"
        f" ORDER BY i.creado_en DESC LIMIT ? OFFSET ?"
    )
    params.extend([per_page, (page - 1) * per_page])
    rows = conn.execute(select_query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


def obtener_incidencia(inc_id):
    conn = get_connection()
    row = conn.execute(
        """SELECT i.*, c.nombre AS cliente_nombre, t.nombre AS tecnico_nombre
           FROM incidencias i
           LEFT JOIN clientes c ON i.cliente_id = c.id
           LEFT JOIN tecnicos t ON i.tecnico_id = t.id
           WHERE i.id = ?""",
        (inc_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_incidencia(inc_id, **campos):
    if not campos:
        return False
    campos["actualizado_en"] = datetime.now().isoformat()
    if campos.get("estado") in ("resuelta", "cerrada"):
        campos["cerrado_en"] = datetime.now().isoformat()
    sets = ", ".join(f"{k} = ?" for k in campos)
    vals = list(campos.values()) + [inc_id]
    conn = get_connection()
    conn.execute(f"UPDATE incidencias SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()
    return True


def eliminar_incidencia(inc_id):
    conn = get_connection()
    conn.execute("DELETE FROM chat_ia WHERE incidencia_id = ?", (inc_id,))
    conn.execute("DELETE FROM historial_ia WHERE incidencia_id = ?", (inc_id,))
    conn.execute("DELETE FROM adjuntos WHERE incidencia_id = ?", (inc_id,))
    conn.execute("DELETE FROM notas WHERE incidencia_id = ?", (inc_id,))
    conn.execute("DELETE FROM incidencias WHERE id = ?", (inc_id,))
    conn.commit()
    conn.close()
    return True


# ── Notas ─────────────────────────────────────────────────────────────────

def agregar_nota(incidencia_id, contenido, autor=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notas (incidencia_id, contenido, autor) VALUES (?, ?, ?)",
        (incidencia_id, contenido, autor),
    )
    conn.commit()
    nota_id = cursor.lastrowid
    conn.close()
    return nota_id


def listar_notas(incidencia_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM notas WHERE incidencia_id = ? ORDER BY creado_en",
        (incidencia_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Historial IA ──────────────────────────────────────────────────────────

def guardar_historial_ia(incidencia_id, tipo, respuesta, contexto_usuario=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO historial_ia (incidencia_id, tipo, respuesta, contexto_usuario)
           VALUES (?, ?, ?, ?)""",
        (incidencia_id, tipo, respuesta, contexto_usuario),
    )
    conn.commit()
    hist_id = cursor.lastrowid
    conn.close()
    return hist_id


def listar_historial_ia(incidencia_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM historial_ia WHERE incidencia_id = ? ORDER BY creado_en DESC",
        (incidencia_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Chat IA ───────────────────────────────────────────────────────────────

def guardar_mensaje_chat(incidencia_id, role, contenido):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_ia (incidencia_id, role, contenido) VALUES (?, ?, ?)",
        (incidencia_id, role, contenido),
    )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id


def listar_chat(incidencia_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM chat_ia WHERE incidencia_id = ? ORDER BY creado_en",
        (incidencia_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def limpiar_chat(incidencia_id):
    conn = get_connection()
    conn.execute("DELETE FROM chat_ia WHERE incidencia_id = ?", (incidencia_id,))
    conn.commit()
    conn.close()
    return True


# ── Usuarios ──────────────────────────────────────────────────────────────

def crear_usuario(username, password, nombre, role="tecnico", cliente_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO usuarios (username, password_hash, nombre, role, cliente_id)
           VALUES (?, ?, ?, ?, ?)""",
        (username, generate_password_hash(password), nombre, role, cliente_id),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def registrar_cliente_usuario(nombre, email, telefono, empresa, username, password):
    """Registra un cliente y crea su cuenta de usuario en una sola operacion."""
    cliente_id = crear_cliente(nombre, email, telefono, empresa)
    user_id = crear_usuario(username, password, nombre, role="cliente", cliente_id=cliente_id)
    return cliente_id, user_id


def autenticar_usuario(username, password):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE username = ? AND activo = 1",
        (username,),
    ).fetchone()
    conn.close()
    if row and check_password_hash(row["password_hash"], password):
        return dict(row)
    return None


def obtener_usuario(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def usuario_existe(username):
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM usuarios WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return row is not None


# ── Adjuntos ──────────────────────────────────────────────────────────────

def guardar_adjunto(incidencia_id, nombre_archivo, nombre_original,
                    mime_type=None, tamano=None, subido_por=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO adjuntos
           (incidencia_id, nombre_archivo, nombre_original, mime_type, tamano, subido_por)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (incidencia_id, nombre_archivo, nombre_original, mime_type, tamano, subido_por),
    )
    conn.commit()
    adj_id = cursor.lastrowid
    conn.close()
    return adj_id


def listar_adjuntos(incidencia_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM adjuntos WHERE incidencia_id = ? ORDER BY creado_en DESC",
        (incidencia_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_adjunto(adjunto_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM adjuntos WHERE id = ?", (adjunto_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── SLA ──────────────────────────────────────────────────────────────────

def obtener_sla_config():
    """Retorna la configuracion SLA como dict {prioridad: {resp, resol}}."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM sla_config").fetchall()
    conn.close()
    return {r["prioridad"]: dict(r) for r in rows}


def calcular_sla_incidencia(inc):
    """Calcula el estado SLA de una incidencia."""
    sla = obtener_sla_config()
    prioridad = inc.get("prioridad", "media")
    config = sla.get(prioridad)
    if not config:
        return {"porcentaje_resolucion": 0, "estado_sla": "sin_sla"}

    creado = datetime.fromisoformat(str(inc["creado_en"]))
    fin = datetime.now()
    if inc.get("cerrado_en"):
        fin = datetime.fromisoformat(str(inc["cerrado_en"]))

    horas = (fin - creado).total_seconds() / 3600
    resol_horas = config["tiempo_resolucion_horas"]
    resp_horas = config["tiempo_respuesta_horas"]
    pct_resol = min(100, (horas / resol_horas) * 100) if resol_horas else 100

    if inc["estado"] in ("resuelta", "cerrada"):
        estado_sla = "cumplido" if horas <= resol_horas else "vencido"
    elif horas > resol_horas:
        estado_sla = "vencido"
    elif horas > resol_horas * 0.75:
        estado_sla = "por_vencer"
    else:
        estado_sla = "en_tiempo"

    return {
        "porcentaje_resolucion": round(pct_resol, 1),
        "estado_sla": estado_sla,
        "horas_transcurridas": round(horas, 1),
        "limite_respuesta": resp_horas,
        "limite_resolucion": resol_horas,
    }


def metricas_sla():
    """Retorna metricas globales de SLA."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT i.*, s.tiempo_resolucion_horas
        FROM incidencias i
        JOIN sla_config s ON i.prioridad = s.prioridad
        WHERE i.estado IN ('resuelta', 'cerrada')
          AND i.cerrado_en IS NOT NULL
    """).fetchall()
    conn.close()

    if not rows:
        return {"total": 0, "cumplidos": 0, "vencidos": 0, "pct_cumplimiento": 0,
                "tiempo_promedio_horas": 0}

    cumplidos = 0
    total_horas = 0
    for r in rows:
        creado = datetime.fromisoformat(str(r["creado_en"]))
        cerrado = datetime.fromisoformat(str(r["cerrado_en"]))
        horas = (cerrado - creado).total_seconds() / 3600
        total_horas += horas
        if horas <= r["tiempo_resolucion_horas"]:
            cumplidos += 1

    total = len(rows)
    return {
        "total": total,
        "cumplidos": cumplidos,
        "vencidos": total - cumplidos,
        "pct_cumplimiento": round((cumplidos / total) * 100, 1) if total else 0,
        "tiempo_promedio_horas": round(total_horas / total, 1) if total else 0,
    }


# ── Auditoria ────────────────────────────────────────────────────────────

def registrar_auditoria(incidencia_id, usuario, accion, campo=None,
                        valor_anterior=None, valor_nuevo=None):
    conn = get_connection()
    conn.execute(
        """INSERT INTO auditoria (incidencia_id, usuario, accion, campo, valor_anterior, valor_nuevo)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (incidencia_id, usuario, accion, campo, valor_anterior, valor_nuevo),
    )
    conn.commit()
    conn.close()


def listar_auditoria(incidencia_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM auditoria WHERE incidencia_id = ? ORDER BY creado_en DESC",
        (incidencia_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Satisfaccion ─────────────────────────────────────────────────────────

def guardar_satisfaccion(incidencia_id, puntuacion, comentario=None):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO satisfaccion (incidencia_id, puntuacion, comentario)
           VALUES (?, ?, ?)""",
        (incidencia_id, puntuacion, comentario),
    )
    conn.commit()
    conn.close()


def obtener_satisfaccion(incidencia_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM satisfaccion WHERE incidencia_id = ?", (incidencia_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def promedio_satisfaccion():
    conn = get_connection()
    row = conn.execute(
        "SELECT AVG(puntuacion) as promedio, COUNT(*) as total FROM satisfaccion"
    ).fetchone()
    conn.close()
    return {"promedio": round(row["promedio"], 1) if row["promedio"] else 0,
            "total": row["total"]}


# ── Notificaciones ───────────────────────────────────────────────────────

def crear_notificacion(usuario_id, titulo, mensaje, enlace=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO notificaciones (usuario_id, titulo, mensaje, enlace)
           VALUES (?, ?, ?, ?)""",
        (usuario_id, titulo, mensaje, enlace),
    )
    conn.commit()
    nid = cursor.lastrowid
    conn.close()
    return nid


def listar_notificaciones(usuario_id, solo_no_leidas=False, limite=20):
    conn = get_connection()
    query = "SELECT * FROM notificaciones WHERE usuario_id = ?"
    params = [usuario_id]
    if solo_no_leidas:
        query += " AND leida = 0"
    query += " ORDER BY creado_en DESC LIMIT ?"
    params.append(limite)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def contar_notificaciones_no_leidas(usuario_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as total FROM notificaciones WHERE usuario_id = ? AND leida = 0",
        (usuario_id,),
    ).fetchone()
    conn.close()
    return row["total"]


def marcar_notificacion_leida(notificacion_id, usuario_id):
    conn = get_connection()
    conn.execute(
        "UPDATE notificaciones SET leida = 1 WHERE id = ? AND usuario_id = ?",
        (notificacion_id, usuario_id),
    )
    conn.commit()
    conn.close()


def marcar_todas_leidas(usuario_id):
    conn = get_connection()
    conn.execute(
        "UPDATE notificaciones SET leida = 1 WHERE usuario_id = ? AND leida = 0",
        (usuario_id,),
    )
    conn.commit()
    conn.close()


def notificar_cambio_incidencia(inc_id, titulo_notif, mensaje, enlace=None):
    """Notifica a todos los usuarios relacionados con una incidencia."""
    conn = get_connection()
    inc = conn.execute("SELECT * FROM incidencias WHERE id = ?", (inc_id,)).fetchone()
    if not inc:
        conn.close()
        return
    usuario_ids = set()
    if inc["cliente_id"]:
        rows = conn.execute(
            "SELECT id FROM usuarios WHERE cliente_id = ? AND activo = 1",
            (inc["cliente_id"],),
        ).fetchall()
        for r in rows:
            usuario_ids.add(r["id"])
    if inc["tecnico_id"]:
        rows = conn.execute(
            "SELECT id FROM usuarios WHERE role = 'tecnico' AND activo = 1"
        ).fetchall()
        for r in rows:
            usuario_ids.add(r["id"])
    rows = conn.execute(
        "SELECT id FROM usuarios WHERE role = 'admin' AND activo = 1"
    ).fetchall()
    for r in rows:
        usuario_ids.add(r["id"])
    conn.close()

    for uid in usuario_ids:
        crear_notificacion(uid, titulo_notif, mensaje, enlace)


# ── Base de Conocimiento ─────────────────────────────────────────────────

def crear_articulo_kb(titulo, contenido, categoria=None, autor=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO articulos_kb (titulo, contenido, categoria, autor)
           VALUES (?, ?, ?, ?)""",
        (titulo, contenido, categoria, autor),
    )
    conn.commit()
    aid = cursor.lastrowid
    conn.close()
    return aid


def listar_articulos_kb(categoria=None, solo_publicados=True, termino=None):
    conn = get_connection()
    query = "SELECT * FROM articulos_kb WHERE 1=1"
    params = []
    if solo_publicados:
        query += " AND publicado = 1"
    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)
    if termino:
        query += " AND (titulo LIKE ? OR contenido LIKE ?)"
        params.extend([f"%{termino}%", f"%{termino}%"])
    query += " ORDER BY creado_en DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_articulo_kb(articulo_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM articulos_kb WHERE id = ?", (articulo_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def incrementar_visitas_kb(articulo_id):
    conn = get_connection()
    conn.execute(
        "UPDATE articulos_kb SET visitas = visitas + 1 WHERE id = ?", (articulo_id,)
    )
    conn.commit()
    conn.close()


def actualizar_articulo_kb(articulo_id, **campos):
    if not campos:
        return False
    campos["actualizado_en"] = datetime.now().isoformat()
    sets = ", ".join(f"{k} = ?" for k in campos)
    vals = list(campos.values()) + [articulo_id]
    conn = get_connection()
    conn.execute(f"UPDATE articulos_kb SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()
    return True


def eliminar_articulo_kb(articulo_id):
    conn = get_connection()
    conn.execute("DELETE FROM articulos_kb WHERE id = ?", (articulo_id,))
    conn.commit()
    conn.close()
    return True
