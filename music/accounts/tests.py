from django.test import TestCase
from django.urls import reverse


class RegisterViewTests(TestCase):
    def test_register_redirects_to_home_with_success_message(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "melody_fan",
                "email": "melody@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("home"))

        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "melody_fan account created successfully!")

    def test_register_popup_rendered_on_home_page(self):
        self.client.post(
            reverse("register"),
            {
                "username": "melody_fan",
                "email": "melody@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        response = self.client.get(reverse("home"))
        self.assertContains(
            response, "melody_fan account created successfully!"
        )
        self.assertContains(response, "toast-popup")
