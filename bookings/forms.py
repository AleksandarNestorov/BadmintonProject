from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserRegisterForm(UserCreationForm):
    
    first_name = forms.CharField(required=True, label="Име")
    last_name = forms.CharField(required=True, label="Фамилия")
    
    email = forms.EmailField(required=True, label="Имейл адрес")
    phone = forms.CharField(required=True, label="Телефон за връзка")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone']