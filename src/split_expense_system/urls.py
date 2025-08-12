from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from utils.router.api import BaseAPI


api = BaseAPI()
api.auto_discover_controllers()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)  # type: ignore
