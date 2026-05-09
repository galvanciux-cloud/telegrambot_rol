# 🤖 NOVA — Agente de IA Conversacional

## Identidad

| Campo | Valor |
|-------|-------|
| **Nombre** | NOVA |
| **Versión** | 2.0.0 |
| **Tipo** | Agente de IA conversacional multi-función con voz |
| **Motor de IA** | HuggingFace Inference API — `HuggingFaceH4/zephyr-7b-beta` |
| **TTS (Voz)** | Microsoft Edge Neural TTS (edge-tts) |
| **ASR (Escucha)** | OpenAI Whisper Large v3 (via HuggingFace) |
| **Interfaz** | Telegram Bot |
| **Idioma principal** | Español (multilingüe, 10+ idiomas con voz) |

---

## ¿Para qué sirve?

NOVA es un asistente inteligente diseñado para ser tu compañero digital en Telegram. Combina capacidades de conversación avanzada con herramientas prácticas del día a día, memoria persistente, búsqueda en internet y ahora también **puede hablar y escuchar**, todo en un solo bot.

### Capacidades principales

1. **Conversación inteligente** — Mantén diálogos naturales y contextuales. NOVA comprende el contexto de la conversación y responde de forma coherente.

2. **🎙️ Voz (TTS + ASR)** — NOVA puede **hablar** y **escuchar**. Envíale un audio y lo transcribirá para entenderte. Activa el modo voz y te responderá con mensajes de voz en vez de texto. Soporta 10+ idiomas con voces masculinas y femeninas de alta calidad (Microsoft Neural TTS).

3. **Búsqueda en internet** — Consulta información actualizada en tiempo real. NOVA puede buscar en la web y sintetizar resultados para responder preguntas sobre actualidad, datos, o cualquier tema.

4. **Memoria a largo plazo** — NOVA recuerda información importante de cada usuario entre sesiones. Puedes decirle que recuerde tu nombre, preferencias, fechas importantes, o cualquier dato que quieras conservar.

5. **Base de conocimientos (RAG)** — Sistema de Generación Aumentada por Recuperación que permite a NOVA consultar documentos y conocimientos específicos almacenados en `knowledge.json` o añadidos dinámicamente.

6. **Calculadora matemática** — Resuelve operaciones matemáticas complejas con precisión.

7. **Información meteorológica** — Consulta el clima actual de cualquier ciudad del mundo.

8. **Búsqueda en Wikipedia** — Accede al conocimiento enciclopédico de Wikipedia en múltiples idiomas.

9. **Traducción** — Traduce texto entre más de 100 idiomas.

10. **Resumen de URLs** — Extrae y resume el contenido de artículos web.

11. **Notas y recordatorios** — Guarda notas personales y configura recordatorios.

---

## Arquitectura del sistema

```
┌─────────────────────────────────────────────────┐
│                   Telegram API                   │
│              (python-telegram-bot)                │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│                 telegram_bot.py                   │
│          (Manejador de mensajes, comandos y voz)  │
└──────────────────────┬──────────────────────────┘
                       │
        ┌──────────────┼───────────────┐
        ▼              ▼               ▼
┌─────────────┐ ┌───────────┐ ┌──────────────┐
│ ai_engine.py│ │tools.py   │ │  voice.py    │
│ (HuggingFace│ │(Funciones │ │ TTS (edge-tts│
│  Inference) │ │ útiles)   │ │ ASR (Whisper)│
└──────┬──────┘ └───────────┘ └──────────────┘
       │
       ▼
┌─────────────────┐  ┌──────────────────┐  ┌──────────┐
│ rag_system.py   │  │ web_search.py    │  │memory.py │
│ (ChromaDB +     │  │ (DuckDuckGo +    │  │(Memoria  │
│  Embeddings)    │  │  Scraping)       │  │largo     │
└─────────────────┘  └──────────────────┘  │plazo)    │
                                             └──────────┘
```

---

## Comandos de Telegram

### Comandos generales

| Comando | Descripción |
|---------|-------------|
| `/start` | Iniciar conversación con NOVA |
| `/help` | Mostrar ayuda y comandos disponibles |
| `/search <query>` | Buscar en internet |
| `/wiki <query>` | Buscar en Wikipedia |
| `/weather <ciudad>` | Consultar el clima |
| `/translate <idioma> <texto>` | Traducir texto |
| `/calc <expresión>` | Calcular operación matemática |
| `/remember <texto>` | Guardar en memoria a largo plazo |
| `/recall <texto>` | Recuperar recuerdos relacionados |
| `/forget` | Borrar todos los recuerdos |
| `/note <texto>` | Guardar una nota |
| `/notes` | Ver notas guardadas |
| `/summarize <url>` | Resumir contenido de una URL |
| `/add_knowledge <texto>` | Añadir conocimiento a la base RAG |
| `/reset` | Reiniciar contexto de conversación |
| `/stats` | Ver estadísticas del sistema |

### Comandos de voz

| Comando | Descripción |
|---------|-------------|
| `/voice` | Activar/desactivar modo voz (NOVA responde con audio) |
| `/speak <texto>` | Convertir texto a voz y enviar como audio |
| `/voices` | Ver idiomas y voces disponibles |
| 🎤 **Enviar audio** | Graba un mensaje de voz y NOVA lo transcribirá y responderá |

---

## Sistema de voz

### Text-to-Speech (TTS) — NOVA habla

NOVA usa **Microsoft Edge Neural TTS** (edge-tts), que proporciona voces de alta calidad, naturales y expresivas, completamente gratuito y sin necesidad de API key.

**Idiomas con voz disponible:**

| Idioma | Código | Voz femenina | Voz masculina |
|--------|--------|-------------|--------------|
| 🇪🇸 Español (España) | `es` | ElviraNeural | AlvaroNeural |
| 🇲🇽 Español (México) | `es-MX` | DaliaNeural | JorgeNeural |
| 🇦🇷 Español (Argentina) | `es-AR` | ElenaNeural | TomasNeural |
| 🇺🇸 Inglés (EEUU) | `en` | JennyNeural | GuyNeural |
| 🇬🇧 Inglés (UK) | `en-GB` | SoniaNeural | RyanNeural |
| 🇫🇷 Francés | `fr` | DeniseNeural | HenriNeural |
| 🇩🇪 Alemán | `de` | KatjaNeural | ConradNeural |
| 🇮🇹 Italiano | `it` | ElsaNeural | DiegoNeural |
| 🇧🇷 Portugués | `pt` | FranciscaNeural | AntonioNeural |
| 🇯🇵 Japonés | `ja` | NanamiNeural | KeitaNeural |
| 🇰🇷 Coreano | `ko` | SunHiNeural | InJoonNeural |
| 🇨🇳 Chino | `zh` | XiaoxiaoNeural | YunxiNeural |
| 🇷🇺 Ruso | `ru` | SvetlanaNeural | DmitryNeural |

### Speech-to-Text (ASR) — NOVA escucha

NOVA usa **OpenAI Whisper Large v3** a través de la API de HuggingFace para transcribir audios. Whisper es uno de los mejores modelos de reconocimiento de voz, capaz de:
- Transcribir en 99 idiomas
- Detectar el idioma automáticamente
- Funcionar con ruido de fondo
- Entender diferentes acentos

### Cómo funciona la interacción por voz

1. **El usuario envía un audio** → Telegram entrega el archivo OGG/Opus
2. **NOVA descarga el audio** → Lo convierte si es necesario
3. **Whisper transcribe** → Convierte la voz a texto
4. **NOVA muestra la transcripción** → "Te escuché decir: ..."
5. **La IA procesa el texto** → Genera una respuesta
6. **Si el modo voz está activo** → La respuesta se convierte a audio con edge-tts y se envía como mensaje de voz
7. **Si no** → Se envía como texto normal

---

## Modelos de IA utilizados

| Componente | Modelo | Propósito |
|------------|--------|-----------|
| **Conversación** | `HuggingFaceH4/zephyr-7b-beta` | Generación de respuestas principales |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | Vectorización para RAG y memoria semántica |
| **TTS (Voz)** | `edge-tts` (Microsoft Neural TTS) | Text-to-Speech, alta calidad, gratuito |
| **ASR (Escucha)** | `openai/whisper-large-v3` | Transcripción de audio a texto |

---

## Sistema de memoria

NOVA implementa un sistema de memoria de tres capas:

1. **Memoria de conversación (corto plazo)** — Contexto de los últimos mensajes de la conversación activa. Se reinicia con `/reset` o al cerrar la sesión.

2. **Memoria semántica (medio/largo plazo)** — Búsqueda vectorial sobre recuerdos almacenados con `/remember`. Permite recuperar información relevante por similitud semántica, no por coincidencia exacta.

3. **Memoria estructurada (largo plazo)** — Datos del usuario almacenados en SQLite: nombre, preferencias, notas, y metadatos. Persiste entre sesiones indefinidamente.

---

## Sistema RAG

El sistema de Generación Aumentada por Recuperación (RAG) funciona así:

1. Los conocimientos se vectorizan con `all-MiniLM-L6-v2`
2. Se almacenan en ChromaDB (base de datos vectorial local)
3. Al recibir una pregunta, se vectoriza y se buscan los fragmentos más relevantes
4. Los fragmentos recuperados se inyectan en el prompt del modelo como contexto
5. El modelo genera una respuesta informada por el conocimiento específico

Los conocimientos se pueden añadir de tres formas:
- Editando directamente `knowledge.json`
- Con el comando `/add_knowledge`
- Automáticamente desde resultados de búsqueda web

---

## Archivos del proyecto

| Archivo | Descripción |
|---------|-------------|
| `main.py` | Punto de entrada principal |
| `telegram_bot.py` | Integración con Telegram (textos + voz) |
| `ai_engine.py` | Motor de IA con HuggingFace |
| `voice.py` | Motor de voz: TTS (edge-tts) + ASR (Whisper) |
| `rag_system.py` | Sistema RAG con ChromaDB |
| `memory.py` | Memoria a largo plazo (SQLite + vectorial) |
| `web_search.py` | Búsqueda en internet |
| `tools.py` | Funciones útiles (clima, wiki, calc, etc.) |
| `config.py` | Configuración centralizada |
| `agent.md` | Este documento |
| `knowledge.json` | Base de conocimientos |
| `requirements.txt` | Dependencias Python |
| `.env` | Variables de entorno |

---

## Configuración de voz en `.env`

```bash
# Activar/desactivar voz
VOICE_ENABLED=true

# Idioma por defecto (es, en, fr, de, it, pt, ja, ko, zh, ru)
VOICE_LANGUAGE=es

# Género de voz (female o male)
VOICE_GENDER=female

# Velocidad de voz (+20% más rápido, -10% más lento, +0% normal)
VOICE_RATE=+0%

# Modelo de transcripción de audio
ASR_MODEL=openai/whisper-large-v3

# Responder siempre con voz (los usuarios pueden cambiar con /voice)
VOICE_AUTO_REPLY=false
```

---

## Requisitos

- Python 3.10+
- Cuenta de HuggingFace (gratuita) con token de acceso
- Conexión a internet
- Bot de Telegram creado via @BotFather
- ffmpeg (opcional, para conversión de formatos de audio)

---

## Notas de seguridad

- El token de Telegram y el token de HuggingFace NUNCA deben compartirse ni subirse a repositorios públicos.
- Las memorias y datos de usuario se almacenan localmente en SQLite.
- Las búsquedas web se realizan a través de DuckDuckGo (sin API key, sin tracking).
- La síntesis de voz usa Microsoft Edge TTS directamente (sin intermediarios).
- Los audios se procesan localmente y los archivos temporales se eliminan tras el envío.
- NOVA no recopila ni envía datos personales a terceros.
