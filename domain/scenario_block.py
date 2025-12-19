
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

