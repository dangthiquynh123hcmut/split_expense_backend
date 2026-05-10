from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.http import require_GET

from utils.router.api import BaseAPI


@require_GET
def root_view(request):
    return JsonResponse(
        {
            "message": "Welcome to Split Expense API",
        }
    )


@require_GET
def health_check(request):
    return JsonResponse({"status": "ok"})


api = BaseAPI()
api.auto_discover_controllers()

urlpatterns = [
    path("", root_view, name="root"),
    path("health/", health_check, name="health"),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)  # type: ignore
