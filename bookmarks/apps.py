from django.apps import AppConfig
from django.db.backends.signals import connection_created


def limit_sqlite_size(sender, connection, **kwargs):
    if connection.vendor != 'sqlite':
        return
    from django.conf import settings

    max_bytes = int(getattr(settings, 'SQLITE_MAX_BYTES', 32 * 1024 * 1024))
    with connection.cursor() as cursor:
        cursor.execute('PRAGMA page_size')
        page_size = cursor.fetchone()[0] or 4096
        cursor.execute(f'PRAGMA max_page_count = {max(1, max_bytes // page_size)}')


class BookmarksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bookmarks'

    def ready(self):
        connection_created.connect(limit_sqlite_size, dispatch_uid='bookmarks.limit_sqlite_size')
