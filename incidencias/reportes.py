"""Módulo de reportes y estadísticas del sistema de incidencias."""

from .database import get_connection


def resumen_general():
    """Retorna estadísticas generales del sistema."""
    conn = get_connection()
    stats = {}

    # Total por estado
    rows = conn.execute(
        "SELECT estado, COUNT(*) as total FROM incidencias GROUP BY estado"
    ).fetchall()
    stats["por_estado"] = {r["estado"]: r["total"] for r in rows}

    # Total por prioridad
    rows = conn.execute(
        "SELECT prioridad, COUNT(*) as total FROM incidencias GROUP BY prioridad"
    ).fetchall()
    stats["por_prioridad"] = {r["prioridad"]: r["total"] for r in rows}

    # Total general
    row = conn.execute("SELECT COUNT(*) as total FROM incidencias").fetchone()
    stats["total_incidencias"] = row["total"]

    # Abiertas (no resueltas ni cerradas)
    row = conn.execute(
        "SELECT COUNT(*) as total FROM incidencias WHERE estado NOT IN ('resuelta', 'cerrada')"
    ).fetchone()
    stats["abiertas"] = row["total"]

    # Total clientes y técnicos
    row = conn.execute("SELECT COUNT(*) as total FROM clientes").fetchone()
    stats["total_clientes"] = row["total"]
    row = conn.execute("SELECT COUNT(*) as total FROM tecnicos WHERE activo = 1").fetchone()
    stats["total_tecnicos"] = row["total"]

    conn.close()
    return stats


def incidencias_por_tecnico():
    """Retorna el conteo de incidencias abiertas por técnico."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.nombre, t.especialidad,
               COUNT(i.id) as total,
               SUM(CASE WHEN i.estado NOT IN ('resuelta', 'cerrada') THEN 1 ELSE 0 END) as abiertas
        FROM tecnicos t
        LEFT JOIN incidencias i ON t.id = i.tecnico_id
        WHERE t.activo = 1
        GROUP BY t.id
        ORDER BY abiertas DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def incidencias_por_cliente():
    """Retorna el conteo de incidencias por cliente."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.nombre, c.empresa,
               COUNT(i.id) as total,
               SUM(CASE WHEN i.estado NOT IN ('resuelta', 'cerrada') THEN 1 ELSE 0 END) as abiertas
        FROM clientes c
        LEFT JOIN incidencias i ON c.id = i.cliente_id
        GROUP BY c.id
        ORDER BY total DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def incidencias_por_categoria():
    """Retorna el conteo de incidencias por categoría."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT COALESCE(categoria, 'Sin categoría') as categoria,
               COUNT(*) as total,
               SUM(CASE WHEN estado NOT IN ('resuelta', 'cerrada') THEN 1 ELSE 0 END) as abiertas
        FROM incidencias
        GROUP BY categoria
        ORDER BY total DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
