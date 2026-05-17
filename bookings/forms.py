from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
import re


PHONE_COUNTRY_RULES = {
    'BG': {
        'label': 'България (+359)',
        'prefix': '+359',
        'digits': 9,
        'example': '888123456',
    },
    'RO': {
        'label': 'Румъния (+40)',
        'prefix': '+40',
        'digits': 9,
        'example': '712345678',
    },
    'GR': {
        'label': 'Гърция (+30)',
        'prefix': '+30',
        'digits': 10,
        'example': '6912345678',
    },
    'TR': {
        'label': 'Турция (+90)',
        'prefix': '+90',
        'digits': 10,
        'example': '5012345678',
    },
    'DE': {
        'label': 'Германия (+49)',
        'prefix': '+49',
        'digits': 10,
        'example': '1512345678',
    },
}

PHONE_COUNTRY_CHOICES = [
    (country_code, settings['label'])
    for country_code, settings in PHONE_COUNTRY_RULES.items()
]

class UserRegisterForm(UserCreationForm):
    
    first_name = forms.CharField(required=True, label="Име")
    last_name = forms.CharField(required=True, label="Фамилия")
    
    email = forms.EmailField(
        required=True,
        label="Имейл адрес",
        widget=forms.TextInput(attrs={
            'inputmode': 'email',
            'autocomplete': 'email',
            'placeholder': 'example@email.com',
        }),
        error_messages={
            'invalid': 'Имейлът трябва да бъде валиден и изписан с латински букви.',
        },
    )
    phone_country = forms.ChoiceField(
        choices=PHONE_COUNTRY_CHOICES,
        initial='BG',
        label="Държава",
    )
    phone = forms.CharField(
        required=True,
        label="Телефон за връзка",
        help_text="За България въведете 9 цифри след +359, например 888123456.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'phone_country':
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

        self.fields['phone_country'].widget.attrs.update({
            'data-phone-rules': '|'.join(
                f"{code}:{rule['prefix']}:{rule['digits']}:{rule['example']}"
                for code, rule in PHONE_COUNTRY_RULES.items()
            )
        })
        self.fields['phone'].widget.attrs.update({
            'inputmode': 'numeric',
            'autocomplete': 'tel-national',
            'placeholder': PHONE_COUNTRY_RULES['BG']['example'],
        })

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if not re.fullmatch(r'[A-Za-z0-9._%+\-@]+', email):
            raise forms.ValidationError(
                'Имейлът трябва да бъде изписан само с латински букви, цифри и стандартни символи.'
            )
        return email

    def clean_phone(self):
        phone_country = self.cleaned_data.get('phone_country', 'BG')
        phone = self.cleaned_data['phone'].strip()
        digits = re.sub(r'\D', '', phone)
        rule = PHONE_COUNTRY_RULES[phone_country]

        if phone.startswith(rule['prefix']):
            digits = digits[len(rule['prefix'].lstrip('+')):]

        if len(digits) != rule['digits']:
            raise forms.ValidationError(
                f"За {rule['label']} телефонът трябва да съдържа точно {rule['digits']} цифри след {rule['prefix']}."
            )

        return f"{rule['prefix']}{digits}"

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_country', 'phone']
