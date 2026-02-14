"""Modulo de integracion con IA (Claude API) para asistencia en incidencias."""

import os
import hashlib
import time
import logging
import anthropic

logger = logging.getLogger(__name__)

CATEGORIAS_VALIDAS = ["hardware", "software", "red", "email", "seguridad", "otro"]
PRIORIDADES_VALIDAS = ["baja", "media", "alta", "critica"]

# ── Excepciones IA ──────────────────────────────────────────────────────


class IAError(Exception):
    """Error base del modulo IA."""
    pass


class IAConfigError(IAError):
    """API key faltante o invalida."""
    pass


class IALimitError(IAError):
    """Limite de uso alcanzado."""
    pass


# ── Cache simple en memoria ─────────────────────────────────────────────

_cache = {}
CACHE_TTL = 300  # 5 minutos


def _cache_key(*args):
    return hashlib.md5(str(args).encode()).hexdigest()


# ── Cliente y llamada base ──────────────────────────────────────────────

def _get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise IAConfigError(
            "ANTHROPIC_API_KEY no esta configurada. Agrega tu clave en el archivo .env"
        )
    return anthropic.Anthropic(api_key=api_key)


def _ask(system_prompt, user_prompt):
    """Envia un mensaje a Claude y retorna la respuesta como texto."""
    try:
        client = _get_client()
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
    except IAConfigError:
        raise
    except anthropic.RateLimitError:
        raise IALimitError(
            "Limite de uso de la API alcanzado. Intenta de nuevo en unos minutos."
        )
    except anthropic.AuthenticationError:
        raise IAConfigError("La clave de API no es valida. Revisa tu archivo .env")
    except anthropic.APIConnectionError:
        raise IAError(
            "No se pudo conectar con la API de Claude. Verifica tu conexion a internet."
        )
    except Exception as e:
        logger.exception("Error inesperado en la API de IA")
        raise IAError(f"Error inesperado: {str(e)}")


def _ask_cached(system_prompt, user_prompt):
    """Igual que _ask pero con cache por TTL."""
    key = _cache_key(system_prompt, user_prompt)
    now = time.time()
    if key in _cache:
        result, ts = _cache[key]
        if now - ts < CACHE_TTL:
            return result
    result = _ask(system_prompt, user_prompt)
    _cache[key] = (result, now)
    return result


# ── Funciones de IA ─────────────────────────────────────────────────────

def redactar_respuesta(incidencia, notas, contexto_usuario=None):
    """Genera una respuesta profesional para enviar al cliente.

    Args:
        incidencia: dict con datos de la incidencia
        notas: lista de notas de la incidencia
        contexto_usuario: texto opcional con lo que el usuario quiere transmitir
    """
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
    )

    if contexto_usuario:
        user += (
            f"\nINSTRUCCIONES DEL AGENTE DE SOPORTE:\n"
            f"El agente quiere transmitir lo siguiente al cliente: {contexto_usuario}\n"
            f"Incorpora esta informacion en la respuesta de forma profesional y natural."
        )
    else:
        user += (
            "\nRedacta una respuesta profesional para actualizar al cliente "
            "sobre el estado de su incidencia."
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
    return _ask_cached(system, user)


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
    return _ask_cached(system, user)


def chat_incidencia(incidencia, notas, historial_chat, mensaje_usuario):
    """Chat interactivo sobre una incidencia especifica."""
    historial_notas = ""
    for n in notas:
        historial_notas += (
            f"- [{n['creado_en']}] {n['autor'] or 'Sistema'}: {n['contenido']}\n"
        )

    system = (
        "Eres un asistente experto en soporte tecnico IT. "
        "Ayudas al agente de soporte a resolver incidencias, responder consultas "
        "y tomar decisiones sobre como proceder. "
        "Tienes acceso al contexto completo de la incidencia. "
        "Responde en espanol. Se conciso y practico."
    )

    contexto = (
        f"[CONTEXTO DE LA INCIDENCIA]\n"
        f"Incidencia #{incidencia['id']}: {incidencia['titulo']}\n"
        f"Descripcion: {incidencia.get('descripcion') or 'Sin descripcion'}\n"
        f"Estado: {incidencia['estado']} | Prioridad: {incidencia['prioridad']}\n"
        f"Categoria: {incidencia.get('categoria') or 'Sin categoria'}\n"
        f"Cliente: {incidencia.get('cliente_nombre') or 'No asignado'}\n"
        f"Tecnico: {incidencia.get('tecnico_nombre') or 'No asignado'}\n"
        f"\nNotas:\n{historial_notas or 'Sin notas'}"
    )

    messages = [
        {"role": "user", "content": contexto},
        {
            "role": "assistant",
            "content": "Entendido. Tengo el contexto de la incidencia. ¿En que puedo ayudarte?",
        },
    ]

    for msg in historial_chat:
        messages.append({"role": msg["role"], "content": msg["contenido"]})

    messages.append({"role": "user", "content": mensaje_usuario})

    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        return response.content[0].text
    except IAConfigError:
        raise
    except anthropic.RateLimitError:
        raise IALimitError("Limite de uso alcanzado. Intenta de nuevo en unos minutos.")
    except anthropic.AuthenticationError:
        raise IAConfigError("La clave de API no es valida.")
    except anthropic.APIConnectionError:
        raise IAError("No se pudo conectar con la API de Claude.")
    except Exception as e:
        logger.exception("Error inesperado en chat IA")
        raise IAError(f"Error inesperado: {str(e)}")
