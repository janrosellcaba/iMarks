from django.contrib import admin

from .models import Bookmark, Folder


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('name',)


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'folder', 'user', 'created_at')
    list_filter = ('user', 'folder')
    search_fields = ('title', 'url')
