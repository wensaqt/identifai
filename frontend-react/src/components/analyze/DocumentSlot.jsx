import { FileDropZone } from "../ui/FileDropZone";
import { Badge } from "../ui/Badge";
import "./DocumentSlot.css";

export function DocumentSlot({ doc, file, onFile, isMissing = false }) {
  return (
    <div className={`doc-slot ${isMissing ? "doc-slot--missing" : ""}`}>
      <div className="doc-slot__header">
        <span className="doc-slot__label">{doc.label}</span>
        {doc.required && <Badge variant={isMissing ? "error" : "neutral"}>Requis</Badge>}
      </div>
      <p className="doc-slot__hint">{doc.hint}</p>
      <FileDropZone onFile={onFile} current={file} error={isMissing} />
    </div>
  );
}
