import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useProcess } from "../../hooks/useProcess";
import { useUpdateProcess } from "../../hooks/useUpdateProcess";
import { getProcessConfiguration } from "../../config/processes";
import { PageContainer } from "../layout/PageContainer";
import { Title } from "../ui/Title";
import { Button } from "../ui/Button";
import { Spinner } from "../ui/Spinner";
import { AnalyzeResults } from "../analyze/AnalyzeResults";
import { DocumentForm } from "../analyze/DocumentForm";
import "./ProcessPage.css";

export function ProcessPage() {
  const { processId } = useParams();
  const navigate = useNavigate();
  const { process, loading: fetching, setProcess } = useProcess(processId);
  const { update, loading: updating, error: updateError } = useUpdateProcess();
  const [editing, setEditing] = useState(false);

  if (fetching) {
    return (
      <PageContainer narrow>
        <div className="process-page__loading">
          <Spinner size={32} />
        </div>
      </PageContainer>
    );
  }

  if (!process) {
    return (
      <PageContainer narrow>
        <Title level={2}>Demande introuvable</Title>
        <Button variant="ghost" onClick={() => navigate("/history")}>
          Retour
        </Button>
      </PageContainer>
    );
  }

  const config = getProcessConfiguration(process.type);
  const hasErrors = process.anomalies?.some((a) => a.severity === "error");
  const canRetry = process.status === "error" || hasErrors;

  const handleResubmit = async (filesMap) => {
    const result = await update(processId, filesMap);
    if (result) {
      setProcess(result);
      setEditing(false);
    }
  };

  return (
    <PageContainer>
      <Button variant="ghost" onClick={() => navigate("/history")}>
        ← Historique
      </Button>

      <Title
        level={2}
        subtitle={`Demande ${processId} — ${process.created_at?.slice(0, 16).replace("T", " ")}`}
      >
        {config?.icon || "📄"} {config?.title || process.type}
      </Title>

      {!editing ? (
        <>
          <AnalyzeResults process={process} />

          {canRetry && (
            <div className="process-page__actions">
              <Button onClick={() => setEditing(true)}>
                Corriger et relancer
              </Button>
            </div>
          )}
        </>
      ) : (
        <>
          <p className="process-page__hint">
            Deposez les documents corriges puis relancez l'analyse.
          </p>
          <DocumentForm
            documents={config?.documents || []}
            onSubmit={handleResubmit}
            loading={updating}
            error={updateError}
          />
          <Button variant="ghost" onClick={() => setEditing(false)}>
            Annuler
          </Button>
        </>
      )}
    </PageContainer>
  );
}
