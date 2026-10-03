from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, date
from unittest.mock import patch
from accounts.models import CustomUser, Profile
from habits.models import Habit, HabitCompletion


def make_user(username, password='password123', tz='UTC'):
    u = CustomUser.objects.create_user(username=username, password=password)
    p, _ = Profile.objects.get_or_create(user=u)
    p.timezone = tz
    p.save()
    return u


def make_habit(user, name='Test Habit', frequency='DAILY'):
    return Habit.objects.create(
        user=user, name=name, frequency=frequency,
        active_from=timezone.now().date()
    )


class HabitCRUDTests(TestCase):
    def setUp(self):
        self.user = make_user('habituser')
        self.client.login(username='habituser', password='password123')

    def test_habit_list_requires_login(self):
        self.client.logout()
        r = self.client.get(reverse('habits:list'))
        self.assertEqual(r.status_code, 302)

    def test_habit_list_authenticated(self):
        make_habit(self.user, name='Morning Run')
        r = self.client.get(reverse('habits:list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Morning Run')

    def test_habit_create(self):
        r = self.client.post(reverse('habits:create'), {
            'name': 'Read 30min', 'frequency': 'DAILY',
            'active_from': timezone.now().date().isoformat()
        })
        self.assertEqual(Habit.objects.filter(user=self.user, name='Read 30min').count(), 1)
        habit = Habit.objects.get(name='Read 30min')
        self.assertRedirects(r, reverse('habits:detail', args=[habit.pk]))

    def test_habit_create_validates_name(self):
        r = self.client.post(reverse('habits:create'), {
            'name': '', 'frequency': 'DAILY',
            'active_from': timezone.now().date().isoformat()
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Habit.objects.filter(user=self.user).count(), 0)

    def test_habit_detail(self):
        habit = make_habit(self.user)
        r = self.client.get(reverse('habits:detail', args=[habit.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, habit.name)

    def test_habit_update(self):
        habit = make_habit(self.user, name='Old Name')
        r = self.client.post(reverse('habits:update', args=[habit.pk]), {
            'name': 'New Name', 'frequency': 'WEEKLY',
            'active_from': timezone.now().date().isoformat()
        })
        self.assertRedirects(r, reverse('habits:detail', args=[habit.pk]))
        habit.refresh_from_db()
        self.assertEqual(habit.name, 'New Name')

    def test_habit_archive(self):
        habit = make_habit(self.user)
        r = self.client.post(reverse('habits:archive', args=[habit.pk]))
        self.assertRedirects(r, reverse('habits:list'))
        habit.refresh_from_db()
        self.assertTrue(habit.is_archived)

    def test_archived_habit_not_in_list(self):
        habit = make_habit(self.user, name='Archived Habit')
        habit.is_archived = True
        habit.save()
        r = self.client.get(reverse('habits:list'))
        self.assertNotContains(r, 'Archived Habit')


class HabitCompletionTests(TestCase):
    def setUp(self):
        self.user = make_user('completionuser')
        self.habit = make_habit(self.user)
        self.client.login(username='completionuser', password='password123')

    def test_complete_habit_today(self):
        r = self.client.post(reverse('habits:complete', args=[self.habit.pk]))
        self.assertRedirects(r, reverse('habits:detail', args=[self.habit.pk]))
        today = self.habit.get_user_today()
        self.assertTrue(HabitCompletion.objects.filter(habit=self.habit, local_date=today).exists())

    def test_complete_creates_single_record(self):
        """Double-completing should not create duplicate (unique_together constraint)."""
        today = self.habit.get_user_today()
        HabitCompletion.objects.create(habit=self.habit, local_date=today)
        # Attempting to create again via toggle should delete (undo)
        self.client.post(reverse('habits:complete', args=[self.habit.pk]))
        self.assertEqual(HabitCompletion.objects.filter(habit=self.habit, local_date=today).count(), 0)

    def test_toggle_uncompletes(self):
        """Completing when already done today should delete the record."""
        today = self.habit.get_user_today()
        HabitCompletion.objects.create(habit=self.habit, local_date=today)
        self.client.post(reverse('habits:complete', args=[self.habit.pk]))
        self.assertFalse(HabitCompletion.objects.filter(habit=self.habit, local_date=today).exists())

    def test_completion_persists_on_reload(self):
        today = self.habit.get_user_today()
        HabitCompletion.objects.create(habit=self.habit, local_date=today)
        # Reload from DB
        exists = HabitCompletion.objects.filter(habit=self.habit, local_date=today).exists()
        self.assertTrue(exists)


class HabitStreakTests(TestCase):
    def setUp(self):
        self.user = make_user('streakuser')
        self.habit = make_habit(self.user)

    def test_zero_streak_with_no_completions(self):
        self.assertEqual(self.habit.get_current_streak(), 0)

    def test_streak_one_day(self):
        today = self.habit.get_user_today()
        HabitCompletion.objects.create(habit=self.habit, local_date=today)
        self.assertEqual(self.habit.get_current_streak(), 1)

    def test_streak_three_consecutive_days(self):
        today = self.habit.get_user_today()
        for i in range(3):
            HabitCompletion.objects.create(habit=self.habit, local_date=today - timedelta(days=i))
        self.assertEqual(self.habit.get_current_streak(), 3)

    def test_streak_breaks_on_missed_day(self):
        today = self.habit.get_user_today()
        # Completed today and 3 days ago but not yesterday or 2 days ago
        HabitCompletion.objects.create(habit=self.habit, local_date=today)
        HabitCompletion.objects.create(habit=self.habit, local_date=today - timedelta(days=3))
        # Streak should be 1 (only today, yesterday is missing)
        self.assertEqual(self.habit.get_current_streak(), 1)

    def test_streak_from_yesterday_if_today_not_done(self):
        today = self.habit.get_user_today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)
        HabitCompletion.objects.create(habit=self.habit, local_date=yesterday)
        HabitCompletion.objects.create(habit=self.habit, local_date=day_before)
        self.assertEqual(self.habit.get_current_streak(), 2)

    def test_future_dates_do_not_count(self):
        today = self.habit.get_user_today()
        HabitCompletion.objects.create(habit=self.habit, local_date=today + timedelta(days=1))
        # future date in set, but today not done, yesterday not done → streak = 0
        self.assertEqual(self.habit.get_current_streak(), 0)

    def test_completion_history_returns_last_30_days(self):
        today = self.habit.get_user_today()
        for i in range(5):
            HabitCompletion.objects.create(habit=self.habit, local_date=today - timedelta(days=i))
        # Older than 30 days should not appear
        HabitCompletion.objects.create(habit=self.habit, local_date=today - timedelta(days=40))
        history = list(self.habit.get_completion_history(days=30))
        self.assertEqual(len(history), 5)

    def test_best_streak_calculation(self):
        self.assertEqual(self.habit.best_streak, 0)
        today = self.habit.get_user_today()
        # Create a 2-day streak in the past
        HabitCompletion.objects.create(habit=self.habit, local_date=today - timedelta(days=10))
        HabitCompletion.objects.create(habit=self.habit, local_date=today - timedelta(days=9))
        self.assertEqual(self.habit.best_streak, 2)

        # Create a 4-day streak later
        for i in range(4):
            HabitCompletion.objects.create(habit=self.habit, local_date=today - timedelta(days=i))
        self.assertEqual(self.habit.best_streak, 4)



class HabitOwnershipTests(TestCase):
    def setUp(self):
        self.owner = make_user('habitowner')
        self.attacker = make_user('habitattacker')
        self.habit = make_habit(self.owner)
        self.client.login(username='habitattacker', password='password123')

    def test_other_user_cannot_view_habit(self):
        r = self.client.get(reverse('habits:detail', args=[self.habit.pk]))
        self.assertEqual(r.status_code, 404)

    def test_other_user_cannot_edit_habit(self):
        r = self.client.post(reverse('habits:update', args=[self.habit.pk]), {
            'name': 'Hacked', 'frequency': 'DAILY',
            'active_from': timezone.now().date().isoformat()
        })
        self.assertEqual(r.status_code, 404)

    def test_other_user_cannot_complete_habit(self):
        r = self.client.post(reverse('habits:complete', args=[self.habit.pk]))
        self.assertEqual(r.status_code, 404)

    def test_other_user_cannot_archive_habit(self):
        r = self.client.post(reverse('habits:archive', args=[self.habit.pk]))
        self.assertEqual(r.status_code, 404)
