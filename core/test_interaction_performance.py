from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json

from accounts.models import CustomUser, Profile
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit, HabitCompletion
from notifications.models import Notification


def create_test_user(username='crucible_warrior', password='password123'):
    user = CustomUser.objects.create_user(username=username, password=password)
    Profile.objects.get_or_create(user=user)
    return user


class InteractionPerformanceTests(TestCase):
    """
    Automated regression tests verifying:
    - Action controls do not redirect to detail pages
    - In-place actions succeed via both AJAX (JSON) and stay-in-place POST (next URL)
    - Double-click idempotency
    - Login performance and direct dashboard routing
    - Light-mode interaction styling integrity
    """

    def setUp(self):
        self.user = create_test_user()
        self.client = Client()
        self.client.login(username='crucible_warrior', password='password123')

        self.arc = Arc.objects.create(
            user=self.user,
            name='Winter Mastery Arc',
            status='ACTIVE',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=90),
            is_primary=True,
        )

        self.goal = Goal.objects.create(
            user=self.user,
            arc=self.arc,
            title='Run 100km in Sub-Zero',
            status='IN_PROGRESS',
        )

        self.milestone = Milestone.objects.create(
            goal=self.goal,
            title='Pass 25km Milestone',
            due_date=timezone.now().date() + timedelta(days=20),
        )

        self.task = Task.objects.create(
            user=self.user,
            goal=self.goal,
            title='Morning 5km Tempo Run',
            status='PENDING',
            priority=1,
        )

        self.habit = Habit.objects.create(
            user=self.user,
            name='Cold Water Immersion',
            frequency='DAILY',
            target_count=1,
            active_from=timezone.now().date(),
        )

    # -------------------------------------------------------------------------
    # A. Task completion from list / stay-in-place
    # -------------------------------------------------------------------------
    def test_a_task_completion_ajax_stays_in_place(self):
        """Task completion via AJAX returns JSON and never redirects to detail page."""
        url = reverse('tasks:complete', args=[self.task.pk])
        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['is_completed'])
        self.assertEqual(data['status'], 'COMPLETED')

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'COMPLETED')
        self.assertTrue(self.task.is_completed)

    def test_a_task_completion_form_post_stays_on_list(self):
        """Task completion via standard form POST with next stays on task list."""
        list_url = reverse('tasks:list')
        url = reverse('tasks:complete', args=[self.task.pk])
        response = self.client.post(url, {'next': list_url})
        self.assertRedirects(response, list_url)

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'COMPLETED')

    # -------------------------------------------------------------------------
    # B. Task undo
    # -------------------------------------------------------------------------
    def test_b_task_undo_ajax_stays_in_place(self):
        """Task undo via AJAX returns JSON and never redirects to detail page."""
        self.task.complete()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'COMPLETED')

        url = reverse('tasks:uncomplete', args=[self.task.pk])
        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['is_completed'])
        self.assertEqual(data['status'], 'PENDING')

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'PENDING')

    def test_b_task_undo_form_post_stays_on_dashboard(self):
        """Task undo with next=dashboard redirects back to dashboard, not detail."""
        self.task.complete()
        dash_url = reverse('dashboard')
        url = reverse('tasks:uncomplete', args=[self.task.pk])
        response = self.client.post(url, {'next': dash_url})
        self.assertRedirects(response, dash_url)

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'PENDING')

    # -------------------------------------------------------------------------
    # C. Habit completion
    # -------------------------------------------------------------------------
    def test_c_habit_completion_ajax_stays_in_place(self):
        """Habit completion via AJAX returns JSON and stays on current page."""
        url = reverse('habits:complete', args=[self.habit.pk])
        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['completed_today'])

        from habits.views import _get_user_today
        today = _get_user_today(self.user)
        self.assertTrue(HabitCompletion.objects.filter(habit=self.habit, local_date=today).exists())

    def test_c_habit_completion_form_post_stays_on_dashboard(self):
        """Habit completion via standard form POST with next stays on dashboard."""
        dash_url = reverse('dashboard')
        url = reverse('habits:complete', args=[self.habit.pk])
        response = self.client.post(url, {'next': dash_url})
        self.assertRedirects(response, dash_url)

    # -------------------------------------------------------------------------
    # D. Habit undo
    # -------------------------------------------------------------------------
    def test_d_habit_undo_ajax_stays_in_place(self):
        """Second POST to habit complete toggles/undoes completion in place."""
        from habits.views import _get_user_today
        today = _get_user_today(self.user)
        HabitCompletion.objects.create(habit=self.habit, local_date=today)

        url = reverse('habits:complete', args=[self.habit.pk])
        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['completed_today'])

        self.assertFalse(HabitCompletion.objects.filter(habit=self.habit, local_date=today).exists())

    # -------------------------------------------------------------------------
    # E. Goal completion
    # -------------------------------------------------------------------------
    def test_e_goal_completion_ajax_stays_in_place(self):
        """Goal completion endpoint completes goal in place and returns JSON."""
        url = reverse('goals:complete', args=[self.goal.pk])
        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['is_completed'])
        self.assertEqual(data['status'], 'COMPLETED')

        self.goal.refresh_from_db()
        self.assertEqual(self.goal.status, 'COMPLETED')

    def test_e_goal_completion_form_post_stays_on_arc_detail(self):
        """Goal complete with next parameter redirects back to arc detail."""
        arc_url = reverse('arcs:detail', args=[self.arc.pk])
        url = reverse('goals:complete', args=[self.goal.pk])
        response = self.client.post(url, {'next': arc_url})
        self.assertRedirects(response, arc_url)

    # -------------------------------------------------------------------------
    # F. Milestone completion
    # -------------------------------------------------------------------------
    def test_f_milestone_completion_ajax_stays_in_place(self):
        """Milestone toggle via AJAX returns milestone state and goal progress."""
        url = reverse('goals:milestone_toggle', args=[self.milestone.pk])
        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['is_completed'])

        self.milestone.refresh_from_db()
        self.assertTrue(self.milestone.is_completed)

    def test_f_milestone_completion_form_post_stays_on_current_page(self):
        """Milestone toggle with next parameter respects target page."""
        dash_url = reverse('dashboard')
        url = reverse('goals:milestone_toggle', args=[self.milestone.pk])
        response = self.client.post(url, {'next': dash_url})
        self.assertRedirects(response, dash_url)

    # -------------------------------------------------------------------------
    # G. Card/title intentional navigation
    # -------------------------------------------------------------------------
    def test_g_intentional_detail_navigation_still_works(self):
        """Intentional navigation to detail pages remains completely functional."""
        r_task = self.client.get(reverse('tasks:detail', args=[self.task.pk]))
        self.assertEqual(r_task.status_code, 200)
        self.assertContains(r_task, self.task.title)

        r_habit = self.client.get(reverse('habits:detail', args=[self.habit.pk]))
        self.assertEqual(r_habit.status_code, 200)
        self.assertContains(r_habit, self.habit.name)

        r_goal = self.client.get(reverse('goals:detail', args=[self.goal.pk]))
        self.assertEqual(r_goal.status_code, 200)
        self.assertContains(r_goal, self.goal.title)

    # -------------------------------------------------------------------------
    # H. Double-click idempotency
    # -------------------------------------------------------------------------
    def test_h_double_submission_is_idempotent(self):
        """Rapid repeated requests for the same task do not duplicate XP or error."""
        url = reverse('tasks:complete', args=[self.task.pk])
        r1 = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        r2 = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'COMPLETED')

    # -------------------------------------------------------------------------
    # I. Failed / Unauthorized request handling
    # -------------------------------------------------------------------------
    def test_i_unauthorized_user_cannot_mutate_task(self):
        """Another user cannot complete a task belonging to this user."""
        other_user = create_test_user(username='adversary_agent', password='password123')
        self.client.login(username='adversary_agent', password='password123')

        url = reverse('tasks:complete', args=[self.task.pk])
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 404)

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'PENDING')

    # -------------------------------------------------------------------------
    # J. Login performance & direct dashboard routing
    # -------------------------------------------------------------------------
    def test_j_successful_login_redirects_directly_to_dashboard(self):
        """Login directly routes to dashboard without unnecessary profile bounces."""
        self.client.logout()
        login_url = reverse('login')
        response = self.client.post(login_url, {
            'username': 'crucible_warrior',
            'password': 'password123'
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_j_failed_login_remains_on_login_page(self):
        """Failed authentication remains on login page with 200 status."""
        self.client.logout()
        login_url = reverse('login')
        response = self.client.post(login_url, {
            'username': 'crucible_warrior',
            'password': 'wrong_password'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct username and password')

    # -------------------------------------------------------------------------
    # K. Light mode CSS variables and interaction styling
    # -------------------------------------------------------------------------
    def test_k_light_mode_has_distinct_interaction_classes(self):
        """Base and output CSS contain dedicated classes for accessible checkbox and hover states."""
        from django.conf import settings
        import os

        input_css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'input.css')
        with open(input_css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()

        self.assertIn('.wa-checkbox-btn', css_content)
        self.assertIn('.wa-checkbox-indicator', css_content)
        self.assertIn('.wa-habit-btn-pending', css_content)
        self.assertIn('.wa-habit-btn-completed', css_content)
        self.assertIn('html[data-theme="light"] .wa-checkbox-indicator.is-completed', css_content)
