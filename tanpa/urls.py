from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from members.forms import EmailLoginForm
from payments.urls import callback_urlpatterns
from payments.views import healthz

admin.site.site_header = "TANPA administration"
admin.site.site_title = "TANPA admin"
admin.site.index_title = "Manage the TANPA website"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(authentication_form=EmailLoginForm), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("manage/", include("dashboard.urls")),
    path("events/", include("events.urls")),
    path("pay/", include("payments.urls")),
    path("callbacks/", include((callback_urlpatterns, "callbacks"))),
    path("healthz", healthz),
    path("", include("members.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA:
    # For simple hosting without a separate web server for uploads (e.g. cPanel Python apps).
    from django.urls import re_path
    from django.views.static import serve

    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]
