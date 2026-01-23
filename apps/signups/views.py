from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.courses.models import CourseSignUp
from apps.schools.models import School

from .forms import CourseSignupForm, SchoolSignupForm
from .models import SignupPage, SignupPageType


class SignupPageMixin:
    """Mixin that provides signup page context."""

    page_type = None

    def get_signup_page(self):
        try:
            return SignupPage.objects.get(page_type=self.page_type)
        except SignupPage.DoesNotExist:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page"] = self.get_signup_page()
        return context


class CourseSignupView(View):
    """Public course signup form with authentication."""

    template_name = "signups/course_signup.html"

    def get_signup_page(self):
        try:
            return SignupPage.objects.prefetch_related("form_fields").get(page_type=SignupPageType.COURSE_SIGNUP)
        except SignupPage.DoesNotExist:
            return None

    def get_auth_context(self, request):
        """Determine authentication state and return context."""
        # Check if user wants to clear session and switch schools
        if request.GET.get("clear") == "1":
            if "course_signup_school_id" in request.session:
                del request.session["course_signup_school_id"]

        # Staff bypass - full access
        if request.user.is_authenticated and request.user.is_staff:
            return {
                "auth_mode": "staff",
                "locked_school": None,
                "show_password_form": False,
                "auth_error": None,
            }

        # Check for token in URL
        token = request.GET.get("token", "").strip()
        if token:
            try:
                school = School.objects.get(
                    signup_token=token,
                    enrolled_at__isnull=False,
                    opted_out_at__isnull=True,
                )
                request.session["course_signup_school_id"] = school.pk
                return {
                    "auth_mode": "token",
                    "locked_school": school,
                    "show_password_form": False,
                    "auth_error": None,
                }
            except School.DoesNotExist:
                return {
                    "auth_mode": None,
                    "locked_school": None,
                    "show_password_form": True,
                    "auth_error": "Ugyldigt link. Brug venligst koden fra jeres velkomstmail.",
                }

        # Check session
        school_id = request.session.get("course_signup_school_id")
        if school_id:
            try:
                school = School.objects.get(
                    pk=school_id,
                    enrolled_at__isnull=False,
                    opted_out_at__isnull=True,
                )
                return {
                    "auth_mode": "session",
                    "locked_school": school,
                    "show_password_form": False,
                    "auth_error": None,
                }
            except School.DoesNotExist:
                del request.session["course_signup_school_id"]

        # Not authenticated
        return {
            "auth_mode": None,
            "locked_school": None,
            "show_password_form": True,
            "auth_error": None,
        }

    def get(self, request):
        page = self.get_signup_page()
        if page and not page.is_active:
            return render(request, "signups/page_unavailable.html", {"page": page})

        auth_context = self.get_auth_context(request)
        form = CourseSignupForm(signup_page=page, locked_school=auth_context.get("locked_school"))

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "page": page,
                **auth_context,
            },
        )

    def post(self, request):
        page = self.get_signup_page()
        if page and not page.is_active:
            return render(request, "signups/page_unavailable.html", {"page": page})

        auth_context = self.get_auth_context(request)

        # Must be authenticated to submit
        if auth_context["show_password_form"] and not auth_context["locked_school"]:
            return render(
                request,
                self.template_name,
                {
                    "form": CourseSignupForm(signup_page=page),
                    "page": page,
                    **auth_context,
                    "auth_error": "Indtast venligst jeres skolekode først.",
                },
            )

        form = CourseSignupForm(
            request.POST, request.FILES, signup_page=page, locked_school=auth_context.get("locked_school")
        )

        # Extract participant data from POST (participant fields are not in the form)
        participants = self._extract_participants(request.POST)

        # Validate we have at least one participant
        if not participants:
            return render(
                request,
                self.template_name,
                {"form": form, "page": page, "participant_error": "Mindst én deltager er påkrævet.", **auth_context},
            )

        # Validate all participants have required fields
        for i, p in enumerate(participants):
            if not p.get("name") or not p.get("email"):
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "page": page,
                        "participant_error": f"Deltager {i + 1} mangler navn eller e-mail.",
                        **auth_context,
                    },
                )

        if form.is_valid():
            from apps.emails.services import send_signup_confirmation

            course = form.cleaned_data["course"]
            school = form.cleaned_data["school"]

            # Create a signup for each participant
            for participant in participants:
                signup = CourseSignUp.objects.create(
                    course=course,
                    school=school,
                    participant_name=participant["name"],
                    participant_email=participant["email"],
                    participant_title=participant.get("title", ""),
                    is_underviser=participant.get("is_underviser", True),
                )
                # Send confirmation email to each participant
                send_signup_confirmation(signup)

            return redirect("signup:course-success")

        return render(request, self.template_name, {"form": form, "page": page, **auth_context})

    def _extract_participants(self, post_data):
        """Extract participant data from POST data with indexed field names."""
        participants = []
        index = 0

        while True:
            name_key = f"participant_name_{index}"
            email_key = f"participant_email_{index}"
            title_key = f"participant_title_{index}"
            is_underviser_key = f"participant_is_underviser_{index}"

            if name_key not in post_data:
                break

            name = post_data.get(name_key, "").strip()
            email = post_data.get(email_key, "").strip()
            title = post_data.get(title_key, "").strip()
            # Checkbox: present in POST if checked, absent if not checked
            is_underviser = is_underviser_key in post_data

            # Only add if at least name or email is provided
            if name or email:
                participants.append(
                    {
                        "name": name,
                        "email": email,
                        "title": title,
                        "is_underviser": is_underviser,
                    }
                )

            index += 1

        return participants


class CourseSignupSuccessView(TemplateView):
    """Course signup success page."""

    template_name = "signups/course_signup_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["page"] = SignupPage.objects.get(page_type=SignupPageType.COURSE_SIGNUP)
        except SignupPage.DoesNotExist:
            context["page"] = None
        return context


class CheckSchoolSeatsView(View):
    """AJAX endpoint to check if a school has available seats."""

    def get(self, request):
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


class CheckCourseSeatsView(View):
    """AJAX endpoint to check available seats on a course."""

    def get(self, request):
        from apps.courses.models import Course

        course_id = request.GET.get("course_id")
        if not course_id:
            return JsonResponse({"error": "Missing course_id"}, status=400)
        try:
            course = Course.objects.get(pk=course_id)
            # Format date string
            if course.start_date == course.end_date:
                date_str = course.start_date.strftime("%-d. %b %Y")
            else:
                date_str = f"{course.start_date.strftime('%-d. %b')} - {course.end_date.strftime('%-d. %b %Y')}"

            return JsonResponse(
                {
                    "capacity": course.capacity,
                    "signup_count": course.signup_count,
                    "available_seats": course.spots_remaining,
                    "is_full": course.is_full,
                    "title": course.title,
                    "date": date_str,
                    "location": course.location,
                    "undervisere": course.undervisere or "",
                }
            )
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)


class SchoolSignupView(View):
    """School signup form for joining the Basal project."""

    template_name = "signups/school_signup.html"

    def get_signup_page(self):
        try:
            return SignupPage.objects.prefetch_related("form_fields").get(page_type=SignupPageType.SCHOOL_SIGNUP)
        except SignupPage.DoesNotExist:
            return None

    def get(self, request):
        page = self.get_signup_page()
        if page and not page.is_active:
            return render(request, "signups/page_unavailable.html", {"page": page})

        form = SchoolSignupForm(signup_page=page)
        return render(request, self.template_name, {"form": form, "page": page})

    def post(self, request):
        from datetime import date

        from apps.emails.services import send_school_enrollment_confirmation, send_school_signup_notifications
        from apps.schools.models import Person, PersonRole

        page = self.get_signup_page()
        if page and not page.is_active:
            return render(request, "signups/page_unavailable.html", {"page": page})

        form = SchoolSignupForm(request.POST, request.FILES, signup_page=page)
        if form.is_valid():
            contact_name = form.cleaned_data["contact_name"]
            contact_email = form.cleaned_data["contact_email"]
            municipality = form.cleaned_data["municipality"]

            if form.cleaned_data.get("school_not_listed"):
                # Create new school
                school = School.objects.create(
                    name=form.cleaned_data["new_school_name"],
                    adresse=form.cleaned_data.get("new_school_address", ""),
                    kommune=municipality,
                    enrolled_at=date.today(),
                )
            else:
                # Use existing school
                school = form.cleaned_data["school"]
                if not school.enrolled_at:
                    school.enrolled_at = date.today()
                    school.save(update_fields=["enrolled_at"])

            # Generate credentials
            school.generate_credentials()

            # Create contact person
            Person.objects.create(
                school=school,
                name=contact_name,
                email=contact_email,
                phone=form.cleaned_data.get("contact_phone", ""),
                role=PersonRole.KOORDINATOR,
                is_primary=True,
            )

            # Send confirmation email
            send_school_enrollment_confirmation(school, contact_email, contact_name)

            # Notify subscribed users
            send_school_signup_notifications(school, contact_name, contact_email)

            return redirect("signup:school-success")

        return render(request, self.template_name, {"form": form, "page": page})


class SchoolSignupSuccessView(TemplateView):
    """School signup success page."""

    template_name = "signups/school_signup_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["page"] = SignupPage.objects.get(page_type=SignupPageType.SCHOOL_SIGNUP)
        except SignupPage.DoesNotExist:
            context["page"] = None
        return context


class SchoolsByKommuneView(View):
    """AJAX endpoint to get schools for a given kommune."""

    def get(self, request):
        kommune = request.GET.get("kommune", "")
        if not kommune:
            return JsonResponse({"schools": []})

        schools = School.objects.active().filter(kommune__iexact=kommune).order_by("name").values("id", "name")

        return JsonResponse({"schools": list(schools)})


class ValidateSchoolPasswordView(View):
    """AJAX endpoint to validate school password and set session."""

    def post(self, request):
        import json

        try:
            data = json.loads(request.body)
            password = data.get("password", "").strip().lower()
        except (json.JSONDecodeError, AttributeError):
            password = request.POST.get("password", "").strip().lower()

        if not password:
            return JsonResponse({"valid": False, "error": "Indtast venligst en kode"})

        try:
            school = School.objects.get(
                signup_password__iexact=password,
                enrolled_at__isnull=False,
                opted_out_at__isnull=True,
            )
            # Store in session
            request.session["course_signup_school_id"] = school.pk
            request.session.modified = True
            request.session.save()
            return JsonResponse(
                {
                    "valid": True,
                    "school_id": school.pk,
                    "school_name": school.name,
                }
            )
        except School.DoesNotExist:
            return JsonResponse({"valid": False, "error": "Ugyldig kode"})
