"""
Strategy Pattern: Конкретні стратегії завантаження та Контекст.
Цей файл відповідає тільки за те, ЯК завантажити один конкретний файл.
"""
import os
import gdown
import yt_dlp
import shutil
from typing import Optional, List
from domain import IDownloadStrategy

from infrastructure.localization import _

VIDEO_FOLDER = "source_videos"

class YouTubeStrategy(IDownloadStrategy):
    """Strategy for downloading videos from YouTube via yt-dlp."""

    def can_handle(self, url: str) -> bool:
        return "youtube.com" in url or "youtu.be" in url

    def download(self, url: str, output_folder: str) -> Optional[str]:
        """Downloads video from YouTube with error handling."""
        print(_("youtube_download_start", url=url))
        
        formats_to_try = [
            {
                'format': 'best[ext=mp4]/best',
            },
            {
                'format': 'best',
            }
        ]
        
        base_opts = {
            'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True, 
            'no_warnings': True,
            'extractor_args': {'youtube': {'player_client': 'web'}},
            'nocheckcertificate': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(base_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                temp_filename = ydl.prepare_filename(info)
                base, ext = os.path.splitext(temp_filename)
                final_path = base + ".mp4"
                
                if os.path.exists(final_path):
                    print(f"[YT-DLP] Файл вже існує: {final_path}")
                    return final_path
        except Exception:
            pass
        
        for format_config in formats_to_try:
            try:
                ydl_opts = {**base_opts, **format_config}
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    temp_filename = ydl.prepare_filename(info)
                    base, ext = os.path.splitext(temp_filename)
                    
                    expected_mp4 = base + ".mp4"
                    expected_original = temp_filename
                    
                    print(f"[YT-DLP] Починаю завантаження (формат: {format_config['format'][:50]}...)")
                    ydl.download([url])
                    
                    if os.path.exists(expected_mp4):
                        print(_("download_success", path=expected_mp4))
                        return expected_mp4
                    
                    if os.path.exists(expected_original):
                        print(_("download_success", path=expected_original))
                        return expected_original
                    
                    base_name = os.path.basename(base)
                    output_dir = os.path.dirname(expected_mp4) if os.path.dirname(expected_mp4) else output_folder
                    
                    if os.path.exists(output_dir):
                        for file in os.listdir(output_dir):
                            file_path = os.path.join(output_dir, file)
                            if (file.startswith(base_name) and 
                                os.path.isfile(file_path) and 
                                file.endswith(('.mp4', '.webm', '.mkv', '.m4a', '.mp3'))):
                                print(f"[YT-DLP] Знайдено файл: {file_path}")
                                print(_("download_success", path=file_path))
                                return file_path
                    
                    continue
                    
            except yt_dlp.utils.DownloadError as e:
                error_str = str(e)
                if "ffmpeg" in error_str.lower() or "merge" in error_str.lower():
                    print(f"[YT-DLP] Формат потребує ffmpeg, пробую інший формат...")
                    continue
                else:
                    print(f"\n{'='*40}")
                    print(_("youtube_download_error_crit", error=error_str))
                    print(f"{'='*40}\n")
                    return None
            except Exception as e:
                print(f"[YT-DLP] Помилка з форматом: {e}, пробую інший...")
                continue
        
        print(f"[YT-DLP] Не вдалося завантажити відео жодним форматом")
        return None

class GoogleDriveStrategy(IDownloadStrategy):
    """Strategy for downloading files from Google Drive via gdown."""

    def can_handle(self, url: str) -> bool:
        return "drive.google.com" in url

    def download(self, url: str, output_folder: str) -> Optional[str]:
        print(_("drive_download_start", url=url))
        try:
            os.makedirs(output_folder, exist_ok=True)
            
            output_file = gdown.download(url, output=None, fuzzy=True, quiet=False)
            
            if output_file and os.path.exists(output_file):
                final_path = os.path.join(output_folder, os.path.basename(output_file))
                
                if os.path.exists(final_path):
                    if os.path.samefile(output_file, final_path):
                        print(_("download_success", path=final_path))
                        return final_path
                    os.remove(final_path)
                
                shutil.move(output_file, final_path)
                print(_("download_success", path=final_path))
                return final_path
            else:
                error_msg = f"gdown повернув None або файл не існує. output_file: {output_file}"
                print(_("drive_download_failed"))
                print(f"[GOOGLE DRIVE] {error_msg}")
                return None
        except FileNotFoundError as e:
            error_msg = f"Файл не знайдено: {e}"
            print(_("drive_download_error", error=error_msg))
            return None
        except PermissionError as e:
            error_msg = f"Помилка доступу: {e}"
            print(_("drive_download_error", error=error_msg))
            return None
        except Exception as e:
            error_msg = f"Несподівана помилка: {type(e).__name__}: {e}"
            print(_("drive_download_error", error=error_msg))
            import traceback
            print(f"[GOOGLE DRIVE] Traceback:\n{traceback.format_exc()}")
            return None

class VideoDownloader:
    """
    Strategy Pattern: Context.
    Manages strategies and selects appropriate one for each link.
    """
    def __init__(self, folder: str = VIDEO_FOLDER):
        self.folder = folder
        os.makedirs(self.folder, exist_ok=True)
      
        self.strategies: List[IDownloadStrategy] = [
            YouTubeStrategy(),
            GoogleDriveStrategy()
        ]

    def process_link(self, url: str) -> Optional[str]:
        """Processes link using appropriate strategy."""
        for strategy in self.strategies:
            if strategy.can_handle(url):
                return strategy.download(url, self.folder)
    
        print(_("no_strategy_for_link", url=url))
        return None