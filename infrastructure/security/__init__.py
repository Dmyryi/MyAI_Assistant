"""Security layer: Безопасное хранение токенов"""
import platform
from .encrypted_token_storage import EncryptedTokenStorage

# Автоматически выбираем лучшее хранилище
if platform.system() == 'Windows':
    try:
        from .windows_credential_storage import WindowsCredentialStorage
        # По умолчанию используем Windows Credential Manager на Windows
        DefaultTokenStorage = WindowsCredentialStorage
        __all__ = ['EncryptedTokenStorage', 'WindowsCredentialStorage', 'DefaultTokenStorage']
    except (ImportError, RuntimeError):
        # Fallback на зашифрованное хранилище
        DefaultTokenStorage = EncryptedTokenStorage
        __all__ = ['EncryptedTokenStorage', 'DefaultTokenStorage']
else:
    # На Linux/Mac используем зашифрованное хранилище
    DefaultTokenStorage = EncryptedTokenStorage
    __all__ = ['EncryptedTokenStorage', 'DefaultTokenStorage']

