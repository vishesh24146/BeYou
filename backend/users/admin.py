from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, OTP, UserKey, UserFollow, UserBlock, PasswordResetRequest

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone_number', 'is_verified', 'verification_status', 'date_joined')
    list_filter = ('is_verified', 'verification_status', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone_number')
    fieldsets = UserAdmin.fieldsets + (
        ('Verification', {'fields': ('is_verified', 'verification_status', 'id_document', 'verification_reason', 
                                 'verification_submitted_at', 'verification_processed_at', 'verification_notes')}),
    )
    readonly_fields = ('verification_submitted_at', 'verification_processed_at')

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(OTP)
admin.site.register(UserKey)
admin.site.register(UserFollow)
admin.site.register(UserBlock)
admin.site.register(PasswordResetRequest)