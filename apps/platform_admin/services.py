from html import escape
from email.mime.image import MIMEImage
from urllib.parse import urljoin

from django.core.mail import EmailMultiAlternatives, get_connection
from django.contrib.staticfiles import finders

from apps.platform_admin.models import (
    CleanGoMailConfiguration,
    SubscriptionEmailLog,
)


def _configuration():
    return CleanGoMailConfiguration.objects.filter(actif=True).first()


def _connection(configuration):
    return get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=configuration.serveur_smtp,
        port=configuration.port_smtp,
        username=configuration.utilisateur_smtp,
        password=configuration.get_password(),
        use_tls=configuration.utiliser_tls,
        use_ssl=configuration.utiliser_ssl,
        timeout=20,
    )


def _recipients(company):
    values = [company.email_contact]
    values.extend(
        company.utilisateurs.filter(role__code="admin", statut="actif")
        .values_list("email", flat=True)
    )
    return list(dict.fromkeys(email.strip().lower() for email in values if email))


def _layout(title, intro, content, button_label, button_url, base_url):
    logo_url = "cid:cleango-logo"
    return f"""<!doctype html>
    <html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
    <body style="margin:0;background:#eef3f5;font-family:Arial,Helvetica,sans-serif;color:#142238">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:30px 12px">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#fff;border:1px solid #dce6e8">
          <tr><td style="height:7px;background:linear-gradient(90deg,#10a867,#ff7417)"></td></tr>
          <tr><td align="center" style="padding:30px 26px;background:#10243b">
            <img src="{escape(logo_url)}" width="76" height="76" alt="CleanGo" style="display:block;width:76px;height:76px;object-fit:contain;background:#fff;padding:8px;border-radius:18px">
            <div style="margin-top:13px;color:#fff;font-size:28px;font-weight:800;letter-spacing:-.5px">CleanGo</div>
            <div style="margin-top:5px;color:#9fdbbf;font-size:13px;letter-spacing:.5px">L’idée du lavage en un clic</div>
          </td></tr>
          <tr><td style="padding:36px 34px 30px">
            <div style="color:#10a867;font-size:11px;font-weight:800;letter-spacing:1.4px;text-align:center">VOTRE ABONNEMENT CLEANGO</div>
            <h1 style="margin:10px 0 12px;font-size:25px;line-height:1.3;text-align:center">{title}</h1>
            <p style="margin:0;color:#667386;font-size:15px;line-height:1.7;text-align:center">{intro}</p>
            {content}
            <table role="presentation" cellspacing="0" cellpadding="0" align="center"><tr><td style="background:#10a867">
              <a href="{escape(button_url)}" style="display:inline-block;padding:15px 27px;color:#fff;font-size:14px;font-weight:800;text-decoration:none">{button_label}&nbsp; →</a>
            </td></tr></table>
            <p style="margin:25px 0 0;color:#8994a2;font-size:11px;line-height:1.6;text-align:center">Besoin d’aide ? Répondez à cet email ou contactez l’équipe CleanGo.</p>
          </td></tr>
          <tr><td align="center" style="padding:22px;background:#10243b;color:#b8c7d2;font-size:11px;line-height:1.7"><strong style="color:#fff">CleanGo</strong><br>La solution simple pour piloter votre activité de lavage.<br><span style="color:#78cba5">L’idée du lavage en un clic</span></td></tr>
        </table>
      </td></tr></table>
    </body></html>"""


def _attach_logo(message):
    logo_path = finders.find("branding/cleango-logo.png")
    if not logo_path:
        return
    with open(logo_path, "rb") as logo_file:
        logo = MIMEImage(logo_file.read(), _subtype="png")
    logo.add_header("Content-ID", "<cleango-logo>")
    logo.add_header("Content-Disposition", "inline", filename="cleango-logo.png")
    message.attach(logo)


def send_expiration_reminder(company, end_date, base_url):
    reference = f"expiration:{company.pk}:{end_date.isoformat()}"
    if SubscriptionEmailLog.objects.filter(reference=reference).exists():
        return False
    configuration = _configuration()
    recipients = _recipients(company)
    if not configuration or not recipients:
        return False
    trial = company.statut_abonnement == "essai"
    type_label = "essai gratuit" if trial else "abonnement"
    from django.utils import timezone
    remaining_days = max((end_date - timezone.localdate()).days, 0)
    remaining_label = "aujourd’hui" if remaining_days == 0 else f"dans {remaining_days} jour{'s' if remaining_days > 1 else ''}"
    content = f"""
      <div style="margin:27px 0;padding:20px;background:#fff7ed;border-left:4px solid #ff7417;text-align:center">
        <div style="color:#8a5b31;font-size:12px">DATE DE FIN</div>
        <div style="margin-top:6px;color:#ff7417;font-size:24px;font-weight:800">{end_date.strftime("%d/%m/%Y")}</div>
        <div style="margin-top:6px;color:#75502f;font-size:13px">Votre accès expire {remaining_label}</div>
      </div>"""
    html = _layout(
        "Votre accès arrive bientôt à expiration",
        f"Bonjour, le {type_label} de <strong>{escape(company.raison_sociale)}</strong> arrive bientôt à expiration.",
        content,
        "Gérer mon abonnement",
        urljoin(base_url.rstrip("/") + "/", "configuration/?tab=subscription"),
        base_url,
    )
    message = EmailMultiAlternatives(
        subject=f"CleanGo – Votre {type_label} expire {remaining_label}",
        body=f"Votre {type_label} CleanGo se termine le {end_date:%d/%m/%Y}.",
        from_email=f"{configuration.nom_expediteur} <{configuration.email_expediteur}>",
        to=recipients,
        connection=_connection(configuration),
    )
    message.attach_alternative(html, "text/html")
    _attach_logo(message)
    message.send(fail_silently=False)
    SubscriptionEmailLog.objects.create(
        reference=reference, entreprise=company,
        type_notification="expiration", destinataires=", ".join(recipients),
    )
    return True


def send_payment_confirmation(payment, base_url, force=False):
    reference = f"paiement:{payment.pk}"
    already_logged = SubscriptionEmailLog.objects.filter(reference=reference).exists()
    if payment.statut != "paye" or (already_logged and not force):
        return False
    company = payment.entreprise
    configuration = _configuration()
    recipients = _recipients(company)
    if not configuration or not recipients:
        return False
    content = f"""
      <div style="margin:25px 0 15px;padding:14px 18px;border-radius:8px;color:#11643f;background:#e8f8f0;text-align:center;font-size:13px;font-weight:700">✓ ABONNEMENT ACTIF</div>
      <div style="margin:0 0 27px;background:#f7faf8;border:1px solid #d9ebe1;border-radius:10px;overflow:hidden">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
          <tr><td colspan="2" align="center" style="padding:18px;background:#10243b"><div style="color:#91a7b6;font-size:10px;letter-spacing:1px">RÉFÉRENCE DU RENOUVELLEMENT</div><div style="margin-top:6px;color:#fff;font-size:18px;font-weight:800;letter-spacing:.5px">{escape(payment.reference)}</div></td></tr>
          <tr><td style="padding:13px 18px;color:#718091;font-size:12px;border-bottom:1px solid #d9ebe1">PLAN</td><td align="right" style="padding:13px 18px;font-weight:700;border-bottom:1px solid #d9ebe1">{escape(payment.plan.nom)}</td></tr>
          <tr><td style="padding:13px 18px;color:#718091;font-size:12px;border-bottom:1px solid #d9ebe1">NOUVELLE DATE DE FIN</td><td align="right" style="padding:13px 18px;font-weight:700;border-bottom:1px solid #d9ebe1">{company.date_fin_abonnement.strftime("%d/%m/%Y") if company.date_fin_abonnement else "—"}</td></tr>
          <tr><td style="padding:17px 18px;color:#718091;font-size:12px">MONTANT PAYÉ</td><td align="right" style="padding:17px 18px;color:#10a867;font-size:22px;font-weight:800">{payment.montant:,.0f} {escape(payment.devise)}</td></tr>
        </table>
      </div>"""
    html = _layout(
        "Votre abonnement a été renouvelé",
        f"Merci <strong>{escape(company.raison_sociale)}</strong>. Votre renouvellement a bien été enregistré et votre accès est de nouveau actif.",
        content,
        "Accéder à mon espace",
        urljoin(base_url.rstrip("/") + "/", "dashboard/"),
        base_url,
    )
    message = EmailMultiAlternatives(
        subject=f"CleanGo – Abonnement renouvelé · {payment.reference}",
        body=f"Abonnement renouvelé jusqu’au {company.date_fin_abonnement:%d/%m/%Y}. Paiement : {payment.montant} {payment.devise}, référence {payment.reference}.",
        from_email=f"{configuration.nom_expediteur} <{configuration.email_expediteur}>",
        to=recipients,
        connection=_connection(configuration),
    )
    message.attach_alternative(html, "text/html")
    _attach_logo(message)
    message.send(fail_silently=False)
    if not already_logged:
        SubscriptionEmailLog.objects.create(reference=reference, entreprise=company, type_notification="paiement", destinataires=", ".join(recipients))
    return True
