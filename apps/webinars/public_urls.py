from django.urls import path

from . import views

app_name = "webinar"

urlpatterns = [
    path("<slug:slug>/", views.WebinarDetailView.as_view(), name="detail"),
    path("<slug:slug>/tak/", views.WebinarSignupSuccessView.as_view(), name="detail-success"),
]
