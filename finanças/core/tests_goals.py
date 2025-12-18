from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Goal
from django.utils import timezone
import datetime

class GoalTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        self.deadline = timezone.now().date() + datetime.timedelta(days=365)

    def test_create_goal(self):
        response = self.client.post(reverse('goal_add'), {
            'name': 'Comprar Carro',
            'target_amount': 50000,
            'current_amount': 5000,
            'deadline': self.deadline,
            'description': 'Economizar para um carro novo'
        })
        self.assertEqual(response.status_code, 302) # Redirects to list
        self.assertEqual(Goal.objects.count(), 1)
        goal = Goal.objects.first()
        self.assertEqual(goal.name, 'Comprar Carro')
        self.assertEqual(goal.progress_percentage, 10) # 5000/50000 = 10%

    def test_update_goal(self):
        goal = Goal.objects.create(
            user=self.user,
            name='Viagem',
            target_amount=10000,
            current_amount=2000,
            deadline=self.deadline
        )
        
        response = self.client.post(reverse('goal_edit', args=[goal.pk]), {
            'name': 'Viagem Europa',
            'target_amount': 10000,
            'current_amount': 8000,
            'deadline': self.deadline,
            'description': 'Atualizado'
        })
        self.assertEqual(response.status_code, 302)
        
        goal.refresh_from_db()
        self.assertEqual(goal.name, 'Viagem Europa')
        self.assertEqual(goal.current_amount, 8000)
        self.assertEqual(goal.progress_percentage, 80)

    def test_delete_goal(self):
        goal = Goal.objects.create(
            user=self.user,
            name='Delete Me',
            target_amount=100,
            current_amount=0,
            deadline=self.deadline
        )
        
        response = self.client.post(reverse('goal_delete', args=[goal.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Goal.objects.count(), 0)
