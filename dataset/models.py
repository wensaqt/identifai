from __future__ import annotations

from dataclasses import dataclass, field

from .consts import AnomalyType, DocType


@dataclass
class Alteration:
    """Declares an anomaly to inject on a specific document type."""
    doc_type: DocType
    anomaly: AnomalyType


@dataclass
class ScenarioDefinition:
    """Declarative description: process type + alterations (empty = happy path)."""
    name: str
    description: str
    process_type: str
    alterations: list[Alteration]
    omitted_docs: list[DocType]


@dataclass
class AnomalyDetail:
    """Structured ground-truth for one expected anomaly."""
    type: AnomalyType
    severity: str
    message: str
    document_refs: list[str]
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        result = {
            "type": str(self.type),
            "severity": self.severity,
            "message": self.message,
            "document_refs": self.document_refs,
        }
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class DocumentRecord:
    """One generated document: identity + flat field dict."""
    doc_id: str
    doc_type: DocType
    filename: str
    fields: dict

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "doc_type": str(self.doc_type),
            "filename": self.filename,
            "fields": self.fields,
        }


@dataclass
class ProcessRecord:
    """Complete ground-truth produced by ScenarioBuilder.build()."""
    id: str
    type: str
    scenario_name: str
    status: str
    noise_level: str
    documents: list[DocumentRecord]
    anomalies_expected: list[AnomalyDetail]
    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "scenario_name": self.scenario_name,
            "status": self.status,
            "noise_level": self.noise_level,
            "documents": [d.to_dict() for d in self.documents],
            "anomalies_expected": [a.to_dict() for a in self.anomalies_expected],
            "created_at": self.created_at,
        }
