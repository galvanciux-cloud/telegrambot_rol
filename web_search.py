"""
web_search.py — Módulo de búsqueda en internet de NOVA
Usa DuckDuckGo Search (sin API key) y scraping para resúmenes de URLs.
"""

import logging
from typing import Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebSearch:
    """Búsqueda en internet usando DuckDuckGo y scraping web."""

    def __init__(self):
        self.ddgs = None
        self._init_ddgs()

    def _init_ddgs(self):
        """Inicializa el cliente de DuckDuckGo Search."""
        try:
            from duckduckgo_search import DDGS
            self.ddgs = DDGS()
            logger.info("DuckDuckGo Search inicializado")
        except ImportError:
            logger.error("duckduckgo_search no instalado. Ejecuta: pip install duckduckgo-search")
        except Exception as e:
            logger.error(f"Error inicializando DuckDuckGo Search: {e}")

    def search(
        self,
        query: str,
        max_results: int = 5,
        region: str = "wt-wt",
    ) -> list[dict]:
        """
        Busca en internet usando DuckDuckGo.

        Args:
            query: Consulta de búsqueda
            max_results: Número máximo de resultados
            region: Región de búsqueda (wt-wt = sin región específica)

        Returns:
            Lista de resultados con title, url, snippet
        """
        if self.ddgs is None:
            return [{"error": "DuckDuckGo Search no disponible. Verifica la instalación."}]

        try:
            results = self.ddgs.text(
                keywords=query,
                region=region,
                max_results=max_results,
            )

            formatted = []
            for r in results:
                formatted.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "source": "DuckDuckGo",
                })

            logger.info(f"Búsqueda web: '{query}' → {len(formatted)} resultados")
            return formatted

        except Exception as e:
            logger.error(f"Error en búsqueda web: {e}")
            return [{"error": f"Error al buscar: {e}"}]

    def search_and_format(self, query: str, max_results: int = 5) -> str:
        """
        Busca y formatea los resultados como texto para el usuario.

        Args:
            query: Consulta de búsqueda
            max_results: Número máximo de resultados

        Returns:
            Texto formateado con los resultados
        """
        results = self.search(query, max_results)

        if not results:
            return "No se encontraron resultados para tu búsqueda."

        if "error" in results[0]:
            return f"❌ {results[0]['error']}"

        output_parts = [f"🔍 Resultados para: *{query}*\n"]

        for i, result in enumerate(results, 1):
            title = result.get("title", "Sin título")
            url = result.get("url", "")
            snippet = result.get("snippet", "")

            output_parts.append(f"{i}. **{title}**")
            if snippet:
                output_parts.append(f"   _{snippet}_")
            if url:
                output_parts.append(f"   🔗 {url}")
            output_parts.append("")

        return "\n".join(output_parts)

    def search_for_context(self, query: str, max_results: int = 3) -> str:
        """
        Busca y devuelve resultados formateados como contexto para el modelo.

        Args:
            query: Consulta de búsqueda
            max_results: Número de resultados

        Returns:
            Texto formateado para inyectar como contexto en el prompt
        """
        results = self.search(query, max_results)

        if not results or "error" in results[0]:
            return ""

        context_parts = []
        for result in results:
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            url = result.get("url", "")

            if snippet:
                context_parts.append(f"- {title}: {snippet} (Fuente: {url})")

        return "\n".join(context_parts) if context_parts else ""

    async def fetch_url_content(self, url: str, max_length: int = 5000) -> dict:
        """
        Obtiene y extrae el contenido de una URL.

        Args:
            url: URL a extraer
            max_length: Longitud máxima del contenido extraído

        Returns:
            Diccionario con title, content, url
        """
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Eliminar elementos innecesarios
                for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    element.decompose()

                title = soup.title.string.strip() if soup.title and soup.title.string else url

                # Intentar obtener el contenido principal
                content = ""

                # Intentar con article o main
                main_content = soup.find("article") or soup.find("main") or soup.find("div", class_="content")
                if main_content:
                    content = main_content.get_text(separator="\n", strip=True)
                else:
                    content = soup.get_text(separator="\n", strip=True)

                # Limpiar líneas vacías excesivas
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                content = "\n".join(lines)

                # Truncar si es necesario
                if len(content) > max_length:
                    content = content[:max_length] + "..."

                return {
                    "title": title,
                    "content": content,
                    "url": url,
                    "success": True,
                }

        except httpx.TimeoutException:
            return {
                "title": "",
                "content": "La URL tardó demasiado en responder.",
                "url": url,
                "success": False,
            }
        except httpx.HTTPStatusError as e:
            return {
                "title": "",
                "content": f"Error HTTP {e.response.status_code} al acceder a la URL.",
                "url": url,
                "success": False,
            }
        except Exception as e:
            return {
                "title": "",
                "content": f"Error al obtener la URL: {e}",
                "url": url,
                "success": False,
            }

    def fetch_url_sync(self, url: str, max_length: int = 5000) -> dict:
        """
        Versión síncrona de fetch_url_content para usar en contextos sin async.
        """
        try:
            with httpx.Client(
                timeout=15.0,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            ) as client:
                response = client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    element.decompose()

                title = soup.title.string.strip() if soup.title and soup.title.string else url

                main_content = soup.find("article") or soup.find("main") or soup.find("div", class_="content")
                if main_content:
                    content = main_content.get_text(separator="\n", strip=True)
                else:
                    content = soup.get_text(separator="\n", strip=True)

                lines = [line.strip() for line in content.split("\n") if line.strip()]
                content = "\n".join(lines)

                if len(content) > max_length:
                    content = content[:max_length] + "..."

                return {
                    "title": title,
                    "content": content,
                    "url": url,
                    "success": True,
                }

        except httpx.TimeoutException:
            return {"title": "", "content": "La URL tardó demasiado en responder.", "url": url, "success": False}
        except httpx.HTTPStatusError as e:
            return {"title": "", "content": f"Error HTTP {e.response.status_code}.", "url": url, "success": False}
        except Exception as e:
            return {"title": "", "content": f"Error: {e}", "url": url, "success": False}
