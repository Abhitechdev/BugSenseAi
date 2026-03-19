"""Vector search service using ChromaDB for similar error detection."""

import asyncio
import hashlib
import time
import structlog
from typing import Optional

import chromadb

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class VectorService:
    """Manages ChromaDB collection for error similarity search."""

    COLLECTION_NAME = "error_analyses"

    def __init__(self):
        self._client: Optional[chromadb.HttpClient] = None
        self._collection = None
        self._disabled_until = 0.0

    def _within_cooldown(self) -> bool:
        return time.monotonic() < self._disabled_until

    def _trip_cooldown(self, error: Exception) -> None:
        self._disabled_until = time.monotonic() + settings.chroma_retry_cooldown_seconds
        self._client = None
        self._collection = None
        logger.warning(
            "chromadb_temporarily_disabled",
            error=str(error),
            retry_after_seconds=settings.chroma_retry_cooldown_seconds,
        )

    def _get_client(self):
        if not settings.chroma_enabled or self._within_cooldown():
            return None
        if self._client is None:
            try:
                self._client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port,
                    ssl=settings.chroma_ssl,
                )
                self._collection = self._client.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info("chromadb_connected", host=settings.chroma_host)
            except Exception as e:
                self._trip_cooldown(e)
        return self._client

    def _ensure_collection(self):
        self._get_client()
        return self._collection

    async def _run_with_timeout(self, func, *args, **kwargs):
        return await asyncio.wait_for(
            asyncio.to_thread(func, *args, **kwargs),
            timeout=settings.chroma_operation_timeout_seconds,
        )

    async def store_analysis(self, input_text: str, analysis: dict, analysis_id: str) -> None:
        """Store an error analysis embedding for future similarity search."""
        try:
            collection = self._ensure_collection()
            if collection is None:
                return

            doc_id = hashlib.md5(input_text.encode()).hexdigest()

            await self._run_with_timeout(
                collection.upsert,
                documents=[input_text],
                metadatas=[{
                    "analysis_id": analysis_id,
                    "error_type": analysis.get("error_type", "unknown"),
                    "root_cause": analysis.get("root_cause", "")[:500],
                }],
                ids=[doc_id],
            )
            logger.info("vector_stored", doc_id=doc_id)
        except Exception as e:
            self._trip_cooldown(e)
            logger.error("vector_store_failed", error=str(e))

    async def search_similar(self, input_text: str, n_results: int = 3) -> list[dict]:
        """Search for similar previously-analyzed errors."""
        try:
            collection = self._ensure_collection()
            if collection is None:
                return []

            results = await self._run_with_timeout(
                collection.query,
                query_texts=[input_text],
                n_results=n_results,
            )

            similar = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 1.0
                    if distance < 0.5:  # Only include relevant matches
                        similar.append({
                            "text_preview": doc[:200],
                            "error_type": meta.get("error_type", ""),
                            "root_cause": meta.get("root_cause", ""),
                            "similarity_score": round(1 - distance, 3),
                        })
            logger.info("vector_search_complete", results_found=len(similar))
            return similar
        except Exception as e:
            self._trip_cooldown(e)
            return []

    async def ping(self) -> bool:
        """Check whether ChromaDB is reachable."""
        collection = self._ensure_collection()
        if collection is None:
            raise RuntimeError("ChromaDB collection unavailable")
        await self._run_with_timeout(collection.count)
        return True

    async def delete_analysis(self, analysis_id: str) -> None:
        """Delete an analysis embedding from chromadb."""
        try:
            collection = self._ensure_collection()
            if collection is None:
                return

            await self._run_with_timeout(collection.delete, where={"analysis_id": analysis_id})
            logger.info("vector_deleted", analysis_id=analysis_id)
        except Exception as e:
            self._trip_cooldown(e)
            logger.error("vector_delete_failed", error=str(e))

    async def delete_analyses(self, analysis_ids: list[str]) -> None:
        """Delete multiple analysis embeddings from chromadb."""
        try:
            collection = self._ensure_collection()
            if collection is None or not analysis_ids:
                return

            await self._run_with_timeout(collection.delete, where={"analysis_id": {"$in": analysis_ids}})
            logger.info("vectors_deleted", count=len(analysis_ids))
        except Exception as e:
            self._trip_cooldown(e)
            logger.error("vectors_delete_failed", error=str(e))

    async def clear_all(self) -> None:
        """Delete all analysis embeddings from chromadb."""
        try:
            if self._client is None:
                self._get_client()
            if self._client is not None:
                try:
                    await self._run_with_timeout(self._client.delete_collection, self.COLLECTION_NAME)
                    self._collection = None
                    logger.info("vector_store_cleared")
                except chromadb.errors.InvalidCollectionException:
                    pass # Collection doesn't exist
        except Exception as e:
            self._trip_cooldown(e)
            logger.error("vector_store_clear_failed", error=str(e))



# Singleton
vector_service = VectorService()
