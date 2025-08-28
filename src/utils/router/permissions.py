from ninja_extra.permissions import BasePermission


class IsAuthenticated(BasePermission):
    message = "Authentication required"

    def has_permission(self, request, controller) -> bool:
        return hasattr(request, "user") and request.user is not None


class IsAdminUser(BasePermission):
    message = "Admin permission required"

    def has_permission(self, request, controller) -> bool:
        user = getattr(request, "user", None)
        return bool(
            user
            and (
                getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)
            )
        )
