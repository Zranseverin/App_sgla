from django import forms
from django.core.exceptions import ValidationError

from apps.client.models import Client

from .models import Vehicule


class VehiculeForm(forms.ModelForm):
    class Meta:
        model = Vehicule
        fields = [
            "client", "immatriculation", "marque", "modele",
            "couleur", "type_vehicule",
        ]
        widgets = {
            "client": forms.Select(attrs={"class": "client-control"}),
            "immatriculation": forms.TextInput(attrs={"class": "client-control", "placeholder": "Ex. AB-123-CD"}),
            "marque": forms.TextInput(attrs={"class": "client-control", "placeholder": "Ex. Toyota"}),
            "modele": forms.TextInput(attrs={"class": "client-control", "placeholder": "Ex. Corolla"}),
            "couleur": forms.TextInput(attrs={"class": "client-control", "placeholder": "Ex. Blanc"}),
            "type_vehicule": forms.TextInput(attrs={"class": "client-control", "placeholder": "Ex. Berline, SUV, Camion"}),
        }

    def __init__(self, *args, entreprise=None, **kwargs):
        self.entreprise = entreprise
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = Client.objects.filter(
            entreprise=entreprise,
            deleted_at__isnull=True,
        ).order_by("nom_complet")

    def clean_immatriculation(self):
        immatriculation = self.cleaned_data["immatriculation"].strip().upper()
        queryset = Vehicule.objects.filter(
            entreprise=self.entreprise,
            immatriculation__iexact=immatriculation,
            deleted_at__isnull=True,
        )
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("Cette immatriculation existe déjà.")
        return immatriculation
