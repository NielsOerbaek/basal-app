from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.CourseListView.as_view(), name="list"),
    path("create/", views.CourseCreateView.as_view(), name="create"),
    path("<int:pk>/", views.CourseDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.CourseUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.CourseDeleteView.as_view(), name="delete"),
    path("<int:pk>/rollcall/", views.RollCallView.as_view(), name="rollcall"),
    path("<int:pk>/bulk-import/", views.BulkImportView.as_view(), name="bulk-import"),
    path("<int:pk>/bulk-import/confirm/", views.BulkImportConfirmView.as_view(), name="bulk-import-confirm"),
    path("export/", views.CourseExportView.as_view(), name="export"),
    path("signups/", views.SignUpListView.as_view(), name="signup-list"),
    path("signups/<int:pk>/edit/", views.SignUpUpdateView.as_view(), name="signup-update"),
    path("signups/<int:pk>/attendance/", views.MarkAttendanceView.as_view(), name="mark-attendance"),
    path("signups/<int:pk>/delete/", views.SignUpDeleteView.as_view(), name="signup-delete"),
    path("signups/export/", views.SignUpExportView.as_view(), name="signup-export"),
    # Course Material URLs
    path("<int:course_pk>/material/add/", views.CourseMaterialCreateView.as_view(), name="material-create"),
    path("material/<int:pk>/delete/", views.CourseMaterialDeleteView.as_view(), name="material-delete"),
]
