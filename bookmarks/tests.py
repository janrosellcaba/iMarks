from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .importers import parse_export
from .models import Bookmark, Folder

NETSCAPE_HTML = """
<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><H3 PERSONAL_TOOLBAR_FOLDER="true">Bookmarks bar</H3>
    <DL><p>
        <DT><A HREF="https://github.com/">GitHub</A>
        <DT><H3>Dev</H3>
        <DL><p>
            <DT><A HREF="https://docs.djangoproject.com/">Django</A>
        </DL><p>
    </DL><p>
    <DT><H3>Other bookmarks</H3>
    <DL><p>
        <DT><A HREF="https://news.ycombinator.com/">HN</A>
    </DL><p>
</DL>
"""

CHROME_JSON = """
{
  "roots": {
    "bookmark_bar": {
      "name": "Bookmarks bar",
      "children": [
        {"type": "url", "name": "GitHub", "url": "https://github.com/"},
        {
          "type": "folder",
          "name": "Dev",
          "children": [
            {"type": "url", "name": "Django", "url": "https://docs.djangoproject.com/"}
          ]
        }
      ]
    }
  }
}
"""

GOOGLE_XML = """
<bookmarks>
  <bookmark>
    <title>GitHub</title>
    <url>https://github.com/</url>
    <labels><label>Dev</label></labels>
  </bookmark>
</bookmarks>
"""


class BookmarkAuthTests(TestCase):
    def test_home_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_add_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse('add_bookmark'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_extract_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse('extract'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)


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

    def test_home_shows_all_bookmarks_including_foldered(self):
        folder = Folder.objects.create(user=self.user, name='Dev', color='#bae1ff')
        Bookmark.objects.create(user=self.user, title='Mine', url='https://example.com')
        Bookmark.objects.create(
            user=self.user, folder=folder, title='Django', url='https://docs.djangoproject.com/',
        )
        Bookmark.objects.create(user=self.other, title='Theirs', url='https://other.example')

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mine')
        self.assertContains(response, 'Django')
        self.assertContains(response, '#bae1ff')
        self.assertNotContains(response, 'Theirs')

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
        self.assertTrue(folder.color.startswith('#'))
        self.assertEqual(len(folder.color), 7)

    def test_extract_chrome_html(self):
        uploaded = SimpleUploadedFile('bookmarks.html', NETSCAPE_HTML.encode(), content_type='text/html')
        response = self.client.post(reverse('extract'), {'file': uploaded})

        self.assertRedirects(response, reverse('home'))
        self.assertTrue(Folder.objects.filter(user=self.user, name='Dev').exists())
        self.assertEqual(Bookmark.objects.filter(user=self.user).count(), 3)
        self.assertEqual(Bookmark.objects.get(title='Django').folder.name, 'Dev')
        self.assertIsNone(Bookmark.objects.get(title='GitHub').folder)
        self.assertTrue(Folder.objects.get(name='Dev').color.startswith('#'))

        again = self.client.post(reverse('extract'), {
            'file': SimpleUploadedFile('bookmarks.html', NETSCAPE_HTML.encode(), content_type='text/html'),
        })
        self.assertRedirects(again, reverse('home'))
        self.assertEqual(Bookmark.objects.filter(user=self.user).count(), 3)


class ImporterTests(TestCase):
    def test_parse_netscape_html(self):
        items = parse_export(NETSCAPE_HTML)
        by_title = {item['title']: item for item in items}
        self.assertEqual(by_title['GitHub']['folders'], [])
        self.assertEqual(by_title['Django']['folders'], ['Dev'])
        self.assertEqual(by_title['HN']['folders'], [])

    def test_parse_chrome_json(self):
        items = parse_export(CHROME_JSON)
        by_title = {item['title']: item for item in items}
        self.assertEqual(by_title['Django']['folders'], ['Dev'])

    def test_parse_google_xml(self):
        items = parse_export(GOOGLE_XML)
        self.assertEqual(items[0]['folders'], ['Dev'])
        self.assertEqual(items[0]['url'], 'https://github.com/')
