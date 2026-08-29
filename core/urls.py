"""
URL configuration for core project.
"""
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import FileResponse, Http404, JsonResponse
from django.urls import include, path
from django.views.decorators.http import require_GET

from bookmarks import views as bookmark_views


ICON_FILES = {
    'favicon.ico': 'image/x-icon',
    'favicon.svg': 'image/svg+xml',
    'favicon.png': 'image/png',
    'apple-touch-icon.png': 'image/png',
}


@require_GET
def site_icon(request, name):
    content_type = ICON_FILES.get(name)
    if not content_type:
        raise Http404()
    icon = Path(settings.BASE_DIR) / 'static' / name
    if not icon.exists():
        raise Http404()
    response = FileResponse(icon.open('rb'), content_type=content_type)
    response['Cache-Control'] = 'public, max-age=86400'
    return response


@require_GET
def manifest(request):
    data = {
        'name': 'iMarks',
        'short_name': 'iMarks',
        'description': 'Your bookmarks, as apps.',
        'start_url': '/',
        'scope': '/',
        'display': 'standalone',
        'orientation': 'any',
        'background_color': '#0f172a',
        'theme_color': '#0f172a',
        'icons': [
            {
                'src': '/favicon.svg',
                'type': 'image/svg+xml',
                'sizes': 'any',
                'purpose': 'any',
            },
            {
                'src': '/apple-touch-icon.png',
                'type': 'image/png',
                'sizes': '180x180',
                'purpose': 'any maskable',
            },
        ],
    }
    response = JsonResponse(data, content_type='application/manifest+json')
    response['Cache-Control'] = 'no-cache'
    return response


@require_GET
def service_worker(request):
    path = Path(settings.BASE_DIR) / 'static' / 'sw.js'
    if not path.exists():
        raise Http404()
    response = FileResponse(path.open('rb'), content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response


@require_GET
def home_js(request):
    path = Path(settings.BASE_DIR) / 'static' / 'home.js'
    if not path.exists():
        raise Http404()
    response = FileResponse(path.open('rb'), content_type='application/javascript')
    response['Cache-Control'] = 'no-cache'
    return response


urlpatterns = [
    path('favicon.ico', site_icon, {'name': 'favicon.ico'}, name='favicon'),
    path('favicon.svg', site_icon, {'name': 'favicon.svg'}, name='favicon_svg'),
    path('apple-touch-icon.png', site_icon, {'name': 'apple-touch-icon.png'}, name='apple_touch_icon'),
    path('manifest.webmanifest', manifest, name='manifest'),
    path('sw.js', service_worker, name='service_worker'),
    path('home.js', home_js, name='home_js'),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('delete-account/', bookmark_views.delete_account, name='delete_account'),
    path('register/', bookmark_views.register, name='register'),
    path('', include('bookmarks.urls')),
]
