from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import BookmarkForm, ExtractForm, FolderForm, RegistrationForm
from .importers import favicon_for_url, import_export, random_pastel_hex
from .models import Bookmark, Folder


@login_required
def home(request):
    bookmarks = (
        Bookmark.objects
        .filter(user=request.user)
        .select_related('folder')
    )
    return render(request, 'bookmarks/home.html', {'bookmarks': bookmarks})


@login_required
def add_bookmark(request):
    if request.method == 'POST':
        form = BookmarkForm(request.POST, user=request.user)
        if form.is_valid():
            bookmark = form.save(commit=False)
            bookmark.user = request.user
            if not bookmark.icon_url:
                bookmark.icon_url = favicon_for_url(bookmark.url)
            bookmark.save()
            return redirect('home')
    else:
        form = BookmarkForm(user=request.user)
    return render(request, 'bookmarks/add_bookmark.html', {'form': form})


@login_required
def add_folder(request):
    if request.method == 'POST':
        form = FolderForm(request.POST)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.user = request.user
            folder.color = random_pastel_hex()
            folder.save()
            return redirect('home')
    else:
        form = FolderForm()
    return render(request, 'bookmarks/add_folder.html', {'form': form})


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
