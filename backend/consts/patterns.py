# ── Extraction patterns (used in extractor to find field values in OCR text) ──

EXTRACT_DATE = r"\d{2}[\/\-]\d{2}[\/\-]\d{4}|\d{4}[\/\-]\d{2}[\/\-]\d{2}"
EXTRACT_SIRET = r"\b(\d{14})\b"
EXTRACT_TVA = r"\b(FR[A-Z0-9]{2}\d{9})\b"
EXTRACT_IBAN = r"\b(FR\d{2}[\s\d]{20,30})\b"
EXTRACT_BIC = r"\bBIC\s*[:\-]?\s*([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b"
EXTRACT_MONTANT_HT = r"(?:total\s+HT|montant\s+HT|HT)\s*[:\-]?\s*([\d\s]+[.,]\d{2})\s*[€E]?"
EXTRACT_MONTANT_TTC = r"(?:total\s+TTC|montant\s+TTC|TTC)\s*[:\-]?\s*([\d\s]+[.,]\d{2})\s*[€E]?"
EXTRACT_MONTANT_TVA = r"TVA\s+\d+%?\s*[:\-]?\s*([\d\s]+[.,]\d{2})\s*[€E]?"
EXTRACT_MONTANT = r"[Mm]ontant\s*[:\-]?\s*([\d\s]+[.,]\d{2})\s*[€E]?"
EXTRACT_PAYMENT_ID = r"\b(PAY-\d{4}-\d{4})\b"
EXTRACT_REFERENCE_FACTURE = r"[Rr][ée]f\.?\s*facture\s*[:\-]?\s*(F-\d{4}-\d{4})"
EXTRACT_METHODE = r"[Mm][ée]thode\s*[:\-]?\s*(virement|pr[ée]l[èe]vement|ch[èe]que|carte\s+bancaire)"
EXTRACT_PERIODE = r"\b(\d{4}-T[1-4])\b"
EXTRACT_CA_DECLARE = r"[Cc]hiffre\s+d.affaires\s+d[ée]clar[ée]\s*[:\-]?\s*([\d\s,.]+)\s*[€E]?"
EXTRACT_DATE_DECLARATION = r"[Dd]ate\s+de\s+d[ée]claration\s*[:\-]?\s*({date})".format(date=EXTRACT_DATE)

# ── Validation patterns (used in validator to check field format) ────────────

VALIDATE_DATE = r"^\d{2}/\d{2}/\d{4}$|^\d{4}-\d{2}-\d{2}$"
VALIDATE_DATE_ISO = r"^\d{4}-\d{2}-\d{2}$"
VALIDATE_AMOUNT = r"^\d+(\.\d{1,2})?$"
VALIDATE_SIRET = r"^\d{14}$"
VALIDATE_SIREN = r"^\d{9}$"
VALIDATE_TVA = r"^FR[A-Z0-9]{2}\d{9}$"
VALIDATE_IBAN = r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$"
VALIDATE_BIC = r"^[A-Z]{6}[A-Z0-9]{2,5}$"
VALIDATE_PERIODE = r"^\d{4}-T[1-4]$"

# ── Classification patterns (used in classifier to identify document type) ───

CLASSIFY_URSSAF_DECLARATION = [r"urssaf", r"d[ée]claration\s+de\s+chiffre"]
CLASSIFY_ATTESTATION_URSSAF = [r"urssaf", r"attestation"]
CLASSIFY_ATTESTATION_SIRET = [r"sirene|siret", r"avis\s+de\s+situation|r[ée]pertoire"]
CLASSIFY_KBIS = [r"extrait\s*k\s*bis|k\s*bis|greffe|tribunal\s+de\s+commerce"]
CLASSIFY_RIB = [r"relev[ée]\s+d.identit[ée]\s+bancaire|rib", r"iban"]
CLASSIFY_PAYMENT = [r"confirmation\s+de\s+paiement"]
CLASSIFY_FACTURE = [r"facture"]
CLASSIFY_DEVIS = [r"devis"]
