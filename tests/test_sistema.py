"""Tests del sistema de gestion de incidencias."""

import os
import tempfile
import unittest

# Configurar DB temporal antes de importar modulos
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
    eliminar_incidencia, agregar_nota, listar_notas, buscar_incidencias,
    crear_usuario, autenticar_usuario, usuario_existe, registrar_cliente_usuario,
    guardar_historial_ia, listar_historial_ia,
    guardar_mensaje_chat, listar_chat, limpiar_chat,
    guardar_adjunto, listar_adjuntos, obtener_adjunto,
)
from incidencias.reportes import (
    resumen_general, incidencias_por_tecnico, incidencias_por_cliente, incidencias_por_categoria,
)


def _limpiar_tablas():
    """Limpia todas las tablas para tests."""
    conn = get_connection()
    for tabla in ["chat_ia", "historial_ia", "adjuntos", "notas", "incidencias",
                  "usuarios", "clientes", "tecnicos"]:
        conn.execute(f"DELETE FROM {tabla}")
    conn.commit()
    conn.close()


class TestClientes(unittest.TestCase):
    def setUp(self):
        init_db()
        _limpiar_tablas()

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
        _limpiar_tablas()

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
        _limpiar_tablas()
        self.cliente_id = crear_cliente("Cliente Test")
        self.tecnico_id = crear_tecnico("Tecnico Test", "General")

    def test_crear_incidencia(self):
        iid = crear_incidencia("Problema test", "Descripcion", "alta", "software",
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
        abiertas, total = listar_incidencias(estado="abierta")
        self.assertEqual(len(abiertas), 1)
        self.assertEqual(total, 1)

    def test_filtrar_por_prioridad(self):
        crear_incidencia("Alta", prioridad="alta")
        crear_incidencia("Baja", prioridad="baja")
        altas, total = listar_incidencias(prioridad="alta")
        self.assertEqual(len(altas), 1)
        self.assertEqual(total, 1)

    def test_paginacion(self):
        for i in range(25):
            crear_incidencia(f"Incidencia {i}")
        page1, total = listar_incidencias(page=1, per_page=10)
        self.assertEqual(len(page1), 10)
        self.assertEqual(total, 25)
        page3, _ = listar_incidencias(page=3, per_page=10)
        self.assertEqual(len(page3), 5)

    def test_eliminar_incidencia(self):
        iid = crear_incidencia("A borrar")
        agregar_nota(iid, "Nota que se borra")
        eliminar_incidencia(iid)
        self.assertIsNone(obtener_incidencia(iid))
        self.assertEqual(len(listar_notas(iid)), 0)

    def test_notas(self):
        iid = crear_incidencia("Con notas")
        agregar_nota(iid, "Primera nota", "Admin")
        agregar_nota(iid, "Segunda nota", "Tecnico")
        notas = listar_notas(iid)
        self.assertEqual(len(notas), 2)
        self.assertEqual(notas[0]["contenido"], "Primera nota")

    def test_buscar_incidencias(self):
        crear_incidencia("Error de red wifi", "No conecta")
        crear_incidencia("Problema con impresora", "No imprime")
        resultados, total = buscar_incidencias("red")
        self.assertEqual(total, 1)
        self.assertEqual(resultados[0]["titulo"], "Error de red wifi")

    def test_join_nombres(self):
        iid = crear_incidencia("Test join", cliente_id=self.cliente_id,
                               tecnico_id=self.tecnico_id)
        inc = obtener_incidencia(iid)
        self.assertEqual(inc["cliente_nombre"], "Cliente Test")
        self.assertEqual(inc["tecnico_nombre"], "Tecnico Test")


class TestUsuarios(unittest.TestCase):
    def setUp(self):
        init_db()
        _limpiar_tablas()

    def test_crear_y_autenticar(self):
        crear_usuario("testuser", "pass123", "Test User", "admin")
        user = autenticar_usuario("testuser", "pass123")
        self.assertIsNotNone(user)
        self.assertEqual(user["nombre"], "Test User")

    def test_password_incorrecto(self):
        crear_usuario("testuser", "pass123", "Test User")
        user = autenticar_usuario("testuser", "wrongpass")
        self.assertIsNone(user)

    def test_usuario_existe(self):
        crear_usuario("admin", "123", "Admin")
        self.assertTrue(usuario_existe("admin"))
        self.assertFalse(usuario_existe("noexiste"))

    def test_registrar_cliente_usuario(self):
        cid, uid = registrar_cliente_usuario(
            "Cliente Web", "web@test.com", "123", "WebCorp", "clienteweb", "pass123"
        )
        self.assertIsNotNone(cid)
        self.assertIsNotNone(uid)
        user = autenticar_usuario("clienteweb", "pass123")
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "cliente")
        self.assertEqual(user["cliente_id"], cid)
        cliente = obtener_cliente(cid)
        self.assertEqual(cliente["nombre"], "Cliente Web")
        self.assertEqual(cliente["empresa"], "WebCorp")

    def test_cliente_ve_sus_incidencias(self):
        cid, uid = registrar_cliente_usuario(
            "Test", "t@t.com", None, None, "testcli", "pass123"
        )
        c2 = crear_cliente("Otro Cliente")
        crear_incidencia("Mi problema", cliente_id=cid)
        crear_incidencia("Otro problema", cliente_id=c2)
        mis, total = listar_incidencias(cliente_id=cid)
        self.assertEqual(total, 1)
        self.assertEqual(mis[0]["titulo"], "Mi problema")


class TestHistorialIA(unittest.TestCase):
    def setUp(self):
        init_db()
        _limpiar_tablas()

    def test_guardar_y_listar(self):
        iid = crear_incidencia("Test IA")
        guardar_historial_ia(iid, "respuesta", "Texto de respuesta", "contexto")
        guardar_historial_ia(iid, "diagnostico", "Texto diagnostico")
        historial = listar_historial_ia(iid)
        self.assertEqual(len(historial), 2)
        tipos = {h["tipo"] for h in historial}
        self.assertIn("respuesta", tipos)
        self.assertIn("diagnostico", tipos)


class TestChatIA(unittest.TestCase):
    def setUp(self):
        init_db()
        _limpiar_tablas()

    def test_chat_flujo(self):
        iid = crear_incidencia("Test Chat")
        guardar_mensaje_chat(iid, "user", "Hola")
        guardar_mensaje_chat(iid, "assistant", "Hola, como puedo ayudarte?")
        msgs = listar_chat(iid)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[1]["contenido"], "Hola, como puedo ayudarte?")

    def test_limpiar_chat(self):
        iid = crear_incidencia("Test Limpiar")
        guardar_mensaje_chat(iid, "user", "msg")
        limpiar_chat(iid)
        self.assertEqual(len(listar_chat(iid)), 0)


class TestAdjuntos(unittest.TestCase):
    def setUp(self):
        init_db()
        _limpiar_tablas()

    def test_guardar_y_listar(self):
        iid = crear_incidencia("Test Adjuntos")
        aid = guardar_adjunto(iid, "abc123.pdf", "documento.pdf", "application/pdf", 1024, "Admin")
        adjuntos = listar_adjuntos(iid)
        self.assertEqual(len(adjuntos), 1)
        adj = obtener_adjunto(aid)
        self.assertEqual(adj["nombre_original"], "documento.pdf")
        self.assertEqual(adj["tamano"], 1024)


class TestReportes(unittest.TestCase):
    def setUp(self):
        init_db()
        _limpiar_tablas()

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
