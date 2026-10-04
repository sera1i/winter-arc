from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from zoneinfo import ZoneInfo
from journal.models import JournalEntry
from gamification.models import XPEvent
from analytics.models import ActivityEvent

User = get_user_model()


class JournalFeatureTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='warrior_a',
            email='warrior_a@winterarc.com',
            password='Password123!'
        )
        self.user_b = User.objects.create_user(
            username='warrior_b',
            email='warrior_b@winterarc.com',
            password='Password123!'
        )
        from accounts.models import Profile
        Profile.objects.get_or_create(user=self.user_a, defaults={'timezone': 'Asia/Kolkata'})
        Profile.objects.get_or_create(user=self.user_b, defaults={'timezone': 'Asia/Kolkata'})

        self.client_a = Client()
        self.client_a.login(username='warrior_a', password='Password123!')

        self.client_b = Client()
        self.client_b.login(username='warrior_b', password='Password123!')

        self.anon_client = Client()

    def test_anonymous_user_cannot_access_journal(self):
        """Unauthenticated access redirects to login."""
        urls = [
            reverse('journal:list'),
            reverse('journal:create'),
        ]
        for url in urls:
            resp = self.anon_client.get(url)
            self.assertEqual(resp.status_code, 302)
            self.assertIn('/accounts/login/', resp.url)

    def test_authenticated_user_can_view_journal_list_and_empty_state(self):
        """Authenticated user sees empty state when no entries exist."""
        resp = self.client_a.get(reverse('journal:list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No journal entries yet.')

    def test_create_journal_entry_awards_40_xp_and_logs_activity(self):
        """Creating an entry awards 40 XP and records a JOURNAL_ENTRY activity event."""
        today = date(2026, 10, 4)
        post_data = {
            'local_date': today.isoformat(),
            'mood': 4,
            'energy': 5,
            'sleep_hours': 8.0,
            'reflection': 'Trained at dawn in freezing winds. Mind unwavering.',
            'notes': 'Increase volume by 10% tomorrow.'
        }
        resp = self.client_a.post(reverse('journal:create'), post_data)
        self.assertEqual(resp.status_code, 302)

        entry = JournalEntry.objects.filter(user=self.user_a, local_date=today).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.mood, 4)
        self.assertEqual(entry.energy, 5)
        self.assertEqual(entry.sleep_hours, 8.0)
        self.assertEqual(entry.reflection, 'Trained at dawn in freezing winds. Mind unwavering.')

        # Verify XP awarded
        xp_events = XPEvent.objects.filter(user=self.user_a, source_type='journal')
        self.assertEqual(xp_events.count(), 1)
        self.assertEqual(xp_events.first().amount, 40)

        # Verify Activity logged
        activity_events = ActivityEvent.objects.filter(user=self.user_a, source_type='journal')
        self.assertEqual(activity_events.count(), 1)
        self.assertEqual(activity_events.first().event_type, 'JOURNAL_ENTRY')

    def test_xp_idempotency_duplicate_create_same_day_blocked_by_validation(self):
        """Form validation blocks creating two journal entries for the exact same local date."""
        today = date(2026, 10, 4)
        JournalEntry.objects.create(
            user=self.user_a,
            local_date=today,
            reflection='First entry'
        )
        post_data = {
            'local_date': today.isoformat(),
            'mood': 3,
            'reflection': 'Duplicate attempt'
        }
        resp = self.client_a.post(reverse('journal:create'), post_data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'A journal entry already exists for {today}')
        self.assertEqual(JournalEntry.objects.filter(user=self.user_a, local_date=today).count(), 1)

    def test_editing_entry_preserves_xp_and_does_not_award_extra_xp(self):
        """Editing an existing journal entry does NOT award additional XP."""
        today = date(2026, 10, 4)
        entry = JournalEntry.objects.create(
            user=self.user_a,
            local_date=today,
            reflection='Initial draft'
        )
        XPEvent.objects.create(
            user=self.user_a,
            source_type='journal',
            source_id=f"{entry.pk}_{today}",
            amount=40,
            description=f'Journal reflection for {today}'
        )
        self.assertEqual(XPEvent.objects.filter(user=self.user_a, source_type='journal').count(), 1)

        # Edit entry
        update_data = {
            'local_date': today.isoformat(),
            'mood': 5,
            'energy': 4,
            'sleep_hours': 7.5,
            'reflection': 'Updated and refined daily reflection.',
            'notes': 'Refined notes.'
        }
        resp = self.client_a.post(reverse('journal:update', args=[entry.pk]), update_data)
        self.assertEqual(resp.status_code, 302)

        entry.refresh_from_db()
        self.assertEqual(entry.reflection, 'Updated and refined daily reflection.')
        self.assertEqual(entry.mood, 5)

        # Still exactly 1 XP event
        self.assertEqual(XPEvent.objects.filter(user=self.user_a, source_type='journal').count(), 1)

    def test_cross_user_isolation_reading(self):
        """User B cannot access or view User A's journal entry."""
        today = date(2026, 10, 4)
        entry_a = JournalEntry.objects.create(
            user=self.user_a,
            local_date=today,
            reflection='Secret thoughts of warrior A.'
        )

        # User B tries to view detail
        resp = self.client_b.get(reverse('journal:detail', args=[entry_a.pk]))
        self.assertEqual(resp.status_code, 404)

        # User B's list should not include User A's entry
        resp_list = self.client_b.get(reverse('journal:list'))
        self.assertNotContains(resp_list, 'Secret thoughts of warrior A.')

    def test_cross_user_isolation_updating(self):
        """User B cannot update User A's journal entry."""
        today = date(2026, 10, 4)
        entry_a = JournalEntry.objects.create(
            user=self.user_a,
            local_date=today,
            reflection='Original User A'
        )
        update_data = {
            'local_date': today.isoformat(),
            'reflection': 'Hacked by User B'
        }
        resp = self.client_b.post(reverse('journal:update', args=[entry_a.pk]), update_data)
        self.assertEqual(resp.status_code, 404)

        entry_a.refresh_from_db()
        self.assertEqual(entry_a.reflection, 'Original User A')

    def test_cross_user_isolation_deleting(self):
        """User B cannot delete User A's journal entry."""
        today = date(2026, 10, 4)
        entry_a = JournalEntry.objects.create(
            user=self.user_a,
            local_date=today,
            reflection='User A Entry'
        )

        resp = self.client_b.post(reverse('journal:delete', args=[entry_a.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(JournalEntry.objects.filter(pk=entry_a.pk).exists())

    def test_owner_can_delete_own_journal_entry(self):
        """Owner can delete their own journal entry."""
        today = date(2026, 10, 4)
        entry_a = JournalEntry.objects.create(
            user=self.user_a,
            local_date=today,
            reflection='User A Entry'
        )

        resp = self.client_a.post(reverse('journal:delete', args=[entry_a.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(JournalEntry.objects.filter(pk=entry_a.pk).exists())

    def test_timezone_date_defaults_correctly(self):
        """Journal creation form initial date reflects the user's local timezone."""
        self.user_a.profile.timezone = 'Asia/Kolkata'
        self.user_a.profile.save()

        resp = self.client_a.get(reverse('journal:create'))
        self.assertEqual(resp.status_code, 200)

        kolkata_tz = ZoneInfo('Asia/Kolkata')
        expected_today = timezone.now().astimezone(kolkata_tz).date()
        form = resp.context['form']
        self.assertEqual(form.initial['local_date'], expected_today)

    def test_navigation_active_highlighting(self):
        """When on /journal/, the Journal link is highlighted as nav-link-active, not Analytics."""
        resp = self.client_a.get(reverse('journal:list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Journal')
        # Check active link assignment
        content = resp.content.decode('utf-8')
        # Check that request.resolver_match.app_name == 'journal'
        self.assertEqual(resp.context['request'].resolver_match.app_name, 'journal')
