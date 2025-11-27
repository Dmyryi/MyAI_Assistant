import os
import shutil
from pathlib import Path
from typing import List

class StorageService:
    """
    Single Responsibility: Управление локальным хранилищем файлов проекта.
    Отвечает за подсчет занимаемого места и очистку рабочих директорий.
    """

    def __init__(self, base_dir: str = "."):
        # Базовые пути
        self.base_path = Path(base_dir)
        self.media_path = self.base_path / "source_videos"
        self.data_path = self.base_path / "data"

        # Список директорий, содержимое которых нужно чистить
        # Мы не удаляем сами папки 'videos', 'thumbnails' и т.д., только файлы внутри них
        self.dirs_to_clean: List[Path] = [
            self.media_path,
            self.data_path / "frames",
        
        ]
        
        # Список конкретных файлов для удаления
        self.files_to_remove: List[Path] = [
            self.data_path / "feedback.json",
            self.data_path / "visual_db.json",
         
        ]

        self._ensure_dirs_exist()

    def _ensure_dirs_exist(self):
        """Создает структуру папок, если её нет"""
        for p in self.dirs_to_clean:
            p.mkdir(parents=True, exist_ok=True)

    def get_total_size_bytes(self) -> int:
        """Считает общий размер файлов в рабочих папках media и data в байтах."""
        total_size = 0
        
        # Считаем размер всех файлов в целевых папках (рекурсивно)
        targets = [self.media_path, self.data_path]
        for target_dir in targets:
            if target_dir.exists():
                for p in target_dir.rglob('*'):
                    if p.is_file():
                        try:
                            total_size += p.stat().st_size
                        except OSError:
                            pass # Игнорируем ошибки доступа, если файлы заняты
        return total_size

    def clear_project_storage(self) -> bool:
        """
        Очищает содержимое рабочих папок и удаляет базу данных.
        Возвращает True, если все прошло успешно.
        """
        success = True
        
        # 1. Очищаем содержимое директорий
        for folder in self.dirs_to_clean:
            if folder.exists():
                for item in folder.iterdir():
                    try:
                        if item.is_file() or item.is_symlink():
                            item.unlink() # Удаляем файл
                        elif item.is_dir():
                            shutil.rmtree(item) # Удаляем вложенную папку
                    except Exception as e:
                        print(f"[Storage] Error deleting {item}: {e}")
                        success = False
        
        # 2. Удаляем конкретные файлы (БД)
        for file_path in self.files_to_remove:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                 print(f"[Storage] Error deleting file {file_path}: {e}")
                 success = False
                 
        # Пересоздаем структуру на всякий случай
        self._ensure_dirs_exist()
        return success