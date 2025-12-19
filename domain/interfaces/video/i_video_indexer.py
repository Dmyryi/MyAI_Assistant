from abc import ABC, abstractmethod
from typing import List
from ...visual_frame import VisualFrame
from ...video_segment import VideoSegment


class IVideoIndexer(ABC):
    """Video indexing interface"""
    @abstractmethod
    def extract_frames(self, video_path: str, threshold: float = 27.0) -> List[VisualFrame]:
        """Извлекает ключевые кадры из видео (старый метод для обратной совместимости)"""
        pass
    
    def extract_segments(self, video_path: str, threshold: float = 27.0) -> List[VideoSegment]:
        """Извлекает сегменты из видео (новый метод)"""
        frames = self.extract_frames(video_path, threshold)
        return []

