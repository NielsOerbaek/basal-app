from django.contrib.auth.models import User
from django.db import models


class ContactTime(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='contact_history'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='contacts_made'
    )
    contacted_date = models.DateField()
    contacted_time = models.TimeField(null=True, blank=True)
    inbound = models.BooleanField(
        default=False,
        verbose_name='Kontaktede de os?'
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-contacted_date', '-contacted_time']

    def __str__(self):
        return f"{self.school.name} - {self.contacted_date.strftime('%Y-%m-%d')}"
