from abc import ABC, abstractmethod
from typing import List
from ...visual_frame import VisualFrame
from ...video_segment import VideoSegment


class IFrameRepository(ABC):
    """Frame and segment repository interface"""
    @abstractmethod
    def save(self, frames: List[VisualFrame]) -> None:
        """Сохраняет список кадров (старый метод для обратной совместимости)"""
        pass
    
    def save_segments(self, segments: List[VideoSegment]) -> None:
        """Сохраняет список сегментов (новый метод)"""
        all_frames = []
        for segment in segments:
            all_frames.extend(segment.key_frames)
        if all_frames:
            self.save(all_frames)
    
    @abstractmethod
    def load_all(self) -> List[VisualFrame]:
        """Загружает все кадры (старый метод для обратной совместимости)"""
        pass
    
    def load_all_segments(self) -> List[VideoSegment]:
        """Загружает все сегменты (новый метод)"""
        return []
    
    @abstractmethod
    def prune_missing(self) -> int:
        """Удаляет записи о несуществующих файлах"""
        pass

