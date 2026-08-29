from urllib.parse import urlparse

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import URLValidator

from .models import Bookmark, Folder
from .utils import FOLDER_COLORS, default_folder_color

INPUT_CLASS = (
    'mt-1 w-full rounded-2xl border-0 bg-white/90 px-4 py-3 text-slate-900 '
    'shadow-sm outline-none ring-1 ring-black/10 focus:ring-2 focus:ring-white'
)


class BookmarkForm(forms.ModelForm):
    url = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'example.com',
            'inputmode': 'url',
            'autocomplete': 'url',
        }),
    )

    class Meta:
        model = Bookmark
        fields = ['title', 'url', 'folder']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Title',
                'autofocus': True,
            }),
            'folder': forms.Select(attrs={'class': INPUT_CLASS}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['folder'].required = False
        self.fields['folder'].empty_label = 'No folder'
        if user is not None:
            self.fields['folder'].queryset = Folder.objects.filter(user=user)
        else:
            self.fields['folder'].queryset = Folder.objects.none()

    def clean_url(self):
        url = self.cleaned_data['url'].strip()
        if url and not urlparse(url).scheme:
            url = f'https://{url}'
        URLValidator()(url)
        if self.user:
            existing = Bookmark.objects.filter(user=self.user, url=url)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError('You already saved this URL.')
        return url


class FolderForm(forms.ModelForm):
    color = forms.ChoiceField(
        choices=[(c, c) for c in FOLDER_COLORS],
        widget=forms.RadioSelect,
        initial=default_folder_color,
        required=False,
    )

    class Meta:
        model = Folder
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Folder name',
                'autofocus': True,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = ''
        if self.instance.pk:
            current = (self.instance.color or '').upper()
        choices = list(FOLDER_COLORS)
        if current and current not in choices:
            choices = [self.instance.color] + choices
        self.fields['color'].choices = [(c, c) for c in choices]
        if not self.is_bound and not self.initial.get('color'):
            self.initial['color'] = self.instance.color if self.instance.pk else default_folder_color()

    def clean_color(self):
        value = (self.cleaned_data.get('color') or '').strip()
        if not value:
            return default_folder_color()
        allowed = {c.upper() for c, _ in self.fields['color'].choices}
        if value.upper() not in allowed:
            raise forms.ValidationError('Pick a color.')
        for choice, _label in self.fields['color'].choices:
            if choice.upper() == value.upper():
                return choice
        return default_folder_color()


class RegistrationForm(UserCreationForm):
    request_number = forms.CharField(
        label='Request Number',
        max_length=64,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Request number',
            'autocomplete': 'off',
        }),
    )

    class Meta(UserCreationForm.Meta):
        fields = ('username',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = INPUT_CLASS

    def clean_request_number(self):
        value = self.cleaned_data['request_number'].strip()
        expected = str(settings.REGISTRATION_REQUEST_NUMBER)
        if value != expected:
            raise forms.ValidationError('Invalid request number.')
        return value
