from apps.schools.models import School, SchoolYear

FILTER_PARAMS = ["search", "year", "status_filter", "kommune", "institutionstype", "unused_seats"]

_INSTITUTIONSTYPE_LABELS = {
    "folkeskole": "Folkeskole",
    "friskole": "Fri/privat grundskole",
    "efterskole": "Efterskole",
}

_DANISH_MONTHS = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]

_STATUS_LABELS_NO_YEAR = {
    "tilmeldt": "Alle tilmeldte",
    "tilmeldt_ny": "Ny tilmeldt (indeværende år)",
    "tilmeldt_fortsaetter": "Fortsætter (indeværende år)",
    "tilmeldt_venter": "Tilmeldt fra næste år",
    "frameldt": "Frameldt",
    "ikke_tilmeldt": "Ikke tilmeldt",
    "har_tilmeldinger_ikke_basal": "Har kurstilmeldinger (ikke tilmeldt i Basal)",
}

_STATUS_LABELS_WITH_YEAR = {
    "tilmeldt_ny": "Ny tilmeldt i {year}",
    "tilmeldt_fortsaetter": "Fortsætter i {year}",
    "frameldt": "Frameldt i {year}",
    "tilmeldt_venter": "Ventende til {year}",
    "ikke_tilmeldt": "Ikke tilmeldt i {year}",
}


def get_filter_summary(request):
    """Build a human-readable summary of active filters for display in the collapsed bar."""
    parts = []
    search = request.GET.get("search", "").strip()
    year = request.GET.get("year", "").strip()
    status_filter = request.GET.get("status_filter", "").strip()
    kommune = request.GET.get("kommune", "").strip()
    unused_seats = request.GET.get("unused_seats", "").strip()

    if search:
        parts.append(f'Søgning: "{search}"')

    if year and status_filter:
        template = _STATUS_LABELS_WITH_YEAR.get(status_filter)
        if template:
            parts.append(template.format(year=year))
        else:
            parts.append(f"Skoleår: {year}")
    elif year:
        parts.append(f"Skoleår: {year}")
    elif status_filter:
        label = _STATUS_LABELS_NO_YEAR.get(status_filter)
        if label:
            parts.append(label)

    if kommune:
        parts.append(f"Kommune: {kommune}")

    institutionstype = request.GET.get("institutionstype", "").strip()
    if institutionstype:
        parts.append(f"Type: {_INSTITUTIONSTYPE_LABELS.get(institutionstype, institutionstype)}")

    if unused_seats == "yes":
        parts.append("Har ubrugte pladser")
    elif unused_seats == "no":
        parts.append("Ingen ubrugte pladser")

    return " · ".join(parts)


class SchoolFilterMixin:
    """
    Mixin for views that include school_filter.html.

    Provides:
    - get_school_filter_queryset(): filtered School queryset from request.GET
    - get_filter_context(): context variables required by school_filter.html
    """

    def get_school_filter_queryset(self):
        """
        Returns a filtered School queryset from request.GET params.
        Applies the same filter logic as SchoolListView for use in views that include school_filter.html.
        """
        from django.db.models import Q

        queryset = School.objects.active().prefetch_related("people")
        search = self.request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(adresse__icontains=search)
                | Q(kommune__icontains=search)
                | Q(people__name__icontains=search)
                | Q(people__email__icontains=search)
            ).distinct()

        status_filter = self.request.GET.get("status_filter", "").strip()
        year_filter = self.request.GET.get("year", "").strip()

        if year_filter and status_filter:
            from apps.schools.school_years import get_school_year_dates

            try:
                start_date, end_date = get_school_year_dates(year_filter)
            except Exception:
                start_date = end_date = None

            if start_date:
                if status_filter == "alle_tilmeldte":
                    queryset = queryset.filter(
                        enrolled_at__isnull=False,
                        active_from__isnull=False,
                        active_from__lte=end_date,
                        opted_out_at__isnull=True,
                    )
                elif status_filter == "alle_ikke_tilmeldte":
                    queryset = queryset.filter(
                        Q(enrolled_at__isnull=True)
                        | Q(active_from__isnull=True)
                        | Q(active_from__gt=end_date)
                        | Q(opted_out_at__isnull=False)
                    )
                elif status_filter == "tilmeldt_ny":
                    queryset = queryset.filter(
                        enrolled_at__isnull=False,
                        active_from__isnull=False,
                        active_from__gte=start_date,
                        active_from__lte=end_date,
                        opted_out_at__isnull=True,
                    )
                elif status_filter == "tilmeldt_fortsaetter":
                    queryset = queryset.filter(
                        enrolled_at__isnull=False,
                        active_from__isnull=False,
                        active_from__lt=start_date,
                    ).filter(Q(opted_out_at__isnull=True) | Q(opted_out_at__gt=start_date))
                elif status_filter == "frameldt":
                    queryset = queryset.filter(
                        opted_out_at__isnull=False,
                        opted_out_at__gte=start_date,
                        opted_out_at__lte=end_date,
                    )
                elif status_filter == "tilmeldt_venter":
                    queryset = queryset.filter(
                        enrolled_at__isnull=False,
                        active_from__isnull=False,
                        active_from__gt=end_date,
                        opted_out_at__isnull=True,
                    )
                elif status_filter == "ikke_tilmeldt":
                    queryset = queryset.filter(
                        Q(enrolled_at__isnull=True) | Q(active_from__isnull=True) | Q(opted_out_at__lte=start_date)
                    )
                    queryset = [s for s in queryset if s.get_status_for_year(year_filter)[0] == "ikke_tilmeldt"]
        elif year_filter:
            # Year only: schools active at any point in that year
            from apps.schools.school_years import get_school_year_dates

            try:
                start_date, end_date = get_school_year_dates(year_filter)
                queryset = queryset.filter(
                    enrolled_at__isnull=False,
                    active_from__isnull=False,
                    active_from__lte=end_date,
                ).filter(Q(opted_out_at__isnull=True) | Q(opted_out_at__gt=start_date))
            except Exception:
                pass
        elif status_filter:
            if status_filter == "tilmeldt":
                queryset = queryset.filter(enrolled_at__isnull=False, opted_out_at__isnull=True)
            elif status_filter == "tilmeldt_ny":
                from apps.schools.school_years import get_current_school_year

                current_sy = get_current_school_year()
                queryset = queryset.filter(
                    enrolled_at__isnull=False,
                    active_from__isnull=False,
                    active_from__gte=current_sy.start_date,
                    active_from__lte=current_sy.end_date,
                    opted_out_at__isnull=True,
                )
            elif status_filter == "tilmeldt_fortsaetter":
                from apps.schools.school_years import get_current_school_year

                current_sy = get_current_school_year()
                queryset = queryset.filter(
                    enrolled_at__isnull=False,
                    active_from__isnull=False,
                    active_from__lt=current_sy.start_date,
                    opted_out_at__isnull=True,
                )
            elif status_filter == "tilmeldt_venter":
                from apps.schools.school_years import get_current_school_year

                current_sy = get_current_school_year()
                queryset = queryset.filter(
                    enrolled_at__isnull=False,
                    active_from__isnull=False,
                    active_from__gt=current_sy.end_date,
                    opted_out_at__isnull=True,
                )
            elif status_filter == "ikke_tilmeldt":
                queryset = queryset.filter(enrolled_at__isnull=True)
            elif status_filter == "frameldt":
                queryset = queryset.filter(opted_out_at__isnull=False)
            elif status_filter == "har_tilmeldinger_ikke_basal":
                from django.db.models import Q

                from apps.courses.models import CourseSignUp

                schools_with_signups = (
                    CourseSignUp.objects.filter(school__isnull=False).values_list("school_id", flat=True).distinct()
                )
                queryset = queryset.filter(pk__in=schools_with_signups).filter(
                    Q(enrolled_at__isnull=True) | Q(opted_out_at__isnull=False)
                )

        kommune_filter = self.request.GET.get("kommune", "").strip()
        if kommune_filter:
            if isinstance(queryset, list):
                queryset = [s for s in queryset if s.kommune == kommune_filter]
            else:
                queryset = queryset.filter(kommune=kommune_filter)

        institutionstype_filter = self.request.GET.get("institutionstype", "").strip()
        if institutionstype_filter:
            if isinstance(queryset, list):
                queryset = [s for s in queryset if s.institutionstype == institutionstype_filter]
            else:
                queryset = queryset.filter(institutionstype=institutionstype_filter)

        unused_filter = self.request.GET.get("unused_seats", "").strip()
        if unused_filter in ("yes", "no"):
            if not isinstance(queryset, list):
                queryset = list(queryset)
            if unused_filter == "yes":
                queryset = [s for s in queryset if s.remaining_seats > 0]
            else:
                queryset = [s for s in queryset if s.remaining_seats == 0]

        return queryset

    def get_filter_context(self):
        """Return context variables required by school_filter.html."""
        kommuner = (
            School.objects.active().exclude(kommune="").values_list("kommune", flat=True).distinct().order_by("kommune")
        )
        school_years = (
            SchoolYear.objects.filter(name__gte="2022/23", name__lte="2028/29")
            .order_by("start_date")
            .values_list("name", flat=True)
        )
        has_active_filters = any(self.request.GET.get(p) for p in FILTER_PARAMS)
        selected_year = self.request.GET.get("year", "").strip() or None

        selected_year_dates = None
        if selected_year:
            try:
                from apps.schools.school_years import get_school_year_dates

                sy_start, sy_end = get_school_year_dates(selected_year)
                selected_year_dates = (
                    f"{sy_start.day}. {_DANISH_MONTHS[sy_start.month - 1]} {sy_start.year}"
                    f" – "
                    f"{sy_end.day}. {_DANISH_MONTHS[sy_end.month - 1]} {sy_end.year}"
                )
            except Exception:
                pass

        return {
            "kommuner": list(kommuner),
            "school_years": list(school_years),
            "filter_summary": get_filter_summary(self.request),
            "has_active_filters": has_active_filters,
            "selected_year": selected_year,
            "selected_year_dates": selected_year_dates,
        }
