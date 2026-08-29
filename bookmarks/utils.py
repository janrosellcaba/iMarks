import colorsys
import random
from html import escape
from urllib.parse import urlparse


def favicon_for_url(url):
    hostname = urlparse(url).hostname
    if not hostname:
        return ''
    return f'https://www.google.com/s2/favicons?domain={hostname}&sz=256'


def random_pastel_hex():
    hue = random.random()
    r, g, b = colorsys.hsv_to_rgb(hue, 0.32, 0.94)
    return f'#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}'


def _anchor(bookmark):
    href = escape(bookmark.url, quote=True)
    title = escape(bookmark.title)
    added = int(bookmark.created_at.timestamp()) if bookmark.created_at else 0
    icon = ''
    if bookmark.icon_url:
        icon = f' ICON="{escape(bookmark.icon_url, quote=True)}"'
    return f'<DT><A HREF="{href}" ADD_DATE="{added}"{icon}>{title}</A>'


def netscape_export(folders, unfiled):
    lines = [
        '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        '<TITLE>Bookmarks</TITLE>',
        '<H1>Bookmarks</H1>',
        '<DL><p>',
    ]
    for folder in folders:
        name = escape(folder.name)
        lines.append(f'    <DT><H3>{name}</H3>')
        lines.append('    <DL><p>')
        for bookmark in folder.bookmarks.all():
            lines.append(f'        {_anchor(bookmark)}')
        lines.append('    </DL><p>')
    for bookmark in unfiled:
        lines.append(f'    {_anchor(bookmark)}')
    lines.append('</DL><p>')
    return '\n'.join(lines) + '\n'
