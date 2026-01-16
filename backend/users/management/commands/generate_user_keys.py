from django.core.management.base import BaseCommand
from users.models import CustomUser, UserKey
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

class Command(BaseCommand):
    help = 'Generate encryption and signing keys for users who do not have them'

    def handle(self, *args, **options):
        users_processed = 0
        keys_generated = 0

        for user in CustomUser.objects.all():
            users_processed += 1
            
            # Check if user already has keys
            signing_key = UserKey.objects.filter(user=user, key_type='signing').first()
            encryption_key = UserKey.objects.filter(user=user, key_type='encryption').first()
            
            # Generate signing key if needed
            if not signing_key:
                self.stdout.write(f"Generating signing key for {user.username}")
                private_key, public_key = self.generate_key_pair()
                UserKey.objects.create(
                    user=user,
                    key_type='signing',
                    public_key=public_key,
                    private_key=private_key
                )
                keys_generated += 1
            
            # Generate encryption key if needed
            if not encryption_key:
                self.stdout.write(f"Generating encryption key for {user.username}")
                private_key, public_key = self.generate_key_pair()
                UserKey.objects.create(
                    user=user,
                    key_type='encryption',
                    public_key=public_key,
                    private_key=private_key
                )
                keys_generated += 1
        
        self.stdout.write(self.style.SUCCESS(
            f"Processed {users_processed} users, generated {keys_generated} keys"
        ))
    
    def generate_key_pair(self):
        """Generate an RSA key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Serialize private key to PEM format
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        # Serialize public key to PEM format
        public_key = private_key.public_key()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        return private_key_pem, public_key_pem