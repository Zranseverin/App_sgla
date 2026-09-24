import io
import json
from unittest.mock import Mock, patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, SimpleTestCase

from .views import google_auth_callback


class GoogleLoginTests(SimpleTestCase):
    def callback(self, users, **changes):
        request = RequestFactory().get('/auth/google/callback/', {'state': 'test-state', 'code': 'code'})
        request.session = SessionStore()
        request.session['google_oauth_state'] = 'test-state'
        request.session['google_signup_identity'] = {'email': 'stale@example.com'}
        request._messages = FallbackStorage(request)
        profile = {'sub': 'google-sub', 'email': 'user@gmail.com', 'email_verified': True}
        profile.update(changes)
        responses = [io.StringIO(json.dumps({'access_token': 'token'})), io.StringIO(json.dumps(profile))]
        with patch('apps.authentication.views.urlopen', side_effect=responses), patch('apps.authentication.views.User.objects.filter') as lookup:
            lookup.return_value.__getitem__.return_value = users
            response = google_auth_callback(request)
        return request, response

    def test_existing_active_account_logs_in(self):
        user = Mock(pk=42, statut='actif', nom='Client')
        request, response = self.callback([user])
        self.assertEqual(request.session['utilisateur_id'], 42)
        self.assertNotIn('google_signup_identity', request.session)
        self.assertTrue(request.session.get_expire_at_browser_close())
        self.assertEqual(response.url, '/dashboard/index/')
        user.save.assert_called_once_with(update_fields=['updated_at'])

    def test_inactive_and_ambiguous_accounts_are_rejected(self):
        for users in ([Mock(statut='inactif')], [Mock(), Mock()]):
            request, response = self.callback(users)
            self.assertNotIn('utilisateur_id', request.session)
            self.assertEqual(response.url, '/connexion/')

    def test_unverified_or_external_email_cannot_log_in(self):
        for changes in ({'email_verified': False}, {'email_verified': 'false'}, {'sub': ''}, {'email': 'user@example.com'}):
            request, _ = self.callback([Mock(statut='actif')], **changes)
            self.assertNotIn('utilisateur_id', request.session)

    def test_unknown_account_continues_registration(self):
        request, response = self.callback([])
        self.assertEqual(response.url, '/inscription/')
        self.assertEqual(request.session['google_signup_identity']['sub'], 'google-sub')

    def test_invalid_state_does_not_contact_google(self):
        request = RequestFactory().get('/auth/google/callback/', {'state': 'wrong', 'code': 'code'})
        request.session = SessionStore()
        request.session['google_oauth_state'] = 'expected'
        request._messages = FallbackStorage(request)
        with patch('apps.authentication.views.urlopen') as remote:
            google_auth_callback(request)
        remote.assert_not_called()
        self.assertNotIn('utilisateur_id', request.session)
