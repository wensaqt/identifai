from __future__ import annotations

from dataclasses import dataclass, fields as dc_fields
from typing import ClassVar, Optional

from consts.doc_types import DocType
from consts.fields import FieldName as F


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
    DOC_TYPE: ClassVar[str] = DocType.INVOICE
    REQUIRED_FIELDS: ClassVar[list[str]] = [
        F.SIRET_EMETTEUR, F.MONTANT_HT, F.MONTANT_TTC, F.DATE_EMISSION,
    ]
    siret_emetteur: Optional[str] = None
    nom_emetteur: Optional[str] = None
    nom_client: Optional[str] = None
    siret_client: Optional[str] = None
    invoice_id: Optional[str] = None
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
    DOC_TYPE: ClassVar[str] = DocType.DEVIS
    REQUIRED_FIELDS: ClassVar[list[str]] = [
        F.SIRET_EMETTEUR, F.MONTANT_HT, F.DATE_EMISSION,
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
    DOC_TYPE: ClassVar[str] = DocType.ATTESTATION_SIRET
    REQUIRED_FIELDS: ClassVar[list[str]] = [F.SIRET]
    siret: Optional[str] = None
    siren: Optional[str] = None
    company_name: Optional[str] = None
    date_inscription: Optional[str] = None


@dataclass
class AttestationUrssafFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = DocType.ATTESTATION_URSSAF
    REQUIRED_FIELDS: ClassVar[list[str]] = [F.SIRET, F.DATE_EXPIRATION]
    siret: Optional[str] = None
    company_name: Optional[str] = None
    date_delivrance: Optional[str] = None
    date_expiration: Optional[str] = None


@dataclass
class KbisFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = DocType.KBIS
    REQUIRED_FIELDS: ClassVar[list[str]] = [F.SIRET, F.SIREN]
    siret: Optional[str] = None
    siren: Optional[str] = None
    company_name: Optional[str] = None
    rcs: Optional[str] = None
    date_immatriculation: Optional[str] = None
    date_extrait: Optional[str] = None


@dataclass
class RibFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = DocType.RIB
    REQUIRED_FIELDS: ClassVar[list[str]] = [F.IBAN]
    titulaire: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_name: Optional[str] = None


@dataclass
class PaymentFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = DocType.PAYMENT
    REQUIRED_FIELDS: ClassVar[list[str]] = [F.MONTANT, F.DATE_PAIEMENT]
    payment_id: Optional[str] = None
    date_paiement: Optional[str] = None
    montant: Optional[str] = None
    emetteur: Optional[str] = None
    destinataire: Optional[str] = None
    reference_facture: Optional[str] = None
    methode: Optional[str] = None


@dataclass
class UrssafDeclarationFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = DocType.URSSAF_DECLARATION
    REQUIRED_FIELDS: ClassVar[list[str]] = [
        F.SIRET, F.PERIODE, F.CHIFFRE_AFFAIRES_DECLARE, F.DATE_DECLARATION,
    ]
    siret: Optional[str] = None
    periode: Optional[str] = None
    chiffre_affaires_declare: Optional[str] = None
    date_declaration: Optional[str] = None


DOC_TYPE_MODELS: dict[str, type[DocumentFields]] = {
    DocType.FACTURE: InvoiceFields,
    DocType.INVOICE: InvoiceFields,
    DocType.DEVIS: DevisFields,
    DocType.ATTESTATION_SIRET: AttestationSiretFields,
    DocType.ATTESTATION_URSSAF: AttestationUrssafFields,
    DocType.KBIS: KbisFields,
    DocType.RIB: RibFields,
    DocType.PAYMENT: PaymentFields,
    DocType.URSSAF_DECLARATION: UrssafDeclarationFields,
}
