from django.db import models
from django.conf import settings
from users.models import CustomUser
import uuid
from cryptography.fernet import Fernet
from django.conf import settings

class Conversation(models.Model):
    CONVERSATION_TYPES = (
        ('direct', 'Direct'),
        ('group', 'Group'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, blank=True, null=True)  # Only used for group conversations
    conversation_type = models.CharField(max_length=10, choices=CONVERSATION_TYPES, default='direct')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def is_group(self):
        return self.conversation_type == 'group'
    
    def get_other_participant(self, user):
        """Return the other participant in a direct conversation"""
        if not self.is_group:
            participant = self.participants.exclude(user=user).first()
            if participant:
                return participant.user
        return None
    
    def __str__(self):
        if self.is_group:
            return f"Group: {self.name}"
        participants = self.participants.all()
        if participants.count() == 2:
            return f"Conversation between {participants[0].user.username} and {participants[1].user.username}"
        return f"Conversation {self.id}"

class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='conversations')
    is_admin = models.BooleanField(default=False)  # For group conversations
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('conversation', 'user')
    
    def __str__(self):
        return f"{self.user.username} in {self.conversation}"

class Message(models.Model):
    MEDIA_TYPES = (
        ('none', 'None'),
        ('image', 'Image'),
        ('video', 'Video'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    encrypted_content = models.TextField(blank=True, null=True)  # Store encrypted message content
    media_file = models.FileField(upload_to='message_media/', blank=True, null=True)  # For media messages
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES, default='none')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    # Add fields for message signing and E2E encryption
    signature = models.TextField(blank=True, null=True)  # Sender's signature
    is_encrypted = models.BooleanField(default=False)  # Whether the message is E2E encrypted
    blockchain_hash = models.CharField(max_length=64, blank=True, null=True)
    integrity_verified = models.BooleanField(default=False)
    
    def encrypt_message(self, content):
        if content:
            key = settings.ENCRYPTION_KEY.encode()
            f = Fernet(key)
            encrypted_message = f.encrypt(content.encode())
            self.encrypted_content = encrypted_message.decode()
        
    def decrypt_message(self):
        if not self.encrypted_content:
            return ""
        key = settings.ENCRYPTION_KEY.encode()
        f = Fernet(key)
        decrypted_message = f.decrypt(self.encrypted_content.encode())
        return decrypted_message.decode()
    
    @property
    def is_media_message(self):
        return self.media_type != 'none' and self.media_file
    
    @property
    def is_image(self):
        return self.media_type == 'image'
    
    @property
    def is_video(self):
        return self.media_type == 'video'
    
    def save(self, *args, **kwargs):
        # First save to get an ID if this is a new message
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Only add to blockchain if it's a new message with content
        if is_new and (self.encrypted_content or self.media_file):
            from .blockchain import record_message
            blockchain_hash = record_message(self)
            if blockchain_hash:
                # Update without triggering another save cycle
                type(self).objects.filter(pk=self.pk).update(
                    blockchain_hash=blockchain_hash,
                    integrity_verified=True
                )
                # Update instance attributes
                self.blockchain_hash = blockchain_hash
                self.integrity_verified = True
    
    def __str__(self):
        if self.is_media_message:
            return f"Media message from {self.sender.username} in {self.conversation}"
        return f"Message from {self.sender.username} in {self.conversation}"

class EncryptedMessageContent(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='encrypted_contents')
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_encrypted_messages')
    encrypted_content = models.TextField()  # Content encrypted with recipient's public key
    
    class Meta:
        unique_together = ('message', 'recipient')

class UserConversationKey(models.Model):
    """Store encryption keys for each user in a conversation"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='conversation_keys')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='user_keys')
    encrypted_key = models.TextField()  # The conversation key encrypted with the user's public key
    
    class Meta:
        unique_together = ('user', 'conversation')

class UserMessageKey(models.Model):
    """Store individual encrypted message content for each recipient"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='message_keys')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='recipient_keys')
    encrypted_content = models.TextField()  # Content encrypted with recipient's public key
    
    class Meta:
        unique_together = ('user', 'message')
        
    def __str__(self):
        return f"Encrypted message for {self.user.username}"
        
    def decrypt_with_private_key(self, private_key_pem):
        """Decrypt the message content with the recipient's private key"""
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend
            
            # Load the private key
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None,
                backend=default_backend()
            )
            
            # Decrypt the content
            decrypted_content = private_key.decrypt(
                bytes.fromhex(self.encrypted_content),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return decrypted_content.decode()
        except Exception as e:
            print(f"Error decrypting message: {e}")
            return None