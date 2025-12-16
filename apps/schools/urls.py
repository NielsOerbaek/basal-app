from django.urls import path

from . import views

app_name = 'schools'

urlpatterns = [
    path('', views.SchoolListView.as_view(), name='list'),
    path('create/', views.SchoolCreateView.as_view(), name='create'),
    path('<int:pk>/', views.SchoolDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.SchoolUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.SchoolDeleteView.as_view(), name='delete'),
    path('<int:pk>/add-seats/', views.AddSeatsView.as_view(), name='add-seats'),
    path('export/', views.SchoolExportView.as_view(), name='export'),
    path('autocomplete/', views.SchoolAutocompleteView.as_view(), name='autocomplete'),
]
