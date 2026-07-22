from django import forms
from django.core.exceptions import ValidationError
from .models import User
from apps.plan.models import Plan
from apps.entreprises.models import Entreprise
from apps.core.models import Civilite, ConfigurationMail
from apps.roles.models import Role


class LoginForm(forms.Form):
    """Formulaire de connexion"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre mot de passe'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        
        if email and password:
            user = User.objects.filter(email__iexact=email).first()
            if user is None or not user.check_password(password):
                raise ValidationError('Email ou mot de passe incorrect.')
            if user.statut != 'actif':
                raise ValidationError(f'Votre compte est {user.statut}. Veuillez contacter l\'administrateur.')
            self.user = user
        
        return cleaned_data


class RegisterForm(forms.Form):
    """Formulaire d'inscription"""
    nom = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre nom complet'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre email'
        })
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe (minimum 8 caractères)'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        })
    )
    entreprise_nom = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom de votre entreprise'
        })
    )
    telephone_contact = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+225 00 00 00 00 00'})
    )
    logo_url = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control file-control', 'accept': 'image/png,image/jpeg,image/webp,image/svg+xml'})
    )
    favicon_url = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control file-control', 'accept': 'image/png,image/x-icon,image/vnd.microsoft.icon'})
    )
    slogan = forms.CharField(
        max_length=180,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre promesse en quelques mots'
        })
    )
    couleur_principale = forms.CharField(
        max_length=7,
        initial='#0e7c86',
        widget=forms.TextInput(attrs={'class': 'form-control color-input', 'type': 'color'})
    )
    devise = forms.ChoiceField(
        choices=[
            ('XOF', 'Franc CFA (XOF)'),
            ('EUR', 'Euro (EUR)'),
            ('USD', 'Dollar US (USD)'),
            ('CAD', 'Dollar canadien (CAD)'),
        ],
        initial='XOF',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    langue = forms.ChoiceField(
        choices=[('fr', 'Français'), ('en', 'English')],
        initial='fr',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    fuseau_horaire = forms.ChoiceField(
        choices=[
            ('Africa/Abidjan', 'Abidjan (GMT)'),
            ('Africa/Dakar', 'Dakar (GMT)'),
            ('Africa/Douala', 'Douala (GMT+1)'),
            ('Africa/Lagos', 'Lagos (GMT+1)'),
            ('Europe/Paris', 'Paris'),
            ('UTC', 'UTC'),
        ],
        initial='Africa/Abidjan',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    plan = forms.ModelChoiceField(
        queryset=Plan.objects.none(),
        empty_label=None,
        widget=forms.RadioSelect()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plan'].queryset = Plan.objects.filter(actif=True).order_by('prix_mensuel')

    def clean_couleur_principale(self):
        couleur = self.cleaned_data.get('couleur_principale', '')
        if len(couleur) != 7 or not couleur.startswith('#'):
            raise ValidationError('Sélectionnez une couleur valide.')
        try:
            int(couleur[1:], 16)
        except ValueError:
            raise ValidationError('Sélectionnez une couleur valide.')
        return couleur.upper()

    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Cet email est déjà utilisé.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError('Les mots de passe ne correspondent pas.')
        
        return cleaned_data


class UserProfileForm(forms.ModelForm):
    """Formulaire de mise à jour du profil"""
    class Meta:
        model = User
        fields = ['nom', 'email', 'photo']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'form-control file-control',
                'accept': 'image/png,image/jpeg,image/webp',
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        instance = getattr(self, 'instance', None)
        if instance and User.objects.exclude(pk=instance.pk).filter(email=email).exists():
            raise ValidationError('Cet email est déjà utilisé par un autre utilisateur.')
        return email


class UserPasswordChangeForm(forms.Form):
    """Formulaire de changement de mot de passe"""
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe actuel'
        })
    )
    new_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nouveau mot de passe (minimum 8 caractères)'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le nouveau mot de passe'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise ValidationError('Mot de passe actuel incorrect.')
        return old_password
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError('Les mots de passe ne correspondent pas.')
        
        return cleaned_data
    
    def save(self):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save()


class PasswordResetRequestForm(forms.Form):
    """Formulaire de demande de réinitialisation"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre email'
        })
    )


class PasswordResetConfirmForm(forms.Form):
    """Formulaire de confirmation de réinitialisation"""
    new_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nouveau mot de passe (minimum 8 caractères)'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError('Les mots de passe ne correspondent pas.')
        
        return cleaned_data


class UserCreateForm(forms.ModelForm):
    """Formulaire de création d'utilisateur (admin)"""

    class Meta:
        model = User
        fields = ['civilite', 'nom', 'email', 'telephone', 'adresse', 'role']
        widgets = {
            'civilite': forms.Select(attrs={'class': 'form-control'}),
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+225 07 00 00 00 00',
            }),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        entreprise = kwargs.pop('entreprise', None)
        super().__init__(*args, **kwargs)
        if entreprise:
            self.fields['role'].queryset = Role.objects.filter(entreprise=entreprise)
            self.fields['civilite'].queryset = Civilite.objects.filter(
                entreprise=entreprise,
                actif=True,
            ).order_by('libelle')
        self.fields['civilite'].required = True
        self.fields['telephone'].required = True
        self.fields['adresse'].required = True
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        instance = getattr(self, 'instance', None)
        if instance and User.objects.exclude(pk=instance.pk).filter(email=email).exists():
            raise ValidationError('Cet email est déjà utilisé.')
        return email
    
class UserUpdateForm(forms.ModelForm):
    """Formulaire de mise à jour d'utilisateur (admin)"""
    class Meta:
        model = User
        fields = ['nom', 'email', 'telephone', 'adresse', 'role', 'statut']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, entreprise=None, **kwargs):
        super().__init__(*args, **kwargs)
        if entreprise:
            self.fields['role'].queryset = Role.objects.filter(entreprise=entreprise)
        self.fields['statut'].widget.choices = [('actif', 'Actif'), ('inactif', 'Inactif')]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        instance = getattr(self, 'instance', None)
        if instance and User.objects.exclude(pk=instance.pk).filter(email=email).exists():
            raise ValidationError('Cet email est déjà utilisé.')
        return email


class EnterpriseProfileForm(forms.ModelForm):
    """Paramètres généraux et identité visuelle de l'entreprise."""

    class Meta:
        model = Entreprise
        fields = [
            'raison_sociale',
            'slogan',
            'logo_url',
            'favicon_url',
            'couleur_principale',
            'email_contact',
            'telephone_contact',
            'devise',
            'langue',
            'fuseau_horaire',
        ]
        widgets = {
            'raison_sociale': forms.TextInput(attrs={'class': 'form-control'}),
            'slogan': forms.TextInput(attrs={'class': 'form-control'}),
            'logo_url': forms.ClearableFileInput(attrs={'class': 'form-control file-control', 'accept': 'image/png,image/jpeg,image/webp,image/svg+xml'}),
            'favicon_url': forms.ClearableFileInput(attrs={'class': 'form-control file-control', 'accept': 'image/png,image/x-icon,image/vnd.microsoft.icon'}),
            'couleur_principale': forms.TextInput(attrs={'class': 'form-control color-control', 'type': 'color'}),
            'email_contact': forms.EmailInput(attrs={'class': 'form-control'}),
            'telephone_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'devise': forms.Select(
                choices=[('XOF', 'Franc CFA (XOF)'), ('EUR', 'Euro (EUR)'), ('USD', 'Dollar US (USD)')],
                attrs={'class': 'form-control'},
            ),
            'langue': forms.Select(
                choices=[('fr', 'Français'), ('en', 'English')],
                attrs={'class': 'form-control'},
            ),
            'fuseau_horaire': forms.Select(
                choices=[
                    ('Africa/Abidjan', 'Abidjan (GMT)'),
                    ('Africa/Dakar', 'Dakar (GMT)'),
                    ('Africa/Douala', 'Douala (GMT+1)'),
                    ('Africa/Lagos', 'Lagos (GMT+1)'),
                    ('Europe/Paris', 'Paris'),
                    ('UTC', 'UTC'),
                ],
                attrs={'class': 'form-control'},
            ),
        }

    def clean_couleur_principale(self):
        couleur = self.cleaned_data.get('couleur_principale')
        if not couleur:
            return couleur
        if len(couleur) != 7 or not couleur.startswith('#'):
            raise ValidationError('Sélectionnez une couleur valide.')
        try:
            int(couleur[1:], 16)
        except ValueError:
            raise ValidationError('Sélectionnez une couleur valide.')
        return couleur.upper()


class CommissionSettingsForm(forms.ModelForm):
    taux_commission_laveur = forms.CharField(
        label='Pourcentage du laveur',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'inputmode': 'decimal',
            'placeholder': 'Ex. 20 ou 15,5',
            'autocomplete': 'off',
        }),
    )

    class Meta:
        model = Entreprise
        fields = ['taux_commission_laveur']

    def clean_taux_commission_laveur(self):
        from decimal import Decimal, InvalidOperation

        raw_value = self.cleaned_data['taux_commission_laveur'].strip().replace(',', '.')
        try:
            taux = Decimal(raw_value)
        except InvalidOperation:
            raise ValidationError('Saisissez un pourcentage valide, par exemple 20 ou 15,5.')
        if taux < 0 or taux > 100:
            raise ValidationError('Le pourcentage doit être compris entre 0 et 100.')
        return taux


class RoleCreationForm(forms.Form):
    libelle = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex. Superviseur'}),
    )

    def __init__(self, *args, entreprise=None, instance=None, **kwargs):
        self.entreprise = entreprise
        self.instance = instance
        super().__init__(*args, **kwargs)

    def clean_libelle(self):
        libelle = self.cleaned_data['libelle'].strip()
        queryset = Role.objects.filter(
            entreprise=self.entreprise,
            libelle__iexact=libelle,
        )
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError('Ce rôle existe déjà.')
        return libelle


class CiviliteCreationForm(forms.ModelForm):
    class Meta:
        model = Civilite
        fields = ['libelle', 'actif']
        widgets = {
            'libelle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex. Madame'}),
            'actif': forms.CheckboxInput(attrs={'class': 'checkbox-control'}),
        }

    def __init__(self, *args, entreprise=None, **kwargs):
        self.entreprise = entreprise
        super().__init__(*args, **kwargs)

    def clean_libelle(self):
        libelle = self.cleaned_data['libelle'].strip()
        if Civilite.objects.filter(
            entreprise=self.entreprise,
            libelle__iexact=libelle,
        ).exists():
            raise ValidationError('Cette civilité existe déjà.')
        return libelle


class MailConfigurationForm(forms.ModelForm):
    mot_de_passe = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Laisser vide pour conserver le mot de passe',
            'autocomplete': 'new-password',
        }),
        label="Mot de passe d’application",
    )

    class Meta:
        model = ConfigurationMail
        fields = [
            'nom_expediteur', 'email_expediteur', 'serveur_smtp',
            'port_smtp', 'utilisateur_smtp', 'utiliser_tls',
            'utiliser_ssl', 'actif',
        ]
        widgets = {
            'nom_expediteur': forms.TextInput(attrs={'class': 'form-control'}),
            'email_expediteur': forms.EmailInput(attrs={'class': 'form-control'}),
            'serveur_smtp': forms.TextInput(attrs={'class': 'form-control'}),
            'port_smtp': forms.NumberInput(attrs={'class': 'form-control'}),
            'utilisateur_smtp': forms.TextInput(attrs={'class': 'form-control'}),
            'utiliser_tls': forms.CheckboxInput(attrs={'class': 'checkbox-control'}),
            'utiliser_ssl': forms.CheckboxInput(attrs={'class': 'checkbox-control'}),
            'actif': forms.CheckboxInput(attrs={'class': 'checkbox-control'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('utiliser_tls') and cleaned.get('utiliser_ssl'):
            raise ValidationError('Choisissez TLS ou SSL, pas les deux simultanément.')
        if not self.instance.pk and not cleaned.get('mot_de_passe'):
            self.add_error('mot_de_passe', 'Le mot de passe est requis.')
        return cleaned
