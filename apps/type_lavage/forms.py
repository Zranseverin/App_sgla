from django import forms
from django.forms import BaseFormSet, formset_factory
from django.core.exceptions import ValidationError

from .models import TypeLavage


class TypeLavageForm(forms.ModelForm):
    class Meta:
        model = TypeLavage
        fields = [
            "libelle",
            "type_vehicule",
            "description",
            "prix_unitaire",
            "duree_estimee_min",
            "actif",
        ]
        widgets = {
            "libelle": forms.TextInput(attrs={"class": "wash-control", "placeholder": "Ex. Lavage complet"}),
            "type_vehicule": forms.Select(attrs={"class": "wash-control"}),
            "description": forms.Textarea(attrs={"class": "wash-control wash-textarea", "rows": 4, "placeholder": "Description du service"}),
            "prix_unitaire": forms.NumberInput(attrs={"class": "wash-control", "min": "0", "step": "0.01", "placeholder": "Ex. 5 000"}),
            "duree_estimee_min": forms.NumberInput(attrs={"class": "wash-control", "min": "1", "placeholder": "Ex. 30"}),
            "actif": forms.CheckboxInput(attrs={"class": "wash-checkbox"}),
        }

    def __init__(self, *args, entreprise=None, **kwargs):
        self.entreprise = entreprise
        super().__init__(*args, **kwargs)
        self.fields["type_vehicule"].required = False
        self.fields["type_vehicule"].initial = self.instance.type_vehicule or "tous"

    def clean_type_vehicule(self):
        return self.cleaned_data.get("type_vehicule") or "tous"

    def clean_libelle(self):
        libelle = self.cleaned_data["libelle"].strip()
        queryset = TypeLavage.objects.filter(
            entreprise=self.entreprise,
            libelle__iexact=libelle,
            type_vehicule=self.data.get("type_vehicule") or self.instance.type_vehicule or "tous",
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


class TypeLavageBatchHeaderForm(forms.Form):
    type_vehicule = forms.ChoiceField(
        choices=TypeLavage.TYPES_VEHICULE,
        initial="tous",
        widget=forms.Select(attrs={"class": "wash-control"}),
        label="Type de véhicule",
    )


class TypeLavageLineForm(forms.Form):
    libelle = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "wash-control", "placeholder": "Ex. Lavage complet"}))
    prix_unitaire = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2, widget=forms.NumberInput(attrs={"class": "wash-control", "min": "0", "step": "0.01", "placeholder": "Ex. 5 000"}))
    duree_estimee_min = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={"class": "wash-control", "min": "1", "placeholder": "Ex. 30"}))
    description = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "wash-control", "placeholder": "Description facultative"}))
    actif = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={"class": "wash-checkbox"}))

    def clean_libelle(self):
        return self.cleaned_data["libelle"].strip()


class BaseTypeLavageLineFormSet(BaseFormSet):
    def __init__(self, *args, entreprise=None, type_vehicule="tous", **kwargs):
        self.entreprise = entreprise
        self.type_vehicule = type_vehicule
        super().__init__(*args, **kwargs)

    def clean(self):
        if any(self.errors):
            return
        labels = set()
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            label = form.cleaned_data["libelle"].casefold()
            if label in labels:
                raise ValidationError("Chaque libellé doit être unique dans la liste.")
            labels.add(label)
            if TypeLavage.objects.filter(
                entreprise=self.entreprise,
                type_vehicule=self.type_vehicule,
                libelle__iexact=form.cleaned_data["libelle"],
                deleted_at__isnull=True,
            ).exists():
                raise ValidationError(f"La prestation « {form.cleaned_data['libelle']} » existe déjà pour ce véhicule.")


TypeLavageLineFormSet = formset_factory(TypeLavageLineForm, formset=BaseTypeLavageLineFormSet, extra=1, can_delete=True, min_num=1, validate_min=True)
