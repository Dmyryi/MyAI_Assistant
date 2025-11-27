"""Конфигурация приложения"""
import os
from dataclasses import dataclass


@dataclass
class AppConfig:
    """Конфигурация приложения - Single Source of Truth"""
    client_secret_file: str = "client_secret.json"
    token_file: str = "token.enc"  # Зашифрованный файл вместо открытого JSON
    use_windows_credential_manager: bool = True  # Использовать Windows Credential Manager на Windows
    video_folder: str = "source_videos"
    frames_dir: str = "data/frames"
    db_file: str = "data/visual_db.json"
    cache_file: str = "data/visual_db.npy"
    feedback_file: str = "data/feedback.json"
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Создает конфигурацию из переменных окружения"""
        return cls(
            client_secret_file=os.getenv("CLIENT_SECRET_FILE", "client_secret.json"),
            token_file=os.getenv("TOKEN_FILE", "token.enc"),
            use_windows_credential_manager=os.getenv("USE_WIN_CRED", "true").lower() == "true",
            video_folder=os.getenv("VIDEO_FOLDER", "source_videos"),
            frames_dir=os.getenv("FRAMES_DIR", "data/frames"),
            db_file=os.getenv("DB_FILE", "data/visual_db.json"),
            cache_file=os.getenv("CACHE_FILE", "data/visual_db.npy"),
            feedback_file=os.getenv("FEEDBACK_FILE", "data/feedback.json"),
        )


# Глобальная конфигурация по умолчанию
default_config = AppConfig()

