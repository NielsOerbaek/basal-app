from django.db import models


class ProjectSettings(models.Model):
    """Singleton model for project-wide settings."""

    klasseforloeb_per_teacher_per_year = models.DecimalField(
        default=1.0, decimal_places=2, max_digits=4, verbose_name="Klasseforløb pr. lærer pr. år"
    )
    students_per_klasseforloeb = models.DecimalField(
        default=24.0, decimal_places=1, max_digits=5, verbose_name="Elever pr. klasseforløb"
    )

    # Global fields shown on all enrolled schools' public pages
    samarbejdsvilkaar_file = models.FileField(
        upload_to="site_files/",
        blank=True,
        verbose_name="Samarbejdsvilkår (PDF)",
        help_text="Fil der vises på alle tilmeldte skolers sider",
    )
    login_info_text = models.TextField(
        blank=True,
        verbose_name="Login-oplysninger",
        help_text="Fritekst med login-oplysninger til sammenomtrivsel.com — vises på alle tilmeldte skolers sider",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Projektindstillinger"
        verbose_name_plural = "Projektindstillinger"

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton pattern
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
