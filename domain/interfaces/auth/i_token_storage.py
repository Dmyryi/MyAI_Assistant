from abc import ABC, abstractmethod
from typing import Optional

class ITokenStorage(ABC):
    """Secure token storage interface"""
    @abstractmethod
    def save_token(self, token_data: str) -> bool:
        """Saves token in encrypted form"""
        pass
    
    @abstractmethod
    def load_token(self) -> Optional[str]:
        """Loads and decrypts token"""
        pass
    
    @abstractmethod
    def token_exists(self) -> bool:
        """Checks if saved token exists"""
        pass
    
    @abstractmethod
    def delete_token(self) -> bool:
        """Deletes saved token"""
        pass