"""Convert School.kommune from CharField to ForeignKey → Kommune.

Steps:
1. Remove old indexes/constraint referencing the CharField
2. Add kommune_fk as nullable FK
3. Data migration: get_or_create Kommune rows, populate FK
4. Remove old kommune CharField
5. Rename kommune_fk → kommune
6. Re-add indexes/constraint on the new FK field
"""

import django.db.models.deletion
from django.db import migrations, models


def populate_kommune_fk(apps, schema_editor):
    School = apps.get_model("schools", "School")
    Kommune = apps.get_model("schools", "Kommune")

    # Build cache of existing Kommune rows
    kommune_cache = {k.name: k for k in Kommune.objects.all()}

    for school in School.objects.exclude(kommune="").exclude(kommune__isnull=True):
        name = school.kommune.strip()
        if not name:
            continue
        if name not in kommune_cache:
            kommune_cache[name] = Kommune.objects.create(name=name)
        school.kommune_fk = kommune_cache[name]
        school.save(update_fields=["kommune_fk"])


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0039_seed_all_kommuner"),
    ]

    operations = [
        # 1. Remove old indexes and constraint that reference the CharField
        migrations.RemoveConstraint(
            model_name="school",
            name="unique_school_per_kommune",
        ),
        migrations.RemoveIndex(
            model_name="school",
            name="schools_sch_kommune_5dce70_idx",
        ),
        migrations.RemoveIndex(
            model_name="school",
            name="schools_sch_is_acti_f9e33a_idx",
        ),
        # 2. Add new FK field
        migrations.AddField(
            model_name="school",
            name="kommune_fk",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="schools",
                to="schools.kommune",
                verbose_name="Kommune",
            ),
        ),
        # 3. Data migration
        migrations.RunPython(populate_kommune_fk, migrations.RunPython.noop),
        # 4. Remove old CharField
        migrations.RemoveField(
            model_name="school",
            name="kommune",
        ),
        # 5. Rename FK field
        migrations.RenameField(
            model_name="school",
            old_name="kommune_fk",
            new_name="kommune",
        ),
        # 6. Re-add indexes and constraint on the new FK
        migrations.AddIndex(
            model_name="school",
            index=models.Index(fields=["kommune"], name="schools_sch_kommune_fk_idx"),
        ),
        migrations.AddIndex(
            model_name="school",
            index=models.Index(fields=["is_active", "kommune"], name="schools_sch_active_kommune_idx"),
        ),
        migrations.AddConstraint(
            model_name="school",
            constraint=models.UniqueConstraint(
                fields=["name", "kommune"],
                name="unique_school_per_kommune",
            ),
        ),
    ]
