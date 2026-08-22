import calendar
import secrets
from datetime import date, timedelta

from django.contrib import messages
from django.core.mail import EmailMessage, EmailMultiAlternatives, get_connection
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.templatetags.static import static
from django.utils import timezone
from django.utils.html import escape

from apps.authentication.models import User
from apps.entreprises.models import Entreprise, VisitorEvent
from apps.plan.models import PaiementAbonnement, Plan
from apps.roles.models import Role

from .forms import (
    EnterpriseCreationForm,
    PlanForm,
    PlatformMailConfigurationForm,
    SubscriptionActivationForm,
)
from .models import CleanGoAdmin, CleanGoMailConfiguration
from .services import send_payment_confirmation


def _connected_admin(request):
    return CleanGoAdmin.objects.filter(
        pk=request.session.get("platform_admin_id"),
        statut="actif",
    ).first()


def _guard(request):
    admin = _connected_admin(request)
    if admin is None:
        messages.error(request, "Accès réservé à l’administration CleanGo.")
        return None, redirect("platform_admin:login")
    return admin, None


def admin_login(request):
    if _connected_admin(request):
        return redirect("platform_admin:dashboard")
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        user = CleanGoAdmin.objects.filter(
            email__iexact=email,
            statut="actif",
        ).first()
        if user and user.check_password(password):
            request.session.flush()
            request.session["platform_admin_id"] = user.pk
            request.session.set_expiry(60 * 60 * 12)
            user.derniere_connexion = timezone.now()
            user.save(update_fields=["derniere_connexion", "updated_at"])
            return redirect("platform_admin:dashboard")
        messages.error(request, "Email ou mot de passe administrateur incorrect.")
    return render(request, "platform_admin/login.html")


def admin_logout(request):
    request.session.flush()
    messages.success(request, "Vous êtes déconnecté de l’administration CleanGo.")
    return redirect("platform_admin:login")


def _add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _context(admin):
    return {"platform_admin": admin, "today": timezone.localdate()}


def _platform_mail_connection(configuration):
    return get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=configuration.serveur_smtp,
        port=configuration.port_smtp,
        username=configuration.utilisateur_smtp,
        password=configuration.get_password(),
        use_tls=configuration.utiliser_tls,
        use_ssl=configuration.utiliser_ssl,
        timeout=15,
    )


def _send_enterprise_credentials(configuration, user, raw_password, login_url, logo_url):
    company_name = user.entreprise.raison_sociale
    safe_company_name = escape(company_name)
    safe_user_name = escape(user.nom)
    safe_email = escape(user.email)
    safe_password = escape(raw_password)
    safe_login_url = escape(login_url)
    safe_logo_url = escape(logo_url)
    text = (
        f"Bonjour {user.nom},\n\nVotre compte CleanGo pour {company_name} est prêt.\n"
        f"Email : {user.email}\nMot de passe provisoire : {raw_password}\n"
        f"Connexion : {login_url}\n\nChangez votre mot de passe après votre première connexion."
    )
    html = f"""<!doctype html>
    <html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
    <body style="margin:0;padding:0;background:#eef3f5;font-family:Arial,Helvetica,sans-serif;color:#142238">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef3f5">
        <tr><td align="center" style="padding:32px 12px">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#ffffff;border:1px solid #dce6e8">
            <tr><td style="height:7px;background:linear-gradient(90deg,#ff7417 0 48%,#10a867 52% 100%)"></td></tr>
            <tr><td align="center" style="padding:28px 24px 22px;background:#10243b">
              <img src="{safe_logo_url}" width="76" height="76" alt="CleanGo" style="display:block;width:76px;height:76px;object-fit:contain;background:#ffffff;padding:7px">
              <div style="margin-top:13px;color:#ffffff;font-size:27px;font-weight:800;letter-spacing:.3px">CleanGo</div>
              <div style="margin-top:5px;color:#9fdbbf;font-size:13px">L’idée du lavage en un clic</div>
            </td></tr>
            <tr><td style="padding:36px 34px 30px">
              <div style="color:#10a867;font-size:11px;font-weight:800;letter-spacing:1.5px;text-align:center">BIENVENUE SUR CLEANGO</div>
              <h1 style="margin:10px 0 12px;color:#142238;font-size:25px;line-height:1.3;text-align:center">Votre espace entreprise est prêt !</h1>
              <p style="margin:0;color:#667386;font-size:15px;line-height:1.7;text-align:center">Bonjour <strong style="color:#142238">{safe_user_name}</strong>, le compte administrateur de <strong style="color:#142238">{safe_company_name}</strong> vient d’être créé.</p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:27px 0;background:#f6f9fa;border:1px solid #dfe8eb">
                <tr><td style="padding:17px 20px;border-bottom:1px solid #dfe8eb;color:#718091;font-size:12px">EMAIL DE CONNEXION</td></tr>
                <tr><td style="padding:0 20px 17px;color:#142238;font-size:15px;font-weight:700;word-break:break-all">{safe_email}</td></tr>
                <tr><td style="padding:17px 20px 7px;border-top:1px solid #dfe8eb;color:#718091;font-size:12px">MOT DE PASSE PROVISOIRE</td></tr>
                <tr><td style="padding:0 20px 18px;color:#ff7417;font-family:Consolas,monospace;font-size:19px;font-weight:800;letter-spacing:.5px">{safe_password}</td></tr>
              </table>
              <table role="presentation" cellspacing="0" cellpadding="0" align="center"><tr><td style="background:#10a867">
                <a href="{safe_login_url}" style="display:inline-block;padding:15px 27px;color:#ffffff;font-size:14px;font-weight:800;text-decoration:none">Accéder à mon espace&nbsp; →</a>
              </td></tr></table>
              <div style="margin-top:27px;padding:15px 17px;background:#fff7ed;border-left:4px solid #ff7417;color:#75502f;font-size:12px;line-height:1.6">
                <strong>Conseil de sécurité :</strong> changez ce mot de passe dès votre première connexion et ne le communiquez à personne.
              </div>
              <p style="margin:25px 0 6px;color:#8994a2;font-size:11px;text-align:center">Si le bouton ne fonctionne pas, copiez ce lien :</p>
              <p style="margin:0;color:#10a867;font-size:11px;text-align:center;word-break:break-all"><a href="{safe_login_url}" style="color:#10a867">{safe_login_url}</a></p>
            </td></tr>
            <tr><td align="center" style="padding:20px;background:#f7f9fa;border-top:1px solid #e3eaed;color:#8792a0;font-size:11px;line-height:1.6">
              Cet email a été envoyé automatiquement par CleanGo.<br>La solution simple pour piloter votre activité de lavage.
            </td></tr>
          </table>
        </td></tr>
      </table>
    </body></html>"""
    message = EmailMultiAlternatives(
        subject=f"Votre compte entreprise CleanGo – {company_name}",
        body=text,
        from_email=f"{configuration.nom_expediteur} <{configuration.email_expediteur}>",
        to=[user.email],
        connection=_platform_mail_connection(configuration),
    )
    message.attach_alternative(html, "text/html")
    message.send(fail_silently=False)


def dashboard(request):
    admin, denied = _guard(request)
    if denied:
        return denied
    today = timezone.localdate()
    query = request.GET.get("q", "").strip()
    status = request.GET.get("statut", "").strip()
    companies = Entreprise.objects.select_related("plan").all()
    if query:
        companies = companies.filter(
            Q(raison_sociale__icontains=query)
            | Q(email_contact__icontains=query)
            | Q(telephone_contact__icontains=query)
        )
    if status:
        companies = companies.filter(statut_abonnement=status)
    companies = companies.order_by("-created_at")
    all_companies = Entreprise.objects.all()
    active = all_companies.filter(
        statut_abonnement="actif",
        date_fin_abonnement__gte=today,
    )
    expiring = active.filter(date_fin_abonnement__lte=today + timedelta(days=30))
    payments = PaiementAbonnement.objects.select_related("entreprise", "plan")
    context = _context(admin)
    context.update({
        "companies": companies,
        "query": query,
        "selected_status": status,
        "stats": {
            "total": all_companies.count(),
            "active": active.count(),
            "trial": all_companies.filter(statut_abonnement="essai").count(),
            "suspended": all_companies.filter(statut_abonnement="suspendu").count(),
            "expiring": expiring.count(),
            "revenue": payments.filter(statut="paye").aggregate(total=Sum("montant"))["total"] or 0,
        },
        "recent_payments": payments[:8],
        "expiring_companies": expiring.order_by("date_fin_abonnement")[:6],
    })
    return render(request, "platform_admin/dashboard.html", context)


def visitor_analytics(request):
    admin, denied = _guard(request)
    if denied:
        return denied
    events = VisitorEvent.objects.select_related("entreprise")
    event_filter = request.GET.get("event", "").strip()
    query = request.GET.get("q", "").strip()
    if event_filter in dict(VisitorEvent.EVENT_TYPES):
        events = events.filter(event_type=event_filter)
    if query:
        events = events.filter(
            Q(visitor_id__icontains=query) | Q(ip_address__icontains=query)
            | Q(search_query__icontains=query) | Q(locality__icontains=query)
            | Q(entreprise__raison_sociale__icontains=query)
        )
    today = timezone.localdate()
    all_events = VisitorEvent.objects.all()
    today_events = all_events.filter(created_at__date=today)
    stats = {
        "visitors": all_events.values("visitor_id").distinct().count(),
        "visitors_today": today_events.values("visitor_id").distinct().count(),
        "page_views": all_events.filter(event_type="page_view").count(),
        "searches": all_events.filter(event_type="search").count(),
        "gps": all_events.filter(event_type="geolocation_success").count(),
        "interest": all_events.filter(event_type__in=("company_view", "catalog_view", "route_request")).count(),
    }
    top_searches = all_events.filter(event_type="search").exclude(search_query="").values("search_query").annotate(total=Count("id")).order_by("-total")[:8]
    top_companies = all_events.filter(entreprise__isnull=False, event_type__in=("company_view", "catalog_view", "route_request")).values("entreprise__raison_sociale").annotate(total=Count("id")).order_by("-total")[:8]
    page = Paginator(events, 40).get_page(request.GET.get("page"))
    return render(request, "platform_admin/visitor_analytics.html", {
        "platform_admin": admin,
        "stats": stats,
        "events": page,
        "event_types": VisitorEvent.EVENT_TYPES,
        "selected_event": event_filter,
        "query": query,
        "top_searches": top_searches,
        "top_companies": top_companies,
    })


def plan_list(request):
    admin, denied = _guard(request)
    if denied:
        return denied
    context = _context(admin)
    context["plans"] = Plan.objects.annotate(
        nombre_entreprises=Count("entreprises"),
    ).order_by("prix_mensuel", "nom")
    return render(request, "platform_admin/plan_list.html", context)


@transaction.atomic
def plan_create(request):
    admin, denied = _guard(request)
    if denied:
        return denied
    form = PlanForm(request.POST or None, initial={"devise": "XOF", "duree_essai_jours": 8, "actif": True})
    if request.method == "POST" and form.is_valid():
        plan = form.save()
        messages.success(request, f"Le plan {plan.nom} a été créé.")
        return redirect("platform_admin:plan_list")
    context = _context(admin)
    context.update({"form": form, "editing": False})
    return render(request, "platform_admin/plan_form.html", context)


@transaction.atomic
def plan_edit(request, pk):
    admin, denied = _guard(request)
    if denied:
        return denied
    plan = get_object_or_404(Plan, pk=pk)
    form = PlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Le plan {plan.nom} a été mis à jour.")
        return redirect("platform_admin:plan_list")
    context = _context(admin)
    context.update({"form": form, "editing": True, "plan": plan})
    return render(request, "platform_admin/plan_form.html", context)


def plan_toggle(request, pk):
    admin, denied = _guard(request)
    if denied:
        return denied
    plan = get_object_or_404(Plan, pk=pk)
    if request.method == "POST":
        plan.actif = not plan.actif
        plan.save(update_fields=["actif", "updated_at"])
        state = "activé" if plan.actif else "désactivé"
        messages.success(request, f"Le plan {plan.nom} a été {state}.")
    return redirect("platform_admin:plan_list")


@transaction.atomic
def mail_configuration(request):
    admin, denied = _guard(request)
    if denied:
        return denied
    configuration = CleanGoMailConfiguration.objects.first()
    form = PlatformMailConfigurationForm(request.POST or None, instance=configuration)
    if request.method == "POST" and form.is_valid():
        configuration = form.save(commit=False)
        configuration.set_password(form.cleaned_data.get("mot_de_passe"))
        configuration.save()
        messages.success(request, "La configuration email CleanGo a été enregistrée.")
        return redirect("platform_admin:mail_configuration")
    context = _context(admin)
    context.update({"form": form, "mail_configuration": configuration})
    return render(request, "platform_admin/mail_configuration.html", context)


def test_mail_configuration(request):
    admin, denied = _guard(request)
    if denied:
        return denied
    if request.method != "POST":
        return redirect("platform_admin:mail_configuration")
    configuration = CleanGoMailConfiguration.objects.filter(actif=True).first()
    recipient = request.POST.get("email_test", "").strip()
    if not configuration:
        messages.error(request, "Enregistrez et activez d’abord la configuration email.")
        return redirect("platform_admin:mail_configuration")
    if not recipient:
        messages.error(request, "Indiquez une adresse pour l’email de test.")
        return redirect("platform_admin:mail_configuration")
    try:
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=configuration.serveur_smtp,
            port=configuration.port_smtp,
            username=configuration.utilisateur_smtp,
            password=configuration.get_password(),
            use_tls=configuration.utiliser_tls,
            use_ssl=configuration.utiliser_ssl,
            timeout=15,
        )
        message = EmailMessage(
            subject="Test de configuration email CleanGo",
            body="Votre configuration SMTP CleanGo fonctionne correctement.",
            from_email=f"{configuration.nom_expediteur} <{configuration.email_expediteur}>",
            to=[recipient],
            connection=connection,
        )
        message.send(fail_silently=False)
        messages.success(request, f"Email de test envoyé à {recipient}.")
    except Exception as exc:
        messages.error(request, f"Échec de l’envoi : {exc}")
    return redirect("platform_admin:mail_configuration")


def create_enterprise(request):
    admin, denied = _guard(request)
    if denied:
        return denied
    form = EnterpriseCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        mail_configuration = CleanGoMailConfiguration.objects.filter(actif=True).first()
        if not mail_configuration:
            form.add_error(None, "Configurez et activez d’abord l’email SMTP CleanGo avant de créer une entreprise.")
            context = _context(admin)
            context.update({"form": form})
            return render(request, "platform_admin/create_enterprise.html", context)
        today = timezone.localdate()
        plan = form.cleaned_data["plan"]
        is_active = form.cleaned_data["statut_abonnement"] == "actif"
        duration = form.cleaned_data.get("duree_mois") or 1
        raw_password = secrets.token_urlsafe(10)
        payment = None
        try:
            with transaction.atomic():
                company = Entreprise.objects.create(
            raison_sociale=form.cleaned_data["raison_sociale"],
            email_contact=form.cleaned_data["email_contact"],
            telephone_contact=form.cleaned_data["telephone_contact"],
            adresse=form.cleaned_data["adresse"],
            plan=plan,
            statut_abonnement="actif" if is_active else "essai",
            date_debut_abonnement=today if is_active else None,
            date_fin_abonnement=_add_months(today, duration) if is_active else None,
            date_debut_essai=None if is_active else today,
            date_fin_essai=None if is_active else today + timedelta(days=plan.duree_essai_jours),
            devise=plan.devise or "XOF",
            langue="fr",
            fuseau_horaire="Africa/Abidjan",
            couleur_principale="#168a55",
            slogan="L’idée du lavage en un clic",
                )
                roles = {}
                for code, label in (
            ("admin", "Administrateur"),
            ("manager", "Manager"),
            ("caissier", "Caissier"),
            ("laveur", "Laveur"),
                ):
                    roles[code] = Role.objects.create(entreprise=company, code=code, libelle=label)
                user = User(
            nom=form.cleaned_data["admin_nom"],
            email=form.cleaned_data["admin_email"],
            telephone=form.cleaned_data["admin_telephone"],
            entreprise=company,
            role=roles["admin"],
            statut="actif",
                )
                user.set_password(raw_password)
                user.save()
                if is_active:
                    payment = PaiementAbonnement.objects.create(
                entreprise=company,
                plan=plan,
                methode="autre",
                montant=plan.prix_mensuel * duration,
                devise=plan.devise,
                statut="paye",
                    )
                login_url = request.build_absolute_uri(reverse("authentication:connexion"))
                logo_url = request.build_absolute_uri(static("branding/cleango-logo.png"))
                _send_enterprise_credentials(mail_configuration, user, raw_password, login_url, logo_url)
        except Exception as exc:
            form.add_error(None, f"Entreprise non créée : l’envoi des identifiants a échoué ({exc}).")
            context = _context(admin)
            context.update({"form": form})
            return render(request, "platform_admin/create_enterprise.html", context)
        if payment:
            try:
                send_payment_confirmation(payment, request.build_absolute_uri("/"))
            except Exception:
                messages.warning(request, "Le compte a été créé, mais la confirmation de paiement n’a pas pu être envoyée.")
        messages.success(request, f"L’entreprise {company.raison_sociale} et son administrateur ont été créés.")
        return redirect("platform_admin:enterprise_detail", pk=company.pk)
    context = _context(admin)
    context.update({"form": form})
    return render(request, "platform_admin/create_enterprise.html", context)


def enterprise_detail(request, pk):
    admin, denied = _guard(request)
    if denied:
        return denied
    company = get_object_or_404(
        Entreprise.objects.select_related("plan"),
        pk=pk,
    )
    context = _context(admin)
    context.update({
        "company": company,
        "company_admins": company.utilisateurs.select_related("role").filter(role__code="admin"),
        "payments": company.paiements_abonnement.select_related("plan")[:20],
        "activation_form": SubscriptionActivationForm(initial={"plan": company.plan, "duree_mois": 1}),
    })
    return render(request, "platform_admin/enterprise_detail.html", context)


@transaction.atomic
def activate_subscription(request, pk):
    admin, denied = _guard(request)
    if denied:
        return denied
    company = get_object_or_404(Entreprise, pk=pk)
    if request.method != "POST":
        return redirect("platform_admin:enterprise_detail", pk=pk)
    form = SubscriptionActivationForm(request.POST)
    if form.is_valid():
        today = timezone.localdate()
        plan = form.cleaned_data["plan"]
        duration = form.cleaned_data["duree_mois"]
        start = company.date_fin_abonnement if company.date_fin_abonnement and company.date_fin_abonnement >= today else today
        company.plan = plan
        company.statut_abonnement = "actif"
        company.date_debut_abonnement = company.date_debut_abonnement or today
        company.date_fin_abonnement = _add_months(start, duration)
        company.save(update_fields=[
            "plan", "statut_abonnement", "date_debut_abonnement",
            "date_fin_abonnement", "updated_at",
        ])
        payment = PaiementAbonnement.objects.create(
            entreprise=company,
            plan=plan,
            methode="autre",
            montant=plan.prix_mensuel * duration,
            devise=plan.devise,
            statut="paye",
        )
        try:
            send_payment_confirmation(payment, request.build_absolute_uri("/"))
        except Exception:
            messages.warning(request, "L’abonnement est actif, mais l’email de confirmation n’a pas pu être envoyé.")
        messages.success(request, f"Abonnement activé jusqu’au {company.date_fin_abonnement:%d/%m/%Y}.")
    else:
        messages.error(request, "Vérifiez le plan et la durée de l’abonnement.")
    return redirect("platform_admin:enterprise_detail", pk=pk)


def suspend_subscription(request, pk):
    admin, denied = _guard(request)
    if denied:
        return denied
    company = get_object_or_404(Entreprise, pk=pk)
    if request.method == "POST":
        company.statut_abonnement = "suspendu"
        company.save(update_fields=["statut_abonnement", "updated_at"])
        messages.success(request, "L’abonnement de l’entreprise a été suspendu.")
    return redirect("platform_admin:enterprise_detail", pk=pk)
