"""Declarative definitions for all 8 business scenarios."""
from .consts import AnomalyType, DocType
from .models import ScenarioDefinition, ScenarioDocSpec

SCENARIOS: list[ScenarioDefinition] = [
    ScenarioDefinition(
        name="happy_path",
        description=(
            "Tous les documents sont cohérents. "
            "Facture payée, paiement correspondant, déclaration URSSAF correcte."
        ),
        doc_specs=[
            ScenarioDocSpec(DocType.INVOICE),
            ScenarioDocSpec(DocType.DEVIS),
            ScenarioDocSpec(DocType.PAYMENT),
            ScenarioDocSpec(DocType.URSSAF_DECLARATION),
            ScenarioDocSpec(DocType.ATTESTATION_SIRET),
            ScenarioDocSpec(DocType.ATTESTATION_URSSAF),
            ScenarioDocSpec(DocType.KBIS),
            ScenarioDocSpec(DocType.RIB),
        ],
        anomaly_types=[],
        risk_level="low",
    ),
    ScenarioDefinition(
        name="missing_payment",
        description="Facture marquée comme payée sans justificatif de paiement.",
        doc_specs=[
            ScenarioDocSpec(DocType.INVOICE, anomaly=AnomalyType.MISSING_PAYMENT),
            ScenarioDocSpec(DocType.ATTESTATION_SIRET),
            ScenarioDocSpec(DocType.ATTESTATION_URSSAF),
        ],
        anomaly_types=[AnomalyType.MISSING_PAYMENT],
        risk_level="medium",
    ),
    ScenarioDefinition(
        name="mauvais_siret",
        description="Le SIRET de la facture ne correspond pas aux attestations.",
        doc_specs=[
            ScenarioDocSpec(DocType.INVOICE, anomaly=AnomalyType.SIRET_MISMATCH),
            ScenarioDocSpec(DocType.ATTESTATION_SIRET),
            ScenarioDocSpec(DocType.ATTESTATION_URSSAF),
            ScenarioDocSpec(DocType.KBIS),
        ],
        anomaly_types=[AnomalyType.SIRET_MISMATCH],
        risk_level="high",
    ),
    ScenarioDefinition(
        name="revenus_sous_declares",
        description="Le CA déclaré à l'URSSAF est inférieur au montant HT facturé.",
        doc_specs=[
            ScenarioDocSpec(DocType.INVOICE),
            ScenarioDocSpec(DocType.URSSAF_DECLARATION, anomaly=AnomalyType.UNDECLARED_REVENUE),
            ScenarioDocSpec(DocType.ATTESTATION_SIRET),
        ],
        anomaly_types=[AnomalyType.UNDECLARED_REVENUE],
        risk_level="high",
    ),
    ScenarioDefinition(
        name="incoherence_tva",
        description="Le montant de TVA ne correspond pas au taux appliqué sur le HT.",
        doc_specs=[
            ScenarioDocSpec(DocType.INVOICE, anomaly=AnomalyType.TVA_MISMATCH),
            ScenarioDocSpec(DocType.ATTESTATION_SIRET),
        ],
        anomaly_types=[AnomalyType.TVA_MISMATCH],
        risk_level="medium",
    ),
    ScenarioDefinition(
        name="attestation_expiree",
        description="L'attestation URSSAF est expirée.",
        doc_specs=[
            ScenarioDocSpec(DocType.INVOICE),
            ScenarioDocSpec(DocType.ATTESTATION_SIRET),
            ScenarioDocSpec(DocType.ATTESTATION_URSSAF, anomaly=AnomalyType.EXPIRED_ATTESTATION),
            ScenarioDocSpec(DocType.KBIS),
        ],
        anomaly_types=[AnomalyType.EXPIRED_ATTESTATION],
        risk_level="high",
    ),
    ScenarioDefinition(
        name="paiement_sans_facture",
        description="Un paiement référence une facture inexistante.",
        doc_specs=[
            ScenarioDocSpec(DocType.PAYMENT, anomaly=AnomalyType.ORPHAN_PAYMENT),
            ScenarioDocSpec(DocType.ATTESTATION_SIRET),
        ],
        anomaly_types=[AnomalyType.ORPHAN_PAYMENT],
        risk_level="medium",
    ),
    ScenarioDefinition(
        name="montant_paiement_incorrect",
        description="Le montant du paiement ne correspond pas au TTC de la facture.",
        doc_specs=[
            ScenarioDocSpec(DocType.INVOICE),
            ScenarioDocSpec(DocType.PAYMENT, anomaly=AnomalyType.PAYMENT_AMOUNT_MISMATCH),
            ScenarioDocSpec(DocType.ATTESTATION_SIRET),
        ],
        anomaly_types=[AnomalyType.PAYMENT_AMOUNT_MISMATCH],
        risk_level="medium",
    ),
]

SCENARIO_BY_NAME: dict[str, ScenarioDefinition] = {s.name: s for s in SCENARIOS}
