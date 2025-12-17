from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import School, Person, SchoolComment, PersonRole, SeatPurchase


class SchoolModelTest(TestCase):
    def test_create_school(self):
        """School model can be created and saved."""
        school = School.objects.create(
            name='Test School',
            location='Test Location',
        )
        self.assertEqual(school.name, 'Test School')
        self.assertTrue(school.is_active)

    def test_soft_delete(self):
        """School soft delete sets is_active to False."""
        school = School.objects.create(
            name='Test School',
            location='Test Location',
        )
        school.delete()
        school.refresh_from_db()
        self.assertFalse(school.is_active)

    def test_active_manager(self):
        """School.objects.active() returns only active schools."""
        active = School.objects.create(
            name='Active School',
            location='Location',
        )
        inactive = School.objects.create(
            name='Inactive School',
            location='Location',
            is_active=False
        )
        self.assertIn(active, School.objects.active())
        self.assertNotIn(inactive, School.objects.active())

    def test_base_seats_without_enrollment(self):
        """School without enrolled_at has 0 base seats."""
        school = School.objects.create(name='Test', location='Test')
        self.assertEqual(school.base_seats, 0)

    def test_base_seats_with_enrollment(self):
        """School with enrolled_at has BASE_SEATS."""
        school = School.objects.create(
            name='Test',
            location='Test',
            enrolled_at=date.today()
        )
        self.assertEqual(school.base_seats, School.BASE_SEATS)

    def test_forankringsplads_before_one_year(self):
        """School enrolled less than 1 year ago has no forankringsplads."""
        school = School.objects.create(
            name='Test',
            location='Test',
            enrolled_at=date.today() - timedelta(days=100)
        )
        self.assertFalse(school.has_forankringsplads)
        self.assertEqual(school.forankring_seats, 0)

    def test_forankringsplads_after_one_year(self):
        """School enrolled more than 1 year ago has forankringsplads."""
        school = School.objects.create(
            name='Test',
            location='Test',
            enrolled_at=date.today() - timedelta(days=400)
        )
        self.assertTrue(school.has_forankringsplads)
        self.assertEqual(school.forankring_seats, School.FORANKRING_SEATS)


class PersonModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School',
            location='Test Location',
        )

    def test_create_person(self):
        """Person model can be created and saved."""
        person = Person.objects.create(
            school=self.school,
            name='Test Person',
            role=PersonRole.KOORDINATOR,
            email='test@example.com',
            phone='12345678'
        )
        self.assertEqual(person.name, 'Test Person')
        self.assertEqual(person.school, self.school)

    def test_display_role_standard(self):
        """display_role returns label for standard roles."""
        person = Person.objects.create(
            school=self.school,
            name='Test',
            role=PersonRole.KOORDINATOR
        )
        self.assertEqual(person.display_role, 'Koordinator')

    def test_display_role_other(self):
        """display_role returns role_other for OTHER role."""
        person = Person.objects.create(
            school=self.school,
            name='Test',
            role=PersonRole.OTHER,
            role_other='Custom Role'
        )
        self.assertEqual(person.display_role, 'Custom Role')

    def test_display_role_other_empty(self):
        """display_role returns 'Andet' when OTHER role has no role_other."""
        person = Person.objects.create(
            school=self.school,
            name='Test',
            role=PersonRole.OTHER
        )
        self.assertEqual(person.display_role, 'Andet')

    def test_person_ordering(self):
        """Persons are ordered by is_primary (desc), then name."""
        person1 = Person.objects.create(
            school=self.school,
            name='Zach',
            is_primary=False
        )
        person2 = Person.objects.create(
            school=self.school,
            name='Alice',
            is_primary=True
        )
        person3 = Person.objects.create(
            school=self.school,
            name='Bob',
            is_primary=False
        )
        people = list(self.school.people.all())
        self.assertEqual(people[0], person2)  # Alice (primary)
        self.assertEqual(people[1], person3)  # Bob
        self.assertEqual(people[2], person1)  # Zach


class SchoolCommentModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School',
            location='Test Location',
        )
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_create_comment(self):
        """SchoolComment model can be created and saved."""
        comment = SchoolComment.objects.create(
            school=self.school,
            comment='Test comment',
            created_by=self.user
        )
        self.assertEqual(comment.comment, 'Test comment')
        self.assertEqual(comment.school, self.school)
        self.assertEqual(comment.created_by, self.user)

    def test_comment_ordering(self):
        """Comments are ordered by created_at descending."""
        comment1 = SchoolComment.objects.create(
            school=self.school,
            comment='First',
            created_by=self.user
        )
        comment2 = SchoolComment.objects.create(
            school=self.school,
            comment='Second',
            created_by=self.user
        )
        comments = list(self.school.school_comments.all())
        self.assertEqual(comments[0], comment2)  # Most recent first
        self.assertEqual(comments[1], comment1)


class SchoolViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.school = School.objects.create(
            name='Test School',
            location='Test Location',
        )

    def test_school_list_requires_login(self):
        """School list should redirect unauthenticated users."""
        response = self.client.get(reverse('schools:list'))
        self.assertEqual(response.status_code, 302)

    def test_school_list_loads(self):
        """School list should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schools/school_list.html')

    def test_school_detail_loads(self):
        """School detail should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:detail', kwargs={'pk': self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schools/school_detail.html')

    def test_school_create_loads(self):
        """School create form should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schools/school_form.html')

    def test_school_update_loads(self):
        """School update form should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:update', kwargs={'pk': self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schools/school_form.html')


class PersonViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.school = School.objects.create(
            name='Test School',
            location='Test Location',
        )
        self.person = Person.objects.create(
            school=self.school,
            name='Test Person',
            role=PersonRole.KOORDINATOR,
            email='test@example.com'
        )

    def test_person_create_requires_login(self):
        """Person create should redirect unauthenticated users."""
        response = self.client.get(reverse('schools:person-create', kwargs={'school_pk': self.school.pk}))
        self.assertEqual(response.status_code, 302)

    def test_person_create_loads(self):
        """Person create form should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:person-create', kwargs={'school_pk': self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schools/person_form.html')

    def test_person_create_post(self):
        """Person can be created via POST."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('schools:person-create', kwargs={'school_pk': self.school.pk}),
            {
                'name': 'New Person',
                'role': PersonRole.SKOLELEDER,
                'email': 'new@example.com',
                'phone': '87654321',
            }
        )
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.assertTrue(Person.objects.filter(name='New Person').exists())

    def test_person_update_loads(self):
        """Person update form should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:person-update', kwargs={'pk': self.person.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schools/person_form.html')

    def test_person_update_post(self):
        """Person can be updated via POST."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('schools:person-update', kwargs={'pk': self.person.pk}),
            {
                'name': 'Updated Name',
                'role': PersonRole.KOORDINATOR,
                'email': 'updated@example.com',
            }
        )
        self.assertEqual(response.status_code, 302)
        self.person.refresh_from_db()
        self.assertEqual(self.person.name, 'Updated Name')

    def test_person_delete_modal_loads(self):
        """Person delete modal should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:person-delete', kwargs={'pk': self.person.pk}))
        self.assertEqual(response.status_code, 200)

    def test_person_delete_post(self):
        """Person can be deleted via POST."""
        self.client.login(username='testuser', password='testpass123')
        person_pk = self.person.pk
        response = self.client.post(reverse('schools:person-delete', kwargs={'pk': person_pk}))
        self.assertEqual(response.status_code, 200)  # JSON response
        self.assertFalse(Person.objects.filter(pk=person_pk).exists())


class SchoolCommentViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.school = School.objects.create(
            name='Test School',
            location='Test Location',
        )
        self.comment = SchoolComment.objects.create(
            school=self.school,
            comment='Test comment',
            created_by=self.user
        )

    def test_comment_create_requires_login(self):
        """Comment create should redirect unauthenticated users."""
        response = self.client.get(reverse('schools:comment-create', kwargs={'school_pk': self.school.pk}))
        self.assertEqual(response.status_code, 302)

    def test_comment_create_loads(self):
        """Comment create form should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:comment-create', kwargs={'school_pk': self.school.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schools/comment_form.html')

    def test_comment_create_post(self):
        """Comment can be created via POST."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('schools:comment-create', kwargs={'school_pk': self.school.pk}),
            {'comment': 'New comment text'}
        )
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.assertTrue(SchoolComment.objects.filter(comment='New comment text').exists())
        new_comment = SchoolComment.objects.get(comment='New comment text')
        self.assertEqual(new_comment.created_by, self.user)

    def test_comment_delete_modal_loads(self):
        """Comment delete modal should load for staff users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('schools:comment-delete', kwargs={'pk': self.comment.pk}))
        self.assertEqual(response.status_code, 200)

    def test_comment_delete_post(self):
        """Comment can be deleted via POST."""
        self.client.login(username='testuser', password='testpass123')
        comment_pk = self.comment.pk
        response = self.client.post(reverse('schools:comment-delete', kwargs={'pk': comment_pk}))
        self.assertEqual(response.status_code, 200)  # JSON response
        self.assertFalse(SchoolComment.objects.filter(pk=comment_pk).exists())
