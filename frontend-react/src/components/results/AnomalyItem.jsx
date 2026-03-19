import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { ANOMALY_LABELS } from "../../config/labels";
import "./AnomalyItem.css";

export function AnomalyItem({ anomaly }) {
  const config = ANOMALY_LABELS[anomaly.type] || { title: anomaly.type, detail: "" };
  const isError = anomaly.severity === "error";

  return (
    <Card variant={isError ? "error" : "warning"}>
      <div className="anomaly-item__header">
        <Badge variant={isError ? "error" : "warning"}>{isError ? "Bloquant" : "A verifier"}</Badge>
        <span className="anomaly-item__title">{config.title}</span>
      </div>
      <p className="anomaly-item__detail">{anomaly.message || config.detail}</p>
      {anomaly.document_refs?.length > 0 && (
        <p className="anomaly-item__refs">Concerne : {anomaly.document_refs.join(", ")}</p>
      )}
    </Card>
  );
}
