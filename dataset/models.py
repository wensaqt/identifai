from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .consts import AnomalyType, DocType


@dataclass
class ScenarioDocSpec:
    """Declares one document slot in a scenario."""
    doc_type: DocType
    min_count: int = 1
    max_count: Optional[int] = None
    anomaly: Optional[AnomalyType] = None  # anomaly carried by this document


@dataclass
class ScenarioDefinition:
    """Declarative description of a scenario: types, quantities, anomalies."""
    name: str
    description: str
    doc_specs: list[ScenarioDocSpec]
    anomaly_types: list[AnomalyType]
    risk_level: str  # "low" | "medium" | "high"


@dataclass
class AnomalyDetail:
    """Structured ground-truth for one expected anomaly."""
    type: AnomalyType
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"type": str(self.type), "details": self.details}


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
class ScenarioMetadata:
    """Complete ground-truth produced by ScenarioBuilder.build()."""
    scenario_name: str
    description: str
    risk_level: str
    noise_level: str
    generated_documents: list[DocumentRecord]
    document_types: list[str]
    anomalies_expected: list[AnomalyDetail]
    anomalies_detected: list[dict]
    financial_summary: dict
    relations: dict  # invoice_to_payment, invoice_to_declaration, …

    def to_dict(self) -> dict:
        return {
            "scenario_name": self.scenario_name,
            "description": self.description,
            "risk_level": self.risk_level,
            "noise_level": self.noise_level,
            "generated_documents": [d.to_dict() for d in self.generated_documents],
            "document_types": self.document_types,
            "anomalies_expected": [a.to_dict() for a in self.anomalies_expected],
            "anomalies_detected": self.anomalies_detected,
            "financial_summary": self.financial_summary,
            "relations": self.relations,
        }
