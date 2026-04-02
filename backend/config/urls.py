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

import os

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, re_path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("planner.urls")),
]

# In production, serve the React SPA for all non-API routes
_index_html = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    os.pardir,
    "frontend",
    "dist",
    "index.html",
)
if os.path.isfile(_index_html):
    def _spa_view(request):
        with open(_index_html) as f:
            return HttpResponse(f.read(), content_type="text/html")

    urlpatterns += [re_path(r"^(?!api/|admin/).*$", _spa_view)]
