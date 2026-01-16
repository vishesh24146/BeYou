from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from base64 import b64encode, b64decode

def generate_key_pair():
    """Generate a new RSA key pair"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Serialize private key to PEM format (This would be client-side in production)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Serialize public key to PEM format
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return {'private_key': private_pem, 'public_key': public_pem}

def load_public_key(pem_public_key):
    """Load a public key from PEM format"""
    try:
        public_key = serialization.load_pem_public_key(
            pem_public_key.encode(),
            backend=default_backend()
        )
        return public_key
    except Exception as e:
        print(f"Error loading public key: {e}")
        return None

def load_private_key(pem_private_key):
    """Load a private key from PEM format"""
    try:
        private_key = serialization.load_pem_private_key(
            pem_private_key.encode(),
            password=None,
            backend=default_backend()
        )
        return private_key
    except Exception as e:
        print(f"Error loading private key: {e}")
        return None

def sign_message(private_key_pem, message):
    """Sign a message with a private key"""
    try:
        private_key = load_private_key(private_key_pem)
        
        signature = private_key.sign(
            message.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return b64encode(signature).decode('utf-8')
    except Exception as e:
        print(f"Error signing message: {e}")
        return None

def verify_signature(public_key_pem, message, signature):
    """Verify a message signature with a public key"""
    try:
        public_key = load_public_key(public_key_pem)
        decoded_signature = b64decode(signature)
        
        public_key.verify(
            decoded_signature,
            message.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return True
    except Exception as e:
        print(f"Signature verification failed: {e}")
        return False

def encrypt_for_recipient(public_key_pem, message):
    """Encrypt a message with a recipient's public key"""
    try:
        public_key = load_public_key(public_key_pem)
        
        ciphertext = public_key.encrypt(
            message.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return b64encode(ciphertext).decode('utf-8')
    except Exception as e:
        print(f"Error encrypting message: {e}")
        return None

def decrypt_message(private_key_pem, encrypted_message):
    """Decrypt a message with the recipient's private key"""
    try:
        private_key = load_private_key(private_key_pem)
        decoded_ciphertext = b64decode(encrypted_message)
        
        plaintext = private_key.decrypt(
            decoded_ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return plaintext.decode('utf-8')
    except Exception as e:
        print(f"Error decrypting message: {e}")
        return None