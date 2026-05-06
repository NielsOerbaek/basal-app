from django.urls import path

from . import views

app_name = "webinars"

urlpatterns = [
    path("", views.WebinarManageListView.as_view(), name="list"),
    path("create/", views.WebinarManageCreateView.as_view(), name="create"),
    path("<int:pk>/", views.WebinarManageDetailView.as_view(), name="manage-detail"),
    path("<int:pk>/edit/", views.WebinarManageUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.WebinarManageDeleteView.as_view(), name="delete"),
]
