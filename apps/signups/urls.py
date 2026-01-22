from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "signup"

urlpatterns = [
    # Redirect root to course signup for backward compatibility
    path("", RedirectView.as_view(pattern_name="signup:course"), name="index"),
    # Course signup
    path("course/", views.CourseSignupView.as_view(), name="course"),
    path("course/success/", views.CourseSignupSuccessView.as_view(), name="course-success"),
    path("course/check-school-seats/", views.CheckSchoolSeatsView.as_view(), name="check-school-seats"),
    path("course/check-course-seats/", views.CheckCourseSeatsView.as_view(), name="check-course-seats"),
    # School signup
    path("school/", views.SchoolSignupView.as_view(), name="school"),
    path("school/success/", views.SchoolSignupSuccessView.as_view(), name="school-success"),
    path("school/schools-by-kommune/", views.SchoolsByKommuneView.as_view(), name="schools-by-kommune"),
]
