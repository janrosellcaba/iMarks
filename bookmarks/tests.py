from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Bookmark, Folder


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

    def test_manage_lists_items(self):
        Folder.objects.create(user=self.user, name='Dev', color='#bae1ff')
        Bookmark.objects.create(user=self.user, title='Mine', url='https://example.com')
        response = self.client.get(reverse('manage'))
        self.assertContains(response, 'Dev')
        self.assertContains(response, 'Mine')

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
        self.assertRedirects(response, reverse('home'))
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
