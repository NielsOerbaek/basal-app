from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Person, PersonRole, School, SchoolComment, SeatPurchase


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
        from apps.courses.models import Course, CourseSignUp

        school = School.objects.create(name="Test", adresse="Test", kommune="Test", enrolled_at=date.today())
        # School has 3 base seats, create 2 signups
        course = Course.objects.create(
            title="Test Course",
            start_date=date.today(),
            end_date=date.today(),
            location="Test",
            capacity=10,
        )
        CourseSignUp.objects.create(course=course, school=school, participant_name="A", participant_email="a@test.com")
        CourseSignUp.objects.create(course=course, school=school, participant_name="B", participant_email="b@test.com")
        self.assertEqual(school.used_seats, 2)
        self.assertEqual(school.total_seats, 3)
        self.assertFalse(school.exceeds_seat_allocation)

    def test_exceeds_seat_allocation_true_when_over(self):
        """exceeds_seat_allocation is True when used_seats > total_seats."""
        from apps.courses.models import Course, CourseSignUp

        school = School.objects.create(name="Test", adresse="Test", kommune="Test", enrolled_at=date.today())
        # School has 3 base seats, create 4 signups to exceed
        course = Course.objects.create(
            title="Test Course",
            start_date=date.today(),
            end_date=date.today(),
            location="Test",
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
        """display_role returns role_other for OTHER role."""
        person = Person.objects.create(school=self.school, name="Test", role=PersonRole.OTHER, role_other="Custom Role")
        self.assertEqual(person.display_role, "Custom Role")

    def test_display_role_other_empty(self):
        """display_role returns 'Andet' when OTHER role has no role_other."""
        person = Person.objects.create(school=self.school, name="Test", role=PersonRole.OTHER)
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
                "role": PersonRole.SKOLELEDER,
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
        from apps.courses.models import Course, CourseSignUp

        # Add some related data
        Person.objects.create(school=self.school, name="Test Person", email="test@example.com")
        course = Course.objects.create(
            title="Test Course",
            start_date=date.today(),
            end_date=date.today(),
            location="Test",
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
        from apps.courses.models import Course, CourseSignUp

        course = Course.objects.create(
            title="Test Course",
            start_date=date.today(),
            end_date=date.today(),
            location="Test",
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
        """PersonForm accepts OTHER role with role_other."""
        from .forms import PersonForm

        form = PersonForm(
            data={
                "name": "Test Person",
                "role": PersonRole.OTHER,
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
