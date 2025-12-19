
@dataclass
class VideoSegment:
    """Entity: Представляет сегмент (фрагмент) видео"""
    video_filename: str
    start_time: float
    end_time: float
    segment_id: str
    preview_frame_path: str
    key_frames: List[VisualFrame] = field(default_factory=list)
    
    def __post_init__(self):
        """Валидация данных"""
        if self.start_time < 0:
            raise ValueError("Start time не может быть отрицательным")
        if self.end_time <= self.start_time:
            raise ValueError("End time должен быть больше start time")
        if not self.video_filename:
            raise ValueError("Имя файла не может быть пустым")
        if not self.segment_id:
            raise ValueError("Segment ID не может быть пустым")
        if not self.preview_frame_path:
            raise ValueError("Preview frame path не может быть пустым")
    
    def duration(self) -> float:
        """Возвращает длительность сегмента в секундах"""
        return self.end_time - self.start_time
    
    def get_middle_timestamp(self) -> float:
        """Возвращает временную метку середины сегмента (для обратной совместимости)"""
        return (self.start_time + self.end_time) / 2.0
