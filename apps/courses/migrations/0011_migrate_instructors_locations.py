from django.db import migrations


def migrate_data(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Instructor = apps.get_model("courses", "Instructor")
    Location = apps.get_model("courses", "Location")

    # Migrate instructors
    for course in Course.objects.exclude(undervisere=""):
        names = [n.strip() for n in course.undervisere.split(",") if n.strip()]
        for name in names:
            instructor, _ = Instructor.objects.get_or_create(name=name)
            course.instructors.add(instructor)

    # Migrate locations
    for course in Course.objects.exclude(location=""):
        location, _ = Location.objects.get_or_create(name=course.location)
        course.location_new = location
        course.save()


def reverse_migrate(apps, schema_editor):
    Course = apps.get_model("courses", "Course")

    for course in Course.objects.all():
        # Restore undervisere from instructors
        instructor_names = list(course.instructors.values_list("name", flat=True))
        course.undervisere = ", ".join(instructor_names)

        # Restore location from location_new
        if course.location_new:
            course.location = course.location_new.name

        course.save()


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0010_add_location_and_course_fields"),
    ]

    operations = [
        migrations.RunPython(migrate_data, reverse_migrate),
    ]
