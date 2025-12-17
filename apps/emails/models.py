from django.db import models


class EmailType(models.TextChoices):
    SIGNUP_CONFIRMATION = 'signup_confirmation', 'Tilmeldingsbekræftelse'
    COURSE_REMINDER = 'course_reminder', 'Kursuspåmindelse (2 dage før)'


class EmailTemplate(models.Model):
    """
    Editable email templates.

    Available template variables:
    - {{ participant_name }} - Participant's name
    - {{ participant_email }} - Participant's email
    - {{ school_name }} - School name
    - {{ course_title }} - Course title
    - {{ course_date }} - Course start date
    - {{ course_location }} - Course location
    """
    email_type = models.CharField(
        max_length=30,
        choices=EmailType.choices,
        unique=True,
        verbose_name='E-mail type'
    )
    subject = models.CharField(
        max_length=255,
        verbose_name='Emne',
        help_text='Kan indeholde variabler som {{ course_title }}'
    )
    body_html = models.TextField(
        verbose_name='Indhold (HTML)',
        help_text='HTML-indhold. Kan indeholde variabler som {{ participant_name }}'
    )
    attachment = models.FileField(
        upload_to='email_attachments/',
        blank=True,
        verbose_name='Vedhæftet fil',
        help_text='PDF eller anden fil der vedhæftes alle e-mails af denne type'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Aktiv',
        help_text='Deaktiver for at stoppe afsendelse af denne e-mail type'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'E-mail skabelon'
        verbose_name_plural = 'E-mail skabeloner'

    def __str__(self):
        return self.get_email_type_display()


class EmailLog(models.Model):
    """Log of sent emails for tracking and debugging."""
    email_type = models.CharField(
        max_length=30,
        choices=EmailType.choices,
        verbose_name='E-mail type'
    )
    recipient_email = models.EmailField(verbose_name='Modtager')
    recipient_name = models.CharField(max_length=255, verbose_name='Modtager navn')
    subject = models.CharField(max_length=255, verbose_name='Emne')
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_logs',
        verbose_name='Kursus'
    )
    signup = models.ForeignKey(
        'courses.CourseSignUp',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_logs',
        verbose_name='Tilmelding'
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name='Sendt')
    success = models.BooleanField(default=True, verbose_name='Succes')
    error_message = models.TextField(blank=True, verbose_name='Fejlbesked')

    class Meta:
        verbose_name = 'E-mail log'
        verbose_name_plural = 'E-mail logs'
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.recipient_email} - {self.get_email_type_display()} ({self.sent_at.strftime('%Y-%m-%d %H:%M')})"
