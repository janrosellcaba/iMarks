from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BookmarkForm, ExtractForm, FolderForm, RegistrationForm
from .importers import favicon_for_url, import_export
from .models import Bookmark, Folder


def after_bookmark_save(bookmark):
    if bookmark.folder_id:
        return redirect('folder', bookmark.folder_id)
    return redirect('home')


@login_required
def home(request, folder_id=None):
    folder = None
    folders = []
    if folder_id:
        folder = get_object_or_404(Folder, pk=folder_id, user=request.user)
        bookmarks = folder.bookmarks.select_related('folder')
    else:
        folders = (
            Folder.objects
            .filter(user=request.user)
            .prefetch_related('bookmarks')
        )
        bookmarks = Bookmark.objects.filter(user=request.user, folder__isnull=True)
    return render(request, 'bookmarks/home.html', {
        'folder': folder,
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
                return redirect('folder', folder_id)
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
def extract_bookmarks(request):
    if request.method == 'POST':
        form = ExtractForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data['file']
            try:
                content = uploaded.read().decode('utf-8-sig')
                bookmarks_created, folders_created = import_export(request.user, content)
            except (UnicodeDecodeError, ValueError) as exc:
                message = str(exc) if isinstance(exc, ValueError) else 'Could not read this file as text.'
                form.add_error('file', message)
            else:
                messages.success(
                    request,
                    f'Extracted {bookmarks_created} bookmark{"" if bookmarks_created == 1 else "s"}'
                    f' and {folders_created} folder{"" if folders_created == 1 else "s"}.',
                )
                return redirect('home')
    else:
        form = ExtractForm()
    return render(request, 'bookmarks/extract.html', {'form': form})


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
