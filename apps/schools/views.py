from datetime import date

from django.contrib import messages
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.decorators import staff_required
from apps.core.export import export_queryset_to_excel
from apps.core.mixins import SortableMixin

from .forms import InvoiceForm, PersonForm, SchoolCommentForm, SchoolForm
from .models import Invoice, Person, School, SchoolComment, SchoolYear


@method_decorator(staff_required, name="dispatch")
class KommuneListView(SortableMixin, ListView):
    template_name = "schools/kommune_list.html"
    context_object_name = "kommuner"
    sortable_fields = {
        "kommune": "kommune",
        "total": "total_schools",
        "enrolled": "enrolled_schools",
        "not_enrolled": "not_enrolled",
    }
    default_sort = "kommune"

    def get_base_queryset(self):
        return (
            School.objects.active()
            .exclude(kommune="")
            .values("kommune")
            .annotate(
                total_schools=Count("id"),
                enrolled_schools=Count("id", filter=Q(enrolled_at__isnull=False)),
                not_enrolled=F("total_schools") - F("enrolled_schools"),
            )
        )


@method_decorator(staff_required, name="dispatch")
class KommuneDetailView(ListView):
    template_name = "schools/kommune_detail.html"
    context_object_name = "schools"

    def get_queryset(self):
        return (
            School.objects.active().filter(kommune=self.kwargs["kommune"]).prefetch_related("people").order_by("name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["kommune"] = self.kwargs["kommune"]
        return context


@method_decorator(staff_required, name="dispatch")
class SchoolListView(SortableMixin, ListView):
    model = School
    template_name = "schools/school_list.html"
    context_object_name = "schools"
    paginate_by = 25
    sortable_fields = {
        "name": "name",
        "kommune": "kommune",
        "seats": "_remaining_seats",  # Special handling for computed property
        "contact": "_last_contact",  # Special handling for latest contact
    }
    default_sort = "name"

    def get_base_queryset(self):
        """Return the base queryset before sorting."""
        from django.db.models import OuterRef, Subquery

        from apps.contacts.models import ContactTime

        queryset = School.objects.active()

        # Search filter
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(adresse__icontains=search)
                | Q(kommune__icontains=search)
                | Q(people__name__icontains=search)
                | Q(people__email__icontains=search)
            ).distinct()

        # Enrollment status filter
        status_filter = self.request.GET.get("status_filter")
        if status_filter == "tilmeldt":
            # All enrolled (both new and anchoring)
            queryset = queryset.filter(enrolled_at__isnull=False, opted_out_at__isnull=True)
        elif status_filter == "tilmeldt_ny":
            # Enrolled in the current school year (on or after Aug 1 of current school year)
            from apps.schools.school_years import get_current_school_year

            current_sy = get_current_school_year()
            queryset = queryset.filter(
                enrolled_at__isnull=False, enrolled_at__gte=current_sy.start_date, opted_out_at__isnull=True
            )
        elif status_filter == "tilmeldt_forankring":
            # Enrolled before the current school year (forankring = anchoring)
            from apps.schools.school_years import get_current_school_year

            current_sy = get_current_school_year()
            queryset = queryset.filter(
                enrolled_at__isnull=False, enrolled_at__lt=current_sy.start_date, opted_out_at__isnull=True
            )
        elif status_filter == "ikke_tilmeldt":
            # Never enrolled
            queryset = queryset.filter(enrolled_at__isnull=True)
        elif status_filter == "frameldt":
            # Previously enrolled but opted out
            queryset = queryset.filter(opted_out_at__isnull=False)
        elif status_filter == "har_tilmeldinger_ikke_basal":
            # Schools with course signups but not enrolled in Basal
            from apps.courses.models import CourseSignUp

            # Get school IDs that have any signups
            schools_with_signups = (
                CourseSignUp.objects.filter(school__isnull=False).values_list("school_id", flat=True).distinct()
            )

            # Filter to schools not currently enrolled (never enrolled OR opted out)
            queryset = queryset.filter(pk__in=schools_with_signups).filter(
                Q(enrolled_at__isnull=True) | Q(opted_out_at__isnull=False)
            )

        # Kommune filter
        kommune_filter = self.request.GET.get("kommune")
        if kommune_filter:
            queryset = queryset.filter(kommune=kommune_filter)

        # School year status filter (for project goals drill-down)
        status_filter = self.request.GET.get("status")
        school_year_filter = self.request.GET.get("school_year")
        if status_filter and school_year_filter:
            # Use the model's get_status_for_year for consistent filtering
            from apps.schools.school_years import normalize_school_year

            year_str = normalize_school_year(school_year_filter)
            if status_filter == "new":
                queryset = [s for s in queryset if s.get_status_for_year(year_str)[0] == "tilmeldt_ny"]
            elif status_filter == "anchoring":
                queryset = [s for s in queryset if s.get_status_for_year(year_str)[0] == "tilmeldt_forankring"]

        # Unused seats filter
        unused_filter = self.request.GET.get("unused_seats")
        if unused_filter == "yes":
            # Schools with remaining seats > 0
            queryset = [s for s in queryset if s.remaining_seats > 0]
        elif unused_filter == "no":
            # Schools with remaining seats = 0
            queryset = [s for s in queryset if s.remaining_seats == 0]

        # Annotate with latest contact date
        if isinstance(queryset, list):
            # Already converted to list for unused_seats filter
            for school in queryset:
                last_contact = school.contact_history.order_by("-contacted_date").first()
                school.last_contact_date = last_contact.contacted_date if last_contact else None
        else:
            # Subquery to get latest contact date
            latest_contact = (
                ContactTime.objects.filter(school=OuterRef("pk"))
                .order_by("-contacted_date")
                .values("contacted_date")[:1]
            )
            queryset = queryset.annotate(last_contact_date=Subquery(latest_contact))

        return queryset

    def get_queryset(self):
        """Handle special sorting for computed fields."""
        sort, order = self.get_sort_params()
        queryset = self.get_base_queryset()

        # If queryset is already a list (from unused_seats filter), sort in Python
        if isinstance(queryset, list):
            reverse = order == "desc"
            if sort == "seats":
                queryset.sort(key=lambda s: s.remaining_seats, reverse=reverse)
            elif sort == "contact":

                def contact_key(s):
                    return getattr(s, "last_contact_date", None) or date.min

                queryset.sort(key=contact_key, reverse=reverse)
            elif sort == "name":
                queryset.sort(key=lambda s: s.name.lower(), reverse=reverse)
            elif sort == "kommune":
                queryset.sort(key=lambda s: (s.kommune or "").lower(), reverse=reverse)
            return queryset

        # For computed fields with Django QuerySet, convert to list and sort
        if sort in ("seats", "contact"):
            queryset = list(queryset)
            reverse = order == "desc"
            if sort == "seats":
                queryset.sort(key=lambda s: s.remaining_seats, reverse=reverse)
            elif sort == "contact":

                def contact_key(s):
                    return getattr(s, "last_contact_date", None) or date.min

                queryset.sort(key=contact_key, reverse=reverse)
            return queryset

        # Use default mixin sorting for other fields
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get unique kommuner for filter dropdown
        context["kommuner"] = (
            School.objects.active().exclude(kommune="").values_list("kommune", flat=True).distinct().order_by("kommune")
        )

        # Build filter explanation for project goals drill-down
        status = self.request.GET.get("status")
        school_year = self.request.GET.get("school_year")
        if status and school_year:
            from apps.schools.school_years import normalize_school_year

            year_display = normalize_school_year(school_year)
            if status == "new":
                context["filter_explanation"] = f"Viser skoler der blev tilmeldt i skoleåret {year_display}"
            elif status == "anchoring":
                context["filter_explanation"] = f"Viser skoler med forankringspladser i skoleåret {year_display}"

        return context


@method_decorator(staff_required, name="dispatch")
class SchoolCreateView(CreateView):
    model = School
    form_class = SchoolForm
    template_name = "schools/school_form.html"
    success_url = reverse_lazy("schools:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.generate_credentials()
        messages.success(self.request, f'Skolen "{self.object.name}" blev oprettet.')
        return response


@method_decorator(staff_required, name="dispatch")
class SchoolDetailView(DetailView):
    model = School
    template_name = "schools/school_detail.html"
    context_object_name = "school"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contact_history"] = self.object.contact_history.select_related("created_by")[:10]
        context["course_signups"] = self.object.course_signups.select_related("course").order_by("-course__start_date")[
            :10
        ]
        context["seat_purchases"] = self.object.seat_purchases.all()
        context["people"] = self.object.people.all()
        context["school_comments"] = self.object.school_comments.select_related("created_by").all()
        context["invoices"] = self.object.invoices.all()
        context["enrollment_history"] = self.object.get_enrollment_history()
        context["person_form"] = PersonForm()
        context["comment_form"] = SchoolCommentForm()
        context["recent_activities"] = self.object.activity_logs.select_related("user", "content_type")[:5]
        context["today"] = date.today()
        return context


@method_decorator(staff_required, name="dispatch")
class SchoolUpdateView(UpdateView):
    model = School
    form_class = SchoolForm
    template_name = "schools/school_form.html"

    def get_success_url(self):
        return reverse_lazy("schools:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Skolen "{self.object.name}" blev opdateret.')
        return response


@method_decorator(staff_required, name="dispatch")
class ToggleEnrollmentView(View):
    """Toggle school enrollment/unenrollment with a specific date."""

    def post(self, request, pk):
        from datetime import datetime

        school = get_object_or_404(School, pk=pk)
        date_str = request.POST.get("date")

        try:
            enrollment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            messages.error(request, "Ugyldig dato.")
            return redirect("schools:detail", pk=pk)

        if school.is_enrolled:
            # Unenroll
            school.opted_out_at = enrollment_date
            school.save(update_fields=["opted_out_at"])
            messages.success(request, f'"{school.name}" er blevet frameldt Basal.')
        else:
            # Enroll
            school.enrolled_at = enrollment_date
            school.opted_out_at = None  # Clear any previous opt-out
            school.save(update_fields=["enrolled_at", "opted_out_at"])
            # Generate credentials if not already set
            if not school.signup_password:
                school.generate_credentials()
            messages.success(request, f'"{school.name}" er blevet tilmeldt Basal.')

        return redirect("schools:detail", pk=pk)


@method_decorator(staff_required, name="dispatch")
class SchoolDeleteView(View):
    def get(self, request, pk):
        school = School.objects.get(pk=pk)
        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Deaktiver skole",
                "message": format_html("Er du sikker på, at du vil deaktivere <strong>{}</strong>?", school.name),
                "warning": "Skolen vil blive skjult, men dens data bevares.",
                "delete_url": reverse_lazy("schools:delete", kwargs={"pk": pk}),
                "button_text": "Deaktiver",
            },
        )

    def post(self, request, pk):
        school = School.objects.get(pk=pk)
        school_name = school.name
        school.delete()
        messages.success(request, f'Skolen "{school_name}" er blevet deaktiveret.')
        return JsonResponse({"success": True, "redirect": str(reverse_lazy("schools:list"))})


@method_decorator(staff_required, name="dispatch")
class SchoolHardDeleteView(View):
    """Permanently delete a school and all related data."""

    def get(self, request, pk):
        from apps.courses.models import CourseSignUp

        school = School.objects.get(pk=pk)
        signup_count = CourseSignUp.objects.filter(school=school).count()
        person_count = school.people.count()
        comment_count = school.school_comments.count()
        contact_count = school.contact_history.count()
        invoice_count = school.invoices.count()

        warning_parts = []
        if signup_count:
            warning_parts.append(f"{signup_count} kursustilmelding{'er' if signup_count != 1 else ''}")
        if person_count:
            warning_parts.append(f"{person_count} person{'er' if person_count != 1 else ''}")
        if comment_count:
            warning_parts.append(f"{comment_count} kommentar{'er' if comment_count != 1 else ''}")
        if contact_count:
            warning_parts.append(f"{contact_count} henvendelse{'r' if contact_count != 1 else ''}")
        if invoice_count:
            warning_parts.append(f"{invoice_count} faktura{'er' if invoice_count != 1 else ''}")

        if warning_parts:
            warning = f"Dette vil permanent slette: {', '.join(warning_parts)}. Handlingen kan ikke fortrydes!"
        else:
            warning = "Handlingen kan ikke fortrydes!"

        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Slet skole permanent",
                "message": format_html(
                    "Er du sikker på, at du vil <strong>permanent slette</strong> skolen <strong>{}</strong>?",
                    school.name,
                ),
                "warning": warning,
                "delete_url": reverse_lazy("schools:hard-delete", kwargs={"pk": pk}),
                "button_text": "Slet permanent",
            },
        )

    def post(self, request, pk):
        from apps.courses.models import CourseSignUp

        school = School.objects.get(pk=pk)
        school_name = school.name

        # Delete course signups first (they have PROTECT)
        CourseSignUp.objects.filter(school=school).delete()

        # Now hard delete the school (bypassing soft delete)
        School.objects.filter(pk=pk).delete()

        messages.success(request, f'Skolen "{school_name}" og al relateret data er blevet permanent slettet.')
        return JsonResponse({"success": True, "redirect": str(reverse_lazy("schools:list"))})


@method_decorator(staff_required, name="dispatch")
class SchoolExportView(View):
    def get(self, request):
        queryset = School.objects.active()
        fields = [
            ("name", "Navn"),
            ("adresse", "Adresse"),
            ("kommune", "Kommune"),
            ("enrolled_at", "Tilmeldt"),
            ("created_at", "Oprettet"),
        ]
        return export_queryset_to_excel(queryset, fields, "schools")


@method_decorator(staff_required, name="dispatch")
class SchoolAutocompleteView(View):
    def get(self, request):
        query = request.GET.get("q", "")
        schools = School.objects.active().filter(name__icontains=query)[:10]
        results = [{"id": s.pk, "name": s.name, "kommune": s.kommune} for s in schools]
        return JsonResponse({"results": results})


@method_decorator(staff_required, name="dispatch")
class PersonCreateView(View):
    def get(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = PersonForm()
        return render(
            request,
            "schools/person_form.html",
            {
                "school": school,
                "form": form,
            },
        )

    def post(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = PersonForm(request.POST)
        if form.is_valid():
            person = form.save(commit=False)
            person.school = school
            person.save()
            messages.success(request, f'Person "{person.name}" tilføjet.')
            return redirect("schools:detail", pk=school.pk)
        return render(
            request,
            "schools/person_form.html",
            {
                "school": school,
                "form": form,
            },
        )


@method_decorator(staff_required, name="dispatch")
class PersonUpdateView(View):
    def get(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        form = PersonForm(instance=person)
        return render(
            request,
            "schools/person_form.html",
            {
                "school": person.school,
                "form": form,
                "person": person,
            },
        )

    def post(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        form = PersonForm(request.POST, instance=person)
        if form.is_valid():
            form.save()
            messages.success(request, f'Person "{person.name}" opdateret.')
            return redirect("schools:detail", pk=person.school.pk)
        return render(
            request,
            "schools/person_form.html",
            {
                "school": person.school,
                "form": form,
                "person": person,
            },
        )


@method_decorator(staff_required, name="dispatch")
class PersonDeleteView(View):
    def get(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Slet person",
                "message": format_html("Er du sikker på, at du vil slette <strong>{}</strong>?", person.name),
                "delete_url": reverse_lazy("schools:person-delete", kwargs={"pk": pk}),
                "button_text": "Slet",
            },
        )

    def post(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        school_pk = person.school.pk
        person_name = person.name
        person.delete()
        messages.success(request, f'Person "{person_name}" er blevet slettet.')
        return JsonResponse(
            {"success": True, "redirect": str(reverse_lazy("schools:detail", kwargs={"pk": school_pk}))}
        )


@method_decorator(staff_required, name="dispatch")
class SchoolCommentCreateView(View):
    def get(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = SchoolCommentForm()
        return render(
            request,
            "schools/comment_form.html",
            {
                "school": school,
                "form": form,
            },
        )

    def post(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = SchoolCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.school = school
            comment.created_by = request.user
            comment.save()
            messages.success(request, "Kommentar tilføjet.")
            return redirect("schools:detail", pk=school.pk)
        return render(
            request,
            "schools/comment_form.html",
            {
                "school": school,
                "form": form,
            },
        )


@method_decorator(staff_required, name="dispatch")
class SchoolCommentDeleteView(View):
    def get(self, request, pk):
        get_object_or_404(SchoolComment, pk=pk)  # Verify exists
        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Slet kommentar",
                "message": "Er du sikker på, at du vil slette denne kommentar?",
                "delete_url": reverse_lazy("schools:comment-delete", kwargs={"pk": pk}),
                "button_text": "Slet",
            },
        )

    def post(self, request, pk):
        comment = get_object_or_404(SchoolComment, pk=pk)
        school_pk = comment.school.pk
        comment.delete()
        messages.success(request, "Kommentar er blevet slettet.")
        return JsonResponse(
            {"success": True, "redirect": str(reverse_lazy("schools:detail", kwargs={"pk": school_pk}))}
        )


@method_decorator(staff_required, name="dispatch")
class InvoiceCreateView(View):
    def get(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = InvoiceForm(school=school)
        return render(
            request,
            "schools/invoice_form.html",
            {
                "school": school,
                "form": form,
            },
        )

    def post(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = InvoiceForm(request.POST, school=school)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.school = school
            invoice.save()
            messages.success(request, f'Faktura "{invoice.invoice_number}" tilføjet.')
            return redirect("schools:detail", pk=school.pk)
        return render(
            request,
            "schools/invoice_form.html",
            {
                "school": school,
                "form": form,
            },
        )


@method_decorator(staff_required, name="dispatch")
class InvoiceDeleteView(View):
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Slet faktura",
                "message": format_html(
                    "Er du sikker på, at du vil slette faktura <strong>{}</strong>?", invoice.invoice_number
                ),
                "delete_url": reverse_lazy("schools:invoice-delete", kwargs={"pk": pk}),
            },
        )

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        school_pk = invoice.school.pk
        invoice_number = invoice.invoice_number
        invoice.delete()
        messages.success(request, f'Faktura "{invoice_number}" er blevet slettet.')
        return JsonResponse(
            {"success": True, "redirect": str(reverse_lazy("schools:detail", kwargs={"pk": school_pk}))}
        )


@method_decorator(staff_required, name="dispatch")
class MissingInvoicesView(ListView):
    template_name = "schools/missing_invoices.html"
    context_object_name = "missing_invoices"

    def _get_relevant_years(self):
        """Get current and previous school years (max 2)."""
        # Get the most recent school year that has started
        from datetime import date

        today = date.today()
        return SchoolYear.objects.filter(start_date__lte=today).order_by("-start_date")[:2]

    def get_queryset(self):
        relevant_years = self._get_relevant_years()

        # For hvert skoleår, find skoler der mangler faktura
        # Forankring invoices are per school year
        # Extra seats invoices are NOT per school year - only one needed ever
        missing = []
        schools_with_extra_seats_shown = set()  # Track schools already shown for extra seats

        for school_year in relevant_years:
            enrolled_schools = school_year.get_enrolled_schools()
            for school in enrolled_schools:
                # Check existing invoices for this school year
                invoices_for_year = school.invoices.filter(school_year=school_year)

                # Determine if school needs forankring invoice (per school year)
                is_forankring = school.enrolled_at and school.enrolled_at < school_year.start_date

                # Check if forankring invoice exists for this year
                has_forankring_invoice = invoices_for_year.exclude(comment__icontains="ekstra").exists()

                # Add missing forankring invoice
                if is_forankring and not has_forankring_invoice:
                    missing.append(
                        {
                            "school": school,
                            "school_year": school_year,
                            "invoice_type": "forankring",
                            "extra_seats": 0,
                        }
                    )

        # Check for extra seats separately (not per school year)
        # Only show once per school, for the current year
        current_year = relevant_years.first() if relevant_years else None
        if current_year:
            for school in current_year.get_enrolled_schools():
                extra_seats = max(0, school.used_seats - school.total_seats)
                if extra_seats > 0:
                    # Check if ANY extra seats invoice exists (across all years)
                    has_extra_seats_invoice = school.invoices.filter(
                        comment__icontains="ekstra"
                    ).exists()

                    if not has_extra_seats_invoice:
                        missing.append(
                            {
                                "school": school,
                                "school_year": current_year,
                                "invoice_type": "extra_seats",
                                "extra_seats": extra_seats,
                            }
                        )

        return missing

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["school_years"] = self._get_relevant_years()
        return context


@method_decorator(staff_required, name="dispatch")
class RegenerateCredentialsView(View):
    """Regenerate signup credentials for a school."""

    def post(self, request, pk):
        school = get_object_or_404(School, pk=pk)
        school.generate_credentials()
        messages.success(request, f'Nye tilmeldingsoplysninger genereret for "{school.name}".')
        return JsonResponse(
            {
                "success": True,
                "password": school.signup_password,
                "token": school.signup_token,
            }
        )


class SchoolPublicView(DetailView):
    """Public read-only view of school for token-based access."""

    model = School
    template_name = "schools/school_public.html"
    context_object_name = "school"
    slug_field = "signup_token"
    slug_url_kwarg = "token"

    def get_queryset(self):
        return School.objects.filter(signup_token__isnull=False).exclude(signup_token="")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.object
        context["people"] = school.people.all()
        context["course_signups"] = school.course_signups.select_related("course").order_by("-course__start_date")
        context["enrollment_history"] = school.get_enrollment_history()
        return context
