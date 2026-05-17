from __future__ import annotations

import base64
import logging
from typing import Optional

from app.config import settings
from app.services.billet_pdf import build_billet_pdf

logger = logging.getLogger(__name__)


def _build_confirmation_html(
    *,
    to_name: str,
    numero_billet: str,
    trajet_resume: str,
    chatbot_url: str,
    montant: str | None = None,
    classe: str | None = None,
) -> str:
    montant_row = f"""
    <tr><td style="padding:6px 0;color:#666;font-size:13px;">Montant payé</td>
        <td style="padding:6px 0;color:#1a1a1a;font-size:14px;font-weight:600;text-align:right;">{montant}</td></tr>""" if montant else ""
    classe_row = f"""
    <tr><td style="padding:6px 0;color:#666;font-size:13px;">Classe</td>
        <td style="padding:6px 0;color:#1a1a1a;font-size:14px;font-weight:600;text-align:right;">{classe}</td></tr>""" if classe else ""

    return f"""<!doctype html>
<html lang="fr">
<head><meta charset="utf-8"><title>Votre billet</title></head>
<body style="margin:0;padding:0;background:#f5f5f4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#1a1a1a;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f5f5f4;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
             style="max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #e7e5e4;">

        <!-- Bandeau orange -->
        <tr><td style="background:#D97757;padding:32px 32px 28px;color:#ffffff;">
          <div style="font-size:22px;font-weight:700;letter-spacing:-0.01em;">Voyage Assistant</div>
          <div style="margin-top:4px;font-size:14px;opacity:0.95;">Confirmation de réservation</div>
        </td></tr>

        <!-- Corps -->
        <tr><td style="padding:32px;">
          <h1 style="margin:0 0 12px;font-size:22px;font-weight:700;letter-spacing:-0.01em;color:#1a1a1a;">
            Bon voyage, {to_name}.
          </h1>
          <p style="margin:0 0 24px;color:#555;font-size:15px;line-height:1.55;">
            Votre billet est confirmé. Vous le trouverez en pièce jointe de cet email,
            prêt à présenter à l'embarquement.
          </p>

          <!-- Carte récap -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
                 style="background:#f9f7f5;border:1px solid #e7e5e4;border-radius:12px;margin-bottom:24px;">
            <tr><td style="padding:20px 22px;">
              <div style="color:#666;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">
                Numéro de billet
              </div>
              <div style="color:#D97757;font-size:22px;font-weight:700;letter-spacing:0.02em;font-family:'SF Mono',Menlo,monospace;">
                {numero_billet}
              </div>
              <div style="margin-top:14px;color:#1a1a1a;font-size:14px;line-height:1.55;">
                {trajet_resume}
              </div>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:14px;">
                {classe_row}
                {montant_row}
              </table>
            </td></tr>
          </table>

          <!-- Bloc assistant -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
                 style="background:#fff;border:1px solid #e7e5e4;border-left:3px solid #D97757;border-radius:8px;margin-bottom:24px;">
            <tr><td style="padding:18px 20px;">
              <div style="font-size:14px;font-weight:600;color:#1a1a1a;margin-bottom:6px;">
                Besoin d'aide pour ce voyage&nbsp;?
              </div>
              <div style="font-size:13.5px;color:#555;line-height:1.55;margin-bottom:12px;">
                Notre assistant Voyage répond 24/7. Communiquez-lui le numéro de billet
                <strong style="color:#1a1a1a;">{numero_billet}</strong> pour modifier votre réservation,
                signaler un retard ou ouvrir une réclamation.
              </div>
              <a href="{chatbot_url}"
                 style="display:inline-block;padding:10px 18px;background:#D97757;color:#ffffff;
                        text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;">
                Parler à l'assistant
              </a>
            </td></tr>
          </table>

          <p style="margin:0;color:#888;font-size:12.5px;line-height:1.55;">
            Document personnel et non cessible · Conservez-le jusqu'à la fin de votre voyage.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#fafaf9;padding:20px 32px;border-top:1px solid #e7e5e4;
                       color:#888;font-size:12px;text-align:center;">
          Voyage Assistant · Avion · Train · Bateau · Bus longue distance<br/>
          <span style="color:#aaa;">Vous recevez cet email suite à une réservation effectuée sur notre plateforme.</span>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_confirmation_email(
    to_email: str,
    to_name: str,
    numero_billet: str,
    trajet_resume: str,
    chatbot_url: str,
    *,
    pdf_bytes: Optional[bytes] = None,
    montant: Optional[str] = None,
    classe: Optional[str] = None,
) -> bool:
    """Envoie l'email de confirmation via Brevo, avec PDF du billet en pièce jointe."""
    subject = f"Votre billet Voyage Assistant — {numero_billet}"
    html = _build_confirmation_html(
        to_name=to_name,
        numero_billet=numero_billet,
        trajet_resume=trajet_resume,
        chatbot_url=chatbot_url,
        montant=montant,
        classe=classe,
    )
    body_text = (
        f"Bonjour {to_name},\n\n"
        f"Votre billet est confirmé.\n\n"
        f"Numéro de billet : {numero_billet}\n"
        f"Trajet : {trajet_resume}\n\n"
        f"Le billet en PDF est joint à ce message.\n\n"
        f"Pour toute question, communiquez le numéro de billet à notre assistant 24/7 :\n"
        f"{chatbot_url}\n\n"
        f"Bon voyage,\nVoyage Assistant"
    )

    if not settings.brevo_api_key or not settings.brevo_sender_email:
        logger.info("[MAIL stub - Brevo non configuré] To=%s Subject=%s", to_email, subject)
        return True

    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException
    except ImportError:
        logger.warning("sib_api_v3_sdk non installé, fallback log only")
        return True

    config = sib_api_v3_sdk.Configuration()
    config.api_key["api-key"] = settings.brevo_api_key
    client = sib_api_v3_sdk.ApiClient(config)
    api = sib_api_v3_sdk.TransactionalEmailsApi(client)

    payload = dict(
        sender={"email": settings.brevo_sender_email, "name": settings.brevo_sender_name},
        to=[{"email": to_email, "name": to_name}],
        subject=subject,
        html_content=html,
        text_content=body_text,
    )
    if pdf_bytes:
        payload["attachment"] = [{
            "content": base64.b64encode(pdf_bytes).decode("ascii"),
            "name": f"billet-{numero_billet}.pdf",
        }]

    send = sib_api_v3_sdk.SendSmtpEmail(**payload)

    try:
        api.send_transac_email(send)
        return True
    except ApiException as exc:
        logger.error("Brevo send failed: %s", exc)
        return False


def send_reclamation_email(
    to_email: str,
    to_name: str,
    numero_suivi: str,
    type_reclamation: str,
) -> bool:
    subject = f"Votre réclamation {numero_suivi} a bien été enregistrée"
    body_text = (
        f"Bonjour {to_name},\n\n"
        f"Votre réclamation de type '{type_reclamation}' a été enregistrée sous le numéro "
        f"{numero_suivi}.\n\nNotre équipe vous répondra sous 72h.\n\nVoyage Assistant"
    )

    if not settings.brevo_api_key:
        logger.info("[MAIL stub] To=%s Subject=%s", to_email, subject)
        return True

    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException
    except ImportError:
        return True

    config = sib_api_v3_sdk.Configuration()
    config.api_key["api-key"] = settings.brevo_api_key
    client = sib_api_v3_sdk.ApiClient(config)
    api = sib_api_v3_sdk.TransactionalEmailsApi(client)

    send = sib_api_v3_sdk.SendSmtpEmail(
        sender={"email": settings.brevo_sender_email, "name": settings.brevo_sender_name},
        to=[{"email": to_email, "name": to_name}],
        subject=subject,
        text_content=body_text,
    )

    try:
        api.send_transac_email(send)
        return True
    except ApiException as exc:
        logger.error("Brevo send failed: %s", exc)
        return False
