# RAG&ROL 🤖

Agente de IA conversacional con **Ollama** (DeepSeek-R1 / Llama3.1 local), RAG con ChromaDB, sistema de roles/personalidades y Telegram como interfaz.

## Características

- **IA Local con Ollama** — Usa `deepseek-r1:8b` o `llama3.1:8b` sin depender de APIs externas
- **RAG (Retrieval-Augmented Generation)** — Base de conocimientos con ChromaDB y sentence-transformers
- **Sistema de Personalidades/Roles** — 8 roles configurables (`developer`, `profesor`, `frontend`, `linux`, etc.)
- **Gestión de Archivos Adjuntos** — Carga archivos `.md` al conocimiento vectorial
- **Memoria a Largo Plazo** — Historial de conversación y recuerdos por usuario
- **Herramientas Integradas** — Búsqueda web, Wikipedia, clima, traductor, calculadora
- **Interfaz Telegram** — Bot conversacional con múltiples comandos

## Requisitos

- Python 3.10+
- [Ollama](https://ollama.ai/) instalado y en ejecución
- Modelos Ollama: `ollama pull llama3.1:8b`
- Token de Telegram (de [@BotFather](https://t.me/BotFather))

## Instalación

```bash
# Clonar repositorio
git clone <repo_url>
cd telegram_ai_agent

# Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con TELEGRAM_BOT_TOKEN

# Descargar modelo Ollama
ollama pull llama3.1:8b

# Ejecutar
python main.py
```

## Estructura del Proyecto

```
telegram_ai_agent/
├── ai_engine.py          # Motor IA (Ollama)
├── rag_system.py         # Sistema RAG (ChromaDB)
├── telegram_bot.py       # Bot de Telegram
├── memory.py            # Memoria a largo plazo
├── config.py            # Configuración
├── tools.py             # Herramientas (clima, wiki, etc.)
├── web_search.py        # Búsqueda web
├── personality.md       # Personalidad base
├── prompts/             # Roles/personalidades
│   ├── intelligent_prompts.md
│   ├── developer.md
│   ├── profesor.md
│   ├── frontend.md
│   └── ...
├── data/
│   └── uploaded_knowledge/  # Archivos adjuntos
├── vector_store/        # Base vectorial ChromaDB
└── .env                 # Variables de entorno
```

## Comandos

| Comando | Descripción |
|---------|-------------|
| `/start` | Iniciar conversación |
| `/help` | Ayuda |
| `/rol <nombre>` | Cambiar personalidad (developer, profesor, etc.) |
| `/model <nombre>` | Cambiar modelo Ollama |
| `/search <query>` | Buscar en internet |
| `/wiki <término>` | Buscar en Wikipedia |
| `/weather <ciudad>` | Clima |
| `/calc <expresión>` | Calculadora |
| `/remember <texto>` | Guardar en memoria |
| `/recall <texto>` | Recuperar recuerdos |
| `/add_knowledge <texto>` | Añadir a base RAG |
| `/reset` | Reiniciar conversación |
| `/stats` | Estadísticas |

## Roles Disponibles

1. **general** — Asistente multi-función (por defecto)
2. **developer** — Desarrollador Senior
3. **profesor** — Docente/Pacificador
4. **frontend** — Desarrollador Frontend
5. **docs** — Redactor técnico
6. **data** — Analista de datos
7. **linux** — Linux/DevOps
8. **mentor** — Mentor de carrera

## Agregar Conocimientos

### Opción 1: Editar `knowledge.json`
```json
{
  "knowledge": [
    {
      "id": "kb_custom",
      "title": "Mi conocimiento",
      "content": "Contenido del conocimiento...",
      "category": "custom",
      "tags": ["tag1", "tag2"]
    }
  ]
}
```

### Opción 2: Archivos en `data/uploaded_knowledge/`
Coloca archivos `.md` en la carpeta — se cargan automáticamente al iniciar.

## Configuración (.env)

```bash
TELEGRAM_BOT_TOKEN=tu_token_de_telegram
HF_API_TOKEN=tu_token_de_huggingface  # Para embeddings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

## Licencia

MIT
