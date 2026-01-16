from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import LoginActivity

class LoggingModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        
        # Create login activity entry
        login_activity = LoginActivity(
            username=username,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            was_successful=False
        )
        
        try:
            # Try to authenticate
            user = super().authenticate(request, username, password, **kwargs)
            if user:
                # Authentication successful
                login_activity.user = user
                login_activity.was_successful = True
                login_activity.session_key = request.session.session_key
            else:
                # Authentication failed
                login_activity.failure_reason = "Invalid credentials"
        except Exception as e:
            # Log any exceptions
            login_activity.failure_reason = str(e)[:100]
        
        # Save the activity log
        login_activity.save()
        
        # Return the user object (or None if authentication failed)
        return user
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip