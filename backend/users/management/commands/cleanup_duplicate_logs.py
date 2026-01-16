# Create a new file: users/management/commands/cleanup_duplicate_logs.py
from django.core.management.base import BaseCommand
from users.models import LoginActivity
from datetime import timedelta

class Command(BaseCommand):
    help = 'Clean up duplicate login activity logs'

    def handle(self, *args, **options):
        # Find logs with same username, timestamp within 1 second, and IP
        duplicates = 0
        
        # Get all login activities
        activities = LoginActivity.objects.all().order_by('timestamp')
        
        previous = None
        to_delete = []
        
        for activity in activities:
            if previous and previous.username == activity.username and \
               previous.ip_address == activity.ip_address and \
               abs((previous.timestamp - activity.timestamp).total_seconds()) < 1:
                
                # If one is "Form validation failed" and the other is more specific, keep the specific one
                if previous.failure_reason == "Form validation failed" and activity.failure_reason != "Form validation failed":
                    to_delete.append(previous.id)
                    previous = activity
                elif activity.failure_reason == "Form validation failed" and previous.failure_reason != "Form validation failed":
                    to_delete.append(activity.id)
                else:
                    # Otherwise keep the first one
                    to_delete.append(activity.id)
            else:
                previous = activity
        
        # Delete duplicates
        if to_delete:
            LoginActivity.objects.filter(id__in=to_delete).delete()
            duplicates = len(to_delete)
        
        self.stdout.write(self.style.SUCCESS(f'Removed {duplicates} duplicate login activity logs'))