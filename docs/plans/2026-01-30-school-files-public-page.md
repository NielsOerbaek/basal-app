# School Files and Public Page Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add internal file uploads per school (staff-only) and enhance the public school page with course attendance and materials.

**Architecture:** New `SchoolFile` model for file storage. Public page view enhanced to aggregate CourseSignUp data by person email, showing attendance status and course materials for courses the school has participated in.

**Tech Stack:** Django 5, Bootstrap 5, HTMX for dynamic interactions, existing file upload patterns.

---

## Task 1: SchoolFile Model

**Files:**
- Modify: `apps/schools/models.py`
- Test: `apps/schools/tests.py`

**Step 1: Write the failing test**

Add to `apps/schools/tests.py`:

```python
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
        self.assertEqual(sf.filename, "my_document.pdf")
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.schools.tests.SchoolFileModelTest -v 2`
Expected: ImportError or AttributeError (SchoolFile doesn't exist)

**Step 3: Write minimal implementation**

Add to `apps/schools/models.py` (after `Invoice` class):

```python
class SchoolFile(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="school_files/%Y/%m/", verbose_name="Fil")
    description = models.TextField(blank=True, verbose_name="Beskrivelse")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="school_files_uploaded"
    )

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Skolefil"
        verbose_name_plural = "Skolefiler"

    def __str__(self):
        return f"{self.school.name} - {self.filename}"

    @property
    def filename(self):
        import os
        return os.path.basename(self.file.name)
```

**Step 4: Create and run migration**

Run: `python manage.py makemigrations schools`
Run: `python manage.py migrate`

**Step 5: Run test to verify it passes**

Run: `python manage.py test apps.schools.tests.SchoolFileModelTest -v 2`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/schools/models.py apps/schools/migrations/ apps/schools/tests.py
git commit -m "feat(schools): add SchoolFile model for internal file uploads"
```

---

## Task 2: SchoolFile Form

**Files:**
- Modify: `apps/schools/forms.py`
- Test: `apps/schools/tests.py`

**Step 1: Write the failing test**

Add to `apps/schools/tests.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.schools.tests.SchoolFileFormTest -v 2`
Expected: ImportError (SchoolFileForm doesn't exist)

**Step 3: Write minimal implementation**

Add to `apps/schools/forms.py`:

```python
from .models import Invoice, Person, School, SchoolComment, SchoolFile
```

Then add at end of file:

```python
class SchoolFileForm(forms.ModelForm):
    class Meta:
        model = SchoolFile
        fields = ["file", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "file",
            "description",
            Submit("submit", "Upload fil", css_class="btn btn-primary"),
        )
```

**Step 4: Run test to verify it passes**

Run: `python manage.py test apps.schools.tests.SchoolFileFormTest -v 2`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/schools/forms.py apps/schools/tests.py
git commit -m "feat(schools): add SchoolFileForm"
```

---

## Task 3: SchoolFile Views

**Files:**
- Modify: `apps/schools/views.py`
- Modify: `apps/schools/urls.py`
- Test: `apps/schools/tests.py`

**Step 1: Write the failing tests**

Add to `apps/schools/tests.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.schools.tests.SchoolFileViewTest -v 2`
Expected: NoReverseMatch (URL doesn't exist)

**Step 3: Write minimal implementation**

Add imports to `apps/schools/views.py`:

```python
from .forms import InvoiceForm, PersonForm, SchoolCommentForm, SchoolForm, SchoolFileForm
from .models import Invoice, Person, School, SchoolComment, SchoolYear, SchoolFile
```

Add views to `apps/schools/views.py` (after `RegenerateCredentialsView`):

```python
@method_decorator(staff_required, name="dispatch")
class SchoolFileCreateView(View):
    def get(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = SchoolFileForm()
        return render(
            request,
            "schools/file_form.html",
            {"school": school, "form": form},
        )

    def post(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = SchoolFileForm(request.POST, request.FILES)
        if form.is_valid():
            school_file = form.save(commit=False)
            school_file.school = school
            school_file.uploaded_by = request.user
            school_file.save()
            messages.success(request, f'Filen "{school_file.filename}" blev uploadet.')
            return redirect("schools:detail", pk=school.pk)
        return render(
            request,
            "schools/file_form.html",
            {"school": school, "form": form},
        )


@method_decorator(staff_required, name="dispatch")
class SchoolFileDeleteView(View):
    def get(self, request, pk):
        school_file = get_object_or_404(SchoolFile, pk=pk)
        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Slet fil",
                "message": format_html("Er du sikker på, at du vil slette <strong>{}</strong>?", school_file.filename),
                "delete_url": reverse_lazy("schools:file-delete", kwargs={"pk": pk}),
                "button_text": "Slet",
            },
        )

    def post(self, request, pk):
        school_file = get_object_or_404(SchoolFile, pk=pk)
        school_pk = school_file.school.pk
        filename = school_file.filename
        school_file.file.delete()  # Delete actual file
        school_file.delete()
        messages.success(request, f'Filen "{filename}" er blevet slettet.')
        return JsonResponse(
            {"success": True, "redirect": str(reverse_lazy("schools:detail", kwargs={"pk": school_pk}))}
        )
```

Add URLs to `apps/schools/urls.py` (after invoice URLs):

```python
    # File URLs
    path("<int:school_pk>/file/add/", views.SchoolFileCreateView.as_view(), name="file-create"),
    path("file/<int:pk>/delete/", views.SchoolFileDeleteView.as_view(), name="file-delete"),
```

**Step 4: Create template**

Create `apps/schools/templates/schools/file_form.html`:

```html
{% extends 'core/base.html' %}
{% load crispy_forms_tags %}

{% block title %}Upload fil - {{ school.name }}{% endblock %}

{% block content %}
<h1 class="mb-4"><i class="bi bi-file-earmark-plus me-2"></i>Upload fil</h1>
<p class="text-muted">Skole: <strong>{{ school.name }}</strong></p>

<div class="card">
    <div class="card-body">
        <form method="post" enctype="multipart/form-data">
            {% csrf_token %}
            {% crispy form %}
        </form>
    </div>
</div>

<div class="mt-3">
    <a href="{% url 'schools:detail' school.pk %}" class="btn btn-outline-secondary">Annuller</a>
</div>
{% endblock %}
```

**Step 5: Run test to verify it passes**

Run: `python manage.py test apps.schools.tests.SchoolFileViewTest -v 2`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/schools/views.py apps/schools/urls.py apps/schools/templates/schools/file_form.html apps/schools/tests.py
git commit -m "feat(schools): add SchoolFile create and delete views"
```

---

## Task 4: SchoolFile Section in School Detail Template

**Files:**
- Modify: `apps/schools/views.py` (SchoolDetailView)
- Modify: `apps/schools/templates/schools/school_detail.html`

**Step 1: Update SchoolDetailView context**

In `apps/schools/views.py`, update `SchoolDetailView.get_context_data`:

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context["contact_history"] = self.object.contact_history.select_related("created_by")[:10]
    context["course_signups"] = self.object.course_signups.select_related("course").order_by("-course__start_date")[
        :10
    ]
    context["seat_purchases"] = self.object.seat_purchases.all()
    context["people"] = self.object.people.all()
    context["school_comments"] = self.object.school_comments.select_related("created_by").all()
    context["invoices"] = self.object.invoices.all()
    context["enrollment_history"] = self.object.get_enrollment_history()
    context["person_form"] = PersonForm()
    context["comment_form"] = SchoolCommentForm()
    context["recent_activities"] = self.object.activity_logs.select_related("user", "content_type")[:5]
    context["today"] = date.today()
    context["school_files"] = self.object.files.select_related("uploaded_by").all()  # ADD THIS LINE
    return context
```

**Step 2: Add files section to template**

In `apps/schools/templates/schools/school_detail.html`, add after the "Kommentarer" card (around line 379):

```html
        <div class="card mb-4">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span><i class="bi bi-folder me-2"></i>Filer</span>
                <a href="{% url 'schools:file-create' school.pk %}" class="btn btn-sm btn-outline-primary">
                    <i class="bi bi-plus-lg me-1"></i>Upload fil
                </a>
            </div>
            <ul class="list-group list-group-flush">
                {% for file in school_files %}
                <li class="list-group-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="mb-1">
                                <a href="{{ file.file.url }}" target="_blank" class="text-decoration-none">
                                    <i class="bi bi-file-earmark me-1"></i>{{ file.filename }}
                                </a>
                            </div>
                            {% if file.description %}
                            <div class="small text-muted">{{ file.description }}</div>
                            {% endif %}
                            <div class="small text-muted">
                                {{ file.uploaded_at|date:"d. M Y" }}
                                {% if file.uploaded_by %} - {{ file.uploaded_by.get_full_name|default:file.uploaded_by.username }}{% endif %}
                            </div>
                        </div>
                        <button type="button" class="btn btn-sm btn-outline-danger ms-2" title="Slet"
                                hx-get="{% url 'schools:file-delete' file.pk %}"
                                hx-target="#modal-container">
                            <i class="bi bi-x-lg"></i>
                        </button>
                    </div>
                </li>
                {% empty %}
                <li class="list-group-item text-muted">Ingen filer uploadet.</li>
                {% endfor %}
            </ul>
        </div>
```

**Step 3: Run tests to verify nothing broke**

Run: `python manage.py test apps.schools -v 2`
Expected: PASS

**Step 4: Commit**

```bash
git add apps/schools/views.py apps/schools/templates/schools/school_detail.html
git commit -m "feat(schools): add files section to school detail page"
```

---

## Task 5: Register SchoolFile for Audit

**Files:**
- Modify: `apps/audit/apps.py`

**Step 1: Add registration**

In `apps/audit/apps.py`, add import and registration:

```python
from apps.schools.models import School, SeatPurchase, Person, SchoolComment, Invoice, SchoolYear, SchoolFile
```

Then add after the `Invoice` registration:

```python
        register_for_audit(
            SchoolFile,
            AuditCfg(
                excluded_fields=["id", "uploaded_at"],
                get_school=lambda instance: instance.school,
            ),
        )
```

**Step 2: Commit**

```bash
git add apps/audit/apps.py
git commit -m "feat(audit): register SchoolFile for activity tracking"
```

---

## Task 6: Public Page - Person Course Attendance

**Files:**
- Modify: `apps/schools/views.py` (SchoolPublicView)
- Modify: `apps/schools/templates/schools/school_public.html`
- Test: `apps/schools/tests.py`

**Step 1: Write the failing test**

Add to `apps/schools/tests.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.schools.tests.SchoolPublicViewCourseAttendanceTest -v 2`
Expected: AssertionError (content not found)

**Step 3: Update SchoolPublicView**

In `apps/schools/views.py`, update `SchoolPublicView.get_context_data`:

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    school = self.object
    people = school.people.all()
    all_signups = school.course_signups.select_related("course", "course__location").order_by("course__start_date")

    # Build set of person emails for matching
    person_emails = {p.email.lower() for p in people if p.email}

    # For each person, find their course signups
    people_with_courses = []
    for person in people:
        person_signups = []
        if person.email:
            person_signups = [s for s in all_signups if s.participant_email.lower() == person.email.lower()]
        people_with_courses.append({
            "person": person,
            "signups": person_signups,
        })

    # Course participants not matching any Person
    other_participants = {}
    for signup in all_signups:
        if signup.participant_email and signup.participant_email.lower() not in person_emails:
            email_key = signup.participant_email.lower()
            if email_key not in other_participants:
                other_participants[email_key] = {
                    "name": signup.participant_name,
                    "email": signup.participant_email,
                    "signups": [],
                }
            other_participants[email_key]["signups"].append(signup)

    context["people_with_courses"] = people_with_courses
    context["other_participants"] = list(other_participants.values())
    context["enrollment_history"] = school.get_enrollment_history()
    return context
```

**Step 4: Update public template**

Replace the Personer card in `apps/schools/templates/schools/school_public.html` (lines 122-158) with:

```html
            {% if people_with_courses %}
            <div class="card mb-4">
                <div class="card-header"><i class="bi bi-people me-2"></i>Kontaktpersoner</div>
                <ul class="list-group list-group-flush">
                    {% for item in people_with_courses %}
                    <li class="list-group-item">
                        <div class="mb-1">
                            <strong>{{ item.person.name }}</strong>
                            <span class="text-muted">, {{ item.person.display_role|lower }}</span>
                            {% if item.person.is_primary %}<span class="badge bg-primary ms-2">primær kontakt</span>{% endif %}
                        </div>
                        <div class="small text-muted">
                            {% if item.person.email %}<i class="bi bi-envelope me-1"></i>{{ item.person.email }}{% endif %}
                            {% if item.person.email and item.person.phone %}<span class="mx-2">|</span>{% endif %}
                            {% if item.person.phone %}<i class="bi bi-telephone me-1"></i>{{ item.person.phone }}{% endif %}
                        </div>
                        {% for signup in item.signups %}
                        <div class="small mt-1 ms-3 text-muted">
                            <i class="bi bi-arrow-return-right me-1"></i>
                            {% if signup.attendance == 'present' %}Uddannet på{% elif signup.attendance == 'absent' %}Mødte ikke op til{% else %}Tilmeldt{% endif %}
                            {{ signup.course.display_name }}
                        </div>
                        {% endfor %}
                    </li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}

            {% if other_participants %}
            <div class="card mb-4">
                <div class="card-header"><i class="bi bi-person-check me-2"></i>Kursusdeltagere</div>
                <ul class="list-group list-group-flush">
                    {% for participant in other_participants %}
                    <li class="list-group-item">
                        <div class="mb-1">
                            <strong>{{ participant.name }}</strong>
                        </div>
                        <div class="small text-muted">
                            <i class="bi bi-envelope me-1"></i>{{ participant.email }}
                        </div>
                        {% for signup in participant.signups %}
                        <div class="small mt-1 ms-3 text-muted">
                            <i class="bi bi-arrow-return-right me-1"></i>
                            {% if signup.attendance == 'present' %}Uddannet på{% elif signup.attendance == 'absent' %}Mødte ikke op til{% else %}Tilmeldt{% endif %}
                            {{ signup.course.display_name }}
                        </div>
                        {% endfor %}
                    </li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
```

**Step 5: Run test to verify it passes**

Run: `python manage.py test apps.schools.tests.SchoolPublicViewCourseAttendanceTest -v 2`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/schools/views.py apps/schools/templates/schools/school_public.html apps/schools/tests.py
git commit -m "feat(schools): show course attendance on public school page"
```

---

## Task 7: Public Page - Course Materials Section

**Files:**
- Modify: `apps/schools/views.py` (SchoolPublicView)
- Modify: `apps/schools/templates/schools/school_public.html`
- Test: `apps/schools/tests.py`

**Step 1: Write the failing test**

Add to `apps/schools/tests.py`:

```python
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
        from apps.courses.models import Course, CourseSignUp, CourseMaterial, Location

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
        CourseMaterial.objects.create(course=course, file=file, display_name="Kursusslides")

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
        CourseMaterial.objects.create(course=course, file=file, display_name="Secret Slides")

        response = self.client.get(f"/school/{self.school.signup_token}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Secret Slides")
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.schools.tests.SchoolPublicViewCourseMaterialsTest -v 2`
Expected: AssertionError (content not found)

**Step 3: Update SchoolPublicView**

In `apps/schools/views.py`, update `SchoolPublicView.get_context_data` to add courses with materials:

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    school = self.object
    people = school.people.all()
    all_signups = school.course_signups.select_related("course", "course__location").order_by("course__start_date")

    # Build set of person emails for matching
    person_emails = {p.email.lower() for p in people if p.email}

    # For each person, find their course signups
    people_with_courses = []
    for person in people:
        person_signups = []
        if person.email:
            person_signups = [s for s in all_signups if s.participant_email.lower() == person.email.lower()]
        people_with_courses.append({
            "person": person,
            "signups": person_signups,
        })

    # Course participants not matching any Person
    other_participants = {}
    for signup in all_signups:
        if signup.participant_email and signup.participant_email.lower() not in person_emails:
            email_key = signup.participant_email.lower()
            if email_key not in other_participants:
                other_participants[email_key] = {
                    "name": signup.participant_name,
                    "email": signup.participant_email,
                    "signups": [],
                }
            other_participants[email_key]["signups"].append(signup)

    # Courses with materials (newest first)
    from apps.courses.models import Course
    course_ids = all_signups.values_list("course_id", flat=True).distinct()
    courses_with_materials = (
        Course.objects.filter(pk__in=course_ids, materials__isnull=False)
        .prefetch_related("materials")
        .distinct()
        .order_by("-start_date")
    )

    context["people_with_courses"] = people_with_courses
    context["other_participants"] = list(other_participants.values())
    context["courses_with_materials"] = courses_with_materials
    context["enrollment_history"] = school.get_enrollment_history()
    return context
```

**Step 4: Add materials section to template**

Add at end of right column in `apps/schools/templates/schools/school_public.html` (before closing `</div>` of col-lg-6):

```html
            {% if courses_with_materials %}
            <div class="card mb-4">
                <div class="card-header"><i class="bi bi-file-earmark-text me-2"></i>Kursusmaterialer</div>
                <ul class="list-group list-group-flush">
                    {% for course in courses_with_materials %}
                    <li class="list-group-item">
                        <div class="fw-bold mb-2">{{ course.display_name }}</div>
                        {% for material in course.materials.all %}
                        <div class="small ms-3">
                            <a href="{{ material.file.url }}" target="_blank" class="text-decoration-none">
                                <i class="bi bi-file-earmark-pdf me-1"></i>{{ material.display_name }}
                            </a>
                        </div>
                        {% endfor %}
                    </li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
```

**Step 5: Run test to verify it passes**

Run: `python manage.py test apps.schools.tests.SchoolPublicViewCourseMaterialsTest -v 2`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/schools/views.py apps/schools/templates/schools/school_public.html apps/schools/tests.py
git commit -m "feat(schools): show course materials on public school page"
```

---

## Task 8: Final Integration Test

**Files:**
- Test: `apps/schools/tests.py`

**Step 1: Write integration test**

Add to `apps/schools/tests.py`:

```python
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
        from apps.courses.models import Course, CourseSignUp, CourseMaterial, Location

        # Create contact person
        person = Person.objects.create(
            school=self.school,
            name="Contact Person",
            role=PersonRole.KOORDINATOR,
            email="contact@test.com",
            is_primary=True,
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
        CourseMaterial.objects.create(course=course, file=file, display_name="Kursusslides")

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
        self.assertContains(response, "Uddannet på")

        # Other participants section
        self.assertContains(response, "Kursusdeltagere")
        self.assertContains(response, "Other Attendee")

        # Materials section
        self.assertContains(response, "Kursusmaterialer")
        self.assertContains(response, "Kursusslides")
```

**Step 2: Run all tests**

Run: `python manage.py test apps.schools -v 2`
Expected: All PASS

**Step 3: Commit**

```bash
git add apps/schools/tests.py
git commit -m "test(schools): add integration test for public page features"
```

---

## Summary

After completing all tasks:
1. SchoolFile model with file upload/delete functionality
2. Files section on staff school detail page
3. Audit tracking for file changes
4. Public page shows contact persons with course attendance
5. Public page shows separate course participants section
6. Public page shows course materials for attended courses
