# tools/vector_store.py
# ChromaDB wrapper for semantic memory storage and retrieval

import json
from pathlib import Path
from datetime import datetime
from loguru import logger
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from config import (
    CHROMA_DIR,
    EMBEDDING_MODEL,
    COLLECTION_RESUMES,
    COLLECTION_SKILLS,
    COLLECTION_MEMORY
)


class VectorStore:
    """
    ChromaDB wrapper that handles:
    - Creating/loading collections
    - Adding documents with metadata
    - Semantic similarity search
    - Deleting and updating records
    """

    def __init__(self):
        logger.info("Initializing ChromaDB vector store...")

        # Ensure directory exists
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)

        # Persistent ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Embedding model — same one used throughout the project
        self.encoder = SentenceTransformer(EMBEDDING_MODEL)

        # Get or create all collections
        self.collections = {
            "resumes": self._get_or_create(COLLECTION_RESUMES),
            "skills":  self._get_or_create(COLLECTION_SKILLS),
            "memory":  self._get_or_create(COLLECTION_MEMORY)
        }

        logger.info("VectorStore ready. Collections: " +
                    str(list(self.collections.keys())))

    def _get_or_create(self, name: str):
        """Get existing collection or create a new one."""
        try:
            col = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}   # cosine similarity
            )
            logger.debug(f"Collection '{name}' ready ({col.count()} docs)")
            return col
        except Exception as e:
            logger.error(f"Failed to get/create collection '{name}': {e}")
            raise

    # ── Add Documents ─────────────────────────────────────────────────────────

    def add_document(
        self,
        collection_name: str,
        doc_id:          str,
        text:            str,
        metadata:        dict = None
    ) -> bool:
        """
        Add a single document to a collection.

        Args:
            collection_name : 'resumes', 'skills', or 'memory'
            doc_id          : Unique ID for this document
            text            : The text content to embed and store
            metadata        : Optional dict of metadata fields

        Returns:
            True on success
        """
        col = self.collections.get(collection_name)
        if not col:
            logger.error(f"Unknown collection: {collection_name}")
            return False

        try:
            embedding = self.encoder.encode(text).tolist()
            meta      = metadata or {}
            meta["stored_at"] = datetime.now().isoformat()
            meta["text"]      = text[:500]   # Store first 500 chars in metadata

            # Upsert — update if exists, insert if new
            col.upsert(
                ids        = [doc_id],
                embeddings = [embedding],
                documents  = [text],
                metadatas  = [meta]
            )
            logger.debug(f"Upserted doc '{doc_id}' into '{collection_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to add document to '{collection_name}': {e}")
            return False

    def add_documents_batch(
        self,
        collection_name: str,
        docs:            list[dict]
    ) -> int:
        """
        Add multiple documents at once (more efficient).

        Args:
            collection_name : Target collection
            docs            : List of dicts with keys: id, text, metadata

        Returns:
            Number of documents successfully added
        """
        col = self.collections.get(collection_name)
        if not col:
            return 0

        ids        = []
        embeddings = []
        documents  = []
        metadatas  = []

        for doc in docs:
            try:
                emb  = self.encoder.encode(doc["text"]).tolist()
                meta = doc.get("metadata", {})
                meta["stored_at"] = datetime.now().isoformat()
                meta["text"]      = doc["text"][:500]

                ids.append(doc["id"])
                embeddings.append(emb)
                documents.append(doc["text"])
                metadatas.append(meta)
            except Exception as e:
                logger.warning(f"Skipping doc '{doc.get('id')}': {e}")

        if ids:
            col.upsert(
                ids        = ids,
                embeddings = embeddings,
                documents  = documents,
                metadatas  = metadatas
            )
            logger.info(
                f"Batch upserted {len(ids)} docs into '{collection_name}'"
            )

        return len(ids)

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(
        self,
        collection_name: str,
        query_text:      str,
        n_results:       int  = 5,
        where:           dict = None
    ) -> list[dict]:
        """
        Semantic similarity search.

        Args:
            collection_name : Target collection
            query_text      : Natural language query
            n_results       : Max results to return
            where           : Optional metadata filter
                              e.g. {"student_id": "arjun_001"}

        Returns:
            List of result dicts with keys:
            id, text, metadata, distance (lower = more similar)
        """
        col = self.collections.get(collection_name)
        if not col:
            return []

        try:
            query_emb = self.encoder.encode(query_text).tolist()

            # Clamp n_results to available docs
            count = col.count()
            if count == 0:
                return []
            n_results = min(n_results, count)

            kwargs = {
                "query_embeddings": [query_emb],
                "n_results":        n_results,
                "include":          ["documents", "metadatas", "distances"]
            }
            if where:
                kwargs["where"] = where

            results = col.query(**kwargs)

            # Unpack ChromaDB response format
            output = []
            for i in range(len(results["ids"][0])):
                output.append({
                    "id":       results["ids"][0][i],
                    "text":     results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": round(results["distances"][0][i], 4)
                })

            return output

        except Exception as e:
            logger.error(f"Query failed on '{collection_name}': {e}")
            return []

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_document(self, collection_name: str, doc_id: str) -> bool:
        """Delete a document by ID."""
        col = self.collections.get(collection_name)
        if not col:
            return False
        try:
            col.delete(ids=[doc_id])
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    def delete_student_memories(self, student_id: str) -> int:
        """
        Delete all memories for a specific student.
        Useful for resetting a student's profile.

        Returns:
            Number of documents deleted
        """
        col     = self.collections["memory"]
        results = col.get(where={"student_id": student_id})
        ids     = results.get("ids", [])

        if ids:
            col.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} memories for student {student_id}")

        return len(ids)

    # ── Utilities ─────────────────────────────────────────────────────────────

    def get_collection_stats(self) -> dict:
        """Return document count per collection."""
        return {
            name: col.count()
            for name, col in self.collections.items()
        }

    def collection_exists(self, name: str) -> bool:
        return name in self.collections