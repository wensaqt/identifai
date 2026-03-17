from __future__ import annotations

from datetime import timedelta

from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from .company import CompanyIdentity

W, H = A4

_PRESTATIONS = [
    "Conseil en gestion", "Audit comptable", "Maintenance informatique",
    "Développement logiciel", "Formation professionnelle", "Prestation de nettoyage",
    "Livraison de fournitures", "Installation réseau", "Support technique",
    "Étude de marché", "Rédaction de contenu", "Design graphique",
    "Hébergement serveur", "Location de matériel", "Réparation équipement",
    "Transport de marchandises", "Consulting stratégique", "Mise en conformité",
    "Gestion de projet", "Analyse de données",
]


class _PdfHelper:

    @staticmethod
    def draw_header(c: Canvas, title: str, company: CompanyIdentity, y: float) -> float:
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

    @staticmethod
    def draw_footer(c: Canvas, company: CompanyIdentity) -> None:
        c.setFont("Helvetica", 7)
        c.drawCentredString(
            W / 2, 15 * mm,
            f"{company.name} — {company.forme_juridique} au capital de "
            f"{company.capital_social:,} € — {company.rcs}",
        )

    @staticmethod
    def draw_field_list(c: Canvas, fields: list[tuple[str, str]], y: float,
                        label_x: float = 30, value_x: float = 80) -> float:
        for label, value in fields:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(label_x * mm, y, f"{label} :")
            c.setFont("Helvetica", 10)
            c.drawString(value_x * mm, y, str(value))
            y -= 8 * mm
        return y

    @staticmethod
    def draw_items_table(c: Canvas, items: list[dict], y: float) -> tuple[float, float]:
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

    @staticmethod
    def draw_totals(c: Canvas, y: float, ht: float, tva_rate: float, tva_amount: float, ttc: float) -> float:
        c.line(130 * mm, y + 3 * mm, 185 * mm, y + 3 * mm)
        c.setFont("Helvetica", 10)
        c.drawString(130 * mm, y, f"Total HT :    {ht:.2f} €")
        y -= 5 * mm
        c.drawString(130 * mm, y, f"TVA {tva_rate*100:.0f}% :     {tva_amount:.2f} €")
        y -= 5 * mm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(130 * mm, y, f"Total TTC :   {ttc:.2f} €")
        return y

    @staticmethod
    def generate_line_items(fake: Faker) -> list[dict]:
        n = fake.random_int(3, 8)
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


class InvoiceFactory:

    def __init__(self, fake: Faker):
        self._fake = fake
        self._pdf = _PdfHelper()

    def create(self, company: CompanyIdentity, client: CompanyIdentity,
               filepath: str, *, tva_rate: float = 0.20,
               statut_paiement: str = "unpaid",
               reference_paiement: str | None = None,
               override_tva: float | None = None) -> dict:
        c = Canvas(filepath, pagesize=A4)
        date_emission = self._fake.date_between(start_date="-1y", end_date="today")
        date_prestation = self._fake.date_between(
            start_date=date_emission - timedelta(days=30), end_date=date_emission)
        numero = f"F-{date_emission.year}-{self._fake.unique.random_int(1, 9999):04d}"

        y = self._pdf.draw_header(c, "FACTURE", company, H - 20 * mm)
        y = self._draw_invoice_header(c, y, numero, date_emission, date_prestation, client)
        y, total_ht = self._draw_line_items(c, y)

        tva_amount = override_tva if override_tva is not None else round(total_ht * tva_rate, 2)
        total_ttc = round(total_ht + tva_amount, 2)

        y -= 8 * mm
        y = self._pdf.draw_totals(c, y, total_ht, tva_rate, tva_amount, total_ttc)
        self._draw_payment_info(c, y, statut_paiement, reference_paiement, company)
        self._pdf.draw_footer(c, company)
        c.save()

        return {
            "type": "invoice", "invoice_id": numero,
            "siret_emetteur": company.siret, "nom_emetteur": company.name,
            "nom_client": client.name, "date_emission": date_emission.isoformat(),
            "date_prestation": date_prestation.isoformat(),
            "montant_ht": total_ht, "tva_rate": tva_rate,
            "montant_tva": tva_amount, "montant_ttc": total_ttc,
            "statut_paiement": statut_paiement,
            "reference_paiement": reference_paiement,
        }

    def _draw_invoice_header(self, c, y, numero, date_emission, date_prestation, client):
        y -= 8 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30 * mm, y, f"N° {numero}")
        c.drawString(120 * mm, y, "Client :")
        y -= 5 * mm
        c.setFont("Helvetica", 9)
        c.drawString(30 * mm, y, f"Date : {date_emission.strftime('%d/%m/%Y')}")
        c.drawString(120 * mm, y, client.name)
        y -= 5 * mm
        c.drawString(30 * mm, y, f"Prestation : {date_prestation.strftime('%d/%m/%Y')}")
        c.drawString(120 * mm, y, client.address)
        y -= 5 * mm
        c.drawString(120 * mm, y, f"{client.zip_code} {client.city}")
        y -= 5 * mm
        c.drawString(120 * mm, y, f"SIRET : {client.siret}")
        return y

    def _draw_line_items(self, c, y):
        y -= 15 * mm
        items = self._pdf.generate_line_items(self._fake)
        return self._pdf.draw_items_table(c, items, y)

    def _draw_payment_info(self, c, y, statut, ref, company):
        y -= 10 * mm
        c.setFont("Helvetica", 9)
        c.drawString(30 * mm, y, f"Statut : {statut.upper()}")
        if ref:
            y -= 5 * mm
            c.drawString(30 * mm, y, f"Réf. paiement : {ref}")
        y -= 10 * mm
        c.setFont("Helvetica", 8)
        c.drawString(30 * mm, y, f"Règlement par virement — IBAN : {company.iban}  BIC : {company.bic}")


class DevisFactory:

    def __init__(self, fake: Faker):
        self._fake = fake
        self._pdf = _PdfHelper()

    def create(self, company: CompanyIdentity, client: CompanyIdentity, filepath: str) -> dict:
        c = Canvas(filepath, pagesize=A4)
        date_emission = self._fake.date_between(start_date="-1y", end_date="today")
        date_validite = date_emission + timedelta(days=30)
        numero = f"D-{date_emission.year}-{self._fake.unique.random_int(1, 9999):04d}"

        y = self._pdf.draw_header(c, "DEVIS", company, H - 20 * mm)
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
        items = self._pdf.generate_line_items(self._fake)
        y, total_ht = self._pdf.draw_items_table(c, items, y)
        tva_amount = round(total_ht * 0.20, 2)
        total_ttc = round(total_ht + tva_amount, 2)

        y -= 8 * mm
        self._pdf.draw_totals(c, y, total_ht, 0.20, tva_amount, total_ttc)
        self._pdf.draw_footer(c, company)
        c.save()

        return {
            "type": "devis", "numero": numero,
            "siret_emetteur": company.siret, "siret_client": client.siret,
            "tva": company.tva, "montant_ht": total_ht, "montant_ttc": total_ttc,
            "date_emission": date_emission.isoformat(),
            "date_validite": date_validite.isoformat(),
        }


class AttestationSiretFactory:

    def __init__(self, fake: Faker):
        self._fake = fake
        self._pdf = _PdfHelper()

    def create(self, company: CompanyIdentity, filepath: str) -> dict:
        c = Canvas(filepath, pagesize=A4)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(W / 2, H - 30 * mm, "AVIS DE SITUATION AU RÉPERTOIRE SIRENE")
        c.setFont("Helvetica", 9)
        c.drawCentredString(W / 2, H - 38 * mm,
                            "Institut National de la Statistique et des Études Économiques")

        fields = [
            ("Dénomination", company.name), ("Forme juridique", company.forme_juridique),
            ("SIREN", company.siren), ("NIC", company.siret[9:]),
            ("SIRET", company.siret),
            ("Adresse", f"{company.address}, {company.zip_code} {company.city}"),
            ("Date d'inscription", company.registration_date),
        ]
        self._pdf.draw_field_list(c, fields, H - 60 * mm)

        c.setFont("Helvetica", 8)
        c.drawCentredString(W / 2, 20 * mm, "Document à caractère informatif, ne constitue pas une preuve juridique.")
        c.save()

        return {
            "type": "attestation_siret", "siret": company.siret,
            "siren": company.siren, "company_name": company.name,
            "date_inscription": company.registration_date,
        }


class AttestationUrssafFactory:

    def __init__(self, fake: Faker):
        self._fake = fake

    def _draw_urssaf_body(self, c: Canvas, company: CompanyIdentity,
                          date_delivrance, date_fin) -> None:
        c.setFillColorRGB(0.0, 0.2, 0.6)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(30 * mm, H - 30 * mm, "URSSAF")
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(W / 2, H - 50 * mm, "ATTESTATION DE VIGILANCE")

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

    def create(self, company: CompanyIdentity, filepath: str) -> dict:
        date_delivrance = self._fake.date_between(start_date="-6m", end_date="today")
        date_fin = date_delivrance + timedelta(days=180)
        c = Canvas(filepath, pagesize=A4)
        self._draw_urssaf_body(c, company, date_delivrance, date_fin)
        c.save()
        return {
            "type": "attestation_urssaf", "siret": company.siret,
            "company_name": company.name,
            "date_delivrance": date_delivrance.isoformat(),
            "date_expiration": date_fin.isoformat(),
        }

    def create_expired(self, company: CompanyIdentity, filepath: str) -> dict:
        date_delivrance = self._fake.date_between(start_date="-5y", end_date="-4y")
        date_fin = date_delivrance + timedelta(days=180)
        c = Canvas(filepath, pagesize=A4)
        self._draw_urssaf_body(c, company, date_delivrance, date_fin)
        c.save()
        return {
            "type": "attestation_urssaf", "siret": company.siret,
            "company_name": company.name,
            "date_delivrance": date_delivrance.isoformat(),
            "date_expiration": date_fin.isoformat(),
            "expired": True,
        }


class KbisFactory:

    def __init__(self, fake: Faker):
        self._fake = fake
        self._pdf = _PdfHelper()

    def create(self, company: CompanyIdentity, filepath: str) -> dict:
        c = Canvas(filepath, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(W / 2, H - 25 * mm, "EXTRAIT K BIS")
        c.setFont("Helvetica", 9)
        c.drawCentredString(W / 2, H - 32 * mm,
                            f"Greffe du Tribunal de Commerce de {company.city}")
        self._draw_stamp(c, company)

        date_extrait = self._fake.date_between(start_date="-3m", end_date="today")
        fields = [
            ("Dénomination", company.name), ("Forme juridique", company.forme_juridique),
            ("Capital social", f"{company.capital_social:,} €"),
            ("Siège social", f"{company.address}, {company.zip_code} {company.city}"),
            ("SIREN", company.siren), ("SIRET (siège)", company.siret),
            ("N° RCS", company.rcs),
            ("Date d'immatriculation", company.registration_date),
            ("Date de l'extrait", date_extrait.strftime("%d/%m/%Y")),
        ]
        self._pdf.draw_field_list(c, fields, H - 55 * mm, label_x=30, value_x=85)
        c.save()

        return {
            "type": "kbis", "siret": company.siret, "siren": company.siren,
            "company_name": company.name, "rcs": company.rcs,
            "date_immatriculation": company.registration_date,
            "date_extrait": date_extrait.isoformat(),
        }

    @staticmethod
    def _draw_stamp(c: Canvas, company: CompanyIdentity) -> None:
        c.setStrokeColorRGB(0.3, 0.3, 0.8)
        c.setLineWidth(2)
        c.circle(160 * mm, H - 55 * mm, 15 * mm, fill=0)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColorRGB(0.3, 0.3, 0.8)
        c.drawCentredString(160 * mm, H - 54 * mm, "GREFFE")
        c.drawCentredString(160 * mm, H - 58 * mm, company.city.upper()[:12])
        c.setFillColorRGB(0, 0, 0)


class RibFactory:

    def __init__(self, fake: Faker):
        self._fake = fake

    def create(self, company: CompanyIdentity, filepath: str) -> dict:
        c = Canvas(filepath, pagesize=A4)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(W / 2, H - 30 * mm, "RELEVÉ D'IDENTITÉ BANCAIRE")

        iban_spaced = " ".join(company.iban[i:i + 4] for i in range(0, len(company.iban), 4))
        y = H - 55 * mm
        for label, value in [("Titulaire", company.name), ("Banque", company.bank_name),
                              ("IBAN", iban_spaced), ("BIC / SWIFT", company.bic)]:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(30 * mm, y, f"{label} :")
            c.setFont("Helvetica", 11)
            c.drawString(75 * mm, y, value)
            y -= 10 * mm

        c.setFont("Helvetica", 8)
        c.drawCentredString(W / 2, 20 * mm, "Ce document est confidentiel et destiné exclusivement au destinataire.")
        c.save()

        return {
            "type": "rib", "titulaire": company.name,
            "iban": company.iban, "bic": company.bic, "bank_name": company.bank_name,
        }


class PaymentFactory:

    def __init__(self, fake: Faker):
        self._fake = fake
        self._pdf = _PdfHelper()

    def create(self, company: CompanyIdentity, client: CompanyIdentity,
               filepath: str, *, invoice_id: str | None = None,
               montant: float | None = None) -> dict:
        date_paiement = self._fake.date_between(start_date="-6m", end_date="today")
        payment_id = f"PAY-{date_paiement.year}-{self._fake.unique.random_int(1, 9999):04d}"
        montant = montant or round(self._fake.pyfloat(min_value=100, max_value=50000, right_digits=2), 2)
        methode = self._fake.random_element(["virement", "prélèvement", "chèque", "carte bancaire"])

        c = Canvas(filepath, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(W / 2, H - 25 * mm, "CONFIRMATION DE PAIEMENT")

        fields = [
            ("Référence", payment_id),
            ("Date", date_paiement.strftime("%d/%m/%Y")),
            ("Émetteur", f"{client.name} (SIRET {client.siret})"),
            ("Destinataire", f"{company.name} (SIRET {company.siret})"),
            ("Montant", f"{montant:.2f} €"),
            ("Méthode", methode),
        ]
        if invoice_id:
            fields.append(("Réf. facture", invoice_id))

        self._pdf.draw_field_list(c, fields, H - 50 * mm)
        c.save()

        return {
            "type": "payment", "payment_id": payment_id,
            "date_paiement": date_paiement.isoformat(), "montant": montant,
            "emetteur": client.name, "destinataire": company.name,
            "reference_facture": invoice_id, "methode": methode,
        }


class UrssafDeclarationFactory:

    def __init__(self, fake: Faker):
        self._fake = fake
        self._pdf = _PdfHelper()

    def create(self, company: CompanyIdentity, filepath: str, *,
               chiffre_affaires: float | None = None) -> dict:
        year = self._fake.date_between(start_date="-1y", end_date="today").year
        trimestre = self._fake.random_element([1, 2, 3, 4])
        periode = f"{year}-T{trimestre}"
        date_declaration = self._fake.date_between(start_date="-3m", end_date="today")
        ca = chiffre_affaires or round(self._fake.pyfloat(min_value=5000, max_value=200000, right_digits=2), 2)

        c = Canvas(filepath, pagesize=A4)
        c.setFillColorRGB(0.0, 0.2, 0.6)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(30 * mm, H - 30 * mm, "URSSAF")
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(W / 2, H - 50 * mm, "DÉCLARATION DE CHIFFRE D'AFFAIRES")

        fields = [
            ("Entreprise", f"{company.name} — {company.forme_juridique}"),
            ("SIRET", company.siret), ("Période", periode),
            ("Chiffre d'affaires déclaré", f"{ca:,.2f} €"),
            ("Date de déclaration", date_declaration.strftime("%d/%m/%Y")),
        ]
        self._pdf.draw_field_list(c, fields, H - 70 * mm, label_x=30, value_x=90)
        c.save()

        return {
            "type": "urssaf_declaration", "periode": periode,
            "chiffre_affaires_declare": ca,
            "date_declaration": date_declaration.isoformat(),
            "siret": company.siret,
        }
