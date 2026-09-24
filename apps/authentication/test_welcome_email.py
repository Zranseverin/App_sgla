from types import SimpleNamespace
from unittest.mock import patch

from django.core import mail
from django.test import SimpleTestCase, override_settings

from .forms import RegisterForm
from .views import send_welcome_email


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   PUBLIC_BASE_URL='https://cleango.example/', DEFAULT_FROM_EMAIL='hello@cleango.example')
class WelcomeEmailTests(SimpleTestCase):
    def test_welcome_contains_login_url_without_password(self):
        user = SimpleNamespace(nom='Client', email='client@example.com')
        send_welcome_email(user, SimpleNamespace(raison_sociale='Station'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['client@example.com'])
        self.assertIn('https://cleango.example/connexion/', mail.outbox[0].body)
        self.assertIn('Continuer avec Google', mail.outbox[0].body)

    def test_failed_delivery_is_not_reported_as_success(self):
        with patch('apps.authentication.views.send_mail', return_value=0):
            with self.assertRaises(RuntimeError):
                send_welcome_email(SimpleNamespace(nom='Client', email='client@example.com'),
                                   SimpleNamespace(raison_sociale='Station'))

    def test_registration_supports_browser_password_generation(self):
        for name in ('password', 'confirm_password'):
            self.assertEqual(RegisterForm.base_fields[name].widget.attrs['autocomplete'], 'new-password')
        self.assertEqual(RegisterForm.base_fields['email'].widget.attrs['autocomplete'], 'username')
