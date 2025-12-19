"""
Dependency Inversion: Implementation of IVideoDownloader interface.
This file handles LIST of links and GUI interaction (progress, statuses).
"""
import sys
import os
from typing import List, Optional, Callable, Dict, Any
from domain import IVideoDownloader
from infrastructure.downloader_strategy import VideoDownloader
from infrastructure.localization import _

class VideoDownloaderImpl(IVideoDownloader):
    """Single Responsibility: High-level downloader implementation."""
    
    def __init__(self, output_dir: str = "source_videos"):
        self.output_dir = output_dir
        self._strategy_context = VideoDownloader(output_dir)
    
    def download_list(
        self,
        urls: List[str],
        output_dir: str,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> List[Dict[str, Any]]:
        """Downloads list of URLs and returns results."""
        
        cleaned_urls = [u.strip() for u in urls if u and u.strip()]
        results: List[Dict[str, Any]] = []
        
        def _emit(msg_type: str, message: str):
            if progress_callback:
                progress_callback(msg_type, message)
            else:
                encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
                safe_message = message.encode(encoding, errors="ignore").decode(encoding, errors="ignore")
                print(safe_message)
        
        if not cleaned_urls:
            _emit("status", _("no_download_links"))
            return results
        
        total = len(cleaned_urls)
        
        def _emit_progress(done: int):
            _emit("download_progress", {"current": done, "total": total})
        
        _emit_progress(0)
        
        for idx, url in enumerate(cleaned_urls, start=1):
            _emit("status", _("downloading_file_progress", idx=idx, total=total, url=url))
            
            try:
                file_path = self._strategy_context.process_link(url)
                
                if file_path and os.path.exists(file_path):
                    _emit("log", _("download_success", path=file_path))
                    results.append({"url": url, "status": "success", "path": file_path})
                elif file_path:
                    error_msg = f"Файл повернуто, але не знайдено на диску: {file_path}"
                    _emit("error", error_msg)
                    _emit("error", _("download_failed_for_url", url=url))
                    results.append({"url": url, "status": "error", "path": None, "error": error_msg})
                else:
                    _emit("error", _("download_failed_for_url", url=url))
                    results.append({"url": url, "status": "error", "path": None})
                    
            except Exception as e:
                error_msg = f"Несподівана помилка: {type(e).__name__}: {e}"
                _emit("error", error_msg)
                import traceback
                _emit("error", f"Traceback:\n{traceback.format_exc()}")
                results.append({"url": url, "status": "error", "path": None, "error": error_msg})
            finally:
                _emit_progress(idx)
        
        return results