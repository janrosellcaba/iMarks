from html import escape
from urllib.parse import urlparse

FOLDER_COLORS = (
    '#F87171',
    '#FB923C',
    '#FBBF24',
    '#A3E635',
    '#4ADE80',
    '#2DD4BF',
    '#22D3EE',
    '#38BDF8',
    '#60A5FA',
    '#818CF8',
    '#A78BFA',
    '#E879F9',
    '#F472B6',
    '#FB7185',
    '#A8A29E',
    '#E2E8F0',
)


def hex_to_rgba(value, alpha=0.32):
    raw = (value or '').strip().lstrip('#')
    if len(raw) == 3:
        raw = ''.join(char * 2 for char in raw)
    if len(raw) != 6:
        return f'rgba(226, 232, 240, {alpha})'
    red = int(raw[0:2], 16)
    green = int(raw[2:4], 16)
    blue = int(raw[4:6], 16)
    return f'rgba({red}, {green}, {blue}, {alpha})'


MULTI_TLDS = {
    'co.uk', 'com.au', 'co.jp', 'com.br', 'co.nz', 'com.mx', 'co.in', 'com.ar',
}


def icon_hosts(url):
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower().strip('.')
    if not host:
        return []
    hosts = []

    def add(name):
        if name and name not in hosts:
            hosts.append(name)

    add(host)
    bare = host[4:] if host.startswith('www.') else host
    if bare != host:
        add(bare)
    parts = [part for part in bare.split('.') if part]
    if len(parts) >= 3:
        tail = '.'.join(parts[-2:])
        if tail in MULTI_TLDS:
            if len(parts) >= 4:
                add('.'.join(parts[-3:]))
        else:
            add('.'.join(parts[1:]))
            add(tail)
    return hosts


def is_apex_host(name):
    parts = [part for part in name.split('.') if part]
    if len(parts) == 2:
        return True
    if len(parts) == 3 and '.'.join(parts[-2:]) in MULTI_TLDS:
        return True
    return False


def icon_candidates(url):
    parsed = urlparse(url)
    hosts = icon_hosts(url)
    if not hosts:
        return []
    scheme = parsed.scheme or 'https'
    urls = []
    seen = set()

    def add(candidate):
        if candidate not in seen:
            seen.add(candidate)
            urls.append(candidate)

    def add_direct(name):
        add(f'{scheme}://{name}/apple-touch-icon.png')
        add(f'{scheme}://{name}/apple-touch-icon-precomposed.png')
        add(f'{scheme}://{name}/favicon.png')
        add(f'{scheme}://{name}/favicon.ico')
        add(f'https://favicone.com/{name}?s=256')
        add(f'https://icons.duckduckgo.com/ip3/{name}.ico')

    exact, *parents = hosts
    add_direct(exact)
    if is_apex_host(exact):
        add(f'https://www.google.com/s2/favicons?sz=256&domain={exact}')
    for name in parents:
        add_direct(name)
        add(f'https://www.google.com/s2/favicons?sz=256&domain={name}')
    return urls


def favicon_for_url(url):
    candidates = icon_candidates(url)
    return candidates[0] if candidates else ''


def default_folder_color():
    return FOLDER_COLORS[0]


def title_from_url(url):
    host = (urlparse(url).hostname or '').lower()
    if host.startswith('www.'):
        host = host[4:]
    parts = [part for part in host.split('.') if part]
    if not parts:
        return 'Bookmark'
    if len(parts) >= 3 and '.'.join(parts[-2:]) in MULTI_TLDS:
        parts = parts[:-2]
    elif len(parts) >= 2:
        parts = parts[:-1]
    return parts[-1] if parts else 'Bookmark'


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
