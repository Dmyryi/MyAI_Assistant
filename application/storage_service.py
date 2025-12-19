import os
import shutil
from pathlib import Path
from typing import List

class StorageService:
    """Manages local project file storage"""

    def __init__(self, base_dir: str = "."):
        self.base_path = Path(base_dir)
        self.media_path = self.base_path / "source_videos"
        self.data_path = self.base_path / "data"

        self.dirs_to_clean: List[Path] = [
            self.media_path,
            self.data_path / "frames",
        ]
        
        self.files_to_remove: List[Path] = [
            self.data_path / "feedback.json",
            self.data_path / "visual_db.json",
        ]

        self._ensure_dirs_exist()

    def _ensure_dirs_exist(self):
        """Creates directory structure if missing"""
        for p in self.dirs_to_clean:
            p.mkdir(parents=True, exist_ok=True)

    def get_total_size_bytes(self) -> int:
        """Calculates total size of files in media and data folders in bytes"""
        total_size = 0
        
        targets = [self.media_path, self.data_path]
        for target_dir in targets:
            if target_dir.exists():
                for p in target_dir.rglob('*'):
                    if p.is_file():
                        try:
                            total_size += p.stat().st_size
                        except OSError:
                            pass
        return total_size

    def clear_project_storage(self) -> bool:
        """Clears working folders and removes database files. Returns True on success"""
        success = True
        
        for folder in self.dirs_to_clean:
            if folder.exists():
                for item in folder.iterdir():
                    try:
                        if item.is_file() or item.is_symlink():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                    except Exception as e:
                        print(f"[Storage] Error deleting {item}: {e}")
                        success = False
        
        for file_path in self.files_to_remove:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                 print(f"[Storage] Error deleting file {file_path}: {e}")
                 success = False
                 
        self._ensure_dirs_exist()
        return success