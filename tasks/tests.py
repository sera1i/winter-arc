from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, date
from accounts.models import CustomUser, Profile
from arcs.models import Arc
from goals.models import Goal
from tasks.models import Task


def make_user(username, password='password123'):
    u = CustomUser.objects.create_user(username=username, password=password)
    Profile.objects.get_or_create(user=u)
    return u


def make_arc(user):
    return Arc.objects.create(
        user=user, name="Test Arc", status='ACTIVE',
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=30),
    )


def make_goal(user, arc):
    return Goal.objects.create(user=user, arc=arc, title="Test Goal", status='IN_PROGRESS')


class TaskCRUDTests(TestCase):
    def setUp(self):
        self.user = make_user('taskuser')
        self.other = make_user('otheruser')
        self.arc = make_arc(self.user)
        self.goal = make_goal(self.user, self.arc)
        self.client.login(username='taskuser', password='password123')

    def test_task_list_requires_login(self):
        self.client.logout()
        r = self.client.get(reverse('tasks:list'))
        self.assertEqual(r.status_code, 302)

    def test_task_list_authenticated(self):
        Task.objects.create(user=self.user, title='My Task')
        r = self.client.get(reverse('tasks:list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'My Task')

    def test_task_create(self):
        r = self.client.post(reverse('tasks:create'), {
            'title': 'New Task', 'priority': 2, 'status': 'PENDING'
        })
        self.assertEqual(Task.objects.filter(user=self.user, title='New Task').count(), 1)
        task = Task.objects.get(title='New Task')
        self.assertRedirects(r, reverse('tasks:detail', args=[task.pk]))

    def test_task_create_validates_title(self):
        r = self.client.post(reverse('tasks:create'), {'title': '', 'priority': 2, 'status': 'PENDING'})
        self.assertEqual(r.status_code, 200)  # stays on form
        self.assertEqual(Task.objects.filter(user=self.user).count(), 0)

    def test_task_detail(self):
        task = Task.objects.create(user=self.user, title='Detail Task')
        r = self.client.get(reverse('tasks:detail', args=[task.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Detail Task')

    def test_task_update(self):
        task = Task.objects.create(user=self.user, title='Old Title')
        r = self.client.post(reverse('tasks:update', args=[task.pk]), {
            'title': 'New Title', 'priority': 1, 'status': 'IN_PROGRESS'
        })
        self.assertRedirects(r, reverse('tasks:detail', args=[task.pk]))
        task.refresh_from_db()
        self.assertEqual(task.title, 'New Title')
        self.assertEqual(task.status, 'IN_PROGRESS')

    def test_task_complete_persists(self):
        task = Task.objects.create(user=self.user, title='Complete Me')
        r = self.client.post(reverse('tasks:complete', args=[task.pk]))
        self.assertRedirects(r, reverse('tasks:detail', args=[task.pk]))
        task.refresh_from_db()
        self.assertEqual(task.status, 'COMPLETED')
        self.assertIsNotNone(task.completed_at)

    def test_task_uncomplete_persists(self):
        task = Task.objects.create(user=self.user, title='Uncomplete Me', status='COMPLETED', completed_at=timezone.now())
        self.client.post(reverse('tasks:uncomplete', args=[task.pk]))
        task.refresh_from_db()
        self.assertEqual(task.status, 'PENDING')
        self.assertIsNone(task.completed_at)

    def test_task_cancel(self):
        task = Task.objects.create(user=self.user, title='Cancel Me')
        r = self.client.post(reverse('tasks:delete', args=[task.pk]))
        self.assertRedirects(r, reverse('tasks:list'))
        task.refresh_from_db()
        self.assertEqual(task.status, 'CANCELLED')

    def test_task_goal_link_scoped_to_user(self):
        """Goal belonging to other user must not be attachable."""
        other_arc = make_arc(self.other)
        other_goal = make_goal(self.other, other_arc)
        self.client.post(reverse('tasks:create'), {
            'title': 'Hijack Task', 'priority': 2, 'status': 'PENDING',
            'goal': other_goal.pk,
        })
        task = Task.objects.filter(title='Hijack Task').first()
        if task:
            self.assertIsNone(task.goal)


class TaskOwnershipTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.attacker = make_user('attacker')
        self.task = Task.objects.create(user=self.owner, title='Private Task')
        self.client.login(username='attacker', password='password123')

    def test_other_user_cannot_view_task(self):
        r = self.client.get(reverse('tasks:detail', args=[self.task.pk]))
        self.assertEqual(r.status_code, 404)

    def test_other_user_cannot_edit_task(self):
        r = self.client.post(reverse('tasks:update', args=[self.task.pk]), {'title': 'Hacked'})
        self.assertEqual(r.status_code, 404)

    def test_other_user_cannot_complete_task(self):
        r = self.client.post(reverse('tasks:complete', args=[self.task.pk]))
        self.assertEqual(r.status_code, 404)

    def test_other_user_cannot_delete_task(self):
        r = self.client.post(reverse('tasks:delete', args=[self.task.pk]))
        self.assertEqual(r.status_code, 404)
