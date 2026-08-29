"""
URL configuration for core project.
"""
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import FileResponse, Http404
from django.urls import include, path
from django.views.decorators.http import require_GET

from bookmarks import views as bookmark_views


@require_GET
def favicon(request):
    icon = Path(settings.BASE_DIR) / 'static' / 'favicon.png'
    if not icon.exists():
        raise Http404()
    return FileResponse(icon.open('rb'), content_type='image/png')


urlpatterns = [
    path('favicon.ico', favicon, name='favicon'),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('delete-account/', bookmark_views.delete_account, name='delete_account'),
    path('register/', bookmark_views.register, name='register'),
    path('', include('bookmarks.urls')),
]
