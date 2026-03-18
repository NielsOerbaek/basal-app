from django.test import TestCase

from apps.bulk_email.models import BulkEmail, BulkEmailRecipient
from apps.schools.models import School


class BulkEmailModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Testskole", signup_token="tok", signup_password="pw")
        self.campaign = BulkEmail.objects.create(
            subject="Test emne",
            body_html="<p>Hej {{ skole_navn }}</p>",
            recipient_type=BulkEmail.KOORDINATOR,
            filter_params={"kommune": "Aarhus"},
        )

    def test_is_sent_false_before_send(self):
        self.assertFalse(self.campaign.is_sent)

    def test_is_interrupted_false_with_no_recipients(self):
        self.assertFalse(self.campaign.is_interrupted)

    def test_is_interrupted_true_with_recipients_and_no_sent_at(self):
        BulkEmailRecipient.objects.create(
            bulk_email=self.campaign,
            school=self.school,
            email="test@test.dk",
            success=True,
        )
        self.assertTrue(self.campaign.is_interrupted)
