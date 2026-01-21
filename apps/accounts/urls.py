from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("users/", views.UserListView.as_view(), name="user-list"),
    path("users/create/", views.UserCreateView.as_view(), name="user-create"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user-detail"),
    path("users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user-update"),
    path("users/<int:pk>/toggle-active/", views.UserToggleActiveView.as_view(), name="user-toggle-active"),
    path("users/<int:pk>/reset-password/", views.UserResetPasswordView.as_view(), name="user-reset-password"),
]
