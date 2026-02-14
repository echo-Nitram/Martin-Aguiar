"""Modulo de integracion con IA (Claude API) para asistencia en incidencias."""

import os
import anthropic

CATEGORIAS_VALIDAS = ["hardware", "software", "red", "email", "seguridad", "otro"]
PRIORIDADES_VALIDAS = ["baja", "media", "alta", "critica"]


def _get_client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def _ask(system_prompt, user_prompt):
    """Envia un mensaje a Claude y retorna la respuesta como texto."""
    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


def redactar_respuesta(incidencia, notas):
    """Genera una respuesta profesional para enviar al cliente."""
    historial = ""
    for n in notas:
        historial += f"- {n['autor'] or 'Sistema'}: {n['contenido']}\n"

    system = (
        "Eres un agente de soporte tecnico profesional y amable. "
        "Redacta una respuesta clara y concisa para enviar al cliente. "
        "Usa un tono profesional pero cercano. Responde en espanol. "
        "NO uses markdown ni formato especial, solo texto plano."
    )
    user = (
        f"Incidencia: {incidencia['titulo']}\n"
        f"Descripcion: {incidencia.get('descripcion') or 'Sin descripcion'}\n"
        f"Estado actual: {incidencia['estado']}\n"
        f"Prioridad: {incidencia['prioridad']}\n"
        f"Categoria: {incidencia.get('categoria') or 'Sin categoria'}\n"
        f"\nHistorial de notas:\n{historial or 'Sin notas previas'}\n"
        f"\nRedacta una respuesta profesional para actualizar al cliente sobre el estado de su incidencia."
    )
    return _ask(system, user)


def auto_clasificar(titulo, descripcion):
    """Sugiere categoria y prioridad basandose en el titulo y descripcion."""
    system = (
        "Eres un sistema de clasificacion de incidencias de soporte tecnico. "
        f"Categorias validas: {', '.join(CATEGORIAS_VALIDAS)}. "
        f"Prioridades validas: {', '.join(PRIORIDADES_VALIDAS)}. "
        "Responde SOLO con este formato exacto sin nada mas:\n"
        "CATEGORIA: <categoria>\n"
        "PRIORIDAD: <prioridad>\n"
        "RAZON: <explicacion breve en una linea>"
    )
    user = f"Titulo: {titulo}\nDescripcion: {descripcion or 'Sin descripcion'}"
    respuesta = _ask(system, user)

    resultado = {"categoria": None, "prioridad": None, "razon": ""}
    for linea in respuesta.strip().split("\n"):
        linea = linea.strip()
        if linea.upper().startswith("CATEGORIA:"):
            val = linea.split(":", 1)[1].strip().lower()
            if val in CATEGORIAS_VALIDAS:
                resultado["categoria"] = val
        elif linea.upper().startswith("PRIORIDAD:"):
            val = linea.split(":", 1)[1].strip().lower()
            if val in PRIORIDADES_VALIDAS:
                resultado["prioridad"] = val
        elif linea.upper().startswith("RAZON:"):
            resultado["razon"] = linea.split(":", 1)[1].strip()
    return resultado


def diagnosticar(incidencia, notas):
    """Sugiere posibles causas y pasos de solucion para una incidencia."""
    historial = ""
    for n in notas:
        historial += f"- {n['autor'] or 'Sistema'}: {n['contenido']}\n"

    system = (
        "Eres un experto en soporte tecnico IT. "
        "Analiza la incidencia y sugiere posibles causas y pasos de solucion concretos. "
        "Se practico y directo. Responde en espanol. "
        "Estructura tu respuesta como:\n"
        "POSIBLES CAUSAS:\n- causa 1\n- causa 2\n\n"
        "PASOS SUGERIDOS:\n1. paso 1\n2. paso 2\n\n"
        "NOTA: alguna observacion adicional si es relevante"
    )
    user = (
        f"Incidencia: {incidencia['titulo']}\n"
        f"Descripcion: {incidencia.get('descripcion') or 'Sin descripcion'}\n"
        f"Categoria: {incidencia.get('categoria') or 'Sin categoria'}\n"
        f"Prioridad: {incidencia['prioridad']}\n"
        f"\nHistorial de notas:\n{historial or 'Sin notas previas'}"
    )
    return _ask(system, user)


def resumir_incidencia(incidencia, notas):
    """Genera un resumen ejecutivo de la incidencia y su historial."""
    historial = ""
    for n in notas:
        historial += f"- [{n['creado_en']}] {n['autor'] or 'Sistema'}: {n['contenido']}\n"

    system = (
        "Eres un asistente que genera resumenes ejecutivos de incidencias de soporte. "
        "Genera un resumen breve (3-5 lineas) que capture el problema, "
        "las acciones tomadas y el estado actual. Responde en espanol. Texto plano."
    )
    user = (
        f"Incidencia #{incidencia['id']}: {incidencia['titulo']}\n"
        f"Descripcion: {incidencia.get('descripcion') or 'Sin descripcion'}\n"
        f"Estado: {incidencia['estado']} | Prioridad: {incidencia['prioridad']}\n"
        f"Categoria: {incidencia.get('categoria') or 'Sin categoria'}\n"
        f"Cliente: {incidencia.get('cliente_nombre') or 'No asignado'}\n"
        f"Tecnico: {incidencia.get('tecnico_nombre') or 'No asignado'}\n"
        f"Creada: {incidencia['creado_en']}\n"
        f"\nHistorial completo:\n{historial or 'Sin notas'}\n"
        f"\nGenera un resumen ejecutivo."
    )
    return _ask(system, user)
