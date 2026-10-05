import zoneinfo
from datetime import date, datetime, timedelta
from unittest.mock import patch

from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.models import Profile
from accounts.views import _get_user_today as accounts_get_user_today
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
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


class HealthCheckTests(TestCase):
    def test_health_liveness(self):
        """GET /health/ returns 200 OK and healthy status."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'ok')

    def test_health_readiness(self):
        """GET /health/ready/ returns 200 OK when DB and Cache are accessible."""
        response = self.client.get('/health/ready/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'ready')
        self.assertEqual(data.get('checks', {}).get('database'), 'ok')
        self.assertEqual(data.get('checks', {}).get('cache'), 'ok')


class ThemeSystemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='themetester', password='password123')
        self.profile, _ = Profile.objects.get_or_create(user=self.user)

    def test_default_theme_is_light_in_base_html(self):
        """Authenticated pages render data-theme='light' on html by default."""
        self.client.force_login(self.user)
        response = self.client.get('/accounts/dashboard/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('data-theme="light"', content)
        self.assertIn('winter_arc_theme', content)

    def test_fowt_protection_early_script_present(self):
        """Early script in head checks localStorage before page render to prevent FOWT."""
        self.client.force_login(self.user)
        response = self.client.get('/accounts/dashboard/')
        content = response.content.decode('utf-8')
        self.assertIn('Early theme detection to prevent flash of wrong theme', content)
        self.assertIn("localStorage.getItem('winter_arc_theme')", content)
        self.assertIn('/static/js/theme', content)

    def test_landing_page_exception_no_data_theme_and_no_toggle(self):
        """Landing page remains untouched: no data-theme attribute and no theme toggle."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        # Landing page uses landing.html which must not have data-theme
        self.assertNotIn('data-theme="light"', content)
        self.assertNotIn('data-theme="dark"', content)
        # Theme toggle must not exist on landing page
        self.assertNotIn('id="theme-toggle-btn"', content)
        self.assertNotIn('theme-toggle-btn', content)

    def test_loading_page_loader_unchanged(self):
        """Loading page/loader remains untouched with original helmet artwork and copy."""
        response = self.client.get('/')
        content = response.content.decode('utf-8')
        self.assertIn('id="wa-loader"', content)
        self.assertIn('Winter is coming', content)
        self.assertIn('Lighting the beacons...', content)
        self.assertIn('loader_clean', content)

    def test_authenticated_pages_receive_theme_and_toggle(self):
        """All main authenticated pages receive theme root and theme toggle in navbar."""
        self.client.force_login(self.user)
        routes = [
            '/accounts/dashboard/',
            '/arcs/',
            '/tasks/',
            '/habits/',
            '/journal/',
            '/analytics/',
            '/notifications/',
            '/accounts/profile/',
        ]
        for route in routes:
            with self.subTest(route=route):
                resp = self.client.get(route)
                self.assertEqual(resp.status_code, 200)
                html = resp.content.decode('utf-8')
                self.assertIn('data-theme="light"', html)
                self.assertIn('theme-toggle-btn', html)
                self.assertIn('id="theme-toggle-btn"', html)

    def test_toggle_keyboard_accessibility_and_contrast_attributes(self):
        """Toggle buttons have proper accessible labels, type='button', and focus rings."""
        self.client.force_login(self.user)
        response = self.client.get('/accounts/dashboard/')
        content = response.content.decode('utf-8')
        self.assertIn('class="theme-toggle-btn', content)
        self.assertIn('aria-label="Switch theme"', content)
        self.assertIn('focus:ring-crimson', content)
        self.assertIn('theme-icon-light', content)
        self.assertIn('theme-icon-dark', content)
        self.assertIn('theme-label-text', content)


class BackNavigationAndContrastTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='navtester', password='password123')
        self.client.force_login(self.user)
        self.arc = Arc.objects.create(
            user=self.user,
            name="Alpha Protocol",
            objective="Protocol testing",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            status='ACTIVE',
            is_primary=True
        )
        self.goal = Goal.objects.create(
            user=self.user,
            arc=self.arc,
            title="Master Cold Exposure",
            deadline=date.today() + timedelta(days=30),
            priority=1
        )
        self.task = Task.objects.create(
            user=self.user,
            title="Morning Ice Bath",
            priority=Task.PRIORITY_HIGH
        )
        self.habit = Habit.objects.create(
            user=self.user,
            name="Dawn Run",
            active_from=date.today()
        )
        self.entry = JournalEntry.objects.create(
            user=self.user,
            local_date=date.today(),
            mood=5,
            energy=5,
            sleep_hours=8.0,
            reflection="Today was cold.",
            notes="Protocol initiated."
        )
        self.milestone = Milestone.objects.create(
            goal=self.goal,
            title="Milestone 1",
            due_date=date.today() + timedelta(days=10)
        )

    def test_back_navigation_links_present_on_detail_and_form_pages(self):
        """All detail, edit, create, and settings pages render deterministic wa-back-link."""
        test_cases = [
            (f'/arcs/{self.arc.pk}/', '/arcs/', 'Back to Arcs'),
            ('/arcs/new/', '/arcs/', 'Back to Arcs'),
            (f'/arcs/{self.arc.pk}/edit/', f'/arcs/{self.arc.pk}/', 'Back to Arc'),
            (f'/arcs/{self.arc.pk}/delete/', f'/arcs/{self.arc.pk}/', 'Back to Arc'),
            (f'/goals/{self.goal.pk}/', f'/arcs/{self.arc.pk}/', f'Back to {self.arc.name}'),
            (f'/goals/arc/{self.arc.pk}/new/', f'/arcs/{self.arc.pk}/', f'Back to {self.arc.name}'),
            (f'/goals/{self.goal.pk}/edit/', f'/arcs/{self.arc.pk}/', f'Back to {self.arc.name}'),
            (f'/goals/milestones/{self.milestone.pk}/edit/', f'/goals/{self.goal.pk}/', f'Back to {self.goal.title}'),
            (f'/goals/{self.goal.pk}/delete/', f'/goals/{self.goal.pk}/', 'Back to Goal'),
            (f'/tasks/{self.task.pk}/', '/tasks/', 'Back to Tasks'),
            ('/tasks/new/', '/tasks/', 'Back to Tasks'),
            (f'/tasks/{self.task.pk}/edit/', f'/tasks/{self.task.pk}/', 'Back to Task'),
            (f'/tasks/{self.task.pk}/delete/', '/tasks/', 'Back to Tasks'),
            (f'/habits/{self.habit.pk}/', '/habits/', 'Back to Habits'),
            ('/habits/new/', '/habits/', 'Back to Habits'),
            (f'/habits/{self.habit.pk}/edit/', f'/habits/{self.habit.pk}/', 'Back to Habit'),
            (f'/habits/{self.habit.pk}/archive/', f'/habits/{self.habit.pk}/', 'Back to Habit'),
            (f'/journal/{self.entry.pk}/', '/journal/', 'Back to Journal'),
            ('/journal/new/', '/journal/', 'Back to Journal'),
            (f'/journal/{self.entry.pk}/edit/', f'/journal/{self.entry.pk}/', 'Back to Entry'),
            (f'/journal/{self.entry.pk}/delete/', f'/journal/{self.entry.pk}/', 'Back to Entry'),
            ('/accounts/profile/', '/accounts/dashboard/', 'Back to Dashboard'),
            ('/notifications/preferences/', '/notifications/', 'Back to Notifications'),
        ]

        for url, expected_href, expected_text in test_cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, f"Failed loading {url}")
                html = response.content.decode('utf-8')
                self.assertIn('wa-back-link', html, f"wa-back-link missing on {url}")
                self.assertIn(f'href="{expected_href}"', html, f"Expected href {expected_href} not found on {url}")
                self.assertIn(expected_text, html, f"Expected text '{expected_text}' not found on {url}")
                self.assertNotIn('javascript:history.back()', html, f"history.back found on {url}")

    def test_css_contrast_rules_compiled(self):
        """Output CSS contains explicit light mode contrast rules for buttons and elements."""
        import os
        css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'output.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()

        # btn-primary text color override in light mode
        self.assertIn('html[data-theme=light] .btn-primary', css_content)
        self.assertIn('color:#faf9f6!important', css_content)

        # wa-back-link class compiled
        self.assertIn('wa-back-link', css_content)

        # progress-bar-track light mode color
        self.assertIn('.progress-bar-track', css_content)

    def test_popup_alert_auto_hide_script_present_with_messages(self):
        """When flash messages exist, the popup container and 5-second auto-hide timer are rendered."""
        self.client.force_login(self.user)
        response = self.client.post('/accounts/profile/', {'timezone': 'UTC'}, follow=True)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertIn('id="flash-messages-container"', html)
        self.assertIn('Your profile has been updated.', html)
        self.assertIn('setTimeout(function() {', html)
        self.assertIn('5000', html)
        self.assertIn("var container = document.getElementById('flash-messages-container');", html)



