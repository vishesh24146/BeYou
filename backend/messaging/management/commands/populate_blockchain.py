from django.core.management.base import BaseCommand
from messaging.models import Message
from messaging.blockchain import record_conversation_message

class Command(BaseCommand):
    help = 'Add existing messages to the blockchain'

    def handle(self, *args, **options):
        # Get all messages without blockchain hashes
        messages = Message.objects.filter(blockchain_hash__isnull=True)
        total = messages.count()
        
        self.stdout.write(f"Found {total} messages to add to blockchain")
        
        # Process messages
        count = 0
        for message in messages:
            blockchain_hash = record_conversation_message(message)
            if blockchain_hash:
                # Update the message
                Message.objects.filter(pk=message.pk).update(
                    blockchain_hash=blockchain_hash,
                    integrity_verified=True
                )
                count += 1
                
                if count % 10 == 0:
                    self.stdout.write(f"Processed {count}/{total} messages...")
        
        self.stdout.write(self.style.SUCCESS(f"Successfully added {count} messages to the blockchain"))