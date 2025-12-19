from abc import ABC, abstractmethod

class ILogger(ABC):
    """Logging interface"""
    @abstractmethod
    def info(self, message: str) -> None:
        """Information message"""
        pass
    
    @abstractmethod
    def error(self, message: str) -> None:
        """Error message"""
        pass
    
    @abstractmethod
    def warning(self, message: str) -> None:
        """Warning message"""
        pass