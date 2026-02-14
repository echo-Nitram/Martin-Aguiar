"""Módulo de base de datos - Inicialización y conexión SQLite."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "incidencias.db")


def get_connection(db_path=None):
    """Retorna una conexión a la base de datos SQLite."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None):
    """Crea las tablas del sistema si no existen."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT,
            telefono TEXT,
            empresa TEXT,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tecnicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            especialidad TEXT,
            email TEXT,
            telefono TEXT,
            activo INTEGER DEFAULT 1,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS incidencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            estado TEXT DEFAULT 'abierta'
                CHECK(estado IN ('abierta', 'en_progreso', 'en_espera', 'resuelta', 'cerrada')),
            prioridad TEXT DEFAULT 'media'
                CHECK(prioridad IN ('baja', 'media', 'alta', 'critica')),
            categoria TEXT,
            cliente_id INTEGER,
            tecnico_id INTEGER,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cerrado_en TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (tecnico_id) REFERENCES tecnicos(id)
        );

        CREATE TABLE IF NOT EXISTS notas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incidencia_id INTEGER NOT NULL,
            contenido TEXT NOT NULL,
            autor TEXT,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (incidencia_id) REFERENCES incidencias(id)
        );

        CREATE TABLE IF NOT EXISTS historial_ia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incidencia_id INTEGER,
            tipo TEXT NOT NULL,
            respuesta TEXT NOT NULL,
            contexto_usuario TEXT,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (incidencia_id) REFERENCES incidencias(id)
        );

        CREATE TABLE IF NOT EXISTS chat_ia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incidencia_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            contenido TEXT NOT NULL,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (incidencia_id) REFERENCES incidencias(id)
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            nombre TEXT NOT NULL,
            role TEXT DEFAULT 'tecnico' CHECK(role IN ('admin', 'tecnico')),
            activo INTEGER DEFAULT 1,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS adjuntos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incidencia_id INTEGER NOT NULL,
            nombre_archivo TEXT NOT NULL,
            nombre_original TEXT NOT NULL,
            mime_type TEXT,
            tamano INTEGER,
            subido_por TEXT,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (incidencia_id) REFERENCES incidencias(id)
        );
    """)

    conn.commit()
    conn.close()
