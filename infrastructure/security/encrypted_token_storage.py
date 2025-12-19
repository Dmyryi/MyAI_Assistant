"""Infrastructure: Encrypted token storage"""
import os
import base64
import json
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from domain import ITokenStorage


class EncryptedTokenStorage(ITokenStorage):
    """
    Single Responsibility: Token encryption and storage
    Uses Fernet (symmetric encryption) with system-bound key
    """
    
    def __init__(self, token_file: str = "token.enc", use_system_key: bool = True):
        self.token_file = token_file
        self.use_system_key = use_system_key
        self._cipher = None
        self._init_cipher()
    
    def _init_cipher(self) -> None:
        """Initializes cipher with system-bound key"""
        if self.use_system_key:
            key = self._generate_system_key()
        else:
            key = os.getenv("TOKEN_ENCRYPTION_KEY")
            if not key:
                key = self._generate_system_key()
        
        try:
            self._cipher = Fernet(key)
        except Exception:
            key = self._generate_system_key()
            self._cipher = Fernet(key)
    
    def _generate_system_key(self) -> bytes:
        """Generates key based on system information"""
        import platform
        import getpass
        
        system_info = f"{platform.node()}{getpass.getuser()}{platform.system()}"
        
        salt = b'auto_montage_salt_2024'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(system_info.encode()))
        return key
    
    def save_token(self, token_data: str) -> bool:
        """Saves token in encrypted form"""
        try:
            encrypted_data = self._cipher.encrypt(token_data.encode('utf-8'))
            
            os.makedirs(os.path.dirname(self.token_file) if os.path.dirname(self.token_file) else '.', exist_ok=True)
            with open(self.token_file, 'wb') as f:
                f.write(encrypted_data)
            
            if os.name != 'nt':
                os.chmod(self.token_file, 0o600)
            
            return True
        except Exception:
            return False
    
    def load_token(self) -> Optional[str]:
        """Loads and decrypts token"""
        if not os.path.exists(self.token_file):
            return None
        
        try:
            with open(self.token_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._cipher.decrypt(encrypted_data)
            return decrypted_data.decode('utf-8')
        except Exception:
            return None
    
    def token_exists(self) -> bool:
        """Checks if saved token exists"""
        return os.path.exists(self.token_file)
    
    def delete_token(self) -> bool:
        """Deletes saved token"""
        try:
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
            return True
        except Exception:
            return False

