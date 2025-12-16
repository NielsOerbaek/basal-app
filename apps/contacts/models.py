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
    contacted_at = models.DateTimeField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-contacted_at']

    def __str__(self):
        return f"{self.school.name} - {self.contacted_at.strftime('%Y-%m-%d')}"
