from django.db.models import Max, Prefetch

from .models import Bookmark, Folder
from .utils import default_folder_color


def next_home_sort(user):
    folder_max = Folder.objects.filter(user=user).aggregate(m=Max('sort_order'))['m']
    bookmark_max = Bookmark.objects.filter(user=user, folder__isnull=True).aggregate(m=Max('sort_order'))['m']
    values = [value for value in (folder_max, bookmark_max) if value is not None]
    return max(values) + 1 if values else 0


def next_folder_sort(folder):
    highest = Bookmark.objects.filter(folder=folder).aggregate(m=Max('sort_order'))['m']
    return highest + 1 if highest is not None else 0


def assign_sort(bookmark, user):
    if bookmark.folder_id:
        bookmark.sort_order = next_folder_sort(bookmark.folder)
    else:
        bookmark.sort_order = next_home_sort(user)


def home_pairs(user):
    items = [
        ('folder', folder.pk, folder.sort_order)
        for folder in Folder.objects.filter(user=user)
    ]
    items.extend(
        ('bookmark', bookmark.pk, bookmark.sort_order)
        for bookmark in Bookmark.objects.filter(user=user, folder__isnull=True)
    )
    items.sort(key=lambda row: (row[2], 0 if row[0] == 'folder' else 1, row[1]))
    return [(kind, pk) for kind, pk, _order in items]


def mixed_home_items(user):
    folders = {
        folder.pk: folder
        for folder in Folder.objects.filter(user=user).prefetch_related(
            Prefetch('bookmarks', queryset=Bookmark.objects.order_by('sort_order', 'pk')),
        )
    }
    bookmarks = {
        bookmark.pk: bookmark
        for bookmark in Bookmark.objects.filter(user=user, folder__isnull=True)
    }
    items = []
    for kind, pk in home_pairs(user):
        if kind == 'folder' and pk in folders:
            items.append({'kind': 'folder', 'folder': folders[pk]})
        elif kind == 'bookmark' and pk in bookmarks:
            items.append({'kind': 'bookmark', 'bookmark': bookmarks[pk]})
    return items


def renumber_home(user, pairs):
    for index, (kind, pk) in enumerate(pairs):
        if kind == 'folder':
            Folder.objects.filter(user=user, pk=pk).update(sort_order=index)
        else:
            Bookmark.objects.filter(user=user, pk=pk, folder__isnull=True).update(sort_order=index)


def compact_folder(user, folder_id):
    ids = list(
        Bookmark.objects.filter(user=user, folder_id=folder_id)
        .order_by('sort_order', 'pk')
        .values_list('pk', flat=True)
    )
    for index, pk in enumerate(ids):
        Bookmark.objects.filter(pk=pk, user=user).update(sort_order=index)


def apply_reorder_home(user, items):
    pairs = [(item['type'], int(item['id'])) for item in items]
    if set(pairs) != set(home_pairs(user)):
        raise ValueError('home mismatch')
    renumber_home(user, pairs)


def apply_reorder_folder(user, folder_id, bookmark_ids):
    folder = Folder.objects.get(pk=folder_id, user=user)
    ids = [int(pk) for pk in bookmark_ids]
    owned = set(Bookmark.objects.filter(user=user, folder=folder).values_list('pk', flat=True))
    if set(ids) != owned:
        raise ValueError('folder mismatch')
    for index, pk in enumerate(ids):
        Bookmark.objects.filter(pk=pk, user=user, folder=folder).update(sort_order=index)


def apply_move(user, bookmark_id, folder_id, index):
    bookmark = Bookmark.objects.get(pk=bookmark_id, user=user)
    old_folder_id = bookmark.folder_id
    dest = None
    if folder_id not in (None, '', 'home'):
        dest = Folder.objects.get(pk=int(folder_id), user=user)

    if dest is None:
        pairs = [pair for pair in home_pairs(user) if pair != ('bookmark', bookmark.pk)]
        index = max(0, min(int(index), len(pairs)))
        bookmark.folder = None
        bookmark.save(update_fields=['folder'])
        pairs.insert(index, ('bookmark', bookmark.pk))
        renumber_home(user, pairs)
    else:
        pairs = [pair for pair in home_pairs(user) if pair != ('bookmark', bookmark.pk)]
        bookmark.folder = dest
        bookmark.save(update_fields=['folder'])
        siblings = list(
            Bookmark.objects.filter(user=user, folder=dest)
            .exclude(pk=bookmark.pk)
            .order_by('sort_order', 'pk')
            .values_list('pk', flat=True)
        )
        index = max(0, min(int(index), len(siblings)))
        siblings.insert(index, bookmark.pk)
        for position, pk in enumerate(siblings):
            Bookmark.objects.filter(pk=pk, user=user).update(sort_order=position)
        renumber_home(user, pairs)

    dest_id = dest.pk if dest else None
    if old_folder_id and old_folder_id != dest_id:
        compact_folder(user, old_folder_id)


def unique_folder_name(user, base='Folder'):
    names = set(Folder.objects.filter(user=user).values_list('name', flat=True))
    if base not in names:
        return base
    n = 2
    while f'{base} {n}' in names:
        n += 1
    return f'{base} {n}'


def apply_stack(user, bookmark_id, onto_id):
    if int(bookmark_id) == int(onto_id):
        raise ValueError('same bookmark')
    dragged = Bookmark.objects.get(pk=bookmark_id, user=user)
    onto = Bookmark.objects.get(pk=onto_id, user=user)
    if onto.folder_id:
        apply_move(user, bookmark_id, onto.folder_id, 999)
        return {'folder_id': onto.folder_id}
    if dragged.folder_id:
        apply_move(user, bookmark_id, None, 999)
        dragged.refresh_from_db()

    pairs = home_pairs(user)
    folder = Folder.objects.create(
        user=user,
        name=unique_folder_name(user),
        color=default_folder_color(),
        sort_order=onto.sort_order,
    )
    onto.folder = folder
    onto.sort_order = 0
    onto.save(update_fields=['folder', 'sort_order'])
    dragged.folder = folder
    dragged.sort_order = 1
    dragged.save(update_fields=['folder', 'sort_order'])

    new_pairs = []
    for pair in pairs:
        if pair == ('bookmark', onto.pk):
            new_pairs.append(('folder', folder.pk))
        elif pair == ('bookmark', dragged.pk):
            continue
        else:
            new_pairs.append(pair)
    renumber_home(user, new_pairs)
    return {'folder_id': folder.pk}
