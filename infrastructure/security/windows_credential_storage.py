"""Infrastructure: Хранение токенов в Windows Credential Manager"""
import platform
from typing import Optional
from domain.interfaces import ITokenStorage


class WindowsCredentialStorage(ITokenStorage):
    """
    Single Responsibility: Хранение токенов в Windows Credential Manager
    Более безопасно, чем файл, так как использует системное хранилище
    """
    
    def __init__(self, credential_name: str = "AutoMontageAI_GoogleToken"):
        if platform.system() != 'Windows':
            raise RuntimeError("WindowsCredentialStorage доступен только на Windows")
        
        self.credential_name = credential_name
        self._wincred = None
        self._init_wincred()
    
    def _init_wincred(self) -> None:
        """Инициализирует Windows Credential Manager"""
        try:
            import wincred
            self._wincred = wincred
        except ImportError:
            try:
                # Альтернатива через pywin32
                import win32cred
                self._wincred = win32cred
                self._use_win32 = True
            except ImportError:
                raise ImportError(
                    "Для использования WindowsCredentialStorage установите: "
                    "pip install pywin32 или pip install pywincred"
                )
    
    def save_token(self, token_data: str) -> bool:
        """Сохраняет токен в Windows Credential Manager"""
        try:
            if hasattr(self._wincred, 'CredWrite'):
                # Используем wincred
                self._wincred.CredWrite({
                    'Type': 1,  # CRED_TYPE_GENERIC
                    'TargetName': self.credential_name,
                    'UserName': 'AutoMontageAI',
                    'CredentialBlob': token_data.encode('utf-8'),
                    'Persist': 2  # CRED_PERSIST_LOCAL_MACHINE
                }, 0)
            else:
                # Используем win32cred
                import win32cred
                win32cred.CredWrite({
                    'Type': win32cred.CRED_TYPE_GENERIC,
                    'TargetName': self.credential_name,
                    'UserName': 'AutoMontageAI',
                    'CredentialBlob': token_data.encode('utf-8'),
                    'Persist': win32cred.CRED_PERSIST_LOCAL_MACHINE
                }, 0)
            
            return True
        except Exception:
            return False
    
    def load_token(self) -> Optional[str]:
        """Загружает токен из Windows Credential Manager"""
        try:
            if hasattr(self._wincred, 'CredRead'):
                # Используем wincred
                cred = self._wincred.CredRead(self.credential_name, 1, 0)
                return cred['CredentialBlob'].decode('utf-8')
            else:
                # Используем win32cred
                import win32cred
                cred = win32cred.CredRead(self.credential_name, win32cred.CRED_TYPE_GENERIC, 0)
                return cred['CredentialBlob'].decode('utf-8')
        except Exception:
            return None
    
    def token_exists(self) -> bool:
        """Проверяет наличие сохраненного токена"""
        return self.load_token() is not None
    
    def delete_token(self) -> bool:
        """Удаляет сохраненный токен"""
        try:
            if hasattr(self._wincred, 'CredDelete'):
                self._wincred.CredDelete(self.credential_name, 1, 0)
            else:
                import win32cred
                win32cred.CredDelete(self.credential_name, win32cred.CRED_TYPE_GENERIC, 0)
            return True
        except Exception:
            return False

