from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from registration import forms as registration_forms

from kobo.static_lists import SECTORS, COUNTRIES

USERNAME_REGEX = r'^[a-z][a-z0-9_]+$'
USERNAME_MAX_LENGTH = 30
USERNAME_INVALID_MESSAGE = _(
    'A username may only contain lowercase letters, numbers, and '
    'underscores (_).'
)


class RegistrationForm(registration_forms.RegistrationForm):
    username = forms.RegexField(
        regex=USERNAME_REGEX,
        max_length=USERNAME_MAX_LENGTH,
        label=_("Username"),
        error_messages={'invalid': USERNAME_INVALID_MESSAGE}
    )
    name = forms.CharField(
        label=_('Name'),
        required=False,
    )
    organization = forms.CharField(
        label=_('Organization name'),
        required=False,
    )
    gender = forms.ChoiceField(
        label=_('Gender'),
        required=False,
        choices=(
                 ('', ''),
                 ('male', _('Male')),
                 ('female', _('Female')),
                 ('other', _('Other')),
                 )
    )

    sector = forms.ChoiceField(
        label=_('Sector'),
        required=False,
        choices=(('', ''),
            ) + SECTORS,
    )
    country = forms.ChoiceField(
        label=_('Country'),
        required=False,
        choices=(('', ''),) + COUNTRIES,
    )
    default_language = forms.ChoiceField(
        label=_('Default language'),
        choices=settings.LANGUAGES,
        # TODO: Read the preferred language from the request?
        initial='en',
    )

    class Meta:
        model = User
        fields = [
            'name',
            'username',
            'organization',
            'email',
            'gender',
            'sector',
            'country',
            'default_language',
            # The 'password' field appears without adding it here; adding it
            # anyway results in a duplicate
        ]
