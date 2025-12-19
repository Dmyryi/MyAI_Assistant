"""Security layer: Secure token storage"""
import platform
from .encrypted_token_storage import EncryptedTokenStorage

if platform.system() == 'Windows':
    try:
        from .windows_credential_storage import WindowsCredentialStorage
        DefaultTokenStorage = WindowsCredentialStorage
        __all__ = ['EncryptedTokenStorage', 'WindowsCredentialStorage', 'DefaultTokenStorage']
    except (ImportError, RuntimeError):
        DefaultTokenStorage = EncryptedTokenStorage
        __all__ = ['EncryptedTokenStorage', 'DefaultTokenStorage']
else:
    DefaultTokenStorage = EncryptedTokenStorage
    __all__ = ['EncryptedTokenStorage', 'DefaultTokenStorage']

