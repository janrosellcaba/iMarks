from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import BookmarkForm, FolderForm, RegistrationForm
from .models import Bookmark, Folder
from .utils import favicon_for_url, netscape_export


def home_with_folder(folder_id):
    url = reverse('home')
    if folder_id:
        return redirect(f'{url}?open={folder_id}')
    return redirect(url)


def after_bookmark_save(bookmark):
    return home_with_folder(bookmark.folder_id)


@login_required
def home(request, folder_id=None):
    if folder_id:
        return home_with_folder(folder_id)

    open_folder = None
    open_id = request.GET.get('open')
    if open_id:
        open_folder = Folder.objects.filter(pk=open_id, user=request.user).first()

    folders = (
        Folder.objects
        .filter(user=request.user)
        .prefetch_related('bookmarks')
    )
    bookmarks = Bookmark.objects.filter(user=request.user, folder__isnull=True)
    return render(request, 'bookmarks/home.html', {
        'open_folder': open_folder,
        'folders': folders,
        'bookmarks': bookmarks,
    })


@login_required
def add_bookmark(request):
    initial = {}
    preset = request.GET.get('folder')
    if preset:
        owned = Folder.objects.filter(pk=preset, user=request.user).first()
        if owned:
            initial['folder'] = owned
    if request.method == 'POST':
        form = BookmarkForm(request.POST, user=request.user)
        if form.is_valid():
            bookmark = form.save(commit=False)
            bookmark.user = request.user
            bookmark.icon_url = favicon_for_url(bookmark.url)
            bookmark.save()
            return after_bookmark_save(bookmark)
    else:
        form = BookmarkForm(user=request.user, initial=initial)
    return render(request, 'bookmarks/bookmark_form.html', {
        'form': form,
        'bookmark': None,
    })


@login_required
def edit_bookmark(request, pk):
    bookmark = get_object_or_404(Bookmark, pk=pk, user=request.user)
    if request.method == 'POST':
        if request.POST.get('delete'):
            folder_id = bookmark.folder_id
            bookmark.delete()
            if folder_id:
                return home_with_folder(folder_id)
            return redirect('manage')
        form = BookmarkForm(request.POST, user=request.user, instance=bookmark)
        if form.is_valid():
            bookmark = form.save(commit=False)
            bookmark.icon_url = favicon_for_url(bookmark.url)
            bookmark.save()
            return redirect('manage')
    else:
        form = BookmarkForm(user=request.user, instance=bookmark)
    return render(request, 'bookmarks/bookmark_form.html', {
        'form': form,
        'bookmark': bookmark,
    })


@login_required
def add_folder(request):
    if request.method == 'POST':
        form = FolderForm(request.POST)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.user = request.user
            folder.save()
            return redirect('home')
    else:
        form = FolderForm()
    return render(request, 'bookmarks/folder_form.html', {
        'form': form,
        'folder': None,
    })


@login_required
def edit_folder(request, pk):
    folder = get_object_or_404(Folder, pk=pk, user=request.user)
    if request.method == 'POST':
        if request.POST.get('delete'):
            folder.delete()
            return redirect('manage')
        form = FolderForm(request.POST, instance=folder)
        if form.is_valid():
            form.save()
            return redirect('manage')
    else:
        form = FolderForm(instance=folder)
    return render(request, 'bookmarks/folder_form.html', {
        'form': form,
        'folder': folder,
    })


@login_required
def manage(request):
    return render(request, 'bookmarks/manage.html', {
        'folders': Folder.objects.filter(user=request.user).annotate(bookmark_count=Count('bookmarks')),
        'bookmarks': Bookmark.objects.filter(user=request.user).select_related('folder'),
    })


@login_required
def export_bookmarks(request):
    folders = (
        Folder.objects
        .filter(user=request.user)
        .prefetch_related('bookmarks')
    )
    unfiled = Bookmark.objects.filter(user=request.user, folder__isnull=True)
    html = netscape_export(folders, unfiled)
    response = HttpResponse(html, content_type='text/html; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="bookmarks.html"'
    return response


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
@require_POST
def delete_account(request):
    user = request.user
    logout(request)
    user.delete()
    return redirect('login')
