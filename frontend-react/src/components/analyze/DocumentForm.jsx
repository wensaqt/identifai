import { useCallback, useState } from "react";
import { DocumentSlot } from "./DocumentSlot";
import { Button } from "../ui/Button";
import { Alert } from "../ui/Alert";
import { Spinner } from "../ui/Spinner";
import { DOC_TYPE_LABELS } from "../../config/labels";
import "./DocumentForm.css";

export function DocumentForm({ documents, onSubmit, loading, error }) {
  const [files, setFiles] = useState({});

  const setFile = useCallback((docType, file) => {
    setFiles((prev) => ({ ...prev, [docType]: file }));
  }, []);

  const missingSlots = error?.type === "missing_documents" ? new Set(error.missing) : new Set();

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(files);
  };

  const filledCount = Object.values(files).filter(Boolean).length;
  const requiredCount = documents.filter((d) => d.required).length;

  return (
    <form className="doc-form" onSubmit={handleSubmit}>
      {error && (
        <Alert variant={error.type === "missing_documents" ? "warning" : "error"}>
          {error.type === "missing_documents"
            ? <>Documents non reconnus : <strong>{error.missing.map((t) => DOC_TYPE_LABELS[t] || t).join(", ")}</strong></>
            : error.message}
        </Alert>
      )}

      <div className="doc-form__grid">
        {documents.map((doc) => (
          <DocumentSlot
            key={doc.id}
            doc={doc}
            file={files[doc.id]}
            onFile={(f) => setFile(doc.id, f)}
            isMissing={missingSlots.has(doc.id)}
          />
        ))}
      </div>

      <div className="doc-form__footer">
        <span className="doc-form__count">{filledCount} / {requiredCount} documents</span>
        <Button type="submit" disabled={loading || filledCount === 0}>
          {loading ? <><Spinner size={16} /> Analyse en cours...</> : "Lancer l'analyse"}
        </Button>
      </div>
    </form>
  );
}
