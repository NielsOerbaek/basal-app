from datetime import date

from django.db import models


class AttendanceStatus(models.TextChoices):
    UNMARKED = 'unmarked', 'Ikke registreret'
    PRESENT = 'present', 'Til stede'
    ABSENT = 'absent', 'Fraværende'


class Course(models.Model):
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField(default=30)
    comment = models.TextField(blank=True)
    is_published = models.BooleanField(
        default=False,
        help_text='Offentliggjorte kurser vises på offentlige tilmeldingsformularer'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        if self.start_date == self.end_date:
            return f"{self.title} - {self.start_date.strftime('%Y-%m-%d')}"
        return f"{self.title} - {self.start_date.strftime('%Y-%m-%d')} til {self.end_date.strftime('%Y-%m-%d')}"

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


class CourseSignUp(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.PROTECT,
        related_name='course_signups'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='signups'
    )
    participant_name = models.CharField(max_length=255)
    participant_email = models.EmailField(
        blank=True,
        help_text='E-mail til kontakt'
    )
    participant_title = models.CharField(
        max_length=255,
        blank=True,
        help_text='Jobtitel eller rolle'
    )
    attendance = models.CharField(
        max_length=10,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.UNMARKED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['school__name', 'participant_name']
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'school', 'participant_name'],
                name='unique_signup_per_course'
            )
        ]

    def __str__(self):
        return f"{self.participant_name} ({self.school.name})"
