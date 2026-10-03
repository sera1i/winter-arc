from django.test import TestCase
from django.urls import reverse
from accounts.models import CustomUser, Profile

class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='testuser', password='password123', email='test@example.com')
        # Profile is created by signal or view in our case, let's ensure it exists
        Profile.objects.get_or_create(user=self.user)

    def test_login_successful(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'password123'})
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_invalid(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_protected_profile_access(self):
        # Unauthenticated
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('profile')}")
        
        # Authenticated
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_update(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('profile'), {
            'display_name': 'Test Display',
            'timezone': 'America/New_York',
            'bio': 'Test bio'
        })
        self.assertRedirects(response, reverse('profile'))
        
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.display_name, 'Test Display')
        self.assertEqual(self.user.profile.timezone, 'America/New_York')

    def test_registration(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
        })
        self.assertEqual(response.status_code, 200)


class DashboardTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='dashuser', password='password123')
        Profile.objects.get_or_create(user=self.user)
        self.client.login(username='dashuser', password='password123')

    def test_dashboard_with_no_arcs(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['primary_arc'])
        self.assertContains(response, 'Create your first Arc')
        self.assertContains(response, 'No active Arcs found')

    def test_dashboard_with_active_arc_not_primary(self):
        from arcs.models import Arc
        from datetime import date, timedelta
        Arc.objects.create(
            user=self.user,
            name="Non-Primary Active Arc",
            objective="Hold the line",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='ACTIVE',
            is_primary=False
        )
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        # MUST NEVER arbitrarily select active arc if user did not mark it primary
        self.assertIsNone(response.context['primary_arc'])
        self.assertContains(response, 'Select Primary Arc')
        self.assertContains(response, 'No Primary Arc selected')

    def test_dashboard_with_primary_arc(self):
        from arcs.models import Arc
        from goals.models import Goal
        from datetime import date, timedelta
        arc = Arc.objects.create(
            user=self.user,
            name="Alpha Arc",
            objective="Mastery",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='ACTIVE',
            is_primary=True
        )
        goal = Goal.objects.create(
            user=self.user,
            arc=arc,
            title="Conquer Mountain",
            status='IN_PROGRESS'
        )
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['primary_arc'], arc)
        self.assertIn(goal, response.context['goals'])
        self.assertContains(response, 'Alpha Arc')
        self.assertContains(response, 'Conquer Mountain')

