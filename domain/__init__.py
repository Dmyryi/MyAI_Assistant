"""Domain layer: Entities и interfaces"""
from .entities import VisualFrame, ScenarioBlock, SearchResult
from .interfaces import (
    IDownloadStrategy,
    IDocumentSource,
    IVideoDownloader,
    ISearchEngine,
    IFrameRepository,
    IVideoIndexer,
    IAuthService
)

__all__ = [
    'VisualFrame',
    'ScenarioBlock',
    'SearchResult',
    'IDownloadStrategy',
    'IDocumentSource',
    'IVideoDownloader',
    'ISearchEngine',
    'IFrameRepository',
    'IVideoIndexer',
    'IAuthService'
]

