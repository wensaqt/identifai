from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from consts.anomalies import AnomalyType, Severity
from consts.process import ProcessStatus
from consts.process_definitions import ProcessDefinition
from db import ProcessRepository
from process import Process, ProcessAnomaly, ProcessDocument
from validator import DocumentValidator
from verifier import DocumentVerifier

logger = logging.getLogger(__name__)


class ProcessRunner:
    """Orchestrates the full pipeline and collects all anomalies at Process level."""

    def __init__(self, repo: ProcessRepository | None = None) -> None:
        self._validator = DocumentValidator()
        self._verifier = DocumentVerifier()
        self._repo = repo

    # ── Public API ───────────────────────────────────────────────────────

    def run(self, documents: list[dict], definition: ProcessDefinition) -> Process:
        """Run the full pipeline: validate each doc, check missing docs, cross-doc verify."""
        process = self._create_pending(definition)
        return self._execute(process, documents, definition)

    def rerun(self, process: Process, documents: list[dict], definition: ProcessDefinition) -> Process:
        """Re-run the pipeline on an existing process (update scenario)."""
        process.status = ProcessStatus.PENDING
        if self._repo:
            self._repo.update(process)
        return self._execute(process, documents, definition)

    def run_verify_only(self, documents: list[dict], definition: ProcessDefinition) -> Process:
        """Run only validation + verification (no OCR). For pre-processed documents."""
        process = self._create_pending(definition)
        return self._execute(process, documents, definition)

    # ── Private ──────────────────────────────────────────────────────────

    def _create_pending(self, definition: ProcessDefinition) -> Process:
        process = Process(
            id=uuid.uuid4().hex[:8],
            type=str(definition.process_type),
            status=ProcessStatus.PENDING,
            documents=[],
            anomalies=[],
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        if self._repo:
            self._repo.insert(process)
        return process

    def _execute(
        self, process: Process, documents: list[dict], definition: ProcessDefinition,
    ) -> Process:
        process.documents = self._build_process_documents(documents)

        anomalies: list[ProcessAnomaly] = []
        anomalies.extend(self._collect_document_anomalies(documents))
        anomalies.extend(self._check_missing_documents(documents, definition))
        anomalies.extend(self._collect_cross_doc_anomalies(documents))

        process.anomalies = anomalies
        process.status = self._compute_status(anomalies)

        if self._repo:
            self._repo.update(process)

        logger.info(
            "[PROCESS] id=%s type=%s status=%s docs=%d anomalies=%d",
            process.id, process.type, process.status,
            len(process.documents), len(process.anomalies),
        )
        return process

    def _build_process_documents(self, documents: list[dict]) -> list[ProcessDocument]:
        return [
            ProcessDocument(
                doc_type=doc.get("doc_type", "unknown"),
                filename=doc.get("filename", "unknown"),
                fields=doc.get("fields", {}),
            )
            for doc in documents
        ]

    def _collect_document_anomalies(self, documents: list[dict]) -> list[ProcessAnomaly]:
        """Run validator on each document and convert issues to ProcessAnomaly."""
        anomalies: list[ProcessAnomaly] = []
        for doc in documents:
            doc_type = doc.get("doc_type")
            fields = doc.get("fields", {})
            filename = doc.get("filename", "unknown")
            result = self._validator.validate(doc_type, fields)

            for issue in result["completeness"]:
                anomalies.append(ProcessAnomaly(
                    type=AnomalyType.MISSING_FIELD,
                    severity=Severity.WARNING,
                    message=issue["message"],
                    document_refs=[filename],
                    field=issue.get("field"),
                ))
            for issue in result["format"]:
                anomalies.append(ProcessAnomaly(
                    type=AnomalyType.INVALID_FORMAT,
                    severity=Severity.WARNING,
                    message=issue["message"],
                    document_refs=[filename],
                    field=issue.get("field"),
                ))
        return anomalies

    def _check_missing_documents(
        self, documents: list[dict], definition: ProcessDefinition,
    ) -> list[ProcessAnomaly]:
        """Check which required doc types are missing."""
        provided = {doc.get("doc_type") for doc in documents}
        anomalies: list[ProcessAnomaly] = []
        for required_type in definition.required_doc_types:
            if required_type not in provided:
                anomalies.append(ProcessAnomaly(
                    type=AnomalyType.MISSING_DOCUMENT,
                    severity=Severity.ERROR,
                    message=f"Document manquant : {required_type}",
                    document_refs=[],
                ))
        return anomalies

    def _collect_cross_doc_anomalies(self, documents: list[dict]) -> list[ProcessAnomaly]:
        """Run verifier and convert issues to ProcessAnomaly."""
        issues = self._verifier.verify(documents)
        return [
            ProcessAnomaly(
                type=issue["type"],
                severity=issue["severity"],
                message=issue["message"],
                document_refs=issue.get("files", []),
            )
            for issue in issues
        ]

    def _compute_status(self, anomalies: list[ProcessAnomaly]) -> str:
        has_error = any(a.severity == Severity.ERROR for a in anomalies)
        return ProcessStatus.ERROR if has_error else ProcessStatus.VALID
