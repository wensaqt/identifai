from __future__ import annotations

from consts.anomalies import AnomalyType, Severity
from models.process import ProcessAnomaly
from models.process_definition import ProcessDefinition


class CompletenessValidator:

    def find_missing(self, provided_types: set[str], definition: ProcessDefinition) -> list[str]:
        return sorted(definition.required_doc_types - provided_types)

    def check_missing_as_anomalies(
        self, documents: list[dict], definition: ProcessDefinition
    ) -> list[ProcessAnomaly]:
        provided = {doc.get("doc_type") for doc in documents}
        return [
            ProcessAnomaly(
                type=AnomalyType.MISSING_DOCUMENT,
                severity=Severity.ERROR,
                message=f"Document manquant : {dt}",
                document_refs=[],
            )
            for dt in self.find_missing(provided, definition)
        ]
