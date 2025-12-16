# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("schools", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Course",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("location", models.CharField(max_length=255)),
                ("capacity", models.PositiveIntegerField(default=30)),
                ("comment", models.TextField(blank=True)),
                (
                    "is_published",
                    models.BooleanField(
                        default=False,
                        help_text="Offentliggjorte kurser vises på offentlige tilmeldingsformularer",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-start_date"],
            },
        ),
        migrations.CreateModel(
            name="CourseSignUp",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("participant_name", models.CharField(max_length=255)),
                (
                    "participant_title",
                    models.CharField(
                        blank=True, help_text="Jobtitel eller rolle", max_length=255
                    ),
                ),
                (
                    "attendance",
                    models.CharField(
                        choices=[
                            ("unmarked", "Ikke registreret"),
                            ("present", "Til stede"),
                            ("absent", "Fraværende"),
                        ],
                        default="unmarked",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="signups",
                        to="courses.course",
                    ),
                ),
                (
                    "school",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="course_signups",
                        to="schools.school",
                    ),
                ),
            ],
            options={
                "ordering": ["school__name", "participant_name"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("course", "school", "participant_name"),
                        name="unique_signup_per_course",
                    )
                ],
            },
        ),
    ]
