import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.bulk_email.models import BulkEmail, BulkEmailAttachment, BulkEmailRecipient
from apps.schools.models import Person, School

User = get_user_model()


def make_staff(username="staff"):
    return User.objects.create_user(username=username, password="pw", is_staff=True)


class BulkEmailListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff()
        self.client.login(username="staff", password="pw")
        self.campaign = BulkEmail.objects.create(
            subject="Test",
            body_html="<p>x</p>",
            recipient_type=BulkEmail.KOORDINATOR,
        )

    def test_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("bulk_email:list"))
        self.assertNotEqual(response.status_code, 200)

    def test_list_returns_200_for_staff(self):
        response = self.client.get(reverse("bulk_email:list"))
        self.assertEqual(response.status_code, 200)

    def test_list_shows_campaign(self):
        response = self.client.get(reverse("bulk_email:list"))
        self.assertContains(response, "Test")

    def test_interrupted_campaign_appears_before_sent(self):
        from django.utils import timezone

        BulkEmail.objects.create(
            subject="Sent", body_html="", recipient_type=BulkEmail.KOORDINATOR, sent_at=timezone.now()
        )
        interrupted = BulkEmail.objects.create(subject="Afbrudt", body_html="", recipient_type=BulkEmail.KOORDINATOR)
        from apps.schools.models import School

        s = School.objects.create(name="S", signup_token="t", signup_password="p")
        BulkEmailRecipient.objects.create(bulk_email=interrupted, school=s, email="x@x.dk", success=True)
        response = self.client.get(reverse("bulk_email:list"))
        content = response.content.decode()
        self.assertLess(content.index("Afbrudt"), content.index("Sent"))


class BulkEmailDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff()
        self.client.login(username="staff", password="pw")
        self.school = School.objects.create(name="Skole", signup_token="tok", signup_password="pw")
        self.person = Person.objects.create(school=self.school, name="P", email="p@s.dk")
        from django.utils import timezone

        self.campaign = BulkEmail.objects.create(
            subject="Detaljetest",
            body_html="<p>x</p>",
            recipient_type=BulkEmail.KOORDINATOR,
            sent_at=timezone.now(),
        )
        BulkEmailRecipient.objects.create(
            bulk_email=self.campaign,
            school=self.school,
            person=self.person,
            email="p@s.dk",
            success=True,
        )

    def test_detail_returns_200(self):
        response = self.client.get(reverse("bulk_email:detail", args=[self.campaign.pk]))
        self.assertEqual(response.status_code, 200)

    def test_detail_shows_recipient(self):
        response = self.client.get(reverse("bulk_email:detail", args=[self.campaign.pk]))
        self.assertContains(response, "Skole")


class AttachmentUploadTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff("staff2")
        self.client.login(username="staff2", password="pw")

    def test_upload_returns_pk(self):
        f = SimpleUploadedFile("test.pdf", b"PDF content", content_type="application/pdf")
        response = self.client.post(
            reverse("bulk_email:attachment_upload"),
            {"file": f},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("pk", data)
        self.assertEqual(data["filename"], "test.pdf")

    def test_upload_requires_staff(self):
        self.client.logout()
        f = SimpleUploadedFile("test.pdf", b"PDF content", content_type="application/pdf")
        response = self.client.post(reverse("bulk_email:attachment_upload"), {"file": f})
        self.assertNotEqual(response.status_code, 200)


class AttachmentDownloadTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff("staff3")
        self.client.login(username="staff3", password="pw")
        self.attachment = BulkEmailAttachment.objects.create(
            filename="doc.pdf",
            file=SimpleUploadedFile("doc.pdf", b"content"),
        )

    def test_download_returns_200_for_staff(self):
        response = self.client.get(reverse("bulk_email:attachment_download", args=[self.attachment.pk]))
        self.assertEqual(response.status_code, 200)

    def test_download_requires_staff(self):
        self.client.logout()
        response = self.client.get(reverse("bulk_email:attachment_download", args=[self.attachment.pk]))
        self.assertNotEqual(response.status_code, 200)


class PreviewViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff("staff4")
        self.client.login(username="staff4", password="pw")
        self.school = School.objects.create(name="Preview Skole", signup_token="tok4", signup_password="pw4")
        Person.objects.create(school=self.school, name="KA", email="ka@s.dk", is_koordinator=True)

    def test_preview_renders_school_name(self):
        response = self.client.post(
            reverse("bulk_email:preview"),
            json.dumps(
                {
                    "school_pk": self.school.pk,
                    "subject": "Hej {{ skole_navn }}",
                    "body_html": "<p>Kære {{ kontakt_navn }}</p>",
                    "recipient_type": BulkEmail.KOORDINATOR,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preview Skole")
        self.assertContains(response, "KA")

    def test_preview_returns_404_for_unknown_school(self):
        response = self.client.post(
            reverse("bulk_email:preview"),
            json.dumps({"school_pk": 99999, "subject": "x", "body_html": "x", "recipient_type": BulkEmail.KOORDINATOR}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)


class DryRunViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_staff("staff5")
        self.client.login(username="staff5", password="pw")
        self.school = School.objects.create(
            name="DryRun Skole",
            kommune="Vejle",
            enrolled_at="2024-08-01",
            active_from="2024-08-01",
            signup_token="tok5",
            signup_password="pw5",
        )
        Person.objects.create(school=self.school, name="KB", email="kb@s.dk", is_koordinator=True)

    def test_dry_run_returns_recipients(self):
        response = self.client.post(
            reverse("bulk_email:dry_run"),
            json.dumps(
                {
                    "recipient_type": BulkEmail.KOORDINATOR,
                    "subject": "{{ skole_navn }}",
                    "body_html": "",
                    "filter_params": {"kommune": "Vejle"},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("recipients", data)
        self.assertEqual(len(data["recipients"]), 1)
        self.assertEqual(data["recipients"][0]["school"], "DryRun Skole")

    def test_dry_run_reports_missing_fields(self):
        response = self.client.post(
            reverse("bulk_email:dry_run"),
            json.dumps(
                {
                    "recipient_type": BulkEmail.KOORDINATOR,
                    "subject": "{{ ean_nummer }}",
                    "body_html": "",
                    "filter_params": {"kommune": "Vejle"},
                }
            ),
            content_type="application/json",
        )
        data = json.loads(response.content)
        self.assertTrue(any("ean_nummer" in w["variable"] for w in data["warnings"]))
