import { useParams, useNavigate } from "react-router-dom";
import { getProcessConfiguration } from "../../config/processes";
import { useAnalyzeDocuments } from "../../hooks/useAnalyzeDocuments";
import { PageContainer } from "../layout/PageContainer";
import { Title } from "../ui/Title";
import { Button } from "../ui/Button";
import { DocumentForm } from "./DocumentForm";
import { AnalyzeResults } from "./AnalyzeResults";

export function AnalyzePage() {
  const { demarcheId } = useParams();
  const navigate = useNavigate();
  const demarche = getProcessConfiguration(demarcheId);
  const { analyze, data, error, loading, reset } = useAnalyzeDocuments();

  if (!demarche || !demarche.enabled) {
    return (
      <PageContainer narrow>
        <Title level={2}>Demarche introuvable</Title>
        <Button variant="ghost" onClick={() => navigate("/")}>
          Retour
        </Button>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <Button variant="ghost" onClick={() => navigate("/")}>
        ← Retour
      </Button>

      <Title level={2} subtitle={demarche.description}>
        {demarche.icon} {demarche.title}
      </Title>

      {data ? (
        <AnalyzeResults process={data} onReset={reset} />
      ) : (
        <DocumentForm
          documents={demarche.documents}
          onSubmit={analyze}
          loading={loading}
          error={error}
        />
      )}
    </PageContainer>
  );
}
