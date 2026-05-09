"""
tools.py — Funciones útiles adicionales de NOVA
Calculadora, clima, Wikipedia, traducción y más.
"""

import logging
import math
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


# ─── Calculadora ────────────────────────────────────────────────────

def calculate(expression: str) -> dict:
    """
    Evalúa una expresión matemática de forma segura.

    Args:
        expression: Expresión matemática (ej: "2 + 3 * 4", "sqrt(16)", "sin(pi/2)")

    Returns:
        Diccionario con result o error
    """
    # Limpiar la expresión
    expression = expression.strip()
    expression = expression.replace("×", "*").replace("÷", "/").replace("^", "**")
    expression = expression.replace("π", "pi").replace("√", "sqrt")

    # Funciones matemáticas permitidas
    safe_dict = {
        # Funciones básicas
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        # Funciones del módulo math
        "sqrt": math.sqrt,
        "pow": pow,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,
        # Trigonometría
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,
        # Constantes
        "pi": math.pi,
        "e": math.e,
        "inf": math.inf,
        # Conversión
        "radians": math.radians,
        "degrees": math.degrees,
        # Factorial
        "factorial": math.factorial,
        "gcd": math.gcd,
        "ceil": math.ceil,
        "floor": math.floor,
    }

    # Verificar que la expresión solo contenga caracteres seguros
    allowed_chars = re.compile(r'^[0-9+\-*/().,%\s_a-zA-Z]+$')
    if not allowed_chars.match(expression):
        return {"error": "Expresión contiene caracteres no permitidos."}

    # Verificar que no haya intentos de ejecutar código
    dangerous = ["__", "import", "exec", "eval", "open", "file", "os.", "sys."]
    for word in dangerous:
        if word in expression.lower():
            return {"error": "Expresión contiene términos no permitidos."}

    try:
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return {
            "expression": expression,
            "result": result,
            "formatted": f"{expression} = {result}",
        }
    except ZeroDivisionError:
        return {"error": "Error: División por cero."}
    except ValueError as e:
        return {"error": f"Error matemático: {e}"}
    except SyntaxError:
        return {"error": "Error de sintaxis en la expresión matemática."}
    except Exception as e:
        return {"error": f"Error al calcular: {e}"}


# ─── Clima ──────────────────────────────────────────────────────────

def get_weather(city: str) -> dict:
    """
    Obtiene el clima actual de una ciudad usando Open-Meteo (gratuito, sin API key).

    Args:
        city: Nombre de la ciudad

    Returns:
        Diccionario con información del clima
    """
    try:
        # Paso 1: Geocodificar la ciudad
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {"name": city, "count": 1, "language": "es", "format": "json"}

        with httpx.Client(timeout=10.0) as client:
            geo_response = client.get(geo_url, params=geo_params)
            geo_data = geo_response.json()

        if not geo_data.get("results"):
            return {"error": f"No se encontró la ciudad: {city}"}

        location = geo_data["results"][0]
        latitude = location["latitude"]
        longitude = location["longitude"]
        location_name = location.get("name", city)
        country = location.get("country", "")

        # Paso 2: Obtener el clima
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
            ],
            "timezone": "auto",
        }

        with httpx.Client(timeout=10.0) as client:
            weather_response = client.get(weather_url, params=weather_params)
            weather_data = weather_response.json()

        current = weather_data.get("current", {})

        # Mapear código de clima a descripción
        weather_code = current.get("weather_code", 0)
        weather_desc = _weather_code_to_description(weather_code)

        return {
            "city": location_name,
            "country": country,
            "temperature": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "weather": weather_desc,
            "wind_speed": current.get("wind_speed_10m"),
            "wind_direction": _degrees_to_direction(current.get("wind_direction_10m", 0)),
            "success": True,
        }

    except httpx.TimeoutException:
        return {"error": "Tiempo de espera agotado al consultar el clima."}
    except Exception as e:
        logger.error(f"Error obteniendo clima: {e}")
        return {"error": f"Error al obtener el clima: {e}"}


def _weather_code_to_description(code: int) -> str:
    """Convierte el código de clima de Open-Meteo a descripción en español."""
    descriptions = {
        0: "Despejado",
        1: "Principalmente despejado",
        2: "Parcialmente nublado",
        3: "Nublado",
        45: "Niebla",
        48: "Niebla con escarcha",
        51: "Llovizna ligera",
        53: "Llovizna moderada",
        55: "Llovizna intensa",
        61: "Lluvia ligera",
        63: "Lluvia moderada",
        65: "Lluvia intensa",
        71: "Nevada ligera",
        73: "Nevada moderada",
        75: "Nevada intensa",
        77: "Granos de nieve",
        80: "Chubascos ligeros",
        81: "Chubascos moderados",
        82: "Chubascos fuertes",
        85: "Chubascos de nieve ligeros",
        86: "Chubascos de nieve fuertes",
        95: "Tormenta",
        96: "Tormenta con granizo ligero",
        99: "Tormenta con granizo fuerte",
    }
    return descriptions.get(code, f"Código {code}")


def _degrees_to_direction(degrees: int | float) -> str:
    """Convierte grados a dirección cardinal."""
    directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO",
    ]
    if isinstance(degrees, (int, float)):
        index = round(degrees / 22.5) % 16
        return directions[index]
    return "N"


def format_weather(weather_data: dict) -> str:
    """Formatea los datos del clima como texto legible."""
    if not weather_data.get("success"):
        return f"❌ {weather_data.get('error', 'Error al obtener el clima')}"

    city = weather_data["city"]
    country = weather_data.get("country", "")
    temp = weather_data.get("temperature", "N/A")
    feels = weather_data.get("feels_like", "N/A")
    humidity = weather_data.get("humidity", "N/A")
    desc = weather_data.get("weather", "N/A")
    wind = weather_data.get("wind_speed", "N/A")
    wind_dir = weather_data.get("wind_direction", "N/A")

    return (
        f"🌤️ **Clima en {city}, {country}**\n\n"
        f"• Condición: {desc}\n"
        f"• Temperatura: {temp}°C\n"
        f"• Sensación térmica: {feels}°C\n"
        f"• Humedad: {humidity}%\n"
        f"• Viento: {wind} km/h ({wind_dir})"
    )


# ─── Wikipedia ──────────────────────────────────────────────────────

def search_wikipedia(query: str, language: str = "es") -> dict:
    """
    Busca en Wikipedia y devuelve un resumen del artículo.

    Args:
        query: Término de búsqueda
        language: Código de idioma (es, en, fr, etc.)

    Returns:
        Diccionario con title, summary, url
    """
    try:
        # Buscar artículos
        search_url = f"https://{language}.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 1,
        }

        with httpx.Client(timeout=10.0) as client:
            search_response = client.get(search_url, params=search_params)
            search_data = search_response.json()

        results = search_data.get("query", {}).get("search", [])
        if not results:
            return {"error": f"No se encontraron resultados en Wikipedia para: {query}"}

        page_title = results[0]["title"]

        # Obtener resumen del artículo
        summary_url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{page_title}"

        with httpx.Client(timeout=10.0) as client:
            summary_response = client.get(summary_url)
            summary_data = summary_response.json()

        return {
            "title": summary_data.get("title", page_title),
            "summary": summary_data.get("extract", "No hay resumen disponible."),
            "url": summary_data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "thumbnail": summary_data.get("thumbnail", {}).get("source", ""),
            "success": True,
        }

    except Exception as e:
        logger.error(f"Error buscando en Wikipedia: {e}")
        return {"error": f"Error al buscar en Wikipedia: {e}"}


def format_wikipedia(wiki_data: dict) -> str:
    """Formatea los resultados de Wikipedia como texto legible."""
    if not wiki_data.get("success"):
        return f"❌ {wiki_data.get('error', 'Error al buscar en Wikipedia')}"

    title = wiki_data["title"]
    summary = wiki_data["summary"]
    url = wiki_data["url"]

    return f"📖 **{title}**\n\n{summary}\n\n🔗 [Ver en Wikipedia]({url})"


# ─── Traducción ─────────────────────────────────────────────────────

def translate_text(text: str, target_lang: str = "en", source_lang: str = "auto") -> dict:
    """
    Traduce texto usando MyMemory API (gratuito, sin API key).

    Args:
        text: Texto a traducir
        target_lang: Idioma destino (en, es, fr, de, it, pt, etc.)
        source_lang: Idioma origen (auto para detección automática)

    Returns:
        Diccionario con translated_text
    """
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": text,
            "langpair": f"{source_lang}|{target_lang}",
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            data = response.json()

        translated = data.get("responseData", {}).get("translatedText", "")

        if not translated or translated == text:
            return {"error": "No se pudo traducir el texto. Verifica los idiomas."}

        return {
            "original": text,
            "translated": translated,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "success": True,
        }

    except Exception as e:
        logger.error(f"Error traduciendo: {e}")
        return {"error": f"Error al traducir: {e}"}


def format_translation(translation_data: dict) -> str:
    """Formatea los resultados de traducción."""
    if not translation_data.get("success"):
        return f"❌ {translation_data.get('error', 'Error al traducir')}"

    original = translation_data["original"]
    translated = translation_data["translated"]
    src = translation_data["source_lang"]
    tgt = translation_data["target_lang"]

    return f"🌐 **Traducción** ({src} → {tgt})\n\n**Original:** {original}\n**Traducción:** {translated}"


# ─── Detectar si el usuario necesita usar una herramienta ──────────

def detect_tool_intent(message: str) -> dict | None:
    """
    Analiza el mensaje del usuario para detectar si necesita
    usar alguna herramienta específica.

    Returns:
        Diccionario con tool_name y parámetros, o None
    """
    message_lower = message.lower().strip()

    # Clima
    weather_patterns = [
        r"(?:clima|tiempo|temperatura|weather)\s+(?:en|de|para|in)\s+(\w+)",
        r"(?:qué|que)\s+(?:clima|tiempo|hace)\s+(?:en|de)\s+(\w+)",
        r"how\s+(?:is|'s)\s+the\s+weather\s+in\s+(\w+)",
    ]
    for pattern in weather_patterns:
        match = re.search(pattern, message_lower)
        if match:
            return {"tool": "weather", "params": {"city": match.group(1).title()}}

    # Cálculo
    calc_patterns = [
        r"(?:calcula|calcula|cuánto\s+es|cuanto\s+es|compute|calc)\s+(.+)",
        r"(?:resuelve|solve)\s+(.+)",
    ]
    for pattern in calc_patterns:
        match = re.search(pattern, message_lower)
        if match:
            return {"tool": "calculator", "params": {"expression": match.group(1)}}

    # Wikipedia
    wiki_patterns = [
        r"(?:qué|que)\s+(?:es|son)\s+(.+?)(?:\?|$)",
        r"(?:quién|quien)\s+(?:es|fue)\s+(.+?)(?:\?|$)",
        r"(?:tell\s+me\s+about|what\s+is|who\s+is)\s+(.+?)(?:\?|$)",
    ]
    for pattern in wiki_patterns:
        match = re.search(pattern, message_lower)
        if match and len(match.group(1)) > 2:
            return {"tool": "wikipedia", "params": {"query": match.group(1).strip()}}

    # Traducción
    translate_patterns = [
        r"(?:traduce|translate)\s+(.+?)\s+(?:al|a|to)\s+(\w+)",
        r"(?:traducir|trad)\s+(.+?)\s+(?:al|a|to)\s+(\w+)",
    ]
    for pattern in translate_patterns:
        match = re.search(pattern, message_lower)
        if match:
            return {
                "tool": "translate",
                "params": {"text": match.group(1), "target_lang": match.group(2)},
            }

    return None
