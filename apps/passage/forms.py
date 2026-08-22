from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.core.exceptions import ValidationError

from apps.authentication.models import User
from apps.client.models import Client
from apps.type_lavage.models import TypeLavage
from apps.vehicule.models import Vehicule

from .models import Passage


class PassageForm(forms.ModelForm):
    class Meta:
        model = Passage
        fields = [
            "date_heure_debut", "date_heure_fin",
            "type_lavage", "piste_id", "employe_realisateur",
            "montant_total", "montant_paye",
            "montant_partiel_verse", "montant_restant", "commission_employe",
            "net_station", "mode_reglement", "statut_reglement", "statut",
            "date_annulation", "motif_annulation",
        ]
        widgets = {
            "date_heure_debut": forms.DateTimeInput(attrs={"class": "client-control", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "date_heure_fin": forms.DateTimeInput(attrs={"class": "client-control", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "date_annulation": forms.DateTimeInput(attrs={"class": "client-control", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "motif_annulation": forms.Textarea(attrs={"class": "client-control passage-textarea", "rows": 3}),
            "mode_reglement": forms.RadioSelect(attrs={"class": "payment-mode-radios"}),
            "type_lavage": forms.RadioSelect(attrs={"class": "wash-type-radios"}),
        }

    def __init__(self, *args, entreprise=None, **kwargs):
        self.entreprise = entreprise
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if "class" not in field.widget.attrs:
                field.widget.attrs["class"] = "client-control"
        self.fields["type_lavage"].queryset = TypeLavage.objects.filter(entreprise=entreprise, deleted_at__isnull=True, actif=True)
        self.fields["type_lavage"].label_from_instance = lambda item: (
            f"{item.libelle} · {item.get_type_vehicule_display()} · "
            f"{item.prix_unitaire:,.0f} {entreprise.devise}"
        )
        self.fields["employe_realisateur"].queryset = User.objects.filter(
            entreprise=entreprise,
            statut="actif",
            role__code__iexact="laveur",
        ).select_related("role").order_by("nom")
        for field_name in [
            "montant_total", "montant_paye", "montant_restant",
            "commission_employe", "net_station",
        ]:
            self.fields[field_name].required = False

    def clean(self):
        cleaned = super().clean()
        debut, fin = cleaned.get("date_heure_debut"), cleaned.get("date_heure_fin")
        if debut and fin and fin < debut:
            self.add_error("date_heure_fin", "La fin doit être postérieure au début.")
        wash_type = cleaned.get("type_lavage")
        total = wash_type.prix_unitaire if wash_type else Decimal("0")
        payment_status = cleaned.get("statut_reglement")
        if payment_status == "paye":
            paid = total
        elif payment_status == "partiel":
            paid = cleaned.get("montant_partiel_verse") or Decimal("0")
            if paid <= 0 or paid >= total:
                self.add_error(
                    "montant_partiel_verse",
                    "Le versement partiel doit être supérieur à zéro et inférieur au total.",
                )
        else:
            paid = Decimal("0")
        paid = min(max(paid, Decimal("0")), total)
        rate = (self.entreprise.taux_commission_laveur or Decimal("0")) / Decimal("100")
        commission = (paid * rate).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        cleaned["montant_total"] = total
        cleaned["montant_paye"] = paid
        cleaned["montant_partiel_verse"] = paid
        cleaned["montant_restant"] = total - paid
        cleaned["commission_employe"] = commission
        cleaned["net_station"] = paid - commission
        if cleaned.get("statut") == "annule" and not cleaned.get("motif_annulation"):
            self.add_error("motif_annulation", "Indiquez le motif de l’annulation.")
        return cleaned
