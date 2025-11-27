"""Application Service: Управление загрузкой видео"""
from typing import List, Optional, Callable
from domain.interfaces import IVideoDownloader, IDownloadStrategy


class VideoDownloadService:
    """Single Responsibility: Координация загрузки видео"""
    
    def __init__(self, downloader: IVideoDownloader):
        self.downloader = downloader
    
    def download_videos(
        self,
        urls: List[str],
        progress_callback: Optional[Callable[[str, dict], None]] = None
    ) -> List[dict]:
        """Загружает список видео"""
        return self.downloader.download_list(urls, "", progress_callback)

