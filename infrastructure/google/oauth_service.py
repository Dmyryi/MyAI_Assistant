"""Single Responsibility: Управление OAuth аутентификацией"""
import os
import json
from typing import Optional, Callable
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from domain.interfaces import IAuthService, ITokenStorage

# Импортируем функцию локализации из инфраструктурного слоя
from infrastructure.localization import _

class OAuthService(IAuthService):
    """Single Responsibility: OAuth аутентификация для Google API"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/documents.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    
    def __init__(
        self,
        client_secret_file: str,
        token_storage: Optional[ITokenStorage] = None,
        status_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.client_secret_file = client_secret_file
        self.token_storage = token_storage
        self.status_callback = status_callback
        self.credentials: Optional[Credentials] = None
        self._load_credentials()
    
    def _emit(self, msg: str) -> None:
        """Отправляет сообщение через callback или печатает"""
        if self.status_callback:
            self.status_callback("status", msg)
        else:
            print(msg)
    
    def _load_credentials(self) -> None:
        """Загружает сохраненные учетные данные из безопасного хранилища"""
        if not self.token_storage:
            return
        
        token_data = self.token_storage.load_token()
        if token_data:
            try:
                # Парсим JSON из зашифрованных данных
                token_dict = json.loads(token_data)
                self.credentials = Credentials.from_authorized_user_info(
                    token_dict,
                    self.SCOPES
                )
            except Exception:
                self.credentials = None
    
    def authenticate(self) -> bool:
        """Выполняет аутентификацию"""
        # Обновление токена, если истек
        if self.credentials and self.credentials.expired and self.credentials.refresh_token:
            try:
                # Используем локализованное сообщение
                self._emit(_("oauth_refreshing_token"))
                self.credentials.refresh(Request())
                self._save_credentials()
                return True
            except Exception:
                self.credentials = None
        
        # Новая аутентификация
        if not self.credentials or not self.credentials.valid:
            if not os.path.exists(self.client_secret_file):
                # Используем локализованное сообщение об ошибке
                self._emit(_("oauth_client_secret_missing"))
                return False
            
            # Используем локализованное сообщение
            self._emit(_("oauth_open_browser_prompt"))
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secret_file, 
                    self.SCOPES
                )
                self.credentials = flow.run_local_server(port=0, prompt='consent')
                self._save_credentials()
                # Используем локализованное сообщение об успехе
                self._emit(_("oauth_auth_success"))
                return True
            except Exception as e:
                # Используем локализованное сообщение об ошибке с параметром
                self._emit(_("oauth_auth_error", error=e))
                return False
        
        return True
    
    def _save_credentials(self) -> None:
        """Сохраняет учетные данные в безопасное хранилище"""
        if not self.token_storage:
            return
        
        try:
            token_json = self.credentials.to_json()
            self.token_storage.save_token(token_json)
        except Exception as e:
            # Используем локализованное сообщение с предупреждением
            self._emit(_("oauth_token_save_warning", error=e))
    
    def is_authenticated(self) -> bool:
        """Проверяет статус аутентификации"""
        if not self.credentials:
            return False
        return self.credentials.valid
    
    def get_credentials(self) -> Optional[Credentials]:
        """Возвращает учетные данные"""
        return self.credentials