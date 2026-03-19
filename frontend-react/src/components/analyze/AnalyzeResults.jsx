import { Alert } from "../ui/Alert";
import { Button } from "../ui/Button";
import { AnomalyList } from "../results/AnomalyList";
import { DocumentList } from "../results/DocumentList";
import "./AnalyzeResults.css";

export function AnalyzeResults({ process, onReset = null }) {
  const { status, anomalies = [], documents = [] } = process;
  const errors = anomalies.filter((a) => a.severity === "error");
  const warnings = anomalies.filter((a) => a.severity === "warning");

  return (
    <div className="results">
      {status === "error" && (
        <Alert variant="error">
          {errors.length} anomalie(s) bloquante(s) — Corrigez les documents concernes.
        </Alert>
      )}
      {status === "valid" && warnings.length > 0 && (
        <Alert variant="warning">
          {warnings.length} point(s) a verifier.
        </Alert>
      )}
      {status === "valid" && warnings.length === 0 && (
        <Alert variant="success">Dossier conforme — aucune anomalie detectee.</Alert>
      )}

      <div className="results__columns">
        <div className="results__col">
          <h3 className="results__heading">Controles</h3>
          <AnomalyList anomalies={anomalies} />
        </div>
        <div className="results__col">
          <h3 className="results__heading">Documents analyses</h3>
          <DocumentList documents={documents} anomalies={anomalies} />
        </div>
      </div>

      {onReset && <Button variant="ghost" onClick={onReset} fullWidth>Nouvelle analyse</Button>}
    </div>
  );
}
