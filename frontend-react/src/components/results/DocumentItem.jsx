import { useState } from "react";
import { Card } from "../ui/Card";
import { DOC_TYPE_LABELS, FIELD_LABELS } from "../../config/labels";
import "./DocumentItem.css";

export function DocumentItem({ document, hasIssue }) {
  const [open, setOpen] = useState(hasIssue);
  const { doc_type, filename, fields = {} } = document;
  const typeLabel = DOC_TYPE_LABELS[doc_type] || doc_type;
  const fieldEntries = Object.entries(fields);

  return (
    <Card variant={hasIssue ? "error" : "success"} className="doc-item">
      <div className="doc-item__header" onClick={() => setOpen((o) => !o)}>
        <span className="doc-item__icon">{hasIssue ? "●" : "✓"}</span>
        <span className="doc-item__filename">{filename}</span>
        <span className="doc-item__type">{typeLabel}</span>
        <span className="doc-item__chevron">{open ? "▾" : "▸"}</span>
      </div>

      {open && (
        <div className="doc-item__fields">
          {fieldEntries.length > 0 ? (
            <table className="doc-item__table">
              <tbody>
                {fieldEntries.map(([k, v]) => (
                  <tr key={k}>
                    <td className="doc-item__field-name">{FIELD_LABELS[k] || k}</td>
                    <td className="doc-item__field-value">{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="doc-item__empty">Aucun champ extrait.</p>
          )}
        </div>
      )}
    </Card>
  );
}
