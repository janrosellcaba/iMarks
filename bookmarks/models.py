from django.conf import settings
from django.db import models


class Folder(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='folders',
    )
    name = models.CharField(max_length=200)
    color = models.CharField(max_length=7, default='#ececf0')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookmarks',
    )
    folder = models.ForeignKey(
        Folder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='bookmarks',
    )
    title = models.CharField(max_length=200)
    url = models.URLField(max_length=2048)
    icon_url = models.URLField(max_length=2048, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']
        constraints = [
            models.UniqueConstraint(fields=['user', 'url'], name='unique_bookmark_user_url'),
        ]

    def __str__(self):
        return self.title

    @property
    def tile_color(self):
        if self.folder_id and self.folder.color:
            return self.folder.color
        return '#ececf0'
