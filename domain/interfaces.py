from abc import ABC, abstractmethod
from typing import List, Iterator, Optional, Callable
from .entities import ScenarioBlock, SearchResult, VisualFrame


class ITokenStorage(ABC):
    """Interface Segregation: Интерфейс для безопасного хранения токенов"""
    @abstractmethod
    def save_token(self, token_data: str) -> bool:
        """Сохраняет токен в зашифрованном виде"""
        pass
    
    @abstractmethod
    def load_token(self) -> Optional[str]:
        """Загружает и расшифровывает токен"""
        pass
    
    @abstractmethod
    def token_exists(self) -> bool:
        """Проверяет наличие сохраненного токена"""
        pass
    
    @abstractmethod
    def delete_token(self) -> bool:
        """Удаляет сохраненный токен"""
        pass


class ILogger(ABC):
    """Interface Segregation: Интерфейс для логирования"""
    @abstractmethod
    def info(self, message: str) -> None:
        """Информационное сообщение"""
        pass
    
    @abstractmethod
    def error(self, message: str) -> None:
        """Сообщение об ошибке"""
        pass
    
    @abstractmethod
    def warning(self, message: str) -> None:
        """Предупреждение"""
        pass


class IDownloadStrategy(ABC):
    """Strategy Pattern: Интерфейс для стратегий загрузки видео"""
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Проверяет, может ли стратегия обработать URL"""
        pass
    
    @abstractmethod
    def download(self, url: str, output_folder: str) -> Optional[str]:
        """Загружает видео и возвращает путь к файлу"""
        pass


class IDocumentSource(ABC):
    """Interface Segregation: Интерфейс для источников документов"""
    @abstractmethod
    def connect(self, resource_id: str) -> None:
        """Подключается к источнику документа"""
        pass
    
    @abstractmethod
    def extract_blocks(self) -> Iterator[ScenarioBlock]:
        """Извлекает блоки текста из документа"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Проверяет, подключен ли источник"""
        pass


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


class ISearchEngine(ABC):
    """Dependency Inversion: Абстракция для поискового движка"""
    @abstractmethod
    def search(self, query_text: str, limit: int = 5) -> List[tuple[VisualFrame, float]]:
        """Ищет кадры по текстовому запросу"""
        pass
    
    @abstractmethod
    def record_feedback(self, frame: VisualFrame, is_positive: bool) -> None:
        """Сохраняет обратную связь для улучшения поиска"""
        pass
    
    @abstractmethod
    def is_ready(self) -> bool:
        """Проверяет, готов ли движок к работе"""
        pass
    
    @abstractmethod
    def extract_tags(self, text: str) -> List[str]:
        """Извлекает ключевые слова/теги из текста"""
        pass


class IFrameRepository(ABC):
    """Repository Pattern: Интерфейс для хранения кадров"""
    @abstractmethod
    def save(self, frames: List[VisualFrame]) -> None:
        """Сохраняет список кадров"""
        pass
    
    @abstractmethod
    def load_all(self) -> List[VisualFrame]:
        """Загружает все кадры"""
        pass
    
    @abstractmethod
    def prune_missing(self) -> int:
        """Удаляет записи о несуществующих файлах"""
        pass


class IVideoIndexer(ABC):
    """Single Responsibility: Интерфейс для индексации видео"""
    @abstractmethod
    def extract_frames(self, video_path: str, threshold: float = 27.0) -> List[VisualFrame]:
        """Извлекает ключевые кадры из видео"""
        pass


class IAuthService(ABC):
    """Interface Segregation: Интерфейс для аутентификации"""
    @abstractmethod
    def authenticate(self) -> bool:
        """Выполняет аутентификацию"""
        pass
    
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Проверяет статус аутентификации"""
        pass
    
    @abstractmethod
    def get_credentials(self):
        """Возвращает учетные данные"""
        pass
