/**
 * Each démarche maps 1:1 to a backend ProcessType.
 * `documents` ids must match backend DocType values exactly.
 * `enabled: false` → displayed greyed out on landing page.
 */
export const PROCESSES = [
  {
    id: "supplier_compliance",
    title: "Conformité fournisseur",
    icon: "🏢",
    enabled: true,
    description:
      "Vérifiez l'identité légale, la validité des attestations et la cohérence documentaire d'un fournisseur.",
    documents: [
      {
        id: "invoice",
        label: "Facture",
        hint: "Facture émise par le fournisseur",
        required: true,
      },
      {
        id: "siret_certificate",
        label: "Attestation SIRET",
        hint: "Attestation INSEE",
        required: true,
      },
      {
        id: "urssaf_certificate",
        label: "Attestation URSSAF",
        hint: "Attestation de vigilance en cours de validité",
        required: true,
      },
      {
        id: "company_registration",
        label: "Extrait Kbis",
        hint: "Kbis de moins de 3 mois",
        required: true,
      },
      {
        id: "bank_account_details",
        label: "RIB",
        hint: "Relevé d'identité bancaire",
        required: true,
      },
      {
        id: "payment",
        label: "Justificatif de paiement",
        hint: "Virement, reçu ou relevé",
        required: true,
      },
      {
        id: "urssaf_declaration",
        label: "Déclaration URSSAF",
        hint: "Déclaration de CA",
        required: true,
      },
    ],
  },
  {
    id: "annual_declaration",
    title: "Déclaration annuelle",
    icon: "📋",
    enabled: false,
    description:
      "Validez votre déclaration de chiffre d'affaires auprès de l'URSSAF.",
    documents: [],
  },
  {
    id: "payment_validation",
    title: "Validation de paiement",
    icon: "💳",
    enabled: false,
    description:
      "Vérifiez la correspondance entre factures et justificatifs de paiement.",
    documents: [],
  },
  {
    id: "invoice_audit",
    title: "Contrôle de facturation",
    icon: "🧾",
    enabled: false,
    description:
      "Analysez vos factures pour détecter des incohérences de calcul.",
    documents: [],
  },
];

export const getProcessConfiguration = (id) =>
  PROCESSES.find((d) => d.id === id);
