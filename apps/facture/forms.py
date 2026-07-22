from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from apps.client.models import Client
from apps.passage.models import Passage
from .models import Facture


class FactureForm(forms.ModelForm):
    class Meta:
        model = Facture
        fields = ["client", "passage", "objet", "date_emission", "date_echeance", "montant_ht", "remise", "taxe", "notes"]
        widgets = {
            "date_emission": forms.DateInput(attrs={"type": "date"}),
            "date_echeance": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, entreprise=None, **kwargs):
        self.entreprise = entreprise
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = Client.objects.filter(entreprise=entreprise, deleted_at__isnull=True)
        passages = Passage.objects.filter(entreprise=entreprise, deleted_at__isnull=True).select_related("client", "vehicule", "type_lavage")
        if self.instance.pk and self.instance.passage_id:
            passages = passages.filter(Q(facture__isnull=True) | Q(pk=self.instance.passage_id))
        else:
            passages = passages.filter(facture__isnull=True)
        self.fields["passage"].queryset = passages
        self.fields["passage"].required = False
        for field in self.fields.values():
            field.widget.attrs["class"] = "client-control"

    def clean(self):
        cleaned = super().clean()
        passage, client = cleaned.get("passage"), cleaned.get("client")
        if passage and client and passage.client_id != client.pk:
            self.add_error("passage", "Ce passage n’appartient pas au client sélectionné.")
        if passage:
            cleaned["montant_ht"] = passage.montant_total
        emission, echeance = cleaned.get("date_emission"), cleaned.get("date_echeance")
        if emission and echeance and echeance < emission:
            self.add_error("date_echeance", "L’échéance doit être postérieure à l’émission.")
        return cleaned
