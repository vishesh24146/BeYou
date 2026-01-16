from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('', views.landing_page, name='landing_page'), 
    path('profile/totp-setup/', views.totp_setup, name='totp_setup'),
    path('profile/<str:username>/', views.profile, name='profile'),
    #path('login/', auth_views.LoginView.as_view(template_name='users/login.html', redirect_field_name='next',next_page='profile'),name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verification/request/', views.verification_request, name='verification_request'),
    path('verification/pending/', views.verification_pending, name='verification_pending'),
    path('keys/generate/', views.generate_keys, name='generate_keys'),
    path('keys/download/', views.download_keys, name='download_keys'),
    path('keys/clear/', views.clear_session_keys, name='clear_session_keys'),
    #path('keys/reupload/', views.reupload_keys, name='reupload_keys'),
    path('admin/blockchain/', views.blockchain_explorer, name='blockchain_explorer'),
    path('admin/blockchain/conversation/<uuid:conversation_id>/', views.conversation_blockchain, name='conversation_blockchain'),
    path('admin/blockchain/populate/', views.populate_blockchain, name='populate_blockchain'),
    path('admin/login-logs/', views.login_logs, name='login_logs'),

    # Admin verification URLs
    path('admin/verifications/', views.admin_verification_list, name='admin_verification_list'),
    path('admin/verification/<int:user_id>/', views.process_verification, name='process_verification'),
    
    # Password reset URLs
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/verify/<int:reset_id>/', views.password_reset_verify, name='password_reset_verify'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),

    # Block and Report URLs
    path('block/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock/<int:user_id>/', views.unblock_user, name='unblock_user'),
    path('blocked-users/', views.blocked_users, name='blocked_users'),
    path('report/user/<int:user_id>/', views.report_user, name='report_user'),
    path('report/message/<uuid:message_id>/', views.report_message, name='report_message'),
    path('report/item/<uuid:item_id>/', views.report_item, name='report_item'),

    # Admin management URLs
    path('admin/reports/', views.admin_reports_list, name='admin_reports_list'),
    path('admin/report/<int:report_id>/', views.admin_process_report, name='admin_process_report'),
    path('admin/users/', views.admin_user_management, name='admin_user_management'),
    path('admin/user/<int:user_id>/ban/', views.admin_ban_user, name='admin_ban_user'),
    path('admin/user/<int:user_id>/unban/', views.admin_unban_user, name='admin_unban_user'),
]