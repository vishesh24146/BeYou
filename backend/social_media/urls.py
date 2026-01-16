"""
URL configuration for BeYou.
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
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from users.views import landing_page
from django.views.generic import RedirectView
from django.http import Http404
from django.urls import re_path
from .views import serve_protected_media



from django.http import HttpResponse

def hidden_admin(request):
    return HttpResponse(
        """
        <html>
        <head><title>403 Forbidden</title></head>
        <body style="text-align:center; margin-top: 50px;">
            <h1>403 Forbidden</h1>
            <p><strong>Admin Dashboard</strong> is not accessible on your IP address.</p>
            <p>Access denied for security reasons. Your attempt has been logged.</p>
            <p>Multiple attempts will result into permamnet IP blocking by Firewall.</p>
        </body>
        </html>
        """,
        content_type='text/html',
        status=403
    )





urlpatterns = [
    path('asvv-only/', admin.site.urls),
    path('admin/', hidden_admin),
    path('users/', include('users.urls')),
    path('friends/', include('friends.urls')),
    path('messaging/', include('messaging.urls')),
    path('marketplace/', include('marketplace.urls')),
    path('', landing_page, name='landing_page'),
    path('', RedirectView.as_view(url='/users/profile/', permanent=False), name='root'),
    path('captcha/', include('captcha.urls')),
    re_path(r'^protected-media/(?P<path>.*)$', serve_protected_media),
]

# Add media serving for development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
