from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class FocusModeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testwarrior',
            email='testwarrior@example.com',
            password='testpassword123'
        )

    def test_focus_url_reverse_and_status(self):
        # Reverse resolution
        url = reverse('focus:index')
        self.assertEqual(url, '/focus/')
        
        url_alias = reverse('focus:focus')
        self.assertEqual(url_alias, '/focus/')

        # Status 200 and template
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'focus/index.html')

    def test_focus_standalone_structure(self):
        response = self.client.get(reverse('focus:index'))
        content = response.content.decode('utf-8')

        # Static assets
        self.assertIn('focus/css/focus', content)
        self.assertIn('focus/js/focus', content)

        # Core DOM elements
        self.assertIn('id="rain"', content)
        self.assertIn('id="stage"', content)
        self.assertIn('id="mainClock"', content)
        self.assertIn('id="ampm"', content)
        self.assertIn('id="timer"', content)
        self.assertIn('id="cd"', content)
        self.assertIn('id="go"', content)
        self.assertIn('id="plus"', content)
        self.assertIn('id="minus"', content)
        self.assertIn('id="reset"', content)
        self.assertIn('id="fullscreen-btn"', content)

        # Top-left back to dashboard button
        self.assertIn('class="back-to-dashboard"', content)
        self.assertIn(f'href="{reverse("dashboard")}"', content)
        self.assertIn('Back to Dashboard', content)

        # Standalone: No navbar, no global footer, no oaths
        self.assertNotIn('id="global-navbar"', content)
        self.assertNotIn('Take the Oath', content)
        self.assertNotIn('footer', content.lower().split('</body')[0].split('<body')[1] if '<body' in content else '')

    def test_navbar_focus_mode_integration(self):
        self.client.login(username='testwarrior', password='testpassword123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        # Focus Mode links in desktop and mobile menu
        focus_url = reverse('focus:index')
        self.assertIn(f'href="{focus_url}"', content)
        self.assertIn('Focus Mode', content)

    def test_profile_backend_preserved(self):
        profile_url = reverse('profile')
        self.assertEqual(profile_url, '/accounts/profile/')
        self.client.login(username='testwarrior', password='testpassword123')
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 200)
