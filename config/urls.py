from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.core.views import CronBackupView, CronSendRemindersView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('summernote/', include('django_summernote.urls')),
    # Cron endpoints
    path('cron/send-reminders/', CronSendRemindersView.as_view(), name='cron-send-reminders'),
    path('cron/backup/', CronBackupView.as_view(), name='cron-backup'),
    path('', include('apps.core.urls')),
    path('schools/', include('apps.schools.urls')),
    path('courses/', include('apps.courses.urls')),
    path('contacts/', include('apps.contacts.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('signup/', include('apps.courses.public_urls')),
    path('aktivitet/', include('apps.audit.urls')),
    # Authentication
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
    # Serve media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
