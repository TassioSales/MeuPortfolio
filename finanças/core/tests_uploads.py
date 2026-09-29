from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse


class ImportUploadValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ivan", password="pass12345")
        self.client.login(username="ivan", password="pass12345")

    def test_rejects_disallowed_extension(self):
        bad_file = SimpleUploadedFile("extrato.exe", b"conteudo qualquer", content_type="application/octet-stream")
        response = self.client.post(reverse("transaction_import"), {"file": bad_file})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)

    def test_rejects_oversized_file(self):
        big_content = b"a" * (6 * 1024 * 1024)
        big_file = SimpleUploadedFile("extrato.csv", big_content, content_type="text/csv")
        response = self.client.post(reverse("transaction_import"), {"file": big_file})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)


class OfxUploadValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="julia", password="pass12345")
        self.client.login(username="julia", password="pass12345")

    def test_rejects_disallowed_extension(self):
        bad_file = SimpleUploadedFile("extrato.txt", b"not ofx", content_type="text/plain")
        response = self.client.post(reverse("import_ofx"), {"ofx_file": bad_file}, follow=True)
        page_messages = list(response.context["messages"])
        self.assertTrue(any(".ofx" in str(m) for m in page_messages))

    def test_rejects_oversized_file(self):
        big_content = b"a" * (6 * 1024 * 1024)
        big_file = SimpleUploadedFile("extrato.ofx", big_content, content_type="application/x-ofx")
        response = self.client.post(reverse("import_ofx"), {"ofx_file": big_file}, follow=True)
        page_messages = list(response.context["messages"])
        self.assertTrue(any("grande" in str(m) for m in page_messages))
