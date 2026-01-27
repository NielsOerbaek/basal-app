from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.core.decorators import staff_required
from apps.core.export import export_queryset_to_excel
from apps.core.mixins import SortableMixin

from .forms import CourseForm, CourseMaterialForm, CourseSignUpForm, PublicSignUpForm
from .models import AttendanceStatus, Course, CourseMaterial, CourseSignUp


@method_decorator(staff_required, name="dispatch")
class CourseListView(SortableMixin, ListView):
    model = Course
    template_name = "courses/course_list.html"
    context_object_name = "courses"
    paginate_by = 25
    sortable_fields = {
        "date": "start_date",
        "location": "location__name",
    }
    default_sort = "date"
    default_order = "desc"

    def get_base_queryset(self):
        queryset = Course.objects.select_related("location").prefetch_related("instructors")
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(Q(location__name__icontains=search))

        # School year filter (for project goals drill-down)
        school_year_filter = self.request.GET.get("school_year")
        if school_year_filter:
            from apps.goals.calculations import get_school_year_dates

            # Convert school_year from URL format (2024-25) to internal format (2024/25)
            year_str = school_year_filter.replace("-", "/")
            start_date, end_date = get_school_year_dates(year_str)
            queryset = queryset.filter(start_date__gte=start_date, start_date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Build filter explanation for project goals drill-down
        school_year = self.request.GET.get("school_year")
        if school_year:
            year_display = school_year.replace("-", "/")
            context["filter_explanation"] = f"Viser kurser i skoleåret {year_display}"

        return context


@method_decorator(staff_required, name="dispatch")
class CourseCreateView(CreateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/course_form.html"
    success_url = reverse_lazy("courses:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Kurset "{self.object.display_name}" blev oprettet.')
        return response


@method_decorator(staff_required, name="dispatch")
class CourseDetailView(DetailView):
    model = Course
    template_name = "courses/course_detail.html"
    context_object_name = "course"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["signups"] = self.object.signups.select_related("school").all()
        context["course_materials"] = self.object.course_materials.all()
        context["recent_activities"] = self.object.activity_logs.select_related("user", "content_type")[:5]
        return context


@method_decorator(staff_required, name="dispatch")
class CourseUpdateView(UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/course_form.html"

    def get_success_url(self):
        return reverse_lazy("courses:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Kurset "{self.object.display_name}" blev opdateret.')
        return response


@method_decorator(staff_required, name="dispatch")
class CourseDeleteView(View):
    def get(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        signup_count = course.signups.count()
        material_count = course.course_materials.count()

        warning_parts = []
        if signup_count:
            warning_parts.append(f"{signup_count} tilmelding{'er' if signup_count != 1 else ''}")
        if material_count:
            warning_parts.append(f"{material_count} materiale{'r' if material_count != 1 else ''}")

        if warning_parts:
            warning = f"Dette vil permanent slette: {', '.join(warning_parts)}. Handlingen kan ikke fortrydes!"
        else:
            warning = "Handlingen kan ikke fortrydes!"

        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Slet kursus permanent",
                "message": format_html(
                    "Er du sikker på, at du vil <strong>permanent slette</strong> kurset <strong>{}</strong>?",
                    course.display_name,
                ),
                "warning": warning,
                "delete_url": reverse_lazy("courses:delete", kwargs={"pk": pk}),
                "button_text": "Slet permanent",
            },
        )

    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        course_name = course.display_name
        course.delete()
        messages.success(request, f'Kurset "{course_name}" er blevet permanent slettet.')
        return JsonResponse({"success": True, "redirect": str(reverse_lazy("courses:list"))})


@method_decorator(staff_required, name="dispatch")
class CourseExportView(View):
    def get(self, request):
        queryset = Course.objects.select_related("location").all()
        fields = [
            ("display_name", "Kursus"),
            ("start_date", "Startdato"),
            ("end_date", "Slutdato"),
            ("location", "Lokation"),
            ("capacity", "Kapacitet"),
            ("signup_count", "Tilmeldinger"),
            ("is_published", "Offentliggjort"),
        ]
        return export_queryset_to_excel(queryset, fields, "courses")


@method_decorator(staff_required, name="dispatch")
class SignUpListView(ListView):
    model = CourseSignUp
    template_name = "courses/signup_list.html"
    context_object_name = "signups"
    paginate_by = 25

    def get_queryset(self):
        queryset = CourseSignUp.objects.select_related("school", "course")
        course_id = self.request.GET.get("course")
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(Q(participant_name__icontains=search) | Q(school__name__icontains=search))

        # School year filter (for project goals drill-down)
        school_year_filter = self.request.GET.get("school_year")
        if school_year_filter:
            from apps.goals.calculations import get_school_year_dates

            # Convert school_year from URL format (2024-25) to internal format (2024/25)
            year_str = school_year_filter.replace("-", "/")
            start_date, end_date = get_school_year_dates(year_str)
            queryset = queryset.filter(course__start_date__gte=start_date, course__start_date__lte=end_date)

        # Attendance filter (for project goals drill-down)
        attended_filter = self.request.GET.get("attended")
        if attended_filter == "true":
            queryset = queryset.filter(attendance=AttendanceStatus.PRESENT)

        # Teacher filter (for project goals drill-down)
        is_underviser_filter = self.request.GET.get("is_underviser")
        if is_underviser_filter == "true":
            queryset = queryset.filter(is_underviser=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["courses"] = Course.objects.all()

        # Build filter explanation for project goals drill-down
        school_year = self.request.GET.get("school_year")
        attended = self.request.GET.get("attended")
        is_underviser = self.request.GET.get("is_underviser")

        if school_year:
            year_display = school_year.replace("-", "/")
            parts = []

            if attended == "true" and is_underviser == "true":
                parts.append("undervisere der deltog i kurser")
            elif attended == "true":
                parts.append("deltagere der deltog i kurser")
            elif is_underviser == "true":
                parts.append("undervisere tilmeldt kurser")
            else:
                parts.append("tilmeldinger til kurser")

            context["filter_explanation"] = f"Viser {parts[0]} i skoleåret {year_display}"

        return context


@method_decorator(staff_required, name="dispatch")
class SignUpExportView(View):
    def get(self, request):
        queryset = CourseSignUp.objects.select_related("school", "course")
        course_id = request.GET.get("course")
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        fields = [
            ("course", "Kursus"),
            ("school", "Skole"),
            ("participant_name", "Deltager"),
            ("participant_title", "Titel"),
            ("attendance", "Fremmøde"),
            ("created_at", "Tilmeldt"),
        ]
        return export_queryset_to_excel(queryset, fields, "signups")


@method_decorator(staff_required, name="dispatch")
class RollCallView(DetailView):
    model = Course
    template_name = "courses/rollcall.html"
    context_object_name = "course"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        signups = self.object.signups.select_related("school").order_by("school__name", "participant_name")
        context["signups"] = signups
        context["total"] = signups.count()
        context["present"] = signups.filter(attendance=AttendanceStatus.PRESENT).count()
        context["absent"] = signups.filter(attendance=AttendanceStatus.ABSENT).count()
        context["unmarked"] = signups.filter(attendance=AttendanceStatus.UNMARKED).count()
        return context


@method_decorator(staff_required, name="dispatch")
class MarkAttendanceView(View):
    def post(self, request, pk):
        signup = get_object_or_404(CourseSignUp, pk=pk)
        attendance = request.POST.get("attendance")
        if attendance in [choice[0] for choice in AttendanceStatus.choices]:
            signup.attendance = attendance
            signup.save()
        return render(request, "courses/partials/rollcall_row.html", {"signup": signup})


@method_decorator(staff_required, name="dispatch")
class SignUpUpdateView(UpdateView):
    model = CourseSignUp
    form_class = CourseSignUpForm
    template_name = "courses/signup_form.html"

    def get_success_url(self):
        return reverse("courses:detail", kwargs={"pk": self.object.course.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.object.course
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Tilmeldingen for {self.object.participant_name} blev opdateret.")
        return response


@method_decorator(staff_required, name="dispatch")
class SignUpDeleteView(View):
    def get(self, request, pk):
        signup = get_object_or_404(CourseSignUp, pk=pk)
        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Slet tilmelding",
                "message": format_html(
                    "Er du sikker på, at du vil slette tilmeldingen for <strong>{}</strong>?", signup.participant_name
                ),
                "delete_url": reverse("courses:signup-delete", kwargs={"pk": pk}),
            },
        )

    def post(self, request, pk):
        signup = get_object_or_404(CourseSignUp, pk=pk)
        course_pk = signup.course.pk
        signup.delete()
        messages.success(request, "Tilmeldingen er blevet slettet.")
        return JsonResponse({"success": True, "redirect": reverse("courses:detail", kwargs={"pk": course_pk})})


class PublicSignUpView(View):
    template_name = "courses/public_signup.html"

    def get(self, request):
        form = PublicSignUpForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = PublicSignUpForm(request.POST)
        if form.is_valid():
            signup = CourseSignUp.objects.create(
                course=form.cleaned_data["course"],
                school=form.cleaned_data["school"],
                participant_name=form.cleaned_data["participant_name"],
                participant_email=form.cleaned_data["participant_email"],
                participant_phone=form.cleaned_data.get("participant_phone", ""),
                participant_title=form.cleaned_data.get("participant_title", ""),
                is_underviser=form.cleaned_data.get("is_underviser", True),
            )
            # Send confirmation email
            from apps.emails.services import send_signup_confirmation

            send_signup_confirmation(signup)

            return redirect("signup-success")

        return render(request, self.template_name, {"form": form})


class SignUpSuccessView(TemplateView):
    template_name = "courses/signup_success.html"


class CheckSchoolSeatsView(View):
    """AJAX endpoint to check if a school has available seats."""

    def get(self, request):
        from apps.schools.models import School

        school_id = request.GET.get("school_id")
        if not school_id:
            return JsonResponse({"error": "Missing school_id"}, status=400)
        try:
            school = School.objects.get(pk=school_id)
            return JsonResponse(
                {
                    "has_available_seats": school.has_available_seats,
                    "remaining_seats": school.remaining_seats,
                }
            )
        except School.DoesNotExist:
            return JsonResponse({"error": "School not found"}, status=404)


@method_decorator(staff_required, name="dispatch")
class BulkImportView(View):
    """Bulk import signups by pasting from Excel."""

    def get(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        return render(request, "courses/bulk_import_modal.html", {"course": course})

    def post(self, request, pk):
        from apps.schools.models import School

        course = get_object_or_404(Course, pk=pk)
        raw_data = request.POST.get("data", "")

        # Parse pasted data (tab-separated: first_name, last_name, phone, email, school, is_underviser)
        rows = []
        lines = raw_data.strip().split("\n")

        for i, line in enumerate(lines):
            if not line.strip():
                continue

            # Split by tab (Excel default) or multiple spaces
            parts = line.split("\t")
            if len(parts) < 3:
                parts = [p.strip() for p in line.split("  ") if p.strip()]

            if len(parts) < 3:
                continue

            first_name = parts[0].strip()
            last_name = parts[1].strip() if len(parts) > 1 else ""
            phone = parts[2].strip() if len(parts) > 2 else ""
            email = parts[3].strip() if len(parts) > 3 else ""
            school_name = parts[4].strip() if len(parts) > 4 else ""
            is_underviser_str = parts[5].strip().lower() if len(parts) > 5 else ""

            # Parse is_underviser (default True)
            is_underviser = is_underviser_str not in ["0", "false", "nej", "no", "n"]

            # Combine first and last name
            name = f"{first_name} {last_name}".strip()

            if not name or not school_name:
                continue

            # Find matching schools (handle "School, Municipality" format)
            # Extract school name before comma for matching, but keep original for display
            if "," in school_name:
                parts_split = school_name.split(",", 1)
                school_search_term = parts_split[0].strip()
                kommune_guess = parts_split[1].strip() if len(parts_split) > 1 else ""
                # Remove "Kommune" suffix if present for cleaner display
                if kommune_guess.lower().endswith(" kommune"):
                    kommune_guess = kommune_guess[:-8].strip()
            else:
                school_search_term = school_name
                kommune_guess = ""

            matches = self._find_school_matches(school_search_term, school_name)

            # Check for exact match (either full name or school name without municipality)
            exact_match = None
            if matches:
                first_match_lower = matches[0].name.lower()
                if first_match_lower == school_name.lower() or first_match_lower == school_search_term.lower():
                    exact_match = matches[0]

            rows.append(
                {
                    "index": len(rows),
                    "name": name,
                    "school_name": school_name,
                    "school_search_term": school_search_term,
                    "kommune_guess": kommune_guess,
                    "email": email,
                    "phone": phone,
                    "is_underviser": is_underviser,
                    "matches": matches,
                    "exact_match": exact_match,
                }
            )

        if not rows:
            messages.error(
                request,
                "Ingen gyldige rækker fundet. Forventet format: Fornavn, Efternavn, Tlf., Mail, Skole, Underviser (tab-separeret)",
            )
            return render(request, "courses/bulk_import_modal.html", {"course": course})

        # Get all schools for fallback dropdown
        all_schools = School.objects.active().order_by("name")

        return render(
            request,
            "courses/bulk_import_match.html",
            {
                "course": course,
                "rows": rows,
                "all_schools": all_schools,
            },
        )

    def _find_school_matches(self, search_term, original_name=None):
        from apps.schools.models import School

        if not search_term:
            return []

        # Try exact match first with the search term (school name without municipality)
        exact = School.objects.active().filter(name__iexact=search_term).first()
        if exact:
            return [exact]

        # Also try with original name if different (in case DB has full "School, Municipality" format)
        if original_name and original_name != search_term:
            exact = School.objects.active().filter(name__iexact=original_name).first()
            if exact:
                return [exact]

        # Find schools containing the search term
        contains = list(School.objects.active().filter(name__icontains=search_term)[:5])

        # Find schools where search term contains school name
        if len(contains) < 5:
            all_schools = School.objects.active()
            for school in all_schools:
                if school.name.lower() in search_term.lower() and school not in contains:
                    contains.append(school)
                    if len(contains) >= 5:
                        break

        # Sort by name length similarity
        contains.sort(key=lambda s: abs(len(s.name) - len(search_term)))

        return contains[:5]


@method_decorator(staff_required, name="dispatch")
class BulkImportConfirmView(View):
    """Process confirmed bulk import."""

    def post(self, request, pk):
        from apps.schools.models import School

        course = get_object_or_404(Course, pk=pk)

        # Get form data
        count = int(request.POST.get("count", 0))
        created = 0
        skipped = 0
        schools_created = 0
        errors = []

        for i in range(count):
            school_id = request.POST.get(f"school_{i}")
            name = request.POST.get(f"name_{i}")
            email = request.POST.get(f"email_{i}", "")
            phone = request.POST.get(f"phone_{i}", "")
            is_underviser = f"is_underviser_{i}" in request.POST

            if not school_id or school_id == "skip":
                skipped += 1
                continue

            try:
                school = None
                other_organization = ""

                if school_id == "other":
                    # Use other organization field
                    other_organization = request.POST.get(f"other_org_{i}", "").strip()
                    if not other_organization:
                        errors.append(f"{name}: Angiv venligst navn på organisation")
                        continue

                    # Check for duplicate (by name and other_organization)
                    if CourseSignUp.objects.filter(
                        course=course, school__isnull=True, other_organization=other_organization, participant_name=name
                    ).exists():
                        errors.append(f"{name} ({other_organization}) er allerede tilmeldt")
                        continue

                elif school_id == "new_school":
                    # Create new school
                    new_school_name = request.POST.get(f"new_school_name_{i}", "").strip()
                    new_school_kommune = request.POST.get(f"new_school_kommune_{i}", "").strip()

                    if not new_school_name or not new_school_kommune:
                        errors.append(f"{name}: Angiv venligst både skolenavn og kommune")
                        continue

                    # Check if school already exists
                    existing = School.objects.filter(name__iexact=new_school_name, kommune__iexact=new_school_kommune).first()
                    if existing:
                        school = existing
                    else:
                        # Create new school with placeholder address
                        school = School.objects.create(
                            name=new_school_name,
                            kommune=new_school_kommune,
                            adresse="(ikke angivet)",
                        )
                        schools_created += 1

                    # Check for duplicate
                    if CourseSignUp.objects.filter(course=course, school=school, participant_name=name).exists():
                        errors.append(f"{name} ({school.name}) er allerede tilmeldt")
                        continue

                else:
                    # Regular school selection
                    school = School.objects.get(pk=school_id)

                    # Check for duplicate
                    if CourseSignUp.objects.filter(course=course, school=school, participant_name=name).exists():
                        errors.append(f"{name} ({school.name}) er allerede tilmeldt")
                        continue

                CourseSignUp.objects.create(
                    course=course,
                    school=school,
                    other_organization=other_organization,
                    participant_name=name,
                    participant_email=email,
                    participant_phone=phone,
                    is_underviser=is_underviser,
                )
                created += 1

            except School.DoesNotExist:
                errors.append(f"Skole ikke fundet for {name}")
            except Exception as e:
                errors.append(f"Fejl ved oprettelse af {name}: {str(e)}")

        # Build result message
        msg_parts = []
        if created:
            msg_parts.append(f'{created} tilmelding{"er" if created != 1 else ""} oprettet')
        if schools_created:
            msg_parts.append(f'{schools_created} ny{"e" if schools_created != 1 else ""} skole{"r" if schools_created != 1 else ""} oprettet')
        if skipped:
            msg_parts.append(f"{skipped} sprunget over")
        if errors:
            msg_parts.append(f"{len(errors)} fejl")

        if created:
            messages.success(request, ". ".join(msg_parts) + ".")
        elif errors:
            messages.error(request, ". ".join(msg_parts) + ".")
        else:
            messages.warning(request, "Ingen tilmeldinger oprettet.")

        if errors:
            for error in errors[:5]:  # Show max 5 errors
                messages.warning(request, error)

        return redirect("courses:detail", pk=course.pk)


@method_decorator(staff_required, name="dispatch")
class CourseMaterialCreateView(View):
    def get(self, request, course_pk):
        course = get_object_or_404(Course, pk=course_pk)
        form = CourseMaterialForm()
        return render(
            request,
            "courses/material_form.html",
            {
                "course": course,
                "form": form,
            },
        )

    def post(self, request, course_pk):
        course = get_object_or_404(Course, pk=course_pk)
        form = CourseMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.course = course
            material.save()
            messages.success(request, "Kursusmateriale tilføjet.")
            return redirect("courses:detail", pk=course.pk)
        return render(
            request,
            "courses/material_form.html",
            {
                "course": course,
                "form": form,
            },
        )


@method_decorator(staff_required, name="dispatch")
class CourseMaterialDeleteView(View):
    def get(self, request, pk):
        material = get_object_or_404(CourseMaterial, pk=pk)
        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Slet kursusmateriale",
                "message": format_html("Er du sikker på, at du vil slette <strong>{}</strong>?", material.display_name),
                "delete_url": reverse("courses:material-delete", kwargs={"pk": pk}),
            },
        )

    def post(self, request, pk):
        material = get_object_or_404(CourseMaterial, pk=pk)
        course_pk = material.course.pk
        material.delete()
        messages.success(request, "Kursusmateriale er blevet slettet.")
        return JsonResponse({"success": True, "redirect": reverse("courses:detail", kwargs={"pk": course_pk})})
