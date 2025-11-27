"""
Dependency Inversion: Реалізація інтерфейсу IVideoDownloader.
Цей файл відповідає за обробку СПИСКУ посилань та взаємодію з GUI (прогрес, статуси).
"""
import sys
from typing import List, Optional, Callable, Dict, Any
from domain.interfaces import IVideoDownloader
# Імпортуємо Контекст стратегій
from infrastructure.downloader_strategy import VideoDownloader

# Імпортуємо функцію локалізації
from infrastructure.localization import _

class VideoDownloaderImpl(IVideoDownloader):
    """Single Responsibility: Реалізація високорівневого завантажувача."""
    
    def __init__(self, output_dir: str = "source_videos"):
        self.output_dir = output_dir
        # Створюємо екземпляр низькорівневого завантажувача (Контексту)
        self._strategy_context = VideoDownloader(output_dir)
    
    def download_list(
        self,
        urls: List[str],
        output_dir: str, # Цей параметр тут для сумісності з інтерфейсом, ми використовуємо self.output_dir
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> List[Dict[str, Any]]:
        """Завантажує список URL і повертає результати."""
        
        cleaned_urls = [u.strip() for u in urls if u and u.strip()]
        results: List[Dict[str, Any]] = []
        
        # Допоміжна функція для відправки повідомлень
        def _emit(msg_type: str, message: str):
            if progress_callback:
                progress_callback(msg_type, message)
            else:
                # Безпечний вивід у консоль
                encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
                safe_message = message.encode(encoding, errors="ignore").decode(encoding, errors="ignore")
                print(safe_message)
        
        if not cleaned_urls:
            _emit("status", _("no_download_links"))
            return results
        
        total = len(cleaned_urls)
        
        # Допоміжна функція для відправки прогресу
        def _emit_progress(done: int):
            _emit("download_progress", {"current": done, "total": total})
        
        _emit_progress(0)
        
        for idx, url in enumerate(cleaned_urls, start=1):
            _emit("status", _("downloading_file_progress", idx=idx, total=total, url=url))
            
            try:
                # ВІДДАЄМО ПОСИЛАННЯ СТРАТЕГІЇ І ЧЕКАЄМО РЕЗУЛЬТАТ
                file_path = self._strategy_context.process_link(url)
                
                if file_path:
                    _emit("log", _("download_success", path=file_path))
                    results.append({"url": url, "status": "success", "path": file_path})
                else:
                    # Якщо стратегія повернула None, значить сталася помилка (вона вже надрукована в консоль)
                    _emit("error", _("download_failed_for_url", url=url))
                    results.append({"url": url, "status": "error", "path": None})
                    
            except Exception as e:
                # Цей блок ловить помилки тільки в самому високорівневому коді,
                # помилки yt-dlp ловляться всередині YouTubeStrategy.
                _emit("error", f"Несподівана помилка: {e}")
                results.append({"url": url, "status": "error", "path": None})
            finally:
                # Завжди оновлюємо прогрес-бар
                _emit_progress(idx)
        
        return results