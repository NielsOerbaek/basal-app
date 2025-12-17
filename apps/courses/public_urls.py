from django.urls import path

from . import views

urlpatterns = [
    path('', views.PublicSignUpView.as_view(), name='public-signup'),
    path('success/', views.SignUpSuccessView.as_view(), name='signup-success'),
    path('check-seats/', views.CheckSchoolSeatsView.as_view(), name='check-school-seats'),
]
