from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class SettingsAccessTests(TestCase):
    def test_non_staff_user_is_redirected_away(self):
        User.objects.create_user(username="karl", password="pass12345")
        self.client.login(username="karl", password="pass12345")
        response = self.client.get(reverse("settings"), follow=True)
        self.assertRedirects(response, reverse("dashboard"))

    def test_staff_user_can_access_settings(self):
        User.objects.create_user(username="laura", password="pass12345", is_staff=True)
        self.client.login(username="laura", password="pass12345")
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 200)
