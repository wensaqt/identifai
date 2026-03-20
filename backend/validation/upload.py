from __future__ import annotations

import json

from consts.anomalies import AnomalyType, Severity
from fastapi import UploadFile
from models.process import ProcessAnomaly

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_SIZE = 20 * 1024 * 1024  # 20 MB


class UploadValidator:

    def validate_file(self, file: UploadFile, file_bytes: bytes) -> str | None:
        """Return an error message if the file is invalid, None otherwise."""
        if file.content_type not in ALLOWED_TYPES:
            return f"Unsupported file type: {file.content_type}"
        if len(file_bytes) > MAX_SIZE:
            return "File exceeds 20 MB limit"
        return None

    def build_expected_map(
        self, files: list[UploadFile], doc_types_json: str | None
    ) -> dict[str, str]:
        """Build {filename: expected_doc_type} from the parallel doc_types JSON array."""
        if not doc_types_json:
            return {}
        try:
            types_list = json.loads(doc_types_json)
        except (json.JSONDecodeError, TypeError):
            return {}
        return {
            files[i].filename: types_list[i]
            for i in range(min(len(files), len(types_list)))
        }

    def detect_type_mismatches(
        self, classified: list[tuple], expected_map: dict[str, str]
    ) -> list[ProcessAnomaly]:
        """Return DOC_TYPE_MISMATCH anomalies where declared type != classified type."""
        anomalies = []
        for result, _ in classified:
            filename = result.get("filename", "")
            declared = expected_map.get(filename)
            detected = result.get("doc_type")
            if declared and detected and declared != detected:
                anomalies.append(
                    ProcessAnomaly(
                        type=AnomalyType.DOC_TYPE_MISMATCH,
                        severity=Severity.WARNING,
                        message=f"Type déclaré '{declared}' ≠ type détecté '{detected}'",
                        document_refs=[filename],
                    )
                )
        return anomalies
