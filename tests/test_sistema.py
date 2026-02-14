"""Tests del sistema de gestión de incidencias."""

import os
import tempfile
import unittest

# Configurar DB temporal antes de importar módulos
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB = _tmp.name
_tmp.close()

import incidencias.database as db
db.DB_PATH = TEST_DB

from incidencias.database import init_db, get_connection
from incidencias.modelos import (
    crear_cliente, listar_clientes, obtener_cliente, actualizar_cliente, eliminar_cliente,
    crear_tecnico, listar_tecnicos, obtener_tecnico, actualizar_tecnico, desactivar_tecnico,
    crear_incidencia, listar_incidencias, obtener_incidencia, actualizar_incidencia,
    eliminar_incidencia, agregar_nota, listar_notas,
)
from incidencias.reportes import (
    resumen_general, incidencias_por_tecnico, incidencias_por_cliente, incidencias_por_categoria,
)


class TestClientes(unittest.TestCase):
    def setUp(self):
        init_db()
        conn = get_connection()
        conn.execute("DELETE FROM notas")
        conn.execute("DELETE FROM incidencias")
        conn.execute("DELETE FROM clientes")
        conn.execute("DELETE FROM tecnicos")
        conn.commit()
        conn.close()

    def test_crear_y_obtener_cliente(self):
        cid = crear_cliente("Test User", "test@test.com", "123456", "TestCorp")
        cliente = obtener_cliente(cid)
        self.assertEqual(cliente["nombre"], "Test User")
        self.assertEqual(cliente["email"], "test@test.com")
        self.assertEqual(cliente["empresa"], "TestCorp")

    def test_listar_clientes(self):
        crear_cliente("Alice")
        crear_cliente("Bob")
        clientes = listar_clientes()
        self.assertEqual(len(clientes), 2)

    def test_actualizar_cliente(self):
        cid = crear_cliente("Viejo Nombre")
        actualizar_cliente(cid, nombre="Nuevo Nombre")
        cliente = obtener_cliente(cid)
        self.assertEqual(cliente["nombre"], "Nuevo Nombre")

    def test_eliminar_cliente(self):
        cid = crear_cliente("A Eliminar")
        eliminar_cliente(cid)
        self.assertIsNone(obtener_cliente(cid))


class TestTecnicos(unittest.TestCase):
    def setUp(self):
        init_db()
        conn = get_connection()
        conn.execute("DELETE FROM notas")
        conn.execute("DELETE FROM incidencias")
        conn.execute("DELETE FROM tecnicos")
        conn.commit()
        conn.close()

    def test_crear_y_obtener_tecnico(self):
        tid = crear_tecnico("Tech1", "Redes", "tech@test.com")
        tecnico = obtener_tecnico(tid)
        self.assertEqual(tecnico["nombre"], "Tech1")
        self.assertEqual(tecnico["especialidad"], "Redes")

    def test_listar_solo_activos(self):
        t1 = crear_tecnico("Activo")
        t2 = crear_tecnico("Inactivo")
        desactivar_tecnico(t2)
        activos = listar_tecnicos(solo_activos=True)
        self.assertEqual(len(activos), 1)
        self.assertEqual(activos[0]["nombre"], "Activo")

    def test_desactivar_tecnico(self):
        tid = crear_tecnico("A Desactivar")
        desactivar_tecnico(tid)
        tecnico = obtener_tecnico(tid)
        self.assertEqual(tecnico["activo"], 0)


class TestIncidencias(unittest.TestCase):
    def setUp(self):
        init_db()
        conn = get_connection()
        conn.execute("DELETE FROM notas")
        conn.execute("DELETE FROM incidencias")
        conn.execute("DELETE FROM clientes")
        conn.execute("DELETE FROM tecnicos")
        conn.commit()
        conn.close()
        self.cliente_id = crear_cliente("Cliente Test")
        self.tecnico_id = crear_tecnico("Tecnico Test", "General")

    def test_crear_incidencia(self):
        iid = crear_incidencia("Problema test", "Descripción", "alta", "software",
                               self.cliente_id, self.tecnico_id)
        inc = obtener_incidencia(iid)
        self.assertEqual(inc["titulo"], "Problema test")
        self.assertEqual(inc["prioridad"], "alta")
        self.assertEqual(inc["estado"], "abierta")

    def test_cambiar_estado(self):
        iid = crear_incidencia("Test estado")
        actualizar_incidencia(iid, estado="en_progreso")
        inc = obtener_incidencia(iid)
        self.assertEqual(inc["estado"], "en_progreso")

    def test_cerrar_registra_fecha(self):
        iid = crear_incidencia("Test cierre")
        actualizar_incidencia(iid, estado="resuelta")
        inc = obtener_incidencia(iid)
        self.assertEqual(inc["estado"], "resuelta")
        self.assertIsNotNone(inc["cerrado_en"])

    def test_filtrar_por_estado(self):
        crear_incidencia("Abierta 1")
        i2 = crear_incidencia("En progreso")
        actualizar_incidencia(i2, estado="en_progreso")
        abiertas = listar_incidencias(estado="abierta")
        self.assertEqual(len(abiertas), 1)

    def test_filtrar_por_prioridad(self):
        crear_incidencia("Alta", prioridad="alta")
        crear_incidencia("Baja", prioridad="baja")
        altas = listar_incidencias(prioridad="alta")
        self.assertEqual(len(altas), 1)

    def test_eliminar_incidencia(self):
        iid = crear_incidencia("A borrar")
        agregar_nota(iid, "Nota que se borra")
        eliminar_incidencia(iid)
        self.assertIsNone(obtener_incidencia(iid))
        self.assertEqual(len(listar_notas(iid)), 0)

    def test_notas(self):
        iid = crear_incidencia("Con notas")
        agregar_nota(iid, "Primera nota", "Admin")
        agregar_nota(iid, "Segunda nota", "Técnico")
        notas = listar_notas(iid)
        self.assertEqual(len(notas), 2)
        self.assertEqual(notas[0]["contenido"], "Primera nota")


class TestReportes(unittest.TestCase):
    def setUp(self):
        init_db()
        conn = get_connection()
        conn.execute("DELETE FROM notas")
        conn.execute("DELETE FROM incidencias")
        conn.execute("DELETE FROM clientes")
        conn.execute("DELETE FROM tecnicos")
        conn.commit()
        conn.close()

    def test_resumen_general(self):
        cid = crear_cliente("C1")
        tid = crear_tecnico("T1")
        crear_incidencia("I1", cliente_id=cid, tecnico_id=tid)
        i2 = crear_incidencia("I2", prioridad="alta")
        actualizar_incidencia(i2, estado="resuelta")

        stats = resumen_general()
        self.assertEqual(stats["total_incidencias"], 2)
        self.assertEqual(stats["abiertas"], 1)
        self.assertEqual(stats["total_clientes"], 1)
        self.assertEqual(stats["total_tecnicos"], 1)

    def test_incidencias_por_tecnico(self):
        tid = crear_tecnico("Tech1", "Redes")
        crear_incidencia("I1", tecnico_id=tid)
        datos = incidencias_por_tecnico()
        self.assertEqual(len(datos), 1)
        self.assertEqual(datos[0]["total"], 1)

    def test_incidencias_por_categoria(self):
        crear_incidencia("I1", categoria="red")
        crear_incidencia("I2", categoria="red")
        crear_incidencia("I3", categoria="software")
        datos = incidencias_por_categoria()
        self.assertEqual(len(datos), 2)


if __name__ == "__main__":
    unittest.main()
