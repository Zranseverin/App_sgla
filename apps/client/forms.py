from django import forms
from django.core.exceptions import ValidationError

from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["nom_complet", "adresse", "telephone", "email"]
        widgets = {
            "nom_complet": forms.TextInput(attrs={"class": "client-control", "placeholder": "Nom et prénoms"}),
            "adresse": forms.TextInput(attrs={"class": "client-control", "placeholder": "Adresse complète"}),
            "telephone": forms.TextInput(attrs={"class": "client-control", "placeholder": "+225 07 00 00 00 00"}),
            "email": forms.EmailInput(attrs={"class": "client-control", "placeholder": "client@example.com"}),
        }

    def __init__(self, *args, entreprise=None, **kwargs):
        self.entreprise = entreprise
        super().__init__(*args, **kwargs)

    def clean_telephone(self):
        telephone = self.cleaned_data["telephone"].strip()
        queryset = Client.objects.filter(
            entreprise=self.entreprise,
            telephone=telephone,
            deleted_at__isnull=True,
        )
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("Un client utilise déjà ce numéro de téléphone.")
        return telephone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            return email
        queryset = Client.objects.filter(
            entreprise=self.entreprise,
            email__iexact=email,
            deleted_at__isnull=True,
        )
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("Un client utilise déjà cette adresse email.")
        return email
