"""
telegram_bot.py — Integración de Billy con Telegram
Maneja todos los comandos y mensajes del bot, incluyendo voz.
"""

import asyncio
import logging
import os
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ai_engine import AIEngine
from config import (
    TELEGRAM_BOT_TOKEN,
    VOICE_AUTO_REPLY,
    VOICE_ENABLED,
    VOICE_GENDER,
    VOICE_LANGUAGE,
    VOICE_RATE,
    OLLAMA_AVAILABLE_MODELS,
    PROMPTS_DIR,
)
from memory import MemorySystem
from rag_system import RAGSystem
from tools import (
    calculate,
    detect_tool_intent,
    format_translation,
    format_weather,
    format_wikipedia,
    get_weather,
    search_wikipedia,
    translate_text,
)
from voice import VoiceEngine
from web_search import WebSearch

logger = logging.getLogger(__name__)


class NovaTelegramBot:
    """Bot de Telegram para NOVA AI Agent."""

    def __init__(self):
        self.ai_engine = AIEngine()
        self.rag_system = RAGSystem()
        self.memory = MemorySystem()
        self.web_search = WebSearch()
        self.voice = VoiceEngine()

        # Track de modo voz por usuario
        self._voice_mode: dict[int, bool] = {}  # user_id → voice_mode

        # Cargar conocimientos iniciales
        loaded = self.rag_system.load_knowledge_json()
        logger.info(f"Conocimientos cargados en RAG: {loaded}")

    def build_application(self) -> Application:
        """Construye la aplicación de Telegram con todos los handlers."""
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Comandos
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("search", self.cmd_search))
        app.add_handler(CommandHandler("wiki", self.cmd_wiki))
        app.add_handler(CommandHandler("weather", self.cmd_weather))
        app.add_handler(CommandHandler("translate", self.cmd_translate))
        app.add_handler(CommandHandler("calc", self.cmd_calc))
        app.add_handler(CommandHandler("remember", self.cmd_remember))
        app.add_handler(CommandHandler("recall", self.cmd_recall))
        app.add_handler(CommandHandler("forget", self.cmd_forget))
        app.add_handler(CommandHandler("note", self.cmd_note))
        app.add_handler(CommandHandler("notes", self.cmd_notes))
        app.add_handler(CommandHandler("summarize", self.cmd_summarize))
        app.add_handler(CommandHandler("add_knowledge", self.cmd_add_knowledge))
        app.add_handler(CommandHandler("reset", self.cmd_reset))
        app.add_handler(CommandHandler("stats", self.cmd_stats))
        app.add_handler(CommandHandler("model", self.cmd_model))
        app.add_handler(CommandHandler("rol", self.cmd_rol))

        # ─── Comandos de voz ────────────────────────────────────
        app.add_handler(CommandHandler("voice", self.cmd_voice))
        app.add_handler(CommandHandler("speak", self.cmd_speak))
        app.add_handler(CommandHandler("voices", self.cmd_voices))

        # Mensajes de voz (audios de Telegram)
        app.add_handler(
            MessageHandler(filters.VOICE | filters.AUDIO, self.handle_voice_message)
        )

        # Mensajes normales (conversación)
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        return app

    # ─── Comandos de Voz ────────────────────────────────────────────

    async def cmd_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /voice — Activa/desactiva modo voz (responde siempre con audio)."""
        user_id = update.effective_user.id

        # Toggle del modo voz
        current_mode = self._voice_mode.get(user_id, False)
        new_mode = not current_mode
        self._voice_mode[user_id] = new_mode

        # Guardar preferencia
        self.memory.set_preference(user_id, "voice_mode", str(new_mode).lower())

        if new_mode:
            status = (
                "🎙️ **Modo voz ACTIVADO**\n\n"
                "A partir de ahora responderé con mensajes de voz.\n"
                "Para desactivar: /voice\n"
                "Para un solo mensaje de voz: /speak <texto>"
            )
        else:
            status = (
                "💬 **Modo voz DESACTIVADO**\n\n"
                "Vuelvo a responder con texto normal.\n"
                "Para reactivar: /voice"
            )

        await update.message.reply_text(status, parse_mode="Markdown")

    async def cmd_speak(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /speak — Convierte texto a voz y envía como audio."""
        text = " ".join(context.args) if context.args else ""

        if not text:
            await update.message.reply_text(
                "❌ Uso: /speak <texto>\n"
                "Ejemplo: /speak Hola, soy NOVA y puedo hablar contigo"
            )
            return

        if not VOICE_ENABLED:
            await update.message.reply_text("❌ La función de voz no está habilitada.")
            return

        await update.message.chat.send_action("record_voice")

        # Detectar idioma del texto (simple heurística)
        language = self._detect_language(text)

        audio_path = await self.voice.text_to_speech(
            text=text,
            language=language,
            voice_gender=VOICE_GENDER,
            rate=VOICE_RATE,
        )

        if audio_path:
            try:
                with open(audio_path, "rb") as audio_file:
                    await update.message.reply_voice(audio_file)
            except Exception as e:
                logger.error(f"Error enviando voz: {e}")
                await update.message.reply_text(f"❌ Error al enviar audio: {e}")
            finally:
                self.voice.cleanup_temp_files(audio_path)
        else:
            await update.message.reply_text("❌ No pude generar el audio. Verifica que edge-tts esté instalado.")

    async def cmd_voices(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /voices — Muestra voces e idiomas disponibles."""
        languages = self.voice.get_available_languages()
        voice_info = self.voice.get_voice_info(VOICE_LANGUAGE)

        lang_names = {
            "es": "🇪🇸 Español (España)", "es-MX": "🇲🇽 Español (México)",
            "es-AR": "🇦🇷 Español (Argentina)", "en": "🇺🇸 Inglés (EEUU)",
            "en-GB": "🇬🇧 Inglés (Reino Unido)", "fr": "🇫🇷 Francés",
            "de": "🇩🇪 Alemán", "it": "🇮🇹 Italiano", "pt": "🇧🇷 Portugués",
            "ja": "🇯🇵 Japonés", "ko": "🇰🇷 Coreano", "zh": "🇨🇳 Chino",
            "ru": "🇷🇺 Ruso",
        }

        voices_text = (
            "🎙️ **Voces disponibles en NOVA**\n\n"
            f"**Voz actual:** {voice_info['voices'].get(VOICE_GENDER, voice_info['voices']['default'])}\n"
            f"**Idioma actual:** {lang_names.get(VOICE_LANGUAGE, VOICE_LANGUAGE)}\n"
            f"**Género actual:** {VOICE_GENDER}\n\n"
            "**Idiomas disponibles:**\n"
        )

        for lang_code in languages:
            name = lang_names.get(lang_code, lang_code)
            voices_text += f"• {name} (`{lang_code}`)\n"

        voices_text += (
            "\n**Comandos de voz:**\n"
            "/voice — Activar/desactivar modo voz\n"
            "/speak <texto> — Convertir texto a voz\n"
            "/voices — Ver esta información\n\n"
            "💡 Configura idioma y género en el archivo `.env`"
        )

        await update.message.reply_text(voices_text, parse_mode="Markdown")

    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja mensajes de voz/audio del usuario (ASR)."""
        user = update.effective_user
        user_id = user.id

        # Actualizar perfil
        self.memory.update_user_profile(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
        )

        await update.message.chat.send_action("typing")

        # Obtener información del archivo de voz
        voice = update.message.voice or update.message.audio

        if not voice:
            await update.message.reply_text("❌ No pude procesar ese audio.")
            return

        file_id = voice.file_id

        # Descargar el audio de Telegram
        audio_path = await self.voice.download_telegram_voice(file_id, TELEGRAM_BOT_TOKEN)

        if not audio_path:
            await update.message.reply_text("❌ No pude descargar el audio. Inténtalo de nuevo.")
            return

        # Convertir a formato compatible si es necesario
        converted_path = self.voice.convert_to_mp3(audio_path)

        # Transcribir el audio
        transcription = await self.voice.speech_to_text(converted_path)

        # Limpiar archivos temporales
        self.voice.cleanup_temp_files(audio_path, converted_path)

        if not transcription.get("success"):
            await update.message.reply_text(
                f"❌ No pude transcribir tu audio: {transcription.get('error', 'Error desconocido')}\n\n"
                "💡 Asegúrate de que el audio sea claro y tenga voz reconocible."
            )
            return

        transcribed_text = transcription["text"]

        if not transcribed_text.strip():
            await update.message.reply_text(
                "🔇 No detecté voz en ese audio. Asegúrate de grabar con claridad."
            )
            return

        # Mostrar transcripción al usuario
        await update.message.reply_text(
            f"🎙️ **Te escuché decir:**\n\n_{transcribed_text}_",
            parse_mode="Markdown",
        )

        # Procesar el texto transcrito como un mensaje normal
        # Guardar en historial
        self.memory.add_to_conversation(user_id, "user", f"[Voz] {transcribed_text}")

        # Generar respuesta de IA
        await self._process_and_respond(update, user_id, transcribed_text)

    # ─── Comandos originales ────────────────────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start — Inicialización del bot."""
        user = update.effective_user
        user_id = user.id

        # Registrar/actualizar perfil del usuario
        self.memory.update_user_profile(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
        )

        # Restaurar preferencia de voz si existe
        voice_pref = self.memory.get_preference(user_id, "voice_mode", "false")
        self._voice_mode[user_id] = voice_pref == "true"

        welcome = (
            f"👋 ¡Hola {user.first_name}! Soy **Billy**, tu asistente de IA.\n\n"
            "Puedo ayudarte con muchas cosas:\n"
            "💬 Conversar y responder preguntas\n"
            "🔍 Buscar en internet\n"
            "🧠 Recordar información para ti\n"
            "🌤️ Consultar el clima\n"
            "📖 Buscar en Wikipedia\n"
            "🌐 Traducir textos\n"
            "🧮 Calcular operaciones matemáticas\n"
            "📝 Tomar notas\n"
            "📄 Resumir artículos web\n"
            "🎙️ **Hablar contigo por voz** — ¡envíame un audio!\n\n"
            "Usa /help para ver todos los comandos disponibles."
        )

        await update.message.reply_text(welcome, parse_mode="Markdown")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help — Muestra la ayuda."""
        help_text = (
            "🤖 **Billy — Comandos disponibles**\n\n"
            "**Conversación:**\n"
            "Escribe cualquier mensaje y conversaré contigo usando IA.\n\n"
            "**Búsqueda y datos:**\n"
            "/search `<consulta>` — Buscar en internet\n"
            "/wiki `<término>` — Buscar en Wikipedia\n"
            "/weather `<ciudad>` — Ver el clima actual\n"
            "/summarize `<url>` — Resumir un artículo web\n\n"
            "**Herramientas:**\n"
            "/calc `<expresión>` — Calcular (ej: 2+3*4, sqrt(16))\n"
            "/translate `<texto>` — Traducir (ej: /translate hello es)\n\n"
            "**🎙️ Voz:**\n"
            "/voice — Activar/desactivar modo voz (respondo con audio)\n"
            "/speak `<texto>` — Convertir texto a voz\n"
            "/voices — Ver idiomas y voces disponibles\n"
            "🎤 Envíame un audio y lo transcribiré\n\n"
            "**Memoria:**\n"
            "/remember `<texto>` — Guardar en memoria a largo plazo\n"
            "/recall `<texto>` — Buscar en tus recuerdos\n"
            "/forget — Borrar todos tus recuerdos\n\n"
            "**Notas:**\n"
            "/note `<texto>` — Guardar una nota\n"
            "/notes — Ver tus notas\n\n"
            "**Conocimientos:**\n"
            "/add_knowledge `<texto>` — Añadir a la base de conocimientos\n\n"
            "**Sistema:**\n"
            "/reset — Reiniciar contexto de conversación\n"
            "/model — Ver/cambiar modelo de IA\n"
            "/rol — Cambiar personalidad/rol\n"
            "/stats — Ver estadísticas del sistema"
        )

        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def cmd_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /search — Búsqueda en internet."""
        query = " ".join(context.args) if context.args else ""

        if not query:
            await update.message.reply_text(
                "❌ Uso: /search <consulta>\nEjemplo: /search noticias de hoy"
            )
            return

        await update.message.chat.send_action("typing")

        results = self.web_search.search_and_format(query)

        # También guardar resultados interesantes en RAG
        raw_results = self.web_search.search(query, max_results=3)
        if raw_results and "error" not in raw_results[0]:
            self.rag_system.add_from_web_search(query, raw_results)

        await update.message.reply_text(results, parse_mode="Markdown")

    async def cmd_wiki(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /wiki — Búsqueda en Wikipedia."""
        query = " ".join(context.args) if context.args else ""

        if not query:
            await update.message.reply_text(
                "❌ Uso: /wiki <término>\nEjemplo: /wiki Inteligencia artificial"
            )
            return

        await update.message.chat.send_action("typing")

        result = search_wikipedia(query)
        formatted = format_wikipedia(result)

        # Añadir a conocimientos si es útil
        if result.get("success") and result.get("summary"):
            self.rag_system.add_document(
                content=result["summary"],
                title=f"Wikipedia: {result.get('title', query)}",
                category="wikipedia",
                tags=["wikipedia", query.lower()],
            )

        await update.message.reply_text(formatted, parse_mode="Markdown")

    async def cmd_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /weather — Información meteorológica."""
        city = " ".join(context.args) if context.args else ""

        if not city:
            await update.message.reply_text(
                "❌ Uso: /weather <ciudad>\nEjemplo: /weather Madrid"
            )
            return

        await update.message.chat.send_action("typing")

        result = get_weather(city)
        formatted = format_weather(result)

        await update.message.reply_text(formatted, parse_mode="Markdown")

    async def cmd_translate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /translate — Traducción de texto."""
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ Uso: /translate <texto> <idioma_destino>\n"
                "Ejemplo: /translate hello es\n"
                "Idiomas: en (inglés), es (español), fr (francés), "
                "de (alemán), it (italiano), pt (portugués), etc."
            )
            return

        target_lang = context.args[-1].lower()
        text = " ".join(context.args[:-1])

        await update.message.chat.send_action("typing")

        result = translate_text(text, target_lang)
        formatted = format_translation(result)

        await update.message.reply_text(formatted, parse_mode="Markdown")

    async def cmd_calc(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /calc — Calculadora matemática."""
        expression = " ".join(context.args) if context.args else ""

        if not expression:
            await update.message.reply_text(
                "❌ Uso: /calc <expresión>\n"
                "Ejemplos: /calc 2+3*4, /calc sqrt(16), /calc sin(pi/2)"
            )
            return

        result = calculate(expression)

        if "error" in result:
            await update.message.reply_text(f"❌ {result['error']}")
        else:
            await update.message.reply_text(
                f"🧮 **{result['formatted']}**", parse_mode="Markdown"
            )

    async def cmd_remember(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /remember — Guardar en memoria a largo plazo."""
        content = " ".join(context.args) if context.args else ""
        user_id = update.effective_user.id

        if not content:
            await update.message.reply_text(
                "❌ Uso: /remember <texto a recordar>\n"
                "Ejemplo: /remember Mi cumpleaños es el 15 de marzo"
            )
            return

        # Guardar en ambas capas de memoria
        self.memory.save_structured_memory(user_id, content, category="explicit")
        self.memory.save_semantic_memory(user_id, content, category="explicit")

        await update.message.reply_text(
            "🧠 ¡Recordado! Guardé esa información en mi memoria a largo plazo."
        )

    async def cmd_recall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /recall — Recuperar recuerdos."""
        query = " ".join(context.args) if context.args else ""
        user_id = update.effective_user.id

        if not query:
            # Mostrar todos los recuerdos estructurados
            memories = self.memory.get_structured_memories(user_id, limit=10)
            if not memories:
                await update.message.reply_text(
                    "🧠 No tengo recuerdos guardados tuyos todavía.\n"
                    "Usa /remember <texto> para guardar información."
                )
                return

            formatted = "🧠 **Tus recuerdos guardados:**\n\n"
            for mem in memories:
                date = mem.get("created_at", "")[:10]
                formatted += f"• [{date}] {mem['content']}\n"

            await update.message.reply_text(formatted, parse_mode="Markdown")
            return

        # Búsqueda semántica
        semantic_results = self.memory.search_semantic_memories(user_id, query)
        structured_results = self.memory.get_structured_memories(user_id, limit=5)

        response_parts = ["🧠 **Recuerdos encontrados:**\n"]

        if semantic_results:
            response_parts.append("*Búsqueda semántica:*")
            for mem in semantic_results:
                response_parts.append(f"• {mem['content']}")
            response_parts.append("")

        if structured_results:
            response_parts.append("*Recuerdos estructurados:*")
            for mem in structured_results:
                response_parts.append(f"• [{mem.get('category', 'general')}] {mem['content']}")

        if not semantic_results and not structured_results:
            response_parts.append("No encontré recuerdos relacionados. Usa /remember para guardar información.")

        await update.message.reply_text("\n".join(response_parts), parse_mode="Markdown")

    async def cmd_forget(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /forget — Borrar todos los recuerdos."""
        user_id = update.effective_user.id

        deleted = self.memory.delete_all_memories(user_id)

        await update.message.reply_text(
            f"🗑️ Se borraron {deleted} recuerdos de mi memoria.\n"
            "¡Empezamos de cero! Usa /remember para guardar nuevos recuerdos."
        )

    async def cmd_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /note — Guardar nota."""
        content = " ".join(context.args) if context.args else ""
        user_id = update.effective_user.id

        if not content:
            await update.message.reply_text(
                "❌ Uso: /note <texto de la nota>\nEjemplo: /note Comprar leche"
            )
            return

        note_id = self.memory.save_note(user_id, content)

        await update.message.reply_text(f"📝 Nota guardada (ID: {note_id})")

    async def cmd_notes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /notes — Ver notas."""
        user_id = update.effective_user.id

        notes = self.memory.get_notes(user_id)

        if not notes:
            await update.message.reply_text(
                "📝 No tienes notas guardadas.\nUsa /note <texto> para crear una."
            )
            return

        formatted = "📝 **Tus notas:**\n\n"
        for note in notes:
            date = note.get("created_at", "")[:10]
            formatted += f"#{note['id']} [{date}] {note['content']}\n"

        await update.message.reply_text(formatted, parse_mode="Markdown")

    async def cmd_summarize(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /summarize — Resumir URL."""
        url = " ".join(context.args) if context.args else ""

        if not url or not url.startswith("http"):
            await update.message.reply_text(
                "❌ Uso: /summarize <url>\nEjemplo: /summarize https://example.com/article"
            )
            return

        await update.message.chat.send_action("typing")

        # Obtener contenido de la URL
        result = self.web_search.fetch_url_sync(url)

        if not result.get("success"):
            await update.message.reply_text(f"❌ {result.get('content', 'Error al acceder a la URL')}")
            return

        # Generar resumen con IA
        content = result.get("content", "")
        title = result.get("title", url)

        if len(content) < 100:
            await update.message.reply_text(
                f"📄 **{title}**\n\nEl contenido es muy corto para resumir:\n\n{content[:500]}"
            )
            return

        # Pedir a la IA que resuma
        summary_prompt = (
            f"Resume el siguiente artículo de forma concisa y clara en español. "
            f"Extrae los puntos clave y preséntalos de forma organizada.\n\n"
            f"Título: {title}\n\nContenido:\n{content[:3000]}"
        )

        summary = self.ai_engine.quick_chat(summary_prompt)

        # Guardar en RAG
        self.rag_system.add_document(
            content=content[:2000],
            title=f"URL: {title}",
            category="summarized_url",
            tags=["url", "summary"],
        )

        response = f"📄 **Resumen de: {title}**\n\n{summary}\n\n🔗 [Ver original]({url})"
        await update.message.reply_text(response, parse_mode="Markdown")

    async def cmd_add_knowledge(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /add_knowledge — Añadir conocimiento a RAG."""
        content = " ".join(context.args) if context.args else ""

        if not content:
            await update.message.reply_text(
                "❌ Uso: /add_knowledge <texto del conocimiento>\n"
                "Ejemplo: /add_knowledge Python fue creado por Guido van Rossum en 1991"
            )
            return

        doc_id = self.rag_system.add_document(
            content=content,
            title="Conocimiento añadido por usuario",
            category="user_added",
            tags=["user", "manual"],
        )

        if doc_id:
            await update.message.reply_text(
                "📚 ¡Conocimiento añadido a mi base de datos! "
                "Podré consultarlo cuando sea relevante en futuras conversaciones."
            )
        else:
            await update.message.reply_text("❌ Error al añadir el conocimiento.")

    async def cmd_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /reset — Reiniciar contexto de conversación."""
        user_id = update.effective_user.id

        # Guardar conversación actual antes de resetear
        self.memory.save_conversation_to_file(user_id)
        self.memory.clear_conversation(user_id)

        await update.message.reply_text(
            "🔄 Contexto de conversación reiniciado. "
            "Tu memoria a largo plazo sigue intacta. ¡Empezamos una conversación nueva!"
        )

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stats — Estadísticas del sistema."""
        user_id = update.effective_user.id

        rag_stats = self.rag_system.get_stats()

        profile = self.memory.get_user_profile(user_id)
        memories = self.memory.get_structured_memories(user_id, limit=100)
        notes = self.memory.get_notes(user_id, limit=100)

        voice_status = "✅ Activado" if self._voice_mode.get(user_id, False) else "❌ Desactivado"

        stats_text = (
            "📊 **Estadísticas de Billy**\n\n"
            f"**Base de conocimientos:**\n"
            f"• Documentos indexados: {rag_stats.get('total_documents', 0)}\n"
            f"• Categorías: {', '.join(rag_stats.get('categories', ['N/A']))}\n\n"
            f"**Tu perfil:**\n"
            f"• Nombre: {profile.get('first_name', 'N/A') if profile else 'N/A'}\n"
            f"• Interacciones: {profile.get('interaction_count', 0) if profile else 0}\n"
            f"• Recuerdos guardados: {len(memories)}\n"
            f"• Notas guardadas: {len(notes)}\n"
            f"• Modo voz: {voice_status}\n\n"
            f"**Sistema:**\n"
            f"• Modelo IA: {self.ai_engine.get_active_model()}\n"
            f"• Embeddings: all-MiniLM-L6-v2\n"
            f"• Almacén vectorial: ChromaDB"
        )

        await update.message.reply_text(stats_text, parse_mode="Markdown")

    async def cmd_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /model — Cambiar modelo de Ollama."""
        if not context.args:
            current = self.ai_engine.get_active_model()
            available = "\n".join([f"• `{m}`" for m in OLLAMA_AVAILABLE_MODELS])
            msg = (
                f"🤖 **Modelo actual:** `{current}`\n\n"
                f"**Modelos disponibles:**\n{available}\n\n"
                "Cambiar con: /model <nombre_modelo>\n"
                "Ejemplo: /model llama3.1:8b"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        new_model = context.args[0]
        if new_model not in OLLAMA_AVAILABLE_MODELS:
            await update.message.reply_text(
                f"❌ Modelo no disponible: {new_model}\n"
                f"Disponibles: {', '.join(OLLAMA_AVAILABLE_MODELS)}"
            )
            return

        self.ai_engine.model = new_model
        logger.info(f"Modelo cambiado a: {new_model}")
        await update.message.reply_text(
            f"✅ Modelo cambiado a: `{new_model}`\n"
            "El siguiente mensaje usará este modelo."
        )

    async def cmd_rol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /rol — Cambiar rol/personalidad."""
        if not context.args:
            roles_text = self.ai_engine._intelligent_prompts or (
                "**Roles disponibles:**\n"
                "1. general — Asistente general\n"
                "2. developer — Desarrollador Senior\n"
                "3. profesor — Profesor/Docente\n"
                "4. frontend — Frontend Developer\n"
                "5. docs — Documentación\n"
                "6. data — Analista de Datos\n"
                "7. linux — Linux/DevOps\n"
                "8. mentor — Mentor de Carrera\n\n"
                "Cambiar con: /rol <nombre>\n"
                "Ejemplo: /rol developer"
            )
            await update.message.reply_text(roles_text, parse_mode="Markdown")
            return

        role_input = context.args[0].lower()

        role_mapping = {
            "1": "general", "general": "general",
            "2": "developer", "developer": "developer",
            "3": "profesor", "profesor": "profesor",
            "4": "frontend", "frontend": "frontend",
            "5": "docs", "docs": "docs",
            "6": "data", "data": "data",
            "7": "linux", "linux": "linux",
            "8": "mentor", "mentor": "mentor",
        }

        role = role_mapping.get(role_input, role_input)

        if role == "general":
            self.ai_engine.set_role("general")
            await update.message.reply_text("✅ Rol cambiado a: **Asistente General**")
        else:
            role_file = PROMPTS_DIR / f"{role}.md"
            if role_file.exists():
                self.ai_engine.set_role(role)
                await update.message.reply_text(f"✅ Rol cambiado a: **{role}**")
            else:
                await update.message.reply_text(
                    f"❌ Rol no encontrado: {role}\n"
                    "Usa /rol sin argumentos para ver roles disponibles."
                )

    # ─── Mensajes normales (conversación) ──────────────────────────

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja mensajes de texto normales (conversación con IA)."""
        user = update.effective_user
        user_id = user.id
        message_text = update.message.text

        # Actualizar perfil del usuario
        self.memory.update_user_profile(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
        )

        # Guardar mensaje del usuario en historial
        self.memory.add_to_conversation(user_id, "user", message_text)

        # Generar respuesta
        await self._process_and_respond(update, user_id, message_text)

    async def _process_and_respond(
        self, update: Update, user_id: int, message_text: str
    ):
        """
        Procesa un mensaje de texto y genera la respuesta de IA.
        Si el modo voz está activado, responde con audio.
        """
        # Indicar que está escribiendo
        await update.message.chat.send_action("typing")

        # 1. Detectar si necesita una herramienta específica
        tool_intent = detect_tool_intent(message_text)
        tool_results = ""

        if tool_intent:
            tool_name = tool_intent["tool"]
            tool_params = tool_intent["params"]

            if tool_name == "weather":
                result = get_weather(tool_params["city"])
                if result.get("success"):
                    tool_results = format_weather(result)
                else:
                    tool_results = f"Consulta de clima: {result.get('error', 'Sin resultados')}"

            elif tool_name == "calculator":
                result = calculate(tool_params["expression"])
                if "result" in result:
                    tool_results = f"Cálculo: {result['formatted']}"
                else:
                    tool_results = f"Error en cálculo: {result.get('error', 'Error')}"

            elif tool_name == "wikipedia":
                result = search_wikipedia(tool_params["query"])
                if result.get("success"):
                    tool_results = f"Wikipedia: {result['summary']}"
                else:
                    tool_results = ""

            elif tool_name == "translate":
                result = translate_text(
                    tool_params["text"], tool_params["target_lang"]
                )
                if result.get("success"):
                    tool_results = format_translation(result)
                else:
                    tool_results = ""

        # 2. Determinar si necesita búsqueda web
        web_context = ""
        needs_web_search = self._should_search_web(message_text)

        if needs_web_search:
            web_context = self.web_search.search_for_context(message_text, max_results=3)
            if web_context:
                # Añadir resultados a RAG
                raw_results = self.web_search.search(message_text, max_results=3)
                if raw_results and "error" not in raw_results[0]:
                    self.rag_system.add_from_web_search(message_text, raw_results)

        # 3. Obtener contexto RAG
        rag_context = self.rag_system.get_context_for_query(message_text)

        # 4. Obtener contexto de memoria
        memory_context = self.memory.get_memory_context(user_id, message_text)

        # 5. Obtener historial de conversación
        conversation_history = self.memory.get_conversation_history(user_id)[:-1]  # Excluir el mensaje actual

        # 6. Generar respuesta
        response = self.ai_engine.generate_response(
            user_message=message_text,
            conversation_history=conversation_history,
            rag_context=rag_context,
            memory_context=memory_context,
            tool_results=tool_results or (f"\nResultados de búsqueda web:\n{web_context}" if web_context else ""),
        )

        # Guardar respuesta en historial
        self.memory.add_to_conversation(user_id, "assistant", response)

        # 7. Decidir si responder con texto o voz
        voice_mode = self._voice_mode.get(user_id, False)

        if voice_mode and VOICE_ENABLED and self.voice._tts_available:
            await self._send_voice_response(update, response)
        else:
            # Enviar respuesta de texto (dividir si es muy larga)
            await self._send_long_message(update, response)

    async def _send_voice_response(self, update: Update, text: str):
        """
        Convierte la respuesta de texto a voz y la envía como mensaje de audio.
        También envía el texto como alternativa.
        """
        # Limpiar Markdown para TTS
        clean_text = VoiceEngine.strip_markdown(text)

        if not clean_text.strip():
            await self._send_long_message(update, text)
            return

        await update.message.chat.send_action("record_voice")

        # Detectar idioma
        language = self._detect_language(clean_text)

        # Generar audio
        audio_path = await self.voice.text_to_speech(
            text=clean_text,
            language=language,
            voice_gender=VOICE_GENDER,
            rate=VOICE_RATE,
        )

        if audio_path:
            try:
                # Enviar el audio
                with open(audio_path, "rb") as audio_file:
                    await update.message.reply_voice(audio_file)

                # También enviar texto resumido como alternativa
                if len(text) > 200:
                    short_text = text[:200] + "..."
                else:
                    short_text = text

                try:
                    await update.message.reply_text(short_text, parse_mode="Markdown")
                except Exception:
                    pass

            except Exception as e:
                logger.error(f"Error enviando voz: {e}")
                # Fallback a texto
                await self._send_long_message(update, text)
            finally:
                self.voice.cleanup_temp_files(audio_path)
        else:
            # Fallback a texto si TTS falla
            await self._send_long_message(update, text)

    # ─── Utilidades ────────────────────────────────────────────────

    def _should_search_web(self, message: str) -> bool:
        """Determina si un mensaje necesita búsqueda web."""
        search_indicators = [
            "actual", "hoy", "ahora", "reciente", "último", "ultimo",
            "noticia", "noticias", "precio", "cotización", "cotizacion",
            "resultado", "qué tal", "que tal", "current", "latest", "today",
            "news", "price", "2024", "2025", "2026",
        ]
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in search_indicators)

    def _detect_language(self, text: str) -> str:
        """
        Detecta el idioma probable del texto.
        Heurística simple basada en caracteres y palabras comunes.
        """
        text_lower = text.lower()

        # Indicadores por idioma
        spanish_words = {"el", "la", "los", "las", "de", "en", "que", "por", "con", "una", "uno", "es", "está", "hola", "gracias", "sí", "también", "pero", "como", "más", "muy", "puedes", "información"}
        english_words = {"the", "is", "are", "and", "or", "but", "in", "on", "at", "to", "for", "with", "can", "you", "hello", "thanks", "yes", "also", "how", "what", "this", "that", "please"}
        french_words = {"le", "la", "les", "de", "du", "des", "est", "et", "en", "un", "une", "bonjour", "merci", "oui", "avec", "pour", "dans"}
        german_words = {"der", "die", "das", "und", "ist", "ein", "eine", "mit", "für", "auf", "nicht", "auch", "hallo", "danke", "ja", "aber"}

        words = set(text_lower.split())

        scores = {
            "es": len(words & spanish_words),
            "en": len(words & english_words),
            "fr": len(words & french_words),
            "de": len(words & german_words),
        }

        best_lang = max(scores, key=scores.get)
        return best_lang if scores[best_lang] > 0 else VOICE_LANGUAGE

    async def _send_long_message(self, update: Update, text: str, max_length: int = 4000):
        """Envía un mensaje largo dividiéndolo si es necesario."""
        if len(text) <= max_length:
            try:
                await update.message.reply_text(text, parse_mode="Markdown")
            except Exception:
                # Si falla Markdown, enviar sin formato
                await update.message.reply_text(text)
            return

        # Dividir en párrafos
        chunks = []
        current_chunk = ""

        for line in text.split("\n"):
            if len(current_chunk) + len(line) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += "\n" + line if current_chunk else line

        if current_chunk:
            chunks.append(current_chunk)

        for chunk in chunks:
            try:
                await update.message.reply_text(chunk, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(chunk)
            # Pequeña pausa entre mensajes
            await asyncio.sleep(0.5)
