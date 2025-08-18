from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import UserChangeEmailRequiredForm, UserCreationEmailRequiredForm
from .models import User


class UserAdmin(BaseUserAdmin):
    add_form = UserCreationEmailRequiredForm
    form = UserChangeEmailRequiredForm
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "phone_number",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    list_display = (
        "email",
        "full_name",
        "phone_number",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "full_name", "phone_number")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("full_name", "phone_number", "avatar_url")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "phone_number",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        is_superuser = request.user.is_superuser

        if not is_superuser:
            form.base_fields["is_superuser"].disabled = True
            form.base_fields["is_staff"].disabled = True
            form.base_fields["is_active"].disabled = True

        return form


admin.site.register(User, UserAdmin)
