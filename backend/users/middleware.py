from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from .models import LoginActivity

class LoginAttemptMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path == '/users/login/' and request.method == 'POST':
            username = request.POST.get('username', '')
            
            # Only create a log entry if we're not already in the authentication backend
            if not getattr(request, '_login_attempt_logged', False):
                login_activity = LoginActivity(
                    username=username,
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    was_successful=False,
                    failure_reason="Form submission failed"
                )
                login_activity.save()
                
                # Mark request to avoid duplicate logging
                request._login_attempt_logged = True
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before the view is called

        # List of URLs that should not be accessible to logged-in users
        restricted_urls = [
            reverse('landing_page'),  # Use the correct URL name here
            reverse('login'),
            reverse('register'),
        ]

        # Check if the user is authenticated and trying to access restricted URLs
        if request.user.is_authenticated and request.path in restricted_urls:
            return redirect('profile')

        response = self.get_response(request)
        return response