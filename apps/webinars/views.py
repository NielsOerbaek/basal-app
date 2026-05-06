from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.decorators import staff_required
from apps.signups.models import SignupPage, SignupPageType

from .forms import WebinarForm, WebinarSignupForm
from .models import Webinar, WebinarSignUp

# ---------------------------------------------------------------------------
# Public per-webinar signup
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Admin-facing CRUD
# ---------------------------------------------------------------------------


@method_decorator(staff_required, name="dispatch")
class WebinarManageListView(ListView):
    model = Webinar
    template_name = "webinars/webinar_list.html"
    context_object_name = "webinars"

    def get_queryset(self):
        qs = Webinar.objects.prefetch_related("instructors").order_by("-start_at")
        search = self.request.GET.get("search", "").strip()
        if search:
            qs = qs.filter(title__icontains=search)
        return qs


@method_decorator(staff_required, name="dispatch")
class WebinarManageCreateView(CreateView):
    model = Webinar
    form_class = WebinarForm
    template_name = "webinars/webinar_form.html"

    def get_success_url(self):
        return reverse_lazy("webinars:manage-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Webinaret "{self.object.title}" blev oprettet.')
        return response


@method_decorator(staff_required, name="dispatch")
class WebinarManageDetailView(DetailView):
    """Admin-facing detail page: webinar metadata + signups table + copy-emails button."""

    model = Webinar
    template_name = "webinars/webinar_manage_detail.html"
    context_object_name = "webinar"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["signups"] = self.object.signups.select_related("kommune").all()
        return context


@method_decorator(staff_required, name="dispatch")
class WebinarManageUpdateView(UpdateView):
    model = Webinar
    form_class = WebinarForm
    template_name = "webinars/webinar_form.html"

    def get_success_url(self):
        return reverse_lazy("webinars:manage-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Webinaret "{self.object.title}" blev opdateret.')
        return response


@method_decorator(staff_required, name="dispatch")
class WebinarManageDeleteView(View):
    def get(self, request, pk):
        webinar = get_object_or_404(Webinar, pk=pk)
        signup_count = webinar.signups.count()

        warning = (
            f"Dette vil permanent slette {signup_count} tilmelding"
            f"{'er' if signup_count != 1 else ''}. Handlingen kan ikke fortrydes!"
            if signup_count
            else "Handlingen kan ikke fortrydes!"
        )

        return render(
            request,
            "core/components/confirm_delete_modal.html",
            {
                "title": "Slet webinar permanent",
                "message": format_html(
                    "Er du sikker på, at du vil <strong>permanent slette</strong> webinaret " "<strong>{}</strong>?",
                    webinar.title,
                ),
                "warning": warning,
                "delete_url": reverse_lazy("webinars:delete", kwargs={"pk": pk}),
                "button_text": "Slet permanent",
            },
        )

    def post(self, request, pk):
        webinar = get_object_or_404(Webinar, pk=pk)
        title = webinar.title
        webinar.delete()
        messages.success(request, f'Webinaret "{title}" er blevet permanent slettet.')
        return JsonResponse({"success": True, "redirect": str(reverse_lazy("webinars:list"))})
