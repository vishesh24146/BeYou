# messaging/tasks.py
from django.utils import timezone
from .models import Message
from .blockchain import validate_blockchain_integrity, batch_verify_messages
import random

def daily_blockchain_integrity_check():
    """
    Daily task to validate blockchain integrity and verify a random sample of messages
    """
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Running daily blockchain integrity check...")
    
    # Validate blockchain
    chain_valid = validate_blockchain_integrity()
    
    # Verify a random sample of messages
    total_messages = Message.objects.count()
    sample_size = min(100, total_messages)  # Verify up to 100 messages
    
    if sample_size > 0:
        # Get random sample
        sample_ids = random.sample(list(Message.objects.values_list('id', flat=True)), sample_size)
        messages_to_verify = Message.objects.filter(id__in=sample_ids)
        
        # Verify
        verification_results = batch_verify_messages(messages_to_verify)
        
        # Count successes
        successes = sum(1 for result in verification_results.values() if result)
        
        # Log results
        print(f"[{timestamp}] Blockchain integrity: {'VALID' if chain_valid else 'INVALID'}")
        print(f"[{timestamp}] Message verification: {successes}/{sample_size} verified successfully")
    
    return chain_valid