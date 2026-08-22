from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.core import signing
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import escape
import random
import string
import logging
import base64
import secrets
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from io import BytesIO
import qrcode
import yagmail
from cryptography.fernet import InvalidToken

from .models import User
from .forms import (
    LoginForm, RegisterForm, UserProfileForm, 
    UserPasswordChangeForm, PasswordResetRequestForm,
    PasswordResetConfirmForm, UserCreateForm, UserUpdateForm,
    EnterpriseProfileForm, RoleCreationForm, CiviliteCreationForm,
    MailConfigurationForm, CommissionSettingsForm,
)
from apps.entreprises.models import Entreprise
from apps.plan.models import PaiementAbonnement, Plan
from apps.roles.models import Role
from apps.core.models import ConfigurationMail

logger = logging.getLogger(__name__)

PASSWORD_RESET_SALT = 'authentication.password-reset'
PASSWORD_RESET_MAX_AGE = 60 * 60 * 24


def _payment_qr_data(provider, entreprise):
    """Construit un QR local; l'URI sera remplacée par celle du prestataire en production."""
    payload = (
        f"sgla://abonnement?provider={provider}"
        f"&entreprise={entreprise.pk}"
    )
    image = qrcode.make(payload)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def _send_collaborator_credentials(mail_config, collaborator, raw_password, login_url):
    smtp = yagmail.SMTP(
        user=mail_config.utilisateur_smtp,
        password=mail_config.get_password(),
        host=mail_config.serveur_smtp,
        port=mail_config.port_smtp,
        smtp_starttls=mail_config.utiliser_tls,
        smtp_ssl=mail_config.utiliser_ssl,
    )
    try:
        smtp.send(
            to=collaborator.email,
            subject=f'Votre compte {collaborator.entreprise.raison_sociale}',
            contents=_collaborator_invitation_email_html(
                collaborator,
                raw_password,
                login_url,
            ),
        )
    finally:
        smtp.close()


def _collaborator_invitation_email_html(collaborator, raw_password, login_url):
    company = collaborator.entreprise
    color = company.couleur_principale or '#1769D2'
    company_name = escape(company.raison_sociale)
    user_name = escape(collaborator.nom)
    email = escape(collaborator.email)
    matricule = escape(collaborator.matricule or '—')
    password = escape(raw_password)
    safe_url = escape(login_url)
    return f"""
    <!doctype html>
    <html lang="fr">
    <body style="margin:0;padding:0;background:#f3f6fa;font-family:Arial,sans-serif;color:#172033">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f6fa;padding:30px 12px">
        <tr><td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:620px;overflow:hidden;border:1px solid #e0e6ee;border-radius:14px;background:#ffffff">
            <tr><td style="padding:26px 30px;color:#ffffff;background:{color}">
              <div style="font-size:12px;font-weight:700;letter-spacing:1.5px;opacity:.82">BIENVENUE DANS VOTRE ESPACE</div>
              <div style="margin-top:7px;font-size:24px;font-weight:800">{company_name}</div>
            </td></tr>
            <tr><td style="padding:32px 30px">
              <h1 style="margin:0 0 14px;font-size:23px;line-height:1.3">Votre compte collaborateur est prêt</h1>
              <p style="margin:0 0 10px;color:#5d687b;font-size:15px;line-height:1.65">Bonjour <strong>{user_name}</strong>,</p>
              <p style="margin:0 0 22px;color:#5d687b;font-size:15px;line-height:1.65">Un compte vient d’être créé pour vous permettre d’accéder à la plateforme de <strong>{company_name}</strong>.</p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #dfe5ed;border-radius:9px;background:#f8fafc">
                <tr><td style="padding:13px 16px;border-bottom:1px solid #e4e9f0;color:#758196;font-size:12px">Email</td><td style="padding:13px 16px;border-bottom:1px solid #e4e9f0;font-size:13px;font-weight:700;text-align:right">{email}</td></tr>
                <tr><td style="padding:13px 16px;border-bottom:1px solid #e4e9f0;color:#758196;font-size:12px">Matricule</td><td style="padding:13px 16px;border-bottom:1px solid #e4e9f0;font-size:13px;font-weight:700;text-align:right">{matricule}</td></tr>
                <tr><td style="padding:13px 16px;color:#758196;font-size:12px">Mot de passe initial</td><td style="padding:13px 16px;font-family:Consolas,monospace;font-size:15px;font-weight:800;text-align:right">{password}</td></tr>
              </table>
              <span style="display:none">Mot de passe initial : {password} </span>
              <table role="presentation" cellspacing="0" cellpadding="0" style="margin:26px 0">
                <tr><td style="border-radius:8px;background:{color}"><a href="{safe_url}" style="display:inline-block;padding:14px 24px;color:#ffffff;font-size:14px;font-weight:800;text-decoration:none">Se connecter à mon espace</a></td></tr>
              </table>
              <div style="padding:14px 16px;border-left:4px solid #f2b84b;border-radius:6px;background:#fff8e8;color:#715614;font-size:13px;line-height:1.55">
                Pour votre sécurité, changez ce mot de passe après votre première connexion et ne le communiquez à personne.
              </div>
              <p style="margin:23px 0 7px;color:#7b8596;font-size:12px">Lien de connexion :</p>
              <p style="margin:0;word-break:break-all;font-size:11px"><a href="{safe_url}" style="color:{color}">{safe_url}</a></p>
            </td></tr>
            <tr><td align="center" style="padding:17px;color:#8a94a5;background:#f8fafc;font-size:11px">Message automatique envoyé par {company_name}</td></tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


def _send_company_email(mail_config, recipient, subject, contents):
    smtp = yagmail.SMTP(
        user=mail_config.utilisateur_smtp,
        password=mail_config.get_password(),
        host=mail_config.serveur_smtp,
        port=mail_config.port_smtp,
        smtp_starttls=mail_config.utiliser_tls,
        smtp_ssl=mail_config.utiliser_ssl,
    )
    try:
        smtp.send(to=recipient, subject=subject, contents=contents)
    finally:
        smtp.close()


def _password_reset_email_html(user, reset_url):
    company = user.entreprise
    color = company.couleur_principale or '#1769D2'
    company_name = escape(company.raison_sociale)
    user_name = escape(user.nom)
    safe_url = escape(reset_url)
    return f"""
    <!doctype html>
    <html lang="fr">
    <body style="margin:0;padding:0;background:#f3f6fa;font-family:Arial,sans-serif;color:#172033">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f6fa;padding:30px 12px">
        <tr><td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;overflow:hidden;border:1px solid #e0e6ee;border-radius:14px;background:#ffffff">
            <tr>
              <td style="padding:25px 30px;color:#ffffff;background:{color}">
                <div style="font-size:12px;font-weight:700;letter-spacing:1.5px;opacity:.82">SÉCURITÉ DU COMPTE</div>
                <div style="margin-top:7px;font-size:23px;font-weight:800">{company_name}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:32px 30px">
                <h1 style="margin:0 0 14px;font-size:23px;line-height:1.25">Réinitialisez votre mot de passe</h1>
                <p style="margin:0 0 12px;color:#5d687b;font-size:15px;line-height:1.65">Bonjour <strong>{user_name}</strong>,</p>
                <p style="margin:0;color:#5d687b;font-size:15px;line-height:1.65">Une demande de réinitialisation a été effectuée pour votre compte. Cliquez sur le bouton ci-dessous pour choisir un nouveau mot de passe.</p>
                <table role="presentation" cellspacing="0" cellpadding="0" style="margin:26px 0">
                  <tr><td style="border-radius:8px;background:{color}">
                    <a href="{safe_url}" style="display:inline-block;padding:14px 23px;color:#ffffff;font-size:14px;font-weight:800;text-decoration:none">Réinitialiser mon mot de passe</a>
                  </td></tr>
                </table>
                <div style="padding:14px 16px;border-left:4px solid #f2b84b;border-radius:6px;background:#fff8e8;color:#715614;font-size:13px;line-height:1.55">
                  Ce lien est valable pendant <strong>24 heures</strong> et ne peut être utilisé qu’une seule fois.
                </div>
                <p style="margin:24px 0 7px;color:#7b8596;font-size:12px">Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :</p>
                <p style="margin:0;word-break:break-all;font-size:11px;line-height:1.5"><a href="{safe_url}" style="color:{color}">{safe_url}</a></p>
                <p style="margin:24px 0 0;padding-top:20px;border-top:1px solid #e8ecf1;color:#7b8596;font-size:12px;line-height:1.55">Si vous n’avez pas demandé cette modification, ignorez simplement cet email. Votre mot de passe actuel restera inchangé.</p>
              </td>
            </tr>
            <tr><td align="center" style="padding:17px;color:#8a94a5;background:#f8fafc;font-size:11px">Message automatique envoyé par {company_name}</td></tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


def connected_profile_view(request):
    """Affiche le profil de l'utilisateur de la session applicative."""
    utilisateur_id = request.session.get('utilisateur_id')
    user = User.objects.select_related('entreprise__plan', 'role').filter(
        pk=utilisateur_id,
        statut='actif',
    ).first()
    if user is None:
        messages.info(request, 'Connectez-vous pour accéder à votre profil.')
        return redirect('authentication:connexion')

    return render(request, 'authentication/profile.html', {
        'user': user,
        'entreprise': user.entreprise,
        'plan': user.entreprise.plan,
        'stats': {
            'total_users': User.objects.filter(entreprise=user.entreprise).count(),
            'jours_restants': max(
                (user.entreprise.date_fin_essai - timezone.localdate()).days,
                0,
            ) if user.entreprise.date_fin_essai else 0,
        },
        'user_initials': ''.join(
            part[0].upper() for part in user.nom.split()[:2] if part
        ),
    })


def edit_connected_profile_view(request):
    """Modifie le nom et l'email de l'utilisateur connecté."""
    utilisateur_id = request.session.get('utilisateur_id')
    user = User.objects.select_related('entreprise__plan', 'role').filter(
        pk=utilisateur_id,
        statut='actif',
    ).first()
    if user is None:
        messages.info(request, 'Connectez-vous pour modifier votre profil.')
        return redirect('authentication:connexion')

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre profil a été mis à jour avec succès.')
            return redirect('authentication:profile')
    else:
        form = UserProfileForm(instance=user)

    return render(request, 'authentication/edit_profile.html', {
        'form': form,
        'user': user,
        'entreprise': user.entreprise,
        'plan': user.entreprise.plan,
        'stats': {
            'total_users': User.objects.filter(entreprise=user.entreprise).count(),
            'jours_restants': max(
                (user.entreprise.date_fin_essai - timezone.localdate()).days,
                0,
            ) if user.entreprise.date_fin_essai else 0,
        },
        'user_initials': ''.join(
            part[0].upper() for part in user.nom.split()[:2] if part
        ),
    })


def enterprise_settings_view(request):
    """Affiche le profil et les paramètres de l'entreprise connectée."""
    utilisateur_id = request.session.get('utilisateur_id')
    user = User.objects.select_related('entreprise__plan', 'role').filter(
        pk=utilisateur_id,
        statut='actif',
    ).first()
    if user is None:
        messages.info(request, 'Connectez-vous pour accéder aux paramètres.')
        return redirect('authentication:connexion')

    entreprise = user.entreprise
    payment_history = entreprise.paiements_abonnement.select_related('plan').all()
    subscription_history = []
    if entreprise.date_debut_essai or entreprise.date_fin_essai:
        subscription_history.append({
            'plan': entreprise.plan,
            'type': 'Essai gratuit',
            'start': entreprise.date_debut_essai,
            'end': entreprise.date_fin_essai,
            'status': (
                'Expiré'
                if entreprise.date_fin_essai
                and entreprise.date_fin_essai < timezone.localdate()
                else 'En cours'
            ),
        })
    for paid_payment in payment_history.filter(statut='paye'):
        subscription_history.append({
            'plan': paid_payment.plan,
            'type': 'Abonnement payant',
            'start': paid_payment.updated_at.date(),
            'end': (
                entreprise.date_fin_abonnement
                if paid_payment.plan_id == entreprise.plan_id
                else None
            ),
            'status': 'Actif' if paid_payment.plan_id == entreprise.plan_id else 'Terminé',
        })
    settings_end_date = (
        entreprise.date_fin_abonnement
        if entreprise.statut_abonnement == 'actif'
        else entreprise.date_fin_essai
    )
    return render(request, 'authentication/enterprise_settings.html', {
        'user': user,
        'entreprise': entreprise,
        'plan': entreprise.plan,
        'can_edit_company': user.role.code == 'admin',
        'payment_history': payment_history,
        'subscription_history': subscription_history,
        'stats': {
            'total_users': entreprise.utilisateurs.count(),
            'jours_restants': max(
                (settings_end_date - timezone.localdate()).days,
                0,
            ) if settings_end_date else 0,
        },
        'user_initials': ''.join(
            part[0].upper() for part in user.nom.split()[:2] if part
        ),
    })


def edit_enterprise_settings_view(request):
    """Modifie le profil de l'entreprise, réservé à son administrateur."""
    utilisateur_id = request.session.get('utilisateur_id')
    user = User.objects.select_related('entreprise__plan', 'role').filter(
        pk=utilisateur_id,
        statut='actif',
    ).first()
    if user is None:
        messages.info(request, 'Connectez-vous pour accéder aux paramètres.')
        return redirect('authentication:connexion')
    if user.role.code != 'admin':
        messages.error(request, 'Seul un administrateur peut modifier le profil de l’entreprise.')
        return redirect('authentication:enterprise_settings')

    entreprise = user.entreprise
    if request.method == 'POST':
        form = EnterpriseProfileForm(request.POST, request.FILES, instance=entreprise)
        if form.is_valid():
            form.save()
            messages.success(request, 'Le profil de l’entreprise a été mis à jour.')
            return redirect('authentication:enterprise_settings')
    else:
        form = EnterpriseProfileForm(instance=entreprise)

    return render(request, 'authentication/edit_enterprise_settings.html', {
        'form': form,
        'user': user,
        'entreprise': entreprise,
        'plan': entreprise.plan,
        'stats': {
            'total_users': entreprise.utilisateurs.count(),
            'jours_restants': max(
                (entreprise.date_fin_essai - timezone.localdate()).days,
                0,
            ) if entreprise.date_fin_essai else 0,
        },
        'user_initials': ''.join(
            part[0].upper() for part in user.nom.split()[:2] if part
        ),
    })


def configuration_hub_view(request):
    """Centre de configuration réservé aux administrateurs."""
    utilisateur_id = request.session.get('utilisateur_id')
    user = User.objects.select_related('entreprise__plan', 'role').filter(
        pk=utilisateur_id,
        statut='actif',
    ).first()
    if user is None:
        messages.info(request, 'Connectez-vous pour accéder à la configuration.')
        return redirect('authentication:connexion')
    if user.role.code != 'admin':
        messages.error(request, 'La configuration est réservée aux administrateurs.')
        return redirect('dashboard:index')

    entreprise = user.entreprise
    active_tab = request.GET.get('tab', 'accounts')
    allowed_tabs = {'accounts', 'enterprise', 'roles', 'civilities', 'subscription', 'mail', 'commissions'}
    if active_tab not in allowed_tabs:
        active_tab = 'accounts'
    today = timezone.localdate()
    trial_expired = bool(
        entreprise.statut_abonnement == 'essai'
        and entreprise.date_fin_essai
        and entreprise.date_fin_essai < today
    )
    paid_subscription_expired = bool(
        entreprise.statut_abonnement == 'actif'
        and entreprise.date_fin_abonnement
        and entreprise.date_fin_abonnement < today
    )
    subscription_end_date = (
        entreprise.date_fin_abonnement
        if entreprise.statut_abonnement == 'actif'
        else entreprise.date_fin_essai
    )
    subscription_active = (
        entreprise.statut_abonnement == 'actif'
        and not paid_subscription_expired
    ) or (
        entreprise.statut_abonnement == 'essai' and not trial_expired
    )
    payment_options = [
        {
            'code': code,
            'label': label,
            'qr': _payment_qr_data(code, entreprise)
            if code in {'mtn', 'wave', 'orange', 'moov'} else '',
        }
        for code, label in PaiementAbonnement.METHODES
    ]
    account_form = UserCreateForm(entreprise=entreprise)
    role_form = RoleCreationForm(entreprise=entreprise)
    edited_account = User.objects.filter(pk=request.GET.get('edit_account'), entreprise=entreprise).first()
    edited_role = Role.objects.filter(pk=request.GET.get('edit_role'), entreprise=entreprise).first()
    if edited_account:
        active_tab = 'accounts'
        account_form = UserUpdateForm(instance=edited_account, entreprise=entreprise)
    if edited_role:
        active_tab = 'roles'
        role_form = RoleCreationForm(initial={'libelle': edited_role.libelle}, entreprise=entreprise, instance=edited_role)
    civilite_form = CiviliteCreationForm(entreprise=entreprise)
    mail_config = ConfigurationMail.objects.filter(entreprise=entreprise).first()
    mail_form = MailConfigurationForm(instance=mail_config)
    commission_form = CommissionSettingsForm(instance=entreprise)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_commission_settings':
            active_tab = 'commissions'
            commission_form = CommissionSettingsForm(request.POST, instance=entreprise)
            if commission_form.is_valid():
                commission_form.save()
                messages.success(request, 'Le pourcentage du laveur a été enregistré.')
                return redirect(f"{reverse('authentication:configuration')}?tab=commissions")
        elif action == 'save_mail_configuration':
            active_tab = 'mail'
            mail_form = MailConfigurationForm(request.POST, instance=mail_config)
            if mail_form.is_valid():
                mail_config = mail_form.save(commit=False)
                mail_config.entreprise = entreprise
                mail_config.set_password(mail_form.cleaned_data.get('mot_de_passe'))
                mail_config.save()
                messages.success(request, 'La configuration mail a été enregistrée.')
                return redirect(f"{reverse('authentication:configuration')}?tab=mail")
        elif action == 'test_mail_configuration':
            active_tab = 'mail'
            if mail_config is None or not mail_config.actif:
                messages.error(request, 'Enregistrez et activez d’abord la configuration mail.')
            else:
                try:
                    smtp = yagmail.SMTP(
                        user=mail_config.utilisateur_smtp,
                        password=mail_config.get_password(),
                        host=mail_config.serveur_smtp,
                        port=mail_config.port_smtp,
                        smtp_starttls=mail_config.utiliser_tls,
                        smtp_ssl=mail_config.utiliser_ssl,
                    )
                    smtp.send(
                        to=entreprise.email_contact,
                        subject=f'Test de messagerie — {entreprise.raison_sociale}',
                        contents=(
                            f'Bonjour,\n\nLa configuration mail de '
                            f'{entreprise.raison_sociale} fonctionne correctement.'
                        ),
                    )
                    smtp.close()
                    messages.success(
                        request,
                        f'Email de test envoyé à {entreprise.email_contact}.',
                    )
                except InvalidToken:
                    logger.exception('Mot de passe SMTP illisible pour entreprise=%s', entreprise.pk)
                    messages.error(
                        request,
                        'Le mot de passe SMTP enregistré ne peut plus être lu. '
                        'Ressaisissez-le puis enregistrez la configuration.',
                    )
                except Exception:
                    logger.exception('Échec du test SMTP pour entreprise=%s', entreprise.pk)
                    messages.error(
                        request,
                        'Échec de l’envoi. Vérifiez le serveur, le port et les identifiants SMTP.',
                    )
        elif action == 'initiate_payment':
            active_tab = 'subscription'
            selected_plan = Plan.objects.filter(
                pk=request.POST.get('plan_id'),
                actif=True,
            ).first()
            methode = request.POST.get('methode')
            telephone = request.POST.get('telephone', '').strip()
            methodes_valides = dict(PaiementAbonnement.METHODES)
            mobile_methods = {'mtn', 'wave', 'orange', 'moov'}
            if selected_plan is None:
                messages.error(request, 'Le plan sélectionné est indisponible.')
            elif methode not in methodes_valides:
                messages.error(request, 'Sélectionnez un moyen de paiement valide.')
            elif methode in mobile_methods and not telephone:
                messages.error(request, 'Saisissez le numéro Mobile Money à débiter.')
            else:
                paiement = PaiementAbonnement.objects.create(
                    entreprise=entreprise,
                    plan=selected_plan,
                    methode=methode,
                    telephone=telephone if methode in mobile_methods else '',
                    montant=selected_plan.prix_mensuel,
                    devise=selected_plan.devise,
                )
                messages.success(
                    request,
                    f'Paiement {paiement.reference} créé. Confirmez la transaction chez '
                    f'{methodes_valides[methode]}.',
                )
                return redirect(
                    f"{reverse('authentication:configuration')}?tab=subscription"
                )
        elif action == 'create_account':
            active_tab = 'accounts'
            account_form = UserCreateForm(request.POST, entreprise=entreprise)
            if account_form.is_valid():
                if User.objects.filter(email__iexact=account_form.cleaned_data['email']).exists():
                    account_form.add_error('email', 'Cet email est déjà utilisé.')
                elif mail_config is None or not mail_config.actif:
                    account_form.add_error(
                        None,
                        'Configurez et activez la messagerie de l’entreprise avant de créer un collaborateur.',
                    )
                else:
                    raw_password = secrets.token_urlsafe(12)
                    try:
                        with transaction.atomic():
                            new_user = account_form.save(commit=False)
                            new_user.entreprise = entreprise
                            new_user.invite_par = user
                            new_user.statut = 'actif'
                            new_user.matricule = f'MAT-{secrets.token_hex(3).upper()}'
                            new_user.set_password(raw_password)
                            new_user.save()
                            _send_collaborator_credentials(
                                mail_config,
                                new_user,
                                raw_password,
                                request.build_absolute_uri(
                                    reverse('authentication:connexion')
                                ),
                            )
                    except Exception:
                        logger.exception(
                            'Échec envoi invitation collaborateur entreprise=%s',
                            entreprise.pk,
                        )
                        account_form.add_error(
                            None,
                            'Le compte n’a pas été créé car l’email d’invitation n’a pas pu être envoyé.',
                        )
                    else:
                        messages.success(
                            request,
                            f'Le compte de {new_user.nom} a été créé et ses accès ont été envoyés par email.',
                        )
                        return redirect(f"{reverse('authentication:configuration')}?tab=accounts")
        elif action == 'update_account':
            active_tab = 'accounts'
            edited_account = User.objects.filter(pk=request.POST.get('account_id'), entreprise=entreprise).first()
            if edited_account is None:
                messages.error(request, 'Compte introuvable.')
            else:
                account_form = UserUpdateForm(request.POST, instance=edited_account, entreprise=entreprise)
                if account_form.is_valid():
                    account_form.save()
                    messages.success(request, f'Le compte de {edited_account.nom} a été modifié.')
                    return redirect(f"{reverse('authentication:configuration')}?tab=accounts")
        elif action == 'create_role':
            active_tab = 'roles'
            role_form = RoleCreationForm(request.POST, entreprise=entreprise, instance=edited_role)
            if role_form.is_valid():
                Role.objects.create(
                    entreprise=entreprise,
                    code=f'ROLE-{secrets.token_hex(3).upper()}',
                    libelle=role_form.cleaned_data['libelle'],
                )
                messages.success(request, 'Le rôle a été créé.')
                return redirect(f"{reverse('authentication:configuration')}?tab=roles")
        elif action == 'update_role':
            active_tab = 'roles'
            edited_role = Role.objects.filter(pk=request.POST.get('role_id'), entreprise=entreprise).first()
            role_form = RoleCreationForm(request.POST, entreprise=entreprise)
            if edited_role is None:
                messages.error(request, 'Rôle introuvable.')
            elif role_form.is_valid():
                edited_role.libelle = role_form.cleaned_data['libelle']
                edited_role.save(update_fields=['libelle'])
                messages.success(request, 'Le rôle a été modifié.')
                return redirect(f"{reverse('authentication:configuration')}?tab=roles")
        elif action == 'create_civilite':
            active_tab = 'civilities'
            civilite_form = CiviliteCreationForm(request.POST, entreprise=entreprise)
            if civilite_form.is_valid():
                civilite = civilite_form.save(commit=False)
                civilite.entreprise = entreprise
                civilite.code = f'CIV-{secrets.token_hex(3).upper()}'
                civilite.save()
                messages.success(request, 'La civilité a été créée.')
                return redirect(f"{reverse('authentication:configuration')}?tab=civilities")

    return render(request, 'authentication/configuration.html', {
        'user': user,
        'entreprise': entreprise,
        'plan': entreprise.plan,
        'active_tab': active_tab,
        'account_form': account_form,
        'edited_account': edited_account,
        'role_form': role_form,
        'edited_role': edited_role,
        'civilite_form': civilite_form,
        'mail_form': mail_form,
        'commission_form': commission_form,
        'mail_config': mail_config,
        'users': entreprise.utilisateurs.select_related('role').order_by('-created_at')[:8],
        'roles': entreprise.roles.order_by('libelle'),
        'civilites': entreprise.civilites.order_by('libelle'),
        'available_plans': Plan.objects.filter(actif=True).order_by('prix_mensuel'),
        'payment_methods': payment_options,
        'recent_payments': entreprise.paiements_abonnement.select_related('plan')[:5],
        'trial_expired': trial_expired,
        'paid_subscription_expired': paid_subscription_expired,
        'subscription_active': subscription_active,
        'subscription_end_date': subscription_end_date,
        'stats': {
            'total_users': entreprise.utilisateurs.count(),
            'jours_restants': max(
                (subscription_end_date - timezone.localdate()).days,
                0,
            ) if subscription_end_date else 0,
        },
        'user_initials': ''.join(
            part[0].upper() for part in user.nom.split()[:2] if part
        ),
    })


def forgot_password_view(request):
    """Envoie un lien de réinitialisation sans révéler si le compte existe."""
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email__iexact=email).first()
            delivery_failed = False
            if user is not None:
                token = signing.dumps(
                    {'user_id': user.pk, 'password': user.password},
                    salt=PASSWORD_RESET_SALT,
                    compress=True,
                )
                reset_url = request.build_absolute_uri(
                    reverse('authentication:reset_password', kwargs={'token': token})
                )
                subject = f'Réinitialisation de votre mot de passe — {user.entreprise.raison_sociale}'
                plain_content = (
                    f'Bonjour {user.nom},\n\n'
                    'Utilisez le lien suivant pour définir un nouveau mot de passe :\n'
                    f'{reset_url}\n\n'
                    'Ce lien est valable pendant 24 heures et ne peut être utilisé qu’une fois.'
                )
                mail_config = ConfigurationMail.objects.filter(
                    entreprise=user.entreprise,
                    actif=True,
                ).first()
                try:
                    if mail_config:
                        _send_company_email(
                            mail_config,
                            user.email,
                            subject,
                            _password_reset_email_html(user, reset_url),
                        )
                    else:
                        send_mail(
                            subject,
                            plain_content,
                            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sgla.local'),
                            [user.email],
                            fail_silently=False,
                        )
                except Exception:
                    delivery_failed = True
                    logger.exception(
                        'Échec envoi réinitialisation utilisateur=%s entreprise=%s',
                        user.pk,
                        user.entreprise_id,
                    )
            if delivery_failed:
                messages.error(
                    request,
                    'Le serveur de messagerie n’a pas pu envoyer le lien. '
                    'Vérifiez la configuration SMTP de l’entreprise ou contactez son administrateur.',
                )
                return redirect('authentication:forgot_password')
            messages.success(
                request,
                'Si un compte correspond à cet email, un lien de réinitialisation a été envoyé.',
            )
            return redirect('authentication:connexion')
    else:
        form = PasswordResetRequestForm()

    return render(request, 'authentication/forgot_password.html', {'form': form})


def reset_password_view(request, token):
    """Valide un jeton signé et enregistre le nouveau mot de passe."""
    try:
        payload = signing.loads(
            token,
            salt=PASSWORD_RESET_SALT,
            max_age=PASSWORD_RESET_MAX_AGE,
        )
        user = User.objects.get(pk=payload['user_id'])
        if payload.get('password') != user.password:
            raise signing.BadSignature
    except (signing.BadSignature, signing.SignatureExpired, User.DoesNotExist, KeyError):
        return render(request, 'authentication/reset_password.html', {
            'invalid_token': True,
            'form': None,
        }, status=400)

    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password'])
            user.save(update_fields=['password', 'updated_at'])
            messages.success(
                request,
                'Votre mot de passe a été réinitialisé. Vous pouvez maintenant vous connecter.',
            )
            return redirect('authentication:connexion')
    else:
        form = PasswordResetConfirmForm()

    return render(request, 'authentication/reset_password.html', {
        'form': form,
        'invalid_token': False,
    })


def company_register_view(request):
    """Crée une entreprise en essai et son premier administrateur."""
    if request.session.get('utilisateur_id'):
        return redirect('authentication:connexion')

    google_identity = request.session.get('google_signup_identity')
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES, google_identity=google_identity)
        if form.is_valid():
            with transaction.atomic():
                plan = form.cleaned_data['plan']
                debut_essai = timezone.localdate()
                entreprise = Entreprise.objects.create(
                    raison_sociale=form.cleaned_data['entreprise_nom'],
                    logo_url=form.cleaned_data.get('logo_url') or None,
                    favicon_url=form.cleaned_data.get('favicon_url') or None,
                    slogan=form.cleaned_data.get('slogan') or None,
                    couleur_principale=form.cleaned_data['couleur_principale'],
                    devise=form.cleaned_data['devise'],
                    langue=form.cleaned_data['langue'],
                    fuseau_horaire=form.cleaned_data['fuseau_horaire'],
                    statut_abonnement='essai',
                    date_debut_essai=debut_essai,
                    date_fin_essai=debut_essai + timezone.timedelta(days=plan.duree_essai_jours),
                    email_contact=form.cleaned_data['email'],
                    telephone_contact=form.cleaned_data.get('telephone_contact') or None,
                    plan=plan,
                )

                roles = {
                    code: Role.objects.create(
                        entreprise=entreprise,
                        code=code,
                        libelle=libelle,
                    )
                    for code, libelle in (
                        ('admin', 'Administrateur'),
                        ('manager', 'Manager'),
                        ('caissier', 'Caissier'),
                        ('laveur', 'Laveur'),
                    )
                }

                user = User(
                    nom=form.cleaned_data['nom'],
                    email=form.cleaned_data['email'].lower(),
                    entreprise=entreprise,
                    role=roles['admin'],
                    statut='actif',
                )
                user.set_password(form.cleaned_data.get('password') or secrets.token_urlsafe(32))
                user.save()

            messages.success(
                request,
                f'Compte créé avec succès. Votre essai {plan.nom} de '
                f'{plan.duree_essai_jours} jours est actif.',
            )
            request.session.pop('google_signup_identity', None)
            if google_identity:
                request.session['utilisateur_id'] = user.pk
                return redirect('dashboard:index')
            return redirect('authentication:connexion')
    else:
        form = RegisterForm(google_identity=google_identity)

    return render(request, 'authentication/register.html', {
        'form': form,
        'plans': Plan.objects.filter(actif=True).order_by('prix_mensuel'),
        'google_identity': google_identity,
        'google_oauth_enabled': bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET),
    })


def google_auth_start(request):
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        messages.error(request, 'La connexion Google doit être configurée par l’administrateur.')
        return redirect('authentication:inscription')
    state = secrets.token_urlsafe(32)
    request.session['google_oauth_state'] = state
    redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI or request.build_absolute_uri(
        reverse('authentication:google_auth_callback')
    )
    params = {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'prompt': 'select_account',
    }
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


def google_auth_callback(request):
    expected_state = request.session.pop('google_oauth_state', None)
    if not expected_state or not secrets.compare_digest(request.GET.get('state', ''), expected_state):
        messages.error(request, 'La vérification de sécurité Google a échoué. Veuillez réessayer.')
        return redirect('authentication:inscription')
    if request.GET.get('error') or not request.GET.get('code'):
        messages.error(request, 'L’inscription Google a été annulée.')
        return redirect('authentication:inscription')

    redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI or request.build_absolute_uri(
        reverse('authentication:google_auth_callback')
    )
    token_data = urlencode({
        'code': request.GET['code'],
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }).encode()
    try:
        token_request = Request(
            'https://oauth2.googleapis.com/token',
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        with urlopen(token_request, timeout=10) as response:
            access_token = json.load(response)['access_token']
        profile_request = Request(
            'https://openidconnect.googleapis.com/v1/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
        )
        with urlopen(profile_request, timeout=10) as response:
            profile = json.load(response)
    except (HTTPError, URLError, KeyError, ValueError):
        logger.exception('Échec de l’authentification Google')
        messages.error(request, 'Google n’a pas pu vérifier votre compte. Veuillez réessayer.')
        return redirect('authentication:inscription')

    if not profile.get('email') or not profile.get('email_verified'):
        messages.error(request, 'Votre adresse email Google doit être vérifiée.')
        return redirect('authentication:inscription')
    if User.objects.filter(email__iexact=profile['email']).exists():
        messages.error(request, 'Un compte existe déjà avec cette adresse. Connectez-vous.')
        return redirect('authentication:connexion')

    request.session['google_signup_identity'] = {
        'sub': profile.get('sub', ''),
        'name': profile.get('name') or profile['email'].split('@')[0],
        'email': profile['email'].lower(),
    }
    messages.success(request, 'Compte Google vérifié. Complétez les informations de votre entreprise.')
    return redirect('authentication:inscription')


# ============================================================================
# VUES D'AUTHENTIFICATION
# ============================================================================

def login_view(request):
    """
    Vue de connexion
    """
    utilisateur_id = request.session.get('utilisateur_id')
    utilisateur_connecte = User.objects.filter(pk=utilisateur_id).first() if utilisateur_id else None
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)
            
            user = form.user
            
            if user is not None:
                if user.statut != 'actif':
                    messages.error(request, f'Votre compte est {user.statut}. Veuillez contacter l\'administrateur.')
                    return render(request, 'authentication/login.html', {'form': form})
                
                request.session['utilisateur_id'] = user.pk
                
                # Mettre à jour la date de dernière connexion
                user.updated_at = timezone.now()
                user.save(update_fields=['updated_at'])
                
                # Gérer le "Se souvenir de moi"
                if not remember_me:
                    request.session.set_expiry(0)  # Session expire à la fermeture du navigateur
                else:
                    request.session.set_expiry(1209600)  # 2 semaines
                
                messages.success(request, f'Bienvenue {user.nom} !')
                
                # Rediriger vers la page demandée ou dashboard
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard:index')
            else:
                messages.error(request, 'Email ou mot de passe incorrect.')
    else:
        form = LoginForm()
    
    return render(request, 'authentication/login.html', {
        'form': form,
        'utilisateur_connecte': utilisateur_connecte,
    })


def logout_view(request):
    """
    Vue de déconnexion
    """
    request.session.pop('utilisateur_id', None)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('authentication:connexion')


def subscription_expired_view(request):
    user = User.objects.select_related("entreprise", "role").filter(
        pk=request.session.get("utilisateur_id"), statut="actif"
    ).first()
    if user is None:
        return redirect("authentication:connexion")
    if user.entreprise.abonnement_est_actif():
        return redirect("dashboard:index")
    return render(request, "authentication/subscription_expired.html", {
        "utilisateur_connecte": user,
        "entreprise": user.entreprise,
        "is_admin": user.role.code == "admin",
    })


def register_view(request):
    """
    Vue d'inscription
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            # Créer l'entreprise
            entreprise = Entreprise.objects.create(
                raison_sociale=form.cleaned_data['entreprise_nom'],
                email_contact=form.cleaned_data['email'],
                plan_id=form.cleaned_data.get('plan_id', 1),
                statut_abonnement='essai',
                date_debut_essai=timezone.now().date(),
                date_fin_essai=timezone.now().date() + timezone.timedelta(days=14)
            )
            
            # Créer les rôles par défaut
            roles_par_defaut = [
                {'code': 'admin', 'libelle': 'Administrateur', 'description': 'Administrateur de l\'entreprise'},
                {'code': 'manager', 'libelle': 'Manager', 'description': 'Gestionnaire'},
                {'code': 'caissier', 'libelle': 'Caissier', 'description': 'Opérateur de caisse'},
                {'code': 'laveur', 'libelle': 'Laveur', 'description': 'Personnel de lavage'},
            ]
            
            for role_data in roles_par_defaut:
                Role.objects.create(entreprise=entreprise, **role_data)
            
            # Récupérer le rôle admin
            role_admin = Role.objects.get(entreprise=entreprise, code='admin')
            
            # Créer l'utilisateur
            user = User.objects.create_user(
                nom=form.cleaned_data['nom'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                entreprise=entreprise,
                role=role_admin,
                statut='actif'
            )
            
            # Envoyer l'email de bienvenue
            try:
                send_welcome_email(user, entreprise)
            except Exception as e:
                logger.error(f"Erreur d'envoi d'email de bienvenue: {e}")
            
            messages.success(request, 'Inscription réussie ! Vous pouvez maintenant vous connecter.')
            return redirect('login')
    else:
        form = RegisterForm()
    
    return render(request, 'authentication/register.html', {'form': form})


def password_reset_request_view(request):
    """
    Vue de demande de réinitialisation du mot de passe
    """
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Générer un token
                reset_token = generate_reset_token(user)
                # Envoyer l'email
                send_password_reset_email(user, reset_token)
                messages.success(request, 'Un email de réinitialisation vous a été envoyé.')
                return redirect('login')
            except User.DoesNotExist:
                # Ne pas révéler si l'email existe (sécurité)
                messages.success(request, 'Un email de réinitialisation vous a été envoyé si le compte existe.')
                return redirect('login')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'authentication/password_reset_request.html', {'form': form})


def password_reset_confirm_view(request, token):
    """
    Vue de confirmation de réinitialisation du mot de passe
    """
    # Vérifier le token
    user = verify_reset_token(token)
    if not user:
        messages.error(request, 'Lien de réinitialisation invalide ou expiré.')
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user.set_password(new_password)
            user.save()
            
            messages.success(request, 'Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter.')
            return redirect('login')
    else:
        form = PasswordResetConfirmForm()
    
    return render(request, 'authentication/password_reset_confirm.html', {
        'form': form,
        'token': token
    })


# ============================================================================
# VUES DU PROFIL UTILISATEUR
# ============================================================================

@login_required
def profile_view(request):
    """
    Vue du profil utilisateur
    """
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user)
    
    return render(request, 'authentication/profile.html', {
        'form': form,
        'user': user
    })


@login_required
def change_password_view(request):
    """
    Vue pour changer le mot de passe
    """
    if request.method == 'POST':
        form = UserPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mot de passe changé avec succès.')
            return redirect('profile')
    else:
        form = UserPasswordChangeForm(request.user)
    
    return render(request, 'authentication/change_password.html', {'form': form})


# ============================================================================
# VUES DE GESTION DES UTILISATEURS (ADMIN)
# ============================================================================

@login_required
def user_list_view(request):
    """
    Liste des utilisateurs
    """
    # Vérifier les permissions
    if not request.user.is_superuser and not request.user.role.code in ['admin', 'manager']:
        messages.error(request, 'Vous n\'avez pas la permission de voir cette page.')
        return redirect('dashboard')
    
    users = User.objects.filter(entreprise=request.user.entreprise)
    
    # Filtres
    search = request.GET.get('search')
    if search:
        users = users.filter(Q(nom__icontains=search) | Q(email__icontains=search))
    
    statut = request.GET.get('statut')
    if statut:
        users = users.filter(statut=statut)
    
    role = request.GET.get('role')
    if role:
        users = users.filter(role_id=role)
    
    return render(request, 'authentication/user_list.html', {
        'users': users,
        'roles': Role.objects.filter(entreprise=request.user.entreprise)
    })


@login_required
def user_create_view(request):
    """
    Création d'un utilisateur
    """
    # Vérifier les permissions
    if not request.user.is_superuser and not request.user.role.code in ['admin', 'manager']:
        messages.error(request, 'Vous n\'avez pas la permission de créer des utilisateurs.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST, entreprise=request.user.entreprise)
        if form.is_valid():
            user = form.save(commit=False)
            user.entreprise = request.user.entreprise
            user.invite_par = request.user
            user.statut = 'actif'
            user.matricule = f'MAT-{secrets.token_hex(3).upper()}'
            user.set_password(secrets.token_urlsafe(12))
            user.save()
            
            messages.success(request, f'Utilisateur {user.nom} créé avec succès.')
            return redirect('user_list')
    else:
        form = UserCreateForm(entreprise=request.user.entreprise)
    
    return render(request, 'authentication/user_form.html', {
        'form': form,
        'title': 'Créer un utilisateur'
    })


@login_required
def user_update_view(request, pk):
    """
    Mise à jour d'un utilisateur
    """
    user = get_object_or_404(User, pk=pk, entreprise=request.user.entreprise)
    
    # Vérifier les permissions
    if not request.user.is_superuser and not request.user.role.code in ['admin', 'manager']:
        messages.error(request, 'Vous n\'avez pas la permission de modifier cet utilisateur.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Utilisateur {user.nom} mis à jour avec succès.')
            return redirect('user_list')
    else:
        form = UserUpdateForm(instance=user)
    
    return render(request, 'authentication/user_form.html', {
        'form': form,
        'title': 'Modifier un utilisateur',
        'user_obj': user
    })


@login_required
def user_delete_view(request, pk):
    """
    Suppression d'un utilisateur
    """
    user = get_object_or_404(User, pk=pk, entreprise=request.user.entreprise)
    
    # Vérifier les permissions
    if not request.user.is_superuser and not request.user.role.code == 'admin':
        messages.error(request, 'Vous n\'avez pas la permission de supprimer des utilisateurs.')
        return redirect('dashboard')
    
    # Empêcher la suppression de soi-même
    if user == request.user:
        messages.error(request, 'Vous ne pouvez pas supprimer votre propre compte.')
        return redirect('user_list')
    
    if request.method == 'POST':
        nom = user.nom
        user.delete()
        messages.success(request, f'Utilisateur {nom} supprimé avec succès.')
        return redirect('user_list')
    
    return render(request, 'authentication/user_confirm_delete.html', {'user': user})


@login_required
def user_toggle_status_view(request, pk):
    """
    Activer/Désactiver un utilisateur
    """
    user = get_object_or_404(User, pk=pk, entreprise=request.user.entreprise)
    
    # Vérifier les permissions
    if not request.user.is_superuser and not request.user.role.code in ['admin', 'manager']:
        messages.error(request, 'Vous n\'avez pas la permission de modifier cet utilisateur.')
        return redirect('dashboard')
    
    # Empêcher la désactivation de soi-même
    if user == request.user:
        messages.error(request, 'Vous ne pouvez pas désactiver votre propre compte.')
        return redirect('user_list')
    
    user.statut = 'inactif' if user.statut == 'actif' else 'actif'
    user.save()
    
    messages.success(request, f'Utilisateur {user.nom} {"activé" if user.statut == "actif" else "désactivé"} avec succès.')
    return redirect('user_list')


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def generate_reset_token(user):
    """
    Génère un token de réinitialisation
    """
    import uuid
    return str(uuid.uuid4())


def verify_reset_token(token):
    """
    Vérifie un token de réinitialisation
    """
    # À implémenter avec votre logique (cache, base de données, etc.)
    # Pour l'exemple, on simule
    return None


def send_welcome_email(user, entreprise):
    """
    Envoie un email de bienvenue
    """
    subject = f"Bienvenue sur {settings.PROJECT_NAME}"
    message = f"""
    Bonjour {user.nom},
    
    Bienvenue sur {settings.PROJECT_NAME} !
    
    Votre compte a été créé avec succès pour l'entreprise {entreprise.raison_sociale}.
    
    Vous pouvez vous connecter avec vos identifiants :
    Email: {user.email}
    
    Lien de connexion: {settings.BASE_URL}/login
    
    Cordialement,
    L'équipe {settings.PROJECT_NAME}
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False
    )


def send_password_reset_email(user, token):
    """
    Envoie un email de réinitialisation du mot de passe
    """
    reset_link = f"{settings.BASE_URL}/reset-password/{token}"
    
    subject = "Réinitialisation de votre mot de passe"
    message = f"""
    Bonjour {user.nom},
    
    Vous avez demandé la réinitialisation de votre mot de passe.
    
    Cliquez sur le lien ci-dessous pour réinitialiser votre mot de passe :
    {reset_link}
    
    Si vous n'avez pas fait cette demande, ignorez cet email.
    
    Ce lien est valable 24 heures.
    
    Cordialement,
    L'équipe {settings.PROJECT_NAME}
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False
    )
