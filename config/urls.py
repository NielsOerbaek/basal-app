from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.core.views import CronBackupView, CronSendRemindersView
from apps.schools.views import (
    PublicPersonCreateView,
    PublicPersonDeleteView,
    PublicPersonUpdateView,
    SchoolPublicView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("summernote/", include("django_summernote.urls")),
    # Cron endpoints
    path("cron/send-reminders/", CronSendRemindersView.as_view(), name="cron-send-reminders"),
    path("cron/backup/", CronBackupView.as_view(), name="cron-backup"),
    # Public school view (token-based access)
    path("school/<str:token>/", SchoolPublicView.as_view(), name="school-public"),
    path(
        "school/<str:token>/person/add/",
        PublicPersonCreateView.as_view(),
        name="school-public-person-create",
    ),
    path(
        "school/<str:token>/person/<int:pk>/edit/",
        PublicPersonUpdateView.as_view(),
        name="school-public-person-update",
    ),
    path(
        "school/<str:token>/person/<int:pk>/delete/",
        PublicPersonDeleteView.as_view(),
        name="school-public-person-delete",
    ),
    path("", include("apps.core.urls")),
    path("schools/", include("apps.schools.urls")),
    path("courses/", include("apps.courses.urls")),
    path("contacts/", include("apps.contacts.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("signup/", include("apps.signups.urls")),
    path("aktivitet/", include("apps.audit.urls")),
    path("projektmaal/", include("apps.goals.urls")),
    # Authentication
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]

if settings.DEBUG:
    import debug_toolbar
    from django.conf.urls.static import static

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
    # Serve media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
