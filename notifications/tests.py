from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from notifications.models import Notification, NotificationPreference
from notifications.services import (
    create_notification,
    get_or_create_user_preferences,
    is_notification_type_enabled,
    get_unread_count,
    mark_notification_as_read,
    mark_all_notifications_as_read,
)
from notifications.tasks import (
    process_due_task_notifications,
    process_habit_reminders,
    process_deadline_notifications,
    process_streak_notifications,
)
from tasks.models import Task
from habits.models import Habit, HabitCompletion
from goals.models import Goal
from arcs.models import Arc
from gamification.models import Achievement, UserAchievement
from gamification.services import check_and_unlock_achievements, get_user_rank

User = get_user_model()


class NotificationModelAndServiceTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='user_a', password='password123')
        self.user_b = User.objects.create_user(username='user_b', password='password123')

    def test_create_notification_success(self):
        n, created = create_notification(
            user=self.user_a,
            notification_type=Notification.TYPE_TASK_DUE_SOON,
            title="Task Due Soon",
            message="Your task is approaching its deadline.",
            dedup_key="test_task_due_1"
        )
        self.assertTrue(created)
        self.assertIsNotNone(n)
        self.assertEqual(n.user, self.user_a)
        self.assertFalse(n.is_read)

    def test_deterministic_deduplication(self):
        # First call creates notification
        n1, created1 = create_notification(
            user=self.user_a,
            notification_type=Notification.TYPE_TASK_DUE_SOON,
            title="Task Due Soon",
            message="Task due alert.",
            dedup_key="dedup_task_123"
        )
        self.assertTrue(created1)

        # Second call with same dedup_key returns existing and does NOT create a duplicate
        n2, created2 = create_notification(
            user=self.user_a,
            notification_type=Notification.TYPE_TASK_DUE_SOON,
            title="Task Due Soon (duplicate attempt)",
            message="Duplicate attempt.",
            dedup_key="dedup_task_123"
        )
        self.assertFalse(created2)
        self.assertEqual(n1.pk, n2.pk)
        self.assertEqual(Notification.objects.filter(user=self.user_a).count(), 1)

    def test_preferences_suppression(self):
        prefs = get_or_create_user_preferences(self.user_a)
        prefs.task_reminders_enabled = False
        prefs.save()

        # Should be suppressed
        n, created = create_notification(
            user=self.user_a,
            notification_type=Notification.TYPE_TASK_DUE_SOON,
            title="Task Due",
            message="Suppressed task.",
            dedup_key="suppressed_task_1"
        )
        self.assertIsNone(n)
        self.assertFalse(created)
        self.assertEqual(Notification.objects.filter(user=self.user_a).count(), 0)

        # Force bypasses preference
        n_forced, created_forced = create_notification(
            user=self.user_a,
            notification_type=Notification.TYPE_TASK_DUE_SOON,
            title="Forced Task Due",
            message="Forced task.",
            dedup_key="forced_task_1",
            force=True
        )
        self.assertIsNotNone(n_forced)
        self.assertTrue(created_forced)

    def test_mark_read_and_unread_counts(self):
        n1, _ = create_notification(self.user_a, Notification.TYPE_TASK_DUE_SOON, "T1", "M1", "k1")
        n2, _ = create_notification(self.user_a, Notification.TYPE_TASK_DUE_SOON, "T2", "M2", "k2")
        self.assertEqual(get_unread_count(self.user_a), 2)

        # Mark single
        success = mark_notification_as_read(self.user_a, n1.pk)
        self.assertTrue(success)
        self.assertEqual(get_unread_count(self.user_a), 1)

        # Cross-user isolation: user_b cannot mark user_a's notification
        cross_success = mark_notification_as_read(self.user_b, n2.pk)
        self.assertFalse(cross_success)
        self.assertEqual(get_unread_count(self.user_a), 1)

        # Mark all read
        mark_all_notifications_as_read(self.user_a)
        self.assertEqual(get_unread_count(self.user_a), 0)


class CeleryTaskWorkerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='worker_user', password='password123')
        self.arc = Arc.objects.create(
            user=self.user,
            name="Winter Arc Test",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=5),
            status='ACTIVE'
        )
        self.goal = Goal.objects.create(
            arc=self.arc,
            user=self.user,
            title="Strategic Goal Test",
            deadline=timezone.now().date() + timedelta(days=3),
            status='IN_PROGRESS'
        )

    def test_process_due_task_notifications_due_soon_and_overdue(self):
        now = timezone.now()
        # 1. Overdue task
        task_overdue = Task.objects.create(
            user=self.user,
            goal=self.goal,
            title="Overdue Task",
            due_at=now - timedelta(hours=2),
            status='PENDING'
        )
        # 2. Due soon task (due in 5 hours)
        task_due_soon = Task.objects.create(
            user=self.user,
            goal=self.goal,
            title="Due Soon Task",
            due_at=now + timedelta(hours=5),
            status='PENDING'
        )
        # 3. Far future task (due in 48 hours - should not alert)
        Task.objects.create(
            user=self.user,
            goal=self.goal,
            title="Future Task",
            due_at=now + timedelta(hours=48),
            status='PENDING'
        )
        # 4. Completed task (should not alert even if due date passed)
        Task.objects.create(
            user=self.user,
            goal=self.goal,
            title="Completed Task",
            due_at=now - timedelta(hours=1),
            status='COMPLETED'
        )

        created_count = process_due_task_notifications()
        self.assertEqual(created_count, 2)

        # Assert correct notifications in database
        self.assertTrue(Notification.objects.filter(user=self.user, notification_type=Notification.TYPE_TASK_OVERDUE).exists())
        self.assertTrue(Notification.objects.filter(user=self.user, notification_type=Notification.TYPE_TASK_DUE_SOON).exists())

        # Retry-safety verification: running again creates 0 new notifications
        second_run_count = process_due_task_notifications()
        self.assertEqual(second_run_count, 0)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 2)

    def test_process_habit_reminders_unlit_and_suppression(self):
        today = timezone.now().date()
        # Habit 1: Active and unlit today
        h1 = Habit.objects.create(user=self.user, name="Deep Reading", active_from=today, is_archived=False)
        # Habit 2: Active and completed today
        h2 = Habit.objects.create(user=self.user, name="Hydration", active_from=today, is_archived=False)
        HabitCompletion.objects.create(habit=h2, local_date=today)
        # Habit 3: Archived habit (must be suppressed)
        Habit.objects.create(user=self.user, name="Archived Habit", active_from=today, is_archived=True)

        created_count = process_habit_reminders()
        self.assertEqual(created_count, 1)

        # Verify only h1 got a reminder
        notif = Notification.objects.get(user=self.user, notification_type=Notification.TYPE_HABIT_REMINDER)
        self.assertEqual(notif.source_id, str(h1.pk))

        # Re-running is idempotent
        self.assertEqual(process_habit_reminders(), 0)

    def test_process_deadline_notifications(self):
        # We already have self.arc (ends in 5 days) and self.goal (ends in 3 days) in setUp
        created_count = process_deadline_notifications()
        self.assertEqual(created_count, 2)

        self.assertTrue(Notification.objects.filter(user=self.user, notification_type=Notification.TYPE_GOAL_DEADLINE).exists())
        self.assertTrue(Notification.objects.filter(user=self.user, notification_type=Notification.TYPE_ARC_DEADLINE).exists())

        # Second run is idempotent
        self.assertEqual(process_deadline_notifications(), 0)

    def test_process_streak_notifications(self):
        today = timezone.now().date()
        h = Habit.objects.create(user=self.user, name="Meditation", active_from=today - timedelta(days=10), is_archived=False)
        # Seed 7 consecutive days of completions
        for i in range(7):
            HabitCompletion.objects.create(habit=h, local_date=today - timedelta(days=i))

        created_count = process_streak_notifications()
        self.assertEqual(created_count, 1)

        streak_notif = Notification.objects.get(user=self.user, notification_type=Notification.TYPE_STREAK_MILESTONE)
        self.assertIn("7-day streak", streak_notif.message)

        # Idempotent
        self.assertEqual(process_streak_notifications(), 0)


    def test_gamification_hooks_create_notifications(self):
        # Test achievement unlock notification hook
        Task.objects.create(
            user=self.user,
            goal=self.goal,
            title="First Step Task",
            status='COMPLETED'
        )
        unlocked = check_and_unlock_achievements(self.user)
        self.assertTrue(len(unlocked) > 0)

        self.assertTrue(Notification.objects.filter(
            user=self.user,
            notification_type=Notification.TYPE_ACHIEVEMENT_UNLOCKED
        ).exists())

        # Test rank promotion notification hook
        from gamification.services import award_xp
        award_xp(self.user, 'task', 'test_xp_1', amount=350, description="Test leveling")
        rank_data = get_user_rank(self.user)
        self.assertEqual(rank_data['current_rank'], 'Sentinel')
        self.assertTrue(Notification.objects.filter(
            user=self.user,
            notification_type=Notification.TYPE_RANK_ACHIEVED
        ).exists())


class NotificationViewAndSecurityTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='view_user1', password='password123')
        self.user2 = User.objects.create_user(username='view_user2', password='password123')

        self.notif1 = Notification.objects.create(
            user=self.user1,
            notification_type=Notification.TYPE_TASK_DUE_SOON,
            title="User 1 Task",
            message="Details",
            dedup_key="u1_t1"
        )
        self.notif2 = Notification.objects.create(
            user=self.user2,
            notification_type=Notification.TYPE_TASK_DUE_SOON,
            title="User 2 Task",
            message="Details",
            dedup_key="u2_t2"
        )

    def test_notification_list_scoped_to_authenticated_user(self):
        self.client.login(username='view_user1', password='password123')
        resp = self.client.get(reverse('notifications:list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "User 1 Task")
        self.assertNotContains(resp, "User 2 Task")

    def test_mark_read_view_and_cross_user_protection(self):
        self.client.login(username='view_user2', password='password123')
        # Attempt to mark user 1's notification as read
        resp = self.client.post(reverse('notifications:mark_read', args=[self.notif1.pk]))
        self.assertEqual(resp.status_code, 302)

        self.notif1.refresh_from_db()
        self.assertFalse(self.notif1.is_read) # User 1's notification remains unread!

        # Marking own notification works
        resp = self.client.post(reverse('notifications:mark_read', args=[self.notif2.pk]))
        self.notif2.refresh_from_db()
        self.assertTrue(self.notif2.is_read)

    def test_preferences_update_view(self):
        self.client.login(username='view_user1', password='password123')
        resp = self.client.get(reverse('notifications:preferences'))
        self.assertEqual(resp.status_code, 200)

        # POST update preferences
        post_data = {
            'task_reminders_enabled': False,
            'habit_reminders_enabled': True,
            'deadline_reminders_enabled': False,
            'gamification_alerts_enabled': True,
        }
        post_resp = self.client.post(reverse('notifications:preferences'), data=post_data)
        self.assertEqual(post_resp.status_code, 302)

        prefs = NotificationPreference.objects.get(user=self.user1)
        self.assertFalse(prefs.task_reminders_enabled)
        self.assertFalse(prefs.deadline_reminders_enabled)
        self.assertTrue(prefs.habit_reminders_enabled)
