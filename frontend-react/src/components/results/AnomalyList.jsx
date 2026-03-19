import { AnomalyItem } from "./AnomalyItem";
import "./AnomalyList.css";

export function AnomalyList({ anomalies }) {
  if (anomalies.length === 0) {
    return <p className="anomaly-list__empty">Aucune anomalie detectee.</p>;
  }

  const errors = anomalies.filter((a) => a.severity === "error");
  const warnings = anomalies.filter((a) => a.severity === "warning");

  return (
    <div className="anomaly-list">
      {[...errors, ...warnings].map((a, i) => (
        <AnomalyItem key={i} anomaly={a} />
      ))}
    </div>
  );
}
