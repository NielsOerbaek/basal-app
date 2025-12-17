from django.urls import path

from apps.audit import views

app_name = 'audit'

urlpatterns = [
    path('', views.ActivityLogListView.as_view(), name='activity_list'),
    path('school/<int:school_id>/', views.SchoolActivityListView.as_view(), name='school_activity'),
    path('course/<int:course_id>/', views.CourseActivityListView.as_view(), name='course_activity'),
]
