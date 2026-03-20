from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProcessAnomaly:
    type: str
    severity: str
    message: str
    document_refs: list[str]
    field: str | None = None

    def to_dict(self) -> dict:
        result = {
            "type": self.type,
            "severity": self.severity,
            "message": self.message,
            "document_refs": self.document_refs,
        }
        if self.field is not None:
            result["field"] = self.field
        return result


@dataclass
class ProcessDocument:
    doc_type: str
    filename: str
    fields: dict

    def to_dict(self) -> dict:
        return {
            "doc_type": self.doc_type,
            "filename": self.filename,
            "fields": self.fields,
        }


@dataclass
class Process:
    id: str
    type: str
    status: str
    documents: list[ProcessDocument]
    anomalies: list[ProcessAnomaly]
    created_at: str
    deleted_at: str | None = None

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "created_at": self.created_at,
            "documents": [d.to_dict() for d in self.documents],
            "anomalies": [a.to_dict() for a in self.anomalies],
        }
        if self.deleted_at is not None:
            result["deleted_at"] = self.deleted_at
        return result
