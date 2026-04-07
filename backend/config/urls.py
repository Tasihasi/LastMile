"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import Http404, HttpResponse
from django.urls import include, path, re_path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("planner.urls")),
]

# In production, serve the React SPA for all non-API routes.
# Path is resolved at import time, but file is read at request time
# so the catch-all works even if the build finishes after Django imports urls.
_index_html = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist" / "index.html"

if not settings.DEBUG or _index_html.is_file():

    def _spa_view(request):
        try:
            return HttpResponse(_index_html.read_text(), content_type="text/html")
        except FileNotFoundError:
            raise Http404("Frontend build not found") from None

    urlpatterns += [re_path(r"^(?!api/|admin/).*$", _spa_view)]
