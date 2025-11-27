"""Application Service: Координация индексации видео"""
import os
from typing import List
from domain.interfaces import IVideoIndexer, IFrameRepository
from domain.entities import VisualFrame

# Импортируем функцию локализации из инфраструктурного слоя
from infrastructure.localization import _

class VideoIndexingService:
    """Single Responsibility: Управление процессом индексации видео"""
    
    def __init__(
        self,
        indexer: IVideoIndexer,
        repository: IFrameRepository,
        video_folder: str = "source_videos"
    ):
        self.indexer = indexer
        self.repository = repository
        # --- ВАЖЛИВЕ ВИПРАВЛЕННЯ ---
        # Перетворюємо відносний шлях на абсолютний, щоб точно знати, де папка.
        # Це гарантує, що індексатор дивиться туди ж, куди і завантажувач.
        self.video_folder = os.path.abspath(video_folder)
        # ---------------------------
        self._ensure_video_folder()
    
    def _ensure_video_folder(self) -> None:
        """Создает папку для видео, если её нет"""
        if not os.path.exists(self.video_folder):
            os.makedirs(self.video_folder)
    
    def get_indexed_files(self) -> set:
        """Возвращает множество уже проиндексированных файлов"""
        frames = self.repository.load_all()
        return {frame.video_filename for frame in frames}
    
    def index_new_videos(self) -> int:
        """Индексирует новые видео из папки"""
        # --- ДОДАЄМО ДЕБАГ-ПРИНТ ---
        print(f"\n[DEBUG ІНДЕКСАТОРА] Шукаю відео в АБСОЛЮТНОМУ шляху: {self.video_folder}")
        # ---------------------------

        # Очистка несуществующих записей
        removed = self.repository.prune_missing()
        if removed > 0:
            # Используем локализованное сообщение
            print(_("video_indexing_pruned", count=removed))
        
        processed_files = self.get_indexed_files()
        
        # Получаем список файлов в папке с видео
        try:
            files_on_disk = [
                f for f in os.listdir(self.video_folder) 
                if f.endswith(('.mp4', '.mov', '.mkv'))
            ]
            print(f"[DEBUG ІНДЕКСАТОРА] Знайдено файлів на диску: {len(files_on_disk)}")
        except OSError as e:
             print(f"[DEBUG ІНДЕКСАТОРА] ❌ ПОМИЛКА доступу до папки: {e}")
             files_on_disk = []

        # Определяем новые файлы, которые еще не проиндексированы
        new_files = [f for f in files_on_disk if f not in processed_files]
        
        if not new_files:
            # Используем локализованное сообщение
            print(_("video_indexing_index_actual"))
            return 0
        
        # Используем локализованное сообщение
        print(_("video_indexing_new_videos_found", count=len(new_files)))
        success_count = 0
        
        for filename in new_files:
            full_path = os.path.join(self.video_folder, filename)
            try:
                # Извлекаем кадры из видео
                print(f"[DEBUG ІНДЕКСАТОРА] Починаю обробку: {filename}")
                frames = self.indexer.extract_frames(full_path)
                if frames:
                    # Сохраняем кадры в репозиторий
                    self.repository.save(frames)
                    # Используем локализованное сообщение
                    print(_("video_indexing_added_to_db", filename=filename))
                    success_count += 1
            except Exception as e:
                # Используем локализованное сообщение об ошибке
                print(_("video_indexing_error_with_file", filename=filename, error=e))
                import traceback
                traceback.print_exc()
        
        return success_count