from django.urls import path
from . import views

urlpatterns = [
    path('', views.conversation_list, name='conversation_list'),
    path('start/<int:user_id>/', views.start_conversation, name='start_conversation'),
    path('view/<uuid:conversation_id>/', views.view_conversation, name='view_conversation'),
    path('group/create/', views.create_group, name='create_group'),
    path('group/<uuid:conversation_id>/remove/<int:user_id>/', views.remove_from_group, name='remove_from_group'),
    path('group/<uuid:conversation_id>/leave/', views.leave_group, name='leave_group'),
    path('group/<uuid:conversation_id>/delete/', views.delete_group, name='delete_group'),
    path('media/<uuid:message_id>/', views.view_media, name='view_media'),
    path('group/<uuid:conversation_id>/manage/', views.manage_group_members, name='manage_group_members'),
]