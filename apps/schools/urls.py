from django.urls import path

from . import views

app_name = "schools"

urlpatterns = [
    path("", views.SchoolListView.as_view(), name="list"),
    # Kommune URLs
    path("kommuner/", views.KommuneListView.as_view(), name="kommune-list"),
    path("kommuner/<str:kommune>/", views.KommuneDetailView.as_view(), name="kommune-detail"),
    path("create/", views.SchoolCreateView.as_view(), name="create"),
    path("<int:pk>/", views.SchoolDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.SchoolUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.SchoolDeleteView.as_view(), name="delete"),
    path("<int:pk>/hard-delete/", views.SchoolHardDeleteView.as_view(), name="hard-delete"),
    path("<int:pk>/regenerate-credentials/", views.RegenerateCredentialsView.as_view(), name="regenerate-credentials"),
    path("<int:pk>/toggle-enrollment/", views.ToggleEnrollmentView.as_view(), name="toggle-enrollment"),
    path("export/", views.SchoolExportView.as_view(), name="export"),
    path("autocomplete/", views.SchoolAutocompleteView.as_view(), name="autocomplete"),
    # Person URLs
    path("<int:school_pk>/person/add/", views.PersonCreateView.as_view(), name="person-create"),
    path("person/<int:pk>/edit/", views.PersonUpdateView.as_view(), name="person-update"),
    path("person/<int:pk>/delete/", views.PersonDeleteView.as_view(), name="person-delete"),
    # CourseSignUp URLs (for kursusdeltagere)
    path("<int:school_pk>/signup/<int:pk>/edit/", views.CourseSignUpUpdateView.as_view(), name="signup-update"),
    path("<int:school_pk>/signup/<int:pk>/delete/", views.CourseSignUpDeleteView.as_view(), name="signup-delete"),
    # Comment URLs
    path("<int:school_pk>/comment/add/", views.SchoolCommentCreateView.as_view(), name="comment-create"),
    path("comment/<int:pk>/delete/", views.SchoolCommentDeleteView.as_view(), name="comment-delete"),
    # Invoice URLs
    path("<int:school_pk>/invoice/add/", views.InvoiceCreateView.as_view(), name="invoice-create"),
    path("invoice/<int:pk>/delete/", views.InvoiceDeleteView.as_view(), name="invoice-delete"),
    path("fakturaer/manglende/", views.MissingInvoicesView.as_view(), name="missing-invoices"),
    # File URLs
    path("<int:school_pk>/file/add/", views.SchoolFileCreateView.as_view(), name="file-create"),
    path("file/<int:pk>/delete/", views.SchoolFileDeleteView.as_view(), name="file-delete"),
]
