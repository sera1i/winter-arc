from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomUser, Profile
from arcs.models import Arc

class ArcTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='arctest', password='password123')
        Profile.objects.get_or_create(user=self.user)
        self.client.login(username='arctest', password='password123')
        
        self.today = timezone.now().date()
        self.tomorrow = self.today + timedelta(days=1)
        
        self.arc = Arc.objects.create(
            user=self.user,
            name="Initial Arc",
            objective="Initial objective",
            start_date=self.today,
            end_date=self.tomorrow,
            status='ACTIVE'
        )

    def test_arc_list_view(self):
        response = self.client.get(reverse('arcs:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Initial Arc")

    def test_arc_create(self):
        response = self.client.post(reverse('arcs:create'), {
            'name': 'New Arc',
            'objective': 'New objective',
            'start_date': self.today,
            'end_date': self.tomorrow,
            'status': 'DRAFT',
            'timezone': 'UTC'
        })
        self.assertEqual(Arc.objects.count(), 2)
        new_arc = Arc.objects.get(name='New Arc')
        self.assertRedirects(response, reverse('arcs:detail', args=[new_arc.pk]))

    def test_arc_create_invalid_dates(self):
        response = self.client.post(reverse('arcs:create'), {
            'name': 'Bad Arc',
            'objective': 'Bad objective',
            'start_date': self.tomorrow,
            'end_date': self.today, # End date before start date
            'status': 'DRAFT',
            'timezone': 'UTC'
        })
        self.assertEqual(response.status_code, 200) # Form renders with errors
        self.assertContains(response, "Start date cannot be after end date")
        self.assertEqual(Arc.objects.count(), 1) # Only initial arc

    def test_arc_update(self):
        response = self.client.post(reverse('arcs:update', args=[self.arc.pk]), {
            'name': 'Updated Arc',
            'objective': 'Updated objective',
            'start_date': self.today,
            'end_date': self.tomorrow,
            'status': 'ACTIVE',
            'timezone': 'UTC'
        })
        self.arc.refresh_from_db()
        self.assertEqual(self.arc.name, 'Updated Arc')
        self.assertRedirects(response, reverse('arcs:detail', args=[self.arc.pk]))

    def test_arc_archive(self):
        response = self.client.post(reverse('arcs:delete', args=[self.arc.pk]))
        self.arc.refresh_from_db()
        self.assertEqual(self.arc.status, 'ARCHIVED')
        self.assertRedirects(response, reverse('arcs:list'))

    def test_arc_make_primary(self):
        # Create second active arc
        arc2 = Arc.objects.create(
            user=self.user, name="Arc 2", objective="Obj", 
            start_date=self.today, end_date=self.tomorrow, status='ACTIVE'
        )
        # Make Arc 2 primary
        response = self.client.post(reverse('arcs:make_primary', args=[arc2.pk]))
        arc2.refresh_from_db()
        self.assertTrue(arc2.is_primary)
        
        # Now make initial arc primary
        response = self.client.post(reverse('arcs:make_primary', args=[self.arc.pk]))
        self.arc.refresh_from_db()
        arc2.refresh_from_db()
        
        self.assertTrue(self.arc.is_primary)
        self.assertFalse(arc2.is_primary) # Ensured unique primary arc
