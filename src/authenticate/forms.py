from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import User 


class UserCreationEmailRequiredForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("full_name", "email", "phone_number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["phone_number"].required = True

    def clean_email(self):
        email = self.cleaned_data.get("email").lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number")
        if User.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("A user with that phone number already exists.")
        return phone_number


class UserChangeEmailRequiredForm(UserChangeForm):
    class Meta:
        model = User
        fields = ("full_name", "email", "phone_number", "is_active", "is_staff")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["phone_number"].required = True

    def clean_email(self):
        email = self.cleaned_data.get("email").lower()
        if (
            User.objects.filter(email__iexact=email)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError(
                "That email is already in use by another account."
            )
        return email
    
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