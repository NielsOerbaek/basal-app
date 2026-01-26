from datetime import date

from django.db import models


class AttendanceStatus(models.TextChoices):
    UNMARKED = "unmarked", "Ikke registreret"
    PRESENT = "present", "Til stede"
    ABSENT = "absent", "Fraværende"


class Instructor(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Navn")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Underviser"
        verbose_name_plural = "Undervisere"

    def __str__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=255, verbose_name="Navn")
    street_address = models.CharField(max_length=255, blank=True, verbose_name="Adresse")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="Postnummer")
    municipality = models.CharField(max_length=100, blank=True, verbose_name="By")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Lokation"
        verbose_name_plural = "Lokationer"

    def __str__(self):
        return self.name

    @property
    def full_address(self):
        """Returns formatted full address."""
        parts = [self.name]
        if self.street_address:
            parts.append(self.street_address)
        if self.postal_code or self.municipality:
            parts.append(f"{self.postal_code} {self.municipality}".strip())
        return ", ".join(parts)


class Course(models.Model):
    start_date = models.DateField(verbose_name="Startdato")
    end_date = models.DateField(verbose_name="Slutdato")
    location = models.ForeignKey(
        "Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
        verbose_name="Lokation",
    )
    instructors = models.ManyToManyField(
        "Instructor",
        blank=True,
        related_name="courses",
        verbose_name="Undervisere",
    )
    capacity = models.PositiveIntegerField(default=30, verbose_name="Kapacitet")
    comment = models.TextField(blank=True, verbose_name="Kommentar")
    materials = models.FileField(
        upload_to="course_materials/",
        blank=True,
        verbose_name="Kursusmateriale",
        help_text="PDF med kursusmateriale (sendes med påmindelses-e-mail)",
    )
    is_published = models.BooleanField(
        default=False,
        verbose_name="Offentliggjort",
        help_text="Offentliggjorte kurser vises på offentlige tilmeldingsformularer",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(fields=["start_date", "end_date"], name="unique_course_dates"),
        ]

    def __str__(self):
        return self.display_name

    @property
    def signup_count(self):
        return self.signups.count()

    @property
    def attendance_count(self):
        return self.signups.filter(attendance=AttendanceStatus.PRESENT).count()

    @property
    def spots_remaining(self):
        return max(0, self.capacity - self.signup_count)

    @property
    def is_full(self):
        return self.signup_count >= self.capacity

    @property
    def is_past(self):
        return self.end_date < date.today()

    @property
    def display_name(self):
        """Auto-generated course name with dates."""
        if self.start_date == self.end_date:
            date_str = self.start_date.strftime("%-d. %b %Y").lower()
        else:
            start_str = self.start_date.strftime("%-d. %b").lower()
            end_str = self.end_date.strftime("%-d. %b %Y").lower()
            date_str = f"{start_str} - {end_str}"
        return f"Kompetenceudviklingskursus, {date_str}"


class CourseSignUp(models.Model):
    school = models.ForeignKey("schools.School", on_delete=models.PROTECT, related_name="course_signups")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="signups")
    participant_name = models.CharField(max_length=255)
    participant_email = models.EmailField(blank=True, help_text="E-mail til kontakt")
    participant_phone = models.CharField(max_length=50, blank=True, verbose_name="Telefon")
    participant_title = models.CharField(max_length=255, blank=True, help_text="Jobtitel eller rolle")
    attendance = models.CharField(max_length=10, choices=AttendanceStatus.choices, default=AttendanceStatus.UNMARKED)
    is_underviser = models.BooleanField(
        default=True, verbose_name="Er underviser", help_text="Afkryds hvis deltageren er underviser (ikke leder/andet)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["school__name", "participant_name"]
        constraints = [
            models.UniqueConstraint(fields=["course", "school", "participant_name"], name="unique_signup_per_course")
        ]

    def __str__(self):
        return f"{self.participant_name} ({self.school.name})"


class CourseMaterial(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="course_materials")
    file = models.FileField(upload_to="course_materials/", verbose_name="Fil")
    name = models.CharField(max_length=255, blank=True, verbose_name="Navn", help_text="Valgfrit navn til filen")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]
        verbose_name = "Kursusmateriale"
        verbose_name_plural = "Kursusmaterialer"

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        if self.name:
            return self.name
        return self.file.name.split("/")[-1] if self.file else ""
