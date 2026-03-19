import { useProcesses } from "../../hooks/useProcesses";
import { PageContainer } from "../layout/PageContainer";
import { Title } from "../ui/Title";
import { Spinner } from "../ui/Spinner";
import { ProcessCard } from "./ProcessCard";
import "./HistoryPage.css";

export function HistoryPage() {
  const { processes, loading } = useProcesses();

  return (
    <PageContainer>
      <Title level={2}>Historique des demandes</Title>

      {loading ? (
        <div className="history__loading"><Spinner size={32} /></div>
      ) : processes.length === 0 ? (
        <p className="history__empty">Aucune demande enregistree.</p>
      ) : (
        <div className="history__list">
          {processes.map((p) => (
            <ProcessCard key={p.id} process={p} />
          ))}
        </div>
      )}
    </PageContainer>
  );
}
