import json
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token

from accounts.models import Profile
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit, HabitCompletion
from journal.models import JournalEntry
from notifications.models import Notification, NotificationPreference
from gamification.models import XPEvent, Achievement, UserAchievement

User = get_user_model()


class WinterArcAPITests(APITestCase):
    def setUp(self):
        # User A (Primary test user)
        self.user_a = User.objects.create_user(
            username='user_a',
            email='user_a@example.com',
            password='Password123!'
        )
        self.profile_a, _ = Profile.objects.get_or_create(
            user=self.user_a,
            defaults={'timezone': 'UTC', 'display_name': 'User Alpha'}
        )
        self.token_a = Token.objects.create(user=self.user_a)

        # User B (Isolation test user)
        self.user_b = User.objects.create_user(
            username='user_b',
            email='user_b@example.com',
            password='Password123!'
        )
        self.profile_b, _ = Profile.objects.get_or_create(
            user=self.user_b,
            defaults={'timezone': 'UTC', 'display_name': 'User Beta'}
        )
        self.token_b = Token.objects.create(user=self.user_b)

        # Arc for User A
        self.arc_a = Arc.objects.create(
            user=self.user_a,
            name='Alpha Protocol',
            objective='Complete the harsh trial',
            start_date=date(2026, 10, 1),
            end_date=date(2026, 12, 31),
            status='ACTIVE',
            is_primary=True
        )

        # Arc for User B
        self.arc_b = Arc.objects.create(
            user=self.user_b,
            name='Beta Protocol',
            objective='Private beta trial',
            start_date=date(2026, 10, 1),
            end_date=date(2026, 12, 31),
            status='ACTIVE',
            is_primary=True
        )

    # -----------------------------------------------------------------------
    # 1. Authentication & Security
    # -----------------------------------------------------------------------
    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests must receive 401 or 403."""
        response = self.client.get('/api/v1/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
        self.assertIn('code', response.data['error'])

    def test_token_auth_endpoint_and_me(self):
        """User can obtain auth token and query /api/v1/me/ securely."""
        response = self.client.post('/api/v1/token-auth/', {
            'username': 'user_a',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.data.get('token')
        self.assertEqual(token, self.token_a.key)

        # Query /me with Token
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        me_resp = self.client.get('/api/v1/me/')
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(me_resp.data['username'], 'user_a')
        self.assertNotIn('password', me_resp.data)

    def test_me_patch_profile(self):
        """User can update profile settings via PATCH /me/."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')
        resp = self.client.patch('/api/v1/me/', {'bio': 'Discipline is destiny.'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.profile_a.refresh_from_db()
        self.assertEqual(self.profile_a.bio, 'Discipline is destiny.')

    # -----------------------------------------------------------------------
    # 2. Arcs CRUD & Actions
    # -----------------------------------------------------------------------
    def test_arc_crud_and_cross_user_isolation(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')

        # List arcs: User A sees only their arc
        list_resp = self.client.get('/api/v1/arcs/')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(list_resp.data['count'], 1)
        self.assertEqual(list_resp.data['results'][0]['name'], 'Alpha Protocol')

        # User A cannot retrieve User B's arc (404 IDOR prevention)
        get_b_resp = self.client.get(f'/api/v1/arcs/{self.arc_b.pk}/')
        self.assertEqual(get_b_resp.status_code, status.HTTP_404_NOT_FOUND)

        # Create Arc
        create_resp = self.client.post('/api/v1/arcs/', {
            'name': 'Secondary Arc',
            'objective': 'Extra fitness goals',
            'start_date': '2026-10-05',
            'end_date': '2026-11-05',
            'status': 'ACTIVE',
        })
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        new_arc_id = create_resp.data['id']

        # Set Primary action
        set_prim_resp = self.client.post(f'/api/v1/arcs/{new_arc_id}/set_primary/')
        self.assertEqual(set_prim_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(set_prim_resp.data['is_primary'])
        self.arc_a.refresh_from_db()
        self.assertFalse(self.arc_a.is_primary)

        # Archive action
        arch_resp = self.client.post(f'/api/v1/arcs/{new_arc_id}/archive/')
        self.assertEqual(arch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(arch_resp.data['status'], 'ARCHIVED')

    # -----------------------------------------------------------------------
    # 3. Goals & Milestones
    # -----------------------------------------------------------------------
    def test_goals_and_milestones_ownership_and_xp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')

        # Create Goal under User A's arc
        g_resp = self.client.post('/api/v1/goals/', {
            'arc': self.arc_a.pk,
            'title': 'Master Coding Discipline',
            'category': 'PRODUCTIVITY',
            'priority': 1
        })
        self.assertEqual(g_resp.status_code, status.HTTP_201_CREATED)
        goal_id = g_resp.data['id']

        # Prevent assigning User A's goal to User B's arc
        bad_g = self.client.post('/api/v1/goals/', {
            'arc': self.arc_b.pk,
            'title': 'Illegal Cross User Goal',
            'category': 'PRODUCTIVITY',
        })
        self.assertEqual(bad_g.status_code, status.HTTP_400_BAD_REQUEST)

        # Create Milestone under Goal
        m_resp = self.client.post('/api/v1/milestones/', {
            'goal': goal_id,
            'title': 'Complete Milestone 1',
            'target_value': 100
        })
        self.assertEqual(m_resp.status_code, status.HTTP_201_CREATED)
        milestone_id = m_resp.data['id']

        # Complete Milestone (triggers 100 XP)
        comp_m = self.client.post(f'/api/v1/milestones/{milestone_id}/complete/')
        self.assertEqual(comp_m.status_code, status.HTTP_200_OK)
        self.assertTrue(comp_m.data['is_completed'])
        m_xp = XPEvent.objects.filter(user=self.user_a, source_type='milestone', source_id=str(milestone_id))
        self.assertTrue(m_xp.exists())
        self.assertEqual(m_xp.first().amount, 100)

        # Complete Goal (triggers 250 XP)
        comp_g = self.client.post(f'/api/v1/goals/{goal_id}/complete/')
        self.assertEqual(comp_g.status_code, status.HTTP_200_OK)
        self.assertEqual(comp_g.data['status'], 'COMPLETED')
        g_xp = XPEvent.objects.filter(user=self.user_a, source_type='goal', source_id=str(goal_id))
        self.assertTrue(g_xp.exists())
        self.assertEqual(g_xp.first().amount, 250)

    # -----------------------------------------------------------------------
    # 4. Tasks Lifecycle & XP
    # -----------------------------------------------------------------------
    def test_tasks_lifecycle_and_security(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')

        # Create Task
        t_resp = self.client.post('/api/v1/tasks/', {
            'title': 'Morning Deep Work',
            'priority': 1
        })
        self.assertEqual(t_resp.status_code, status.HTTP_201_CREATED)
        task_id = t_resp.data['id']

        # User B cannot access User A's task
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_b.key}')
        b_get = self.client.get(f'/api/v1/tasks/{task_id}/')
        self.assertEqual(b_get.status_code, status.HTTP_404_NOT_FOUND)

        # Switch back to User A to complete task
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')
        comp_t = self.client.post(f'/api/v1/tasks/{task_id}/complete/')
        self.assertEqual(comp_t.status_code, status.HTTP_200_OK)
        self.assertEqual(comp_t.data['status'], 'COMPLETED')
        self.assertTrue(comp_t.data['is_completed'])

        # Verify XP awarded (50 XP for task)
        t_xp = XPEvent.objects.filter(user=self.user_a, source_type='task', source_id=str(task_id))
        self.assertTrue(t_xp.exists())
        self.assertEqual(t_xp.first().amount, 50)

        # Uncomplete task
        uncomp_t = self.client.post(f'/api/v1/tasks/{task_id}/uncomplete/')
        self.assertEqual(uncomp_t.status_code, status.HTTP_200_OK)
        self.assertEqual(uncomp_t.data['status'], 'PENDING')

        # Cancel task
        canc_t = self.client.post(f'/api/v1/tasks/{task_id}/cancel/')
        self.assertEqual(canc_t.status_code, status.HTTP_200_OK)
        self.assertEqual(canc_t.data['status'], 'CANCELLED')

    # -----------------------------------------------------------------------
    # 5. Habits & Completions
    # -----------------------------------------------------------------------
    def test_habits_and_streaks(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')

        # Create Habit
        h_resp = self.client.post('/api/v1/habits/', {
            'name': 'Cold Shower',
            'frequency': 'DAILY',
            'active_from': '2026-10-01'
        })
        self.assertEqual(h_resp.status_code, status.HTTP_201_CREATED)
        habit_id = h_resp.data['id']

        # Complete Habit
        comp_h = self.client.post(f'/api/v1/habits/{habit_id}/complete/')
        self.assertEqual(comp_h.status_code, status.HTTP_200_OK)
        self.assertEqual(comp_h.data['status'], 'completed')
        self.assertTrue(comp_h.data['habit']['is_completed_today'])
        self.assertEqual(comp_h.data['habit']['current_streak'], 1)

        # Verify XP awarded (30 XP for habit)
        habit_obj = Habit.objects.get(pk=habit_id)
        today = habit_obj.get_user_today()
        h_xp = XPEvent.objects.filter(user=self.user_a, source_type='habit', source_id=f"{habit_id}_{today}")
        self.assertTrue(h_xp.exists())
        self.assertEqual(h_xp.first().amount, 30)

        # Undo habit completion
        undo_h = self.client.post(f'/api/v1/habits/{habit_id}/undo/')
        self.assertEqual(undo_h.status_code, status.HTTP_200_OK)
        self.assertEqual(undo_h.data['status'], 'undone')
        self.assertFalse(undo_h.data['habit']['is_completed_today'])

    # -----------------------------------------------------------------------
    # 6. Journal
    # -----------------------------------------------------------------------
    def test_journal_entry_and_xp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')

        j_resp = self.client.post('/api/v1/journal/', {
            'local_date': '2026-10-04',
            'mood': 5,
            'energy': 4,
            'sleep_hours': 7.5,
            'reflection': 'Unwavering focus.'
        })
        self.assertEqual(j_resp.status_code, status.HTTP_201_CREATED)
        j_id = j_resp.data['id']

        # Verify 40 XP for journal reflection
        j_xp = XPEvent.objects.filter(user=self.user_a, source_type='journal')
        self.assertTrue(j_xp.exists())
        self.assertEqual(j_xp.first().amount, 40)

    # -----------------------------------------------------------------------
    # 7. Notifications & Preferences
    # -----------------------------------------------------------------------
    def test_notifications_endpoints(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')

        # Create notification for User A
        n = Notification.objects.create(
            user=self.user_a,
            notification_type='TASK_DUE_SOON',
            title='Task Due',
            message='Your morning workout is due soon.',
            dedup_key='test-key-api-1'
        )

        # List notifications
        list_n = self.client.get('/api/v1/notifications/')
        self.assertEqual(list_n.status_code, status.HTTP_200_OK)
        self.assertEqual(list_n.data['count'], 1)

        # Unread count
        count_resp = self.client.get('/api/v1/notifications/unread_count/')
        self.assertEqual(count_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(count_resp.data['unread_count'], 1)

        # Mark read
        mark_resp = self.client.post(f'/api/v1/notifications/{n.pk}/mark_read/')
        self.assertEqual(mark_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(mark_resp.data['is_read'])

        # Notification Preferences GET & PATCH
        p_get = self.client.get('/api/v1/notifications/preferences/')
        self.assertEqual(p_get.status_code, status.HTTP_200_OK)

        p_patch = self.client.patch('/api/v1/notifications/preferences/', {
            'email_enabled': False
        }, format='json')
        self.assertEqual(p_patch.status_code, status.HTTP_200_OK)
        self.assertFalse(p_patch.data['email_enabled'])

    # -----------------------------------------------------------------------
    # 8. Analytics & Gamification Read-Only Endpoints
    # -----------------------------------------------------------------------
    def test_analytics_and_gamification_views(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')

        # Query /api/v1/analytics/
        ana_resp = self.client.get('/api/v1/analytics/')
        self.assertEqual(ana_resp.status_code, status.HTTP_200_OK)
        self.assertIn('arc_progress', ana_resp.data)
        self.assertIn('task_stats', ana_resp.data)
        self.assertIn('habit_stats', ana_resp.data)
        self.assertIn('rank_info', ana_resp.data)

        # Query /api/v1/gamification/
        gam_resp = self.client.get('/api/v1/gamification/')
        self.assertEqual(gam_resp.status_code, status.HTTP_200_OK)
        self.assertIn('total_xp', gam_resp.data)
        self.assertIn('current_rank', gam_resp.data)
        self.assertIn('achievements', gam_resp.data)
        self.assertIn('recent_xp_events', gam_resp.data)

    # -----------------------------------------------------------------------
    # 9. OpenAPI Schema
    # -----------------------------------------------------------------------
    def test_openapi_schema_endpoint(self):
        """OpenAPI schema generation is accessible."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')
        schema_resp = self.client.get('/api/v1/schema/')
        self.assertEqual(schema_resp.status_code, status.HTTP_200_OK)
        self.assertIn('openapi', schema_resp.data)
        self.assertIn('paths', schema_resp.data)

    # -----------------------------------------------------------------------
    # 10. Error Format & Mass Assignment Guards
    # -----------------------------------------------------------------------
    def test_standard_error_format_on_validation_failure(self):
        """Validation errors follow standard {error: {code, message, details}} schema."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')
        resp = self.client.post('/api/v1/arcs/', {
            'name': 'Invalid Dates Arc',
            'objective': 'Test error format',
            'start_date': '2026-12-31',
            'end_date': '2026-01-01',  # end earlier than start
            'status': 'ACTIVE'
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', resp.data)
        self.assertIn('code', resp.data['error'])
        self.assertIn('message', resp.data['error'])
        self.assertIn('details', resp.data['error'])

    def test_task_mass_assignment_guards(self):
        """Clients cannot inject user or force is_completed directly on create."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')
        resp = self.client.post('/api/v1/tasks/', {
            'title': 'Test Guard Task',
            'user': self.user_b.pk,  # attempted spoofing
            'status': 'COMPLETED',
            'is_completed': True,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=resp.data['id'])
        # Task MUST belong to authenticated user, not user_b
        self.assertEqual(task.user, self.user_a)

    def test_pagination_structure(self):
        """List responses follow standard paginated schema with count, results, and page."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token_a.key}')
        resp = self.client.get('/api/v1/tasks/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('count', resp.data)
        self.assertIn('results', resp.data)
        self.assertIn('total_pages', resp.data)
        self.assertIn('page', resp.data)

