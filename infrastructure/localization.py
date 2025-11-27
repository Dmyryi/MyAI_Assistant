import json
import os
from typing import Dict, List

class LocalizationManager:
    """
    Клас для керування багатомовністю в програмі.
    Завантажує переклади з JSON файлів.
    (Знаходиться в шарі Infrastructure)
    """
    
    def __init__(self, locales_dir: str, default_lang: str = "en"):
        self.locales_dir = locales_dir
        self._current_lang = default_lang
        self.translations: Dict[str, str] = {}
        # Завантажуємо мову за замовчуванням при старті
        self.load_language(default_lang)

    @property
    def current_language(self) -> str:
        """Повертає код поточної мови."""
        return self._current_lang

    def get_available_languages(self) -> List[str]:
        """Сканує папку локалей і повертає список доступних кодів мов."""
        languages = []
        if os.path.exists(self.locales_dir):
            for filename in os.listdir(self.locales_dir):
                if filename.endswith(".json"):
                    # Видаляємо розширення .json, залишаємо тільки код (напр., 'ru')
                    languages.append(filename[:-5])
        # Сортуємо, щоб 'en' зазвичай було першим, або просто за абеткою
        return sorted(languages)

    def load_language(self, lang_code: str) -> bool:
        """Завантажує файл перекладу для вказаної мови."""
        lang_file = os.path.join(self.locales_dir, f"{lang_code}.json")
        if not os.path.exists(lang_file):
            print(f"[Localization] Warning: Language file not found: {lang_file}")
            # Якщо не знайшли, пробуємо дефолтну (en), якщо це не вона сама
            if lang_code != "en" and lang_code != "ru" and lang_code != "uk":
                 print(f"[Localization] Falling back to default")
                 # Спробуємо завантажити хоча б щось
                 fallback_langs = self.get_available_languages()
                 if fallback_langs:
                     return self.load_language(fallback_langs[0])
            return False

        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self._current_lang = lang_code
            print(f"[Localization] Language switched to: {lang_code}")
            return True
        except json.JSONDecodeError as e:
             print(f"[Localization] Error parsing JSON for '{lang_code}': {e}")
             self.translations = {}
             return False
        except Exception as e:
             print(f"[Localization] Unexpected error loading '{lang_code}': {e}")
             self.translations = {}
             return False

    def get(self, key: str, **kwargs) -> str:
        """Отримує перекладений рядок за ключем з підтримкою форматування."""
        text = self.translations.get(key, key) # Повертає ключ, якщо переклад не знайдено
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError as e:
                # print(f"[Localization] Formatting error for key '{key}': missing arg {e}")
                return text
            except ValueError as e:
                 # print(f"[Localization] Formatting error for key '{key}': {e}")
                 return text
        return text

# --- НАЛАШТУВАННЯ ШЛЯХІВ ---
# Визначаємо шлях до папки locales відносно цього файлу.
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALES_PATH = os.path.join(_base_dir, "locales")

# Створюємо глобальний екземпляр (сінглтон)
i18n = LocalizationManager(LOCALES_PATH, default_lang="en")

# Створюємо короткий аліас для використання в коді
_ = i18n.get

