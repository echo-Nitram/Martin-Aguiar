#!/usr/bin/env python3
"""Carga datos de ejemplo en el sistema de incidencias."""

from incidencias.database import init_db
from incidencias.modelos import (
    crear_cliente,
    crear_tecnico,
    crear_incidencia,
    agregar_nota,
    actualizar_incidencia,
)


def cargar_datos():
    init_db()

    # Clientes
    c1 = crear_cliente("María López", "maria@ejemplo.com", "11-4567-8901", "Consultora ABC")
    c2 = crear_cliente("Carlos García", "carlos@ejemplo.com", "11-2345-6789", "Tienda Online XYZ")
    c3 = crear_cliente("Ana Rodríguez", "ana@ejemplo.com", "11-8765-4321", "Estudio Contable JR")

    # Técnicos
    t1 = crear_tecnico("Juan Pérez", "Redes y conectividad", "juan@soporte.com", "11-1111-2222")
    t2 = crear_tecnico("Laura Martínez", "Software y sistemas", "laura@soporte.com", "11-3333-4444")
    t3 = crear_tecnico("Diego Torres", "Hardware", "diego@soporte.com", "11-5555-6666")

    # Incidencias
    i1 = crear_incidencia(
        "Sin acceso a internet en oficina principal",
        "El router no responde a ping. Las luces indicadoras están apagadas.",
        "critica", "red", c1, t1,
    )
    actualizar_incidencia(i1, estado="en_progreso")
    agregar_nota(i1, "Se verificó que el router necesita reinicio. Agendada visita.", "Juan Pérez")

    i2 = crear_incidencia(
        "Error al abrir sistema de facturación",
        "Aparece error 'conexión a base de datos rechazada' al iniciar la aplicación.",
        "alta", "software", c2, t2,
    )
    agregar_nota(i2, "Se revisaron los logs del servidor. El servicio MySQL estaba detenido.", "Laura Martínez")
    agregar_nota(i2, "Servicio reiniciado. Verificar que no se repita.", "Laura Martínez")
    actualizar_incidencia(i2, estado="resuelta")

    i3 = crear_incidencia(
        "PC no enciende después de corte de luz",
        "La fuente de poder hace un click y no arranca. Sin olor a quemado.",
        "alta", "hardware", c3, t3,
    )
    actualizar_incidencia(i3, estado="en_progreso")

    i4 = crear_incidencia(
        "Configurar cuentas de email para nuevos empleados",
        "Se necesitan 3 cuentas nuevas en el dominio de la empresa.",
        "media", "email", c1, t2,
    )

    i5 = crear_incidencia(
        "Instalar antivirus en equipos de ventas",
        "5 equipos del área de ventas no tienen antivirus actualizado.",
        "media", "seguridad", c2, None,
    )

    i6 = crear_incidencia(
        "Impresora de red no imprime",
        "La impresora HP del segundo piso no aparece en la red.",
        "baja", "red", c3, t1,
    )

    print("Datos de ejemplo cargados exitosamente:")
    print(f"  - {3} clientes")
    print(f"  - {3} técnicos")
    print(f"  - {6} incidencias")
    print(f"  - {3} notas")
    print("\nEjecuta 'python main.py' para iniciar el sistema.")


if __name__ == "__main__":
    cargar_datos()
