from django.contrib import admin
from .models import FriendRequest, Notification

admin.site.register(FriendRequest)
admin.site.register(Notification)