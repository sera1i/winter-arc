import json
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import CustomUser, Profile
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit
from analytics.models import ActivityEvent
from gamification.services import get_user_total_xp
from core.presets import (
    get_all_presets,
    get_preset_by_key,
    PRESETS_REGISTRY,
    PresetDefinition,
)
from arcs.preset_services import (
    initialize_blueprint_draft,
    validate_blueprint_draft,
    activate_blueprint_arc,
)


class PresetDefinitionTests(TestCase):
    """Verify integrity of the preset blueprints specifications."""

    def test_all_seven_presets_exist(self):
        presets = get_all_presets()
        self.assertEqual(len(presets), 7)
        expected_keys = {'classic', 'student', 'fitness', 'monk_mode', 'mind_body', 'career', 'custom'}
        self.assertEqual(set(PRESETS_REGISTRY.keys()), expected_keys)

    def test_preset_keys_and_properties(self):
        for key, preset in PRESETS_REGISTRY.items():
            self.assertEqual(key, preset.key)
            self.assertTrue(len(preset.name) > 0)
            self.assertTrue(len(preset.tagline) > 0)
            self.assertTrue(len(preset.description) > 0)
            self.assertEqual(preset.recommended_duration_days, 90)

    def test_classic_preset_structure(self):
        preset = get_preset_by_key('classic')
        self.assertIsNotNone(preset)
        self.assertEqual(preset.name, 'Classic Winter Arc')
        self.assertEqual(preset.habit_count, 5)
        self.assertEqual(preset.goal_count, 3)

        # Habit names
        habit_names = [h.name for h in preset.habits]
        self.assertIn('Daily Movement', habit_names)
        self.assertIn('Read / Study', habit_names)
        self.assertIn('Sleep Discipline', habit_names)
        self.assertIn('Limit Mindless Scrolling', habit_names)
        self.assertIn('Daily Reflection', habit_names)

        # Goal titles
        goal_titles = [g.title for g in preset.goals]
        self.assertIn('Build Physical Discipline', goal_titles)
        self.assertIn('Strengthen Mental Discipline', goal_titles)
        self.assertIn('Protect Focus & Recovery', goal_titles)

    def test_custom_preset_blank_slate(self):
        preset = get_preset_by_key('custom')
        self.assertIsNotNone(preset)
        self.assertEqual(preset.name, 'Custom Arc')
        self.assertEqual(preset.habit_count, 0)
        self.assertEqual(preset.goal_count, 0)


class PresetServiceTests(TestCase):
    """Test blueprint drafting, validation, and atomic creation logic."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(username='servicetester', password='password123')
        self.profile = Profile.objects.create(user=self.user, timezone='Asia/Kolkata')

    def test_initialize_blueprint_draft(self):
        preset = get_preset_by_key('student')
        draft = initialize_blueprint_draft(preset, self.user)
        self.assertEqual(draft['preset_key'], 'student')
        self.assertEqual(draft['name'], 'Student Lock-In')
        self.assertTrue(draft['is_primary'])
        self.assertEqual(len(draft['goals']), 3)
        self.assertEqual(len(draft['habits']), 5)
        self.assertEqual(draft['timezone'], 'Asia/Kolkata')

    def test_initialize_blueprint_draft_existing_primary_arc(self):
        today = timezone.now().date()
        Arc.objects.create(
            user=self.user,
            name='Current Arc',
            objective='Active watch',
            start_date=today,
            end_date=today + timedelta(days=90),
            status='ACTIVE',
            is_primary=True,
        )
        preset = get_preset_by_key('fitness')
        draft = initialize_blueprint_draft(preset, self.user)
        # Should not default to primary if user already has an active primary arc
        self.assertFalse(draft['is_primary'])

    def test_validate_blueprint_draft_valid(self):
        today = timezone.now().date()
        payload = {
            'name': 'Winter Protocol 2026',
            'objective': 'Total discipline across body and mind.',
            'start_date': today.isoformat(),
            'end_date': (today + timedelta(days=90)).isoformat(),
            'timezone': 'Asia/Kolkata',
            'is_primary': True,
            'goals': [
                {'title': 'Complete Thesis', 'category': 'LEARNING', 'priority': 1, 'milestones': [], 'tasks': []}
            ],
            'habits': [
                {'name': 'Deep Study', 'frequency': 'DAILY', 'target_count': 60, 'target_label': '60 minutes'}
            ]
        }
        is_valid, cleaned, errors = validate_blueprint_draft(payload)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        self.assertEqual(cleaned['name'], 'Winter Protocol 2026')
        self.assertEqual(len(cleaned['goals']), 1)
        self.assertEqual(len(cleaned['habits']), 1)

    def test_validate_blueprint_draft_invalid_dates(self):
        today = timezone.now().date()
        payload = {
            'name': 'Bad Dates Arc',
            'objective': 'Test objective',
            'start_date': (today + timedelta(days=10)).isoformat(),
            'end_date': today.isoformat(),  # Start after end
            'timezone': 'UTC',
        }
        is_valid, cleaned, errors = validate_blueprint_draft(payload)
        self.assertFalse(is_valid)
        self.assertIn('start_date', errors)

    def test_validate_blueprint_draft_blank_name_and_objective(self):
        payload = {
            'name': '   ',
            'objective': '',
            'start_date': '2026-10-01',
            'end_date': '2026-12-31',
        }
        is_valid, cleaned, errors = validate_blueprint_draft(payload)
        self.assertFalse(is_valid)
        self.assertIn('name', errors)
        self.assertIn('objective', errors)

    def test_activate_blueprint_arc_atomic_creation(self):
        initial_xp = get_user_total_xp(self.user)
        preset = get_preset_by_key('classic')
        draft = initialize_blueprint_draft(preset, self.user)
        is_valid, cleaned, errors = validate_blueprint_draft(draft)
        self.assertTrue(is_valid)

        arc = activate_blueprint_arc(self.user, cleaned)

        # 1. Arc created correctly
        self.assertEqual(Arc.objects.filter(user=self.user).count(), 1)
        self.assertEqual(arc.user, self.user)
        self.assertEqual(arc.status, 'ACTIVE')
        self.assertTrue(arc.is_primary)

        # 2. Child entities created with correct ownership
        goals = Goal.objects.filter(arc=arc)
        self.assertEqual(goals.count(), 3)
        for g in goals:
            self.assertEqual(g.user, self.user)
            self.assertEqual(g.arc, arc)

        milestones = Milestone.objects.filter(goal__arc=arc)
        self.assertTrue(milestones.count() > 0)

        tasks = Task.objects.filter(goal__arc=arc)
        self.assertTrue(tasks.count() > 0)
        for t in tasks:
            self.assertEqual(t.user, self.user)
            self.assertEqual(t.status, 'PENDING')

        habits = Habit.objects.filter(user=self.user)
        self.assertEqual(habits.count(), 5)
        for h in habits:
            self.assertEqual(h.user, self.user)
            self.assertFalse(h.is_archived)

        # 3. Activity Event logged
        event = ActivityEvent.objects.filter(user=self.user, event_type='ARC_STARTED').first()
        self.assertIsNotNone(event)
        self.assertEqual(event.arc, arc)

        # 4. Creation is NOT completion: XP should NOT change
        final_xp = get_user_total_xp(self.user)
        self.assertEqual(initial_xp, final_xp)


class PresetWebFlowTests(TestCase):
    """Test user web journey: Starting Points -> Review -> Customize -> Oath -> Activate."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(username='webflowuser', password='password123')
        Profile.objects.create(user=self.user, timezone='Asia/Kolkata')
        self.client.login(username='webflowuser', password='password123')

    def test_unauthenticated_redirects(self):
        self.client.logout()
        resp = self.client.get(reverse('arcs:presets'))
        self.assertEqual(resp.status_code, 302)

    def test_preset_library_renders_all_blueprints(self):
        resp = self.client.get(reverse('arcs:presets'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Forge an Arc')
        self.assertContains(resp, 'Classic Winter Arc')
        self.assertContains(resp, 'Student Lock-In')
        self.assertContains(resp, 'Fitness Arc')
        self.assertContains(resp, 'Monk Mode')
        self.assertContains(resp, 'Mind + Body')
        self.assertContains(resp, 'Career Lock-In')
        self.assertContains(resp, 'Custom Arc')
        # Check back link
        self.assertContains(resp, reverse('dashboard'))

    def test_preset_review_screen(self):
        resp = self.client.get(reverse('arcs:preset_review', kwargs={'key': 'classic'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Classic Winter Arc')
        self.assertContains(resp, 'Suggested Goals')
        self.assertContains(resp, 'Suggested Habits')
        self.assertContains(resp, 'Customize Blueprint')
        self.assertContains(resp, reverse('arcs:presets'))

    def test_preset_review_invalid_key_redirects(self):
        resp = self.client.get(reverse('arcs:preset_review', kwargs={'key': 'nonexistent_key'}))
        self.assertRedirects(resp, reverse('arcs:presets'))

    def test_preset_customize_get_initializes_session(self):
        resp = self.client.get(reverse('arcs:preset_customize', kwargs={'key': 'student'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Shape Your Season')
        session_key = 'preset_draft_student'
        self.assertIn(session_key, self.client.session)
        draft = self.client.session[session_key]
        self.assertEqual(draft['preset_key'], 'student')

    def test_preset_customize_get_renders_predefined_goals_and_habits_in_html(self):
        """Classic preset customize GET must render all predefined goals and habits directly in the HTML."""
        resp = self.client.get(reverse('arcs:preset_customize', kwargs={'key': 'classic'}))
        self.assertEqual(resp.status_code, 200)

        # Goals directly present in response HTML
        self.assertContains(resp, 'Build Physical Discipline')
        self.assertContains(resp, 'Strengthen Mental Discipline')
        self.assertContains(resp, 'Protect Focus &amp; Recovery')

        # Habits directly present in response HTML
        self.assertContains(resp, 'Daily Movement')
        self.assertContains(resp, 'Read / Study')
        self.assertContains(resp, 'Sleep Discipline')
        self.assertContains(resp, 'Limit Mindless Scrolling')
        self.assertContains(resp, 'Daily Reflection')

        # Milestones present
        self.assertContains(resp, 'Establish 30-day consistent movement baseline')

        # Must NOT show empty state placeholder for preset
        self.assertNotContains(resp, 'empty-goals-placeholder')
        self.assertNotContains(resp, 'empty-habits-placeholder')

    def test_custom_preset_starts_with_clean_slate_zero_goals_habits(self):
        """Custom arc starts with 0 goals and 0 habits (clean slate)."""
        resp = self.client.get(reverse('arcs:preset_customize', kwargs={'key': 'custom'}))
        self.assertEqual(resp.status_code, 200)

        # Empty state text and classes must be shown for custom
        self.assertContains(resp, 'empty-goals-placeholder')
        self.assertContains(resp, 'empty-habits-placeholder')
        self.assertContains(resp, 'No goals added yet')
        self.assertContains(resp, 'No daily habits added yet')

        session_key = 'preset_draft_custom'
        self.assertIn(session_key, self.client.session)
        draft = self.client.session[session_key]
        self.assertEqual(len(draft['goals']), 0)
        self.assertEqual(len(draft['habits']), 0)

    def test_preset_customize_pass_through_no_changes_preserves_all_entities(self):
        """Entering customize and proceeding to Oath without modifications preserves all predefined entities."""
        # 1. Enter review
        resp_rev = self.client.get(reverse('arcs:preset_review', kwargs={'key': 'classic'}))
        self.assertEqual(resp_rev.status_code, 200)

        # 2. Enter customize
        resp_cust = self.client.get(reverse('arcs:preset_customize', kwargs={'key': 'classic'}))
        self.assertEqual(resp_cust.status_code, 200)

        # 3. Post to Oath with pass-through (empty payload fallback or untouched form)
        resp_post = self.client.post(
            reverse('arcs:preset_customize', kwargs={'key': 'classic'}),
            {'name': 'Classic Winter Arc', 'objective': 'Untouched commitment'}
        )
        self.assertRedirects(resp_post, reverse('arcs:preset_oath', kwargs={'key': 'classic'}))

        # 4. Oath screen shows all 3 goals and 5 habits
        resp_oath = self.client.get(reverse('arcs:preset_oath', kwargs={'key': 'classic'}))
        self.assertEqual(resp_oath.status_code, 200)
        self.assertContains(resp_oath, '3 Total')  # 3 goals
        self.assertContains(resp_oath, '5 Total')  # 5 habits
        self.assertContains(resp_oath, 'Build Physical Discipline')
        self.assertContains(resp_oath, 'Daily Movement')

        # 5. Activate Arc
        resp_act = self.client.post(reverse('arcs:preset_activate', kwargs={'key': 'classic'}))
        arc = Arc.objects.get(name='Classic Winter Arc', user=self.user)
        self.assertRedirects(resp_act, reverse('arcs:detail', kwargs={'pk': arc.pk}))

        # 6. Verify database records
        self.assertEqual(arc.goals.count(), 3)
        self.assertEqual(Habit.objects.filter(user=self.user).count(), 5)
        self.assertTrue(Milestone.objects.filter(goal__arc=arc).count() >= 3)

    def test_preset_customize_modifications_and_back_navigation(self):
        """User modifications persist across back navigation between Oath and Customize."""
        today = timezone.now().date()
        custom_payload = {
            'name': 'Customized Monk Shield',
            'objective': 'Radical focus and zero distractions.',
            'start_date': today.isoformat(),
            'end_date': (today + timedelta(days=90)).isoformat(),
            'timezone': 'Asia/Kolkata',
            'is_primary': True,
            'preset_key': 'monk_mode',
            'preset_name': 'Monk Mode',
            'goals': [
                {'title': 'Deep Work Mastery', 'category': 'PRODUCTIVITY', 'priority': 1, 'milestones': [], 'tasks': []}
            ],
            'habits': [
                {'name': '4hr Deep Work Block', 'frequency': 'DAILY', 'target_count': 240, 'target_label': '240 minutes'},
                {'name': 'Cold Shower', 'frequency': 'DAILY', 'target_count': 1, 'target_label': '1 cold shower'}
            ]
        }

        # Submit modifications
        resp = self.client.post(
            reverse('arcs:preset_customize', kwargs={'key': 'monk_mode'}),
            {'customized_payload': json.dumps(custom_payload)}
        )
        self.assertRedirects(resp, reverse('arcs:preset_oath', kwargs={'key': 'monk_mode'}))

        # Navigate back to Customize
        resp_back = self.client.get(reverse('arcs:preset_customize', kwargs={'key': 'monk_mode'}))
        self.assertEqual(resp_back.status_code, 200)
        self.assertContains(resp_back, 'Customized Monk Shield')
        self.assertContains(resp_back, 'Deep Work Mastery')
        self.assertContains(resp_back, '4hr Deep Work Block')
        self.assertContains(resp_back, 'Cold Shower')

    def test_preset_customize_reset_button_restores_defaults(self):
        """Reset button (?reset=1) restores preset blueprint defaults."""
        today = timezone.now().date()
        custom_payload = {
            'name': 'Wiped Arc',
            'objective': 'Temporary test objective',
            'start_date': today.isoformat(),
            'end_date': (today + timedelta(days=90)).isoformat(),
            'timezone': 'Asia/Kolkata',
            'is_primary': True,
            'preset_key': 'fitness',
            'preset_name': 'Fitness Arc',
            'goals': [],
            'habits': []
        }
        self.client.post(
            reverse('arcs:preset_customize', kwargs={'key': 'fitness'}),
            {'customized_payload': json.dumps(custom_payload)}
        )

        # Now trigger reset
        resp_reset = self.client.get(reverse('arcs:preset_customize', kwargs={'key': 'fitness'}) + '?reset=1')
        self.assertEqual(resp_reset.status_code, 200)
        self.assertContains(resp_reset, 'Fitness Arc')
        # All fitness defaults restored
        self.assertContains(resp_reset, 'Build Training Consistency')
        self.assertContains(resp_reset, 'Training / Workout')

    def test_no_database_records_created_prior_to_activation(self):
        """Confirm NO Arc, Goal, Milestone, Task, or Habit is created during Review, Customize, or Oath viewing."""
        self.client.get(reverse('arcs:preset_review', kwargs={'key': 'classic'}))
        self.client.get(reverse('arcs:preset_customize', kwargs={'key': 'classic'}))
        self.client.get(reverse('arcs:preset_oath', kwargs={'key': 'classic'}))

        self.assertEqual(Arc.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Goal.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Milestone.objects.filter(goal__user=self.user).count(), 0)
        self.assertEqual(Task.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Habit.objects.filter(user=self.user).count(), 0)

    def test_preset_customize_post_saves_and_redirects_to_oath(self):
        today = timezone.now().date()
        custom_payload = {
            'name': 'Customized Student Crucible',
            'objective': 'Academic high performance with strict sleep protocol.',
            'start_date': today.isoformat(),
            'end_date': (today + timedelta(days=90)).isoformat(),
            'timezone': 'Asia/Kolkata',
            'is_primary': True,
            'preset_key': 'student',
            'preset_name': 'Student Lock-In',
            'goals': [
                {'title': 'Pass All Exams', 'category': 'LEARNING', 'priority': 1, 'milestones': [], 'tasks': []}
            ],
            'habits': [
                {'name': 'Study 2 Hours', 'frequency': 'DAILY', 'target_count': 120, 'target_label': '120 minutes'},
                {'name': 'Gym Workout', 'frequency': 'DAILY', 'target_count': 45, 'target_label': '45 minutes'}
            ]
        }

        resp = self.client.post(
            reverse('arcs:preset_customize', kwargs={'key': 'student'}),
            {'customized_payload': json.dumps(custom_payload)}
        )
        self.assertRedirects(resp, reverse('arcs:preset_oath', kwargs={'key': 'student'}))

        # Session should hold modified draft
        saved_draft = self.client.session['preset_draft_student']
        self.assertEqual(saved_draft['name'], 'Customized Student Crucible')
        self.assertEqual(len(saved_draft['habits']), 2)

    def test_preset_oath_and_activation_flow(self):
        today = timezone.now().date()
        session = self.client.session
        session['preset_draft_fitness'] = {
            'name': 'Iron Arc',
            'objective': 'Build stamina and discipline.',
            'start_date': today.isoformat(),
            'end_date': (today + timedelta(days=90)).isoformat(),
            'timezone': 'Asia/Kolkata',
            'is_primary': True,
            'preset_key': 'fitness',
            'preset_name': 'Fitness Arc',
            'goals': [
                {'title': 'Hypertrophy Training', 'category': 'HEALTH', 'priority': 1, 'milestones': [], 'tasks': []}
            ],
            'habits': [
                {'name': 'Pushups', 'frequency': 'DAILY', 'target_count': 100, 'target_label': '100 pushups'}
            ]
        }
        session.save()

        # Oath GET
        resp_oath = self.client.get(reverse('arcs:preset_oath', kwargs={'key': 'fitness'}))
        self.assertEqual(resp_oath.status_code, 200)
        self.assertContains(resp_oath, 'The Oath')
        self.assertContains(resp_oath, 'Iron Arc')
        self.assertContains(resp_oath, 'Sign the Oath & Activate Arc')

        # Activate POST
        resp_activate = self.client.post(reverse('arcs:preset_activate', kwargs={'key': 'fitness'}))
        arc = Arc.objects.get(name='Iron Arc', user=self.user)
        self.assertRedirects(resp_activate, reverse('arcs:detail', kwargs={'pk': arc.pk}))

        # Verify arc and relations exist
        self.assertEqual(arc.status, 'ACTIVE')
        self.assertEqual(arc.goals.count(), 1)
        self.assertEqual(Habit.objects.filter(user=self.user, name='Pushups').count(), 1)

        # Verify session cleared
        self.assertNotIn('preset_draft_fitness', self.client.session)


class PresetSecurityAndIsolationTests(TestCase):
    """Verify strict tenant isolation and security boundaries."""

    def setUp(self):
        self.user_a = CustomUser.objects.create_user(username='usera', password='password123')
        Profile.objects.create(user=self.user_a)

        self.user_b = CustomUser.objects.create_user(username='userb', password='password123')
        Profile.objects.create(user=self.user_b)

    def test_user_cannot_activate_another_users_session_draft(self):
        # User A sets a draft
        client_a = self.client
        client_a.login(username='usera', password='password123')
        today = timezone.now().date()
        client_a.post(
            reverse('arcs:preset_customize', kwargs={'key': 'classic'}),
            {'customized_payload': json.dumps({
                'name': 'User A Arc',
                'objective': 'Secret personal goals',
                'start_date': today.isoformat(),
                'end_date': (today + timedelta(days=90)).isoformat(),
                'is_primary': True,
                'goals': [],
                'habits': []
            })}
        )

        # User B logs in on separate client
        from django.test import Client
        client_b = Client()
        client_b.login(username='userb', password='password123')

        # User B activating without having initialized their own draft gets redirected
        resp_b = client_b.post(reverse('arcs:preset_activate', kwargs={'key': 'classic'}))
        self.assertRedirects(resp_b, reverse('arcs:preset_customize', kwargs={'key': 'classic'}))
        self.assertFalse(Arc.objects.filter(user=self.user_b, name='User A Arc').exists())

    def test_all_created_entities_belong_strictly_to_request_user(self):
        today = timezone.now().date()
        payload = {
            'name': 'Secure Arc',
            'objective': 'Security verification.',
            'start_date': today.isoformat(),
            'end_date': (today + timedelta(days=90)).isoformat(),
            'timezone': 'UTC',
            'is_primary': True,
            'goals': [
                {'title': 'Security Goal', 'category': 'OTHER', 'priority': 1, 'milestones': [{'title': 'M1'}], 'tasks': [{'title': 'T1'}]}
            ],
            'habits': [
                {'name': 'Daily Security Habit', 'frequency': 'DAILY', 'target_count': 1}
            ]
        }
        is_valid, cleaned, _ = validate_blueprint_draft(payload)
        self.assertTrue(is_valid)

        arc = activate_blueprint_arc(self.user_a, cleaned)

        self.assertEqual(arc.user, self.user_a)
        goal = Goal.objects.get(arc=arc)
        self.assertEqual(goal.user, self.user_a)
        task = Task.objects.get(goal=goal)
        self.assertEqual(task.user, self.user_a)
        habit = Habit.objects.get(user=self.user_a, name='Daily Security Habit')
        self.assertEqual(habit.user, self.user_a)

        # User B cannot view User A's arc
        from django.test import Client
        client_b = Client()
        client_b.login(username='userb', password='password123')
        resp = client_b.get(reverse('arcs:detail', kwargs={'pk': arc.pk}))
        self.assertEqual(resp.status_code, 404)


class PresetAPITests(TestCase):
    """Test read-only presets REST API endpoints."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(username='apiuser', password='password123')
        Profile.objects.create(user=self.user)
        self.client = APIClient()

    def test_unauthenticated_api_request_denied(self):
        resp = self.client.get(reverse('api_presets'))
        self.assertEqual(resp.status_code, 401)

    def test_authenticated_preset_list_endpoint(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse('api_presets'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 7)
        keys = [p['key'] for p in data]
        self.assertIn('classic', keys)
        self.assertIn('student', keys)
        self.assertIn('fitness', keys)
        self.assertIn('monk_mode', keys)
        self.assertIn('mind_body', keys)
        self.assertIn('career', keys)
        self.assertIn('custom', keys)

    def test_authenticated_preset_detail_endpoint(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse('api_preset_detail', kwargs={'key': 'monk_mode'}))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['key'], 'monk_mode')
        self.assertEqual(data['name'], 'Monk Mode')
        self.assertEqual(data['habit_count'], 5)
        self.assertEqual(data['goal_count'], 3)
        self.assertTrue(len(data['goals']) == 3)
        self.assertTrue(len(data['habits']) == 5)

    def test_authenticated_preset_detail_not_found(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse('api_preset_detail', kwargs={'key': 'does_not_exist'}))
        self.assertEqual(resp.status_code, 404)
