"""Infrastructure: Зашифрованное хранилище токенов"""
import os
import base64
import json
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from domain.interfaces import ITokenStorage


class EncryptedTokenStorage(ITokenStorage):
    """
    Single Responsibility: Шифрование и хранение токенов
    Использует Fernet (симметричное шифрование) с ключом, привязанным к системе
    """
    
    def __init__(self, token_file: str = "token.enc", use_system_key: bool = True):
        self.token_file = token_file
        self.use_system_key = use_system_key
        self._cipher = None
        self._init_cipher()
    
    def _init_cipher(self) -> None:
        """Инициализирует шифр с ключом, привязанным к системе"""
        # Генерируем ключ на основе системной информации
        if self.use_system_key:
            key = self._generate_system_key()
        else:
            # Для разработки: можно использовать фиксированный ключ из переменной окружения
            key = os.getenv("TOKEN_ENCRYPTION_KEY")
            if not key:
                # Генерируем ключ на основе имени пользователя и машины
                key = self._generate_system_key()
        
        # Создаем Fernet cipher
        try:
            self._cipher = Fernet(key)
        except Exception:
            # Если ключ невалидный, генерируем новый
            key = self._generate_system_key()
            self._cipher = Fernet(key)
    
    def _generate_system_key(self) -> bytes:
        """Генерирует ключ на основе системной информации"""
        import platform
        import getpass
        
        # Используем информацию о системе для генерации ключа
        system_info = f"{platform.node()}{getpass.getuser()}{platform.system()}"
        
        # Создаем ключ через PBKDF2
        salt = b'auto_montage_salt_2024'  # Можно сделать уникальным для каждого пользователя
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(system_info.encode()))
        return key
    
    def save_token(self, token_data: str) -> bool:
        """Сохраняет токен в зашифрованном виде"""
        try:
            encrypted_data = self._cipher.encrypt(token_data.encode('utf-8'))
            
            # Сохраняем в файл
            os.makedirs(os.path.dirname(self.token_file) if os.path.dirname(self.token_file) else '.', exist_ok=True)
            with open(self.token_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Устанавливаем права доступа только для владельца (только на Unix)
            if os.name != 'nt':
                os.chmod(self.token_file, 0o600)
            
            return True
        except Exception:
            return False
    
    def load_token(self) -> Optional[str]:
        """Загружает и расшифровывает токен"""
        if not os.path.exists(self.token_file):
            return None
        
        try:
            with open(self.token_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._cipher.decrypt(encrypted_data)
            return decrypted_data.decode('utf-8')
        except Exception:
            # Если не удалось расшифровать (например, на другой машине), возвращаем None
            return None
    
    def token_exists(self) -> bool:
        """Проверяет наличие сохраненного токена"""
        return os.path.exists(self.token_file)
    
    def delete_token(self) -> bool:
        """Удаляет сохраненный токен"""
        try:
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
            return True
        except Exception:
            return False

