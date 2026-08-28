"""
URL configuration for core project.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from bookmarks import views as bookmark_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', bookmark_views.register, name='register'),
    path('', include('bookmarks.urls')),
]
