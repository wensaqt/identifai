from __future__ import annotations

from dataclasses import dataclass, fields as dc_fields
from typing import ClassVar, Optional


@dataclass
class DocumentFields:
    """Base class for all document field models."""

    DOC_TYPE: ClassVar[str] = ""
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    def to_dict(self) -> dict:
        return {
            f.name: getattr(self, f.name)
            for f in dc_fields(self)
            if getattr(self, f.name) is not None
        }

    def missing_fields(self) -> list[str]:
        return [f for f in self.REQUIRED_FIELDS if getattr(self, f, None) is None]


@dataclass
class InvoiceFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = "invoice"
    REQUIRED_FIELDS: ClassVar[list[str]] = [
        "siret_emetteur", "montant_ht", "montant_ttc", "date_emission",
    ]
    invoice_id: Optional[str] = None
    siret_emetteur: Optional[str] = None
    nom_emetteur: Optional[str] = None
    nom_client: Optional[str] = None
    siret_client: Optional[str] = None
    date_emission: Optional[str] = None
    date_prestation: Optional[str] = None
    montant_ht: Optional[str] = None
    tva_rate: Optional[str] = None
    montant_tva: Optional[str] = None
    montant_ttc: Optional[str] = None
    statut_paiement: Optional[str] = None
    reference_paiement: Optional[str] = None


@dataclass
class DevisFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = "devis"
    REQUIRED_FIELDS: ClassVar[list[str]] = [
        "siret_emetteur", "montant_ht", "date_emission",
    ]
    numero: Optional[str] = None
    siret_emetteur: Optional[str] = None
    siret_client: Optional[str] = None
    tva: Optional[str] = None
    montant_ht: Optional[str] = None
    montant_ttc: Optional[str] = None
    date_emission: Optional[str] = None
    date_validite: Optional[str] = None


@dataclass
class AttestationSiretFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = "attestation_siret"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["siret"]
    siret: Optional[str] = None
    siren: Optional[str] = None
    company_name: Optional[str] = None
    date_inscription: Optional[str] = None


@dataclass
class AttestationUrssafFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = "attestation_urssaf"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["siret", "date_expiration"]
    siret: Optional[str] = None
    company_name: Optional[str] = None
    date_delivrance: Optional[str] = None
    date_expiration: Optional[str] = None


@dataclass
class KbisFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = "kbis"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["siret", "siren"]
    siret: Optional[str] = None
    siren: Optional[str] = None
    company_name: Optional[str] = None
    rcs: Optional[str] = None
    date_immatriculation: Optional[str] = None
    date_extrait: Optional[str] = None


@dataclass
class RibFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = "rib"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["iban"]
    titulaire: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_name: Optional[str] = None


@dataclass
class PaymentFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = "payment"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["montant", "date_paiement"]
    payment_id: Optional[str] = None
    date_paiement: Optional[str] = None
    montant: Optional[str] = None
    emetteur: Optional[str] = None
    destinataire: Optional[str] = None
    reference_facture: Optional[str] = None
    methode: Optional[str] = None


@dataclass
class UrssafDeclarationFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = "urssaf_declaration"
    REQUIRED_FIELDS: ClassVar[list[str]] = [
        "siret", "periode", "chiffre_affaires_declare", "date_declaration",
    ]
    siret: Optional[str] = None
    periode: Optional[str] = None
    chiffre_affaires_declare: Optional[str] = None
    date_declaration: Optional[str] = None


DOC_TYPE_MODELS: dict[str, type[DocumentFields]] = {
    "facture": InvoiceFields,
    "invoice": InvoiceFields,
    "devis": DevisFields,
    "attestation_siret": AttestationSiretFields,
    "attestation_urssaf": AttestationUrssafFields,
    "kbis": KbisFields,
    "rib": RibFields,
    "payment": PaymentFields,
    "urssaf_declaration": UrssafDeclarationFields,
}
