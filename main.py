import os
import sys

if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(os.path.abspath(sys.executable)))

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
from oauth_config import get_client_secret_path

def create_services():
    """Creates and initializes all application services"""
    logger = ConsoleLogger()
    
    if default_config.use_windows_credential_manager:
        try:
            token_storage = DefaultTokenStorage()
        except (ImportError, RuntimeError):
            from infrastructure.security import EncryptedTokenStorage
            token_storage = EncryptedTokenStorage(default_config.token_file)
    else:
        from infrastructure.security import EncryptedTokenStorage
        token_storage = EncryptedTokenStorage(default_config.token_file)
    
    client_secret_path = get_client_secret_path(status_callback=logger.info if logger else None)
    
    auth_service = OAuthService(
        client_secret_path,
        token_storage=token_storage,
        status_callback=None
    )
    docs_client = GoogleDocsClient(auth_service)
    frame_repository = VisualFrameRepository(default_config.db_file)
    video_indexer = VideoIndexer(default_config.frames_dir)
    search_engine = ClipSearchEngine(
        frame_repository,
        cache_file=default_config.cache_file,
        feedback_file=default_config.feedback_file
    )
    
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
    """Application entry point"""
    services = create_services()
    
    app = App(
        analysis_service=services['analysis_service'],
        indexing_service=services['indexing_service'],
        auth_service=services['auth_service'],
        storage_service=services['storage_service']
    )
    
    app.mainloop()


if __name__ == "__main__":
    main()