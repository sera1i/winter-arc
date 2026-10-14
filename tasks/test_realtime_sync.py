from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import date
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit, HabitCompletion
from gamification.models import XPEvent
from gamification.services import get_user_total_xp, get_user_rank

User = get_user_model()


class RealtimeSyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='crusader_one', password='password123')
        self.other_user = User.objects.create_user(username='crusader_two', password='password123')
        
        self.arc = Arc.objects.create(
            user=self.user,
            name='Winter Crucible',
            objective='Endure the season',
            start_date=date(2026, 10, 1),
            end_date=date(2026, 12, 31),
            status='ACTIVE',
            is_primary=True
        )
        self.goal = Goal.objects.create(
            user=self.user,
            arc=self.arc,
            title='Master the Blade',
            category='DISCIPLINE',
            target_value=10,
            unit='levels',
            status='IN_PROGRESS'
        )
        self.milestone = Milestone.objects.create(
            goal=self.goal,
            title='First Checkpoint',
            due_date=date(2026, 11, 1)
        )
        self.task = Task.objects.create(
            user=self.user,
            goal=self.goal,
            title='Daily Drill',
            priority=1,
            status='PENDING'
        )
        self.habit = Habit.objects.create(
            user=self.user,
            name='Dawn Run',
            frequency='DAILY',
            active_from=date(2026, 10, 1)
        )

        from gamification.models import Achievement, UserAchievement
        from gamification.services import _ensure_achievements_seeded
        _ensure_achievements_seeded()
        first_task_ach = Achievement.objects.filter(code='FIRST_TASK').first()
        if first_task_ach:
            UserAchievement.objects.get_or_create(user=self.user, achievement=first_task_ach)

        self.client = Client()
        self.client.login(username='crusader_one', password='password123')

    def test_complete_and_undo_daily_task_sync(self):
        # 1. Complete Task via AJAX
        res = self.client.post(
            reverse('tasks:complete', args=[self.task.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'COMPLETED')
        self.assertTrue(data['is_completed'])
        
        # Verify sync payload
        sync = data['sync']
        self.assertEqual(sync['total_xp'], 50)
        self.assertEqual(sync['tasks']['today_completed'], 1)
        self.assertEqual(sync['tasks']['total_pending'], 0)
        self.assertEqual(get_user_total_xp(self.user), 50)
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'COMPLETED')
        self.assertIsNotNone(self.task.completed_at)

        # 2. Duplicate Complete Click (Idempotency) - Must not award XP twice
        res_dup = self.client.post(
            reverse('tasks:complete', args=[self.task.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(res_dup.status_code, 200)
        self.assertEqual(res_dup.json()['sync']['total_xp'], 50)
        self.assertEqual(get_user_total_xp(self.user), 50)

        # 3. Undo Task via AJAX
        res_undo = self.client.post(
            reverse('tasks:uncomplete', args=[self.task.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(res_undo.status_code, 200)
        data_undo = res_undo.json()
        self.assertTrue(data_undo['success'])
        self.assertEqual(data_undo['status'], 'PENDING')
        self.assertFalse(data_undo['is_completed'])
        
        # Verify sync payload reflects rollback
        sync_undo = data_undo['sync']
        self.assertEqual(sync_undo['total_xp'], 0)
        self.assertEqual(sync_undo['tasks']['today_completed'], 0)
        self.assertEqual(sync_undo['tasks']['total_pending'], 1)
        self.assertEqual(get_user_total_xp(self.user), 0)

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'PENDING')
        self.assertIsNone(self.task.completed_at)

    def test_complete_and_undo_habit_sync(self):
        # 1. Complete Habit via AJAX
        res = self.client.post(
            reverse('habits:complete', args=[self.habit.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['completed_today'])
        self.assertEqual(data['streak'], 1)
        
        # Verify sync payload
        sync = data['sync']
        self.assertEqual(sync['total_xp'], 30)
        self.assertEqual(sync['habits']['completed_today'], 1)
        self.assertEqual(sync['habits']['total_habits'], 1)
        self.assertEqual(get_user_total_xp(self.user), 30)

        # 2. Undo Habit via AJAX
        res_undo = self.client.post(
            reverse('habits:complete', args=[self.habit.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(res_undo.status_code, 200)
        data_undo = res_undo.json()
        self.assertTrue(data_undo['success'])
        self.assertFalse(data_undo['completed_today'])
        self.assertEqual(data_undo['streak'], 0)

        # Verify sync payload reflects rollback
        sync_undo = data_undo['sync']
        self.assertEqual(sync_undo['total_xp'], 0)
        self.assertEqual(sync_undo['habits']['completed_today'], 0)
        self.assertEqual(get_user_total_xp(self.user), 0)

    def test_milestone_toggle_sync(self):
        # 1. Toggle Milestone Complete
        res = self.client.post(
            reverse('goals:milestone_toggle', args=[self.milestone.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['is_completed'])
        
        # All milestones done for this goal => Goal also completed!
        # Milestone XP (100) + Goal XP (250) = 350 XP
        self.milestone.refresh_from_db()
        self.goal.refresh_from_db()
        self.assertTrue(self.milestone.is_completed)
        self.assertEqual(self.goal.status, 'COMPLETED')
        
        sync = data['sync']
        self.assertEqual(sync['total_xp'], 350)
        self.assertEqual(sync['goal']['progress'], 100)
        self.assertEqual(sync['arc']['progress'], 100)
        self.assertEqual(get_user_total_xp(self.user), 350)

        # 2. Toggle Milestone Uncomplete (Undo)
        res_undo = self.client.post(
            reverse('goals:milestone_toggle', args=[self.milestone.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(res_undo.status_code, 200)
        data_undo = res_undo.json()
        self.assertTrue(data_undo['success'])
        self.assertFalse(data_undo['is_completed'])

        self.milestone.refresh_from_db()
        self.goal.refresh_from_db()
        self.assertFalse(self.milestone.is_completed)
        self.assertEqual(self.goal.status, 'IN_PROGRESS')

        sync_undo = data_undo['sync']
        self.assertEqual(sync_undo['total_xp'], 0)
        self.assertEqual(sync_undo['goal']['progress'], 0)
        self.assertEqual(sync_undo['arc']['progress'], 0)
        self.assertEqual(get_user_total_xp(self.user), 0)

    def test_unauthorized_user_cannot_modify_tasks_or_habits(self):
        other_client = Client()
        other_client.login(username='crusader_two', password='password123')
        
        # Attempt to complete user 1's task
        res = other_client.post(
            reverse('tasks:complete', args=[self.task.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(res.status_code, 404)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'PENDING')
        self.assertEqual(get_user_total_xp(self.other_user), 0)

        # Attempt to complete user 1's habit
        res_habit = other_client.post(
            reverse('habits:complete', args=[self.habit.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(res_habit.status_code, 404)
        self.assertEqual(HabitCompletion.objects.filter(habit=self.habit).count(), 0)
        self.assertEqual(get_user_total_xp(self.other_user), 0)
