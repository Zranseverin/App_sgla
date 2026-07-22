from django import forms
from .models import MouvementCaisse


class MouvementCaisseForm(forms.ModelForm):
    class Meta:
        model = MouvementCaisse
        fields = ["montant", "motif", "reference", "mode_reglement", "date_mouvement", "notes"]
        widgets = {
            "date_mouvement": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "client-control"

    def clean_montant(self):
        montant = self.cleaned_data["montant"]
        if montant <= 0:
            raise forms.ValidationError("Le montant de la sortie doit être supérieur à zéro.")
        return montant


class EncaissementPassageForm(forms.Form):
    montant = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        label="Nouveau versement",
        widget=forms.NumberInput(attrs={"class": "client-control", "step": "0.01", "inputmode": "decimal"}),
    )
    mode_reglement = forms.ChoiceField(
        choices=MouvementCaisse.MODES,
        label="Mode de règlement",
        widget=forms.Select(attrs={"class": "client-control"}),
    )

    def __init__(self, *args, montant_restant=None, **kwargs):
        self.montant_restant = montant_restant
        super().__init__(*args, **kwargs)
        if montant_restant is not None:
            self.fields["montant"].widget.attrs["max"] = str(montant_restant)

    def clean_montant(self):
        montant = self.cleaned_data["montant"]
        if self.montant_restant is not None and montant > self.montant_restant:
            raise forms.ValidationError("Le versement ne peut pas dépasser le montant restant.")
        return montant
