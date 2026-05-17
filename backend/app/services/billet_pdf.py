"""Génère le PDF d'un billet de voyage (à joindre au mail de confirmation)."""
from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ORANGE = colors.HexColor("#D97757")
GREY_DARK = colors.HexColor("#1a1a1a")
GREY_MED = colors.HexColor("#666666")
GREY_LIGHT = colors.HexColor("#f5f5f4")
GREY_BORDER = colors.HexColor("#e7e5e4")


def build_billet_pdf(
    *,
    numero_billet: str,
    voyageur_nom: str,
    voyageur_prenom: str,
    trajet_type: str,
    depart: str,
    arrivee: str,
    date_depart: str,
    date_arrivee: str,
    compagnie: str,
    classe: str,
    prix_paye: float,
    siege: str | None = None,
) -> bytes:
    """Retourne le PDF du billet comme bytes."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Bandeau orange
    c.setFillColor(ORANGE)
    c.rect(0, height - 35 * mm, width, 35 * mm, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(20 * mm, height - 17 * mm, "Voyage Assistant")
    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, height - 25 * mm, "Votre billet de voyage")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 20 * mm, height - 17 * mm, f"Billet n° {numero_billet}")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 20 * mm, height - 23 * mm, "À présenter à l'embarquement")

    # Voyageur
    y = height - 50 * mm
    c.setFillColor(GREY_MED)
    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, y, "VOYAGEUR")
    c.setFillColor(GREY_DARK)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y - 6 * mm, f"{voyageur_prenom} {voyageur_nom}")

    # Trajet — bloc encadré
    y_box = y - 18 * mm
    box_h = 55 * mm
    c.setStrokeColor(GREY_BORDER)
    c.setFillColor(GREY_LIGHT)
    c.roundRect(15 * mm, y_box - box_h, width - 30 * mm, box_h, 4 * mm, fill=True, stroke=True)

    # Calcule une taille de police qui rentre dans la colonne disponible
    def _fit_font(text: str, max_width_mm: float, max_size: int = 16, min_size: int = 10) -> int:
        for size in range(max_size, min_size - 1, -1):
            if c.stringWidth(text, "Helvetica-Bold", size) <= max_width_mm * mm:
                return size
        return min_size

    # Largeur réservée à chaque colonne ville (la flèche centrale prend 30 mm)
    col_w = (width - 50 * mm - 30 * mm) / 2  # ~ (210-50-30)/2 = 65 mm chacun

    # Départ (gauche)
    c.setFillColor(GREY_MED)
    c.setFont("Helvetica", 8)
    c.drawString(25 * mm, y_box - 10 * mm, "DÉPART")
    size_dep = _fit_font(depart, col_w)
    c.setFillColor(GREY_DARK)
    c.setFont("Helvetica-Bold", size_dep)
    c.drawString(25 * mm, y_box - 20 * mm, depart)
    c.setFont("Helvetica", 10)
    c.drawString(25 * mm, y_box - 27 * mm, date_depart)

    # Flèche centrale (plus compacte : 24 mm de large)
    cx = width / 2
    c.setStrokeColor(ORANGE)
    c.setLineWidth(1.5)
    c.line(cx - 12 * mm, y_box - 23 * mm, cx + 12 * mm, y_box - 23 * mm)
    # pointe
    c.line(cx + 12 * mm, y_box - 23 * mm, cx + 8 * mm, y_box - 20 * mm)
    c.line(cx + 12 * mm, y_box - 23 * mm, cx + 8 * mm, y_box - 26 * mm)
    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(cx, y_box - 16 * mm, trajet_type.upper())

    # Arrivée (droite)
    c.setFillColor(GREY_MED)
    c.setFont("Helvetica", 8)
    c.drawRightString(width - 25 * mm, y_box - 10 * mm, "ARRIVÉE")
    size_arr = _fit_font(arrivee, col_w)
    c.setFillColor(GREY_DARK)
    c.setFont("Helvetica-Bold", size_arr)
    c.drawRightString(width - 25 * mm, y_box - 20 * mm, arrivee)
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 25 * mm, y_box - 27 * mm, date_arrivee)

    # Bas du bloc trajet
    c.setStrokeColor(GREY_BORDER)
    c.line(25 * mm, y_box - 35 * mm, width - 25 * mm, y_box - 35 * mm)
    c.setFillColor(GREY_MED)
    c.setFont("Helvetica", 8)
    col = 25 * mm
    for label, value in [
        ("COMPAGNIE", compagnie),
        ("CLASSE", classe),
        ("SIÈGE", siege or "Attribué à l'embarquement"),
        ("MONTANT", f"{prix_paye:.2f} EUR"),
    ]:
        c.setFillColor(GREY_MED)
        c.setFont("Helvetica", 7)
        c.drawString(col, y_box - 42 * mm, label)
        c.setFillColor(GREY_DARK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(col, y_box - 48 * mm, str(value))
        col += (width - 50 * mm) / 4

    # Footer
    c.setFillColor(GREY_BORDER)
    c.rect(0, 0, width, 12 * mm, fill=True, stroke=False)
    c.setFillColor(GREY_MED)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 5 * mm, "Voyage Assistant · Billet personnel et non cessible · Conservez ce document jusqu'à la fin du voyage")

    c.showPage()
    c.save()
    return buf.getvalue()
