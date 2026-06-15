from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class LoginRedirectAuthenticatedUserTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("logintest", password="testpass123!")
        self.client.force_login(self.user)

    def test_authenticated_user_visiting_login_is_redirected(self):
        response = self.client.get(reverse("login"))
        self.assertRedirects(response, "/")
