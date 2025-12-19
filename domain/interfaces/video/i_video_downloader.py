from abc import ABC, abstractmethod
from typing import List, Optional, Callable

class IVideoDownloader(ABC):
    """Dependency Inversion: Абстракция для загрузчика видео"""
    @abstractmethod
    def download_list(
        self, 
        urls: List[str], 
        output_dir: str, 
        progress_callback: Optional[Callable[[str, dict], None]] = None
    ) -> List[dict]:
        """Загружает список URL и возвращает результаты"""
        pass
