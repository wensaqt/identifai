from datetime import timedelta

from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from .company import CompanyIdentity

W, H = A4


# ── Helpers ──────────────────────────────────────────────────────────────────

def _header(c: Canvas, title: str, company: CompanyIdentity, y: float) -> float:
    c.setFont("Helvetica-Bold", 18)
    c.drawString(30 * mm, y, title)
    y -= 12 * mm
    c.setFont("Helvetica", 9)
    for line in [
        f"{company.name} — {company.forme_juridique}",
        company.address,
        f"{company.zip_code} {company.city}",
        f"SIRET : {company.siret}  —  TVA : {company.tva}",
    ]:
        c.drawString(30 * mm, y, line)
        y -= 5 * mm
    return y


def _footer(c: Canvas, company: CompanyIdentity):
    c.setFont("Helvetica", 7)
    c.drawCentredString(
        W / 2, 15 * mm,
        f"{company.name} — {company.forme_juridique} au capital de {company.capital_social:,} € — {company.rcs}",
    )


_PRESTATIONS = [
    "Conseil en gestion", "Audit comptable", "Maintenance informatique",
    "Développement logiciel", "Formation professionnelle", "Prestation de nettoyage",
    "Livraison de fournitures", "Installation réseau", "Support technique",
    "Étude de marché", "Rédaction de contenu", "Design graphique",
    "Hébergement serveur", "Location de matériel", "Réparation équipement",
    "Transport de marchandises", "Consulting stratégique", "Mise en conformité",
    "Gestion de projet", "Analyse de données",
]


def _line_items(fake: Faker, n: int = None):
    n = n or fake.random_int(3, 8)
    items = []
    for _ in range(n):
        qty = fake.random_int(1, 20)
        unit_price = round(fake.pyfloat(min_value=10, max_value=500, right_digits=2), 2)
        items.append({
            "description": fake.random_element(_PRESTATIONS),
            "qty": qty,
            "unit_price": unit_price,
            "total": round(qty * unit_price, 2),
        })
    return items


def _draw_items_table(c: Canvas, items: list[dict], y: float) -> tuple[float, float]:
    c.setFont("Helvetica-Bold", 9)
    cols = [30 * mm, 110 * mm, 130 * mm, 155 * mm]
    for label, x in zip(["Description", "Qté", "PU HT (€)", "Total HT (€)"], cols):
        c.drawString(x, y, label)
    y -= 3 * mm
    c.line(30 * mm, y, 185 * mm, y)
    y -= 5 * mm

    c.setFont("Helvetica", 9)
    total_ht = 0.0
    for item in items:
        c.drawString(cols[0], y, item["description"][:40])
        c.drawString(cols[1], y, str(item["qty"]))
        c.drawString(cols[2], y, f"{item['unit_price']:.2f}")
        c.drawString(cols[3], y, f"{item['total']:.2f}")
        total_ht += item["total"]
        y -= 5 * mm

    return y, round(total_ht, 2)


# ── Document generators ─────────────────────────────────────────────────────

def generate_facture(company: CompanyIdentity, client: CompanyIdentity,
                     fake: Faker, filepath: str) -> dict:
    c = Canvas(filepath, pagesize=A4)
    date_emission = fake.date_between(start_date="-1y", end_date="today")
    numero = f"F-{date_emission.year}-{fake.unique.random_int(1, 9999):04d}"

    y = _header(c, "FACTURE", company, H - 20 * mm)

    y -= 8 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30 * mm, y, f"N° {numero}")
    c.drawString(120 * mm, y, "Client :")
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    c.drawString(30 * mm, y, f"Date : {date_emission.strftime('%d/%m/%Y')}")
    c.drawString(120 * mm, y, client.name)
    y -= 5 * mm
    c.drawString(120 * mm, y, client.address)
    y -= 5 * mm
    c.drawString(120 * mm, y, f"{client.zip_code} {client.city}")
    y -= 5 * mm
    c.drawString(120 * mm, y, f"SIRET : {client.siret}")

    y -= 15 * mm
    items = _line_items(fake)
    y, total_ht = _draw_items_table(c, items, y)

    tva_amount = round(total_ht * 0.20, 2)
    total_ttc = round(total_ht + tva_amount, 2)

    y -= 8 * mm
    c.line(130 * mm, y + 3 * mm, 185 * mm, y + 3 * mm)
    c.setFont("Helvetica", 10)
    c.drawString(130 * mm, y, f"Total HT :    {total_ht:.2f} €")
    y -= 5 * mm
    c.drawString(130 * mm, y, f"TVA 20% :     {tva_amount:.2f} €")
    y -= 5 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(130 * mm, y, f"Total TTC :   {total_ttc:.2f} €")

    y -= 15 * mm
    c.setFont("Helvetica", 8)
    c.drawString(30 * mm, y, f"Règlement par virement — IBAN : {company.iban}  BIC : {company.bic}")

    _footer(c, company)
    c.save()

    return {
        "type": "facture",
        "numero": numero,
        "siret_emetteur": company.siret,
        "siret_client": client.siret,
        "tva": company.tva,
        "montant_ht": total_ht,
        "montant_ttc": total_ttc,
        "date_emission": date_emission.isoformat(),
    }


def generate_devis(company: CompanyIdentity, client: CompanyIdentity,
                   fake: Faker, filepath: str) -> dict:
    c = Canvas(filepath, pagesize=A4)
    date_emission = fake.date_between(start_date="-1y", end_date="today")
    date_validite = date_emission + timedelta(days=30)
    numero = f"D-{date_emission.year}-{fake.unique.random_int(1, 9999):04d}"

    y = _header(c, "DEVIS", company, H - 20 * mm)

    y -= 8 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30 * mm, y, f"N° {numero}")
    c.drawString(120 * mm, y, "Client :")
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    c.drawString(30 * mm, y, f"Date : {date_emission.strftime('%d/%m/%Y')}")
    c.drawString(120 * mm, y, client.name)
    y -= 5 * mm
    c.drawString(30 * mm, y, f"Validité : {date_validite.strftime('%d/%m/%Y')}")
    c.drawString(120 * mm, y, client.address)
    y -= 5 * mm
    c.drawString(120 * mm, y, f"{client.zip_code} {client.city}")

    y -= 15 * mm
    items = _line_items(fake)
    y, total_ht = _draw_items_table(c, items, y)

    tva_amount = round(total_ht * 0.20, 2)
    total_ttc = round(total_ht + tva_amount, 2)

    y -= 8 * mm
    c.line(130 * mm, y + 3 * mm, 185 * mm, y + 3 * mm)
    c.setFont("Helvetica", 10)
    c.drawString(130 * mm, y, f"Total HT :    {total_ht:.2f} €")
    y -= 5 * mm
    c.drawString(130 * mm, y, f"TVA 20% :     {tva_amount:.2f} €")
    y -= 5 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(130 * mm, y, f"Total TTC :   {total_ttc:.2f} €")

    _footer(c, company)
    c.save()

    return {
        "type": "devis",
        "numero": numero,
        "siret_emetteur": company.siret,
        "siret_client": client.siret,
        "tva": company.tva,
        "montant_ht": total_ht,
        "montant_ttc": total_ttc,
        "date_emission": date_emission.isoformat(),
        "date_validite": date_validite.isoformat(),
    }


def generate_attestation_siret(company: CompanyIdentity,
                               fake: Faker, filepath: str) -> dict:
    c = Canvas(filepath, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, H - 30 * mm, "AVIS DE SITUATION AU RÉPERTOIRE SIRENE")

    c.setFont("Helvetica", 9)
    c.drawCentredString(W / 2, H - 38 * mm, "Institut National de la Statistique et des Études Économiques")

    y = H - 60 * mm
    fields = [
        ("Dénomination", company.name),
        ("Forme juridique", company.forme_juridique),
        ("SIREN", company.siren),
        ("NIC", company.siret[9:]),
        ("SIRET", company.siret),
        ("Adresse", f"{company.address}, {company.zip_code} {company.city}"),
        ("Date d'inscription", company.registration_date),
    ]

    for label, value in fields:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30 * mm, y, f"{label} :")
        c.setFont("Helvetica", 10)
        c.drawString(80 * mm, y, value)
        y -= 8 * mm

    c.setFont("Helvetica", 8)
    c.drawCentredString(W / 2, 20 * mm, "Document à caractère informatif, ne constitue pas une preuve juridique.")
    c.save()

    return {
        "type": "attestation_siret",
        "siret": company.siret,
        "siren": company.siren,
        "company_name": company.name,
        "date_inscription": company.registration_date,
    }


def generate_attestation_urssaf(company: CompanyIdentity,
                                fake: Faker, filepath: str) -> dict:
    c = Canvas(filepath, pagesize=A4)

    c.setFillColorRGB(0.0, 0.2, 0.6)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(30 * mm, H - 30 * mm, "URSSAF")
    c.setFillColorRGB(0, 0, 0)

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, H - 50 * mm, "ATTESTATION DE VIGILANCE")

    date_delivrance = fake.date_between(start_date="-6m", end_date="today")
    date_fin = date_delivrance + timedelta(days=180)

    y = H - 70 * mm
    c.setFont("Helvetica", 10)
    lines = [
        "Je soussigné, l'URSSAF, atteste que la société :",
        "",
        f"    {company.name} — {company.forme_juridique}",
        f"    SIRET : {company.siret}",
        f"    {company.address}, {company.zip_code} {company.city}",
        "",
        "est à jour de ses obligations de déclaration et de paiement",
        "auprès de l'organisme de recouvrement.",
        "",
        f"Date de délivrance : {date_delivrance.strftime('%d/%m/%Y')}",
        f"Date de fin de validité : {date_fin.strftime('%d/%m/%Y')}",
    ]

    for line in lines:
        c.drawString(30 * mm, y, line)
        y -= 6 * mm

    c.save()

    return {
        "type": "attestation_urssaf",
        "siret": company.siret,
        "company_name": company.name,
        "date_delivrance": date_delivrance.isoformat(),
        "date_expiration": date_fin.isoformat(),
    }


def generate_attestation_urssaf_expired(company: CompanyIdentity,
                                         fake: Faker, filepath: str) -> dict:
    """Generate an URSSAF attestation that is already expired."""
    c = Canvas(filepath, pagesize=A4)

    c.setFillColorRGB(0.0, 0.2, 0.6)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(30 * mm, H - 30 * mm, "URSSAF")
    c.setFillColorRGB(0, 0, 0)

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, H - 50 * mm, "ATTESTATION DE VIGILANCE")

    # Expired: delivered 5-4 years ago, validity of 180 days => clearly expired
    date_delivrance = fake.date_between(start_date="-5y", end_date="-4y")
    date_fin = date_delivrance + timedelta(days=180)

    y = H - 70 * mm
    c.setFont("Helvetica", 10)
    lines = [
        "Je soussigné, l'URSSAF, atteste que la société :",
        "",
        f"    {company.name} — {company.forme_juridique}",
        f"    SIRET : {company.siret}",
        f"    {company.address}, {company.zip_code} {company.city}",
        "",
        "est à jour de ses obligations de déclaration et de paiement",
        "auprès de l'organisme de recouvrement.",
        "",
        f"Date de délivrance : {date_delivrance.strftime('%d/%m/%Y')}",
        f"Date de fin de validité : {date_fin.strftime('%d/%m/%Y')}",
    ]

    for line in lines:
        c.drawString(30 * mm, y, line)
        y -= 6 * mm

    c.save()

    return {
        "type": "attestation_urssaf",
        "siret": company.siret,
        "company_name": company.name,
        "date_delivrance": date_delivrance.isoformat(),
        "date_expiration": date_fin.isoformat(),
        "expired": True,
    }


def generate_facture_no_amounts(company: CompanyIdentity, client: CompanyIdentity,
                                fake: Faker, filepath: str) -> dict:
    """Facture sans totaux HT/TTC — déclenche missing_fields."""
    c = Canvas(filepath, pagesize=A4)
    date_emission = fake.date_between(start_date="-1y", end_date="today")
    numero = f"F-{date_emission.year}-{fake.unique.random_int(1, 9999):04d}"

    y = _header(c, "FACTURE", company, H - 20 * mm)

    y -= 8 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30 * mm, y, f"N° {numero}")
    c.drawString(120 * mm, y, "Client :")
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    c.drawString(30 * mm, y, f"Date : {date_emission.strftime('%d/%m/%Y')}")
    c.drawString(120 * mm, y, client.name)
    y -= 5 * mm
    c.drawString(120 * mm, y, f"SIRET : {client.siret}")

    y -= 15 * mm
    items = _line_items(fake)
    y, total_ht = _draw_items_table(c, items, y)
    # Totaux délibérément omis

    _footer(c, company)
    c.save()

    return {
        "type": "facture",
        "numero": numero,
        "siret_emetteur": company.siret,
        "siret_client": client.siret,
        "date_emission": date_emission.isoformat(),
        "missing": ["montant_ht", "montant_ttc"],
    }


def generate_rib_no_iban(company: CompanyIdentity, fake: Faker, filepath: str) -> dict:
    """RIB sans IBAN — déclenche missing_fields."""
    c = Canvas(filepath, pagesize=A4)

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, H - 30 * mm, "RELEVÉ D'IDENTITÉ BANCAIRE")

    y = H - 55 * mm
    fields = [
        ("Titulaire", company.name),
        ("Banque", company.bank_name),
        # IBAN délibérément absent
        ("BIC / SWIFT", company.bic),
    ]

    for label, value in fields:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(30 * mm, y, f"{label} :")
        c.setFont("Helvetica", 11)
        c.drawString(75 * mm, y, value)
        y -= 10 * mm

    c.setFont("Helvetica", 8)
    c.drawCentredString(W / 2, 20 * mm, "Ce document est confidentiel et destiné exclusivement au destinataire.")
    c.save()

    return {
        "type": "rib",
        "titulaire": company.name,
        "bic": company.bic,
        "bank_name": company.bank_name,
        "missing": ["iban"],
    }


def generate_attestation_urssaf_no_expiry(company: CompanyIdentity,
                                          fake: Faker, filepath: str) -> dict:
    """Attestation URSSAF sans date de fin de validité — déclenche missing_fields."""
    c = Canvas(filepath, pagesize=A4)

    c.setFillColorRGB(0.0, 0.2, 0.6)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(30 * mm, H - 30 * mm, "URSSAF")
    c.setFillColorRGB(0, 0, 0)

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, H - 50 * mm, "ATTESTATION DE VIGILANCE")

    date_delivrance = fake.date_between(start_date="-6m", end_date="today")

    y = H - 70 * mm
    c.setFont("Helvetica", 10)
    lines = [
        "Je soussigné, l'URSSAF, atteste que la société :",
        "",
        f"    {company.name} — {company.forme_juridique}",
        f"    SIRET : {company.siret}",
        f"    {company.address}, {company.zip_code} {company.city}",
        "",
        "est à jour de ses obligations de déclaration et de paiement",
        "auprès de l'organisme de recouvrement.",
        "",
        f"Date de délivrance : {date_delivrance.strftime('%d/%m/%Y')}",
        # Date de fin de validité délibérément absente
    ]

    for line in lines:
        c.drawString(30 * mm, y, line)
        y -= 6 * mm

    c.save()

    return {
        "type": "attestation_urssaf",
        "siret": company.siret,
        "company_name": company.name,
        "date_delivrance": date_delivrance.isoformat(),
        "missing": ["date_expiration"],
    }


def generate_kbis(company: CompanyIdentity, fake: Faker, filepath: str) -> dict:
    c = Canvas(filepath, pagesize=A4)

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W / 2, H - 25 * mm, "EXTRAIT K BIS")
    c.setFont("Helvetica", 9)
    c.drawCentredString(W / 2, H - 32 * mm, f"Greffe du Tribunal de Commerce de {company.city}")

    # Stamp circle
    c.setStrokeColorRGB(0.3, 0.3, 0.8)
    c.setLineWidth(2)
    c.circle(160 * mm, H - 55 * mm, 15 * mm, fill=0)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColorRGB(0.3, 0.3, 0.8)
    c.drawCentredString(160 * mm, H - 54 * mm, "GREFFE")
    c.drawCentredString(160 * mm, H - 58 * mm, company.city.upper()[:12])
    c.setFillColorRGB(0, 0, 0)

    date_immat = company.registration_date
    date_extrait = fake.date_between(start_date="-3m", end_date="today")

    y = H - 55 * mm
    fields = [
        ("Dénomination", company.name),
        ("Forme juridique", company.forme_juridique),
        ("Capital social", f"{company.capital_social:,} €"),
        ("Siège social", f"{company.address}, {company.zip_code} {company.city}"),
        ("SIREN", company.siren),
        ("SIRET (siège)", company.siret),
        ("N° RCS", company.rcs),
        ("Date d'immatriculation", date_immat),
        ("Date de l'extrait", date_extrait.strftime("%d/%m/%Y")),
    ]

    for label, value in fields:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30 * mm, y, f"{label} :")
        c.setFont("Helvetica", 10)
        c.drawString(85 * mm, y, str(value))
        y -= 8 * mm

    c.save()

    return {
        "type": "kbis",
        "siret": company.siret,
        "siren": company.siren,
        "company_name": company.name,
        "rcs": company.rcs,
        "date_immatriculation": date_immat,
        "date_extrait": date_extrait.isoformat(),
    }


def generate_rib(company: CompanyIdentity, fake: Faker, filepath: str) -> dict:
    c = Canvas(filepath, pagesize=A4)

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, H - 30 * mm, "RELEVÉ D'IDENTITÉ BANCAIRE")

    y = H - 55 * mm
    iban_spaced = " ".join(company.iban[i:i + 4] for i in range(0, len(company.iban), 4))

    fields = [
        ("Titulaire", company.name),
        ("Banque", company.bank_name),
        ("IBAN", iban_spaced),
        ("BIC / SWIFT", company.bic),
    ]

    for label, value in fields:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(30 * mm, y, f"{label} :")
        c.setFont("Helvetica", 11)
        c.drawString(75 * mm, y, value)
        y -= 10 * mm

    c.setFont("Helvetica", 8)
    c.drawCentredString(W / 2, 20 * mm, "Ce document est confidentiel et destiné exclusivement au destinataire.")
    c.save()

    return {
        "type": "rib",
        "titulaire": company.name,
        "iban": company.iban,
        "bic": company.bic,
        "bank_name": company.bank_name,
    }
