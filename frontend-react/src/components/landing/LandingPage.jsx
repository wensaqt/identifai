import { useNavigate } from "react-router-dom";
import { PROCESSES } from "../../config/processes";
import { PageContainer } from "../layout/PageContainer";
import { DemarcheCard } from "./DemarcheCard";
import "./LandingPage.css";

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <PageContainer>
      <div className="demarche-grid">
        {PROCESSES.map((d) => (
          <DemarcheCard
            key={d.id}
            demarche={d}
            onClick={() => navigate(`/analyze/${d.id}`)}
          />
        ))}
      </div>
    </PageContainer>
  );
}
