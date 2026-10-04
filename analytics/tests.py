from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit, HabitCompletion
from analytics.models import ActivityEvent
from analytics.services import log_activity, get_recent_activity
from analytics.progress_services import (
    calculate_arc_progress, get_task_statistics, get_habit_statistics,
    get_activity_breakdown, get_full_analytics_summary, get_user_local_date
)
from gamification.services import (
    award_xp, get_user_total_xp, get_user_rank,
    check_and_unlock_achievements, RANKS
)

User = get_user_model()

class AnalyticsAndProgressTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='analytics_hero', password='password123')
        self.user_other = User.objects.create_user(username='analytics_rival', password='password123')

        self.arc = Arc.objects.create(
            user=self.user,
            name='Winter Crucible',
            objective='Test analytics',
            start_date=date(2026, 10, 1),
            end_date=date(2026, 12, 31),
            status='ACTIVE',
            is_primary=True
        )

    def test_arc_progress_calculation(self):
        # Empty arc has 0 progress
        self.assertEqual(calculate_arc_progress(self.arc), 0)

        # Add goal with 2 milestones
        goal = Goal.objects.create(user=self.user, arc=self.arc, title='Iron Body')
        m1 = Milestone.objects.create(goal=goal, title='10k Run')
        m2 = Milestone.objects.create(goal=goal, title='100 Pushups')

        # 0 of 2 done -> 0%
        self.assertEqual(calculate_arc_progress(self.arc), 0)

        # 1 of 2 done -> 50%
        m1.completed_at = timezone.now()
        m1.save()
        self.assertEqual(calculate_arc_progress(self.arc), 50)

        # 2 of 2 done -> 100%
        m2.completed_at = timezone.now()
        m2.save()
        self.assertEqual(calculate_arc_progress(self.arc), 100)

    def test_task_statistics_and_isolation(self):
        t1 = Task.objects.create(user=self.user, title='Task 1', status='COMPLETED')
        t2 = Task.objects.create(user=self.user, title='Task 2', status='PENDING', priority=Task.PRIORITY_HIGH)
        t_rival = Task.objects.create(user=self.user_other, title='Rival Task', status='COMPLETED')

        stats = get_task_statistics(self.user)
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['completed'], 1)
        self.assertEqual(stats['pending'], 1)
        self.assertEqual(stats['completion_rate'], 50)
        self.assertEqual(stats['high_priority'], 1)

        # Rival sees only their own task
        rival_stats = get_task_statistics(self.user_other)
        self.assertEqual(rival_stats['total'], 1)
        self.assertEqual(rival_stats['completed'], 1)

    def test_task_analytics_arc_scoping_fallback(self):
        """When an arc is selected but has no goal-attached tasks, get_task_statistics falls back to user tasks."""
        t1 = Task.objects.create(user=self.user, title='Global Task', status='COMPLETED')
        stats = get_task_statistics(self.user, arc=self.arc)
        self.assertEqual(stats['total'], 1)
        self.assertEqual(stats['completed'], 1)
        self.assertFalse(stats['is_scoped_to_arc'])

    def test_habit_statistics_and_streaks(self):
        h = Habit.objects.create(
            user=self.user,
            name='Dawn Meditation',
            active_from=date(2026, 10, 1)
        )
        today = get_user_local_date(self.user)
        # Complete for 3 consecutive days
        HabitCompletion.objects.create(habit=h, local_date=today - timedelta(days=2))
        HabitCompletion.objects.create(habit=h, local_date=today - timedelta(days=1))
        HabitCompletion.objects.create(habit=h, local_date=today)

        stats = get_habit_statistics(self.user)
        self.assertEqual(stats['total_habits'], 1)
        self.assertEqual(stats['completed_today'], 1)
        self.assertEqual(stats['top_current_streak'], 3)
        self.assertEqual(stats['top_best_streak'], 3)

    def test_habit_completion_idempotency_same_day(self):
        """Repeated completion calls for same habit on same local date must not create duplicate records."""
        h = Habit.objects.create(
            user=self.user,
            name='Cold Plunge',
            active_from=date(2026, 10, 1)
        )
        today = get_user_local_date(self.user)
        c1, created1 = HabitCompletion.objects.get_or_create(habit=h, local_date=today)
        self.assertTrue(created1)

        c2, created2 = HabitCompletion.objects.get_or_create(habit=h, local_date=today)
        self.assertFalse(created2)
        self.assertEqual(c1.pk, c2.pk)
        self.assertEqual(HabitCompletion.objects.filter(habit=h, local_date=today).count(), 1)

    def test_activity_event_idempotency(self):
        """Activity logging for idempotent habit actions must not create multiple events."""
        event1 = log_activity(
            user=self.user,
            event_type='HABIT_COMPLETED',
            title='Beacon lit: Cold Plunge',
            source_type='habit',
            source_id='100_2026-10-03'
        )
        event2 = log_activity(
            user=self.user,
            event_type='HABIT_COMPLETED',
            title='Beacon lit: Cold Plunge',
            source_type='habit',
            source_id='100_2026-10-03'
        )
        self.assertEqual(event1.pk, event2.pk)
        self.assertEqual(ActivityEvent.objects.filter(user=self.user, source_type='habit', source_id='100_2026-10-03').count(), 1)

    def test_consistency_calculation_formula(self):
        """Formula: completion_count / (active_habits * 30) * 100 (excludes archived habits)."""
        h1 = Habit.objects.create(user=self.user, name='H1', active_from=date(2026, 10, 1))
        h2 = Habit.objects.create(user=self.user, name='H2', active_from=date(2026, 10, 1))
        h_archived = Habit.objects.create(user=self.user, name='H_Arch', active_from=date(2026, 10, 1), is_archived=True)
        today = get_user_local_date(self.user)

        # Completions on active habits
        for i in range(3):
            HabitCompletion.objects.create(habit=h1, local_date=today - timedelta(days=i))
            HabitCompletion.objects.create(habit=h2, local_date=today - timedelta(days=i))
        # Completion on archived habit (must be excluded from 30d consistency)
        HabitCompletion.objects.create(habit=h_archived, local_date=today)
        
        # total active completions = 6, possible = 2 * 30 = 60 -> 6/60 * 100 = 10%
        stats = get_habit_statistics(self.user)
        self.assertEqual(stats['total_habits'], 2)
        self.assertEqual(stats['completions_30d'], 6)
        self.assertEqual(stats['consistency_rate'], 10)

    def test_activity_logging_and_feed(self):
        log_activity(
            user=self.user,
            event_type='TASK_COMPLETED',
            title='Ran 5 Miles',
            arc=self.arc
        )
        # Rival logs activity
        log_activity(
            user=self.user_other,
            event_type='TASK_COMPLETED',
            title='Rival Action'
        )

        user_feed = get_recent_activity(self.user)
        self.assertEqual(user_feed.count(), 1)
        self.assertEqual(user_feed.first().title, 'Ran 5 Miles')

    def test_analytics_empty_state_safety(self):
        summary = get_full_analytics_summary(self.user_other)
        self.assertIsNone(summary['selected_arc'])
        self.assertEqual(summary['arc_progress'], 0)
        self.assertEqual(summary['task_stats']['total'], 0)
        self.assertEqual(summary['habit_stats']['total_habits'], 0)
        self.assertEqual(summary['rank_info']['current_xp'], 0)
        self.assertEqual(summary['rank_info']['current_rank'], 'Recruit')

    def test_badge_conditions_individual(self):
        """Verify each achievement unlocks strictly when its underlying criteria is met."""
        # 1. FIRST_TASK
        self.assertEqual(len(check_and_unlock_achievements(self.user)), 0)
        Task.objects.create(user=self.user, title='T1', status='COMPLETED')
        u1 = check_and_unlock_achievements(self.user)
        self.assertEqual(len(u1), 1)
        self.assertEqual(u1[0].achievement.code, 'FIRST_TASK')

        # 2. FIRST_GOAL
        goal = Goal.objects.create(user=self.user, arc=self.arc, title='G1', status='COMPLETED')
        u2 = check_and_unlock_achievements(self.user)
        self.assertEqual(len(u2), 1)
        self.assertEqual(u2[0].achievement.code, 'FIRST_GOAL')

        # 3. STREAK_7 & STREAK_30
        h = Habit.objects.create(user=self.user, name='H_Streak', active_from=date(2026, 10, 1))
        today = date.today()
        for i in range(7):
            HabitCompletion.objects.create(habit=h, local_date=today - timedelta(days=i))
        u3 = check_and_unlock_achievements(self.user)
        self.assertEqual(len(u3), 1)
        self.assertEqual(u3[0].achievement.code, 'STREAK_7')

        # 4. FIRST_ARC
        self.arc.status = 'COMPLETED'
        self.arc.save()
        u4 = check_and_unlock_achievements(self.user)
        self.assertEqual(len(u4), 1)
        self.assertEqual(u4[0].achievement.code, 'FIRST_ARC')

    def test_activity_breakdown_daily_items_and_zero_activity(self):
        """Verify activity breakdown returns daily_items with exact counts and handles zero activity days."""
        breakdown = get_activity_breakdown(self.user, days=7)
        self.assertEqual(len(breakdown['labels']), 7)
        self.assertEqual(len(breakdown['tasks_data']), 7)
        self.assertEqual(len(breakdown['habits_data']), 7)
        self.assertEqual(len(breakdown['daily_items']), 7)
        self.assertEqual(breakdown['total_tasks_period'], 0)
        self.assertEqual(breakdown['total_habits_period'], 0)

        # Complete a task today
        t = Task.objects.create(user=self.user, title='Morning Drill', status='COMPLETED', completed_at=timezone.now())
        breakdown_after = get_activity_breakdown(self.user, days=7)
        self.assertEqual(breakdown_after['total_tasks_period'], 1)
        self.assertEqual(breakdown_after['daily_items'][-1]['tasks'], 1)
        self.assertEqual(breakdown_after['daily_items'][0]['tasks'], 0)

