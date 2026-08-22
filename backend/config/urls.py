"""
URL configuration for config project.

Routes API calls under /api/ and admin under /admin/; everything else falls
through to the built single-page app (index.html), so client-side routes work
on reload. The SPA's own assets are served by WhiteNoise under /static/.
"""
from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, HttpResponseNotFound
from django.urls import include, path, re_path

INDEX_FILE = settings.FRONTEND_DIST / "index.html"


def serve_index(_request, *_args, **_kwargs):
    if not INDEX_FILE.exists():
        return HttpResponseNotFound(
            "Frontend not built. Run `npm run build` inside frontend/."
        )
    return FileResponse(open(INDEX_FILE, "rb"), content_type="text/html")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('internal/n8n/', include('accounts.n8n_internal_urls')),
    re_path(r"^.*$", serve_index),
]
