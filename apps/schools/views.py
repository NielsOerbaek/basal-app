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
from apps.courses.forms import CourseSignUpParticipantForm
from apps.courses.models import CourseSignUp
from apps.schools.consumption import get_consumption_overview

from .forms import EnrollmentDatesForm, PersonForm, SchoolCommentForm, SchoolFileForm, SchoolForm
from .mixins import SchoolFilterMixin
from .models import Person, School, SchoolComment, SchoolFile, SchoolYear


@method_decorator(staff_required, name="dispatch")
class KommuneListView(SortableMixin, ListView):
    template_name = "schools/kommune_list.html"
    context_object_name = "kommuner"
    sortable_fields = {
        "kommune": "kommune_name",
        "total": "total_schools",
        "enrolled": "enrolled_schools",
        "not_enrolled": "not_enrolled",
        "enrolled_kommunen_betaler": "enrolled_kommunen_betaler",
    }
    default_sort = "kommune"

    def get_base_queryset(self):
        return (
            School.objects.active()
            .exclude(kommune__isnull=True)
            .values(kommune_name=F("kommune__name"))
            .annotate(
                total_schools=Count("id"),
                enrolled_schools=Count("id", filter=Q(enrolled_at__isnull=False, opted_out_at__isnull=True)),
                not_enrolled=F("total_schools") - F("enrolled_schools"),
                enrolled_kommunen_betaler=Count(
                    "id",
                    filter=Q(
                        enrolled_at__isnull=False,
                        opted_out_at__isnull=True,
                        kommunen_betaler=True,
                    ),
                ),
            )
        )


@method_decorator(staff_required, name="dispatch")
class KommuneDetailView(SortableMixin, ListView):
    template_name = "schools/kommune_detail.html"
    context_object_name = "schools"
    sortable_fields = {
        "name": "name",
        "school_year": "active_from",
    }
    default_sort = "name"

    def get_base_queryset(self):
        return School.objects.active().filter(kommune__name=self.kwargs["kommune"]).prefetch_related("people")

    def _has_kommunen_betaler_school(self, kommune_name):
        return School.objects.filter(kommune__name=kommune_name, kommunen_betaler=True).exists()

    def get_context_data(self, **kwargs):
        from django.db.models import Count

        from apps.schools.forms import KommuneBillingForm
        from apps.schools.models import InstitutionstypeChoice, Kommune

        context = super().get_context_data(**kwargs)
        kommune_name = self.kwargs["kommune"]
        context["kommune"] = kommune_name
        context["kommune_obj"] = Kommune.objects.filter(name=kommune_name).first()
        context["has_kommunen_betaler"] = self._has_kommunen_betaler_school(kommune_name)
        context["billing_form"] = KommuneBillingForm(instance=context["kommune_obj"])

        # Stats
        qs = School.objects.active().filter(kommune__name=kommune_name)
        type_counts = dict(
            qs.values_list("institutionstype").annotate(c=Count("id")).values_list("institutionstype", "c")
        )
        labels = dict(InstitutionstypeChoice.choices)
        context["stats"] = {
            "total": qs.count(),
            "by_type": [
                (labels.get(code, code), type_counts.get(code, 0))
                for code in [
                    InstitutionstypeChoice.FOLKESKOLE,
                    InstitutionstypeChoice.FRISKOLE,
                    InstitutionstypeChoice.EFTERSKOLE,
                    InstitutionstypeChoice.FRISKOLE_EFTERSKOLE,
                ]
                if type_counts.get(code, 0) > 0
            ],
            "enrolled": qs.filter(enrolled_at__isnull=False, opted_out_at__isnull=True).count(),
            "enrolled_kommunen_betaler": qs.filter(
                enrolled_at__isnull=False,
                opted_out_at__isnull=True,
                kommunen_betaler=True,
            ).count(),
        }

        from apps.courses.models import CourseSignUp

        kursusdeltagere = (
            CourseSignUp.objects.filter(kommune__name=kommune_name)
            .select_related("course", "course__location")
            .order_by("-course__start_date", "participant_name")
        )
        context["kursusdeltagere"] = kursusdeltagere
        context["stats"]["kommune_participants_count"] = kursusdeltagere.count()
        return context

    def post(self, request, *args, **kwargs):
        from apps.schools.forms import KommuneBillingForm
        from apps.schools.models import Kommune

        kommune_name = kwargs["kommune"]
        kommune_obj, _ = Kommune.objects.get_or_create(name=kommune_name)
        form = KommuneBillingForm(request.POST, instance=kommune_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Faktureringsoplysninger for {kommune_name} er gemt.")
            return redirect("schools:kommune-detail", kommune=kommune_name)

        # Re-render with errors
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        context["billing_form"] = form
        return self.render_to_response(context)


@method_decorator(staff_required, name="dispatch")
class SchoolListView(SchoolFilterMixin, SortableMixin, ListView):
    model = School
    template_name = "schools/school_list.html"
    context_object_name = "schools"
    paginate_by = 25
    sortable_fields = {
        "name": "name",
        "kommune": "kommune",
        "school_year": "active_from",
        "seats": "_remaining_seats",  # Special handling for computed property
        "contact": "_last_contact",  # Special handling for latest contact
    }
    default_sort = "name"

    def get_base_queryset(self):
        """Return the base queryset before sorting."""
        return self.get_school_filter_queryset()

    def get_queryset(self):
        """Handle special sorting for computed fields."""
        sort, order = self.get_sort_params()
        queryset = self.get_base_queryset()

        # If queryset is already a list (from unused_seats filter), sort in Python
        if isinstance(queryset, list):
            reverse = order == "desc"
            if sort == "seats":
                queryset.sort(key=lambda s: s.used_seats, reverse=reverse)
            elif sort == "contact":

                def contact_key(s):
                    return getattr(s, "last_contact_date", None) or date.min

                queryset.sort(key=contact_key, reverse=reverse)
            elif sort == "name":
                queryset.sort(key=lambda s: s.name.lower(), reverse=reverse)
            elif sort == "kommune":
                queryset.sort(key=lambda s: (s.kommune.name if s.kommune else "").lower(), reverse=reverse)
            elif sort == "school_year":
                queryset.sort(key=lambda s: s.active_from or date.min, reverse=reverse)
            return queryset

        # For computed fields with Django QuerySet, convert to list and sort
        if sort in ("seats", "contact"):
            queryset = list(queryset)
            reverse = order == "desc"
            if sort == "seats":
                queryset.sort(key=lambda s: s.used_seats, reverse=reverse)
            elif sort == "contact":

                def contact_key(s):
                    return getattr(s, "last_contact_date", None) or date.min

                queryset.sort(key=contact_key, reverse=reverse)
            return queryset

        # Use default mixin sorting for other fields
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filter context from SchoolFilterMixin (kommuner, school_years, filter_summary, etc.)
        context.update(self.get_filter_context())

        # Metrics
        paginator = context.get("paginator")
        context["filtered_count"] = paginator.count if paginator else len(context.get("schools", []))
        context["enrolled_count"] = School.objects.filter(enrolled_at__isnull=False, opted_out_at__isnull=True).count()
        context["ever_enrolled_count"] = School.objects.filter(enrolled_at__isnull=False).count()

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
        from apps.schools.models import get_default_active_from, get_enrollment_cutoff_date
        from apps.schools.school_years import get_current_school_year

        context = super().get_context_data(**kwargs)
        # Resolve effective billing source: kommune row when "kommunen betaler",
        # else the school's own fakturering_* fields.
        if self.object.kommunen_betaler and self.object.kommune:
            if self.object.kommune.has_billing_info():
                context["billing_source"] = self.object.kommune
                context["billing_from_kommune"] = True
            else:
                context["billing_source"] = None
                context["billing_from_kommune"] = False
        else:
            context["billing_source"] = None
            context["billing_from_kommune"] = False
        context["kursusdeltagere"] = self.object.course_signups.select_related("course").order_by(
            "participant_name", "-course__start_date"
        )
        context["kontaktpersoner"] = self.object.people.all()
        context["school_comments"] = self.object.school_comments.select_related("created_by").all()
        context["enrollment_history"] = self.object.get_enrollment_history()
        context["person_form"] = PersonForm()
        context["comment_form"] = SchoolCommentForm()
        context["recent_activities"] = self.object.activity_logs.select_related("user", "content_type")[:5]
        context["today"] = date.today()
        context["school_files"] = self.object.files.select_related("uploaded_by").all()

        # Seat calculation context
        context["first_year_seats"] = self.object.get_first_year_seats()
        context["fortsaetter_seats"] = self.object.get_fortsaetter_seats()
        context["consumption_overview"] = get_consumption_overview(self.object)

        # Determine which bucket is "current"
        if self.object.active_from:
            try:
                current_year = get_current_school_year()
                first_year_name = self.object.get_first_school_year()
                context["is_in_first_year"] = current_year.name == first_year_name
                context["is_waiting_for_first_year"] = self.object.active_from > current_year.end_date
            except SchoolYear.DoesNotExist:
                context["is_in_first_year"] = False
                context["is_waiting_for_first_year"] = False

        # Enrollment cutoff info for modal
        try:
            current_sy = get_current_school_year()
            cutoff = get_enrollment_cutoff_date(current_sy)
            default_active_from = get_default_active_from()
            context["enrollment_cutoff"] = cutoff
            context["default_active_from"] = default_active_from
            context["is_past_cutoff"] = cutoff and date.today() > cutoff
            if context["is_past_cutoff"]:
                next_sy = SchoolYear.objects.filter(start_date__gt=current_sy.start_date).order_by("start_date").first()
                context["next_school_year"] = next_sy
        except Exception:
            context["is_past_cutoff"] = False

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

        from apps.schools.models import get_default_active_from

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
            # Set active_from: use enrollment date if in the future, otherwise use default logic
            default_active = get_default_active_from()
            school.active_from = max(enrollment_date, default_active)
            school.save(update_fields=["enrolled_at", "opted_out_at", "active_from"])
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
        warning_parts = []
        if signup_count:
            warning_parts.append(f"{signup_count} kursustilmelding{'er' if signup_count != 1 else ''}")
        if person_count:
            warning_parts.append(f"{person_count} person{'er' if person_count != 1 else ''}")
        if comment_count:
            warning_parts.append(f"{comment_count} kommentar{'er' if comment_count != 1 else ''}")
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
class SchoolExportView(SchoolFilterMixin, View):
    def get(self, request):
        from apps.schools.school_years import calculate_school_year_for_date

        queryset = self.get_school_filter_queryset()
        if not isinstance(queryset, list):
            queryset = list(queryset.order_by("name"))
        else:
            queryset.sort(key=lambda s: s.name.lower())
        for school in queryset:
            school._export_status = school.enrollment_status[1]
            school._export_school_year = (
                calculate_school_year_for_date(school.active_from) if school.active_from else ""
            )
            school._export_institutionstype = school.get_institutionstype_display()
            if school.enrolled_at and not school.opted_out_at:
                school._export_seats = f"{school.used_seats} / {school.total_seats}"
            else:
                school._export_seats = ""
        fields = [
            ("name", "Navn"),
            ("kommune", "Kommune"),
            ("_export_institutionstype", "Institutionstype"),
            ("_export_status", "Status"),
            ("_export_school_year", "Tilmeldt skoleår"),
            ("_export_seats", "Brugte pladser"),
        ]
        return export_queryset_to_excel(queryset, fields, "schools")


@method_decorator(staff_required, name="dispatch")
class SchoolAutocompleteView(View):
    def get(self, request):
        query = request.GET.get("q", "")
        schools = School.objects.active().filter(name__icontains=query)[:10]
        results = [{"id": s.pk, "name": s.name, "kommune": s.kommune.name if s.kommune else ""} for s in schools]
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
class CourseSignUpUpdateView(View):
    def get(self, request, school_pk, pk):
        school = get_object_or_404(School, pk=school_pk)
        signup = get_object_or_404(CourseSignUp, pk=pk, school=school)
        form = CourseSignUpParticipantForm(instance=signup)
        return render(
            request,
            "schools/signup_form.html",
            {
                "school": school,
                "signup": signup,
                "form": form,
            },
        )

    def post(self, request, school_pk, pk):
        school = get_object_or_404(School, pk=school_pk)
        signup = get_object_or_404(CourseSignUp, pk=pk, school=school)
        form = CourseSignUpParticipantForm(request.POST, instance=signup)
        if form.is_valid():
            form.save()
            messages.success(request, f'Kursusdeltageren "{signup.participant_name}" er opdateret.')
            return redirect("schools:detail", pk=school.pk)
        return render(
            request,
            "schools/signup_form.html",
            {
                "school": school,
                "signup": signup,
                "form": form,
            },
        )


@method_decorator(staff_required, name="dispatch")
class CourseSignUpDeleteView(View):
    def get(self, request, school_pk, pk):
        school = get_object_or_404(School, pk=school_pk)
        signup = get_object_or_404(CourseSignUp, pk=pk, school=school)
        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Slet kursusdeltagere",
                "message": format_html(
                    "Er du sikker på, at du vil slette <strong>{}</strong> fra {}?",
                    signup.participant_name,
                    signup.course.display_name,
                ),
                "delete_url": reverse_lazy("schools:signup-delete", kwargs={"school_pk": school_pk, "pk": pk}),
                "button_text": "Slet",
            },
        )

    def post(self, request, school_pk, pk):
        school = get_object_or_404(School, pk=school_pk)
        signup = get_object_or_404(CourseSignUp, pk=pk, school=school)
        participant_name = signup.participant_name
        signup.delete()
        messages.success(request, f'Kursusdeltageren "{participant_name}" er blevet slettet.')
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
class SchoolCommentEditView(View):
    def get(self, request, pk):
        comment = get_object_or_404(SchoolComment, pk=pk)
        form = SchoolCommentForm(instance=comment)
        return render(
            request,
            "schools/comment_form.html",
            {
                "school": comment.school,
                "form": form,
                "editing": True,
            },
        )

    def post(self, request, pk):
        comment = get_object_or_404(SchoolComment, pk=pk)
        form = SchoolCommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, "Kommentar opdateret.")
            return redirect("schools:detail", pk=comment.school.pk)
        return render(
            request,
            "schools/comment_form.html",
            {
                "school": comment.school,
                "form": form,
                "editing": True,
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


@method_decorator(staff_required, name="dispatch")
class ToggleDoNotContactView(View):
    """Toggle the do_not_contact_at flag for a school."""

    def post(self, request, pk):
        from django.utils import timezone

        school = get_object_or_404(School, pk=pk)
        if school.do_not_contact_at:
            school.do_not_contact_at = None
            messages.success(request, f'"{school.name}" kan nu kontaktes igen.')
        else:
            school.do_not_contact_at = timezone.now()
            messages.success(request, f'"{school.name}" er markeret som ønsker ikke kontakt.')
        school.save(update_fields=["do_not_contact_at", "updated_at"])
        return JsonResponse({"success": True})


@method_decorator(staff_required, name="dispatch")
class EditEnrollmentDatesView(View):
    """Edit enrollment dates (enrolled_at and active_from) for a school."""

    def get(self, request, pk):
        school = get_object_or_404(School, pk=pk)
        form = EnrollmentDatesForm(instance=school)
        return render(
            request,
            "schools/enrollment_dates_form.html",
            {"school": school, "form": form},
        )

    def post(self, request, pk):
        school = get_object_or_404(School, pk=pk)
        form = EnrollmentDatesForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, "Tilmeldingsdatoer opdateret.")
            return redirect("schools:detail", pk=school.pk)
        return render(
            request,
            "schools/enrollment_dates_form.html",
            {"school": school, "form": form},
        )


@method_decorator(staff_required, name="dispatch")
class DeleteEnrollmentHistoryView(View):
    """Delete an ActivityLog entry from the enrollment history."""

    def post(self, request, pk, log_id):
        from django.contrib.contenttypes.models import ContentType

        from apps.audit.models import ActivityLog

        school = get_object_or_404(School, pk=pk)
        school_ct = ContentType.objects.get_for_model(School)
        log = get_object_or_404(ActivityLog, pk=log_id, content_type=school_ct, object_id=school.pk)
        log.delete()
        messages.success(request, "Rækken er fjernet fra historikken.")
        return redirect("schools:detail", pk=pk)


@method_decorator(staff_required, name="dispatch")
class EditOptedOutDateView(View):
    """Edit the opted_out_at date for a school."""

    def post(self, request, pk):
        from datetime import datetime

        school = get_object_or_404(School, pk=pk)
        date_str = request.POST.get("date")

        try:
            new_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            messages.error(request, "Ugyldig dato.")
            return redirect("schools:detail", pk=pk)

        if not school.opted_out_at:
            messages.error(request, "Skolen er ikke frameldt.")
            return redirect("schools:detail", pk=pk)

        school.opted_out_at = new_date
        school.save(update_fields=["opted_out_at"])
        messages.success(request, f"Afmeldelsesdato ændret til {new_date.strftime('%d. %b %Y')}.")
        return redirect("schools:detail", pk=pk)


@method_decorator(staff_required, name="dispatch")
class ClearEnrollmentView(View):
    """Clear all enrollment dates (enrolled_at, active_from, opted_out_at) for a school."""

    def post(self, request, pk):
        school = get_object_or_404(School, pk=pk)
        school.enrolled_at = None
        school.active_from = None
        school.opted_out_at = None
        school.save(update_fields=["enrolled_at", "active_from", "opted_out_at"])
        messages.success(request, "Tilmeldingsdatoer nulstillet.")
        return redirect("schools:detail", pk=school.pk)


@method_decorator(staff_required, name="dispatch")
class SchoolFileCreateView(View):
    def get(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = SchoolFileForm()
        return render(
            request,
            "schools/file_form.html",
            {"school": school, "form": form},
        )

    def post(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = SchoolFileForm(request.POST, request.FILES)
        if form.is_valid():
            school_file = form.save(commit=False)
            school_file.school = school
            school_file.uploaded_by = request.user
            school_file.save()
            messages.success(request, f'Filen "{school_file.filename}" blev uploadet.')
            return redirect("schools:detail", pk=school.pk)
        return render(
            request,
            "schools/file_form.html",
            {"school": school, "form": form},
        )


@method_decorator(staff_required, name="dispatch")
class SchoolFileEditView(View):
    def get(self, request, pk):
        school_file = get_object_or_404(SchoolFile, pk=pk)
        form = SchoolFileForm(instance=school_file)
        return render(
            request,
            "schools/file_form.html",
            {"school": school_file.school, "form": form, "editing": True},
        )

    def post(self, request, pk):
        school_file = get_object_or_404(SchoolFile, pk=pk)
        form = SchoolFileForm(request.POST, request.FILES, instance=school_file)
        if form.is_valid():
            form.save()
            messages.success(request, f'Filen "{school_file.filename}" blev opdateret.')
            return redirect("schools:detail", pk=school_file.school.pk)
        return render(
            request,
            "schools/file_form.html",
            {"school": school_file.school, "form": form, "editing": True},
        )


@method_decorator(staff_required, name="dispatch")
class SchoolFileDeleteView(View):
    def get(self, request, pk):
        school_file = get_object_or_404(SchoolFile, pk=pk)
        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Slet fil",
                "message": format_html("Er du sikker på, at du vil slette <strong>{}</strong>?", school_file.filename),
                "delete_url": reverse_lazy("schools:file-delete", kwargs={"pk": pk}),
                "button_text": "Slet",
            },
        )

    def post(self, request, pk):
        school_file = get_object_or_404(SchoolFile, pk=pk)
        school_pk = school_file.school.pk
        filename = school_file.filename
        school_file.file.delete()  # Delete actual file
        school_file.delete()
        messages.success(request, f'Filen "{filename}" er blevet slettet.')
        return JsonResponse(
            {"success": True, "redirect": str(reverse_lazy("schools:detail", kwargs={"pk": school_pk}))}
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

        # Kontaktpersoner - simple list, no email matching
        context["kontaktpersoner"] = school.people.all()

        # Kursusdeltagere - all signups, one per row
        context["kursusdeltagere"] = school.course_signups.select_related("course", "course__location").order_by(
            "participant_name", "-course__start_date"
        )

        context["enrollment_history"] = school.get_enrollment_history()

        # Seat calculation context
        context["first_year_seats"] = school.get_first_year_seats()
        context["fortsaetter_seats"] = school.get_fortsaetter_seats()
        context["consumption_overview"] = get_consumption_overview(school)

        if school.active_from:
            from apps.schools.models import SchoolYear
            from apps.schools.school_years import get_current_school_year

            try:
                current_year = get_current_school_year()
                first_year_name = school.get_first_school_year()
                context["is_in_first_year"] = current_year.name == first_year_name
                context["is_waiting_for_first_year"] = school.active_from > current_year.end_date
            except SchoolYear.DoesNotExist:
                context["is_in_first_year"] = False
                context["is_waiting_for_first_year"] = False

        # Global site settings (samarbejdsvilkår + login info)
        from apps.core.models import ProjectSettings

        site_settings = ProjectSettings.get()
        context["site_settings"] = site_settings

        # Courses with materials (newest first)
        from apps.courses.models import Course

        course_ids = context["kursusdeltagere"].values_list("course_id", flat=True).distinct()
        courses_with_materials = (
            Course.objects.filter(pk__in=course_ids, course_materials__isnull=False)
            .prefetch_related("course_materials")
            .distinct()
            .order_by("-start_date")
        )

        context["courses_with_materials"] = courses_with_materials

        return context


class PublicPersonCreateView(View):
    """Public view for adding a person to a school via token."""

    def get_school(self, token):
        return get_object_or_404(
            School.objects.filter(signup_token__isnull=False).exclude(signup_token=""),
            signup_token=token,
        )

    def get(self, request, token):
        school = self.get_school(token)
        form = PersonForm()
        return render(
            request,
            "schools/public_person_form.html",
            {"school": school, "form": form},
        )

    def post(self, request, token):
        school = self.get_school(token)
        form = PersonForm(request.POST)
        if form.is_valid():
            person = form.save(commit=False)
            person.school = school
            person.save()
            messages.success(request, f'Person "{person.name}" tilføjet.')
            return redirect("school-public", token=token)
        return render(
            request,
            "schools/public_person_form.html",
            {"school": school, "form": form},
        )


class PublicPersonUpdateView(View):
    """Public view for editing a person via token."""

    def get_school_and_person(self, token, pk):
        school = get_object_or_404(
            School.objects.filter(signup_token__isnull=False).exclude(signup_token=""),
            signup_token=token,
        )
        person = get_object_or_404(Person, pk=pk, school=school)
        return school, person

    def get(self, request, token, pk):
        school, person = self.get_school_and_person(token, pk)
        form = PersonForm(instance=person)
        return render(
            request,
            "schools/public_person_form.html",
            {"school": school, "form": form, "person": person},
        )

    def post(self, request, token, pk):
        school, person = self.get_school_and_person(token, pk)
        form = PersonForm(request.POST, instance=person)
        if form.is_valid():
            form.save()
            messages.success(request, f'Person "{person.name}" opdateret.')
            return redirect("school-public", token=token)
        return render(
            request,
            "schools/public_person_form.html",
            {"school": school, "form": form, "person": person},
        )


class PublicPersonDeleteView(View):
    """Public view for deleting a person via token."""

    def get_school_and_person(self, token, pk):
        school = get_object_or_404(
            School.objects.filter(signup_token__isnull=False).exclude(signup_token=""),
            signup_token=token,
        )
        person = get_object_or_404(Person, pk=pk, school=school)
        return school, person

    def get(self, request, token, pk):
        school, person = self.get_school_and_person(token, pk)
        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Slet person",
                "message": format_html("Er du sikker på, at du vil slette <strong>{}</strong>?", person.name),
                "delete_url": reverse_lazy("school-public-person-delete", kwargs={"token": token, "pk": pk}),
                "button_text": "Slet",
            },
        )

    def post(self, request, token, pk):
        school, person = self.get_school_and_person(token, pk)
        person_name = person.name
        person.delete()
        messages.success(request, f'Person "{person_name}" er blevet slettet.')
        return JsonResponse({"success": True, "redirect": str(reverse_lazy("school-public", kwargs={"token": token}))})


class PublicCourseSignUpUpdateView(View):
    """Public view for editing a course signup's participant details via token."""

    def get_school_and_signup(self, token, pk):
        school = get_object_or_404(
            School.objects.filter(signup_token__isnull=False).exclude(signup_token=""),
            signup_token=token,
        )
        signup = get_object_or_404(CourseSignUp, pk=pk, school=school)
        return school, signup

    def get(self, request, token, pk):
        school, signup = self.get_school_and_signup(token, pk)
        form = CourseSignUpParticipantForm(instance=signup)
        return render(
            request,
            "schools/public_signup_form.html",
            {"school": school, "signup": signup, "form": form},
        )

    def post(self, request, token, pk):
        school, signup = self.get_school_and_signup(token, pk)
        form = CourseSignUpParticipantForm(request.POST, instance=signup)
        if form.is_valid():
            form.save()
            messages.success(request, f'Kursusdeltageren "{signup.participant_name}" er opdateret.')
            return redirect("school-public", token=token)
        return render(
            request,
            "schools/public_signup_form.html",
            {"school": school, "signup": signup, "form": form},
        )
