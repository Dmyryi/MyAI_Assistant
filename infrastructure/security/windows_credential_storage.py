"""Infrastructure: Token storage in Windows Credential Manager"""
import platform
from typing import Optional
from domain import ITokenStorage


class WindowsCredentialStorage(ITokenStorage):
    """
    Single Responsibility: Token storage in Windows Credential Manager
    More secure than file, as it uses system storage
    """
    
    def __init__(self, credential_name: str = "AutoMontageAI_GoogleToken"):
        if platform.system() != 'Windows':
            raise RuntimeError("WindowsCredentialStorage is only available on Windows")
        
        self.credential_name = credential_name
        self._wincred = None
        self._init_wincred()
    
    def _init_wincred(self) -> None:
        """Initializes Windows Credential Manager"""
        try:
            import wincred
            self._wincred = wincred
        except ImportError:
            try:
                import win32cred
                self._wincred = win32cred
                self._use_win32 = True
            except ImportError:
                raise ImportError(
                    "Для использования WindowsCredentialStorage установите: "
                    "pip install pywin32 или pip install pywincred"
                )
    
    def save_token(self, token_data: str) -> bool:
        """Saves token to Windows Credential Manager"""
        try:
            if hasattr(self._wincred, 'CredWrite'):
                self._wincred.CredWrite({
                    'Type': 1,
                    'TargetName': self.credential_name,
                    'UserName': 'AutoMontageAI',
                    'CredentialBlob': token_data.encode('utf-8'),
                    'Persist': 2
                }, 0)
            else:
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
        """Loads token from Windows Credential Manager"""
        try:
            if hasattr(self._wincred, 'CredRead'):
                cred = self._wincred.CredRead(self.credential_name, 1, 0)
                return cred['CredentialBlob'].decode('utf-8')
            else:
                import win32cred
                cred = win32cred.CredRead(self.credential_name, win32cred.CRED_TYPE_GENERIC, 0)
                return cred['CredentialBlob'].decode('utf-8')
        except Exception:
            return None
    
    def token_exists(self) -> bool:
        """Checks if saved token exists"""
        return self.load_token() is not None
    
    def delete_token(self) -> bool:
        """Deletes saved token"""
        try:
            if hasattr(self._wincred, 'CredDelete'):
                self._wincred.CredDelete(self.credential_name, 1, 0)
            else:
                import win32cred
                win32cred.CredDelete(self.credential_name, win32cred.CRED_TYPE_GENERIC, 0)
            return True
        except Exception:
            return False

