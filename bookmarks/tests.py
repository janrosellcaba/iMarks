from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Bookmark, Folder
from .utils import hex_to_rgba, icon_candidates


class BookmarkAuthTests(TestCase):
    def test_home_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_add_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse('add_bookmark'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_export_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse('export'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_delete_account_requires_post(self):
        response = self.client.get(reverse('delete_account'))
        self.assertEqual(response.status_code, 302)


@override_settings(REGISTRATION_REQUEST_NUMBER='123456')
class RegistrationTests(TestCase):
    def test_rejects_wrong_request_number(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'A-strong-pass-123',
            'password2': 'A-strong-pass-123',
            'request_number': '000000',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid request number')
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_creates_account_with_valid_request_number(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'A-strong-pass-123',
            'password2': 'A-strong-pass-123',
            'request_number': '123456',
        })
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(User.objects.filter(username='newuser').exists())


class BookmarkViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('jan', password='secret')
        self.other = User.objects.create_user('other', password='secret')
        self.client.login(username='jan', password='secret')

    def test_home_keeps_folders_closed(self):
        folder = Folder.objects.create(user=self.user, name='Dev', color='#bae1ff')
        Bookmark.objects.create(user=self.user, title='Mine', url='https://example.com')
        Bookmark.objects.create(
            user=self.user, folder=folder, title='Django', url='https://docs.djangoproject.com/',
        )
        Bookmark.objects.create(user=self.other, title='Theirs', url='https://other.example')

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mine')
        self.assertContains(response, 'Dev')
        self.assertNotContains(response, 'Django')
        self.assertNotContains(response, 'Theirs')

        opened = self.client.get(reverse('home'), {'open': folder.pk})
        self.assertContains(opened, 'Django')
        self.assertContains(opened, 'Mine')
        self.assertContains(opened, 'Dev')

    def test_edit_bookmark_and_folder(self):
        folder = Folder.objects.create(user=self.user, name='Dev', color='#bae1ff')
        bookmark = Bookmark.objects.create(
            user=self.user, title='Django', url='https://docs.djangoproject.com/',
        )
        self.client.post(reverse('edit_bookmark', args=[bookmark.pk]), {
            'title': 'Docs',
            'url': 'https://docs.djangoproject.com/',
            'folder': folder.pk,
        })
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.title, 'Docs')
        self.assertEqual(bookmark.folder, folder)

        self.client.post(reverse('edit_folder', args=[folder.pk]), {
            'name': 'Work',
            'color': '#F472B6',
        })
        folder.refresh_from_db()
        self.assertEqual(folder.name, 'Work')
        self.assertEqual(folder.color, '#F472B6')

    def test_header_has_home_tab(self):
        home = self.client.get(reverse('home'))
        self.assertContains(home, 'Home')
        manage = self.client.get(reverse('manage'))
        self.assertContains(manage, 'href="/"')
        self.assertContains(manage, 'Home')

    def test_manage_lists_items(self):
        Folder.objects.create(user=self.user, name='Dev', color='#bae1ff')
        Bookmark.objects.create(user=self.user, title='Mine', url='https://example.com')
        response = self.client.get(reverse('manage'))
        self.assertContains(response, 'Mine')

    def test_folders_page_lists_folders_and_add_button(self):
        Folder.objects.create(user=self.user, name='Dev', color='#bae1ff')
        response = self.client.get(reverse('folders'))
        self.assertContains(response, 'Dev')
        self.assertContains(response, 'Add folder')
        self.assertContains(response, reverse('add_folder'))

    def test_add_bookmark_creates_row_and_favicon(self):
        response = self.client.post(reverse('add_bookmark'), {
            'title': 'Django',
            'url': 'https://www.djangoproject.com/',
        })

        self.assertRedirects(response, reverse('home'))
        bookmark = Bookmark.objects.get(title='Django')
        self.assertEqual(bookmark.user, self.user)
        self.assertIsNone(bookmark.folder)
        self.assertIn('djangoproject.com', bookmark.icon_url)

    def test_add_bookmark_assumes_https(self):
        response = self.client.post(reverse('add_bookmark'), {
            'title': 'Bitwarden',
            'url': 'bitwarden.com',
        })

        self.assertRedirects(response, reverse('home'))
        bookmark = Bookmark.objects.get(title='Bitwarden')
        self.assertEqual(bookmark.url, 'https://bitwarden.com')
        self.assertIn('bitwarden.com', bookmark.icon_url)

    def test_add_bookmark_without_title_uses_domain(self):
        response = self.client.post(reverse('add_bookmark'), {
            'title': '',
            'url': 'https://app.jan.com',
        })
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(Bookmark.objects.get(url='https://app.jan.com').title, 'jan')

    def test_duplicate_url_is_rejected(self):
        Bookmark.objects.create(user=self.user, title='One', url='https://example.com/')
        response = self.client.post(reverse('add_bookmark'), {
            'title': 'Two',
            'url': 'https://example.com/',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Bookmark.objects.filter(user=self.user).count(), 1)

    def test_create_folder_assigns_color(self):
        response = self.client.post(reverse('add_folder'), {'name': 'Work'})
        self.assertRedirects(response, reverse('folders'))
        folder = Folder.objects.get(name='Work', user=self.user)
        self.assertEqual(folder.color, '#F87171')

    def test_export_netscape_html(self):
        folder = Folder.objects.create(user=self.user, name='Dev', color='#bae1ff')
        Bookmark.objects.create(user=self.user, title='Mine', url='https://example.com')
        Bookmark.objects.create(
            user=self.user, folder=folder, title='Django', url='https://docs.djangoproject.com/',
        )
        Bookmark.objects.create(user=self.other, title='Theirs', url='https://other.example')

        response = self.client.get(reverse('export'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('bookmarks.html', response['Content-Disposition'])
        body = response.content.decode()
        self.assertIn('NETSCAPE-Bookmark-file-1', body)
        self.assertIn('Mine', body)
        self.assertIn('Django', body)
        self.assertIn('<H3>Dev</H3>', body)
        self.assertNotIn('Theirs', body)

    def test_delete_account_removes_user(self):
        Bookmark.objects.create(user=self.user, title='Mine', url='https://example.com')
        response = self.client.post(reverse('delete_account'))
        self.assertRedirects(response, reverse('login'))
        self.assertFalse(User.objects.filter(username='jan').exists())
        self.assertEqual(Bookmark.objects.count(), 0)


class FaviconAndIconTests(TestCase):
    def test_favicon_route_serves_icon(self):
        response = self.client.get('/favicon.ico')
        self.assertEqual(response.status_code, 200)
        self.assertIn(response['Content-Type'], {'image/x-icon', 'image/vnd.microsoft.icon', 'image/png'})

    def test_favicon_svg_is_served_from_app_not_static(self):
        response = self.client.get('/favicon.svg')
        self.assertEqual(response.status_code, 200)
        self.assertIn('svg', response['Content-Type'])
        home = self.client.get(reverse('login'))
        self.assertContains(home, '/favicon.ico')
        self.assertNotContains(home, 'static/favicon.svg')

    def test_hex_to_rgba_is_transparent(self):
        self.assertEqual(hex_to_rgba('#F87171', 0.28), 'rgba(248, 113, 113, 0.28)')


class PwaTests(TestCase):
    def test_manifest_and_service_worker(self):
        manifest = self.client.get('/manifest.webmanifest')
        self.assertEqual(manifest.status_code, 200)
        self.assertIn('standalone', manifest.json()['display'])
        worker = self.client.get('/sw.js')
        self.assertEqual(worker.status_code, 200)
        self.assertEqual(worker['Service-Worker-Allowed'], '/')
        script = self.client.get('/home.js')
        self.assertEqual(script.status_code, 200)
        body = b''.join(script.streaming_content)
        self.assertIn(b'pointerdown', body)

    def test_pages_link_manifest(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, '/manifest.webmanifest')
        self.assertContains(response, 'apple-mobile-web-app-capable')

    def test_icon_candidates_include_fallbacks(self):
        urls = icon_candidates('https://www.djangoproject.com/')
        joined = ' '.join(urls)
        self.assertIn('djangoproject.com', joined)
        self.assertIn('sz=256', joined)
        self.assertIn('google.com/s2/favicons', joined)
        self.assertIn('/favicon.ico', joined)

    def test_icon_candidates_use_parent_domain_for_subdomains(self):
        urls = icon_candidates('https://web.whatsapp.com/')
        self.assertTrue(urls[0].startswith('https://web.whatsapp.com/'))
        self.assertIn('whatsapp.com', ' '.join(urls))
        exact = next(i for i, url in enumerate(urls) if 'web.whatsapp.com' in url)
        parent = next(i for i, url in enumerate(urls) if 'domain=whatsapp.com' in url)
        self.assertLess(exact, parent)

    def test_subdomain_icons_try_exact_host_before_parent(self):
        urls = icon_candidates('https://cal.janrosell.com/')
        self.assertTrue(urls[0].startswith('https://cal.janrosell.com/'))
        exact = next(i for i, url in enumerate(urls) if 'cal.janrosell.com' in url)
        parent = next(i for i, url in enumerate(urls) if 'domain=janrosell.com' in url)
        self.assertLess(exact, parent)


class ArrangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('jan', password='secret')
        self.other = User.objects.create_user('other', password='secret')
        self.client.login(username='jan', password='secret')

    def post_arrange(self, payload):
        return self.client.post(
            reverse('arrange'),
            data=payload,
            content_type='application/json',
        )

    def test_reorder_home(self):
        folder = Folder.objects.create(user=self.user, name='Dev', sort_order=0)
        first = Bookmark.objects.create(user=self.user, title='A', url='https://a.example', sort_order=1)
        second = Bookmark.objects.create(user=self.user, title='B', url='https://b.example', sort_order=2)
        response = self.post_arrange({
            'op': 'reorder_home',
            'items': [
                {'type': 'bookmark', 'id': second.pk},
                {'type': 'folder', 'id': folder.pk},
                {'type': 'bookmark', 'id': first.pk},
            ],
        })
        self.assertEqual(response.status_code, 200)
        second.refresh_from_db()
        folder.refresh_from_db()
        first.refresh_from_db()
        self.assertEqual(second.sort_order, 0)
        self.assertEqual(folder.sort_order, 1)
        self.assertEqual(first.sort_order, 2)

    def test_move_into_and_out_of_folder(self):
        folder = Folder.objects.create(user=self.user, name='Dev')
        bookmark = Bookmark.objects.create(user=self.user, title='A', url='https://a.example')
        response = self.post_arrange({
            'op': 'move',
            'bookmark_id': bookmark.pk,
            'folder_id': folder.pk,
            'index': 0,
        })
        self.assertEqual(response.status_code, 200)
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.folder, folder)

        response = self.post_arrange({
            'op': 'move',
            'bookmark_id': bookmark.pk,
            'folder_id': None,
            'index': 0,
        })
        self.assertEqual(response.status_code, 200)
        bookmark.refresh_from_db()
        self.assertIsNone(bookmark.folder)

    def test_stack_creates_folder(self):
        first = Bookmark.objects.create(user=self.user, title='A', url='https://a.example', sort_order=0)
        second = Bookmark.objects.create(user=self.user, title='B', url='https://b.example', sort_order=1)
        response = self.post_arrange({
            'op': 'stack',
            'bookmark_id': second.pk,
            'onto_bookmark_id': first.pk,
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        folder = Folder.objects.get(pk=data['folder_id'])
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.folder, folder)
        self.assertEqual(second.folder, folder)
        self.assertEqual(Bookmark.objects.filter(user=self.user, folder__isnull=True).count(), 0)

    def test_cannot_arrange_someone_elses_bookmark(self):
        bookmark = Bookmark.objects.create(user=self.other, title='Theirs', url='https://other.example')
        folder = Folder.objects.create(user=self.user, name='Dev')
        response = self.post_arrange({
            'op': 'move',
            'bookmark_id': bookmark.pk,
            'folder_id': folder.pk,
            'index': 0,
        })
        self.assertEqual(response.status_code, 400)
        bookmark.refresh_from_db()
        self.assertIsNone(bookmark.folder)

    def test_home_has_desktop(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'home-desktop')
        self.assertNotContains(response, 'titles-toggle')
