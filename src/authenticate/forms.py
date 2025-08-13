from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class UserCreationEmailRequiredForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("full_name", "username", "phone_number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].required = True
        self.fields["phone_number"].required = True

    def clean_username(self):
        username = self.cleaned_data.get("username").lower()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return username

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number")
        if User.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("A user with that phone number already exists.")
        return phone_number


class UserChangeEmailRequiredForm(UserChangeForm):
    class Meta:
        model = User
        fields = ("full_name", "username", "phone_number", "is_active", "is_staff")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].required = True
        self.fields["phone_number"].required = True

    def clean_username(self):
        username = self.cleaned_data.get("username").lower()
        if (
            User.objects.filter(username__iexact=username)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError(
                "That email is already in use by another account."
            )
        return username

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number")
        if (
            User.objects.filter(phone_number=phone_number)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError(
                "That phone number is already in use by another account."
            )
        return phone_number
