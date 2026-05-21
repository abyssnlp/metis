"""ChromaDB-based vector search for semantic queries."""

import contextlib
from typing import Optional

import chromadb

from metis.store import METIS_DIR, Entry, Store

CHROMA_DIR = METIS_DIR / "vectorstore"


class VectorSearch:
    def __init__(self):
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._collection = self._client.get_or_create_collection(
            name="metis_entries",
            metadata={"hnsw:space": "cosine"},
        )

    def _text_for(self, entry: Entry) -> str:
        return f"{entry.title} {entry.command} {entry.description} {' '.join(entry.tags)}"

    def index_entry(self, entry: Entry):
        self._collection.upsert(
            ids=[entry.id],
            documents=[self._text_for(entry)],
            metadatas=[{"kb": entry.kb}],
        )

    def reindex_all(self, store: Store):
        entries = store.get_entries()
        if not entries:
            return
        self._collection.upsert(
            ids=[e.id for e in entries],
            documents=[self._text_for(e) for e in entries],
            metadatas=[{"kb": e.kb} for e in entries],
        )

    def search(self, query: str, kb: Optional[str] = None, n: int = 10) -> list[str]:
        """Return entry IDs ranked by semantic similarity."""
        count = self._collection.count()
        if count == 0:
            return []
        where = {"kb": kb} if kb and kb != "all" else None
        results = self._collection.query(
            query_texts=[query],
            n_results=min(n, count),
            where=where,
        )
        return results["ids"][0] if results["ids"] else []

    def delete_entry(self, entry_id: str):
        with contextlib.suppress(Exception):
            self._collection.delete(ids=[entry_id])
