from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('folder/<int:folder_id>/', views.home, name='folder'),
    path('add/', views.add_bookmark, name='add_bookmark'),
    path('bookmarks/<int:pk>/edit/', views.edit_bookmark, name='edit_bookmark'),
    path('folders/add/', views.add_folder, name='add_folder'),
    path('folders/<int:pk>/edit/', views.edit_folder, name='edit_folder'),
    path('manage/', views.manage, name='manage'),
    path('extract/', views.extract_bookmarks, name='extract'),
]
