"""
Strategy Pattern: Конкретні стратегії завантаження та Контекст.
Цей файл відповідає тільки за те, ЯК завантажити один конкретний файл.
"""
import os
import gdown
import yt_dlp
import shutil
from typing import Optional, List
from domain.interfaces import IDownloadStrategy

# Імпортуємо функцію локалізації
from infrastructure.localization import _

# Константа для папки з відео за замовчуванням
VIDEO_FOLDER = "source_videos"

class YouTubeStrategy(IDownloadStrategy):
    """Стратегія для завантаження відео з YouTube через yt-dlp."""

    def can_handle(self, url: str) -> bool:
        return "youtube.com" in url or "youtu.be" in url

    def download(self, url: str, output_folder: str) -> Optional[str]:
        """Завантажує відео з YouTube з обробкою помилок."""
        print(_("youtube_download_start", url=url))
        
        # Налаштування для yt-dlp
        ydl_opts = {
            # Формат: найкраще mp4 відео + найкраще m4a аудіо, або просто найкраще mp4
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            # Зберігаємо у mp4 контейнер
            'merge_output_format': 'mp4',
            # Шлях та шаблон назви файлу
            'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
            # Не качати плейлисти
            'noplaylist': True,
            # Менше шуму в консолі
            'quiet': True, 
            'no_warnings': True,
            # Іноді допомагає обійти обмеження
            'extractor_args': {'youtube': {'player_client': 'web'}},
            # Ігнорувати помилки SSL
            'nocheckcertificate': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 1. Отримуємо інформацію
                info = ydl.extract_info(url, download=False)
                
                # Отримуємо очікуваний шлях до файлу
                temp_filename = ydl.prepare_filename(info)
                
                # Перевіряємо, чи файл вже існує, щоб не качати знову
                # Враховуємо, що розширення може змінитися після злиття (на .mp4)
                base, ext = os.path.splitext(temp_filename)
                final_path = base + ".mp4"

                if os.path.exists(final_path):
                    print(f"[YT-DLP] Файл вже існує: {final_path}")
                    return final_path

                # 2. Якщо файлу немає, починаємо завантаження
                print(f"[YT-DLP] Починаю завантаження у: {final_path}")
                ydl.download([url])
                
                # Ще раз перевіряємо, чи файл створився
                if os.path.exists(final_path):
                     print(_("download_success", path=final_path))
                     return final_path
                else:
                     # Якщо після завантаження файлу немає, щось пішло не так
                     raise Exception("Файл не знайдено після завантаження")

        except yt_dlp.utils.DownloadError as e:
            # --- ОСЬ ТУТ МИ ЛОВИМО ПОМИЛКУ YOUTUBE ---
            print(f"\n{'='*40}")
            # Локалізоване повідомлення про критичну помилку
            print(_("youtube_download_error_crit", error=str(e)))
            print(f"{'='*40}\n")
            return None
        except Exception as e:
            print(f"[НЕВІДОМА ПОМИЛКА] {e}")
            return None

class GoogleDriveStrategy(IDownloadStrategy):
    """Стратегія для завантаження файлів з Google Drive через gdown."""

    def can_handle(self, url: str) -> bool:
        return "drive.google.com" in url

    def download(self, url: str, output_folder: str) -> Optional[str]:
        print(_("drive_download_start", url=url))
        try:
            # Завантажуємо файл. output=None означає, що gdown сам визначить ім'я.
            # quiet=False щоб бачити прогрес gdown у консолі
            output_file = gdown.download(url, output=None, fuzzy=True, quiet=False)
            
            if output_file:
                # Переміщуємо завантажений файл у цільову папку
                final_path = os.path.join(output_folder, os.path.basename(output_file))
                # Якщо файл вже є в цільовій папці, shutil.move його перезапише
                shutil.move(output_file, final_path)
                print(_("download_success", path=final_path))
                return final_path
            else:
                print(_("drive_download_failed"))
                return None
        except Exception as e:
            print(_("drive_download_error", error=e))
            return None

class VideoDownloader:
    """
    Strategy Pattern: Контекст.
    Керує стратегіями та обирає потрібну для кожного посилання.
    """
    def __init__(self, folder: str = VIDEO_FOLDER):
        self.folder = folder
        # Створюємо папку, якщо її немає
        os.makedirs(self.folder, exist_ok=True)
      
        self.strategies: List[IDownloadStrategy] = [
            YouTubeStrategy(),
            GoogleDriveStrategy()
        ]

    def process_link(self, url: str) -> Optional[str]:
        """Обробляє посилання, використовуючи відповідну стратегію."""
        for strategy in self.strategies:
            if strategy.can_handle(url):
                # Передаємо папку, куди зберігати
                return strategy.download(url, self.folder)
    
        print(_("no_strategy_for_link", url=url))
        return None