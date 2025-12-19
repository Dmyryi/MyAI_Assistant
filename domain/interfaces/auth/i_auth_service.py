from abc import ABC, abstractmethod

class IAuthService(ABC):
    """Authentication service interface"""
    @abstractmethod
    def authenticate(self) -> bool:
        """Performs authentication"""
        pass
    
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Checks authentication status"""
        pass
    
    @abstractmethod
    def get_credentials(self):
        """Returns credentials"""
        pass
