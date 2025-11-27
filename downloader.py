"""
Обратная совместимость: обертка для старого API downloader
"""
from infrastructure.downloading.video_downloader_impl import VideoDownloaderImpl

# Создаем глобальный экземпляр для обратной совместимости
_downloader = VideoDownloaderImpl()


def download_links(urls: list[str], progress_callback=None):
    """
    Скачивает список ссылок последовательно, возвращает статусы.
    progress_callback ожидает сигнатуру callback(type, message), как в GUI.
    """
    return _downloader.download_list(urls, "", progress_callback)


def download_from_drive(url):
    """Обратная совместимость для старого API"""
    from infrastructure.downloader_strategy import VideoDownloader
    downloader = VideoDownloader()
    return downloader.process_link(url)

