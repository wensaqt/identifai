import { DocumentItem } from "./DocumentItem";
import "./DocumentList.css";

export function DocumentList({ documents, anomalies }) {
  const issueFiles = new Set(anomalies.flatMap((a) => a.document_refs || []));

  return (
    <div className="doc-list">
      {documents.map((doc, i) => (
        <DocumentItem key={i} document={doc} hasIssue={issueFiles.has(doc.filename)} />
      ))}
    </div>
  );
}
