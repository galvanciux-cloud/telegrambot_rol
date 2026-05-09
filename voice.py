"""
voice.py — Módulo de voz de NOVA
Implementa Text-to-Speech (TTS) y Speech-to-Text (ASR).

TTS: Usa edge-tts (Microsoft Edge TTS) — gratuito, alta calidad, múltiples voces e idiomas.
ASR: Usa HuggingFace Inference API con Whisper (openai/whisper-large-v3) — gratuito con token HF.
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import httpx
from huggingface_hub import InferenceClient

from config import DATA_DIR, HF_API_TOKEN

logger = logging.getLogger(__name__)

# ─── Voces disponibles por idioma ──────────────────────────────────

VOICE_MAP = {
    # Español
    "es": {
        "female": "es-ES-ElviraNeural",
        "male": "es-ES-AlvaroNeural",
        "default": "es-ES-ElviraNeural",
    },
    "es-MX": {
        "female": "es-MX-DaliaNeural",
        "male": "es-MX-JorgeNeural",
        "default": "es-MX-DaliaNeural",
    },
    "es-AR": {
        "female": "es-AR-ElenaNeural",
        "male": "es-AR-TomasNeural",
        "default": "es-AR-ElenaNeural",
    },
    # Inglés
    "en": {
        "female": "en-US-JennyNeural",
        "male": "en-US-GuyNeural",
        "default": "en-US-JennyNeural",
    },
    "en-GB": {
        "female": "en-GB-SoniaNeural",
        "male": "en-GB-RyanNeural",
        "default": "en-GB-SoniaNeural",
    },
    # Francés
    "fr": {
        "female": "fr-FR-DeniseNeural",
        "male": "fr-FR-HenriNeural",
        "default": "fr-FR-DeniseNeural",
    },
    # Alemán
    "de": {
        "female": "de-DE-KatjaNeural",
        "male": "de-DE-ConradNeural",
        "default": "de-DE-KatjaNeural",
    },
    # Italiano
    "it": {
        "female": "it-IT-ElsaNeural",
        "male": "it-IT-DiegoNeural",
        "default": "it-IT-ElsaNeural",
    },
    # Portugués
    "pt": {
        "female": "pt-BR-FranciscaNeural",
        "male": "pt-BR-AntonioNeural",
        "default": "pt-BR-FranciscaNeural",
    },
    # Japonés
    "ja": {
        "female": "ja-JP-NanamiNeural",
        "male": "ja-JP-KeitaNeural",
        "default": "ja-JP-NanamiNeural",
    },
    # Coreano
    "ko": {
        "female": "ko-KR-SunHiNeural",
        "male": "ko-KR-InJoonNeural",
        "default": "ko-KR-SunHiNeural",
    },
    # Chino
    "zh": {
        "female": "zh-CN-XiaoxiaoNeural",
        "male": "zh-CN-YunxiNeural",
        "default": "zh-CN-XiaoxiaoNeural",
    },
    # Ruso
    "ru": {
        "female": "ru-RU-SvetlanaNeural",
        "male": "ru-RU-DmitryNeural",
        "default": "ru-RU-SvetlanaNeural",
    },
}


class VoiceEngine:
    """Motor de voz de NOVA: TTS (Text-to-Speech) y ASR (Speech-to-Text)."""

    def __init__(self):
        self._tts_available = False
        self._asr_client = None
        self._check_tts()
        self._check_asr()

    def _check_tts(self):
        """Verifica si edge-tts está disponible."""
        try:
            import edge_tts
            self._tts_available = True
            logger.info("TTS: edge-tts disponible")
        except ImportError:
            logger.warning("TTS: edge-tts no instalado. Ejecuta: pip install edge-tts")
            self._tts_available = False

    def _check_asr(self):
        """Verifica si el ASR (Whisper) está disponible."""
        if HF_API_TOKEN and HF_API_TOKEN != "tu_token_de_huggingface_aqui":
            try:
                self._asr_client = InferenceClient(api_key=HF_API_TOKEN)
                logger.info("ASR: HuggingFace Whisper disponible")
            except Exception as e:
                logger.warning(f"ASR: Error inicializando cliente HF: {e}")
        else:
            logger.warning("ASR: HF_API_TOKEN no configurado. Transcripción de voz no disponible.")

    # ─── Text-to-Speech (TTS) ──────────────────────────────────────

    async def text_to_speech(
        self,
        text: str,
        language: str = "es",
        voice_gender: str = "female",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        output_path: str | None = None,
    ) -> str | None:
        """
        Convierte texto a voz usando edge-tts.

        Args:
            text: Texto a convertir en voz
            language: Código de idioma (es, en, fr, de, it, pt, etc.)
            voice_gender: Género de la voz ("female" o "male")
            rate: Velocidad de lectura (ej: "+20%", "-10%")
            pitch: Tono de voz (ej: "+5Hz", "-3Hz")
            output_path: Ruta de salida. Si es None, se genera automáticamente.

        Returns:
            Ruta al archivo de audio generado, o None si falla
        """
        if not self._tts_available:
            logger.error("TTS no disponible. Instala edge-tts: pip install edge-tts")
            return None

        if not text.strip():
            return None

        # Limitar longitud del texto (máximo ~3000 caracteres para evitar audios excesivamente largos)
        text = text[:3000]

        # Obtener voz según idioma y género
        voice = self._get_voice(language, voice_gender)

        # Generar ruta de salida si no se proporciona
        if not output_path:
            temp_dir = DATA_DIR / "voice_temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(temp_dir / f"tts_{os.getpid()}_{id(text)}.mp3")

        try:
            import edge_tts

            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch,
            )

            await communicate.save(output_path)

            # Verificar que el archivo se creó correctamente
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"TTS generado: {output_path} ({os.path.getsize(output_path)} bytes)")
                return output_path
            else:
                logger.error("TTS: El archivo de audio no se generó correctamente")
                return None

        except Exception as e:
            logger.error(f"Error en TTS: {e}")
            return None

    def text_to_speech_sync(
        self,
        text: str,
        language: str = "es",
        voice_gender: str = "female",
        rate: str = "+0%",
        output_path: str | None = None,
    ) -> str | None:
        """
        Versión síncrona de text_to_speech.
        Ejecuta el TTS en un event loop separado.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si ya estamos en un event loop, crear uno nuevo en un hilo
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.text_to_speech(text, language, voice_gender, rate, output_path=output_path)
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(
                    self.text_to_speech(text, language, voice_gender, rate, output_path=output_path)
                )
        except RuntimeError:
            return asyncio.run(
                self.text_to_speech(text, language, voice_gender, rate, output_path=output_path)
            )

    def _get_voice(self, language: str, gender: str = "female") -> str:
        """Obtiene el nombre de la voz edge-tts según idioma y género."""
        lang_data = VOICE_MAP.get(language, VOICE_MAP.get("es"))
        voice = lang_data.get(gender, lang_data.get("default", "es-ES-ElviraNeural"))
        return voice

    # ─── Speech-to-Text (ASR) ──────────────────────────────────────

    async def speech_to_text(self, audio_path: str, language: str | None = None) -> dict:
        """
        Transcribe audio a texto usando HuggingFace Whisper.

        Args:
            audio_path: Ruta al archivo de audio
            language: Idioma del audio (None para auto-detección)

        Returns:
            Diccionario con text, language y success
        """
        if not self._asr_client:
            return {
                "text": "",
                "error": "ASR no disponible. Configura HF_API_TOKEN.",
                "success": False,
            }

        if not os.path.exists(audio_path):
            return {
                "text": "",
                "error": f"Archivo de audio no encontrado: {audio_path}",
                "success": False,
            }

        try:
            # Leer el archivo de audio
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            # Usar HuggingFace Inference API para transcripción
            result = self._asr_client.automatic_speech_recognition(
                audio=audio_data,
                model="openai/whisper-large-v3",
            )

            transcribed_text = result.get("text", "") if isinstance(result, dict) else str(result)

            if transcribed_text:
                logger.info(f"ASR transcrito: '{transcribed_text[:100]}...'")
                return {
                    "text": transcribed_text.strip(),
                    "language": language,
                    "success": True,
                }
            else:
                return {
                    "text": "",
                    "error": "No se pudo transcribir el audio. Puede que esté vacío o muy corto.",
                    "success": False,
                }

        except Exception as e:
            logger.error(f"Error en ASR: {e}")
            return {
                "text": "",
                "error": f"Error al transcribir: {e}",
                "success": False,
            }

    # ─── Descargar archivo de voz de Telegram ──────────────────────

    async def download_telegram_voice(
        self,
        file_id: str,
        bot_token: str,
        output_path: str | None = None,
    ) -> str | None:
        """
        Descarga un archivo de voz de Telegram.

        Args:
            file_id: ID del archivo en Telegram
            bot_token: Token del bot de Telegram
            output_path: Ruta de salida personalizada

        Returns:
            Ruta al archivo descargado, o None si falla
        """
        try:
            # Obtener la URL del archivo
            file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(file_url)
                data = response.json()

            if not data.get("ok"):
                logger.error(f"Error obteniendo archivo de Telegram: {data}")
                return None

            file_path = data["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

            # Generar ruta de salida
            if not output_path:
                temp_dir = DATA_DIR / "voice_temp"
                temp_dir.mkdir(parents=True, exist_ok=True)
                ext = Path(file_path).suffix or ".ogg"
                output_path = str(temp_dir / f"voice_{os.getpid()}_{id(file_id)}{ext}")

            # Descargar el archivo
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(download_url)
                with open(output_path, "wb") as f:
                    f.write(response.content)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"Voz descargada: {output_path} ({os.path.getsize(output_path)} bytes)")
                return output_path
            else:
                logger.error("Error: Archivo de voz vacío o no descargado")
                return None

        except Exception as e:
            logger.error(f"Error descargando voz de Telegram: {e}")
            return None

    # ─── Convertir formato de audio ────────────────────────────────

    def convert_to_mp3(self, input_path: str, output_path: str | None = None) -> str | None:
        """
        Convierte un archivo de audio a MP3 usando ffmpeg.
        Necesario porque Telegram envía audios en formato OGG/Opus.

        Args:
            input_path: Ruta al archivo de entrada
            output_path: Ruta al archivo de salida

        Returns:
            Ruta al archivo MP3, o None si falla
        """
        if not output_path:
            output_path = input_path.rsplit(".", 1)[0] + ".mp3"

        try:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-i", input_path, "-vn", "-ar", "16000", "-ac", "1",
                 "-b:a", "128k", "-y", output_path],
                capture_output=True,
                timeout=30,
            )

            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Audio convertido: {output_path}")
                return output_path
            else:
                logger.warning(f"ffmpeg falló: {result.stderr.decode()[:200]}")
                # Si ffmpeg falla, usar el archivo original (Whisper soporta OGG)
                return input_path

        except FileNotFoundError:
            logger.warning("ffmpeg no instalado. Usando archivo original.")
            return input_path
        except Exception as e:
            logger.error(f"Error convirtiendo audio: {e}")
            return input_path

    # ─── Utilidades ────────────────────────────────────────────────

    def get_available_languages(self) -> list[str]:
        """Devuelve la lista de idiomas disponibles para TTS."""
        return list(VOICE_MAP.keys())

    def get_voice_info(self, language: str = "es") -> dict:
        """Devuelve información sobre las voces disponibles para un idioma."""
        lang_data = VOICE_MAP.get(language, VOICE_MAP.get("es"))
        return {
            "language": language,
            "voices": lang_data,
        }

    def cleanup_temp_files(self, *paths: str):
        """Elimina archivos temporales de audio."""
        for path in paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.warning(f"Error eliminando archivo temporal {path}: {e}")

    @staticmethod
    def strip_markdown(text: str) -> str:
        """
        Elimina formato Markdown del texto antes de pasarlo a TTS.
        Para que la voz no diga "asterisco asterisco" etc.
        """
        import re

        # Eliminar negritas y cursivas
        text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
        # Eliminar enlaces [texto](url) → texto
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Eliminar emojis comunes
        text = re.sub(r'[🤖💬🔍🧠🌤️📖🌐🧮📝📄🔄📊👋❌✅⏳⏱️🗑️📚🌙🎙️🔊]', '', text)
        # Eliminar código
        text = re.sub(r'`{1,3}([^`]+)`{1,3}', r'\1', text)
        # Eliminar listas con viñetas
        text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)
        # Eliminar numeración de listas
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
        # Eliminar encabezados
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Eliminar líneas horizontales
        text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
        # Limpiar espacios múltiples
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'  +', ' ', text)

        return text.strip()
