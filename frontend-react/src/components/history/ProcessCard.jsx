import { useNavigate } from "react-router-dom";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { DOC_TYPE_LABELS, STATUS_CONFIG, ANOMALY_LABELS } from "../../config/labels";
import "./ProcessCard.css";

export function ProcessCard({ process }) {
  const navigate = useNavigate();
  const { id, status, documents = [], anomalies = [], created_at } = process;
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const created = created_at?.slice(0, 16).replace("T", " ") || "";

  return (
    <Card onClick={() => navigate(`/process/${id}`)}>
      <div className="process-card__header">
        <Badge variant={config.variant}>{config.icon} {config.label}</Badge>
        <span className="process-card__id">{id}</span>
        <span className="process-card__date">{created}</span>
      </div>

      <div className="process-card__stats">
        <span>{documents.length} document(s)</span>
        <span>{anomalies.length} anomalie(s)</span>
      </div>

      {documents.length > 0 && (
        <div className="process-card__docs">
          {documents.map((d, i) => (
            <span key={i} className="process-card__doc-tag">
              {DOC_TYPE_LABELS[d.doc_type] || d.doc_type}
            </span>
          ))}
        </div>
      )}

      {anomalies.length > 0 && (
        <div className="process-card__anomalies">
          {anomalies.map((a, i) => {
            const label = ANOMALY_LABELS[a.type]?.title || a.type;
            return (
              <Badge key={i} variant={a.severity === "error" ? "error" : "warning"}>
                {label}
              </Badge>
            );
          })}
        </div>
      )}
    </Card>
  );
}
