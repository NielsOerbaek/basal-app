"""
Importer skoler fra STIL InstReg CSV-udtræk.

Forventet format: UTF-16-LE, semikolon-separeret, kolonner inkluderer
INST_NR, INST_NAVN, INST_ADR, POSTNR, POSTDISTRIKT, BEL_KOMMUNE_NAVN,
CVR_NR, INST_TYPE_NR, UNDERV_NIV.

Skoler filtreres så kun dem der dækker 7.-10. klasse importeres
(UNDERV_NIV >= 7 eller blank for efterskoler).
"""

import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.schools.models import InstitutionstypeChoice, Person, School, TitelChoice

# STIL INST_TYPE_NR -> our institutionstype
INST_TYPE_MAP = {
    "1011": InstitutionstypeChoice.EFTERSKOLE,  # Efterskoler
    "1013": InstitutionstypeChoice.FRISKOLE,  # Friskoler og private grundskoler
}


class Command(BaseCommand):
    help = "Importer friskoler/efterskoler fra STIL InstReg CSV-udtræk"

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="Sti til CSV-fil")
        parser.add_argument(
            "--type",
            choices=["friskole", "efterskole", "auto"],
            default="auto",
            help="Forventet institutionstype (auto = udled fra INST_TYPE_NR pr. række)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Vis hvad der ville ske uden at gemme",
        )
        parser.add_argument(
            "--encoding",
            default="utf-16-le",
            help="Filencoding (standard: utf-16-le)",
        )

    def handle(self, *args, **options):
        file_path = options["file_path"]
        forced_type = options["type"]
        dry_run = options["dry_run"]
        encoding = options["encoding"]

        try:
            with open(file_path, "r", encoding=encoding) as fh:
                reader = csv.DictReader(fh, delimiter=";")
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"Fil ikke fundet: {file_path}")
        except Exception as e:
            raise CommandError(f"Kunne ikke læse fil: {e}")

        self.stdout.write(f"Læste {len(rows)} rækker fra {file_path}")

        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN — ingen data gemmes ==="))

        stats = {
            "created": 0,
            "updated": 0,
            "skipped_grade": 0,
            "skipped_type": 0,
            "errors": 0,
            "people_created": 0,
        }
        self._stats = stats

        with transaction.atomic():
            for row in rows:
                result = self._process_row(row, forced_type, dry_run)
                stats[result] = stats.get(result, 0) + 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Færdig: {stats['created']} oprettet, {stats['updated']} opdateret, "
                f"{stats['people_created']} personer oprettet, "
                f"{stats['skipped_grade']} sprunget over (forkert klassetrin), "
                f"{stats['skipped_type']} sprunget over (forkert type), "
                f"{stats['errors']} fejl"
            )
        )

    def _process_row(self, row, forced_type, dry_run):
        # Determine institutionstype
        inst_type_nr = (row.get("INST_TYPE_NR") or "").strip()
        institutionstype = INST_TYPE_MAP.get(inst_type_nr)

        if forced_type == "friskole":
            if institutionstype != InstitutionstypeChoice.FRISKOLE:
                return "skipped_type"
        elif forced_type == "efterskole":
            if institutionstype != InstitutionstypeChoice.EFTERSKOLE:
                return "skipped_type"
        else:  # auto
            if institutionstype is None:
                return "skipped_type"

        # Filter on UNDERV_NIV: keep blank or >= 7
        underv_niv = (row.get("UNDERV_NIV") or "").strip()
        if underv_niv:
            try:
                if int(underv_niv) < 7:
                    return "skipped_grade"
            except ValueError:
                pass

        inst_nr = (row.get("INST_NR") or "").strip()
        name = (row.get("INST_NAVN") or "").strip()
        if not name:
            self.stderr.write(self.style.WARNING(f"Række uden INST_NAVN sprunget over (INST_NR={inst_nr})"))
            return "errors"

        kommune = (row.get("BEL_KOMMUNE_NAVN") or "").strip()
        # Strip "Kommune" suffix if present (e.g. "Københavns Kommune" -> "Københavns")
        # — actually keep as-is to match how existing data looks. Leave to user/admin.

        defaults = {
            "name": name,
            "adresse": (row.get("INST_ADR") or "").strip(),
            "postnummer": (row.get("POSTNR") or "").strip()[:4],
            "by": (row.get("POSTDISTRIKT") or "").strip(),
            "kommune": kommune,
            "ean_nummer": (row.get("CVR_NR") or "").strip()[:13],
            "institutionstype": institutionstype,
            "inst_nr": inst_nr,
        }

        # Lookup: prefer inst_nr, then (name, kommune)
        school = None
        if inst_nr:
            school = School.objects.filter(inst_nr=inst_nr).first()
        if not school:
            school = School.objects.filter(name=name, kommune=kommune).first()

        leader_name = (row.get("INST_LEDER") or "").strip()
        # INST_LEDER often has trailing notes like ", konstitueret" — keep as-is.
        general_email = (row.get("E_MAIL") or "").strip()
        general_phone = (row.get("TLF_NR") or "").strip()

        if school:
            # Detect cross-type match: same physical institution registered as
            # both friskole and efterskole → mark as kombineret. Preserve the
            # existing inst_nr in that case (we only have one slot).
            combined = {InstitutionstypeChoice.FRISKOLE, InstitutionstypeChoice.EFTERSKOLE}
            if school.institutionstype == InstitutionstypeChoice.FRISKOLE_EFTERSKOLE or (
                school.institutionstype in combined
                and institutionstype in combined
                and school.institutionstype != institutionstype
            ):
                defaults["institutionstype"] = InstitutionstypeChoice.FRISKOLE_EFTERSKOLE
                defaults["inst_nr"] = school.inst_nr or inst_nr

            changed = False
            for field, value in defaults.items():
                if getattr(school, field) != value:
                    setattr(school, field, value)
                    changed = True
            if changed and not dry_run:
                school.save()
            if changed:
                self.stdout.write(f"  ~ {name} ({kommune})")
            # For matched schools: only add Generel Kontakt if email not already present
            if general_email and not school.people.filter(email__iexact=general_email).exists():
                if not dry_run:
                    Person.objects.create(
                        school=school,
                        name="Generel Kontakt",
                        email=general_email,
                        phone=general_phone,
                    )
                self._stats["people_created"] += 1
                self.stdout.write(f"    + person: Generel Kontakt <{general_email}>")
            return "updated"
        else:
            if dry_run:
                self.stdout.write(self.style.SUCCESS(f"  + {name} ({kommune})"))
                # Count would-be people
                if leader_name:
                    self._stats["people_created"] += 1
                if general_email:
                    self._stats["people_created"] += 1
                return "created"
            new_school = School.objects.create(**defaults)
            self.stdout.write(self.style.SUCCESS(f"  + {name} ({kommune})"))
            if leader_name:
                Person.objects.create(
                    school=new_school,
                    name=leader_name,
                    titel=TitelChoice.SKOLELEDER,
                )
                self._stats["people_created"] += 1
            if general_email:
                Person.objects.create(
                    school=new_school,
                    name="Generel Kontakt",
                    email=general_email,
                    phone=general_phone,
                )
                self._stats["people_created"] += 1
            return "created"
