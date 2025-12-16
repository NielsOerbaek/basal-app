from django.urls import path

from . import views

urlpatterns = [
    path('', views.PublicSignUpView.as_view(), name='public-signup'),
    path('success/', views.SignUpSuccessView.as_view(), name='signup-success'),
]
