from django import forms
from django.core.exceptions import ValidationError

from .models import TypeLavage


class TypeLavageForm(forms.ModelForm):
    class Meta:
        model = TypeLavage
        fields = [
            "libelle",
            "description",
            "prix_unitaire",
            "duree_estimee_min",
            "actif",
        ]
        widgets = {
            "libelle": forms.TextInput(attrs={"class": "wash-control", "placeholder": "Ex. Lavage complet"}),
            "description": forms.Textarea(attrs={"class": "wash-control wash-textarea", "rows": 4, "placeholder": "Description du service"}),
            "prix_unitaire": forms.NumberInput(attrs={"class": "wash-control", "min": "0", "step": "0.01"}),
            "duree_estimee_min": forms.NumberInput(attrs={"class": "wash-control", "min": "1", "placeholder": "Durée en minutes"}),
            "actif": forms.CheckboxInput(attrs={"class": "wash-checkbox"}),
        }

    def __init__(self, *args, entreprise=None, **kwargs):
        self.entreprise = entreprise
        super().__init__(*args, **kwargs)

    def clean_libelle(self):
        libelle = self.cleaned_data["libelle"].strip()
        queryset = TypeLavage.objects.filter(
            entreprise=self.entreprise,
            libelle__iexact=libelle,
            deleted_at__isnull=True,
        )
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("Ce type de lavage existe déjà.")
        return libelle

    def clean_duree_estimee_min(self):
        duree = self.cleaned_data.get("duree_estimee_min")
        if duree is not None and duree <= 0:
            raise ValidationError("La durée doit être supérieure à zéro.")
        return duree
