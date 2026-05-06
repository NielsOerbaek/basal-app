from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.signups.auth import resolve_signup_auth
from apps.signups.models import SignupPage, SignupPageType

from .forms import GatedWebinarSignupForm, PublicWebinarSignupForm
from .models import Webinar, WebinarAccessMode, WebinarSignUp


class WebinarDetailView(View):
    template_name = "webinars/webinar_detail.html"

    def _get_signup_page(self):
        return (
            SignupPage.objects.prefetch_related("form_fields").filter(page_type=SignupPageType.WEBINAR_SIGNUP).first()
        )

    def _get_webinar(self, slug):
        webinar = get_object_or_404(Webinar, slug=slug, is_published=True)
        return webinar

    def _resolve_intro_text(self, webinar, page):
        if webinar.intro_text:
            return webinar.intro_text
        if page:
            return page.intro_text
        return ""

    def _gate_state(self, webinar):
        """Return ('available', None) or (gate_name, gate_message)."""
        if webinar.is_past:
            return ("past", "Dette webinar har allerede fundet sted.")
        if webinar.registration_deadline and webinar.registration_deadline < timezone.now():
            return ("deadline", "Tilmelding er lukket.")
        if webinar.is_full:
            return ("full", "Fuldt – alle pladser er optaget.")
        return ("available", None)

    def _build_context(self, request, webinar, page, form, gate_state, gate_message):
        return {
            "webinar": webinar,
            "page": page,
            "intro_text": self._resolve_intro_text(webinar, page),
            "form": form,
            "gate_state": gate_state,
            "gate_message": gate_message,
        }

    def get(self, request, slug):
        webinar = self._get_webinar(slug)
        page = self._get_signup_page()
        gate_state, gate_message = self._gate_state(webinar)

        if webinar.access_mode == WebinarAccessMode.PUBLIC:
            form = (
                PublicWebinarSignupForm(
                    signup_page=page,
                    submit_label=(page.submit_button_text if page else "Tilmeld"),
                )
                if gate_state == "available"
                else None
            )
            return render(
                request,
                self.template_name,
                self._build_context(request, webinar, page, form, gate_state, gate_message),
            )

        # SCHOOL_GATED
        auth = resolve_signup_auth(request)
        form = None
        if gate_state == "available" and not auth["show_password_form"]:
            form = GatedWebinarSignupForm(
                signup_page=page,
                submit_label=(page.submit_button_text if page else "Tilmeld"),
            )
        ctx = self._build_context(request, webinar, page, form, gate_state, gate_message)
        ctx.update(auth)
        return render(request, self.template_name, ctx)

    def post(self, request, slug):
        webinar = self._get_webinar(slug)
        page = self._get_signup_page()
        gate_state, gate_message = self._gate_state(webinar)

        if gate_state != "available":
            return render(
                request,
                self.template_name,
                self._build_context(request, webinar, page, None, gate_state, gate_message),
            )

        if webinar.access_mode == WebinarAccessMode.PUBLIC:
            form = PublicWebinarSignupForm(
                request.POST,
                signup_page=page,
                submit_label=(page.submit_button_text if page else "Tilmeld"),
            )
            if form.is_valid():
                if WebinarSignUp.objects.filter(webinar=webinar, participant_email=form.cleaned_data["email"]).exists():
                    form.add_error("email", "Denne e-mail er allerede tilmeldt dette webinar.")
                else:
                    signup = WebinarSignUp.objects.create(
                        webinar=webinar,
                        school=None,
                        participant_name=form.cleaned_data["name"],
                        participant_email=form.cleaned_data["email"],
                        participant_phone=form.cleaned_data.get("phone", ""),
                        participant_title=form.cleaned_data.get("title", ""),
                        organization=form.cleaned_data.get("organization", ""),
                    )
                    self._send_emails(webinar, signup)
                    return redirect("webinar:detail-success", slug=webinar.slug)
            return render(
                request,
                self.template_name,
                self._build_context(request, webinar, page, form, gate_state, gate_message),
            )

        # SCHOOL_GATED
        auth = resolve_signup_auth(request)
        if auth["show_password_form"]:
            ctx = self._build_context(request, webinar, page, None, gate_state, gate_message)
            ctx.update(auth)
            return render(request, self.template_name, ctx)

        form = GatedWebinarSignupForm(
            request.POST,
            signup_page=page,
            submit_label=(page.submit_button_text if page else "Tilmeld"),
        )
        if form.is_valid():
            if WebinarSignUp.objects.filter(webinar=webinar, participant_email=form.cleaned_data["email"]).exists():
                form.add_error("email", "Denne e-mail er allerede tilmeldt dette webinar.")
            else:
                signup = WebinarSignUp.objects.create(
                    webinar=webinar,
                    school=auth["locked_school"],
                    participant_name=form.cleaned_data["name"],
                    participant_email=form.cleaned_data["email"],
                    participant_phone=form.cleaned_data.get("phone", ""),
                    participant_title=form.cleaned_data.get("title", ""),
                    organization="",
                )
                self._send_emails(webinar, signup)
                return redirect("webinar:detail-success", slug=webinar.slug)
        ctx = self._build_context(request, webinar, page, form, gate_state, gate_message)
        ctx.update(auth)
        return render(request, self.template_name, ctx)

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
