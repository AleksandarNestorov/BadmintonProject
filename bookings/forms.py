import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import CATEGORY_CHOICES, Expense, Product, User


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


class UserLoginForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Невалидно потребителско име или парола.',
        'inactive': 'Този профил е деактивиран. Свържете се с администратор, ако смятате, че това е грешка.',
    }

    def clean(self):
        username = (self.data.get('username') or '').strip()
        if username:
            matched_user = User.objects.filter(username__iexact=username).only('id', 'is_active').first()
            if matched_user and not matched_user.is_active:
                raise forms.ValidationError(
                    self.error_messages['inactive'],
                    code='inactive',
                )
        return super().clean()


class UserRegisterForm(UserCreationForm):
    username = forms.CharField(
        label='Потребителско име',
        help_text='Използвайте поне 3 символа с латински букви, цифри и стандартни знаци.',
    )
    first_name = forms.CharField(required=True, label='Име')
    last_name = forms.CharField(required=True, label='Фамилия')
    gender = forms.ChoiceField(
        choices=[('', 'Изберете пол'), *User.GENDER_CHOICES],
        required=True,
        label='Пол',
    )
    password1 = forms.CharField(
        label='Парола',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='Паролата трябва да съдържа поне 8 символа.',
    )
    password2 = forms.CharField(
        label='Потвърди паролата',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='Въведете същата парола отново за потвърждение.',
    )
    email = forms.EmailField(
        required=True,
        label='Имейл адрес',
        widget=forms.TextInput(
            attrs={
                'inputmode': 'email',
                'autocomplete': 'email',
                'placeholder': 'example@email.com',
            }
        ),
        error_messages={
            'invalid': 'Имейлът трябва да бъде валиден и изписан с латински букви.',
        },
    )
    phone_country = forms.ChoiceField(
        choices=PHONE_COUNTRY_CHOICES,
        initial='BG',
        label='Държава',
    )
    phone = forms.CharField(
        required=True,
        label='Телефон за връзка',
        help_text='За България въведете 9 цифри след +359, например 888123456.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields([
            'username',
            'first_name',
            'last_name',
            'gender',
            'email',
            'phone_country',
            'phone',
            'password1',
            'password2',
        ])
        for field_name, field in self.fields.items():
            if field_name == 'phone_country':
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

        self.fields['phone_country'].widget.attrs.update(
            {
                'data-phone-rules': '|'.join(
                    f"{code}:{rule['prefix']}:{rule['digits']}:{rule['example']}"
                    for code, rule in PHONE_COUNTRY_RULES.items()
                )
            }
        )
        self.fields['phone'].widget.attrs.update(
            {
                'inputmode': 'numeric',
                'autocomplete': 'tel-national',
                'placeholder': PHONE_COUNTRY_RULES['BG']['example'],
            }
        )
        self.fields['username'].widget.attrs.update(
            {
                'autocomplete': 'username',
                'placeholder': 'Напр. aleks123',
            }
        )
        self.fields['password1'].widget.attrs.update({'placeholder': 'Въведете парола'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Повторете паролата'})

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
        fields = ['username', 'first_name', 'last_name', 'gender', 'email', 'phone_country', 'phone']


class CustomerProfileEditForm(forms.ModelForm):
    phone_country = forms.ChoiceField(
        choices=PHONE_COUNTRY_CHOICES,
        initial='BG',
        label='Държава',
    )
    phone = forms.CharField(
        required=True,
        label='Телефон за връзка',
        help_text='Въведете телефонния номер според избраната държава.',
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        labels = {
            'first_name': 'Име',
            'last_name': 'Фамилия',
            'email': 'Имейл адрес',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'phone_country':
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

        self.fields['phone_country'].widget.attrs.update(
            {
                'data-phone-rules': '|'.join(
                    f"{code}:{rule['prefix']}:{rule['digits']}:{rule['example']}"
                    for code, rule in PHONE_COUNTRY_RULES.items()
                )
            }
        )

        self.fields['email'].widget.attrs.update(
            {
                'inputmode': 'email',
                'autocomplete': 'email',
                'placeholder': 'example@email.com',
            }
        )
        self.fields['phone'].widget.attrs.update(
            {
                'inputmode': 'numeric',
                'autocomplete': 'tel-national',
            }
        )

        saved_phone = (self.instance.phone or '').strip()
        for country_code, rule in PHONE_COUNTRY_RULES.items():
            if saved_phone.startswith(rule['prefix']):
                self.fields['phone_country'].initial = country_code
                self.fields['phone'].initial = saved_phone[len(rule['prefix']):]
                self.fields['phone'].widget.attrs['placeholder'] = rule['example']
                break
        else:
            self.fields['phone_country'].initial = 'BG'
            self.fields['phone'].widget.attrs['placeholder'] = PHONE_COUNTRY_RULES['BG']['example']

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


class ProfilePhotoForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['profile_photo']
        labels = {
            'profile_photo': 'Профилна снимка',
        }
        widgets = {
            'profile_photo': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['profile_photo'].required = False
        self.fields['profile_photo'].widget.attrs.update({'class': 'form-control'})


class AdminUserManagementForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'role', 'is_active']
        labels = {
            'first_name': 'Име',
            'last_name': 'Фамилия',
            'email': 'Имейл',
            'phone': 'Телефон',
            'role': 'Роля',
            'is_active': 'Активен',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'is_active':
                field.widget.attrs.update({'class': 'form-check-input'})
            elif field_name == 'role':
                field.widget.attrs.update({'class': 'form-select form-select-sm'})
            else:
                field.widget.attrs.update({'class': 'form-control form-control-sm'})


class AdminCatalogItemForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'quantity']
        labels = {
            'name': 'Име',
            'description': 'Описание',
            'category': 'Категория',
            'price': 'Цена',
            'quantity': 'Наличност',
        }

    def __init__(self, *args, allowed_categories=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].choices = [
            choice for choice in CATEGORY_CHOICES
            if allowed_categories is None or choice[0] in allowed_categories
        ]
        self.fields['quantity'].required = False

        self.fields['name'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['description'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['category'].widget.attrs.update({'class': 'form-select form-select-sm'})
        self.fields['price'].widget.attrs.update({'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0'})
        self.fields['quantity'].widget.attrs.update({'class': 'form-control form-control-sm', 'min': '0', 'placeholder': 'по избор'})


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'category', 'payment_method', 'amount', 'comment']
        labels = {
            'title': 'Разход',
            'category': 'Категория',
            'payment_method': 'Начин на плащане',
            'amount': 'Сума',
            'comment': 'Коментар',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Доставка на напитки'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01', 'step': '0.01', 'placeholder': '50.00'}),
            'comment': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Допълнителна бележка'}),
        }
