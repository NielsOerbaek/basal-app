from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.courses.models import CourseSignUp
from apps.schools.models import School

from .forms import CourseSignupForm, SchoolSignupForm
from .models import SchoolSignup, SignupPage, SignupPageType


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
    """Public course signup form."""

    template_name = "signups/course_signup.html"

    def get_signup_page(self):
        try:
            return SignupPage.objects.prefetch_related("form_fields").get(page_type=SignupPageType.COURSE_SIGNUP)
        except SignupPage.DoesNotExist:
            return None

    def get(self, request):
        page = self.get_signup_page()
        if page and not page.is_active:
            return render(request, "signups/page_unavailable.html", {"page": page})

        form = CourseSignupForm(signup_page=page)
        return render(request, self.template_name, {"form": form, "page": page})

    def post(self, request):
        page = self.get_signup_page()
        if page and not page.is_active:
            return render(request, "signups/page_unavailable.html", {"page": page})

        form = CourseSignupForm(request.POST, request.FILES, signup_page=page)
        if form.is_valid():
            # Create the signup
            signup = CourseSignUp.objects.create(
                course=form.cleaned_data["course"],
                school=form.cleaned_data["school"],
                participant_name=form.cleaned_data["participant_name"],
                participant_email=form.cleaned_data["participant_email"],
                participant_title=form.cleaned_data.get("participant_title", ""),
            )

            # Send confirmation email
            from apps.emails.services import send_signup_confirmation

            send_signup_confirmation(signup)

            return redirect("signup:course-success")

        return render(request, self.template_name, {"form": form, "page": page})


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
        page = self.get_signup_page()
        if page and not page.is_active:
            return render(request, "signups/page_unavailable.html", {"page": page})

        form = SchoolSignupForm(request.POST, request.FILES, signup_page=page)
        if form.is_valid():
            # Create the school signup
            school_signup = SchoolSignup.objects.create(
                school=form.cleaned_data.get("school") if not form.cleaned_data.get("school_not_listed") else None,
                new_school_name=form.cleaned_data.get("new_school_name", ""),
                municipality=form.cleaned_data["municipality"],
                contact_name=form.cleaned_data["contact_name"],
                contact_email=form.cleaned_data["contact_email"],
                contact_phone=form.cleaned_data.get("contact_phone", ""),
                contact_title=form.cleaned_data.get("contact_title", ""),
                comments=form.cleaned_data.get("comments", ""),
            )

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
