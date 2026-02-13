# Data + schema migration to rename forankring -> fortsætter

from django.db import migrations, models

SEAT_INCLUDES_TEXT = """<p><strong>1 kursusplads inkluderer:</strong> 2-dages forløb, overnatning, forplejning, notesbog, faciliteringsguide, 28 elevhæfter og web-app login.</p>"""


def rename_scenarios_forward(apps, schema_editor):
    SeatInfoContent = apps.get_model("signups", "SeatInfoContent")
    SeatInfoContent.objects.filter(scenario="forankring_available").update(
        scenario="fortsaetter_available",
        title="Fortsætterplads",
        content="<p>Som fortsætterskole har I adgang til 1 kursusplads.</p>" + SEAT_INCLUDES_TEXT,
    )
    SeatInfoContent.objects.filter(scenario="forankring_none").update(
        scenario="fortsaetter_none",
    )


def rename_scenarios_reverse(apps, schema_editor):
    SeatInfoContent = apps.get_model("signups", "SeatInfoContent")
    SeatInfoContent.objects.filter(scenario="fortsaetter_available").update(
        scenario="forankring_available",
        title="Forankringsplads",
        content="<p>Som en del af jeres forankringsaftale har I adgang til 1 kursusplads.</p>" + SEAT_INCLUDES_TEXT,
    )
    SeatInfoContent.objects.filter(scenario="fortsaetter_none").update(
        scenario="forankring_none",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("signups", "0007_update_seat_info_content"),
    ]

    operations = [
        # First rename the data rows
        migrations.RunPython(rename_scenarios_forward, rename_scenarios_reverse),
        # Then update the field choices
        migrations.AlterField(
            model_name="seatinfocontent",
            name="scenario",
            field=models.CharField(
                choices=[
                    ("first_year_unused", "Første år – ubrugte pladser"),
                    ("first_year_all_used", "Første år – alle pladser brugt"),
                    ("first_year_extra", "Første år – ekstra pladser"),
                    ("fortsaetter_available", "Fortsætter – plads tilgængelig"),
                    ("fortsaetter_none", "Fortsætter – ingen gratis pladser"),
                ],
                max_length=30,
                unique=True,
                verbose_name="Scenarie",
            ),
        ),
    ]
