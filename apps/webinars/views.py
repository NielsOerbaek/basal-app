from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.signups.models import SignupPage, SignupPageType

from .forms import WebinarSignupForm
from .models import Webinar, WebinarSignUp


class WebinarDetailView(View):
    template_name = "webinars/webinar_detail.html"

    def _get_signup_page(self):
        return (
            SignupPage.objects.prefetch_related("form_fields").filter(page_type=SignupPageType.WEBINAR_SIGNUP).first()
        )

    def _get_webinar(self, slug):
        return get_object_or_404(Webinar, slug=slug, is_published=True)

    def _gate_state(self, webinar):
        """Return ('available', None) or (gate_name, gate_message)."""
        if webinar.is_past:
            return ("past", "Dette webinar har allerede fundet sted.")
        if webinar.is_full:
            return ("full", "Fuldt – alle pladser er optaget.")
        return ("available", None)

    def _build_context(self, webinar, page, form, gate_state, gate_message):
        return {
            "webinar": webinar,
            "page": page,
            "form": form,
            "gate_state": gate_state,
            "gate_message": gate_message,
        }

    def _make_form(self, page, data=None):
        return WebinarSignupForm(
            data,
            signup_page=page,
            submit_label=(page.submit_button_text if page else "Tilmeld"),
        )

    def get(self, request, slug):
        webinar = self._get_webinar(slug)
        page = self._get_signup_page()
        gate_state, gate_message = self._gate_state(webinar)
        form = self._make_form(page) if gate_state == "available" else None
        return render(
            request,
            self.template_name,
            self._build_context(webinar, page, form, gate_state, gate_message),
        )

    def post(self, request, slug):
        webinar = self._get_webinar(slug)
        page = self._get_signup_page()
        gate_state, gate_message = self._gate_state(webinar)

        if gate_state != "available":
            return render(
                request,
                self.template_name,
                self._build_context(webinar, page, None, gate_state, gate_message),
            )

        form = self._make_form(page, request.POST)
        if form.is_valid():
            if WebinarSignUp.objects.filter(webinar=webinar, participant_email=form.cleaned_data["email"]).exists():
                form.add_error("email", "Denne e-mail er allerede tilmeldt dette webinar.")
            else:
                signup = WebinarSignUp.objects.create(
                    webinar=webinar,
                    kommune=form.cleaned_data["kommune"],
                    school_name=form.cleaned_data["school_name"],
                    participant_name=form.cleaned_data["name"],
                    participant_email=form.cleaned_data["email"],
                )
                self._send_emails(webinar, signup)
                return redirect("webinar:detail-success", slug=webinar.slug)
        return render(
            request,
            self.template_name,
            self._build_context(webinar, page, form, gate_state, gate_message),
        )

    def _send_emails(self, webinar, signup):
        from apps.emails.services import (
            send_webinar_signup_confirmation,
            send_webinar_signup_notification,
        )

        send_webinar_signup_confirmation(signup)
        send_webinar_signup_notification(webinar, signup)


class WebinarSignupSuccessView(View):
    template_name = "webinars/webinar_success.html"

    def get(self, request, slug):
        webinar = get_object_or_404(Webinar, slug=slug, is_published=True)
        page = SignupPage.objects.filter(page_type=SignupPageType.WEBINAR_SIGNUP).first()
        return render(
            request,
            self.template_name,
            {"webinar": webinar, "page": page},
        )
