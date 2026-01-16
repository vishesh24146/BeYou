from django.db import models
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True, db_index=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    totp_secret = models.CharField(max_length=32, blank=True, null=True)  # TOTP secret for 2FA

    id_document = models.ImageField(upload_to='verification_docs/', null=True, blank=True)
    verification_reason = models.TextField(max_length=500, blank=True, null=True)
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending',
        blank=True, null=True
    )
    verification_submitted_at = models.DateTimeField(null=True, blank=True)
    verification_processed_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True, null=True)  # Admin notes

class OTP(models.Model):
    PURPOSE_CHOICES = [
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
        ('high_risk', 'High Risk Action'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=128)  # store hashed OTP for security
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"OTP for {self.user.username} - {self.purpose}"

class UserKey(models.Model):
    KEY_TYPE_CHOICES = [
        ('signing', 'Signing'),
        ('encryption', 'Encryption'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='keys')
    public_key = models.TextField()
    public_key_hash = models.CharField(max_length=64, db_index=True, unique=True, null=True)
    key_type = models.CharField(max_length=20, choices=KEY_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.key_type.capitalize()} Key for {self.user.username}"
    
    def save(self, *args, **kwargs):
        # Generate a hash of the public key for easier lookups
        if not self.public_key_hash and self.public_key:
            import hashlib
            self.public_key_hash = hashlib.sha256(self.public_key.encode()).hexdigest()
        super().save(*args, **kwargs)

class UserBlock(models.Model):
    blocker = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='blocking')
    blocked_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='blocked_by')
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked_user')

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked_user.username}"
    
class PasswordResetRequest(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token = models.CharField(max_length=32)  # TOTP secret for reset
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Password reset for {self.user.username}"
    
    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()
    
class Report(models.Model):
    REPORT_TYPES = [
        ('user', 'User Report'),
        ('message', 'Message Report'),
        ('item', 'Marketplace Item Report'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    reporter = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='submitted_reports')
    reported_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reports_against', null=True, blank=True)
    reported_message = models.UUIDField(null=True, blank=True)  # Store the message ID
    reported_item = models.UUIDField(null=True, blank=True)  # Store the item ID
    
    report_type = models.CharField(max_length=10, choices=REPORT_TYPES)
    reason = models.TextField()
    additional_details = models.TextField(blank=True, null=True)
    screenshot = models.ImageField(upload_to='report_evidence/', null=True, blank=True)
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, null=True)
    action_taken = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.report_type == 'user':
            return f"User Report: {self.reporter.username} reported {self.reported_user.username}"
        elif self.report_type == 'message':
            return f"Message Report by {self.reporter.username}"
        else:
            return f"Item Report by {self.reporter.username}"
        
class UserFollow(models.Model):
    follower = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='following')
    followee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followee')

    def __str__(self):
        return f"{self.follower.username} follows {self.followee.username}"

class LoginActivity(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='login_activities', null=True, blank=True)
    username = models.CharField(max_length=150, blank=True, null=True)  # Store username even for failed attempts
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    was_successful = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=100, blank=True, null=True)
    session_key = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = "Login Activity"
        verbose_name_plural = "Login Activities"
        ordering = ['-timestamp']
    
    def __str__(self):
        status = "Success" if self.was_successful else "Failed"
        if self.user:
            return f"{status} - {self.user.username} - {self.timestamp}"
        return f"{status} - {self.username or 'Unknown'} - {self.timestamp}"     