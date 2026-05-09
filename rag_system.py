"""
rag_system.py — Sistema RAG (Retrieval-Augmented Generation) de Billy
Usa ChromaDB como base de datos vectorial y sentence-transformers para embeddings.
Permite cargar conocimientos desde archivos .md y knowledge.json.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import (
    EMBEDDING_MODEL,
    KNOWLEDGE_FILE,
    RAG_TOP_K,
    VECTOR_STORE_DIR,
    UPLOADED_KNOWLEDGE_DIR,
)

logger = logging.getLogger(__name__)


class RAGSystem:
    """Sistema de Generación Aumentada por Recuperación."""

    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(
            path=str(VECTOR_STORE_DIR),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        self.collection = self.chroma_client.get_or_create_collection(
            name="knowledge_base",
            metadata={"description": "Base de conocimientos de Billy"},
        )

        self._embedding_function = None
        logger.info(
            f"RAGSystem inicializado. Documentos en colección: {self.collection.count()}"
        )

    def _get_embedding_function(self):
        """Obtiene la función de embeddings (lazy loading del modelo)."""
        if self._embedding_function is None:
            try:
                from chromadb.utils import embedding_functions

                self._embedding_function = (
                    embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name=EMBEDDING_MODEL,
                    )
                )
                logger.info(f"Modelo de embeddings cargado: {EMBEDDING_MODEL}")
            except Exception as e:
                logger.error(f"Error cargando modelo de embeddings: {e}")
                self._embedding_function = None
        return self._embedding_function

    def add_document(
        self,
        content: str,
        title: str = "",
        category: str = "general",
        tags: list[str] | None = None,
        doc_id: str | None = None,
    ) -> str:
        """Añade un documento a la base de conocimientos."""
        if not content.strip():
            return ""

        doc_id = doc_id or f"doc_{uuid.uuid4().hex[:8]}"
        metadata = {
            "title": title or "Sin título",
            "category": category,
            "tags": json.dumps(tags or [], ensure_ascii=False),
        }

        chunks = self._split_text(content, max_length=500)

        try:
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}" if len(chunks) > 1 else doc_id
                chunk_metadata = {**metadata, "chunk_index": i, "total_chunks": len(chunks)}

                self.collection.add(
                    ids=[chunk_id],
                    documents=[chunk],
                    metadatas=[chunk_metadata],
                )

            logger.info(f"Documento añadido: {doc_id} ({len(chunks)} chunks)")
            return doc_id

        except Exception as e:
            logger.error(f"Error añadiendo documento: {e}")
            return ""

    def search(
        self,
        query: str,
        top_k: int | None = None,
        category: str | None = None,
    ) -> list[dict]:
        """Busca documentos relevantes por similitud semántica."""
        top_k = top_k or RAG_TOP_K

        if self.collection.count() == 0:
            return []

        try:
            where_filter = {"category": category} if category else None

            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, self.collection.count()),
                where=where_filter,
            )

            documents = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0.0

                    documents.append({
                        "content": doc,
                        "metadata": metadata,
                        "relevance_score": round(1.0 - distance, 4),
                    })

            logger.info(f"Búsqueda RAG: '{query[:50]}...' → {len(documents)} resultados")
            return documents

        except Exception as e:
            logger.error(f"Error en búsqueda RAG: {e}")
            return []

    def get_context_for_query(self, query: str, top_k: int | None = None) -> str:
        """Obtiene contexto formateado para una consulta."""
        results = self.search(query, top_k)

        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results, 1):
            title = result["metadata"].get("title", "Sin título")
            category = result["metadata"].get("category", "general")
            score = result["relevance_score"]
            content = result["content"]

            context_parts.append(
                f"[{i}] ({category}) {title} (relevancia: {score})\n{content}"
            )

        return "\n\n---\n\n".join(context_parts)

    def load_knowledge_json(self, file_path: Path | None = None) -> int:
        """Carga conocimientos desde el archivo knowledge.json."""
        file_path = file_path or KNOWLEDGE_FILE

        if not file_path.exists():
            logger.warning(f"Archivo de conocimientos no encontrado: {file_path}")
            return 0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error leyendo knowledge.json: {e}")
            return 0

        knowledge_entries = data.get("knowledge", [])
        custom_entries = data.get("custom_entries", {}).get("entries", [])
        all_entries = knowledge_entries + custom_entries

        existing_ids = set()
        try:
            all_items = self.collection.get(include=[])
            if all_items and all_items["ids"]:
                existing_ids = {
                    item_id.rsplit("_chunk_", 1)[0] if "_chunk_" in item_id else item_id
                    for item_id in all_items["ids"]
                }
        except Exception:
            pass

        added = 0
        for entry in all_entries:
            entry_id = entry.get("id", "")
            if entry_id in existing_ids:
                continue

            doc_id = self.add_document(
                content=entry.get("content", ""),
                title=entry.get("title", ""),
                category=entry.get("category", "general"),
                tags=entry.get("tags", []),
                doc_id=entry_id,
            )
            if doc_id:
                added += 1

        logger.info(f"Cargados {added} documentos nuevos desde knowledge.json "
                     f"({len(existing_ids)} ya existían)")
        return added

    def load_uploaded_files(self, directory: Path | None = None) -> int:
        """Carga documentos .md/.txt desde el directorio de archivos subidos."""
        directory = directory or UPLOADED_KNOWLEDGE_DIR

        if not directory.exists():
            logger.warning(f"Directorio de archivos subidos no encontrado: {directory}")
            return 0

        existing_ids = set()
        try:
            all_items = self.collection.get(include=[])
            if all_items and all_items["ids"]:
                existing_ids = {
                    item_id.rsplit("_chunk_", 1)[0] if "_chunk_" in item_id else item_id
                    for item_id in all_items["ids"]
                }
        except Exception:
            pass

        added = 0
        for file_path in directory.glob("*.md"):
            doc_id = f"upload_{file_path.stem}"
            if doc_id in existing_ids:
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                if content.strip():
                    self.add_document(
                        content=content,
                        title=file_path.stem,
                        category="uploaded",
                        tags=["uploaded", file_path.name],
                        doc_id=doc_id,
                    )
                    added += 1
                    logger.info(f"Documento cargado: {file_path.name}")
            except Exception as e:
                logger.error(f"Error cargando {file_path.name}: {e}")

        logger.info(f"Cargados {added} documentos desde archivos subidos")
        return added

    def load_all_knowledge(self) -> int:
        """Carga conocimientos desde todas las fuentes."""
        total = 0
        total += self.load_knowledge_json()
        total += self.load_uploaded_files()
        return total

    def add_from_web_search(self, query: str, search_results: list[dict]) -> int:
        """Añade conocimientos desde resultados de búsqueda web."""
        added = 0
        for result in search_results:
            snippet = result.get("snippet", "")
            title = result.get("title", query)
            if snippet and len(snippet) > 30:
                doc_id = self.add_document(
                    content=f"Búsqueda web sobre '{query}': {snippet}",
                    title=f"Web: {title}",
                    category="web_search",
                    tags=["web", "auto", query.lower()],
                )
                if doc_id:
                    added += 1
        return added

    def delete_document(self, doc_id: str) -> bool:
        """Elimina un documento por su ID."""
        try:
            all_items = self.collection.get()
            ids_to_delete = [
                item_id
                for item_id in all_items["ids"]
                if item_id == doc_id or item_id.startswith(f"{doc_id}_chunk_")
            ]
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"Documento eliminado: {doc_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error eliminando documento: {e}")
            return False

    def get_stats(self) -> dict:
        """Devuelve estadísticas de la base de conocimientos."""
        try:
            count = self.collection.count()
            all_items = self.collection.get(include=["metadatas"])
            categories = set()
            if all_items and all_items["metadatas"]:
                for meta in all_items["metadatas"]:
                    if "category" in meta:
                        categories.add(meta["category"])

            return {
                "total_documents": count,
                "categories": list(categories),
                "vector_store_path": str(VECTOR_STORE_DIR),
            }
        except Exception as e:
            return {"error": str(e)}

    def _split_text(self, text: str, max_length: int = 500) -> list[str]:
        """Divide un texto largo en chunks más pequeños."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        paragraphs = text.split("\n\n")

        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                if len(para) > max_length:
                    sentences = para.replace(". ", ".\n").split("\n")
                    current_chunk = ""
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 1 > max_length:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = sentence
                        else:
                            current_chunk += " " + sentence if current_chunk else sentence
                else:
                    current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks
