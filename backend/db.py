from __future__ import annotations

import logging
import os

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from consts.process import ProcessStatus
from process import Process, ProcessAnomaly, ProcessDocument

logger = logging.getLogger(__name__)

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "identifai")


def get_client() -> MongoClient:
    return MongoClient(MONGO_URL)


def get_database(client: MongoClient | None = None) -> Database:
    c = client or get_client()
    return c[MONGO_DB]


class ProcessRepository:
    """CRUD operations for Process documents in MongoDB."""

    def __init__(self, database: Database | None = None) -> None:
        db = database or get_database()
        self._col: Collection = db["processes"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._col.create_index("status")
        self._col.create_index("created_at")

    # ── Write ────────────────────────────────────────────────────────────

    def insert(self, process: Process) -> None:
        self._col.insert_one(process.to_dict())
        logger.info("[DB] inserted process %s", process.id)

    def update(self, process: Process) -> None:
        self._col.replace_one({"id": process.id}, process.to_dict())
        logger.info("[DB] updated process %s", process.id)

    def soft_delete(self, process_id: str, deleted_at: str) -> bool:
        result = self._col.update_one(
            {"id": process_id, "deleted_at": None},
            {"$set": {"status": ProcessStatus.CANCELLED, "deleted_at": deleted_at}},
        )
        if result.modified_count:
            logger.info("[DB] soft-deleted process %s", process_id)
        return result.modified_count > 0

    # ── Read ─────────────────────────────────────────────────────────────

    def find_by_id(self, process_id: str) -> Process | None:
        doc = self._col.find_one({"id": process_id})
        if not doc:
            return None
        return _doc_to_process(doc)

    def find_active(self) -> list[Process]:
        docs = self._col.find({"deleted_at": None}).sort("created_at", -1)
        return [_doc_to_process(d) for d in docs]


# ── Deserialisation ──────────────────────────────────────────────────────────

def _doc_to_process(doc: dict) -> Process:
    return Process(
        id=doc["id"],
        type=doc["type"],
        status=doc["status"],
        documents=[
            ProcessDocument(
                doc_type=d["doc_type"],
                filename=d["filename"],
                fields=d["fields"],
            )
            for d in doc.get("documents", [])
        ],
        anomalies=[
            ProcessAnomaly(
                type=a["type"],
                severity=a["severity"],
                message=a["message"],
                document_refs=a.get("document_refs", []),
                field=a.get("field"),
            )
            for a in doc.get("anomalies", [])
        ],
        created_at=doc["created_at"],
        deleted_at=doc.get("deleted_at"),
    )
