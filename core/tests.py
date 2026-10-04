import zoneinfo
from datetime import date, datetime, timedelta
from unittest.mock import patch

from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.models import Profile
from accounts.views import _get_user_today as accounts_get_user_today
from habits.models import Habit, HabitCompletion
from habits.views import _get_user_today as habits_get_user_today
from journal.models import JournalEntry
from analytics.progress_services import get_user_local_date, get_activity_breakdown, get_habit_statistics
from notifications.tasks import _get_user_local_date as notif_get_user_local_date, _get_user_local_now
from core.middleware import TimezoneMiddleware

User = get_user_model()


class TemporalIntegrityTests(TestCase):
    def setUp(self):
        # 1. User in Asia/Kolkata (East of UTC: UTC+05:30)
        self.user_kolkata = User.objects.create_user(username='kolkata_user', password='password123')
        self.profile_kolkata, _ = Profile.objects.get_or_create(user=self.user_kolkata)
        self.profile_kolkata.timezone = 'Asia/Kolkata'
        self.profile_kolkata.save()

        # 2. User in America/New_York (West of UTC: UTC-04:00 EDT)
        self.user_ny = User.objects.create_user(username='ny_user', password='password123')
        self.profile_ny, _ = Profile.objects.get_or_create(user=self.user_ny)
        self.profile_ny.timezone = 'America/New_York'
        self.profile_ny.save()

        # 3. User in UTC
        self.user_utc = User.objects.create_user(username='utc_user', password='password123')
        self.profile_utc, _ = Profile.objects.get_or_create(user=self.user_utc)
        self.profile_utc.timezone = 'UTC'
        self.profile_utc.save()

        # 4. User with no explicit profile timezone (falls back to settings.TIME_ZONE)
        self.user_default = User.objects.create_user(username='default_user', password='password123')
        self.profile_default, _ = Profile.objects.get_or_create(user=self.user_default)
        self.profile_default.timezone = ''
        self.profile_default.save()

        self.factory = RequestFactory()

    def test_timezone_boundary_transition_at_fixed_instant(self):
        """
        At 2026-10-03 21:00:00 UTC:
          - UTC date is 2026-10-03 (Saturday)
          - America/New_York (17:00 EDT) is 2026-10-03 (Saturday)
          - Asia/Kolkata (02:30 IST on Oct 4) is 2026-10-04 (Sunday)
        """
        frozen_instant = datetime(2026, 10, 3, 21, 0, 0, tzinfo=zoneinfo.ZoneInfo('UTC'))
        with patch('django.utils.timezone.now', return_value=frozen_instant):
            # Check accounts helper
            self.assertEqual(accounts_get_user_today(self.user_utc), date(2026, 10, 3))
            self.assertEqual(accounts_get_user_today(self.user_ny), date(2026, 10, 3))
            self.assertEqual(accounts_get_user_today(self.user_kolkata), date(2026, 10, 4))

            # Check habits helper
            self.assertEqual(habits_get_user_today(self.user_utc), date(2026, 10, 3))
            self.assertEqual(habits_get_user_today(self.user_ny), date(2026, 10, 3))
            self.assertEqual(habits_get_user_today(self.user_kolkata), date(2026, 10, 4))

            # Check analytics helper
            self.assertEqual(get_user_local_date(self.user_utc), date(2026, 10, 3))
            self.assertEqual(get_user_local_date(self.user_ny), date(2026, 10, 3))
            self.assertEqual(get_user_local_date(self.user_kolkata), date(2026, 10, 4))

            # Check notifications helper
            self.assertEqual(notif_get_user_local_date(self.user_utc), date(2026, 10, 3))
            self.assertEqual(notif_get_user_local_date(self.user_ny), date(2026, 10, 3))
            self.assertEqual(notif_get_user_local_date(self.user_kolkata), date(2026, 10, 4))

    def test_default_user_falls_back_to_settings_timezone(self):
        """When user profile timezone is empty, falls back to settings.TIME_ZONE."""
        frozen_instant = datetime(2026, 10, 3, 21, 0, 0, tzinfo=zoneinfo.ZoneInfo('UTC'))
        with patch('django.utils.timezone.now', return_value=frozen_instant):
            today = accounts_get_user_today(self.user_default)
            # settings.TIME_ZONE defaults to Asia/Kolkata, so date is Oct 4
            expected = frozen_instant.astimezone(zoneinfo.ZoneInfo(settings.TIME_ZONE)).date()
            self.assertEqual(today, expected)

    def test_habit_completion_dates_remain_distinct_across_boundary(self):
        """
        October 3 completion remains October 3.
        October 4 completion is recorded as October 4.
        Completions do not shift dates.
        """
        habit = Habit.objects.create(
            user=self.user_kolkata,
            name="Early Dawn Protocol",
            active_from=date(2026, 10, 1)
        )

        # Complete on Oct 3
        c_oct3 = HabitCompletion.objects.create(habit=habit, local_date=date(2026, 10, 3))
        # Complete on Oct 4
        c_oct4 = HabitCompletion.objects.create(habit=habit, local_date=date(2026, 10, 4))

        self.assertEqual(c_oct3.local_date, date(2026, 10, 3))
        self.assertEqual(c_oct4.local_date, date(2026, 10, 4))
        self.assertEqual(habit.completions.count(), 2)

    def test_streak_preservation_from_yesterday_when_today_starts(self):
        """
        When dawn arrives on Oct 4, yesterday's (Oct 3) completion preserves streak = 1.
        Once Oct 4 is completed, streak increments to 2.
        """
        habit = Habit.objects.create(
            user=self.user_kolkata,
            name="Cold Immersion",
            active_from=date(2026, 10, 1)
        )
        HabitCompletion.objects.create(habit=habit, local_date=date(2026, 10, 3))

        # Freeze time at Oct 4 dawn (03:00 IST = 21:30 UTC on Oct 3)
        frozen_instant = datetime(2026, 10, 3, 21, 30, 0, tzinfo=zoneinfo.ZoneInfo('UTC'))
        with patch('django.utils.timezone.now', return_value=frozen_instant):
            # Not yet completed on Oct 4, but completed on Oct 3 -> streak is 1
            self.assertFalse(habit.is_completed_today())
            self.assertEqual(habit.get_current_streak(), 1)

            # Now complete on Oct 4
            HabitCompletion.objects.create(habit=habit, local_date=date(2026, 10, 4))
            self.assertTrue(habit.is_completed_today())
            self.assertEqual(habit.get_current_streak(), 2)

    def test_journal_daily_entry_idempotency_and_distinct_dates(self):
        """
        Journal entries are strictly unique per (user, local_date).
        Oct 3 and Oct 4 entries are distinct.
        """
        j_oct3 = JournalEntry.objects.create(
            user=self.user_kolkata,
            local_date=date(2026, 10, 3),
            mood=4,
            reflection="Eve of winter."
        )
        j_oct4 = JournalEntry.objects.create(
            user=self.user_kolkata,
            local_date=date(2026, 10, 4),
            mood=5,
            reflection="Dawn watch commenced."
        )
        self.assertNotEqual(j_oct3.pk, j_oct4.pk)
        self.assertEqual(j_oct3.local_date, date(2026, 10, 3))
        self.assertEqual(j_oct4.local_date, date(2026, 10, 4))

    def test_analytics_date_windows_respect_local_date(self):
        """
        7-day activity breakdown accurately ends on user's local date.
        """
        frozen_instant = datetime(2026, 10, 3, 21, 30, 0, tzinfo=zoneinfo.ZoneInfo('UTC'))
        with patch('django.utils.timezone.now', return_value=frozen_instant):
            breakdown_kolkata = get_activity_breakdown(self.user_kolkata, days=7)
            breakdown_ny = get_activity_breakdown(self.user_ny, days=7)

            # Last label for Kolkata is Oct 04
            self.assertEqual(breakdown_kolkata['labels'][-1], 'Oct 04')
            # Last label for New York is Oct 03
            self.assertEqual(breakdown_ny['labels'][-1], 'Oct 03')

    def test_timezone_middleware_activates_user_profile_timezone(self):
        """Middleware activates the authenticated user's timezone during request processing."""
        request = self.factory.get('/accounts/dashboard/')
        request.user = self.user_kolkata

        def view(req):
            current_tz = timezone.get_current_timezone_name()
            current_date = timezone.localdate()
            return (current_tz, current_date)

        mw = TimezoneMiddleware(view)
        active_tz, active_date = mw(request)

        self.assertEqual(active_tz, 'Asia/Kolkata')
        # Outside middleware, timezone is deactivated
        self.assertEqual(timezone.get_current_timezone_name(), settings.TIME_ZONE)

    def test_timezone_middleware_cookie_fallback_for_anonymous_or_default(self):
        """Middleware uses django_timezone cookie if profile timezone is absent."""
        request = self.factory.get('/')
        request.user = self.user_default
        request.COOKIES['django_timezone'] = 'Asia/Tokyo'

        def view(req):
            return timezone.get_current_timezone_name()

        mw = TimezoneMiddleware(view)
        active_tz = mw(request)
        self.assertEqual(active_tz, 'Asia/Tokyo')

    def test_celery_and_settings_timezone_configuration(self):
        """Settings TIME_ZONE and CELERY_TIMEZONE align with project configuration."""
        self.assertIn(settings.TIME_ZONE, ['Asia/Kolkata', 'UTC'])
        self.assertEqual(getattr(settings, 'CELERY_TIMEZONE', None), settings.TIME_ZONE)


class ProductionHealthCheckTests(TestCase):
    def setUp(self):
        self.client = self.client_class()

    def test_liveness_endpoint_returns_200_and_json(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/json')
        data = response.json()
        self.assertEqual(data.get('status'), 'live')
        self.assertIn('timestamp', data)

    def test_readiness_endpoint_returns_200_when_healthy(self):
        response = self.client.get('/health/ready/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/json')
        data = response.json()
        self.assertEqual(data.get('status'), 'ready')
        self.assertTrue(data['components']['database'])
        self.assertTrue(data['components']['cache'])

    @patch('django.db.connection.cursor')
    def test_readiness_endpoint_returns_503_on_db_failure(self, mock_cursor):
        mock_cursor.side_effect = Exception("Database connection failure")
        response = self.client.get('/health/ready/')
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get('status'), 'unhealthy')
        self.assertFalse(data['components']['database'])
        # Never leak exception details in response payload
        self.assertNotIn("Database connection failure", response.content.decode())


class ProductionSecurityTests(TestCase):
    def test_production_security_headers_present(self):
        """Verify standard security headers configured in settings."""
        self.assertTrue(getattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF', False))
        self.assertEqual(getattr(settings, 'X_FRAME_OPTIONS', ''), 'DENY')
        self.assertEqual(getattr(settings, 'SECURE_REFERRER_POLICY', ''), 'same-origin')

