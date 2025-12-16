from django.urls import path

from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.CourseListView.as_view(), name='list'),
    path('create/', views.CourseCreateView.as_view(), name='create'),
    path('<int:pk>/', views.CourseDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.CourseUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.CourseDeleteView.as_view(), name='delete'),
    path('<int:pk>/rollcall/', views.RollCallView.as_view(), name='rollcall'),
    path('export/', views.CourseExportView.as_view(), name='export'),
    path('signups/', views.SignUpListView.as_view(), name='signup-list'),
    path('signups/<int:pk>/attendance/', views.MarkAttendanceView.as_view(), name='mark-attendance'),
    path('signups/export/', views.SignUpExportView.as_view(), name='signup-export'),
]
