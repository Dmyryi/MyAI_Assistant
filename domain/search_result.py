
@dataclass
class SearchResult:
    """Entity: Результат поиска кадра/сегмента по тексту сценария"""
    scenario_text_snippet: str
    video_filename: str
    timecode_str: str
    timestamp_seconds: float
    accuracy_score: float
    frame_path: str
    tags: List[str]
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    segment_id: Optional[str] = None
    
    def __post_init__(self):
        """Валидация данных"""
        if not 0.0 <= self.accuracy_score <= 1.0:
            raise ValueError("Accuracy score должен быть между 0 и 1")
        if self.timestamp_seconds < 0:
            raise ValueError("Timestamp не может быть отрицательным")
        if self.start_time is not None and self.end_time is not None:
            if self.start_time < 0:
                raise ValueError("Start time не может быть отрицательным")
            if self.end_time <= self.start_time:
                raise ValueError("End time должен быть больше start time")
    
    def is_segment(self) -> bool:
        """Проверяет, является ли результат сегментом (а не отдельным кадром)"""
        return self.start_time is not None and self.end_time is not None
    
    def get_timecode_range(self) -> str:
        """Возвращает строку с временным диапазоном для сегмента"""
        if not self.is_segment():
            return self.timecode_str
        
        def format_timecode(seconds: float) -> str:
            m = int(seconds // 60)
            s = int(seconds % 60)
            return f"{m:02d}:{s:02d}"
        
        start_tc = format_timecode(self.start_time)
        end_tc = format_timecode(self.end_time)
        return f"{start_tc} - {end_tc}"