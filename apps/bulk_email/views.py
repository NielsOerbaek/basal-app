from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View

from apps.core.decorators import staff_required


@method_decorator(staff_required, name="dispatch")
class BulkEmailListView(View):
    def get(self, request):
        return HttpResponse("list placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailCreateView(View):
    def get(self, request):
        return HttpResponse("create placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailDetailView(View):
    def get(self, request, pk):
        return HttpResponse("detail placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailPreviewView(View):
    def post(self, request):
        return HttpResponse("preview placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailDryRunView(View):
    def post(self, request):
        return HttpResponse("dry-run placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailSendView(View):
    def post(self, request):
        return HttpResponse("send placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailAttachmentUploadView(View):
    def post(self, request):
        return HttpResponse("upload placeholder")


@method_decorator(staff_required, name="dispatch")
class BulkEmailAttachmentDownloadView(View):
    def get(self, request, pk):
        return HttpResponse("download placeholder")
