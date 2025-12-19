"""
Backward compatibility: wrapper for old downloader API
"""
from infrastructure.downloading.video_downloader_impl import VideoDownloaderImpl

_downloader = VideoDownloaderImpl()


def download_links(urls: list[str], progress_callback=None):
    """
    Downloads list of links sequentially, returns statuses.
    progress_callback expects signature callback(type, message), as in GUI.
    """
    return _downloader.download_list(urls, "", progress_callback)


def download_from_drive(url):
    """Backward compatibility for old API"""
    from infrastructure.downloader_strategy import VideoDownloader
    downloader = VideoDownloader()
    return downloader.process_link(url)

