# main/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.activity_list, name='activity_list'),
    path('signup/', views.signup, name='signup'),
    path('activity/new/', views.activity_create, name='activity_create'),
]
