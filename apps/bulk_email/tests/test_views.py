from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.bulk_email.models import BulkEmail, BulkEmailRecipient
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
