import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import "./DemarcheCard.css";

export function DemarcheCard({ demarche, onClick }) {
  return (
    <Card variant={demarche.enabled ? "default" : "disabled"} onClick={demarche.enabled ? onClick : undefined}>
      <div className="demarche-card__icon">{demarche.icon}</div>
      <h3 className="demarche-card__title">{demarche.title}</h3>
      <p className="demarche-card__desc">{demarche.description}</p>
      <div className="demarche-card__footer">
        {demarche.enabled ? (
          <Badge variant="success">{demarche.documents.length} documents requis</Badge>
        ) : (
          <Badge variant="neutral">Bientot disponible</Badge>
        )}
      </div>
    </Card>
  );
}
