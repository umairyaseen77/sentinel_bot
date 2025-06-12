import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_SIZE = 16

def get_key_from_password(password: str, salt: bytes) -> bytes:
    """Derives a cryptographic key from a password and salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt(data: str, password: str) -> str:
    """Encrypts data using a password, embedding the salt in the output."""
    if not data:
        return ""
    salt = os.urandom(SALT_SIZE)
    key = get_key_from_password(password, salt)
    f = Fernet(key)
    encrypted_data = f.encrypt(data.encode())
    # Prepend the salt to the encrypted data for storage
    return base64.urlsafe_b64encode(salt + encrypted_data).decode('utf-8')

def decrypt(encrypted_str: str, password: str) -> str:
    """Decrypts data using a password, extracting the salt from the input."""
    if not encrypted_str:
        return ""
    try:
        decoded_data = base64.urlsafe_b64decode(encrypted_str.encode('utf-8'))
        salt = decoded_data[:SALT_SIZE]
        encrypted_data = decoded_data[SALT_SIZE:]
        key = get_key_from_password(password, salt)
        f = Fernet(key)
        return f.decrypt(encrypted_data).decode()
    except Exception as e:
        # This can happen if the master password is wrong
        print(f"Decryption failed: {e}")
        raise ValueError("Decryption failed. The master password may be incorrect.")

def hash_password(password: str) -> bytes:
    """Hashes a password for verification purposes, embedding the salt."""
    salt = os.urandom(SALT_SIZE)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    hashed_password = kdf.derive(password.encode())
    # Prepend salt to hash for storage
    return salt + hashed_password

def verify_password(stored_hash: bytes, provided_password: str) -> bool:
    """Verifies a provided password against a stored hash."""
    try:
        salt = stored_hash[:SALT_SIZE]
        actual_hash = stored_hash[SALT_SIZE:]
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        kdf.verify(provided_password.encode(), actual_hash)
        return True
    except Exception:
        return False 