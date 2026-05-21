"""Data models and JSON-based storage for knowledge bases and entries."""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

METIS_DIR = Path.home() / ".metis"
DB_FILE = METIS_DIR / "metis.json"


@dataclass
class Entry:
    id: str
    title: str
    command: str
    description: str = ""
    tags: list = field(default_factory=list)
    kb: str = "default"
    created_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:8]
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self):
        METIS_DIR.mkdir(parents=True, exist_ok=True)
        self._path = DB_FILE
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            return json.loads(self._path.read_text())
        return {"knowledge_bases": ["default"], "entries": []}

    def _save(self):
        self._path.write_text(json.dumps(self._data, indent=2))

    # -- knowledge bases --

    def list_kbs(self) -> list[str]:
        return sorted(self._data["knowledge_bases"])

    def create_kb(self, name: str) -> bool:
        name = name.lower().strip()
        if name in self._data["knowledge_bases"]:
            return False
        self._data["knowledge_bases"].append(name)
        self._save()
        return True

    # -- entries --

    def add_entry(self, entry: Entry):
        if entry.kb not in self._data["knowledge_bases"]:
            self._data["knowledge_bases"].append(entry.kb)
        self._data["entries"].append(asdict(entry))
        self._save()

    def get_entries(self, kb: Optional[str] = None) -> list[Entry]:
        entries = self._data["entries"]
        if kb and kb != "all":
            entries = [e for e in entries if e["kb"] == kb]
        return [Entry(**e) for e in entries]

    def delete_entry(self, entry_id: str) -> bool:
        before = len(self._data["entries"])
        self._data["entries"] = [e for e in self._data["entries"] if e["id"] != entry_id]
        if len(self._data["entries"]) < before:
            self._save()
            return True
        return False

    def keyword_search(self, query: str, kb: Optional[str] = None) -> list[Entry]:
        entries = self.get_entries(kb)
        terms = query.lower().split()
        results = []
        for e in entries:
            text = f"{e.title} {e.command} {e.description} {' '.join(e.tags)}".lower()
            if all(t in text for t in terms):
                results.append(e)
        return results
