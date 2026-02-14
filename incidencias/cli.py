"""Interfaz de línea de comandos interactiva para el sistema de incidencias."""

import sys
from tabulate import tabulate
from . import modelos, reportes
from .database import init_db

# ── Utilidades de presentación ────────────────────────────────────────────

ESTADOS = ["abierta", "en_progreso", "en_espera", "resuelta", "cerrada"]
PRIORIDADES = ["baja", "media", "alta", "critica"]
CATEGORIAS = ["hardware", "software", "red", "email", "seguridad", "otro"]

PRIORIDAD_ICONO = {"baja": "▽", "media": "◇", "alta": "△", "critica": "⬆"}
ESTADO_ICONO = {
    "abierta": "○",
    "en_progreso": "◉",
    "en_espera": "◈",
    "resuelta": "●",
    "cerrada": "✓",
}


def limpiar_pantalla():
    print("\033[2J\033[H", end="")


def input_opcion(prompt, opciones):
    """Solicita al usuario elegir una opción numérica."""
    while True:
        try:
            valor = input(prompt).strip()
            if valor == "":
                return None
            num = int(valor)
            if 1 <= num <= len(opciones):
                return num
            print(f"  Ingrese un número entre 1 y {len(opciones)}")
        except ValueError:
            print("  Ingrese un número válido")


def input_texto(prompt, requerido=False):
    """Solicita texto al usuario."""
    while True:
        valor = input(prompt).strip()
        if valor or not requerido:
            return valor if valor else None
        print("  Este campo es requerido")


def input_seleccion(prompt, opciones):
    """Muestra opciones numeradas y retorna la selección."""
    for i, op in enumerate(opciones, 1):
        print(f"  {i}. {op}")
    sel = input_opcion(prompt, opciones)
    return opciones[sel - 1] if sel else None


def mostrar_banner():
    print("=" * 60)
    print("   SISTEMA DE GESTIÓN DE INCIDENCIAS")
    print("   Soporte Técnico")
    print("=" * 60)


# ── Menú principal ────────────────────────────────────────────────────────

def menu_principal():
    init_db()
    while True:
        print()
        mostrar_banner()
        print()
        opciones = [
            "Gestionar Incidencias",
            "Gestionar Clientes",
            "Gestionar Técnicos",
            "Reportes y Estadísticas",
            "Salir",
        ]
        for i, op in enumerate(opciones, 1):
            print(f"  {i}. {op}")
        print()
        sel = input_opcion("Seleccione una opción: ", opciones)
        if sel == 1:
            menu_incidencias()
        elif sel == 2:
            menu_clientes()
        elif sel == 3:
            menu_tecnicos()
        elif sel == 4:
            menu_reportes()
        elif sel == 5:
            print("\n¡Hasta luego!")
            sys.exit(0)


# ── Menú de Incidencias ──────────────────────────────────────────────────

def menu_incidencias():
    while True:
        print("\n--- INCIDENCIAS ---")
        opciones = [
            "Crear nueva incidencia",
            "Listar incidencias",
            "Ver detalle de incidencia",
            "Cambiar estado",
            "Asignar técnico",
            "Agregar nota",
            "Eliminar incidencia",
            "Volver",
        ]
        for i, op in enumerate(opciones, 1):
            print(f"  {i}. {op}")
        sel = input_opcion("\nSeleccione: ", opciones)
        if sel == 1:
            crear_incidencia_ui()
        elif sel == 2:
            listar_incidencias_ui()
        elif sel == 3:
            ver_incidencia_ui()
        elif sel == 4:
            cambiar_estado_ui()
        elif sel == 5:
            asignar_tecnico_ui()
        elif sel == 6:
            agregar_nota_ui()
        elif sel == 7:
            eliminar_incidencia_ui()
        elif sel == 8:
            return


def crear_incidencia_ui():
    print("\n--- NUEVA INCIDENCIA ---")
    titulo = input_texto("Título (*): ", requerido=True)
    descripcion = input_texto("Descripción: ")

    print("\nPrioridad:")
    prioridad = input_seleccion("Seleccione prioridad: ", PRIORIDADES) or "media"

    print("\nCategoría:")
    categoria = input_seleccion("Seleccione categoría: ", CATEGORIAS)

    # Seleccionar cliente
    clientes = modelos.listar_clientes()
    cliente_id = None
    if clientes:
        print("\nCliente:")
        nombres = [f"{c['nombre']} ({c['empresa'] or 'Sin empresa'})" for c in clientes]
        nombres.append("Ninguno")
        sel = input_seleccion("Seleccione cliente: ", nombres)
        if sel and sel != "Ninguno":
            idx = nombres.index(sel)
            cliente_id = clientes[idx]["id"]

    # Seleccionar técnico
    tecnicos = modelos.listar_tecnicos()
    tecnico_id = None
    if tecnicos:
        print("\nTécnico asignado:")
        nombres = [f"{t['nombre']} ({t['especialidad'] or 'General'})" for t in tecnicos]
        nombres.append("Sin asignar")
        sel = input_seleccion("Seleccione técnico: ", nombres)
        if sel and sel != "Sin asignar":
            idx = nombres.index(sel)
            tecnico_id = tecnicos[idx]["id"]

    inc_id = modelos.crear_incidencia(
        titulo, descripcion, prioridad, categoria, cliente_id, tecnico_id
    )
    print(f"\n  Incidencia #{inc_id} creada exitosamente.")


def listar_incidencias_ui():
    print("\n--- LISTADO DE INCIDENCIAS ---")
    print("Filtrar por estado:")
    filtros = ["Todas"] + ESTADOS
    sel = input_seleccion("", filtros)
    estado = sel if sel != "Todas" else None

    incs = modelos.listar_incidencias(estado=estado)
    if not incs:
        print("\n  No hay incidencias registradas.")
        return

    tabla = []
    for i in incs:
        estado_str = f"{ESTADO_ICONO.get(i['estado'], '')} {i['estado']}"
        prioridad_str = f"{PRIORIDAD_ICONO.get(i['prioridad'], '')} {i['prioridad']}"
        tabla.append([
            i["id"],
            i["titulo"][:40],
            estado_str,
            prioridad_str,
            i["cliente_nombre"] or "-",
            i["tecnico_nombre"] or "Sin asignar",
            i["creado_en"][:10] if i["creado_en"] else "-",
        ])

    headers = ["ID", "Título", "Estado", "Prioridad", "Cliente", "Técnico", "Fecha"]
    print()
    print(tabulate(tabla, headers=headers, tablefmt="simple"))
    print(f"\n  Total: {len(incs)} incidencia(s)")


def ver_incidencia_ui():
    inc_id = input_texto("\nID de incidencia: ", requerido=True)
    try:
        inc_id = int(inc_id)
    except ValueError:
        print("  ID inválido")
        return

    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        print("  Incidencia no encontrada.")
        return

    print(f"\n{'=' * 50}")
    print(f"  INCIDENCIA #{inc['id']}")
    print(f"{'=' * 50}")
    print(f"  Título:     {inc['titulo']}")
    print(f"  Estado:     {ESTADO_ICONO.get(inc['estado'], '')} {inc['estado']}")
    print(f"  Prioridad:  {PRIORIDAD_ICONO.get(inc['prioridad'], '')} {inc['prioridad']}")
    print(f"  Categoría:  {inc['categoria'] or '-'}")
    print(f"  Cliente:    {inc['cliente_nombre'] or '-'}")
    print(f"  Técnico:    {inc['tecnico_nombre'] or 'Sin asignar'}")
    print(f"  Creada:     {inc['creado_en']}")
    print(f"  Actualizada:{inc['actualizado_en']}")
    if inc["cerrado_en"]:
        print(f"  Cerrada:    {inc['cerrado_en']}")
    if inc["descripcion"]:
        print(f"\n  Descripción:\n  {inc['descripcion']}")

    # Mostrar notas
    notas = modelos.listar_notas(inc_id)
    if notas:
        print(f"\n  --- Notas ({len(notas)}) ---")
        for n in notas:
            autor = n["autor"] or "Sistema"
            print(f"  [{n['creado_en']}] {autor}: {n['contenido']}")
    print()


def cambiar_estado_ui():
    inc_id = input_texto("\nID de incidencia: ", requerido=True)
    try:
        inc_id = int(inc_id)
    except ValueError:
        print("  ID inválido")
        return

    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        print("  Incidencia no encontrada.")
        return

    print(f"\n  Estado actual: {inc['estado']}")
    print("\nNuevo estado:")
    nuevo_estado = input_seleccion("Seleccione: ", ESTADOS)
    if nuevo_estado:
        modelos.actualizar_incidencia(inc_id, estado=nuevo_estado)
        print(f"  Estado actualizado a: {nuevo_estado}")


def asignar_tecnico_ui():
    inc_id = input_texto("\nID de incidencia: ", requerido=True)
    try:
        inc_id = int(inc_id)
    except ValueError:
        print("  ID inválido")
        return

    tecnicos = modelos.listar_tecnicos()
    if not tecnicos:
        print("  No hay técnicos registrados.")
        return

    print("\nTécnico:")
    nombres = [f"{t['nombre']} ({t['especialidad'] or 'General'})" for t in tecnicos]
    sel = input_seleccion("Seleccione: ", nombres)
    if sel:
        idx = nombres.index(sel)
        modelos.actualizar_incidencia(inc_id, tecnico_id=tecnicos[idx]["id"])
        print(f"  Técnico asignado: {tecnicos[idx]['nombre']}")


def agregar_nota_ui():
    inc_id = input_texto("\nID de incidencia: ", requerido=True)
    try:
        inc_id = int(inc_id)
    except ValueError:
        print("  ID inválido")
        return

    if not modelos.obtener_incidencia(inc_id):
        print("  Incidencia no encontrada.")
        return

    contenido = input_texto("Nota: ", requerido=True)
    autor = input_texto("Autor: ")
    modelos.agregar_nota(inc_id, contenido, autor)
    print("  Nota agregada.")


def eliminar_incidencia_ui():
    inc_id = input_texto("\nID de incidencia a eliminar: ", requerido=True)
    try:
        inc_id = int(inc_id)
    except ValueError:
        print("  ID inválido")
        return

    inc = modelos.obtener_incidencia(inc_id)
    if not inc:
        print("  Incidencia no encontrada.")
        return

    confirm = input_texto(f"¿Eliminar incidencia #{inc_id} '{inc['titulo']}'? (s/n): ")
    if confirm and confirm.lower() == "s":
        modelos.eliminar_incidencia(inc_id)
        print("  Incidencia eliminada.")


# ── Menú de Clientes ─────────────────────────────────────────────────────

def menu_clientes():
    while True:
        print("\n--- CLIENTES ---")
        opciones = [
            "Registrar cliente",
            "Listar clientes",
            "Editar cliente",
            "Eliminar cliente",
            "Volver",
        ]
        for i, op in enumerate(opciones, 1):
            print(f"  {i}. {op}")
        sel = input_opcion("\nSeleccione: ", opciones)
        if sel == 1:
            crear_cliente_ui()
        elif sel == 2:
            listar_clientes_ui()
        elif sel == 3:
            editar_cliente_ui()
        elif sel == 4:
            eliminar_cliente_ui()
        elif sel == 5:
            return


def crear_cliente_ui():
    print("\n--- NUEVO CLIENTE ---")
    nombre = input_texto("Nombre (*): ", requerido=True)
    email = input_texto("Email: ")
    telefono = input_texto("Teléfono: ")
    empresa = input_texto("Empresa: ")
    cid = modelos.crear_cliente(nombre, email, telefono, empresa)
    print(f"\n  Cliente #{cid} registrado exitosamente.")


def listar_clientes_ui():
    clientes = modelos.listar_clientes()
    if not clientes:
        print("\n  No hay clientes registrados.")
        return

    tabla = []
    for c in clientes:
        tabla.append([c["id"], c["nombre"], c["email"] or "-", c["telefono"] or "-", c["empresa"] or "-"])

    headers = ["ID", "Nombre", "Email", "Teléfono", "Empresa"]
    print()
    print(tabulate(tabla, headers=headers, tablefmt="simple"))


def editar_cliente_ui():
    cid = input_texto("\nID de cliente: ", requerido=True)
    try:
        cid = int(cid)
    except ValueError:
        print("  ID inválido")
        return

    cliente = modelos.obtener_cliente(cid)
    if not cliente:
        print("  Cliente no encontrado.")
        return

    print(f"  Editando: {cliente['nombre']} (Enter para mantener valor actual)")
    campos = {}
    nombre = input_texto(f"  Nombre [{cliente['nombre']}]: ")
    if nombre:
        campos["nombre"] = nombre
    email = input_texto(f"  Email [{cliente['email'] or ''}]: ")
    if email:
        campos["email"] = email
    telefono = input_texto(f"  Teléfono [{cliente['telefono'] or ''}]: ")
    if telefono:
        campos["telefono"] = telefono
    empresa = input_texto(f"  Empresa [{cliente['empresa'] or ''}]: ")
    if empresa:
        campos["empresa"] = empresa

    if campos:
        modelos.actualizar_cliente(cid, **campos)
        print("  Cliente actualizado.")
    else:
        print("  Sin cambios.")


def eliminar_cliente_ui():
    cid = input_texto("\nID de cliente a eliminar: ", requerido=True)
    try:
        cid = int(cid)
    except ValueError:
        print("  ID inválido")
        return

    cliente = modelos.obtener_cliente(cid)
    if not cliente:
        print("  Cliente no encontrado.")
        return

    confirm = input_texto(f"¿Eliminar cliente '{cliente['nombre']}'? (s/n): ")
    if confirm and confirm.lower() == "s":
        modelos.eliminar_cliente(cid)
        print("  Cliente eliminado.")


# ── Menú de Técnicos ─────────────────────────────────────────────────────

def menu_tecnicos():
    while True:
        print("\n--- TÉCNICOS ---")
        opciones = [
            "Registrar técnico",
            "Listar técnicos",
            "Editar técnico",
            "Desactivar técnico",
            "Volver",
        ]
        for i, op in enumerate(opciones, 1):
            print(f"  {i}. {op}")
        sel = input_opcion("\nSeleccione: ", opciones)
        if sel == 1:
            crear_tecnico_ui()
        elif sel == 2:
            listar_tecnicos_ui()
        elif sel == 3:
            editar_tecnico_ui()
        elif sel == 4:
            desactivar_tecnico_ui()
        elif sel == 5:
            return


def crear_tecnico_ui():
    print("\n--- NUEVO TÉCNICO ---")
    nombre = input_texto("Nombre (*): ", requerido=True)
    especialidad = input_texto("Especialidad: ")
    email = input_texto("Email: ")
    telefono = input_texto("Teléfono: ")
    tid = modelos.crear_tecnico(nombre, especialidad, email, telefono)
    print(f"\n  Técnico #{tid} registrado exitosamente.")


def listar_tecnicos_ui():
    tecnicos = modelos.listar_tecnicos(solo_activos=False)
    if not tecnicos:
        print("\n  No hay técnicos registrados.")
        return

    tabla = []
    for t in tecnicos:
        estado = "Activo" if t["activo"] else "Inactivo"
        tabla.append([
            t["id"], t["nombre"], t["especialidad"] or "-",
            t["email"] or "-", t["telefono"] or "-", estado,
        ])

    headers = ["ID", "Nombre", "Especialidad", "Email", "Teléfono", "Estado"]
    print()
    print(tabulate(tabla, headers=headers, tablefmt="simple"))


def editar_tecnico_ui():
    tid = input_texto("\nID de técnico: ", requerido=True)
    try:
        tid = int(tid)
    except ValueError:
        print("  ID inválido")
        return

    tecnico = modelos.obtener_tecnico(tid)
    if not tecnico:
        print("  Técnico no encontrado.")
        return

    print(f"  Editando: {tecnico['nombre']} (Enter para mantener valor actual)")
    campos = {}
    nombre = input_texto(f"  Nombre [{tecnico['nombre']}]: ")
    if nombre:
        campos["nombre"] = nombre
    especialidad = input_texto(f"  Especialidad [{tecnico['especialidad'] or ''}]: ")
    if especialidad:
        campos["especialidad"] = especialidad
    email = input_texto(f"  Email [{tecnico['email'] or ''}]: ")
    if email:
        campos["email"] = email
    telefono = input_texto(f"  Teléfono [{tecnico['telefono'] or ''}]: ")
    if telefono:
        campos["telefono"] = telefono

    if campos:
        modelos.actualizar_tecnico(tid, **campos)
        print("  Técnico actualizado.")
    else:
        print("  Sin cambios.")


def desactivar_tecnico_ui():
    tid = input_texto("\nID de técnico a desactivar: ", requerido=True)
    try:
        tid = int(tid)
    except ValueError:
        print("  ID inválido")
        return

    tecnico = modelos.obtener_tecnico(tid)
    if not tecnico:
        print("  Técnico no encontrado.")
        return

    confirm = input_texto(f"¿Desactivar técnico '{tecnico['nombre']}'? (s/n): ")
    if confirm and confirm.lower() == "s":
        modelos.desactivar_tecnico(tid)
        print("  Técnico desactivado.")


# ── Menú de Reportes ─────────────────────────────────────────────────────

def menu_reportes():
    while True:
        print("\n--- REPORTES Y ESTADÍSTICAS ---")
        opciones = [
            "Resumen general",
            "Incidencias por técnico",
            "Incidencias por cliente",
            "Incidencias por categoría",
            "Volver",
        ]
        for i, op in enumerate(opciones, 1):
            print(f"  {i}. {op}")
        sel = input_opcion("\nSeleccione: ", opciones)
        if sel == 1:
            reporte_resumen()
        elif sel == 2:
            reporte_por_tecnico()
        elif sel == 3:
            reporte_por_cliente()
        elif sel == 4:
            reporte_por_categoria()
        elif sel == 5:
            return


def reporte_resumen():
    stats = reportes.resumen_general()
    print(f"\n{'=' * 45}")
    print("  RESUMEN GENERAL")
    print(f"{'=' * 45}")
    print(f"  Total incidencias:  {stats['total_incidencias']}")
    print(f"  Abiertas (activas): {stats['abiertas']}")
    print(f"  Total clientes:     {stats['total_clientes']}")
    print(f"  Técnicos activos:   {stats['total_tecnicos']}")

    if stats["por_estado"]:
        print("\n  Por estado:")
        for estado, total in stats["por_estado"].items():
            print(f"    {ESTADO_ICONO.get(estado, '')} {estado}: {total}")

    if stats["por_prioridad"]:
        print("\n  Por prioridad:")
        for prioridad, total in stats["por_prioridad"].items():
            print(f"    {PRIORIDAD_ICONO.get(prioridad, '')} {prioridad}: {total}")
    print()


def reporte_por_tecnico():
    datos = reportes.incidencias_por_tecnico()
    if not datos:
        print("\n  No hay datos de técnicos.")
        return

    tabla = [[d["nombre"], d["especialidad"] or "-", d["total"], d["abiertas"]] for d in datos]
    headers = ["Técnico", "Especialidad", "Total", "Abiertas"]
    print("\n  INCIDENCIAS POR TÉCNICO")
    print(tabulate(tabla, headers=headers, tablefmt="simple"))
    print()


def reporte_por_cliente():
    datos = reportes.incidencias_por_cliente()
    if not datos:
        print("\n  No hay datos de clientes.")
        return

    tabla = [[d["nombre"], d["empresa"] or "-", d["total"], d["abiertas"]] for d in datos]
    headers = ["Cliente", "Empresa", "Total", "Abiertas"]
    print("\n  INCIDENCIAS POR CLIENTE")
    print(tabulate(tabla, headers=headers, tablefmt="simple"))
    print()


def reporte_por_categoria():
    datos = reportes.incidencias_por_categoria()
    if not datos:
        print("\n  No hay datos.")
        return

    tabla = [[d["categoria"], d["total"], d["abiertas"]] for d in datos]
    headers = ["Categoría", "Total", "Abiertas"]
    print("\n  INCIDENCIAS POR CATEGORÍA")
    print(tabulate(tabla, headers=headers, tablefmt="simple"))
    print()
