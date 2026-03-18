import logging

from django.db.models import F
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, ListView

from apps.bulk_email.models import BulkEmail
from apps.core.decorators import staff_required

logger = logging.getLogger(__name__)


@method_decorator(staff_required, name="dispatch")
class BulkEmailListView(ListView):
    model = BulkEmail
    template_name = "bulk_email/bulk_email_list.html"
    context_object_name = "campaigns"

    def get_queryset(self):
        return BulkEmail.objects.prefetch_related("recipients").order_by(
            F("sent_at").asc(nulls_first=True),
            "-created_at",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for campaign in context["campaigns"]:
            campaign.recipient_count = campaign.recipients.count()
            campaign.failure_count = campaign.recipients.filter(success=False).count()
        return context


@method_decorator(staff_required, name="dispatch")
class BulkEmailDetailView(DetailView):
    model = BulkEmail
    template_name = "bulk_email/bulk_email_detail.html"
    context_object_name = "campaign"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = self.object
        context["recipients"] = campaign.recipients.select_related("school", "person").order_by(
            "success", "school__name"
        )
        context["sent_count"] = campaign.recipients.filter(success=True).count()
        context["failed_count"] = campaign.recipients.filter(success=False).count()
        context["filter_summary"] = campaign.get_filter_summary_display()
        return context


@method_decorator(staff_required, name="dispatch")
class BulkEmailCreateView(View):
    def get(self, request):
        from django.http import HttpResponse

        return HttpResponse("create placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailPreviewView(View):
    def post(self, request):
        from django.http import HttpResponse

        return HttpResponse("preview placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailDryRunView(View):
    def post(self, request):
        from django.http import HttpResponse

        return HttpResponse("dry-run placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailSendView(View):
    def post(self, request):
        from django.http import HttpResponse

        return HttpResponse("send placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailAttachmentUploadView(View):
    def post(self, request):
        from django.http import HttpResponse

        return HttpResponse("upload placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailAttachmentDownloadView(View):
    def get(self, request, pk):
        from django.http import HttpResponse

        return HttpResponse("download placeholder")
