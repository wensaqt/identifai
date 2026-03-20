from __future__ import annotations

from dataclasses import dataclass
from dataclasses import fields as dc_fields
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
        F.INVOICE_ID,
        F.SIRET_EMETTEUR,
        F.MONTANT_HT,
        F.MONTANT_TTC,
        F.DATE_EMISSION,
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
class QuoteFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = DocType.QUOTE
    REQUIRED_FIELDS: ClassVar[list[str]] = [
        F.SIRET_EMETTEUR,
        F.MONTANT_HT,
        F.DATE_EMISSION,
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
class SiretCertificateFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = DocType.SIRET_CERTIFICATE
    REQUIRED_FIELDS: ClassVar[list[str]] = [F.SIRET]
    siret: Optional[str] = None
    siren: Optional[str] = None
    company_name: Optional[str] = None
    date_inscription: Optional[str] = None


@dataclass
class UrssafCertificateFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = DocType.URSSAF_CERTIFICATE
    REQUIRED_FIELDS: ClassVar[list[str]] = [F.SIRET, F.DATE_EXPIRATION]
    siret: Optional[str] = None
    company_name: Optional[str] = None
    date_delivrance: Optional[str] = None
    date_expiration: Optional[str] = None


@dataclass
class CompanyRegistrationFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = DocType.COMPANY_REGISTRATION
    REQUIRED_FIELDS: ClassVar[list[str]] = [F.SIRET, F.SIREN]
    siret: Optional[str] = None
    siren: Optional[str] = None
    company_name: Optional[str] = None
    rcs: Optional[str] = None
    date_immatriculation: Optional[str] = None
    date_extrait: Optional[str] = None


@dataclass
class BankAccountDetailsFields(DocumentFields):
    DOC_TYPE: ClassVar[str] = DocType.BANK_ACCOUNT_DETAILS
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
        F.SIRET,
        F.PERIODE,
        F.CHIFFRE_AFFAIRES_DECLARE,
        F.DATE_DECLARATION,
    ]
    siret: Optional[str] = None
    periode: Optional[str] = None
    chiffre_affaires_declare: Optional[str] = None
    date_declaration: Optional[str] = None


DOC_TYPE_MODELS: dict[str, type[DocumentFields]] = {
    DocType.INVOICE: InvoiceFields,
    DocType.QUOTE: QuoteFields,
    DocType.SIRET_CERTIFICATE: SiretCertificateFields,
    DocType.URSSAF_CERTIFICATE: UrssafCertificateFields,
    DocType.COMPANY_REGISTRATION: CompanyRegistrationFields,
    DocType.BANK_ACCOUNT_DETAILS: BankAccountDetailsFields,
    DocType.PAYMENT: PaymentFields,
    DocType.URSSAF_DECLARATION: UrssafDeclarationFields,
}
