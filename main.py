
from infrastructure.google import OAuthService, GoogleDocsClient
from infrastructure.persistence import VisualFrameRepository
from infrastructure.ai import VideoIndexer, ClipSearchEngine
from infrastructure.logging.console_logger import ConsoleLogger
from infrastructure.security import DefaultTokenStorage
from application.video_indexing_service import VideoIndexingService
from application.document_analysis_service import DocumentAnalysisService
from presentation.app import App
from config import default_config
from application.storage_service import StorageService

def create_services():
    """Factory Method: Создает все необходимые сервисы"""
    # Infrastructure layer
    logger = ConsoleLogger()
    
    # Создаем безопасное хранилище токенов
    if default_config.use_windows_credential_manager:
        try:
            token_storage = DefaultTokenStorage()
        except (ImportError, RuntimeError):
            # Fallback на зашифрованное хранилище
            from infrastructure.security import EncryptedTokenStorage
            token_storage = EncryptedTokenStorage(default_config.token_file)
    else:
        from infrastructure.security import EncryptedTokenStorage
        token_storage = EncryptedTokenStorage(default_config.token_file)
    
    # OAuthService будет создан без callback, callback установится в GUI
    auth_service = OAuthService(
        default_config.client_secret_file,
        token_storage=token_storage,
        status_callback=None  # Будет установлен в GUI при необходимости
    )
    docs_client = GoogleDocsClient(auth_service)
    frame_repository = VisualFrameRepository(default_config.db_file)
    video_indexer = VideoIndexer(default_config.frames_dir)
    search_engine = ClipSearchEngine(
        frame_repository,
        cache_file=default_config.cache_file,
        feedback_file=default_config.feedback_file
    )
    
    # Application layer
    indexing_service = VideoIndexingService(
        video_indexer,
        frame_repository,
        default_config.video_folder
    )
    analysis_service = DocumentAnalysisService(
        docs_client,
        search_engine,
        logger=logger
    )
    storage_service = StorageService()
    
    return {
        'auth_service': auth_service,
        'docs_client': docs_client,
        'indexing_service': indexing_service,
        'analysis_service': analysis_service,
        'logger': logger,
        'storage_service': storage_service,
    }


def main():
    """Точка входа приложения"""
    # Dependency Injection: Создаем все зависимости
    services = create_services()
    
    # Presentation layer: Передаем сервисы в GUI
    app = App(
        analysis_service=services['analysis_service'],
        indexing_service=services['indexing_service'],
        auth_service=services['auth_service'],
        storage_service=services['storage_service']
    )
    
    app.mainloop()


if __name__ == "__main__":
    main()