from django.urls import path

from .views import ProjectGoalsView, ProjectSettingsUpdateView

app_name = "goals"

urlpatterns = [
    path("", ProjectGoalsView.as_view(), name="project-goals"),
    path("settings/", ProjectSettingsUpdateView.as_view(), name="settings-update"),
]
