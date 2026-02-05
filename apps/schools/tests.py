import re
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.courses.models import Course

from .models import Invoice, Person, School, SchoolComment, SchoolYear, TitelChoice


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


class ActiveFromFieldTest(TestCase):
    def test_school_has_active_from_field(self):
        """School model has active_from field."""
        school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today(),
            active_from=date.today(),
        )
        self.assertEqual(school.active_from, date.today())

    def test_active_from_can_be_null(self):
        """active_from can be null for non-enrolled schools."""
        school = School.objects.create(
            name="Test School",
            adresse="Test Address",
            kommune="Test Kommune",
        )
        self.assertIsNone(school.active_from)


class ActiveFromSeatsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create school year spanning current date
        today = date.today()
        # Determine if we're in first half (Aug-Dec) or second half (Jan-Jul) of school year
        if today.month >= 8:
            start_year = today.year
        else:
            start_year = today.year - 1
        cls.current_year, _ = SchoolYear.objects.get_or_create(
            name=f"{start_year}/{str(start_year + 1)[-2:]}",
            defaults={
                "start_date": date(start_year, 8, 1),
                "end_date": date(start_year + 1, 7, 31),
            },
        )

    def test_base_seats_with_active_from_in_future(self):
        """School with active_from in future still has BASE_SEATS (year-based, not date-based)."""
        school = School.objects.create(
            name="Test",
            adresse="Test",
            kommune="Test",
            enrolled_at=date.today(),
            active_from=date.today() + timedelta(days=30),
        )
        self.assertEqual(school.base_seats, School.BASE_SEATS)

    def test_base_seats_positive_when_active_from_today_or_past(self):
        """School with active_from today or in past has BASE_SEATS."""
        school = School.objects.create(
            name="Test",
            adresse="Test",
            kommune="Test",
            enrolled_at=date.today(),
            active_from=date.today(),
        )
        self.assertEqual(school.base_seats, School.BASE_SEATS)

    def test_forankring_uses_active_from_not_enrolled_at(self):
        """Forankring status uses active_from, not enrolled_at."""
        # School enrolled recently but with active_from backdated
        school = School.objects.create(
            name="Test",
            adresse="Test",
            kommune="Test",
            enrolled_at=date.today(),
            active_from=self.current_year.start_date - timedelta(days=1),
        )
        self.assertTrue(school.has_forankringsplads)


class SchoolYearEnrolledSchoolsTest(TestCase):
    def test_get_enrolled_schools_uses_active_from(self):
        """get_enrolled_schools uses active_from, not enrolled_at."""
        school_year = SchoolYear.objects.create(
            name="Test Year 2025/26",
            start_date=date(2025, 8, 1),
            end_date=date(2026, 7, 31),
        )
        # School enrolled in 2025/26 but active from 2026/27
        school = School.objects.create(
            name="Test",
            adresse="Test",
            kommune="Test",
            enrolled_at=date(2025, 6, 1),
            active_from=date(2026, 8, 1),  # Next school year
        )
        enrolled = school_year.get_enrolled_schools()
        self.assertNotIn(school, enrolled)


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

    def test_base_seats_with_enrollment_and_active_from(self):
        """School with enrolled_at and active_from has BASE_SEATS."""
        school = School.objects.create(
            name="Test",
            adresse="Test",
            kommune="Test",
            enrolled_at=date.today(),
            active_from=date.today(),
        )
        self.assertEqual(school.base_seats, School.BASE_SEATS)

    def test_base_seats_with_enrollment_no_active_from(self):
        """School with enrolled_at but no active_from has 0 base seats."""
        school = School.objects.create(name="Test", adresse="Test", kommune="Test", enrolled_at=date.today())
        self.assertEqual(school.base_seats, 0)

    def test_forankringsplads_before_one_year(self):
        """School active less than 1 year ago has no forankringsplads."""
        active_from_date = date.today() - timedelta(days=100)
        school = School.objects.create(
            name="Test",
            adresse="Test",
            kommune="Test",
            enrolled_at=active_from_date,
            active_from=active_from_date,
        )
        self.assertFalse(school.has_forankringsplads)
        self.assertEqual(school.forankring_seats, 0)

    def test_forankringsplads_after_one_year(self):
        """School active more than 1 year ago has forankringsplads."""
        active_from_date = date.today() - timedelta(days=400)
        school = School.objects.create(
            name="Test",
            adresse="Test",
            kommune="Test",
            enrolled_at=active_from_date,
            active_from=active_from_date,
        )
        self.assertTrue(school.has_forankringsplads)
        self.assertEqual(school.forankring_seats, School.FORANKRING_SEATS)

    def test_exceeds_seat_allocation_false_when_under(self):
        """exceeds_seat_allocation is False when used_seats <= total_seats."""
        from apps.courses.models import Course, CourseSignUp, Location

        school = School.objects.create(
            name="Test",
            adresse="Test",
            kommune="Test",
            enrolled_at=date.today(),
            active_from=date.today(),
        )
        location = Location.objects.create(name="Test Location")
        # School has 3 base seats in first year, create 2 signups in same year
        course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
            location=location,
            capacity=10,
        )
        CourseSignUp.objects.create(course=course, school=school, participant_name="A", participant_email="a@test.com")
        CourseSignUp.objects.create(course=course, school=school, participant_name="B", participant_email="b@test.com")
        self.assertEqual(school.used_seats, 2)
        self.assertFalse(school.exceeds_seat_allocation)

    def test_exceeds_seat_allocation_true_when_over(self):
        """exceeds_seat_allocation is True when used_seats > total_seats."""
        from apps.courses.models import Course, CourseSignUp, Location

        school = School.objects.create(
            name="Test",
            adresse="Test",
            kommune="Test",
            enrolled_at=date.today(),
            active_from=date.today(),
        )
        location = Location.objects.create(name="Test Location")
        # School has 3 base seats in first year, create 4 signups to exceed
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
            is_koordinator=True,
            email="test@example.com",
            phone="12345678",
        )
        self.assertEqual(person.name, "Test Person")
        self.assertEqual(person.school, self.school)

    def test_person_ordering(self):
        """Persons are ordered by is_koordinator (desc), is_oekonomisk_ansvarlig (desc), then name."""
        person1 = Person.objects.create(school=self.school, name="Zach", is_koordinator=False)
        person2 = Person.objects.create(school=self.school, name="Alice", is_koordinator=True)
        person3 = Person.objects.create(school=self.school, name="Bob", is_oekonomisk_ansvarlig=True)
        people = list(self.school.people.all())
        self.assertEqual(people[0], person2)  # Alice (koordinator)
        self.assertEqual(people[1], person3)  # Bob (oekonomisk_ansvarlig)
        self.assertEqual(people[2], person1)  # Zach (neither)

    def test_person_can_have_both_roles(self):
        """Person can be both koordinator and oekonomisk_ansvarlig."""
        person = Person.objects.create(
            school=self.school,
            name="Both Roles",
            is_koordinator=True,
            is_oekonomisk_ansvarlig=True,
        )
        self.assertTrue(person.is_koordinator)
        self.assertTrue(person.is_oekonomisk_ansvarlig)

    def test_person_roles_property(self):
        """roles property returns correct labels."""
        person1 = Person.objects.create(school=self.school, name="P1", is_koordinator=True)
        person2 = Person.objects.create(school=self.school, name="P2", is_oekonomisk_ansvarlig=True)
        person3 = Person.objects.create(
            school=self.school, name="P3", is_koordinator=True, is_oekonomisk_ansvarlig=True
        )
        person4 = Person.objects.create(school=self.school, name="P4")

        self.assertEqual(person1.roles, ["Koordinator"])
        self.assertEqual(person2.roles, ["Økonomisk ansvarlig"])
        self.assertEqual(person3.roles, ["Koordinator", "Økonomisk ansvarlig"])
        self.assertEqual(person4.roles, [])


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

    def test_school_detail_enrolled_with_missing_fields_shows_warning(self):
        """School detail shows warning for enrolled school missing postnummer/by/ean."""
        from datetime import date

        self.school.enrolled_at = date.today()
        self.school.save()
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:detail", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manglende oplysninger")

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

    def test_school_update_post(self):
        """School can be updated via POST."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("schools:update", kwargs={"pk": self.school.pk}),
            {
                "name": "Updated School",
                "kommune": "Københavns Kommune",
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.school.refresh_from_db()
        self.assertEqual(self.school.name, "Updated School")

    def test_school_form_no_nested_forms(self):
        """School form should not have nested form tags."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("schools:update", kwargs={"pk": self.school.pk}))
        content = response.content.decode()
        # Find form that posts to the school update URL (the main edit form)
        main_form_pattern = r'<form[^>]*method="post"[^>]*>.*?</form>'
        forms = re.findall(main_form_pattern, content, re.DOTALL | re.IGNORECASE)
        # Filter to forms that don't have an action (post to same page) - the edit form
        edit_forms = [f for f in forms if 'action="' not in f or 'action=""' in f]
        self.assertTrue(len(edit_forms) >= 1, "Should have at least one edit form")
        # The edit form should not contain another <form tag (nested forms)
        for form in edit_forms:
            nested_forms = form.count("<form")
            self.assertEqual(nested_forms, 1, f"Form should not have nested forms, found {nested_forms}")


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
            school=self.school, name="Test Person", is_koordinator=True, email="test@example.com"
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
                "is_koordinator": True,
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
                "is_koordinator": True,
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
        Person.objects.create(school=self.school1, name="John Doe", email="john@example.com", is_koordinator=True)

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
                "is_koordinator": True,
            }
        )
        self.assertTrue(form.is_valid())

    def test_person_form_requires_name(self):
        """PersonForm requires name field."""
        from .forms import PersonForm

        form = PersonForm(
            data={
                "is_koordinator": True,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_person_form_validates_email(self):
        """PersonForm validates email format."""
        from .forms import PersonForm

        form = PersonForm(
            data={
                "name": "Test Person",
                "is_koordinator": True,
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
        self.assertContains(response, "Kodeord og links")
        self.assertContains(response, "bafimoku")

    def test_detail_hides_credentials_for_unenrolled(self):
        """School detail hides credentials for unenrolled schools."""
        self.school.enrolled_at = None
        self.school.save()
        self.client.login(username="credsuser", password="testpass123")
        response = self.client.get(reverse("schools:detail", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Kodeord og links")

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
            is_koordinator=True,
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

    def test_public_view_has_edit_buttons(self):
        """Public view shows edit buttons for kontaktpersoner."""
        Person.objects.create(school=self.school, name="John", is_koordinator=True)
        response = self.client.get(f"/school/{self.school.signup_token}/")
        self.assertContains(response, "bi-pencil")


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

        Person.objects.create(school=self.school, name="Contact Person", is_koordinator=True)
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
        """Form queryset is filtered to school's enrolled years and excludes future years."""
        from .forms import InvoiceForm

        # Create another school year that is in the future
        future_year, _ = SchoolYear.objects.get_or_create(
            name="2030/31",
            defaults={"start_date": date(2030, 8, 1), "end_date": date(2031, 7, 31)},
        )

        form = InvoiceForm(school=self.school)
        queryset = form.fields["school_year"].queryset

        # School enrolled in 2024-09-01, so 2024/25 should be included
        self.assertIn(self.school_year, queryset)
        # Future years are excluded (only current and past years allowed)
        self.assertNotIn(future_year, queryset)

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
            active_from=date(2023, 9, 1),
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
            active_from=date(2024, 9, 1),
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
            active_from=date(2023, 9, 1),
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
            active_from=date(2023, 9, 1),
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
            active_from=date(2024, 9, 1),
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
            is_koordinator=True,
            titel=TitelChoice.SKOLELEDER,
        )
        self.assertEqual(person.titel, TitelChoice.SKOLELEDER)
        self.assertEqual(person.display_titel, "Skoleleder")

    def test_person_titel_other(self):
        """Person titel_other works when titel is ANDET."""
        person = Person.objects.create(
            school=self.school,
            name="Test Person",
            is_koordinator=True,
            titel=TitelChoice.ANDET,
            titel_other="Speciallærer",
        )
        self.assertEqual(person.display_titel, "Speciallærer")

    def test_person_is_oekonomisk_ansvarlig(self):
        """Person can have is_oekonomisk_ansvarlig set to True."""
        person = Person.objects.create(
            school=self.school,
            name="Test Person",
            is_oekonomisk_ansvarlig=True,
        )
        self.assertTrue(person.is_oekonomisk_ansvarlig)
        self.assertEqual(person.roles, ["Økonomisk ansvarlig"])


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
                "is_koordinator": True,
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
            is_koordinator=True,
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


class SchoolDetailBillingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="billinguser", password="testpass123", is_staff=True)
        self.school = School.objects.create(
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

    def test_detail_shows_billing_info(self):
        """School detail shows billing info when kommunen_betaler is True."""
        self.client.login(username="billinguser", password="testpass123")
        response = self.client.get(reverse("schools:detail", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kommunen betaler")
        self.assertContains(response, "Rådhuspladsen 1")
        self.assertContains(response, "5790000000001")

    def test_detail_hides_billing_when_not_enabled(self):
        """School detail hides billing info when kommunen_betaler is False."""
        self.school.kommunen_betaler = False
        self.school.save()
        self.client.login(username="billinguser", password="testpass123")
        response = self.client.get(reverse("schools:detail", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Kommunen betaler")


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
            is_koordinator=True,
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
        # Check for the badge-style display (course name + "Uddannet" badge)
        self.assertContains(response, "Uddannet")

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


class SchoolPublicPageIntegrationTest(TestCase):
    """Integration test for all public page features."""

    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Integration Test School",
            adresse="Test Address",
            kommune="Test Kommune",
            enrolled_at=date.today() - timedelta(days=400),
            signup_token="integration123token",
        )

    def test_full_public_page_with_all_features(self):
        """Public page shows contacts, participants, and materials correctly."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.courses.models import Course, CourseMaterial, CourseSignUp, Location

        # Create contact person
        Person.objects.create(
            school=self.school,
            name="Contact Person",
            is_koordinator=True,
            email="contact@test.com",
        )

        # Create course with material
        location = Location.objects.create(name="Copenhagen")
        course = Course.objects.create(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() - timedelta(days=28),
            location=location,
            capacity=20,
        )
        file = SimpleUploadedFile("course_slides.pdf", b"content")
        CourseMaterial.objects.create(course=course, file=file, name="Kursusslides")

        # Contact person attended course
        CourseSignUp.objects.create(
            school=self.school,
            course=course,
            participant_name="Contact Person",
            participant_email="contact@test.com",
            attendance="present",
        )

        # Another person attended (not a contact)
        CourseSignUp.objects.create(
            school=self.school,
            course=course,
            participant_name="Other Attendee",
            participant_email="other@test.com",
            attendance="present",
        )

        response = self.client.get(f"/school/{self.school.signup_token}/")
        self.assertEqual(response.status_code, 200)

        # Contact person section
        self.assertContains(response, "Kontaktpersoner")
        self.assertContains(response, "Contact Person")
        # Check for the badge-style display (course name + "Uddannet" badge)
        self.assertContains(response, "Uddannet")

        # Other participants section
        self.assertContains(response, "Kursusdeltagere")
        self.assertContains(response, "Other Attendee")

        # Materials section
        self.assertContains(response, "Kursusmaterialer")
        self.assertContains(response, "Kursusslides")


class CourseSignUpUpdateViewTest(TestCase):
    def setUp(self):
        from apps.courses.models import Course, CourseSignUp

        self.user = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")
        self.school = School.objects.create(name="Test School", kommune="København")
        self.course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
        )
        self.signup = CourseSignUp.objects.create(
            course=self.course,
            school=self.school,
            participant_name="Test Person",
            participant_email="test@example.com",
        )

    def test_get_edit_form(self):
        """Staff can access the edit form for a course signup."""
        response = self.client.get(
            reverse("schools:signup-update", kwargs={"school_pk": self.school.pk, "pk": self.signup.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Person")

    def test_post_updates_signup(self):
        """Staff can update participant details."""
        response = self.client.post(
            reverse("schools:signup-update", kwargs={"school_pk": self.school.pk, "pk": self.signup.pk}),
            {
                "participant_name": "Updated Name",
                "participant_title": "Lærer",
                "participant_email": "updated@example.com",
                "participant_phone": "12345678",
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.signup.refresh_from_db()
        self.assertEqual(self.signup.participant_name, "Updated Name")


class CourseSignUpDeleteViewTest(TestCase):
    def setUp(self):
        from apps.courses.models import Course, CourseSignUp

        self.user = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")
        self.school = School.objects.create(name="Test School", kommune="København")
        self.course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
        )
        self.signup = CourseSignUp.objects.create(
            course=self.course,
            school=self.school,
            participant_name="Test Person",
        )

    def test_get_delete_confirmation(self):
        """Staff can access delete confirmation."""
        response = self.client.get(
            reverse("schools:signup-delete", kwargs={"school_pk": self.school.pk, "pk": self.signup.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Person")

    def test_post_deletes_signup(self):
        """Staff can delete a signup."""
        from apps.courses.models import CourseSignUp

        response = self.client.post(
            reverse("schools:signup-delete", kwargs={"school_pk": self.school.pk, "pk": self.signup.pk})
        )
        self.assertEqual(response.status_code, 200)  # JSON response
        self.assertFalse(CourseSignUp.objects.filter(pk=self.signup.pk).exists())


class PublicPersonCreateViewTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Test School", kommune="København")
        self.school.generate_credentials()

    def test_get_form(self):
        """Anyone with token can access add person form."""
        response = self.client.get(reverse("school-public-person-create", kwargs={"token": self.school.signup_token}))
        self.assertEqual(response.status_code, 200)

    def test_post_creates_person(self):
        """Anyone with token can add a person."""
        self.client.post(
            reverse("school-public-person-create", kwargs={"token": self.school.signup_token}),
            {
                "name": "New Person",
                "titel": "",
                "titel_other": "",
                "phone": "12345678",
                "email": "new@example.com",
                "comment": "",
                "is_koordinator": True,
                "is_oekonomisk_ansvarlig": False,
            },
        )
        self.assertEqual(Person.objects.filter(school=self.school).count(), 1)
        person = Person.objects.get(school=self.school)
        self.assertEqual(person.name, "New Person")


class PublicPersonUpdateViewTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Test School", kommune="København")
        self.school.generate_credentials()
        self.person = Person.objects.create(school=self.school, name="Test Person")

    def test_get_form(self):
        """Anyone with token can access edit form."""
        response = self.client.get(
            reverse(
                "school-public-person-update",
                kwargs={"token": self.school.signup_token, "pk": self.person.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Person")

    def test_post_updates_person(self):
        """Anyone with token can update a person."""
        self.client.post(
            reverse(
                "school-public-person-update",
                kwargs={"token": self.school.signup_token, "pk": self.person.pk},
            ),
            {
                "name": "Updated Name",
                "titel": "",
                "titel_other": "",
                "phone": "",
                "email": "",
                "comment": "",
                "is_koordinator": False,
                "is_oekonomisk_ansvarlig": False,
            },
        )
        self.person.refresh_from_db()
        self.assertEqual(self.person.name, "Updated Name")


class PublicPersonDeleteViewTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Test School", kommune="København")
        self.school.generate_credentials()
        self.person = Person.objects.create(school=self.school, name="Test Person")

    def test_post_deletes_person(self):
        """Anyone with token can delete a person."""
        self.client.post(
            reverse(
                "school-public-person-delete",
                kwargs={"token": self.school.signup_token, "pk": self.person.pk},
            )
        )
        self.assertFalse(Person.objects.filter(pk=self.person.pk).exists())


class PublicCourseSignUpUpdateViewTest(TestCase):
    def setUp(self):
        from apps.courses.models import Course, CourseSignUp

        self.school = School.objects.create(name="Test School", kommune="København")
        self.school.generate_credentials()
        self.course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
        )
        self.signup = CourseSignUp.objects.create(
            course=self.course,
            school=self.school,
            participant_name="Test Person",
            participant_email="test@example.com",
        )

    def test_get_form(self):
        """Anyone with token can access edit form for signup."""
        response = self.client.get(
            reverse(
                "school-public-signup-update",
                kwargs={"token": self.school.signup_token, "pk": self.signup.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Person")

    def test_post_updates_signup(self):
        """Anyone with token can update participant details."""
        self.client.post(
            reverse(
                "school-public-signup-update",
                kwargs={"token": self.school.signup_token, "pk": self.signup.pk},
            ),
            {
                "participant_name": "Updated Name",
                "participant_title": "Lærer",
                "participant_email": "updated@example.com",
                "participant_phone": "12345678",
            },
        )
        self.signup.refresh_from_db()
        self.assertEqual(self.signup.participant_name, "Updated Name")


class KontaktpersonerKursusdeltagereIntegrationTest(TestCase):
    """Integration tests for the split kontaktpersoner/kursusdeltagere feature."""

    def setUp(self):
        from apps.courses.models import Course, CourseSignUp

        self.user = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.school = School.objects.create(name="Test School", kommune="København")
        self.school.generate_credentials()
        self.course = Course.objects.create(
            start_date=date.today(),
            end_date=date.today(),
        )
        # Create a kontaktperson
        self.person = Person.objects.create(
            school=self.school,
            name="Contact Person",
            email="contact@example.com",
            is_koordinator=True,
        )
        # Create a kursusdeltagere (signup)
        self.signup = CourseSignUp.objects.create(
            course=self.course,
            school=self.school,
            participant_name="Course Participant",
            participant_email="participant@example.com",
        )

    def test_staff_view_shows_both_boxes(self):
        """Staff view shows separate kontaktpersoner and kursusdeltagere boxes."""
        self.client.login(username="staff", password="pass")
        response = self.client.get(reverse("schools:detail", kwargs={"pk": self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kontaktpersoner")
        self.assertContains(response, "Kursusdeltagere")
        self.assertContains(response, "Contact Person")
        self.assertContains(response, "Course Participant")

    def test_public_view_shows_both_boxes(self):
        """Public view shows separate kontaktpersoner and kursusdeltagere boxes."""
        response = self.client.get(reverse("school-public", kwargs={"token": self.school.signup_token}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kontaktpersoner")
        self.assertContains(response, "Kursusdeltagere")
        self.assertContains(response, "Contact Person")
        self.assertContains(response, "Course Participant")

    def test_same_email_appears_in_both_lists(self):
        """A person and signup with the same email appear in both boxes (no matching)."""
        from apps.courses.models import CourseSignUp

        # Create signup with same email as person
        CourseSignUp.objects.create(
            course=self.course,
            school=self.school,
            participant_name="Same Email Person",
            participant_email="contact@example.com",  # Same as self.person
        )
        response = self.client.get(reverse("school-public", kwargs={"token": self.school.signup_token}))
        # Both should appear - kontaktperson in first box, signup in second box
        self.assertContains(response, "Contact Person")
        self.assertContains(response, "Same Email Person")


class StatusForYearTest(TestCase):
    def test_get_status_uses_active_from(self):
        """get_status_for_year uses active_from for forankring check."""
        school_year, _ = SchoolYear.objects.get_or_create(
            name="2025/26",
            defaults={
                "start_date": date(2025, 8, 1),
                "end_date": date(2026, 7, 31),
            },
        )
        # Enrolled recently but active_from before year start
        school = School.objects.create(
            name="Test Status",
            adresse="Test",
            kommune="Test",
            enrolled_at=date(2025, 9, 1),
            active_from=date(2024, 8, 1),
        )
        status_code, _, _ = school.get_status_for_year("2025/26")
        self.assertEqual(status_code, "tilmeldt_forankring")

    def test_was_enrolled_in_year_uses_active_from(self):
        """was_enrolled_in_year uses active_from."""
        school_year, _ = SchoolYear.objects.get_or_create(
            name="2025/26",
            defaults={
                "start_date": date(2025, 8, 1),
                "end_date": date(2026, 7, 31),
            },
        )
        school = School.objects.create(
            name="Test Enrolled",
            adresse="Test",
            kommune="Test",
            enrolled_at=date(2025, 6, 1),
            active_from=date(2026, 8, 1),  # After 2025/26
        )
        self.assertFalse(school.was_enrolled_in_year(school_year))


class EnrollmentCutoffTest(TestCase):
    def test_get_enrollment_cutoff_date_returns_last_course_deadline(self):
        """Cutoff is the signup deadline of the last course."""
        from apps.schools.models import get_enrollment_cutoff_date

        school_year, _ = SchoolYear.objects.get_or_create(
            name="2025/26",
            defaults={
                "start_date": date(2025, 8, 1),
                "end_date": date(2026, 7, 31),
            },
        )
        # Create courses with different deadlines
        Course.objects.create(
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 2),
            registration_deadline=date(2025, 9, 15),
        )
        Course.objects.create(
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 2),
            registration_deadline=date(2026, 4, 15),  # Latest deadline
        )
        cutoff = get_enrollment_cutoff_date(school_year)
        self.assertEqual(cutoff, date(2026, 4, 15))

    def test_get_enrollment_cutoff_date_returns_none_if_no_courses(self):
        """Cutoff is None if no courses exist."""
        from apps.schools.models import get_enrollment_cutoff_date

        school_year, _ = SchoolYear.objects.get_or_create(
            name="2025/26",
            defaults={
                "start_date": date(2025, 8, 1),
                "end_date": date(2026, 7, 31),
            },
        )
        cutoff = get_enrollment_cutoff_date(school_year)
        self.assertIsNone(cutoff)

    def test_get_default_active_from_returns_today_before_cutoff(self):
        """Default active_from is today when before cutoff."""
        from apps.schools.models import get_default_active_from

        # Create school year containing today
        today = date.today()
        if today.month >= 8:
            start_year = today.year
        else:
            start_year = today.year - 1
        SchoolYear.objects.get_or_create(
            name=f"{start_year}/{str(start_year + 1)[-2:]}",
            defaults={
                "start_date": date(start_year, 8, 1),
                "end_date": date(start_year + 1, 7, 31),
            },
        )
        # Create course with deadline in the future
        Course.objects.create(
            start_date=today + timedelta(days=60),
            end_date=today + timedelta(days=61),
            registration_deadline=today + timedelta(days=30),
        )
        result = get_default_active_from()
        self.assertEqual(result, today)


class SeatCalculationTest(TestCase):
    """Tests for per-year seat calculation methods on School model."""

    @classmethod
    def setUpTestData(cls):
        from apps.courses.models import Location

        # School years (use get_or_create since migrations may populate them)
        cls.year_2024, _ = SchoolYear.objects.get_or_create(
            name="2024/25",
            defaults={"start_date": date(2024, 8, 1), "end_date": date(2025, 7, 31)},
        )
        cls.year_2025, _ = SchoolYear.objects.get_or_create(
            name="2025/26",
            defaults={"start_date": date(2025, 8, 1), "end_date": date(2026, 7, 31)},
        )
        cls.year_2026, _ = SchoolYear.objects.get_or_create(
            name="2026/27",
            defaults={"start_date": date(2026, 8, 1), "end_date": date(2027, 7, 31)},
        )
        cls.location = Location.objects.create(name="Test Location SeatCalc")

    def _make_school(self, enrolled_at=None, active_from=None, opted_out_at=None):
        return School.objects.create(
            name=f"School {School.objects.count() + 1}",
            adresse="Addr",
            kommune="Kommune",
            enrolled_at=enrolled_at,
            active_from=active_from,
            opted_out_at=opted_out_at,
        )

    def _make_course(self, start_date):
        return Course.objects.create(
            start_date=start_date,
            end_date=start_date,
            location=self.location,
            capacity=30,
        )

    def _make_signup(self, school, course, name="Participant"):
        from apps.courses.models import CourseSignUp

        return CourseSignUp.objects.create(
            course=course,
            school=school,
            participant_name=name,
        )

    # --- get_first_school_year ---

    def test_get_first_school_year_returns_correct_year(self):
        """get_first_school_year returns the school year name for active_from date."""
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        self.assertEqual(school.get_first_school_year(), "2024/25")

    def test_get_first_school_year_january_falls_in_previous_year(self):
        """active_from in January falls in the school year that started previous August."""
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2025, 1, 15))
        self.assertEqual(school.get_first_school_year(), "2024/25")

    def test_get_first_school_year_none_without_active_from(self):
        """get_first_school_year returns None if no active_from."""
        school = self._make_school()
        self.assertIsNone(school.get_first_school_year())

    # --- get_first_year_seats ---

    def test_first_year_seats_zero_signups(self):
        """First year seats with 0 signups: 3 free, 0 used, 3 remaining."""
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        info = school.get_first_year_seats()
        self.assertEqual(info["free"], 3)
        self.assertEqual(info["used"], 0)
        self.assertEqual(info["remaining"], 3)
        self.assertEqual(info["year"], "2024/25")

    def test_first_year_seats_with_signups(self):
        """First year seats with 2 signups: 3 free, 2 used, 1 remaining."""
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        course = self._make_course(start_date=date(2024, 10, 15))
        self._make_signup(school, course, "A")
        self._make_signup(school, course, "B")
        info = school.get_first_year_seats()
        self.assertEqual(info["free"], 3)
        self.assertEqual(info["used"], 2)
        self.assertEqual(info["remaining"], 1)

    def test_first_year_seats_ignores_wrong_year_signups(self):
        """First year seats only counts signups from courses in the first school year."""
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        # Course in next year (2025/26) should NOT count
        course_next_year = self._make_course(start_date=date(2025, 9, 15))
        self._make_signup(school, course_next_year, "A")
        info = school.get_first_year_seats()
        self.assertEqual(info["used"], 0)
        self.assertEqual(info["remaining"], 3)

    def test_first_year_seats_not_enrolled(self):
        """Not-enrolled school gets zero first year seats."""
        school = self._make_school()  # no enrolled_at
        info = school.get_first_year_seats()
        self.assertEqual(info["free"], 0)
        self.assertEqual(info["used"], 0)
        self.assertEqual(info["remaining"], 0)
        self.assertIsNone(info["year"])

    def test_first_year_seats_enrolled_no_active_from(self):
        """Enrolled school without active_from gets zero first year seats."""
        school = self._make_school(enrolled_at=date(2024, 6, 1))
        info = school.get_first_year_seats()
        self.assertEqual(info["free"], 0)
        self.assertEqual(info["used"], 0)
        self.assertEqual(info["remaining"], 0)

    # --- get_forankring_seats ---

    def test_forankring_seats_zero_signups(self):
        """Forankring with 0 signups: 1 free, 0 used, 1 remaining."""
        # active_from in 2024/25, so in 2025/26+ the school is forankring
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        info = school.get_forankring_seats()
        # has_forankringsplads depends on current year being after first year,
        # so we need to check if the school is eligible
        if school.has_forankringsplads:
            self.assertEqual(info["free"], 1)
            self.assertEqual(info["used"], 0)
            self.assertEqual(info["remaining"], 1)
        else:
            # If current date is in 2024/25, school doesn't have forankring yet
            self.assertEqual(info["free"], 0)
            self.assertEqual(info["used"], 0)
            self.assertEqual(info["remaining"], 0)

    def test_forankring_seats_with_signup(self):
        """Forankring with 1 signup: 1 free, 1 used, 0 remaining."""
        # Use a school active from 2024/25 (should have forankring if current year > 2024/25)
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        if not school.has_forankringsplads:
            self.skipTest("Current date is in the school's first year, forankring not applicable")
        # Course after first year ends (i.e., in 2025/26 or later)
        course = self._make_course(start_date=date(2025, 9, 15))
        self._make_signup(school, course, "A")
        info = school.get_forankring_seats()
        self.assertEqual(info["free"], 1)
        self.assertEqual(info["used"], 1)
        self.assertEqual(info["remaining"], 0)

    def test_forankring_seats_not_enrolled(self):
        """Not-enrolled school gets zero forankring seats."""
        school = self._make_school()
        info = school.get_forankring_seats()
        self.assertEqual(info["free"], 0)
        self.assertEqual(info["used"], 0)
        self.assertEqual(info["remaining"], 0)

    def test_forankring_seats_no_forankringsplads(self):
        """School without forankringsplads gets zero forankring seats."""
        # A school that just started this year has no forankring
        today = date.today()
        school = self._make_school(enrolled_at=today, active_from=today)
        info = school.get_forankring_seats()
        self.assertEqual(info["free"], 0)
        self.assertEqual(info["used"], 0)

    # --- Cross-bucket isolation ---

    def test_first_year_signups_not_in_forankring(self):
        """Signups in the first year do not count in forankring bucket."""
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        if not school.has_forankringsplads:
            self.skipTest("Current date is in the school's first year")
        # Create signup in first year
        course_first = self._make_course(start_date=date(2024, 10, 15))
        self._make_signup(school, course_first, "First Year Person")
        info = school.get_forankring_seats()
        self.assertEqual(info["used"], 0)

    def test_forankring_signups_not_in_first_year(self):
        """Signups after the first year do not count in first year bucket."""
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        # Create signup after first year
        course_later = self._make_course(start_date=date(2025, 9, 15))
        self._make_signup(school, course_later, "Later Person")
        info = school.get_first_year_seats()
        self.assertEqual(info["used"], 0)

    # --- seats_for_course ---

    def test_seats_for_course_first_year(self):
        """seats_for_course returns first_year info for a course in the first year."""
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        course = self._make_course(start_date=date(2024, 11, 1))
        info = school.seats_for_course(course)
        self.assertTrue(info["is_first_year"])
        self.assertEqual(info["school_year"], "2024/25")
        self.assertEqual(info["free"], 3)

    def test_seats_for_course_later_year(self):
        """seats_for_course returns forankring info for a course in a later year."""
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        course = self._make_course(start_date=date(2025, 10, 1))
        info = school.seats_for_course(course)
        self.assertFalse(info["is_first_year"])
        self.assertEqual(info["school_year"], "2025/26")
        # free seats depend on has_forankringsplads
        if school.has_forankringsplads:
            self.assertEqual(info["free"], 1)
        else:
            self.assertEqual(info["free"], 0)

    # --- Backward-compat properties ---

    def test_current_seats_returns_current_bucket(self):
        """current_seats returns the bucket matching the current school year."""
        # School in forankring (active_from in previous school year)
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        seats = school.current_seats
        self.assertEqual(seats["label"], "Forankring")
        self.assertEqual(seats["free"], school.FORANKRING_SEATS)

    def test_total_seats_returns_current_bucket(self):
        """total_seats returns current bucket's free seats."""
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        self.assertEqual(school.total_seats, school.current_seats["free"])

    def test_used_seats_returns_current_bucket(self):
        """used_seats returns current bucket's used seats."""
        # School in forankring — signup in forankring period
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        course = self._make_course(start_date=date(2025, 10, 15))  # In 2025/26 (forankring)
        self._make_signup(school, course, "A")
        self.assertEqual(school.used_seats, 1)

    def test_remaining_seats_returns_current_bucket(self):
        """remaining_seats returns current bucket's remaining seats."""
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        self.assertEqual(school.remaining_seats, school.current_seats["remaining"])

    def test_has_available_seats(self):
        """has_available_seats is True when remaining_seats > 0."""
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        self.assertTrue(school.has_available_seats)

    def test_exceeds_seat_allocation(self):
        """exceeds_seat_allocation is True when used > total in current bucket."""
        # School in forankring (1 free seat) — add 2 signups in forankring period
        school = self._make_school(enrolled_at=date(2024, 6, 1), active_from=date(2024, 9, 1))
        for i in range(2):
            course = self._make_course(start_date=date(2025, 10, 1 + i))  # In 2025/26
            self._make_signup(school, course, f"P{i}")
        self.assertTrue(school.exceeds_seat_allocation)
