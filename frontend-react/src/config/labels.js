export const DOC_TYPE_LABELS = {
  invoice: "Facture",
  quote: "Devis",
  siret_certificate: "Attestation SIRET",
  urssaf_certificate: "Attestation URSSAF",
  company_registration: "Extrait Kbis",
  bank_account_details: "RIB",
  payment: "Justificatif de paiement",
  urssaf_declaration: "Déclaration URSSAF",
};

export const ANOMALY_LABELS = {
  siret_mismatch: { title: "SIRET non conforme", detail: "Le SIRET ne correspond pas entre les documents." },
  expired_attestation: { title: "Attestation expirée", detail: "L'attestation URSSAF n'est plus valide." },
  tva_mismatch: { title: "Incohérence TVA", detail: "Le montant TVA ne correspond pas au taux appliqué." },
  payment_amount_mismatch: { title: "Montant incorrect", detail: "Le montant réglé ne correspond pas au TTC." },
  orphan_payment: { title: "Paiement sans facture", detail: "Le paiement référence une facture introuvable." },
  missing_payment: { title: "Paiement non justifié", detail: "Aucun justificatif pour cette facture." },
  undeclared_revenue: { title: "CA sous-déclaré", detail: "Le CA déclaré est inférieur au HT facturé." },
  missing_field: { title: "Champ manquant", detail: "Des informations obligatoires sont absentes." },
  invalid_format: { title: "Format invalide", detail: "Un champ ne respecte pas le format attendu." },
  missing_document: { title: "Document manquant", detail: "Un document requis est absent du dossier." },
  doc_type_mismatch: { title: "Type inattendu", detail: "Le document ne correspond pas au type attendu." },
};

export const FIELD_LABELS = {
  siret: "SIRET",
  siret_emetteur: "SIRET émetteur",
  siren: "SIREN",
  iban: "IBAN",
  bic: "BIC",
  montant_ht: "Montant HT",
  montant_ttc: "Montant TTC",
  montant_tva: "Montant TVA",
  montant: "Montant",
  tva_rate: "Taux TVA",
  date_emission: "Date d'émission",
  date_expiration: "Date d'expiration",
  date_paiement: "Date de paiement",
  date_delivrance: "Date de délivrance",
  invoice_id: "N° de facture",
  payment_id: "N° de paiement",
  reference_facture: "Réf. facture",
  chiffre_affaires_declare: "CA déclaré",
  periode: "Période",
  company_name: "Dénomination",
  methode: "Méthode de paiement",
};

export const STATUS_CONFIG = {
  valid: { icon: "✓", label: "Conforme", variant: "success" },
  error: { icon: "✕", label: "Non conforme", variant: "error" },
  pending: { icon: "…", label: "En cours", variant: "neutral" },
  cancelled: { icon: "—", label: "Annulé", variant: "neutral" },
};
