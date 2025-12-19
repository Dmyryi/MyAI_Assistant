from abc import ABC, abstractmethod
from typing import List, Tuple
from ...visual_frame import VisualFrame
from ...video_segment import VideoSegment

class ISearchEngine(ABC):
    """Search engine interface"""
    @abstractmethod
    def search(self, query_text: str, limit: int = 5) -> List[tuple[VisualFrame, float]]:
        """Ищет кадры по текстовому запросу (старый метод для обратной совместимости)"""
        pass
    
    def search_segments(self, query_text: str, limit: int = 5) -> List[tuple[VideoSegment, float]]:
        """Ищет сегменты по текстовому запросу (новый метод)"""
        frame_results = self.search(query_text, limit)
        return []
    
    @abstractmethod
    def record_feedback(self, frame: VisualFrame, is_positive: bool) -> None:
        """Сохраняет обратную связь для улучшения поиска"""
        pass
    
    def record_segment_feedback(self, segment: VideoSegment, is_positive: bool) -> None:
        """Сохраняет обратную связь для сегмента"""
        if segment.key_frames:
            self.record_feedback(segment.key_frames[0], is_positive)
    
    @abstractmethod
    def is_ready(self) -> bool:
        """Проверяет, готов ли движок к работе"""
        pass
    
    @abstractmethod
    def extract_tags(self, text: str) -> List[str]:
        """Извлекает ключевые слова/теги из текста"""
        pass
