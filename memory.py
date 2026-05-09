"""
memory.py — Sistema de memoria a largo plazo de NOVA
Implementa tres capas de memoria:
1. Memoria de conversación (corto plazo) — en memoria
2. Memoria semántica (largo plazo) — búsqueda vectorial en ChromaDB
3. Memoria estructurada (largo plazo) — SQLite persistente
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import (
    CONVERSATIONS_DIR,
    MAX_CONVERSATION_HISTORY,
    MEMORY_DB,
)

logger = logging.getLogger(__name__)


class MemorySystem:
    """Sistema de memoria multi-capa para NOVA."""

    def __init__(self):
        # ─── Capa 1: Memoria de conversación (en memoria) ───────────
        # user_id -> lista de mensajes
        self._conversation_history: dict[int, list[dict]] = {}

        # ─── Capa 2: Memoria semántica (ChromaDB) ──────────────────
        self._semantic_store = None  # Se inicializa bajo demanda

        # ─── Capa 3: Memoria estructurada (SQLite) ─────────────────
        self._init_sqlite()

        logger.info("MemorySystem inicializado (3 capas)")

    def _get_db_connection(self) -> sqlite3.Connection:
        """Obtiene conexión a la base de datos SQLite."""
        conn = sqlite3.connect(MEMORY_DB)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self):
        """Inicializa las tablas de SQLite."""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        # Tabla de perfil de usuario
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'es',
                created_at TEXT,
                last_interaction TEXT,
                interaction_count INTEGER DEFAULT 0,
                preferences TEXT DEFAULT '{}'
            )
        """)

        # Tabla de recuerdos explícitos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                importance INTEGER DEFAULT 5,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
            )
        """)

        # Tabla de notas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
            )
        """)

        conn.commit()
        conn.close()

    # ─── Capa 1: Memoria de conversación ────────────────────────────

    def add_to_conversation(self, user_id: int, role: str, content: str):
        """Añade un mensaje al historial de conversación del usuario."""
        if user_id not in self._conversation_history:
            self._conversation_history[user_id] = []

        self._conversation_history[user_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

        # Limitar tamaño del historial
        if len(self._conversation_history[user_id]) > MAX_CONVERSATION_HISTORY:
            self._conversation_history[user_id] = self._conversation_history[user_id][
                -MAX_CONVERSATION_HISTORY:
            ]

    def get_conversation_history(self, user_id: int) -> list[dict]:
        """Obtiene el historial de conversación del usuario."""
        return self._conversation_history.get(user_id, [])

    def clear_conversation(self, user_id: int):
        """Limpia el historial de conversación del usuario."""
        self._conversation_history[user_id] = []

    def save_conversation_to_file(self, user_id: int):
        """Guarda la conversación actual en un archivo JSON."""
        history = self._conversation_history.get(user_id, [])
        if not history:
            return

        filename = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = CONVERSATIONS_DIR / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            logger.info(f"Conversación guardada: {filepath}")
        except IOError as e:
            logger.error(f"Error guardando conversación: {e}")

    # ─── Capa 2: Memoria semántica ──────────────────────────────────

    def _get_semantic_store(self):
        """Obtiene la colección de memoria semántica (lazy init)."""
        if self._semantic_store is None:
            try:
                import chromadb
                from chromadb.config import Settings as ChromaSettings
                from config import VECTOR_STORE_DIR

                client = chromadb.PersistentClient(
                    path=str(VECTOR_STORE_DIR),
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                self._semantic_store = client.get_or_create_collection(
                    name="user_memories",
                    metadata={"description": "Memorias semánticas de usuarios"},
                )
            except Exception as e:
                logger.error(f"Error inicializando memoria semántica: {e}")
        return self._semantic_store

    def save_semantic_memory(self, user_id: int, content: str, category: str = "general") -> bool:
        """
        Guarda un recuerdo en la memoria semántica del usuario.

        Args:
            user_id: ID del usuario de Telegram
            content: Contenido del recuerdo
            category: Categoría del recuerdo

        Returns:
            True si se guardó correctamente
        """
        store = self._get_semantic_store()
        if store is None:
            return False

        try:
            memory_id = f"mem_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            store.add(
                ids=[memory_id],
                documents=[content],
                metadatas=[{
                    "user_id": user_id,
                    "category": category,
                    "created_at": datetime.now().isoformat(),
                }],
            )
            logger.info(f"Memoria semántica guardada para usuario {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error guardando memoria semántica: {e}")
            return False

    def search_semantic_memories(
        self, user_id: int, query: str, top_k: int = 3
    ) -> list[dict]:
        """
        Busca recuerdos semánticos del usuario.

        Args:
            user_id: ID del usuario
            query: Consulta para buscar recuerdos
            top_k: Número de resultados

        Returns:
            Lista de recuerdos relevantes
        """
        store = self._get_semantic_store()
        if store is None:
            return []

        try:
            # Filtrar por user_id
            results = store.query(
                query_texts=[query],
                n_results=top_k,
                where={"user_id": user_id},
            )

            memories = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    memories.append({
                        "content": doc,
                        "metadata": meta,
                    })

            return memories

        except Exception as e:
            logger.error(f"Error buscando memorias semánticas: {e}")
            return []

    def get_memory_context(self, user_id: int, query: str) -> str:
        """
        Obtiene contexto de memoria formateado para inyectar en el prompt.

        Args:
            user_id: ID del usuario
            query: Mensaje actual del usuario

        Returns:
            Texto formateado con recuerdos relevantes
        """
        # Buscar en memoria semántica
        semantic_memories = self.search_semantic_memories(user_id, query)

        # Buscar en memoria estructurada (SQLite)
        structured_memories = self.get_structured_memories(user_id)

        context_parts = []

        if semantic_memories:
            context_parts.append("### Recuerdos semánticos:")
            for mem in semantic_memories:
                context_parts.append(f"- {mem['content']}")

        if structured_memories:
            context_parts.append("### Datos recordados:")
            for mem in structured_memories:
                context_parts.append(f"- [{mem['category']}] {mem['content']}")

        # Añadir perfil del usuario si existe
        profile = self.get_user_profile(user_id)
        if profile:
            profile_info = []
            if profile.get("first_name"):
                profile_info.append(f"Nombre: {profile['first_name']}")
            if profile.get("language"):
                profile_info.append(f"Idioma: {profile['language']}")
            if profile.get("interaction_count", 0) > 0:
                profile_info.append(f"Interacciones: {profile['interaction_count']}")

            if profile_info:
                context_parts.append("### Perfil del usuario:")
                context_parts.extend(f"- {info}" for info in profile_info)

        return "\n".join(context_parts) if context_parts else ""

    # ─── Capa 3: Memoria estructurada (SQLite) ─────────────────────

    def update_user_profile(
        self,
        user_id: int,
        username: str | None = None,
        first_name: str | None = None,
        language: str | None = None,
    ):
        """Actualiza o crea el perfil del usuario."""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        # Verificar si el usuario ya existe
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        if existing:
            # Actualizar
            updates = {"last_interaction": now, "interaction_count": existing["interaction_count"] + 1}
            if username:
                updates["username"] = username
            if first_name:
                updates["first_name"] = first_name
            if language:
                updates["language"] = language

            set_clause = ", ".join(f"{k} = ?" for k in updates)
            cursor.execute(
                f"UPDATE user_profiles SET {set_clause} WHERE user_id = ?",
                list(updates.values()) + [user_id],
            )
        else:
            # Crear
            cursor.execute(
                """INSERT INTO user_profiles
                   (user_id, username, first_name, language, created_at, last_interaction, interaction_count)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (user_id, username, first_name, language or "es", now, now),
            )

        conn.commit()
        conn.close()

    def get_user_profile(self, user_id: int) -> dict | None:
        """Obtiene el perfil del usuario."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def save_structured_memory(
        self,
        user_id: int,
        content: str,
        category: str = "general",
        importance: int = 5,
    ) -> bool:
        """Guarda un recuerdo en la memoria estructurada (SQLite)."""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """INSERT INTO memories (user_id, content, category, importance, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, content, category, importance, datetime.now().isoformat()),
            )
            conn.commit()
            logger.info(f"Memoria estructurada guardada para usuario {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error guardando memoria estructurada: {e}")
            return False
        finally:
            conn.close()

    def get_structured_memories(
        self,
        user_id: int,
        category: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Obtiene recuerdos estructurados del usuario."""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        if category:
            cursor.execute(
                """SELECT * FROM memories
                   WHERE user_id = ? AND category = ?
                   ORDER BY importance DESC, created_at DESC
                   LIMIT ?""",
                (user_id, category, limit),
            )
        else:
            cursor.execute(
                """SELECT * FROM memories
                   WHERE user_id = ?
                   ORDER BY importance DESC, created_at DESC
                   LIMIT ?""",
                (user_id, limit),
            )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def delete_all_memories(self, user_id: int) -> int:
        """Elimina todos los recuerdos de un usuario."""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        # Eliminar de SQLite
        cursor.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        # Eliminar de ChromaDB (memoria semántica)
        store = self._get_semantic_store()
        if store is not None:
            try:
                all_items = store.get(where={"user_id": user_id})
                if all_items and all_items["ids"]:
                    store.delete(ids=all_items["ids"])
            except Exception as e:
                logger.error(f"Error eliminando memorias semánticas: {e}")

        return deleted

    # ─── Notas ──────────────────────────────────────────────────────

    def save_note(self, user_id: int, content: str) -> int:
        """Guarda una nota del usuario. Retorna el ID de la nota."""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO notes (user_id, content, created_at) VALUES (?, ?, ?)",
            (user_id, content, datetime.now().isoformat()),
        )
        note_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return note_id

    def get_notes(self, user_id: int, limit: int = 20) -> list[dict]:
        """Obtiene las notas del usuario."""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT * FROM notes
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def delete_note(self, note_id: int, user_id: int) -> bool:
        """Elimina una nota específica."""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM notes WHERE id = ? AND user_id = ?",
            (note_id, user_id),
        )

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    # ─── Preferencias del usuario ───────────────────────────────────

    def set_preference(self, user_id: int, key: str, value: str):
        """Establece una preferencia del usuario."""
        profile = self.get_user_profile(user_id)
        if not profile:
            self.update_user_profile(user_id)

        conn = self._get_db_connection()
        cursor = conn.cursor()

        preferences = json.loads(profile.get("preferences", "{}")) if profile else {}
        preferences[key] = value

        cursor.execute(
            "UPDATE user_profiles SET preferences = ? WHERE user_id = ?",
            (json.dumps(preferences, ensure_ascii=False), user_id),
        )

        conn.commit()
        conn.close()

    def get_preference(self, user_id: int, key: str, default: str = "") -> str:
        """Obtiene una preferencia del usuario."""
        profile = self.get_user_profile(user_id)
        if not profile:
            return default

        preferences = json.loads(profile.get("preferences", "{}"))
        return preferences.get(key, default)
