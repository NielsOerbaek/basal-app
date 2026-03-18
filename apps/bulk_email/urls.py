from django.urls import path

from . import views

app_name = "bulk_email"

urlpatterns = [
    path("", views.BulkEmailListView.as_view(), name="list"),
    path("ny/", views.BulkEmailCreateView.as_view(), name="create"),
    path("ny/upload/", views.BulkEmailAttachmentUploadView.as_view(), name="attachment_upload"),
    path("ny/save-draft/", views.BulkEmailDraftSaveView.as_view(), name="save_draft"),
    path("<int:pk>/", views.BulkEmailDetailView.as_view(), name="detail"),
    path("preview/", views.BulkEmailPreviewView.as_view(), name="preview"),
    path("dry-run/", views.BulkEmailDryRunView.as_view(), name="dry_run"),
    path("send/", views.BulkEmailSendView.as_view(), name="send"),
    path("attachments/<int:pk>/", views.BulkEmailAttachmentDownloadView.as_view(), name="attachment_download"),
]
