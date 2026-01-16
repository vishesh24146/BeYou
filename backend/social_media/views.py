from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.conf import settings
import os

@login_required
def serve_protected_media(request, path):
    file_path = os.path.join(settings.MEDIA_ROOT, path)

    if not os.path.isfile(file_path):
        raise Http404("File not found")

    return FileResponse(open(file_path, 'rb'))
