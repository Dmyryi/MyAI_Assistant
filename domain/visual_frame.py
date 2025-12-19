@dataclass
class VisualFrame:
    """Entity: Represents a single frame from a video"""
    video_filename: str
    timestamp: float
    frame_path: str
    
    def __post_init__(self):
        """Validates data"""
        if self.timestamp < 0:
            raise ValueError("Timestamp не может быть отрицательным")
        if not self.video_filename:
            raise ValueError("Имя файла не может быть пустым")