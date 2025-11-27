from dataclasses import dataclass
from typing import List, Optional


@dataclass
class VisualFrame:
    """Entity: Представляет один кадр из видео"""
    video_filename: str
    timestamp: float
    frame_path: str
    
    def __post_init__(self):
        """Валидация данных"""
        if self.timestamp < 0:
            raise ValueError("Timestamp не может быть отрицательным")
        if not self.video_filename:
            raise ValueError("Имя файла не может быть пустым")


@dataclass
class ScenarioBlock:
    """Entity: Блок текста из сценария"""
    text: str
    block_id: str
    
    def __post_init__(self):
        """Валидация данных"""
        if not self.text or len(self.text.strip()) < 1:
            raise ValueError("Текст блока не может быть пустым")
        if not self.block_id:
            raise ValueError("ID блока не может быть пустым")


@dataclass
class SearchResult:
    """Entity: Результат поиска кадра по тексту сценария"""
    scenario_text_snippet: str
    video_filename: str
    timecode_str: str
    timestamp_seconds: float
    accuracy_score: float
    frame_path: str
    tags: List[str]
    
    def __post_init__(self):
        """Валидация данных"""
        if not 0.0 <= self.accuracy_score <= 1.0:
            raise ValueError("Accuracy score должен быть между 0 и 1")
        if self.timestamp_seconds < 0:
            raise ValueError("Timestamp не может быть отрицательным")