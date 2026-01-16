from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import LoginActivity
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta

class Command(BaseCommand):
    help = 'Check for suspicious login activity and send alerts'

    def handle(self, *args, **options):
        # Check for multiple failed attempts from same IP
        threshold = 5  # Failed attempts threshold
        time_window = timezone.now() - timedelta(hours=1)  # Last hour
        
        # Get IPs with multiple failed attempts
        suspicious_ips = {}
        for activity in LoginActivity.objects.filter(
            timestamp__gte=time_window,
            was_successful=False
        ):
            ip = activity.ip_address
            if ip not in suspicious_ips:
                suspicious_ips[ip] = 0
            suspicious_ips[ip] += 1
        
        # Filter IPs that exceed threshold
        alert_ips = {ip: count for ip, count in suspicious_ips.items() if count >= threshold}
        
        if alert_ips:
            # Format alert message
            message = "Suspicious login activity detected:\n\n"
            for ip, count in alert_ips.items():
                message += f"IP: {ip} - {count} failed attempts\n"
                # Get usernames tried
                usernames = LoginActivity.objects.filter(
                    ip_address=ip,
                    was_successful=False,
                    timestamp__gte=time_window
                ).values_list('username', flat=True).distinct()
                
                message += f"Attempted usernames: {', '.join(filter(None, usernames))}\n\n"
            
            # Send alert email to admins
            send_mail(
                'Security Alert: Suspicious Login Activity',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [admin[1] for admin in settings.ADMINS],
                fail_silently=False,
            )
            
            self.stdout.write(self.style.WARNING(f"Found {len(alert_ips)} suspicious IPs, sent alert email."))
        else:
            self.stdout.write(self.style.SUCCESS("No suspicious activity detected."))