from abc import ABC, abstractmethod
from typing import Optional

class IDownloadStrategy(ABC):
    """Video download strategy interface"""
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Checks if strategy can handle URL"""
        pass
    
    @abstractmethod
    def download(self, url: str, output_folder: str) -> Optional[str]:
        """Downloads video and returns file path"""
        pass
