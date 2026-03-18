"""Declarative definitions for all 8 business scenarios."""
from .consts import AnomalyType, DocType, ProcessType
from .models import Alteration, ScenarioDefinition

SCENARIOS: list[ScenarioDefinition] = [
    ScenarioDefinition(
        name="happy_path",
        description=(
            "Process complet, tous les documents valides. "
            "Facture payée, paiement correspondant, déclaration URSSAF correcte."
        ),
        process_type=ProcessType.CONFORMITE_FOURNISSEUR,
        alterations=[],
        omitted_docs=[],
    ),
    ScenarioDefinition(
        name="missing_payment",
        description="Facture marquée comme payée sans justificatif de paiement.",
        process_type=ProcessType.CONFORMITE_FOURNISSEUR,
        alterations=[Alteration(DocType.INVOICE, AnomalyType.MISSING_PAYMENT)],
        omitted_docs=[DocType.PAYMENT],
    ),
    ScenarioDefinition(
        name="mauvais_siret",
        description="Le SIRET de la facture ne correspond pas aux attestations.",
        process_type=ProcessType.CONFORMITE_FOURNISSEUR,
        alterations=[Alteration(DocType.INVOICE, AnomalyType.SIRET_MISMATCH)],
        omitted_docs=[],
    ),
    ScenarioDefinition(
        name="revenus_sous_declares",
        description="Le CA déclaré à l'URSSAF est inférieur au montant HT facturé.",
        process_type=ProcessType.CONFORMITE_FOURNISSEUR,
        alterations=[Alteration(DocType.URSSAF_DECLARATION, AnomalyType.UNDECLARED_REVENUE)],
        omitted_docs=[],
    ),
    ScenarioDefinition(
        name="incoherence_tva",
        description="Le montant de TVA ne correspond pas au taux appliqué sur le HT.",
        process_type=ProcessType.CONFORMITE_FOURNISSEUR,
        alterations=[Alteration(DocType.INVOICE, AnomalyType.TVA_MISMATCH)],
        omitted_docs=[],
    ),
    ScenarioDefinition(
        name="attestation_expiree",
        description="L'attestation URSSAF est expirée.",
        process_type=ProcessType.CONFORMITE_FOURNISSEUR,
        alterations=[Alteration(DocType.ATTESTATION_URSSAF, AnomalyType.EXPIRED_ATTESTATION)],
        omitted_docs=[],
    ),
    ScenarioDefinition(
        name="paiement_sans_facture",
        description="Un paiement référence une facture inexistante.",
        process_type=ProcessType.CONFORMITE_FOURNISSEUR,
        alterations=[Alteration(DocType.PAYMENT, AnomalyType.ORPHAN_PAYMENT)],
        omitted_docs=[DocType.INVOICE],
    ),
    ScenarioDefinition(
        name="montant_paiement_incorrect",
        description="Le montant du paiement ne correspond pas au TTC de la facture.",
        process_type=ProcessType.CONFORMITE_FOURNISSEUR,
        alterations=[Alteration(DocType.PAYMENT, AnomalyType.PAYMENT_AMOUNT_MISMATCH)],
        omitted_docs=[],
    ),
]

SCENARIO_BY_NAME: dict[str, ScenarioDefinition] = {s.name: s for s in SCENARIOS}
