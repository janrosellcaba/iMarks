from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('add/', views.add_bookmark, name='add_bookmark'),
    path('folders/add/', views.add_folder, name='add_folder'),
    path('extract/', views.extract_bookmarks, name='extract'),
]
