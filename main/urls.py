# main/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('activities/', views.ActivityListView.as_view(), name='activity_list'),
    path('signup/', views.signup, name='signup'),
    path('accounts/login/', views.CustomLoginView.as_view(), name='login'),
    path('activity/new/', views.activity_create, name='activity_create'),
    path('activity/<int:pk>/', views.ActivityDetailView.as_view(), name='activity_detail'),
    path('search-suggest/', views.search_suggest, name='search_suggest'),
    path('activity/<int:pk>/register/', views.register_activity, name='activity_register'),
    path('activity/<int:pk>/cancel/', views.cancel_registration, name='activity_cancel'),
    path('history/', views.user_history, name='user_history'),
    path('contact/', views.contact_us, name='contact_us'),
    path('about/', views.about_us, name='about_us'),


]
