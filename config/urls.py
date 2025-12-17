from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('summernote/', include('django_summernote.urls')),
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
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
