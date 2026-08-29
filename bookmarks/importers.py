import colorsys
import json
import random
from urllib.parse import urlparse
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from django.db import IntegrityError

from .models import Bookmark, Folder

FLATTEN_ROOTS = {
    'bookmarks',
    'bookmarks bar',
    'bookmarks toolbar',
    'bookmarks menu',
    'other bookmarks',
    'mobile bookmarks',
}


def favicon_for_url(url):
    hostname = urlparse(url).hostname
    if not hostname:
        return ''
    return f'https://www.google.com/s2/favicons?domain={hostname}&sz=256'


def random_pastel_hex():
    hue = random.random()
    r, g, b = colorsys.hsv_to_rgb(hue, 0.32, 0.94)
    return f'#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}'


def get_or_create_folder(user, name):
    folder = Folder.objects.filter(user=user, name=name).first()
    if folder:
        return folder, False
    return Folder.objects.create(user=user, name=name, color=random_pastel_hex()), True


def is_http_url(url):
    return bool(url) and urlparse(url).scheme in {'http', 'https'}


def flatten_default_roots(items):
    for item in items:
        while item['folders'] and item['folders'][0].lower() in FLATTEN_ROOTS:
            item['folders'] = item['folders'][1:]
    return items


def parse_netscape(content):
    soup = BeautifulSoup(content, 'html.parser')
    items = []

    def walk(dl, path):
        if dl is None:
            return
        for dt in dl.find_all('dt'):
            if dt.find_parent('dl') is not dl:
                continue
            h3 = dt.find('h3')
            link = dt.find('a', href=True)
            if h3 and h3.find_parent('dt') is dt:
                name = h3.get_text(strip=True)
                nested = dt.find('dl')
                if nested is None:
                    sibling = dt.find_next_sibling('dl')
                    if sibling is not None and sibling.find_parent('dl') is dl:
                        nested = sibling
                walk(nested, path + [name])
            elif link and link.find_parent('dt') is dt:
                items.append({
                    'title': link.get_text(strip=True) or link['href'],
                    'url': link['href'],
                    'folders': list(path),
                })

    walk(soup.find('dl'), [])
    return flatten_default_roots(items)


def parse_chrome_json(content):
    data = json.loads(content)
    items = []
    roots = data.get('roots', data)
    for key in ('bookmark_bar', 'other', 'synced', 'mobile'):
        node = roots.get(key)
        if not node:
            continue
        name = node.get('name') or key.replace('_', ' ')
        _walk_chrome_node(node, [name], items)
    if not items and isinstance(data, dict):
        _walk_chrome_node(data, [], items)
    return flatten_default_roots(items)


def _walk_chrome_node(node, path, items):
    for child in node.get('children') or []:
        if child.get('children') is not None or child.get('type') == 'folder':
            name = child.get('name') or 'Untitled'
            _walk_chrome_node(child, path + [name], items)
        elif child.get('url'):
            items.append({
                'title': child.get('name') or child['url'],
                'url': child['url'],
                'folders': list(path),
            })


def parse_google_xml(content):
    root = ElementTree.fromstring(content)
    items = []
    for bookmark in root.findall('bookmark'):
        title = (bookmark.findtext('title') or '').strip()
        url = (bookmark.findtext('url') or '').strip()
        labels = [
            (label.text or '').strip()
            for label in bookmark.findall('labels/label')
            if (label.text or '').strip()
        ]
        items.append({
            'title': title or url,
            'url': url,
            'folders': labels[:1],
        })
    return items


def parse_export(content):
    stripped = content.lstrip('\ufeff \t\r\n')
    if not stripped:
        raise ValueError('The file is empty.')
    if stripped.startswith('{'):
        try:
            return parse_chrome_json(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError('Could not parse this Chrome JSON file.') from exc
    if stripped.startswith('<?xml') or stripped.lower().startswith('<bookmarks'):
        try:
            return parse_google_xml(stripped)
        except ElementTree.ParseError as exc:
            raise ValueError('Could not parse this Google Bookmarks XML file.') from exc
    if 'NETSCAPE-Bookmark-file' in stripped or '<DL' in stripped or '<dl' in stripped:
        return parse_netscape(stripped)
    raise ValueError(
        'Unrecognized file. Export HTML from Chrome, or upload Chrome JSON / Google Bookmarks XML.'
    )


def import_export(user, content):
    items = parse_export(content)
    existing_urls = set(
        Bookmark.objects.filter(user=user).values_list('url', flat=True)
    )
    bookmarks_created = 0
    folders_created = 0

    for item in items:
        url = (item.get('url') or '').strip()
        if not is_http_url(url) or url in existing_urls:
            continue

        folder = None
        for name in item.get('folders') or []:
            name = name.strip()[:200]
            if not name:
                continue
            folder, created = get_or_create_folder(user, name)
            folders_created += int(created)

        try:
            Bookmark.objects.create(
                user=user,
                folder=folder,
                title=(item.get('title') or url)[:200],
                url=url[:2048],
                icon_url=favicon_for_url(url),
            )
        except IntegrityError:
            continue
        existing_urls.add(url)
        bookmarks_created += 1

    return bookmarks_created, folders_created
