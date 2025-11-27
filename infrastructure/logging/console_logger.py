"""Infrastructure: Реализация логирования для консоли"""
from domain.interfaces import ILogger


class ConsoleLogger(ILogger):
    """Single Responsibility: Логирование в консоль"""
    
    def info(self, message: str) -> None:
        """Информационное сообщение"""
        print(message)
    
    def error(self, message: str) -> None:
        """Сообщение об ошибке"""
        print(f"❌ {message}")
    
    def warning(self, message: str) -> None:
        """Предупреждение"""
        print(f"⚠️ {message}")

