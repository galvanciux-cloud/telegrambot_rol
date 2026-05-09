"""
ai_engine.py — Motor de IA de Billy usando Ollama (DeepSeek-R1:8B local)
Gestiona la comunicación con el modelo de lenguaje y el formateo de prompts.
"""

import logging
import json
from typing import Optional
from pathlib import Path

from config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_AVAILABLE_MODELS,
    MAX_TOKENS,
    TEMPERATURE,
    PERSONALIDAD_FILE,
    PROMPTS_DIR,
)

logger = logging.getLogger(__name__)


class AIEngine:
    """Motor de IA que se comunica con Ollama local."""

    def __init__(self):
        import httpx
        self.client = httpx.Client(timeout=300.0)
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL
        self.available_models = OLLAMA_AVAILABLE_MODELS
        self.max_tokens = MAX_TOKENS
        self.temperature = TEMPERATURE
        self.current_role = "general"
        self._personalidad = self._load_file(PERSONALIDAD_FILE)
        self._intelligent_prompts = self._load_file(PROMPTS_DIR / "intelligent_prompts.md")
        self._check_connection()
        logger.info(f"AIEngine inicializado con modelo: {self.model}")

    def _check_connection(self):
        """Verifica conexión con Ollama."""
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                logger.info(f"Modelos disponibles en Ollama: {model_names}")
                if self.model not in model_names:
                    logger.warning(
                        f"Modelo {self.model} no encontrado. "
                        f"Disponibles: {model_names}"
                    )
            else:
                logger.warning(f"Ollama responded with status: {response.status_code}")
        except Exception as e:
            logger.error(f"Error conectando con Ollama: {e}")

    def _load_file(self, path: Path) -> str:
        """Carga contenido de un archivo .md"""
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error cargando {path}: {e}")
        return ""

    def set_role(self, role: str):
        """Cambia el rol/personalidad activa."""
        role_file = PROMPTS_DIR / f"{role}.md"
        if role == "general":
            self.current_role = "general"
            logger.info("Rol cambiado a: General (personalidad base)")
        elif role_file.exists():
            self.current_role = role
            logger.info(f"Rol cambiado a: {role}")
        else:
            logger.warning(f"Archivo de rol no encontrado: {role_file}")

    def get_role_prompt(self, role: str) -> str:
        """Obtiene las instrucciones específicas de un rol."""
        if role == "general":
            return ""
        role_file = PROMPTS_DIR / f"{role}.md"
        return self._load_file(role_file)

    def generate_response(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
        rag_context: str = "",
        memory_context: str = "",
        tool_results: str = "",
    ) -> str:
        """Genera una respuesta del modelo de IA con Ollama."""
        messages = self._build_messages(
            user_message,
            conversation_history,
            rag_context,
            memory_context,
            tool_results,
        )

        try:
            response = self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    },
                },
            )

            if response.status_code == 200:
                content = response.json().get("message", {}).get("content", "")
                return content.strip() if content else "Lo siento, no pude generar una respuesta."
            else:
                return self._handle_error(response.status_code, response.text)

        except Exception as e:
            logger.error(f"Error comunicando con Ollama: {e}")
            return f"❌ Error al comunicarse con Ollama: {e}"

    def _build_messages(
        self,
        user_message: str,
        conversation_history: list[dict] | None,
        rag_context: str,
        memory_context: str,
        tool_results: str,
    ) -> list[dict]:
        """Construye la lista de mensajes para Ollama."""
        role_prompt = self.get_role_prompt(self.current_role)

        system_content = self._personalidad

        if role_prompt:
            system_content += f"\n\n## Rol Actual\n\n{role_prompt}"

        if rag_context:
            system_content += f"\n\n## Contexto de conocimientos relevantes:\n{rag_context}"

        if memory_context:
            system_content += f"\n\n## Información recordada del usuario:\n{memory_context}"

        if tool_results:
            system_content += f"\n\n## Resultados de herramientas:\n{tool_results}"

        messages = [{"role": "system", "content": system_content}]

        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

        messages.append({"role": "user", "content": user_message})

        return messages

    def _handle_error(self, status_code: int, text: str) -> str:
        """Maneja errores de la API de Ollama."""
        if status_code == 404:
            return (
                f"❌ Modelo no encontrado: {self.model}\n\n"
                f"Instálalo con: ollama pull {self.model}"
            )
        elif status_code == 500:
            return (
                "❌ Error interno del servidor Ollama. "
                "El modelo puede estar cargándose. Espera unos segundos."
            )
        elif "connection" in text.lower():
            return (
                "❌ No se puede conectar con Ollama.\n\n"
                "Verifica que:\n"
                "1. Ollama está instalado y ejecutándose\n"
                "2. El modelo está descargado (`ollama pull deepseek-r1:8b`)\n"
                "3. La URL es correcta en config.py"
            )
        else:
            return f"❌ Error de Ollama ({status_code}): {text}"

    def quick_chat(self, message: str) -> str:
        """Chat rápido sin contexto adicional."""
        messages = [
            {"role": "system", "content": self._personalidad},
            {"role": "user", "content": message},
        ]
        try:
            response = self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    },
                },
            )
            if response.status_code == 200:
                content = response.json().get("message", {}).get("content", "")
                return content.strip() if content else "Sin respuesta."
            return f"Error: {response.status_code}"
        except Exception as e:
            return f"Error: {e}"

    def get_active_model(self) -> str:
        """Devuelve el modelo que está funcionando actualmente."""
        return self.model

    def get_current_role(self) -> str:
        """Devuelve el rol actual."""
        return self.current_role

    def get_available_models(self) -> list[str]:
        """Devuelve la lista de modelos disponibles."""
        return self.available_models.copy()
