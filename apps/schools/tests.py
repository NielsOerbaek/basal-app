from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Invoice, Person, PersonRole, School, SchoolComment, SchoolYear, SeatPurchase, TitelChoice


class SchoolExtendedFieldsTest(TestCase):
    def test_school_has_postnummer_field(self):
        """School model has postnummer field."""
        school = School.objects.create(
            name="Test School",
            adresse="Testvej 1",
            kommune="København",
            postnummer="2100",
            by="København Ø",
            ean_nummer="5790001234567",
        )
        self.assertEqual(school.postnummer, "2100")

    def test_school_has_by_field(self):
        """School model has by field."""
        school = School.objects.create(
            name="Test School",
            adresse="Testvej 1",
            kommune="København",
            postnummer="2100",
            by="København Ø",
            ean_nummer="5790001234567",
        )
        self.assertEqual(school.by, "København Ø")

    def test_school_has_ean_nummer_field(self):
        """School model has ean_nummer field."""
        school = School.objects.create(
            name="Test School",
            adresse="Testvej 1",
            kommune="København",
            postnummer="2100",
            by="København Ø",
            ean_nummer="5790001234567",
        )
        self.assertEqual(school.ean_nummer, "5790001234567")


class SchoolModelTest(TestCase):
    def test_create_school(self):
        """School model can be created and saved."""
        school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        self.assertEqual(school.name, "Test School")
        self.assertTrue(school.is_active)

    def test_soft_delete(self):
        """School soft delete sets is_active to False."""
        school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        school.delete()
        school.refresh_from_db()
        self.assertFalse(school.is_active)

    def test_active_manager(self):
        """School.objects.active() returns only active schools."""
        active = School.objects.create(
            name="Active School",
            adresse="Address",
            kommune="Kommune",
        )
        inactive = School.objects.create(name="Inactive School", adresse="Address", kommune="Kommune", is_active=False)
        self.assertIn(active, School.objects.active())
        self.assertNotIn(inactive, School.objects.active())

    def test_base_seats_without_enrollment(self):
        """School without enrolled_at has 0 base seats."""
        school = School.objects.create(name="Test", adresse="Test", kommune="Test")
        self.assertEqual(school.base_seats, 0)

    def test_base_seats_with_enrollment(self):
        """School with enrolled_at has BASE_SEATS."""
        school = School.objects.create(name="Test", adresse="Test", kommune="Test", enrolled_at=date.today())
        self.assertEqual(school.base_seats, School.BASE_SEATS)

    def test_forankringsplads_before_one_year(self):
        """School enrolled less than 1 year ago has no forankringsplads."""
        school = School.objects.create(
            name="Test", adresse="Test", kommune="Test", enrolled_at=date.today() - timedelta(days=100)
        )
        self.assertFalse(school.has_forankringsplads)
        self.assertEqual(school.forankring_seats, 0)

    def test_forankringsplads_after_one_year(self):
        """School enrolled more than 1 year ago has forankringsplads."""
        school = School.objects.create(
            name="Test", adresse="Test", kommune="Test", enrolled_at=date.today() - timedelta(days=400)
        )
        self.assertTrue(school.has_forankringsplads)
        self.assertEqual(school.forankring_seats, School.FORANKRING_SEATS)

    def test_exceeds_seat_allocation_false_when_under(self):
        """exceeds_seat_allocation is False when used_seats <= total_seats."""
        from apps.courses.models import Course, CourseSignUp, Location

        school = School.objects.create(name="Test", adresse="Test", kommune="Test", enrolled_at=date.today())
        location = Location.objects.create(name="Test Location")
        # School has 3 base seats, create 2 signups
        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
            location=location,
            capacity=10,
        )
        CourseSignUp.objects.create(course=course, school=school, participant_name="A", participant_email="a@test.com")
        CourseSignUp.objects.create(course=course, school=school, participant_name="B", participant_email="b@test.com")
        self.assertEqual(school.used_seats, 2)
        self.assertEqual(school.total_seats, 3)
        self.assertFalse(school.exceeds_seat_allocation)

    def test_exceeds_seat_allocation_true_when_over(self):
        """exceeds_seat_allocation is True when used_seats > total_seats."""
        from apps.courses.models import Course, CourseSignUp, Location

        school = School.objects.create(name="Test", adresse="Test", kommune="Test", enrolled_at=date.today())
        location = Location.objects.create(name="Test Location")
        # School has 3 base seats, create 4 signups to exceed
        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
            location=location,
            capacity=10,
        )
        for i in range(4):
            CourseSignUp.objects.create(
                course=course, school=school, participant_name=f"Person {i}", participant_email=f"p{i}@test.com"
            )
        self.assertEqual(school.used_seats, 4)
        self.assertEqual(school.total_seats, 3)
        self.assertTrue(school.exceeds_seat_allocation)


class PersonModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )

    def test_create_person(self):
        """Person model can be created and saved."""
        person = Person.objects.create(
            school=self.school,
            name="Test Person",
            role=PersonRole.KOORDINATOR,
            email="test@example.com",
            phone="12345678",
        )
        self.assertEqual(person.name, "Test Person")
        self.assertEqual(person.school, self.school)

    def test_display_role_standard(self):
        """display_role returns label for standard roles."""
        person = Person.objects.create(school=self.school, name="Test", role=PersonRole.KOORDINATOR)
        self.assertEqual(person.display_role, "Koordinator")

    def test_display_role_other(self):
        """display_role returns role_other for ANDET role."""
        person = Person.objects.create(school=self.school, name="Test", role=PersonRole.ANDET, role_other="Custom Role")
        self.assertEqual(person.display_role, "Custom Role")

    def test_display_role_other_empty(self):
        """display_role returns 'Andet' when ANDET role has no role_other."""
        person = Person.objects.create(school=self.school, name="Test", role=PersonRole.ANDET)
        self.assertEqual(person.display_role, "Andet")

    def test_person_ordering(self):
        """Persons are ordered by is_primary (desc), then name."""
        person1 = Person.objects.create(school=self.school, name="Zach", is_primary=False)
        person2 = Person.objects.create(school=self.school, name="Alice", is_primary=True)
        person3 = Person.objects.create(school=self.school, name="Bob", is_primary=False)
        people = list(self.school.people.all())
        self.assertEqual(people[0], person2)  # Alice (primary)
        self.assertEqual(people[1], person3)  # Bob
        self.assertEqual(people[2], person1)  # Zach


class SchoolCommentModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_create_comment(self):
        """SchoolComment model can be created and saved."""
        comment = SchoolComment.objects.create(school=self.school, comment="Test comment", created_by=self.user)
        self.assertEqual(comment.comment, "Test comment")
        self.assertEqual(comment.school, self.school)
        self.assertEqual(comment.created_by, self.user)

    def test_comment_ordering(self):
        """Comments are ordered by created_at descending."""
        comment1 = SchoolComment.objects.create(school=self.school, comment="First", created_by=self.user)
        comment2 = SchoolComment.objects.create(school=self.school, comment="Second", created_by=self.user)
        comments = list(self.school.school_comments.all())
        self.assertEqual(comments[0], comment2)  # Most recent first
        self.assertEqual(comments[1], comment1)


class SchoolViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )

    def test_school_list_requires_login(self):
        """School list should redirect unauthenticated users."""
        response = self.client.get(reverse("schools:list"))
        self.assertEqual(response.status_code, 302)

    def test_school_list_loads(self):
        """School list should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "schools/school_list.html")

    def test_school_detail_loads(self):
        """School detail should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:detail", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "schools/school_detail.html")

    def test_school_create_loads(self):
        """School create form should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "schools/school_form.html")

    def test_school_update_loads(self):
        """School update form should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:update", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "schools/school_form.html")


class PersonViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        self.person = Person.objects.create(
            school=self.school, name="Test Person", role=PersonRole.KOORDINATOR, email="test@example.com"
        )

    def test_person_create_requires_login(self):
        """Person create should redirect unauthenticated users."""
        response = self.client.get(reverse("schools:person-create", kwargs={"school_pk": self.school.pk}))
        self.assertEqual(response.status_code, 302)

    def test_person_create_loads(self):
        """Person create form should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:person-create", kwargs={"school_pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "schools/person_form.html")

    def test_person_create_post(self):
        """Person can be created via POST."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("schools:person-create", kwargs={"school_pk": self.school.pk}),
            {
                "name": "New Person",
                "role": PersonRole.KOORDINATOR,
                "email": "new@example.com",
                "phone": "87654321",
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.assertTrue(Person.objects.filter(name="New Person").exists())

    def test_person_update_loads(self):
        """Person update form should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:person-update", kwargs={"pk": self.person.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "schools/person_form.html")

    def test_person_update_post(self):
        """Person can be updated via POST."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("schools:person-update", kwargs={"pk": self.person.pk}),
            {
                "name": "Updated Name",
                "role": PersonRole.KOORDINATOR,
                "email": "updated@example.com",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.person.refresh_from_db()
        self.assertEqual(self.person.name, "Updated Name")

    def test_person_delete_modal_loads(self):
        """Person delete modal should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:person-delete", kwargs={"pk": self.person.pk}))
        self.assertEqual(response.status_code, 200)

    def test_person_delete_post(self):
        """Person can be deleted via POST."""
        self.client.login(username="testuser", password="testpass123")
        person_pk = self.person.pk
        response = self.client.post(reverse("schools:person-delete", kwargs={"pk": person_pk}))
        self.assertEqual(response.status_code, 200)  # JSON response
        self.assertFalse(Person.objects.filter(pk=person_pk).exists())


class SchoolCommentViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        self.comment = SchoolComment.objects.create(school=self.school, comment="Test comment", created_by=self.user)

    def test_comment_create_requires_login(self):
        """Comment create should redirect unauthenticated users."""
        response = self.client.get(reverse("schools:comment-create", kwargs={"school_pk": self.school.pk}))
        self.assertEqual(response.status_code, 302)

    def test_comment_create_loads(self):
        """Comment create form should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:comment-create", kwargs={"school_pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "schools/comment_form.html")

    def test_comment_create_post(self):
        """Comment can be created via POST."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("schools:comment-create", kwargs={"school_pk": self.school.pk}), {"comment": "New comment text"}
        )
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.assertTrue(SchoolComment.objects.filter(comment="New comment text").exists())
        new_comment = SchoolComment.objects.get(comment="New comment text")
        self.assertEqual(new_comment.created_by, self.user)

    def test_comment_delete_modal_loads(self):
        """Comment delete modal should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:comment-delete", kwargs={"pk": self.comment.pk}))
        self.assertEqual(response.status_code, 200)

    def test_comment_delete_post(self):
        """Comment can be deleted via POST."""
        self.client.login(username="testuser", password="testpass123")
        comment_pk = self.comment.pk
        response = self.client.post(reverse("schools:comment-delete", kwargs={"pk": comment_pk}))
        self.assertEqual(response.status_code, 200)  # JSON response
        self.assertFalse(SchoolComment.objects.filter(pk=comment_pk).exists())


class SeatPurchaseModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School", adresse="Test Address", kommune="Test Kommune", enrolled_at=date.today()
        )

    def test_create_seat_purchase(self):
        """SeatPurchase model can be created and saved."""
        purchase = SeatPurchase.objects.create(
            school=self.school, seats=5, purchased_at=date.today(), notes="Test purchase"
        )
        self.assertEqual(purchase.seats, 5)
        self.assertEqual(purchase.school, self.school)

    def test_purchased_seats_aggregation(self):
        """School.purchased_seats aggregates all seat purchases."""
        SeatPurchase.objects.create(school=self.school, seats=3)
        SeatPurchase.objects.create(school=self.school, seats=2)
        self.assertEqual(self.school.purchased_seats, 5)

    def test_total_seats_calculation(self):
        """School.total_seats includes base + forankring + purchased."""
        SeatPurchase.objects.create(school=self.school, seats=5)
        expected = School.BASE_SEATS + 0 + 5  # No forankring (not 1 year old)
        self.assertEqual(self.school.total_seats, expected)

    def test_remaining_seats_calculation(self):
        """School.remaining_seats is total minus used."""
        SeatPurchase.objects.create(school=self.school, seats=5)
        # No signups, so remaining = total
        self.assertEqual(self.school.remaining_seats, self.school.total_seats)

    def test_has_available_seats(self):
        """School.has_available_seats returns True when seats available."""
        self.assertTrue(self.school.has_available_seats)

    def test_seat_purchase_ordering(self):
        """SeatPurchases are ordered by purchased_at descending."""
        purchase1 = SeatPurchase.objects.create(
            school=self.school, seats=1, purchased_at=date.today() - timedelta(days=10)
        )
        purchase2 = SeatPurchase.objects.create(school=self.school, seats=2, purchased_at=date.today())
        purchases = list(self.school.seat_purchases.all())
        self.assertEqual(purchases[0], purchase2)  # Most recent first
        self.assertEqual(purchases[1], purchase1)


class SchoolDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )

    def test_delete_requires_login(self):
        """School delete should redirect unauthenticated users."""
        response = self.client.get(reverse("schools:delete", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 302)

    def test_delete_modal_loads(self):
        """School delete modal should load for staff users."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:delete", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)

    def test_delete_post_soft_deletes(self):
        """School delete POST soft deletes the school."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("schools:delete", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)  # JSON response
        self.school.refresh_from_db()
        self.assertFalse(self.school.is_active)


class SchoolHardDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="harddeluser", password="testpass123", is_staff=True)
        self.school = School.objects.create(
            name="School To Delete",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
        )

    def test_hard_delete_modal_shows_counts(self):
        """Hard delete modal shows related data counts."""
        from apps.courses.models import Course, CourseSignUp, Location

        # Add some related data
        Person.objects.create(school=self.school, name="Test Person", email="test@example.com")
        location = Location.objects.create(name="Test Location")
        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
            location=location,
            is_published=True,
        )
        CourseSignUp.objects.create(
            course=course,
            school=self.school,
            participant_name="Test",
            participant_email="test@example.com",
        )

        self.client.login(username="harddeluser", password="testpass123")
        response = self.client.get(reverse("schools:hard-delete", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1 kursustilmelding")
        self.assertContains(response, "1 person")

    def test_hard_delete_removes_school_and_signups(self):
        """Hard delete permanently removes school and course signups."""
        from apps.courses.models import Course, CourseSignUp, Location

        location = Location.objects.create(name="Test Location")
        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
            location=location,
            is_published=True,
        )
        CourseSignUp.objects.create(
            course=course,
            school=self.school,
            participant_name="Test",
            participant_email="test@example.com",
        )

        self.client.login(username="harddeluser", password="testpass123")
        response = self.client.post(reverse("schools:hard-delete", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)

        # School should be completely gone
        self.assertFalse(School.objects.filter(pk=self.school.pk).exists())
        # Course signup should be gone too
        self.assertEqual(CourseSignUp.objects.filter(school=self.school).count(), 0)


class SchoolSearchViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_staff=True)
        self.school1 = School.objects.create(
            name="Alpha School",
            adresse="Testvej 1",
            kommune="København",
        )
        self.school2 = School.objects.create(
            name="Beta School",
            adresse="Testvej 2",
            kommune="Aarhus",
        )
        # Add person to school1
        Person.objects.create(
            school=self.school1, name="John Doe", email="john@example.com", role=PersonRole.KOORDINATOR
        )

    def test_search_by_school_name(self):
        """Search finds schools by name."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:list"), {"search": "Alpha"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpha School")
        self.assertNotContains(response, "Beta School")

    def test_search_by_kommune(self):
        """Search finds schools by kommune."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:list"), {"search": "København"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpha School")
        self.assertNotContains(response, "Beta School")

    def test_search_by_adresse(self):
        """Search finds schools by adresse."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:list"), {"search": "Testvej 1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpha School")
        self.assertNotContains(response, "Beta School")

    def test_search_by_person_name(self):
        """Search finds schools by person name."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:list"), {"search": "John"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpha School")
        self.assertNotContains(response, "Beta School")

    def test_search_by_person_email(self):
        """Search finds schools by person email."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:list"), {"search": "john@example"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpha School")
        self.assertNotContains(response, "Beta School")

    def test_search_no_results(self):
        """Search with no matches shows empty state."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:list"), {"search": "Nonexistent"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Alpha School")
        self.assertNotContains(response, "Beta School")


class FormValidationTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )

    def test_school_form_valid(self):
        """SchoolForm accepts valid data."""
        from .forms import SchoolForm

        form = SchoolForm(
            data={
                "name": "New School",
                "adresse": "New Address",
                "kommune": "Københavns Kommune",
            }
        )
        self.assertTrue(form.is_valid())

    def test_school_form_valid_without_adresse(self):
        """SchoolForm accepts data without address (optional field)."""
        from .forms import SchoolForm

        form = SchoolForm(
            data={
                "name": "New School",
                "kommune": "Københavns Kommune",
            }
        )
        self.assertTrue(form.is_valid())

    def test_school_form_requires_name(self):
        """SchoolForm requires name field."""
        from .forms import SchoolForm

        form = SchoolForm(
            data={
                "adresse": "Address",
                "kommune": "Københavns Kommune",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_school_form_requires_kommune(self):
        """SchoolForm requires kommune field."""
        from .forms import SchoolForm

        form = SchoolForm(
            data={
                "name": "School Name",
                "adresse": "Address",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("kommune", form.errors)

    def test_school_form_rejects_invalid_kommune(self):
        """SchoolForm rejects kommune values not in the dropdown."""
        from .forms import SchoolForm

        form = SchoolForm(
            data={
                "name": "New School",
                "kommune": "Invalid Kommune",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("kommune", form.errors)

    def test_person_form_valid(self):
        """PersonForm accepts valid data."""
        from .forms import PersonForm

        form = PersonForm(
            data={
                "name": "Test Person",
                "role": PersonRole.KOORDINATOR,
            }
        )
        self.assertTrue(form.is_valid())

    def test_person_form_requires_name(self):
        """PersonForm requires name field."""
        from .forms import PersonForm

        form = PersonForm(
            data={
                "role": PersonRole.KOORDINATOR,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_person_form_with_other_role(self):
        """PersonForm accepts ANDET role with role_other."""
        from .forms import PersonForm

        form = PersonForm(
            data={
                "name": "Test Person",
                "role": PersonRole.ANDET,
                "role_other": "Custom Role",
            }
        )
        self.assertTrue(form.is_valid())

    def test_person_form_validates_email(self):
        """PersonForm validates email format."""
        from .forms import PersonForm

        form = PersonForm(
            data={
                "name": "Test Person",
                "role": PersonRole.KOORDINATOR,
                "email": "invalid-email",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_comment_form_valid(self):
        """SchoolCommentForm accepts valid data."""
        from .forms import SchoolCommentForm

        form = SchoolCommentForm(
            data={
                "comment": "This is a test comment",
            }
        )
        self.assertTrue(form.is_valid())

    def test_comment_form_requires_comment(self):
        """SchoolCommentForm requires comment field."""
        from .forms import SchoolCommentForm

        form = SchoolCommentForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("comment", form.errors)


class PasswordGenerationTest(TestCase):
    def test_generate_pronounceable_password_format(self):
        """Pronounceable password has format like 'babe.dula.kibe.popy'."""
        from apps.schools.utils import generate_pronounceable_password

        password = generate_pronounceable_password(segments=4)
        # 4 segments of 4 chars + 3 dots = 19 chars
        self.assertEqual(len(password), 19)
        # Should have 3 dots
        self.assertEqual(password.count("."), 3)
        # Each segment should be 4 chars
        segments = password.split(".")
        self.assertEqual(len(segments), 4)
        for segment in segments:
            self.assertEqual(len(segment), 4)

    def test_generate_pronounceable_password_pattern(self):
        """Each segment alternates consonants and vowels."""
        from apps.schools.utils import generate_pronounceable_password

        password = generate_pronounceable_password(segments=4)
        consonants = "bdfgklmnprstvz"
        vowels = "aeiou"
        for segment in password.split("."):
            for i, char in enumerate(segment):
                if i % 2 == 0:
                    self.assertIn(char, consonants)
                else:
                    self.assertIn(char, vowels)

    def test_generate_token_length(self):
        """Token has correct length."""
        from apps.schools.utils import generate_signup_token

        token = generate_signup_token()
        self.assertEqual(len(token), 32)

    def test_generate_token_alphanumeric(self):
        """Token contains only alphanumeric characters."""
        from apps.schools.utils import generate_signup_token

        token = generate_signup_token()
        self.assertTrue(token.isalnum())


class SchoolCredentialsTest(TestCase):
    def test_school_has_signup_password_field(self):
        """School model has signup_password field."""
        school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        self.assertEqual(school.signup_password, "")

    def test_school_has_signup_token_field(self):
        """School model has signup_token field."""
        school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        self.assertEqual(school.signup_token, "")

    def test_generate_credentials(self):
        """School.generate_credentials() creates password and token."""
        school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        school.generate_credentials()
        self.assertEqual(len(school.signup_password), 19)
        self.assertEqual(len(school.signup_token), 32)

    def test_generate_credentials_saves(self):
        """School.generate_credentials() saves to database."""
        school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        school.generate_credentials()
        school.refresh_from_db()
        self.assertEqual(len(school.signup_password), 19)
        self.assertEqual(len(school.signup_token), 32)


class SchoolCredentialsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="credsuser", password="testpass123", is_staff=True)
        self.school = School.objects.create(
            name="Credentials Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
            signup_password="bafimoku",
            signup_token="abc123token",
        )

    def test_detail_shows_credentials_for_enrolled(self):
        """School detail shows credentials section for enrolled schools."""
        self.client.login(username="credsuser", password="testpass123")
        response = self.client.get(reverse("schools:detail", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kodeord og tilmeldingslink")
        self.assertContains(response, "bafimoku")

    def test_detail_hides_credentials_for_unenrolled(self):
        """School detail hides credentials for unenrolled schools."""
        self.school.enrolled_at = None
        self.school.save()
        self.client.login(username="credsuser", password="testpass123")
        response = self.client.get(reverse("schools:detail", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Kodeord og tilmeldingslink")

    def test_regenerate_credentials(self):
        """Regenerate credentials creates new password and token."""
        self.client.login(username="credsuser", password="testpass123")
        old_password = self.school.signup_password
        old_token = self.school.signup_token

        response = self.client.post(reverse("schools:regenerate-credentials", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)

        self.school.refresh_from_db()
        self.assertNotEqual(self.school.signup_password, old_password)
        self.assertNotEqual(self.school.signup_token, old_token)


class SchoolPublicViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today() - timedelta(days=400),
            signup_token="abc123def456ghi789",
        )

    def test_public_view_with_valid_token(self):
        """Public view loads with valid token."""
        response = self.client.get(f"/school/{self.school.signup_token}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test School")

    def test_public_view_with_invalid_token(self):
        """Public view returns 404 with invalid token."""
        response = self.client.get("/school/invalidtoken123/")
        self.assertEqual(response.status_code, 404)

    def test_public_view_shows_seat_info(self):
        """Public view shows seat information."""
        response = self.client.get(f"/school/{self.school.signup_token}/")
        self.assertContains(response, "Pladser")

    def test_public_view_shows_people(self):
        """Public view shows people from school."""
        Person.objects.create(
            school=self.school,
            name="John Doe",
            role=PersonRole.KOORDINATOR,
            email="john@test.com",
        )
        response = self.client.get(f"/school/{self.school.signup_token}/")
        self.assertContains(response, "John Doe")

    def test_public_view_shows_signups(self):
        """Public view shows course signups."""
        from apps.courses.models import Course, CourseSignUp, Location

        location = Location.objects.create(name="Test Location")
        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
            location=location,
            capacity=10,
        )
        CourseSignUp.objects.create(
            school=self.school,
            course=course,
            participant_name="Jane Smith",
            participant_title="Laerer",
        )
        response = self.client.get(f"/school/{self.school.signup_token}/")
        self.assertContains(response, "Jane Smith")

    def test_public_view_no_edit_buttons(self):
        """Public view does not show edit buttons."""
        Person.objects.create(school=self.school, name="John", role=PersonRole.KOORDINATOR)
        response = self.client.get(f"/school/{self.school.signup_token}/")
        self.assertNotContains(response, "Rediger")
        self.assertNotContains(response, "bi-pencil")


class SchoolDetailMergedPeopleTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
        )

    def test_detail_shows_people_and_signups_together(self):
        """School detail shows people and signups in same section."""
        from apps.courses.models import Course, CourseSignUp, Location

        Person.objects.create(school=self.school, name="Contact Person", role=PersonRole.KOORDINATOR)
        location = Location.objects.create(name="Test Location")
        course = Course.objects.create(start_date=date.today(), end_date=date.today(), location=location, capacity=10)
        CourseSignUp.objects.create(
            school=self.school, course=course, participant_name="Signup Person", participant_title="Laerer"
        )

        response = self.client.get(reverse("schools:detail", args=[self.school.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contact Person")
        self.assertContains(response, "Signup Person")
        # Verify both names appear on page
        content = response.content.decode()
        self.assertIn("Contact Person", content)
        self.assertIn("Signup Person", content)

    def test_signups_show_course_link(self):
        """Signups show link to course."""
        from apps.courses.models import Course, CourseSignUp, Location

        location = Location.objects.create(name="Test Location")
        course = Course.objects.create(start_date=date.today(), end_date=date.today(), location=location, capacity=10)
        CourseSignUp.objects.create(
            school=self.school, course=course, participant_name="Signup Person", participant_title="Laerer"
        )

        response = self.client.get(reverse("schools:detail", args=[self.school.pk]))
        self.assertContains(response, f'href="{reverse("courses:detail", args=[course.pk])}"')


class InvoiceModelTest(TestCase):
    """Tests for the Invoice model."""

    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="København",
            enrolled_at=date(2024, 9, 1),
        )
        self.school_year, _ = SchoolYear.objects.get_or_create(
            name="2024/25",
            defaults={"start_date": date(2024, 8, 1), "end_date": date(2025, 7, 31)},
        )

    def test_create_invoice(self):
        """Invoice can be created with required fields."""
        from .models import Invoice

        invoice = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=10000.00,
            date=date.today(),
        )
        self.assertEqual(invoice.invoice_number, "INV-001")
        self.assertEqual(invoice.amount, 10000.00)
        self.assertEqual(invoice.school, self.school)

    def test_invoice_str(self):
        """Invoice __str__ returns invoice number and school name."""
        from .models import Invoice

        invoice = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=5000.00,
        )
        self.assertEqual(str(invoice), "INV-001 - Test School")

    def test_invoice_default_status(self):
        """Invoice defaults to 'planned' status."""
        from .models import Invoice, InvoiceStatus

        invoice = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=5000.00,
        )
        self.assertEqual(invoice.status, InvoiceStatus.PLANNED)

    def test_invoice_status_choices(self):
        """Invoice can have different status values."""
        from .models import Invoice, InvoiceStatus

        invoice = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=5000.00,
        )
        # Test each status
        for status in [InvoiceStatus.PLANNED, InvoiceStatus.SENT, InvoiceStatus.PAID]:
            invoice.status = status
            invoice.save()
            invoice.refresh_from_db()
            self.assertEqual(invoice.status, status)

    def test_invoice_school_year_fk(self):
        """Invoice can be associated with a school year."""
        from .models import Invoice

        invoice = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=10000.00,
            school_year=self.school_year,
        )

        self.assertEqual(invoice.school_year, self.school_year)

    def test_invoice_school_year_blank(self):
        """Invoice can have no school year (blank=True)."""
        from .models import Invoice

        invoice = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=5000.00,
        )
        self.assertIsNone(invoice.school_year)

    def test_invoice_ordering(self):
        """Invoices are ordered by date descending."""
        from .models import Invoice

        inv1 = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=1000.00,
            date=date(2024, 1, 1),
        )
        inv2 = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-002",
            amount=2000.00,
            date=date(2024, 6, 1),
        )
        inv3 = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-003",
            amount=3000.00,
            date=date(2024, 3, 1),
        )

        invoices = list(Invoice.objects.all())
        # Most recent date first
        self.assertEqual(invoices[0], inv2)  # June
        self.assertEqual(invoices[1], inv3)  # March
        self.assertEqual(invoices[2], inv1)  # January

    def test_invoice_cascade_delete(self):
        """Hard deleting school deletes its invoices."""
        from .models import Invoice

        invoice = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-CASCADE-001",
            amount=5000.00,
        )
        self.assertTrue(Invoice.objects.filter(pk=invoice.pk).exists())

        # Hard delete bypasses soft delete by using queryset delete
        School.objects.filter(pk=self.school.pk).delete()
        self.assertFalse(Invoice.objects.filter(pk=invoice.pk).exists())

    def test_invoice_related_name(self):
        """School.invoices returns related invoices."""
        from .models import Invoice

        inv1 = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=1000.00,
        )
        inv2 = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-002",
            amount=2000.00,
        )

        self.assertEqual(self.school.invoices.count(), 2)
        self.assertIn(inv1, self.school.invoices.all())
        self.assertIn(inv2, self.school.invoices.all())


class InvoiceFormTest(TestCase):
    """Tests for the InvoiceForm."""

    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="København",
            enrolled_at=date(2024, 9, 1),
        )
        self.school_year, _ = SchoolYear.objects.get_or_create(
            name="2024/25",
            defaults={"start_date": date(2024, 8, 1), "end_date": date(2025, 7, 31)},
        )

    def test_form_valid(self):
        """Form is valid with required fields."""
        from .forms import InvoiceForm

        form = InvoiceForm(
            data={
                "invoice_number": "INV-001",
                "amount": "5000.00",
                "date": date.today(),
                "status": "planned",
                "school_year": self.school_year.pk,
            },
            school=self.school,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_requires_invoice_number(self):
        """Form requires invoice_number field."""
        from .forms import InvoiceForm

        form = InvoiceForm(
            data={
                "amount": "5000.00",
                "date": date.today(),
                "status": "planned",
            },
            school=self.school,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("invoice_number", form.errors)

    def test_form_requires_amount(self):
        """Form requires amount field."""
        from .forms import InvoiceForm

        form = InvoiceForm(
            data={
                "invoice_number": "INV-001",
                "date": date.today(),
                "status": "planned",
            },
            school=self.school,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_form_school_year_optional(self):
        """Form is valid without school_year (blank=True on model)."""
        from .forms import InvoiceForm

        form = InvoiceForm(
            data={
                "invoice_number": "INV-001",
                "amount": "5000.00",
                "date": date.today(),
                "status": "planned",
            },
            school=self.school,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_school_year_queryset_filtered(self):
        """Form queryset is filtered to school's enrolled years."""
        from .forms import InvoiceForm

        # Create another school year that the school wasn't enrolled in
        future_year, _ = SchoolYear.objects.get_or_create(
            name="2030/31",
            defaults={"start_date": date(2030, 8, 1), "end_date": date(2031, 7, 31)},
        )

        form = InvoiceForm(school=self.school)
        queryset = form.fields["school_year"].queryset

        # School enrolled in 2024-09-01, so 2024/25 should be included
        self.assertIn(self.school_year, queryset)
        # Future year should also be included (enrolled school covers all years from enrollment onwards)
        self.assertIn(future_year, queryset)

    def test_form_school_year_queryset_excludes_opted_out_years(self):
        """Form queryset excludes years after school opted out."""
        from .forms import InvoiceForm

        # Opt out the school before the 2024/25 year starts
        self.school.opted_out_at = date(2024, 7, 15)
        self.school.save()

        form = InvoiceForm(school=self.school)
        queryset = form.fields["school_year"].queryset

        # School opted out before 2024/25 started, so it shouldn't appear
        self.assertNotIn(self.school_year, queryset)

    def test_form_widget_is_select(self):
        """Form uses Select widget for school_year."""
        from django.forms import Select

        from .forms import InvoiceForm

        form = InvoiceForm(school=self.school)
        self.assertIsInstance(form.fields["school_year"].widget, Select)

    def test_form_duplicate_invoice_number_same_school_year_invalid(self):
        """Form rejects duplicate invoice_number + school_year combination."""
        from .forms import InvoiceForm

        # Create an existing invoice
        Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=5000,
            school_year=self.school_year,
        )

        # Try to create another invoice with same number and school year
        form = InvoiceForm(
            data={
                "invoice_number": "INV-001",
                "amount": "3000.00",
                "date": date.today(),
                "status": "planned",
                "school_year": self.school_year.pk,
            },
            school=self.school,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn("INV-001", form.errors["__all__"][0])
        self.assertIn("2024/25", form.errors["__all__"][0])

    def test_form_duplicate_invoice_number_different_school_year_valid(self):
        """Form allows same invoice_number if school_year is different."""
        from .forms import InvoiceForm

        # Create a second school year
        other_year, _ = SchoolYear.objects.get_or_create(
            name="2023/24",
            defaults={"start_date": date(2023, 8, 1), "end_date": date(2024, 7, 31)},
        )
        # Adjust school enrollment to include the other year
        self.school.enrolled_at = date(2023, 9, 1)
        self.school.save()

        # Create an existing invoice
        Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=5000,
            school_year=self.school_year,
        )

        # Create invoice with same number but different school year
        form = InvoiceForm(
            data={
                "invoice_number": "INV-001",
                "amount": "3000.00",
                "date": date.today(),
                "status": "planned",
                "school_year": other_year.pk,
            },
            school=self.school,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_duplicate_invoice_number_no_school_year_valid(self):
        """Form allows duplicate invoice_number if school_year is null."""
        from .forms import InvoiceForm

        # Create an existing invoice with school year
        Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=5000,
            school_year=self.school_year,
        )

        # Create invoice with same number but no school year
        form = InvoiceForm(
            data={
                "invoice_number": "INV-001",
                "amount": "3000.00",
                "date": date.today(),
                "status": "planned",
            },
            school=self.school,
        )
        self.assertTrue(form.is_valid(), form.errors)


class InvoiceViewTest(TestCase):
    """Tests for Invoice CRUD views."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass", is_staff=True)
        self.client = Client()
        self.client.login(username="testuser", password="testpass")
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="København",
            enrolled_at=date(2024, 9, 1),
        )
        self.school_year, _ = SchoolYear.objects.get_or_create(
            name="2024/25",
            defaults={"start_date": date(2024, 8, 1), "end_date": date(2025, 7, 31)},
        )

    def test_invoice_create_requires_login(self):
        """Invoice create view requires authentication."""
        self.client.logout()
        url = reverse("schools:invoice-create", args=[self.school.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_invoice_create_loads(self):
        """Invoice create form loads successfully."""
        url = reverse("schools:invoice-create", args=[self.school.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tilføj faktura")
        self.assertContains(response, self.school.name)

    def test_invoice_create_post(self):
        """Invoice can be created via POST."""
        from .models import Invoice

        url = reverse("schools:invoice-create", args=[self.school.pk])
        response = self.client.post(
            url,
            {
                "invoice_number": "INV-001",
                "amount": "5000.00",
                "date": date.today(),
                "status": "planned",
                "school_year": self.school_year.pk,
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirect on success

        # Verify invoice was created
        invoice = Invoice.objects.get(invoice_number="INV-001")
        self.assertEqual(invoice.school, self.school)
        self.assertEqual(invoice.amount, 5000.00)
        self.assertEqual(invoice.school_year, self.school_year)

    def test_invoice_create_invalid_post(self):
        """Invoice create with invalid data shows form again."""
        url = reverse("schools:invoice-create", args=[self.school.pk])
        response = self.client.post(
            url,
            {
                "invoice_number": "",  # Required field empty
                "amount": "5000.00",
                "date": date.today(),
                "status": "planned",
            },
        )
        self.assertEqual(response.status_code, 200)  # Form re-rendered
        self.assertContains(response, "Tilføj faktura")

    def test_invoice_delete_modal_loads(self):
        """Invoice delete modal loads successfully."""
        from .models import Invoice

        invoice = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=5000.00,
        )
        url = reverse("schools:invoice-delete", args=[invoice.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Slet")

    def test_invoice_delete_post(self):
        """Invoice can be deleted via POST."""
        from .models import Invoice

        invoice = Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=5000.00,
        )
        url = reverse("schools:invoice-delete", args=[invoice.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)  # Returns JSON
        self.assertEqual(Invoice.objects.count(), 0)

    def test_invoice_displayed_on_school_detail(self):
        """Invoice is displayed on school detail page."""
        from .models import Invoice

        Invoice.objects.create(
            school=self.school,
            invoice_number="INV-001",
            amount=5000.00,
            school_year=self.school_year,
        )

        url = reverse("schools:detail", args=[self.school.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "INV-001")
        self.assertContains(response, "5000")


class MissingInvoicesViewTest(TestCase):
    """Tests for the MissingInvoicesView."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass", is_staff=True)
        self.client = Client()
        self.client.login(username="testuser", password="testpass")

        # Clear all school years to have a controlled test environment
        SchoolYear.objects.all().delete()

        self.school_year = SchoolYear.objects.create(
            name="2024/25",
            start_date=date(2024, 8, 1),
            end_date=date(2025, 7, 31),
        )

    def test_missing_invoices_requires_login(self):
        """Missing invoices view requires authentication."""
        self.client.logout()
        url = reverse("schools:missing-invoices")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_missing_invoices_loads(self):
        """Missing invoices view loads successfully."""
        url = reverse("schools:missing-invoices")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_missing_invoices_shows_forankring_school_without_invoice(self):
        """Forankring schools (enrolled before year) without invoice appear in list."""
        School.objects.create(
            name="Forankring School",
            adresse="Test Address",
            kommune="København",
            enrolled_at=date(2023, 9, 1),  # Enrolled before 2024/25 = forankring
        )

        url = reverse("schools:missing-invoices")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Forankring School")
        self.assertContains(response, "2024/25")

    def test_missing_invoices_excludes_new_school_without_invoice(self):
        """New schools (enrolled during year) without invoice don't appear (unless exceeding seats)."""
        School.objects.create(
            name="New School",
            adresse="Test Address",
            kommune="København",
            enrolled_at=date(2024, 9, 1),  # Enrolled during 2024/25 = new
        )

        url = reverse("schools:missing-invoices")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # New schools don't need invoice in first year
        self.assertNotContains(response, "New School")

    def test_missing_invoices_excludes_forankring_school_with_invoice(self):
        """Forankring schools with invoice for a year don't appear in missing list."""

        school = School.objects.create(
            name="School With Invoice",
            adresse="Test Address",
            kommune="København",
            enrolled_at=date(2023, 9, 1),  # Forankring
        )
        Invoice.objects.create(
            school=school,
            invoice_number="INV-001",
            amount=5000.00,
            school_year=self.school_year,
        )

        url = reverse("schools:missing-invoices")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # School should not appear since it has an invoice for 2024/25
        self.assertNotContains(response, "School With Invoice")

    def test_missing_invoices_excludes_schools_opted_out_before_year(self):
        """Schools that opted out before a school year started don't appear for that year."""
        # School enrolled in 2023 and opted out before 2024/25 school year started (Aug 1, 2024)
        School.objects.create(
            name="Opted Out Early School",
            adresse="Test Address",
            kommune="København",
            enrolled_at=date(2023, 9, 1),
            opted_out_at=date(2024, 6, 1),  # Opted out before 2024/25 started
        )

        url = reverse("schools:missing-invoices")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # School should not appear for 2024/25 since it opted out before that year started
        self.assertNotContains(response, "Opted Out Early School")

    def test_missing_invoices_multiple_years(self):
        """Missing invoices shows schools missing invoices across multiple years."""
        from .models import Invoice

        school_year_2, _ = SchoolYear.objects.get_or_create(
            name="2025/26",
            defaults={"start_date": date(2025, 8, 1), "end_date": date(2026, 7, 31)},
        )

        school = School.objects.create(
            name="Multi Year School",
            adresse="Test Address",
            kommune="København",
            enrolled_at=date(2024, 9, 1),
        )
        # Add invoice for 2024/25 only
        Invoice.objects.create(
            school=school,
            invoice_number="INV-001",
            amount=5000.00,
            school_year=self.school_year,
        )

        url = reverse("schools:missing-invoices")
        response = self.client.get(url)

        # School should appear for 2025/26 (missing invoice) but not 2024/25
        content = response.content.decode()
        # Check that the school appears with the missing year
        self.assertIn("Multi Year School", content)
        self.assertIn("2025/26", content)


class SchoolFormExtendedFieldsTest(TestCase):
    def test_school_form_includes_new_fields(self):
        """SchoolForm includes postnummer, by, and ean_nummer fields."""
        from .forms import SchoolForm

        form = SchoolForm()
        self.assertIn("postnummer", form.fields)
        self.assertIn("by", form.fields)
        self.assertIn("ean_nummer", form.fields)

    def test_school_form_saves_new_fields(self):
        """SchoolForm saves postnummer, by, and ean_nummer."""
        from .forms import SchoolForm

        form = SchoolForm(
            data={
                "name": "Test School",
                "adresse": "Testvej 1",
                "kommune": "Københavns Kommune",
                "postnummer": "2100",
                "by": "København Ø",
                "ean_nummer": "5790001234567",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        school = form.save()
        self.assertEqual(school.postnummer, "2100")
        self.assertEqual(school.by, "København Ø")
        self.assertEqual(school.ean_nummer, "5790001234567")


class PersonExtendedFieldsTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )

    def test_person_has_titel_field(self):
        """Person model has titel field with choices."""
        person = Person.objects.create(
            school=self.school,
            name="Test Person",
            role=PersonRole.KOORDINATOR,
            titel=TitelChoice.SKOLELEDER,
        )
        self.assertEqual(person.titel, TitelChoice.SKOLELEDER)
        self.assertEqual(person.display_titel, "Skoleleder")

    def test_person_titel_other(self):
        """Person titel_other works when titel is ANDET."""
        person = Person.objects.create(
            school=self.school,
            name="Test Person",
            role=PersonRole.KOORDINATOR,
            titel=TitelChoice.ANDET,
            titel_other="Speciallærer",
        )
        self.assertEqual(person.display_titel, "Speciallærer")

    def test_person_role_oekonomisk_ansvarlig(self):
        """Person can have OEKONOMISK_ANSVARLIG role."""
        person = Person.objects.create(
            school=self.school,
            name="Test Person",
            role=PersonRole.OEKONOMISK_ANSVARLIG,
        )
        self.assertEqual(person.role, PersonRole.OEKONOMISK_ANSVARLIG)
        self.assertEqual(person.get_role_display(), "Økonomisk ansvarlig")

    def test_person_role_andet(self):
        """Person role ANDET uses role_other."""
        person = Person.objects.create(
            school=self.school,
            name="Test Person",
            role=PersonRole.ANDET,
            role_other="Custom Role",
        )
        self.assertEqual(person.display_role, "Custom Role")


class PersonFormExtendedFieldsTest(TestCase):
    def test_person_form_includes_titel_fields(self):
        """PersonForm includes titel and titel_other fields."""
        from .forms import PersonForm

        form = PersonForm()
        self.assertIn("titel", form.fields)
        self.assertIn("titel_other", form.fields)

    def test_person_form_saves_titel(self):
        """PersonForm saves titel field."""
        from .forms import PersonForm

        school = School.objects.create(name="Test", adresse="Test", kommune="Test")
        form = PersonForm(
            data={
                "name": "Test Person",
                "role": PersonRole.KOORDINATOR,
                "titel": TitelChoice.SKOLELEDER,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        person = form.save(commit=False)
        person.school = school
        person.save()
        self.assertEqual(person.titel, TitelChoice.SKOLELEDER)


class SchoolDetailExtendedFieldsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="detailuser", password="testpass123", is_staff=True)
        self.school = School.objects.create(
            name="Test School",
            adresse="Testvej 1",
            kommune="København",
            postnummer="2100",
            by="København Ø",
            ean_nummer="5790001234567",
        )

    def test_detail_shows_postnummer_and_by(self):
        """School detail shows postnummer and by."""
        self.client.login(username="detailuser", password="testpass123")
        response = self.client.get(reverse("schools:detail", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2100")
        self.assertContains(response, "København Ø")

    def test_detail_shows_ean_nummer(self):
        """School detail shows EAN-nummer."""
        self.client.login(username="detailuser", password="testpass123")
        response = self.client.get(reverse("schools:detail", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "5790001234567")


class PersonDetailTitelTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="personuser", password="testpass123", is_staff=True)
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="København",
        )
        self.person = Person.objects.create(
            school=self.school,
            name="Test Person",
            role=PersonRole.KOORDINATOR,
            titel=TitelChoice.SKOLELEDER,
        )

    def test_detail_shows_person_titel(self):
        """School detail shows person titel."""
        self.client.login(username="personuser", password="testpass123")
        response = self.client.get(reverse("schools:detail", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "skoleleder")  # lowercase due to |lower filter


class SchoolBillingFieldsTest(TestCase):
    def test_school_has_billing_fields(self):
        """School model has billing fields for municipality billing."""
        school = School.objects.create(
            name="Test School",
            adresse="Testvej 1",
            kommune="København",
            kommunen_betaler=True,
            fakturering_adresse="Rådhuspladsen 1",
            fakturering_postnummer="1550",
            fakturering_by="København V",
            fakturering_ean_nummer="5790000000001",
            fakturering_kontakt_navn="Kommune Kontakt",
            fakturering_kontakt_email="faktura@kommune.dk",
        )
        self.assertTrue(school.kommunen_betaler)
        self.assertEqual(school.fakturering_adresse, "Rådhuspladsen 1")
        self.assertEqual(school.fakturering_postnummer, "1550")
        self.assertEqual(school.fakturering_by, "København V")
        self.assertEqual(school.fakturering_ean_nummer, "5790000000001")
        self.assertEqual(school.fakturering_kontakt_navn, "Kommune Kontakt")
        self.assertEqual(school.fakturering_kontakt_email, "faktura@kommune.dk")

    def test_school_billing_fields_optional(self):
        """Billing fields are optional."""
        school = School.objects.create(
            name="Test School",
            adresse="Testvej 1",
            kommune="København",
        )
        self.assertFalse(school.kommunen_betaler)
        self.assertEqual(school.fakturering_adresse, "")


class SchoolFormBillingFieldsTest(TestCase):
    def test_school_form_includes_billing_fields(self):
        """SchoolForm includes billing fields."""
        from .forms import SchoolForm

        form = SchoolForm()
        self.assertIn("kommunen_betaler", form.fields)
        self.assertIn("fakturering_adresse", form.fields)
        self.assertIn("fakturering_ean_nummer", form.fields)

    def test_school_form_saves_billing_fields(self):
        """SchoolForm saves billing fields."""
        from .forms import SchoolForm

        form = SchoolForm(
            data={
                "name": "Test School",
                "kommune": "Københavns Kommune",
                "kommunen_betaler": True,
                "fakturering_adresse": "Rådhuspladsen 1",
                "fakturering_postnummer": "1550",
                "fakturering_by": "København V",
                "fakturering_ean_nummer": "5790000000001",
                "fakturering_kontakt_navn": "Kommune Kontakt",
                "fakturering_kontakt_email": "faktura@kommune.dk",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        school = form.save()
        self.assertTrue(school.kommunen_betaler)
        self.assertEqual(school.fakturering_adresse, "Rådhuspladsen 1")


class SchoolFileModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_create_school_file(self):
        """SchoolFile model can be created and saved."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.schools.models import SchoolFile

        file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        school_file = SchoolFile.objects.create(
            school=self.school,
            file=file,
            description="Test description",
            uploaded_by=self.user,
        )
        self.assertEqual(school_file.school, self.school)
        self.assertEqual(school_file.description, "Test description")
        self.assertEqual(school_file.uploaded_by, self.user)
        self.assertIsNotNone(school_file.uploaded_at)

    def test_school_file_ordering(self):
        """SchoolFiles are ordered by uploaded_at descending."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.schools.models import SchoolFile

        file1 = SimpleUploadedFile("test1.pdf", b"content1")
        file2 = SimpleUploadedFile("test2.pdf", b"content2")
        sf1 = SchoolFile.objects.create(school=self.school, file=file1)
        sf2 = SchoolFile.objects.create(school=self.school, file=file2)
        files = list(self.school.files.all())
        self.assertEqual(files[0], sf2)  # Most recent first
        self.assertEqual(files[1], sf1)

    def test_school_file_filename_property(self):
        """SchoolFile.filename returns just the filename."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.schools.models import SchoolFile

        file = SimpleUploadedFile("my_document.pdf", b"content")
        sf = SchoolFile.objects.create(school=self.school, file=file)
        # Django may add a random suffix to avoid collisions (e.g., my_document_abc123.pdf)
        self.assertTrue(sf.filename.startswith("my_document"))
        self.assertTrue(sf.filename.endswith(".pdf"))


class SchoolFileFormTest(TestCase):
    def test_school_file_form_valid(self):
        """SchoolFileForm accepts valid data."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.schools.forms import SchoolFileForm

        file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        form = SchoolFileForm(data={"description": "Test"}, files={"file": file})
        self.assertTrue(form.is_valid(), form.errors)

    def test_school_file_form_requires_file(self):
        """SchoolFileForm requires file field."""
        from apps.schools.forms import SchoolFileForm

        form = SchoolFileForm(data={"description": "Test"})
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)

    def test_school_file_form_description_optional(self):
        """SchoolFileForm description is optional."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.schools.forms import SchoolFileForm

        file = SimpleUploadedFile("test.pdf", b"content")
        form = SchoolFileForm(data={}, files={"file": file})
        self.assertTrue(form.is_valid(), form.errors)


class SchoolPublicViewCourseAttendanceTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today() - timedelta(days=400),
            signup_token="abc123def456ghi789",
        )
        # Create person
        self.person = Person.objects.create(
            school=self.school,
            name="John Doe",
            role=PersonRole.KOORDINATOR,
            email="john@test.com",
        )

    def test_public_view_shows_person_course_attendance(self):
        """Public view shows course attendance under person."""
        from apps.courses.models import Course, CourseSignUp, Location

        location = Location.objects.create(name="Test Location")
        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
            location=location,
            capacity=10,
        )
        # Create signup matching person email
        CourseSignUp.objects.create(
            school=self.school,
            course=course,
            participant_name="John Doe",
            participant_email="john@test.com",
            attendance="present",
        )
        response = self.client.get(f"/school/{self.school.signup_token}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Uddannet på")

    def test_public_view_shows_separate_course_participants(self):
        """Public view shows course participants not matching contacts."""
        from apps.courses.models import Course, CourseSignUp, Location

        location = Location.objects.create(name="Test Location")
        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
            location=location,
            capacity=10,
        )
        # Create signup NOT matching any person
        CourseSignUp.objects.create(
            school=self.school,
            course=course,
            participant_name="Jane Smith",
            participant_email="jane@test.com",
            attendance="unmarked",
        )
        response = self.client.get(f"/school/{self.school.signup_token}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jane Smith")
        self.assertContains(response, "Kursusdeltagere")


class SchoolFileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="fileuser", password="testpass123", is_staff=True)
        self.school = School.objects.create(
            name="File Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )

    def test_file_create_requires_login(self):
        """File create should redirect unauthenticated users."""
        response = self.client.get(reverse("schools:file-create", kwargs={"school_pk": self.school.pk}))
        self.assertEqual(response.status_code, 302)

    def test_file_create_loads(self):
        """File create form should load for staff users."""
        self.client.login(username="fileuser", password="testpass123")
        response = self.client.get(reverse("schools:file-create", kwargs={"school_pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)

    def test_file_create_post(self):
        """File can be created via POST."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.schools.models import SchoolFile

        self.client.login(username="fileuser", password="testpass123")
        file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        response = self.client.post(
            reverse("schools:file-create", kwargs={"school_pk": self.school.pk}),
            {"file": file, "description": "Test file"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SchoolFile.objects.filter(school=self.school).exists())

    def test_file_delete_post(self):
        """File can be deleted via POST."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.schools.models import SchoolFile

        self.client.login(username="fileuser", password="testpass123")
        file = SimpleUploadedFile("test.pdf", b"content")
        sf = SchoolFile.objects.create(school=self.school, file=file, uploaded_by=self.user)
        response = self.client.post(reverse("schools:file-delete", kwargs={"pk": sf.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SchoolFile.objects.filter(pk=sf.pk).exists())


class SchoolPublicViewCourseMaterialsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today() - timedelta(days=400),
            signup_token="materials123token",
        )

    def test_public_view_shows_course_materials(self):
        """Public view shows course materials section."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.courses.models import Course, CourseMaterial, CourseSignUp, Location

        location = Location.objects.create(name="Test Location")
        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
            location=location,
            capacity=10,
        )
        CourseSignUp.objects.create(
            school=self.school,
            course=course,
            participant_name="Test",
            participant_email="test@test.com",
        )
        file = SimpleUploadedFile("slides.pdf", b"content")
        CourseMaterial.objects.create(course=course, file=file, name="Kursusslides")

        response = self.client.get(f"/school/{self.school.signup_token}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kursusmaterialer")
        self.assertContains(response, "Kursusslides")

    def test_public_view_hides_materials_for_courses_without_signups(self):
        """Public view doesn't show materials for courses school didn't attend."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.courses.models import Course, CourseMaterial, Location

        location = Location.objects.create(name="Test Location")
        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
            location=location,
            capacity=10,
        )
        # No signup for this school
        file = SimpleUploadedFile("slides.pdf", b"content")
        CourseMaterial.objects.create(course=course, file=file, name="Secret Slides")

        response = self.client.get(f"/school/{self.school.signup_token}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Secret Slides")
