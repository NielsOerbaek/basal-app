"""Tests for the import_stil_schools management command."""

import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from apps.schools.models import InstitutionstypeChoice, Person, School

CSV_HEADER = (
    "HOVEDSKOLE_INST;INST_NR;INST_NAVN;ENHEDSART;INST_ADR;POSTNR;POSTDISTRIKT;"
    "TLF_NR;E_MAIL;WEB_ADR;INST_TYPE_NR;INST_TYPE_NAVN;INST_TYPE_GRUPPE;"
    "UNDERV_NIV;INST_LEDER;CVR_NR;KOMMUNE_NR;ADM_KOMMUNE_NAVN;BEL_KOMMUNE;"
    "BEL_KOMMUNE_NAVN;BEL_REGION;REGION_NAVN;EJER_KODE;EJERKODE_NAVN;P_NR;"
    "VEJKODE;GEO_BREDDE_GRAD;GEO_LAENGDE_GRAD"
)


def _row(**overrides):
    base = {
        "HOVEDSKOLE_INST": "",
        "INST_NR": "100001",
        "INST_NAVN": "Testfriskole",
        "ENHEDSART": "Institution uden enheder",
        "INST_ADR": "Testvej 1",
        "POSTNR": "8000",
        "POSTDISTRIKT": "Aarhus C",
        "TLF_NR": "12345678",
        "E_MAIL": "kontakt@test.dk",
        "WEB_ADR": "",
        "INST_TYPE_NR": "1013",
        "INST_TYPE_NAVN": "Friskoler og private grundskoler",
        "INST_TYPE_GRUPPE": "",
        "UNDERV_NIV": "9",
        "INST_LEDER": "Anne Andersen",
        "CVR_NR": "12345678",
        "KOMMUNE_NR": "",
        "ADM_KOMMUNE_NAVN": "",
        "BEL_KOMMUNE": "",
        "BEL_KOMMUNE_NAVN": "Aarhus Kommune",
        "BEL_REGION": "",
        "REGION_NAVN": "",
        "EJER_KODE": "",
        "EJERKODE_NAVN": "",
        "P_NR": "",
        "VEJKODE": "",
        "GEO_BREDDE_GRAD": "",
        "GEO_LAENGDE_GRAD": "",
    }
    base.update(overrides)
    cols = CSV_HEADER.split(";")
    return ";".join(base[c] for c in cols)


def _write_csv(rows):
    content = CSV_HEADER + "\n" + "\n".join(rows) + "\n"
    fh = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    fh.write(content)
    fh.close()
    return Path(fh.name)


class ImportStilSchoolsTest(TestCase):
    def _run(self, path, **opts):
        out = StringIO()
        call_command(
            "import_stil_schools",
            str(path),
            "--encoding",
            "utf-8",
            stdout=out,
            stderr=StringIO(),
            **opts,
        )
        return out.getvalue()

    def test_creates_friskole_with_people(self):
        path = _write_csv([_row()])
        self._run(path)

        school = School.objects.get(inst_nr="100001")
        self.assertEqual(school.name, "Testfriskole")
        self.assertEqual(school.institutionstype, InstitutionstypeChoice.FRISKOLE)
        self.assertEqual(school.kommune, "Aarhus Kommune")
        self.assertEqual(school.ean_nummer, "12345678")

        people = list(school.people.order_by("name"))
        self.assertEqual(len(people), 2)
        names = {p.name for p in people}
        self.assertIn("Anne Andersen", names)
        self.assertIn("Generel Kontakt", names)
        general = school.people.get(name="Generel Kontakt")
        self.assertEqual(general.email, "kontakt@test.dk")
        self.assertEqual(general.phone, "12345678")

    def test_skips_low_grade_school(self):
        path = _write_csv([_row(INST_NR="100002", UNDERV_NIV="6")])
        self._run(path)
        self.assertFalse(School.objects.filter(inst_nr="100002").exists())

    def test_efterskole_blank_underv_niv_kept(self):
        path = _write_csv(
            [
                _row(
                    INST_NR="200001",
                    INST_NAVN="Test Efterskole",
                    INST_TYPE_NR="1011",
                    INST_TYPE_NAVN="Efterskoler",
                    UNDERV_NIV="",
                )
            ]
        )
        self._run(path)
        s = School.objects.get(inst_nr="200001")
        self.assertEqual(s.institutionstype, InstitutionstypeChoice.EFTERSKOLE)

    def test_matched_school_gets_type_flipped(self):
        # Existing folkeskole row that matches by name+kommune
        existing = School.objects.create(
            name="Testfriskole",
            kommune="Aarhus Kommune",
            institutionstype=InstitutionstypeChoice.FOLKESKOLE,
        )
        path = _write_csv([_row()])
        self._run(path)
        existing.refresh_from_db()
        self.assertEqual(existing.institutionstype, InstitutionstypeChoice.FRISKOLE)
        self.assertEqual(existing.inst_nr, "100001")

    def test_matched_school_skips_general_kontakt_if_email_exists(self):
        existing = School.objects.create(
            name="Testfriskole",
            kommune="Aarhus Kommune",
        )
        Person.objects.create(school=existing, name="Eksisterende", email="kontakt@test.dk")
        path = _write_csv([_row()])
        self._run(path)
        # No new "Generel Kontakt" person should be added
        self.assertFalse(existing.people.filter(name="Generel Kontakt").exists())
        self.assertEqual(existing.people.count(), 1)

    def test_cross_type_match_becomes_kombineret(self):
        # Import as efterskole first
        path1 = _write_csv(
            [
                _row(
                    INST_NR="309300",
                    INST_NAVN="Vinde Helsinge Friskole, Vestsjællands Idrætsefterskole",
                    INST_TYPE_NR="1011",
                    INST_TYPE_NAVN="Efterskoler",
                    UNDERV_NIV="10",
                    BEL_KOMMUNE_NAVN="Kalundborg Kommune",
                )
            ]
        )
        self._run(path1)

        # Now import same name+kommune as friskole (different inst_nr)
        path2 = _write_csv(
            [
                _row(
                    INST_NR="309004",
                    INST_NAVN="Vinde Helsinge Friskole, Vestsjællands Idrætsefterskole",
                    INST_TYPE_NR="1013",
                    INST_TYPE_NAVN="Friskoler og private grundskoler",
                    UNDERV_NIV="9",
                    BEL_KOMMUNE_NAVN="Kalundborg Kommune",
                )
            ]
        )
        self._run(path2)

        schools = School.objects.filter(name="Vinde Helsinge Friskole, Vestsjællands Idrætsefterskole")
        self.assertEqual(schools.count(), 1)
        s = schools.first()
        self.assertEqual(s.institutionstype, InstitutionstypeChoice.FRISKOLE_EFTERSKOLE)
        # Existing inst_nr (efterskole) preserved
        self.assertEqual(s.inst_nr, "309300")

    def test_dry_run_does_not_persist(self):
        path = _write_csv([_row()])
        self._run(path, dry_run=True)
        self.assertFalse(School.objects.filter(inst_nr="100001").exists())
