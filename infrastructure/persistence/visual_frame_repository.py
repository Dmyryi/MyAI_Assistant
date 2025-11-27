"""Repository Pattern: Реализация хранения кадров"""
import os
import json
from typing import List
from dataclasses import asdict
from domain.interfaces import IFrameRepository
from domain.entities import VisualFrame


class VisualFrameRepository(IFrameRepository):
    """Single Responsibility: Управление персистентностью кадров"""
    
    def __init__(self, db_file: str = "data/visual_db.json"):
        self.db_file = db_file
        self.db_dir = os.path.dirname(db_file)
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Создает директорию для БД, если её нет"""
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)
    
    def save(self, frames: List[VisualFrame]) -> None:
        """Сохраняет кадры в JSON файл"""
        all_data = []
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                all_data = []
        
        for frame in frames:
            all_data.append(asdict(frame))
        
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    def load_all(self) -> List[VisualFrame]:
        """Загружает все кадры из JSON файла"""
        if not os.path.exists(self.db_file):
            return []
        
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [VisualFrame(**item) for item in data]
        except (json.JSONDecodeError, IOError, TypeError):
            return []
    
    def prune_missing(self) -> int:
        """Удаляет записи о несуществующих файлах"""
        if not os.path.exists(self.db_file):
            return 0
        
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return 0
        
        original_len = len(data)
        filtered = [
            item for item in data 
            if item.get("frame_path") and os.path.exists(item["frame_path"])
        ]
        removed = original_len - len(filtered)
        
        if removed > 0:
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(filtered, f, ensure_ascii=False, indent=2)
            self._cleanup_empty_dirs()
        
        return removed
    
    def _cleanup_empty_dirs(self) -> None:
        """Очищает пустые директории кадров"""
        frames_dir = "data/frames"
        if not os.path.exists(frames_dir):
            return
        
        for root, dirs, files in os.walk(frames_dir, topdown=False):
            if not dirs and not files:
                try:
                    os.rmdir(root)
                except OSError:
                    pass

