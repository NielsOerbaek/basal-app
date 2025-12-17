from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

User = get_user_model()


class ActionType(models.TextChoices):
    CREATE = 'CREATE', 'Oprettet'
    UPDATE = 'UPDATE', 'Opdateret'
    DELETE = 'DELETE', 'Slettet'


class ActivityLog(models.Model):
    """
    Generic activity log that can track changes to any model.
    Uses Django's ContentType framework for flexibility.
    """
    # Who performed the action
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        verbose_name='Bruger'
    )

    # What object was affected (generic foreign key)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name='Objekttype'
    )
    object_id = models.PositiveIntegerField(verbose_name='Objekt ID')
    content_object = GenericForeignKey('content_type', 'object_id')

    # Human-readable representation at time of action
    object_repr = models.CharField(
        max_length=255,
        verbose_name='Objekt beskrivelse'
    )

    # What action was performed
    action = models.CharField(
        max_length=10,
        choices=ActionType.choices,
        verbose_name='Handling'
    )

    # What changed (JSON field for flexibility)
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Ændringer',
        help_text='Field changes: {"field": {"old": ..., "new": ...}}'
    )

    # When it happened
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Tidspunkt'
    )

    # Optional: Related school for filtering
    related_school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        verbose_name='Relateret skole'
    )

    # Optional: Related course for filtering
    related_course = models.ForeignKey(
        'courses.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        verbose_name='Relateret kursus'
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Aktivitetslog'
        verbose_name_plural = 'Aktivitetslogs'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['related_school', '-timestamp']),
            models.Index(fields=['related_course', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.get_action_display()}: {self.object_repr}"
