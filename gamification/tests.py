from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit, HabitCompletion
from gamification.models import XPEvent, Achievement, UserAchievement
from gamification.services import (
    award_xp, get_user_total_xp, get_user_rank,
    check_and_unlock_achievements, RANKS,
    XP_TASK_COMPLETED, XP_HABIT_COMPLETED, XP_MILESTONE_COMPLETED
)

User = get_user_model()

class GamificationAndXPTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_crusader', password='password123')
        self.user_b = User.objects.create_user(username='rival_crusader', password='password123')
        self.arc = Arc.objects.create(
            user=self.user,
            name='Forge Arc',
            objective='Testing XP',
            start_date=date(2026, 10, 1),
            end_date=date(2026, 12, 31),
            status='ACTIVE',
            is_primary=True
        )

    def test_award_xp_basic(self):
        event, created = award_xp(self.user, 'task', 'task_1', amount=50, arc=self.arc)
        self.assertTrue(created)
        self.assertEqual(event.amount, 50)
        self.assertEqual(get_user_total_xp(self.user), 50)

    def test_award_xp_idempotency_same_source_not_duplicated(self):
        event1, created1 = award_xp(self.user, 'task', 'task_1', amount=50)
        self.assertTrue(created1)
        self.assertEqual(get_user_total_xp(self.user), 50)

        # Trigger again with exact same user, source_type, source_id
        event2, created2 = award_xp(self.user, 'task', 'task_1', amount=50)
        self.assertFalse(created2)
        self.assertEqual(event1.pk, event2.pk)
        # XP must NOT increase
        self.assertEqual(get_user_total_xp(self.user), 50)

    def test_rank_thresholds_exact_boundary(self):
        # 0 XP -> Recruit
        r0 = get_user_rank(self.user)
        self.assertEqual(r0['current_rank'], 'Recruit')
        self.assertEqual(r0['current_level'], 1)
        self.assertEqual(r0['next_rank'], 'Sentinel')
        self.assertEqual(r0['next_threshold'], 300)
        self.assertEqual(r0['xp_to_next'], 300)

        # 299 XP -> One XP below Sentinel -> Recruit
        award_xp(self.user, 'test', 't_299', amount=299)
        r299 = get_user_rank(self.user)
        self.assertEqual(r299['current_rank'], 'Recruit')
        self.assertEqual(r299['xp_to_next'], 1)

        # 300 XP -> Exact Sentinel threshold
        award_xp(self.user, 'test', 't_1', amount=1)
        r300 = get_user_rank(self.user)
        self.assertEqual(r300['current_rank'], 'Sentinel')
        self.assertEqual(r300['current_level'], 2)
        self.assertEqual(r300['next_rank'], 'Ranger')
        self.assertEqual(r300['next_threshold'], 900)
        self.assertEqual(r300['xp_to_next'], 600)

        # 899 XP -> One below Ranger -> Sentinel
        award_xp(self.user, 'test', 't_599', amount=599)
        r899 = get_user_rank(self.user)
        self.assertEqual(r899['current_rank'], 'Sentinel')
        self.assertEqual(r899['xp_to_next'], 1)

        # 900 XP -> Exact Ranger threshold
        award_xp(self.user, 'test', 't_ranger', amount=1)
        r900 = get_user_rank(self.user)
        self.assertEqual(r900['current_rank'], 'Ranger')
        self.assertEqual(r900['current_level'], 3)
        self.assertEqual(r900['next_rank'], 'Warden')
        self.assertEqual(r900['next_threshold'], 2000)

        # 1999 XP -> Ranger
        award_xp(self.user, 'test', 't_almost_warden', amount=1099)
        r1999 = get_user_rank(self.user)
        self.assertEqual(r1999['current_rank'], 'Ranger')
        self.assertEqual(r1999['xp_to_next'], 1)

        # 2000 XP -> Warden (Max rank)
        award_xp(self.user, 'test', 't_warden', amount=1)
        r2000 = get_user_rank(self.user)
        self.assertEqual(r2000['current_rank'], 'Warden')
        self.assertEqual(r2000['current_level'], 4)
        self.assertTrue(r2000['is_max_rank'])
        self.assertIsNone(r2000['next_rank'])
        self.assertEqual(r2000['xp_to_next'], 0)

    def test_user_xp_isolation(self):
        award_xp(self.user, 'task', 'task_a', amount=100)
        award_xp(self.user_b, 'task', 'task_b', amount=250)

        self.assertEqual(get_user_total_xp(self.user), 100)
        self.assertEqual(get_user_total_xp(self.user_b), 250)

    def test_achievement_deterministic_unlock(self):
        # Create completed task
        Task.objects.create(user=self.user, title='First Step', status='COMPLETED')
        unlocked = check_and_unlock_achievements(self.user)
        self.assertEqual(len(unlocked), 1)
        self.assertEqual(unlocked[0].achievement.code, 'FIRST_TASK')

        # Check idempotency: second check shouldn't re-unlock or re-award
        unlocked_again = check_and_unlock_achievements(self.user)
        self.assertEqual(len(unlocked_again), 0)
