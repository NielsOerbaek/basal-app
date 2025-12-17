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

    # Danish model name translations
    MODEL_NAME_MAP = {
        'school': 'Skole',
        'seatpurchase': 'Pladskøb',
        'person': 'Person',
        'schoolcomment': 'Kommentar',
        'course': 'Kursus',
        'coursesignup': 'Tilmelding',
        'contacttime': 'Henvendelse',
    }

    # Danish action verbs (past tense)
    ACTION_VERB_MAP = {
        'CREATE': 'oprettet',
        'UPDATE': 'ændret',
        'DELETE': 'slettet',
    }

    @property
    def model_name_danish(self):
        """Return Danish name for the model."""
        model_name = self.content_type.model
        return self.MODEL_NAME_MAP.get(model_name, model_name.capitalize())

    @property
    def action_description(self):
        """Return combined type + action description (e.g., 'Henvendelse oprettet')."""
        verb = self.ACTION_VERB_MAP.get(self.action, self.get_action_display().lower())
        return f"{self.model_name_danish} {verb}"

    @property
    def description(self):
        """Return a meaningful description of the activity."""
        model_name = self.content_type.model

        # For comments and contact times, object_repr contains the comment text
        if model_name in ('schoolcomment', 'contacttime'):
            text = self.object_repr
            if len(text) > 100:
                return text[:100] + '...'
            return text

        # For persons, show the name
        if model_name == 'person':
            # Person __str__ is "Name (Role)"
            if '(' in self.object_repr:
                return self.object_repr.split('(')[0].strip()
            return self.object_repr

        # For course signups, show participant name
        if model_name == 'coursesignup':
            return self.object_repr

        # For seat purchases, show "X pladser"
        if model_name == 'seatpurchase':
            return self.object_repr

        # For schools and courses, just show the name
        return self.object_repr
