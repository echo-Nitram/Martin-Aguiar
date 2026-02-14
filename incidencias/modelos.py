"""Modelos de datos - Operaciones CRUD para clientes, técnicos e incidencias."""

from datetime import datetime
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


def listar_incidencias(estado=None, prioridad=None, tecnico_id=None, cliente_id=None):
    conn = get_connection()
    query = """
        SELECT i.*, c.nombre AS cliente_nombre, t.nombre AS tecnico_nombre
        FROM incidencias i
        LEFT JOIN clientes c ON i.cliente_id = c.id
        LEFT JOIN tecnicos t ON i.tecnico_id = t.id
        WHERE 1=1
    """
    params = []
    if estado:
        query += " AND i.estado = ?"
        params.append(estado)
    if prioridad:
        query += " AND i.prioridad = ?"
        params.append(prioridad)
    if tecnico_id:
        query += " AND i.tecnico_id = ?"
        params.append(tecnico_id)
    if cliente_id:
        query += " AND i.cliente_id = ?"
        params.append(cliente_id)
    query += " ORDER BY i.creado_en DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


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
