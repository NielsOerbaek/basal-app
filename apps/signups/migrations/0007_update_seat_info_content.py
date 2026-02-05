# Generated data migration to update seat info content text

from django.db import migrations

SEAT_INCLUDES_TEXT = """<p><strong>1 kursusplads inkluderer:</strong> 2-dages forløb, overnatning, forplejning, notesbog, faciliteringsguide, 28 elevhæfter og web-app login.</p>"""

PRICE_TABLE = """<p><strong>Priser for ekstra pladser (ekskl. moms):</strong></p>
<ul>
<li>1 ekstra plads: 7.995 kr.</li>
<li>2 ekstra pladser: 15.190 kr.</li>
<li>3 ekstra pladser: 21.586 kr.</li>
</ul>"""

UPDATES = {
    "first_year_all_used": {
        "title": "Alle pladser er brugt",
        "content": ("<p>Jeres skole har brugt alle kursuspladser fra det første år.</p>" + SEAT_INCLUDES_TEXT),
    },
    "first_year_extra": {
        "title": "Ekstra pladser",
        "content": (
            "<p>Jeres skole har brugt alle inkluderede kursuspladser. "
            "I kan tilkøbe ekstra pladser til nedenstående priser.</p>" + SEAT_INCLUDES_TEXT + PRICE_TABLE
        ),
    },
    "forankring_available": {
        "title": "Forankringsplads",
        "content": (
            "<p>Som en del af jeres forankringsaftale har I adgang til " "1 kursusplads.</p>" + SEAT_INCLUDES_TEXT
        ),
    },
    "forankring_none": {
        "title": "Ingen ledige pladser",
        "content": (
            "<p>Jeres skole har ingen kursuspladser tilbage i denne periode. "
            "I kan tilkøbe ekstra pladser til nedenstående priser.</p>" + SEAT_INCLUDES_TEXT + PRICE_TABLE
        ),
    },
}


def update_seat_info_content(apps, schema_editor):
    SeatInfoContent = apps.get_model("signups", "SeatInfoContent")
    for scenario, data in UPDATES.items():
        SeatInfoContent.objects.filter(scenario=scenario).update(title=data["title"], content=data["content"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("signups", "0006_populate_seat_info_content"),
    ]

    operations = [
        migrations.RunPython(update_seat_info_content, noop),
    ]
