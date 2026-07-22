from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.authentication.models import User
from .models import Employe


class EmployeForm(forms.ModelForm):
    class Meta:
        model = Employe
        fields = ["user", "poste", "date_naissance", "date_embauche", "numero_piece_identite", "numero_cnps", "salaire_brut", "categorie_permis", "numero_permis", "expiration_permis", "banque", "iban", "statut"]
        widgets = {
            "date_naissance": forms.DateInput(attrs={"type": "date"}),
            "date_embauche": forms.DateInput(attrs={"type": "date"}),
            "expiration_permis": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, entreprise=None, **kwargs):
        self.entreprise = entreprise
        super().__init__(*args, **kwargs)
        users = User.objects.filter(entreprise=entreprise).order_by("nom")
        users = users.filter(Q(fiche_employe__isnull=True) | Q(pk=self.instance.user_id)) if self.instance.pk else users.filter(fiche_employe__isnull=True)
        self.fields["user"].queryset = users
        for field in self.fields.values():
            field.widget.attrs["class"] = "client-control"

    def clean_numero_cnps(self):
        value = (self.cleaned_data.get("numero_cnps") or "").strip() or None
        if value:
            queryset = Employe.objects.filter(entreprise=self.entreprise, numero_cnps__iexact=value)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise ValidationError("Ce numéro CNPS est déjà utilisé.")
        return value
