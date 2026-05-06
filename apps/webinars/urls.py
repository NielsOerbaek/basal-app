from django.urls import path

from . import views

app_name = "webinars"

urlpatterns = [
    path("<int:pk>/", views.WebinarManageDetailView.as_view(), name="manage-detail"),
]
