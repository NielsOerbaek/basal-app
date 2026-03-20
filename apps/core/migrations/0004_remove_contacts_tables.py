from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_add_seat_info_toggle"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "DROP TABLE IF EXISTS contacts_contacttime_contacted_persons CASCADE;",
                "DROP TABLE IF EXISTS contacts_contacttime CASCADE;",
            ],
            reverse_sql=[],  # No reverse — the app code is removed
        ),
    ]
