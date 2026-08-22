from django import forms
from django.core.exceptions import ValidationError

from apps.authentication.models import User
from apps.plan.models import Plan
from .models import CleanGoMailConfiguration


class EnterpriseCreationForm(forms.Form):
    raison_sociale = forms.CharField(max_length=150, label="Nom de l’entreprise")
    email_contact = forms.EmailField(label="Email de l’entreprise")
    telephone_contact = forms.CharField(max_length=30, label="Téléphone", required=False)
    adresse = forms.CharField(max_length=255, label="Adresse", required=False)
    plan = forms.ModelChoiceField(queryset=Plan.objects.none(), label="Plan")
    statut_abonnement = forms.ChoiceField(
        choices=[("essai", "Essai gratuit"), ("actif", "Abonnement actif")],
        label="Abonnement initial",
    )
    duree_mois = forms.IntegerField(min_value=1, max_value=36, initial=1, label="Durée (mois)", required=False)
    admin_nom = forms.CharField(max_length=100, label="Nom de l’administrateur")
    admin_email = forms.EmailField(label="Email de connexion")
    admin_telephone = forms.CharField(max_length=30, label="Téléphone administrateur", required=False)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plan"].queryset = Plan.objects.filter(actif=True).order_by("prix_mensuel")
        for field in self.fields.values():
            field.widget.attrs["class"] = "admin-control"

    def clean_admin_email(self):
        email = self.cleaned_data["admin_email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Un compte utilise déjà cette adresse email.")
        return email


class SubscriptionActivationForm(forms.Form):
    plan = forms.ModelChoiceField(queryset=Plan.objects.none(), label="Plan")
    duree_mois = forms.IntegerField(min_value=1, max_value=36, initial=1, label="Durée (mois)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plan"].queryset = Plan.objects.filter(actif=True).order_by("prix_mensuel")
        for field in self.fields.values():
            field.widget.attrs["class"] = "admin-control"


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = [
            "code", "nom", "description", "prix_mensuel", "devise",
            "duree_essai_jours", "max_centres", "max_utilisateurs",
            "quota_sms_mensuel", "actif",
        ]
        labels = {
            "code": "Code du plan",
            "nom": "Nom du plan",
            "description": "Description",
            "prix_mensuel": "Prix mensuel",
            "devise": "Devise",
            "duree_essai_jours": "Durée d’essai (jours)",
            "max_centres": "Nombre maximum de centres",
            "max_utilisateurs": "Nombre maximum d’utilisateurs",
            "quota_sms_mensuel": "Quota SMS mensuel",
            "actif": "Plan disponible à la souscription",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "devise": forms.Select(choices=[
                ("XOF", "Franc CFA (XOF)"),
                ("EUR", "Euro (EUR)"),
                ("USD", "Dollar US (USD)"),
            ]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "actif":
                field.widget.attrs["class"] = "admin-control"
        self.fields["code"].widget.attrs["placeholder"] = "Ex. STARTER"
        self.fields["nom"].widget.attrs["placeholder"] = "Ex. Essentiel"
        self.fields["prix_mensuel"].widget.attrs["min"] = "0"
        self.fields["duree_essai_jours"].widget.attrs["min"] = "0"

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        duplicate = Plan.objects.filter(code__iexact=code)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise ValidationError("Un autre plan utilise déjà ce code.")
        return code


class PlatformMailConfigurationForm(forms.ModelForm):
    mot_de_passe = forms.CharField(
        required=False,
        label="Mot de passe d’application SMTP",
        widget=forms.PasswordInput(attrs={
            "class": "admin-control",
            "placeholder": "Laisser vide pour conserver le mot de passe",
            "autocomplete": "new-password",
        }),
    )

    class Meta:
        model = CleanGoMailConfiguration
        fields = [
            "nom_expediteur", "email_expediteur", "serveur_smtp",
            "port_smtp", "utilisateur_smtp", "utiliser_tls",
            "utiliser_ssl", "actif",
        ]
        labels = {
            "nom_expediteur": "Nom de l’expéditeur",
            "email_expediteur": "Email de l’expéditeur",
            "serveur_smtp": "Serveur SMTP",
            "port_smtp": "Port SMTP",
            "utilisateur_smtp": "Utilisateur SMTP",
            "utiliser_tls": "Utiliser TLS",
            "utiliser_ssl": "Utiliser SSL",
            "actif": "Configuration email active",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ("utiliser_tls", "utiliser_ssl", "actif", "mot_de_passe"):
                field.widget.attrs["class"] = "admin-control"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("utiliser_tls") and cleaned.get("utiliser_ssl"):
            raise ValidationError("Choisissez TLS ou SSL, pas les deux simultanément.")
        if not self.instance.pk and not cleaned.get("mot_de_passe"):
            self.add_error("mot_de_passe", "Le mot de passe SMTP est obligatoire.")
        return cleaned
