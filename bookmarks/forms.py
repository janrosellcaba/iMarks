from urllib.parse import urlparse

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import URLValidator

from .importers import random_pastel_hex
from .models import Bookmark, Folder

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
    class Meta:
        model = Folder
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Folder name',
                'autofocus': True,
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'mt-1 h-12 w-full cursor-pointer rounded-2xl border-0 bg-white/90 p-1',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['color'].required = False
        if not self.is_bound and not self.initial.get('color') and not (self.instance and self.instance.pk and self.instance.color):
            self.initial['color'] = random_pastel_hex()

    def clean_color(self):
        value = (self.cleaned_data.get('color') or '').strip()
        if not value:
            value = self.initial.get('color') or random_pastel_hex()
        if not (value.startswith('#') and len(value) == 7):
            raise forms.ValidationError('Pick a color.')
        return value


class ExtractForm(forms.Form):
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': INPUT_CLASS,
            'accept': '.html,.htm,.json,.xml,text/html,application/json,application/xml',
        }),
    )


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
